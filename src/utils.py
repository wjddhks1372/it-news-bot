import json
import os
import hashlib
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self, file_path="data/sent_articles.json", retention_days=7):
        self.file_path = file_path
        self.retention_days = retention_days
        # 데이터 저장 폴더가 없으면 생성
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """기존에 발송된 기사 데이터를 불러옵니다."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"상태 파일 로드 실패: {e}")
        return {}

    def _generate_hash(self, text: str) -> str:
        """기사 URL 등을 고유한 해시값으로 변환합니다."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def is_already_sent(self, article_url: str) -> bool:
        """이미 발송된 기사인지 확인합니다."""
        article_hash = self._generate_hash(article_url)
        return article_hash in self.state

    def add_article(self, article_url: str):
        """발송 목록에 기사를 추가합니다."""
        article_hash = self._generate_hash(article_url)
        self.state[article_hash] = datetime.now().isoformat()
        self._save_state()

    def _save_state(self):
        """현재 상태를 파일로 저장합니다."""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"상태 저장 실패: {e}")

    def clean_old_state(self):
        """설정된 기간(7일)보다 오래된 기록을 삭제하여 파일 크기를 유지합니다."""
        now = datetime.now()
        threshold = now - timedelta(days=self.retention_days)
        
        new_state = {}
        for h, ts in self.state.items():
            if datetime.fromisoformat(ts) > threshold:
                new_state[h] = ts
        
        self.state = new_state
        self._save_state()
        logger.info("오래된 상태 데이터 정리 완료.")