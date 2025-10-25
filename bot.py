import asyncio
import sqlite3
import json
import os
from datetime import datetime
from telethon import TelegramClient, events
from telegram import Bot
from telegram.ext import Application

def load_env():
    env_vars = {}
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    return env_vars

env_vars = load_env()

API_ID = int(env_vars['API_ID'])
API_HASH = env_vars['API_HASH']
BOT_TOKEN = env_vars['BOT_TOKEN']
NOTIFY_USER_ID = int(env_vars['NOTIFY_USER_ID'])
CHANNELS_CONFIG = json.loads(env_vars['CHANNELS_CONFIG'])

class DatabaseManager:
    def __init__(self):
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect('monitor.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_messages (
                message_id INTEGER PRIMARY KEY,
                chat_id INTEGER,
                chat_username TEXT,
                processed_at TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def is_message_processed(self, message_id):
        conn = sqlite3.connect('monitor.db')
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM processed_messages WHERE message_id = ?', (message_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    def mark_message_processed(self, message_id, chat_id, chat_username):
        conn = sqlite3.connect('monitor.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO processed_messages VALUES (?, ?, ?, ?)',
            (message_id, chat_id, chat_username, datetime.now())
        )
        conn.commit()
        conn.close()

class TelegramMonitor:
    def __init__(self):
        self.telegram_client = TelegramClient('session', API_ID, API_HASH)
        self.bot = Bot(token=BOT_TOKEN)
        self.db = DatabaseManager()
        self.channels_config = CHANNELS_CONFIG
        
        print("🚀 Бот запущен")
        print(f"📊 Каналов: {len(self.channels_config)}")
    
    async def check_message(self, text, channel):
        if not text: return None
        text_lower = text.lower()
        for phrase in self.channels_config.get(channel, []):
            if all(word.lower() in text_lower for word in phrase):
                return phrase
        return None
    
    async def send_notification(self, message_text, message_link, matched_phrase, channel_name):
        short_text = message_text[:300] + "..." if len(message_text) > 300 else message_text
        notification = f"🔔 **Совпадение в {channel_name}**\n\n"
        notification += f"**Фраза:** {', '.join(matched_phrase)}\n"
        notification += f"**Сообщение:** {short_text}\n"
        notification += f"**Ссылка:** {message_link}"
        
        try:
            await self.bot.send_message(
                chat_id=NOTIFY_USER_ID,
                text=notification,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            print("📤 Уведомление отправлено")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    async def message_handler(self, event):
        try:
            if self.db.is_message_processed(event.message.id):
                return
            
            message_text = event.message.text or ""
            chat = await event.get_chat()
            chat_id = f"@{chat.username}" if chat.username else f"id{chat.id}"
            
            if chat_id in self.channels_config:
                matched_phrase = await self.check_message(message_text, chat_id)
                if matched_phrase:
                    print(f"🎯 Найдено: {matched_phrase} в {chat_id}")
                    
                    message_link = f"https://t.me/{chat.username}/{event.message.id}" if chat.username else f"https://t.me/c/{str(chat.id)[4:]}/{event.message.id}"
                    
                    await self.send_notification(
                        message_text, message_link, matched_phrase, 
                        getattr(chat, 'title', chat_id)
                    )
                    
                    self.db.mark_message_processed(event.message.id, chat.id, chat_id)
                    
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    async def start_monitoring(self):
        await self.telegram_client.start()
        print("✅ Подключено")
        print("📢 Каналы:", list(self.channels_config.keys()))
        print("👂 Ожидание сообщений...\n" + "-"*50)
        
        @self.telegram_client.on(events.NewMessage)
        async def handler(event):
            await self.message_handler(event)
        
        await self.telegram_client.run_until_disconnected()
    
    async def stop_monitoring(self):
        await self.telegram_client.disconnect()
        print("⏹️ Остановлен")

async def main():
    monitor = TelegramMonitor()
    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\n🛑 Остановка...")
    finally:
        await monitor.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
