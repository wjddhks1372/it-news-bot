import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        # 1. API Keys (쉼표로 구분된 4개의 키를 정확히 파싱)
        _raw_keys = os.getenv("GEMINI_API_KEYS", "")
        self.GEMINI_API_KEYS = [k.strip() for k in _raw_keys.split(",") if k.strip()]
        
        # 2. Telegram (메시지가 안 온다면 이 환경 변수를 GitHub Secrets에서 다시 확인하세요)
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        self.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
        
        # 3. Supabase
        self.SUPABASE_URL = os.getenv("SUPABASE_URL")
        self.SUPABASE_KEY = os.getenv("SUPABASE_KEY")
        
        # 4. Logging
        self.LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

settings = Settings()