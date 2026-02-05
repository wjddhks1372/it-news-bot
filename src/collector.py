import httpx
import feedparser
import logging
import asyncio

logger = logging.getLogger(__name__)

class NewsCollector:
    def __init__(self):
        self.sources = [
            # 국내 핵심 소스
            {"name": "Toss_Tech", "url": "https://toss.tech/rss.xml"},
            {"name": "Karrot_Tech", "url": "https://medium.com/feed/daangn"},
            {"name": "Naver_D2", "url": "https://d2.naver.com/d2.atom"},
            {"name": "Kakao_Tech", "url": "https://tech.kakao.com/feed/"},
            
            # [글로벌 소스 확장]
            {"name": "HackerNews", "url": "https://news.ycombinator.com/rss"},
            {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
            {"name": "TheVerge", "url": "https://www.theverge.com/rss/index.xml"},
            {"name": "AWS_Global", "url": "https://aws.amazon.com/blogs/aws/feed/"}
        ]
        
        # 브라우저 위장 헤더 (AAS 패턴)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        }

    async def fetch_rss(self, source):
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=25.0) as client:
                response = await client.get(source["url"])
                if response.status_code != 200: return []
                
                feed = feedparser.parse(response.text)
                articles = []
                for entry in feed.entries[:10]:
                    articles.append({
                        "title": entry.title,
                        "link": entry.link,
                        "description": entry.get("summary", entry.get("description", "")),
                        "source": source["name"]
                    })
                logger.info(f"✅ {source['name']} 수집 성공")
                return articles
        except Exception as e:
            logger.error(f"❌ {source['name']} 에러: {e}")
            return []

    async def collect_all(self):
        tasks = [self.fetch_rss(s) for s in self.sources]
        results = await asyncio.gather(*tasks)
        all_articles = [item for sublist in results for item in sublist]
        return all_articles