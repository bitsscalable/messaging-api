import socketio

# Create a Socket.IO client for userA
sio = socketio.Client()

# Event: Connected to the server
@sio.event
def connect():
    print("UserA connected to WebSocket!")

# Event: Receive new messages
@sio.on('new_message')
def on_new_message(data):
    print("UserA received message:", data)


@sio.on('chat_history')
def on_chat_history(data):
    print("UserA received message:", data)


# Connect to the server
sio.connect('http://localhost:5000')

# Join a room
sio.emit('join', {'username': 'userA', 'peer': 'userB'})

# Send a message to userB
sio.emit('new_message', {
    'sender': 'userA',
    'recipient': 'userB',
    'message': 'Hello3 from userA!',
    'timestamp': '2024-11-20T12:00:00Z'
})


# Keep the connection open to listen for events
sio.wait()

