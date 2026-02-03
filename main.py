import sys, argparse, logging, asyncio
from src.collector import NewsCollector
from src.analyzer import NewsAnalyzer
from src.notifier import TelegramNotifier
from src.utils import StateManager
from config.settings import settings

logging.basicConfig(level=logging.INFO, format=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)

class NewsSystem:
    def __init__(self):
        self.state = StateManager()
        self.analyzer = NewsAnalyzer(state_manager=self.state)
        self.collector = NewsCollector()
        self.notifier = TelegramNotifier()

    async def run(self, mode: str):
        logger.info(f"🚀 시스템 가동: {mode} 모드")
        self.analyzer.update_user_preference()

        # 1. 뉴스 수집 및 개수 제한 (API 할당량 방어: 최대 30개)
        articles = await self.collector.collect_all()
        new_articles = [a for a in articles if not self.state.is_already_sent(a['link'])][:30]
        
        if not new_articles:
            logger.info("✅ 새로운 뉴스가 없습니다.")
            return

        # 2. AI 스코어링 (Retry 로직 포함)
        scored = self.analyzer.score_articles(new_articles)
        
        if mode == "regular":
            # 7점 이상을 찾되, 없으면 4점 이상의 상위 3개라도 발송 (시스템 침묵 방지)
            candidates = [a for a in scored if a['score'] >= 7]
            if not candidates:
                logger.info("7점 이상 기사가 없어 차선책(4점+)을 탐색합니다.")
                candidates = [a for a in scored if a['score'] >= 4]

            high_priority = sorted(candidates, key=lambda x: x['score'], reverse=True)[:3]

            for a in high_priority:
                analysis = self.analyzer.analyze_article(a)
                if "장애" not in analysis:
                    header = f"<b>[AI 평점: {a['score']}점]</b>\n<i>💡 {a.get('reason', 'N/A')}</i>"
                    if self.notifier.send_report(f"{header}\n\n{analysis}", a['link']):
                        self.state.add_article(a)
                        await asyncio.sleep(5) 

        elif mode == "summary":
            mid_priority = [a for a in scored if 4 <= a['score'] < 7]
            if mid_priority:
                summary = self.analyzer.analyze_daily_summary(mid_priority)
                if self.notifier.send_combined_summary(summary):
                    for a in mid_priority: self.state.add_article(a)

        self.state.clean_old_state()
        logger.info("🏁 작업 완료")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["regular", "summary"], default="regular")
    args = parser.parse_args()
    try:
        asyncio.run(NewsSystem().run(args.mode))
    except Exception as e:
        logger.error(f"❌ 오류: {e}")
        sys.exit(1)