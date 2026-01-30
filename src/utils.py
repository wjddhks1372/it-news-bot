import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self, file_path="data/sent_articles.json"):
        self.file_path = file_path
        # 데이터 디렉토리 자동 생성
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        self.sent_articles = self._load_state()

    def _load_state(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def is_already_sent(self, link: str) -> bool:
        return link in self.sent_articles

    def add_article(self, link: str):
        self.sent_articles[link] = datetime.now().isoformat()
        self._save_state()

    def _save_state(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.sent_articles, f, ensure_ascii=False, indent=2)

    def clean_old_state(self, days=7):
        """7일 이상 된 기록은 삭제하여 파일 크기를 유지합니다."""
        now = datetime.now()
        cutoff = now - timedelta(days=days)
        
        initial_count = len(self.sent_articles)
        self.sent_articles = {
            link: ts for link, ts in self.sent_articles.items()
            if datetime.fromisoformat(ts) > cutoff
        }
        
        if initial_count != len(self.sent_articles):
            self._save_state()
            logger.info(f"오래된 상태 데이터 정리 완료 ({initial_count} -> {len(self.sent_articles)})")