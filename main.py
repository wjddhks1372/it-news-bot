import sys, argparse, logging, time, asyncio
from src.collector import NewsCollector
from src.analyzer import NewsAnalyzer
from src.notifier import TelegramNotifier
from src.utils import StateManager
from config.settings import settings

logging.basicConfig(level=logging.INFO, format=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)

class NewsSystem:
    def __init__(self):
        self.collector = NewsCollector()
        self.analyzer = NewsAnalyzer()
        self.notifier = TelegramNotifier()
        self.state = StateManager()

    async def run(self, mode: str):
        logger.info(f"시스템 가동: {mode} 모드")
        articles = await self.collector.collect_all()
        new_articles = [a for a in articles if not self.state.is_already_sent(a['link'])]
        
        if not new_articles:
            logger.info("새로운 뉴스가 없습니다.")
            return

        # 1. AI 스코어링
        scored = self.analyzer.score_articles(new_articles)
        
        if mode == "regular":
            # 7점 이상: 즉시 상세 분석 보고 (최대 3개)
            high_priority = sorted([a for a in scored if a['score'] >= 7], key=lambda x: x['score'], reverse=True)[:3]
            for a in high_priority:
                analysis = self.analyzer.analyze_article(a)
                if "실패" not in analysis:
                    self.notifier.send_report(f"<b>[AI 선정 주요 뉴스 - {a['score']}점]</b>\n{analysis}", a['link'])
                    self.state.add_article(a['link'])
                    await asyncio.sleep(10)

        elif mode == "summary":
            # 4~6점: 저녁 요약 보고
            mid_priority = [a for a in scored if 4 <= a['score'] < 7]
            summary = self.analyzer.analyze_daily_summary(mid_priority)
            self.notifier.send_combined_summary(summary)
            for a in new_articles: # 요약된 기사들도 발송 완료 처리
                self.state.add_article(a['link'])

        self.state.clean_old_state()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["regular", "summary"], default="regular")
    args = parser.parse_args()
    try:
        system = NewsSystem()
        asyncio.run(system.run(args.mode))
    except Exception as e:
        logger.error(f"치명적 오류: {e}")
        sys.exit(1)