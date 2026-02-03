import httpx
import feedparser
import logging
import asyncio

logger = logging.getLogger(__name__)

class NewsCollector:
    def __init__(self):
        self.sources = [
            {"name": "Karrot_Tech", "url": "https://medium.com/feed/daangn"},
            {"name": "Toss_Tech", "url": "https://toss.tech/rss.xml"},
            {"name": "AWS_News", "url": "https://aws.amazon.com/ko/blogs/aws/feed/"},
            {"name": "HackerNews", "url": "https://news.ycombinator.com/rss"},
            {"name": "Unity_Blog", "url": "https://unity.com/kr/blog/rss"},
            {"name": "GeekNews", "url": "https://news.hada.io/rss"},
            {"name": "ITWorld_Korea", "url": "https://www.itworld.co.kr/rss/feed/index.php"}
        ]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def fetch_rss(self, source):
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=15.0) as client:
                response = await client.get(source["url"])
                if response.status_code != 200:
                    logger.error(f"❌ {source['name']} 응답 에러: {response.status_code}")
                    return []
                
                feed = feedparser.parse(response.text)
                articles = []
                for entry in feed.entries[:15]:
                    articles.append({
                        "title": entry.title,
                        "link": entry.link,
                        "description": entry.get("summary", entry.get("description", "")),
                        "source": source["name"]
                    })
                logger.info(f"✅ {source['name']} 수집 성공 ({len(articles)}건)")
                return articles
        except Exception as e:
            logger.error(f"❌ {source['name']} 수집 중 예외 발생: {e}")
            return []

    async def collect_all(self):
        # 1. 우선순위 도메인과 일반 도메인 분리
        priority_names = ["Toss_Tech", "Karrot_Tech"]
        priority_sources = [s for s in self.sources if s["name"] in priority_names]
        other_sources = [s for s in self.sources if s["name"] not in priority_names]

        # 2. 비동기로 수집 실행
        priority_tasks = [self.fetch_rss(s) for s in priority_sources]
        other_tasks = [self.fetch_rss(s) for s in other_sources]

        # 3. 결과 합치기 (우선순위 기사가 리스트 앞쪽에 위치)
        priority_results = await asyncio.gather(*priority_tasks)
        other_results = await asyncio.gather(*other_tasks)

        all_articles = []
        for res in priority_results: all_articles.extend(res)
        for res in other_results: all_articles.extend(res)

        logger.info(f"🚀 전체 수집 완료: 총 {len(all_articles)}건 (우선순위 도메인 우선 배치)")
        return all_articles