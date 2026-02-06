import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class StateManager:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE 환경변수가 없습니다.")
        # 속성명을 'db'로 고정하여 모듈 간 인터페이스 일치
        self.db: Client = create_client(url, key)

    def is_already_sent(self, url: str) -> bool:
        res = self.db.table("news_articles").select("url").eq("url", url).execute()
        return len(res.data) > 0

    def add_article(self, article: dict):
        self.db.table("news_articles").insert({
            "title": article['title'],
            "url": article['link'],
            "source": article['source'],
            "score": article.get('score', 0)
        }).execute()

    def clean_old_state(self):
        pass