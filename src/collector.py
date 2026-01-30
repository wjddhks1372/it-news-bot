import feedparser
import logging
import asyncio
import httpx # 여전히 비동기 처리를 위해 필요
from urllib.parse import urlparse, urlunparse
from typing import List, Dict

logger = logging.getLogger(__name__)

class NewsCollector:
    def __init__(self):
        self.sources = {
            # GeekNews: 쿼리 파라미터를 붙여 캐시를 우회하고 봇 탐지를 흐립니다.
            "GeekNews": "https://news.hada.io/rss?v=1", 
            "ITWorld_Korea": "https://www.itworld.co.kr/rss/feed/index.php",
            "HackerNews": "https://news.ycombinator.com/rss",
            "AWS_News": "https://aws.amazon.com/ko/blogs/aws/feed/",
            "Unity_Blog": "https://unity.com/kr/blog/rss",
            "Toss_Tech": "https://toss.tech/rss.xml",
            "Karrot_Tech": "https://medium.com/feed/daangn"
        }
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com/" # 구글에서 유입된 것처럼 위장
        }

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

    async def _fetch_feed(self, client: httpx.AsyncClient, name: str, url: str) -> List[Dict]:
        try:
            # ITWorld 같은 사이트를 위해 주소 끝에 슬래시 유무를 강제 조정하지 않음
            response = await client.get(url, timeout=15.0, follow_redirects=True, headers=self.headers)
            
            if response.status_code == 403 and "hada.io" in url:
                logger.warning(f"⚠️ {name}가 차단되었습니다. 다른 주소 시도...")
                # 403 발생 시 우회 주소로 한 번 더 시도
                response = await client.get("https://news.hada.io/rss", timeout=15.0, follow_redirects=True, headers=self.headers)

            if response.status_code != 200:
                logger.error(f"❌ {name} 응답 에러: {response.status_code} ({url})")
                return []

            feed = feedparser.parse(response.text)
            articles = []
            for entry in feed.entries[:15]:
                articles.append({
                    "source": name,
                    "title": entry.get("title", "제목 없음").strip(),
                    "link": self._normalize_url(entry.get("link", "")),
                    "description": entry.get("description", ""),
                    "published": entry.get("published", "")
                })
            logger.info(f"✅ {name} 수집 성공 ({len(articles)}건)")
            return articles
            
        except Exception as e:
            logger.error(f"❌ {name} 연결 실패: {str(e)}")
            return []

    async def collect_all(self) -> List[Dict]:
        async with httpx.AsyncClient(http2=True) as client: # HTTP/2 활성화로 봇 탐지 우회 확률 증가
            tasks = [self._fetch_feed(client, name, url) for name, url in self.sources.items()]
            results = await asyncio.gather(*tasks)
            raw_articles = [a for sub in results for a in sub]
            
            unique_articles = {}
            for a in raw_articles:
                if a['link'] not in unique_articles:
                    unique_articles[a['link']] = a
            
            final_list = list(unique_articles.values())
            logger.info(f"🚀 전체 수집 완료: 총 {len(final_list)}건")
            return final_list