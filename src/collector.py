import httpx, feedparser, logging, asyncio
logger = logging.getLogger(__name__)

class NewsCollector:
    def __init__(self):
        self.sources = [
            {"name": "Karrot_Tech", "url": "https://medium.com/feed/daangn"},
            {"name": "Toss_Tech", "url": "https://toss.tech/rss.xml"},
            {"name": "AWS_News", "url": "https://aws.amazon.com/ko/blogs/aws/feed/"},
            {"name": "HackerNews", "url": "https://news.ycombinator.com/rss"},
            {"name": "Unity_Blog", "url": "https://unity.com/kr/blog/rss"}
        ]

    async def fetch_rss(self, source):
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                res = await client.get(source["url"])
                feed = feedparser.parse(res.text)
                return [{"title": e.title, "link": e.link, "description": e.get("summary", ""), "source": source["name"]} for e in feed.entries[:15]]
        except: return []

    async def collect_all(self):
        priority = ["Toss_Tech", "Karrot_Tech"]
        p_sources = [s for s in self.sources if s["name"] in priority]
        o_sources = [s for s in self.sources if s["name"] not in priority]
        
        p_res = await asyncio.gather(*[self.fetch_rss(s) for s in p_sources])
        o_res = await asyncio.gather(*[self.fetch_rss(s) for s in o_sources])
        
        results = []
        for r in p_res: results.extend(r)
        for r in o_res: results.extend(r)
        return results