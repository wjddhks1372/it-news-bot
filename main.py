import sys, argparse, logging, asyncio, re
from src.collector import NewsCollector
from src.analyzer import NewsAnalyzer
from src.notifier import TelegramNotifier
from src.utils import StateManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

BLACKLIST = [r"채용", r"모집", r"이벤트", r"할인", r"특가"]

class NewsSystem:
    def __init__(self):
        self.state = StateManager()
        self.analyzer = NewsAnalyzer(state_manager=self.state)
        self.collector = NewsCollector()
        self.notifier = TelegramNotifier()

    async def run(self, mode: str):
        logger.info(f"🚀 모드: {mode}")
        self.analyzer.learn_user_feedback()

        articles = await self.collector.collect_all()
        filtered = []
        for a in articles:
            if self.state.is_already_sent(a['link']): continue
            if any(re.search(p, a['title']) for p in BLACKLIST): continue
            filtered.append(a)
            if len(filtered) >= 30: break # API 보호

        if not filtered: return logger.info("✅ 신규 없음")

        scored = self.analyzer.score_articles(filtered)
        candidates = [a for a in scored if a['score'] >= 7] or [a for a in scored if a['score'] >= 4]
        high_priority = sorted(candidates, key=lambda x: x['score'], reverse=True)[:3]

        for a in high_priority:
            analysis = self.analyzer.analyze_article(a)
            header = f"<b>[AI 평점: {a['score']}점]</b>\n<i>💡 {a.get('reason', 'N/A')}</i>"
            if self.notifier.send_report(f"{header}\n\n{analysis}", a['link']):
                self.state.add_article(a)
                await asyncio.sleep(5)
        
        self.state.clean_old_state()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["regular", "summary"], default="regular")
    asyncio.run(NewsSystem().run(parser.parse_args().mode))