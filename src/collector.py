import feedparser
import logging
import asyncio
import httpx
from urllib.parse import urlparse, urlunparse
from typing import List, Dict

logger = logging.getLogger(__name__)

class NewsCollector:
    def __init__(self):
        self.sources = {
            "GeekNews": "https://news.hada.io/rss",
            "ITWorld_Korea": "https://www.itworld.co.kr/rss/feed/", # 주소 수정
            "HackerNews": "https://news.ycombinator.com/rss",
            "AWS_News": "https://aws.amazon.com/ko/blogs/aws/feed/",
            "Unity_Blog": "https://blog.unity.com/feed",
            "Toss_Tech": "https://toss.tech/rss.xml",
            "Karrot_Tech": "https://medium.com/feed/daangn"
        }
        # 브라우저처럼 보이게 하기 위한 헤더
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

    async def _fetch_feed(self, client: httpx.AsyncClient, name: str, url: str) -> List[Dict]:
        try:
            response = await client.get(url, timeout=10.0, follow_redirects=True, headers=self.headers)
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            
            articles = []
            # 최신 15개만 슬라이싱하여 수집 (792건 방지)
            for entry in feed.entries[:15]:
                articles.append({
                    "source": name,
                    "title": entry.get("title", "제목 없음").strip(),
                    "link": self._normalize_url(entry.get("link", "")),
                    "description": entry.get("description", ""),
                    "published": entry.get("published", "")
                })
            return articles
        except Exception as e:
            logger.error(f"❌ {name} 수집 실패: {e}")
            return []

    async def collect_all(self) -> List[Dict]:
        async with httpx.AsyncClient() as client:
            tasks = [self._fetch_feed(client, name, url) for name, url in self.sources.items()]
            results = await asyncio.gather(*tasks)
            raw_articles = [article for sublist in results for article in sublist]
            
            unique_articles = {}
            for article in raw_articles:
                if article['link'] not in unique_articles:
                    unique_articles[article['link']] = article
            
            final_list = list(unique_articles.values())
            logger.info(f"🚀 수집 완료: 총 {len(final_list)}건 (최신 항목 한정)")
            return final_list