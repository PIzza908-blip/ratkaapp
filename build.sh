#!/bin/bash
# Установка pip и зависимостей
python -m pip install --upgrade pip
python -m pip install flask gunicorn Pillow

# Проверяем, что gunicorn установлен
if ! command -v gunicorn &> /dev/null; then
    echo "gunicorn not found, installing again..."
    python -m pip install gunicorn
fi

echo "Build complete!"
