import httpx
import feedparser
import logging
import asyncio

logger = logging.getLogger(__name__)

class NewsCollector:
    def __init__(self):
        self.sources = [
            {"name": "Toss_Tech", "url": "https://toss.tech/rss.xml"},
            {"name": "Karrot_Tech", "url": "https://medium.com/feed/daangn"},
            {"name": "Naver_D2", "url": "https://d2.naver.com/d2.atom"},
            {"name": "Kakao_Tech", "url": "https://tech.kakao.com/feed/"},
            {"name": "Line_Eng", "url": "https://techblog.lycorp.co.jp/ko/feed/index.xml"},
            {"name": "Woowahan", "url": "https://techblog.woowahan.com/feed/"}, # 403 타겟
            {"name": "AWS_News", "url": "https://aws.amazon.com/ko/blogs/aws/feed/"},
            {"name": "HackerNews", "url": "https://news.ycombinator.com/rss"},
            {"name": "Unity_Blog", "url": "https://unity.com/kr/blog/rss"}
        ]
        
        # [운영자 패치] 정교한 브라우저 위장 헤더
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "max-age=0",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }

    async def fetch_rss(self, source):
        try:
            # 403 에러 방지를 위해 타임아웃과 리디렉션 설정을 강화함
            async with httpx.AsyncClient(
                headers=self.headers, 
                follow_redirects=True, 
                timeout=30.0,
                verify=False # SSL 인증서 문제가 있을 경우 대비 (운영적 선택)
            ) as client:
                response = await client.get(source["url"])
                
                if response.status_code != 200:
                    logger.error(f"❌ {source['name']} 응답 에러: {response.status_code}")
                    return []
                
                feed = feedparser.parse(response.text)
                articles = []
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
            logger.error(f"❌ {source['name']} 예외 발생: {e}")
            return []

    async def collect_all(self):
        tasks = [self.fetch_rss(s) for s in self.sources]
        results = await asyncio.gather(*tasks)
        
        all_articles = []
        for res in results:
            all_articles.extend(res)
            
        logger.info(f"🚀 전체 수집 완료: 총 {len(all_articles)}건")
        return all_articles