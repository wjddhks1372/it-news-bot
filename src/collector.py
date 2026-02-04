import httpx
import feedparser
import logging
import asyncio

logger = logging.getLogger(__name__)

class NewsCollector:
    def __init__(self):
        # 국내외 주요 기술 소스 확장 (P0 순위 반영)
        self.sources = [
            # 1순위: 선호 도메인
            {"name": "Toss_Tech", "url": "https://toss.tech/rss.xml"},
            {"name": "Karrot_Tech", "url": "https://medium.com/feed/daangn"},
            {"name": "Naver_D2", "url": "https://d2.naver.com/d2.atom"},
            {"name": "Kakao_Tech", "url": "https://tech.kakao.com/feed/"},
            {"name": "Line_Eng", "url": "https://engineering.linecorp.com/ko/feed/"},
            {"name": "Woowahan", "url": "https://techblog.woowahan.com/feed/"},
            
            # 2순위: 글로벌 및 인프라
            {"name": "AWS_News", "url": "https://aws.amazon.com/ko/blogs/aws/feed/"},
            {"name": "HackerNews", "url": "https://news.ycombinator.com/rss"},
            {"name": "Unity_Blog", "url": "https://unity.com/kr/blog/rss"}
        ]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def fetch_rss(self, source):
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=20.0) as client:
                response = await client.get(source["url"])
                if response.status_code != 200:
                    logger.error(f"❌ {source['name']} 응답 에러: {response.status_code}")
                    return []
                
                feed = feedparser.parse(response.text)
                articles = []
                # 각 소스당 최신 10건씩 수집
                for entry in feed.entries[:10]:
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
        # [우선순위 로직] 선호 도메인을 리스트 앞쪽에 배치
        priority_names = ["Toss_Tech", "Karrot_Tech", "Naver_D2", "Kakao_Tech"]
        p_sources = [s for s in self.sources if s["name"] in priority_names]
        o_sources = [s for s in self.sources if s["name"] not in priority_names]

        # 비동기 병렬 수집
        p_tasks = [self.fetch_rss(s) for s in p_sources]
        o_tasks = [self.fetch_rss(s) for s in o_sources]

        p_results = await asyncio.gather(*p_tasks)
        o_results = await asyncio.gather(*o_tasks)

        all_articles = []
        for res in p_results: all_articles.extend(res)
        for res in o_results: all_articles.extend(res)

        logger.info(f"🚀 전체 수집 완료: 총 {len(all_articles)}건 (우선순위 소스 전방 배치)")
        return all_articles