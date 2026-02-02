import logging
from datetime import datetime, timedelta
from supabase import create_client
from config.settings import settings

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_KEY
        if not self.url or not self.key:
            logger.error("Supabase API 정보가 누락되었습니다.")
            self.client = None
        else:
            self.client = create_client(self.url, self.key)

    def is_already_sent(self, link: str) -> bool:
        """DB에서 URL 존재 여부 확인"""
        if not self.client: return False
        try:
            res = self.client.table("news_articles").select("url").eq("url", link).execute()
            return len(res.data) > 0
        except Exception as e:
            logger.error(f"DB 조회 실패: {e}")
            return False

    def add_article(self, article: dict):
        """기사 상세 정보를 DB에 Upsert"""
        if not self.client: return
        try:
            data = {
                "url": article['link'],
                "source": article['source'],
                "title": article['title'],
                "score": article.get('score', 0),
                "reason": article.get('reason', ""),
                "created_at": datetime.now().isoformat()
            }
            self.client.table("news_articles").upsert(data).execute()
        except Exception as e:
            logger.error(f"DB 저장 실패: {e}")

    def clean_old_state(self, days=30):
        """무료 용량 관리를 위해 30일 지난 데이터 삭제"""
        if not self.client: return
        try:
            limit = (datetime.now() - timedelta(days=days)).isoformat()
            self.client.table("news_articles").delete().lt("created_at", limit).execute()
        except Exception as e:
            logger.error(f"DB 정리 실패: {e}")