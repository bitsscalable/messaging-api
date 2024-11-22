from flask import Flask, jsonify
from flask_socketio import SocketIO, emit, join_room
import pika
import threading
import json
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from flask_cors import CORS  # Import CORS
import eventlet
import eventlet.wsgi

import hashlib
import logging


logging.basicConfig(level=logging.DEBUG)
logging.getLogger('pymongo').setLevel(logging.WARNING)
logging.getLogger('pika').setLevel(logging.WARNING)



# Flask Setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

CORS(app)

MONGODB_HOST="mongodb://mongo-db:27017/"
RABBITMQ_HOST="rabbitmq"
# MongoDB Setup
client = MongoClient(MONGODB_HOST)
db = client.chat_database
messages_collection = db.messages
channels_collection = db.channels

# Store user-room mapping
users = {}

def start_rabbitmq_listener():
    """
    Starts a RabbitMQ listener that continuously listens for messages.
    """
    def callback(ch, method, properties, body):
        """
        RabbitMQ callback to process received messages.
        """
        print("Received message:", body)
        # Process the message and emit to the relevant WebSocket channel

        message = json.loads(body)
        sender = message['sender']
        recipient = message['recipient']
        room =  message['room']
        if room:
            # Send message to the recipient's room
            socketio.emit('new_message', message, to=room)

        message['timestamp'] = datetime.now().isoformat()
        messages_collection.insert_one(message)


    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
        channel = connection.channel()
        channel.queue_declare(queue="chat")
        channel.basic_consume(queue="chat", on_message_callback=callback, auto_ack=True)
        print("Starting RabbitMQ listener...")
        channel.start_consuming()
    except Exception as e:
        print("Error in RabbitMQ listener:", str(e))



def generate_chat_id(user1, user2):
    # Create a consistent string combining both usernames
    sorted_users = "-".join(sorted([user1, user2]))
    # Hash the string to create a unique identifier
    return hashlib.md5(sorted_users.encode()).hexdigest()

@socketio.on('connect') 
def on_connect():
    print("A user connected")

@socketio.on('join')
def on_join(data):
    username = data['username']
    peer = data['peer']
    room = generate_chat_id(username, peer)
    users[username] = room
    join_room(room)
    print(f"{username} joined room: {room}")

    # store channel details in DB

    try:
        # Check if the channel already exists in db
        channel = channels_collection.find_one({"name": room})

        if not channel:
            # Create a new channel
            channels_collection.insert_one({
                "name": room,
                "username": username,
                "peer": peer,
                "created_at": datetime.now().isoformat()
            })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    # Fetch chat history from MongoDB and ensure it's JSON serializable
    chat_history = list(messages_collection.find(
        {'$or': [
            {'sender': username, 'recipient': peer},
            {'sender': peer, 'recipient': username}
        ]}
    ).sort('timestamp'))

    # Convert MongoDB documents to JSON-serializable format
    for message in chat_history:
        if '_id' in message:
            del message['_id']
        

    print(chat_history)

    # Send chat history to the user
    emit('chat_history', chat_history, room=room)  # Emit to the specific room


@socketio.on('new_message')
def on_new_message(data):
    sender = data['sender']
    recipient = data['recipient']
    room = generate_chat_id(sender, recipient)
    data['room'] = room
    print(data)

    # Publish the message to RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue='chat')
    channel.basic_publish(exchange='', routing_key='chat', body=json.dumps(data))
    connection.close()
    print(f"Message from {sender} to {recipient} published to RabbitMQ")

@app.route('/api/messages/<username>/channels', methods=['GET'])
def get_user_channels(username):
    """
    API to fetch channels for a given username.
    """
    try:
        # Fetch channels where the user is sender
        channels = channels_collection.find({"username": username})
        
        # Convert MongoDB cursor to a list
        channel_list1 = [channel["peer"] for channel in channels]

        # Fetch channels where the user is a reciever
        channels = channels_collection.find({"peer": username})
        
        # Convert MongoDB cursor to a list
        channel_list2 = [channel["username"] for channel in channels]

        channel_list = channel_list1 + channel_list2
        
        return jsonify({"status": "success", "peers": channel_list}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Add a function to start the listener (to be called explicitly in the worker lifecycle)
# def start_listener_in_worker():
#     listener_thread = threading.Thread(target=start_rabbitmq_listener)
#     listener_thread.daemon = True
#     listener_thread.start()

if __name__ == '__main__':

    # Start RabbitMQ listener in a separate thread
    threading.Thread(target=start_rabbitmq_listener, daemon=True).start()
    eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 5000)), app)

