import logging
from supabase import create_client
from config.settings import settings

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self):
        self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    def is_already_sent(self, url: str) -> bool:
        res = self.client.table("news_articles").select("url").eq("url", url).execute()
        return len(res.data) > 0

    def add_article(self, article: dict):
        self.client.table("news_articles").insert({
            "title": article['title'],
            "url": article['link'],
            "score": article.get('score', 0),
            "reason": article.get('reason', ""),
            "source": article.get('source', "")
        }).execute()

    def get_user_persona(self):
        """DB에서 캐싱된 취향 데이터를 가져옵니다."""
        try:
            res = self.client.table("user_preferences").select("*").eq("persona_type", "main").single().execute()
            return res.data
        except:
            return None

    def save_user_persona(self, pref, dislike):
        """취향 데이터를 DB에 캐싱합니다."""
        self.client.table("user_preferences").update({
            "preference_summary": pref,
            "dislike_summary": dislike,
            "updated_at": "now()"
        }).eq("persona_type", "main").execute()

    def clean_old_state(self, days=30):
        from datetime import datetime, timedelta
        threshold = (datetime.now() - timedelta(days=days)).isoformat()
        self.client.table("news_articles").delete().lt("created_at", threshold).execute()