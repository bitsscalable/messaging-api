import socketio

# Create a Socket.IO client for userB
sio = socketio.Client()

# Event: Connected to the server
@sio.event
def connect():
    print("UserB connected to WebSocket!")

# Event: Receive new messages
@sio.on('new_message')
def on_new_message(data):
    print("UserB received message:", data)

@sio.on('chat_history')
def on_chat_history(data):
    print("UserB received message:", data)

# Connect to the server
sio.connect('http://localhost:5000')

# Join a room
sio.emit('join', {'username': 'userA', 'peer': 'userB'})

# Send a message to userA
sio.emit('new_message', {
    'sender': 'userB',
    'recipient': 'userA',
    'message': 'Hello from userB!',
    'timestamp': '2024-11-20T12:05:00Z'
})

# Keep the connection open to listen for events
sio.wait()

