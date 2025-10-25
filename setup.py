#!/usr/bin/env python3
import os
import json
import subprocess
import sys

def run_command(cmd):
    """Выполняет команду и возвращает результат"""
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка: {e}")
        return None

def install_dependencies():
    """Устанавливает системные зависимости"""
    print("🔧 Установка системных зависимостей...")
    
    # Определяем дистрибутив
    if os.path.exists('/etc/debian_version'):
        run_command('sudo apt update && sudo apt install -y python3 python3-pip python3-venv git')
    elif os.path.exists('/etc/redhat-release'):
        run_command('sudo yum install -y python3 python3-pip git')
    else:
        print("⚠️  Неизвестный дистрибутив, установите вручную: python3, pip, git")
    
    print("✅ Системные зависимости установлены")

def create_virtual_env():
    """Создает виртуальное окружение"""
    print("🐍 Создание виртуального окружения...")
    
    if not os.path.exists('bot_env'):
        run_command('python3 -m venv bot_env')
        print("✅ Виртуальное окружение создано")
    else:
        print("✅ Виртуальное окружение уже существует")

def install_python_packages():
    """Устанавливает Python пакеты"""
    print("📦 Установка Python пакетов...")
    
    # Создаем requirements.txt если его нет
    if not os.path.exists('requirements.txt'):
        with open('requirements.txt', 'w') as f:
            f.write("python-telegram-bot==20.7\ntelethon==1.28.5\naiohttp==3.8.5\n")
    
    # Устанавливаем пакеты
    run_command('bot_env/bin/pip install -r requirements.txt')
    print("✅ Python пакеты установлены")

def setup_env_file():
    """Настройка .env файла"""
    print("\n📝 Настройка конфигурации...")
    print("=" * 50)
    
    # Запрашиваем данные
    api_id = input("Введите API_ID (из my.telegram.org): ").strip()
    api_hash = input("Введите API_HASH (из my.telegram.org): ").strip()
    bot_token = input("Введите BOT_TOKEN (от @BotFather): ").strip()
    user_id = input("Введите ваш USER_ID (узнать у @userinfobot): ").strip()
    
    print("\n📢 Настройка каналов для мониторинга")
    print("Формат: channel_username:word1,word2;word3")
    print("Пример: @sales:продам,телевизор;куплю,смартфон")
    print("Оставьте пустым для завершения ввода")
    
    channels_config = {}
    
    while True:
        channel_input = input("\nВведите канал и фразы: ").strip()
        if not channel_input:
            break
            
        if ':' in channel_input:
            channel, phrases_str = channel_input.split(':', 1)
            channel = channel.strip()
            
            phrases = []
            for phrase_group in phrases_str.split(';'):
                words = [word.strip() for word in phrase_group.split(',') if word.strip()]
                if words:
                    phrases.append(words)
            
            if phrases:
                channels_config[channel] = phrases
                print(f"✅ Добавлен канал {channel} с {len(phrases)} фразами")
            else:
                print("❌ Неверный формат фраз")
        else:
            print("❌ Неверный формат. Используйте channel:phrases")
    
    # Создаем .env файл
    env_content = f"""# Данные от Telegram API
API_ID={api_id}
API_HASH={api_hash}

# Токен бота
BOT_TOKEN={bot_token}

# Ваш User ID для уведомлений
NOTIFY_USER_ID={user_id}

# Настройки базы данных
DB_PATH=monitor.db

# Конфигурация каналов и фраз
CHANNELS_CONFIG={json.dumps(channels_config, ensure_ascii=False)}
"""
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print(f"\n✅ Файл .env создан!")
    print(f"📊 Настроено каналов: {len(channels_config)}")

def setup_systemd_service():
    """Настройка systemd сервиса"""
    print("\n⚙️  Настройка автозапуска...")
    
    answer = input("Создать systemd сервис для автозапуска? (y/n): ").strip().lower()
    
    if answer == 'y':
        # Получаем текущую директорию
        current_dir = os.getcwd()
        
        # Читаем шаблон сервиса
        service_content = f"""[Unit]
Description=Telegram Monitor Bot
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'root')}
WorkingDirectory={current_dir}
Environment=PATH={current_dir}/bot_env/bin
ExecStart={current_dir}/bot_env/bin/python {current_dir}/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
        
        # Сохраняем файл сервиса
        with open('telegram-bot.service', 'w') as f:
            f.write(service_content)
        
        # Копируем в systemd и активируем
        run_command('sudo cp telegram-bot.service /etc/systemd/system/')
        run_command('sudo systemctl daemon-reload')
        run_command('sudo systemctl enable telegram-bot.service')
        
        print("✅ Systemd сервис создан и активирован")
        return True
    else:
        print("ℹ️  Systemd сервис не создан")
        return False

def create_start_script():
    """Создает скрипт для ручного запуска"""
    start_script = """#!/bin/bash
cd "$(dirname "$0")"
source bot_env/bin/activate
python bot.py
"""
    
    with open('start.sh', 'w') as f:
        f.write(start_script)
    
    run_command('chmod +x start.sh')
    print("✅ Скрипт start.sh создан")

def main():
    print("🚀 Установка Telegram Monitor Bot")
    print("=" * 50)
    
    # Устанавливаем зависимости
    install_dependencies()
    create_virtual_env()
    install_python_packages()
    
    # Настраиваем конфигурацию
    setup_env_file()
    
    # Создаем скрипт запуска
    create_start_script()
    
    # Настраиваем systemd
    has_systemd = setup_systemd_service()
    
    # Выводим итоговую инструкцию
    print("\n🎉 УСТАНОВКА ЗАВЕРШЕНА!")
    print("=" * 50)
    
    if has_systemd:
        print("\n📋 УПРАВЛЕНИЕ СЕРВИСОМ:")
        print("sudo systemctl start telegram-bot.service    # Запустить")
        print("sudo systemctl stop telegram-bot.service     # Остановить")
        print("sudo systemctl restart telegram-bot.service  # Перезапустить")
        print("sudo systemctl status telegram-bot.service   # Статус")
        print("sudo journalctl -u telegram-bot.service -f   # Логи")
        print("\nБот будет автоматически запускаться при загрузке системы")
    else:
        print("\n📋 РУЧНОЙ ЗАПУСК:")
        print("./start.sh    # Запустить бота")
        print("Ctrl+C        # Остановить бота")
    
    print("\n🔧 РЕДАКТИРОВАНИЕ НАСТРОЕК:")
    print("nano .env        # Редактировать конфигурацию")
    print("После изменения .env перезапустите бота")
    
    print("\n📞 ПРОВЕРКА РАБОТЫ:")
    print("1. Отправьте тестовое сообщение в мониторируемый канал")
    print("2. Проверьте что приходит уведомление")
    
    if has_systemd:
        print("\n▶️  ДЛЯ ЗАПУСКА ВЫПОЛНИТЕ:")
        print("sudo systemctl start telegram-bot.service")

if __name__ == "__main__":
    main()
