import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    # 설정
    RETRY_COUNT = 3
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 분석 타겟 (나중에 keywords.yaml로 분리 가능)
    TARGET_KEYWORDS = ["Kubernetes", "DevOps", "Docker", "Cloud Native", "Linux"]

settings = Settings()