from flask import Flask
from flask_socketio import SocketIO, emit, join_room
import pika
import threading
import json
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from flask_cors import CORS  # Import CORS


# Flask Setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

CORS(app)


# MongoDB Setup
client = MongoClient('mongodb://mongo-db:27017/')
db = client.chat_database
messages_collection = db.messages

# Store user-room mapping
users = {}

# RabbitMQ Listener
def start_rabbitmq_listener():

    connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))

    channel = connection.channel()
    channel.queue_declare(queue='chat')

    def callback(ch, method, properties, body):
        message = json.loads(body)
        recipient = message['recipient']
        room = users.get(recipient)
        if room:
            # Send message to the recipient's room
            socketio.emit('new_message', message, to=room)
        # Store message in MongoDB
        message['timestamp'] = datetime.now().isoformat()
        messages_collection.insert_one(message)

    channel.basic_consume(queue='chat', on_message_callback=callback, auto_ack=True)
    channel.start_consuming()

# Start RabbitMQ listener in a separate thread
threading.Thread(target=start_rabbitmq_listener, daemon=True).start()

@socketio.on('connect')
def on_connect():
    print("A user connected")

@socketio.on('join')
def on_join(data):
    username = data['username']
    peer = data['peer']
    room = f"{username}_{peer}"  # Unique room for the two users
    users[username] = room
    join_room(room)
    print(f"{username} joined room: {room}")

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

    # Publish the message to RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
    channel = connection.channel()
    channel.queue_declare(queue='chat')
    channel.basic_publish(exchange='', routing_key='chat', body=json.dumps(data))
    connection.close()
    print(f"Message from {sender} to {recipient} published to RabbitMQ")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)

