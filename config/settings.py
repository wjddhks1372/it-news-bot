import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        # API Keys
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        self.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
        
        # Supabase Config (새로 추가)
        self.SUPABASE_URL = os.getenv("SUPABASE_URL")
        self.SUPABASE_KEY = os.getenv("SUPABASE_KEY")
        
        # System Settings
        self.LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

settings = Settings()