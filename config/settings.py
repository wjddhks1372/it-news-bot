import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        # 1. Gemini API Keys (쉼표 구분 파싱)
        _raw_keys = os.getenv("GEMINI_API_KEYS", "")
        self.GEMINI_API_KEYS = [k.strip() for k in _raw_keys.split(",") if k.strip()]
        
        # [방어 로직] 복수 키가 없을 경우 단일 키 변수 확인
        if not self.GEMINI_API_KEYS:
            single_key = os.getenv("GEMINI_API_KEY")
            if single_key:
                self.GEMINI_API_KEYS = [single_key]
        
        # 2. Telegram Config
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        self.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
        
        # 3. Supabase Config
        self.SUPABASE_URL = os.getenv("SUPABASE_URL")
        self.SUPABASE_KEY = os.getenv("SUPABASE_KEY")
        
        # 4. System Settings
        # 가독성을 위해 format에서 name(logger 이름)을 제거하여 로그 길이를 최적화함
        self.LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

settings = Settings()