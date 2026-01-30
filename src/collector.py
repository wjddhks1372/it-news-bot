import feedparser
import logging
from typing import List, Dict

# 로깅 설정 (실무에서는 print 대신 logging을 사용함)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsCollector:
    def __init__(self):
        # 수집할 RSS 소스 목록 (추후 config/keywords.yaml로 이동 예정)
        self.sources = {
            "GeekNews": "https://news.hada.io/rss",
            "ITWorld_Korea": "https://www.itworld.co.kr/rss/feed/index.php",
            "HackerNews": "https://news.ycombinator.com/rss"
        }

    def collect_all(self) -> List[Dict]:
        """모든 소스로부터 최신 기사를 수집합니다."""
        all_articles = []
        
        for name, url in self.sources.items():
            try:
                logger.info(f"수집 중: {name}")
                feed = feedparser.parse(url)
                
                for entry in feed.entries:
                    article = {
                        "source": name,
                        "title": entry.title,
                        "link": entry.link,
                        "description": entry.get("description", ""),
                        "published": entry.get("published", "")
                    }
                    all_articles.append(article)
                    
            except Exception as e:
                logger.error(f"{name} 수집 중 오류 발생: {e}")
                
        return all_articles

    def filter_by_keywords(self, articles: List[Dict], keywords: List[str]) -> List[Dict]:
        """키워드가 포함된 긴급 기사를 필터링합니다."""
        urgent_articles = []
        for article in articles:
            # 제목이나 설명에 키워드가 있는지 확인 (대소문자 구분 없음)
            if any(kw.lower() in article['title'].lower() or kw.lower() in article['description'].lower() for kw in keywords):
                urgent_articles.append(article)
        return urgent_articles