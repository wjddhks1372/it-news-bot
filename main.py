import sys, argparse, logging, asyncio, re
from src.collector import NewsCollector
from src.analyzer import NewsAnalyzer
from src.notifier import TelegramNotifier
from src.utils import StateManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BLACKLIST = [r"채용", r"모집", r"이벤트", r"할인", r"특가", r"웨비나", r"공고", r"수강생"]

class NewsSystem:
    def __init__(self):
        self.state = StateManager()
        self.analyzer = NewsAnalyzer(state_manager=self.state)
        self.collector = NewsCollector()
        self.notifier = TelegramNotifier()

    async def run(self, mode: str):
        logger.info(f"🚀 [운영] {mode} 모드 가동")
        self.analyzer.learn_user_feedback()

        # 1. 수집 및 필터링
        articles = await self.collector.collect_all()
        filtered = []
        for a in articles:
            if self.state.is_already_sent(a['link']): continue
            if any(re.search(p, a['title']) for p in BLACKLIST): continue
            filtered.append(a)
            if len(filtered) >= 15: break 

        if not filtered: 
            return logger.info("✅ 처리할 신규 뉴스가 없습니다.")

        # 2. AI 스코어링
        scored = await self.analyzer.score_articles(filtered)
        
        # 3. [Regular 모드] Top 3 상세 분석 발송
        if mode == "regular":
            high_priority = sorted(scored, key=lambda x: x['score'], reverse=True)[:3]
            for a in high_priority:
                analysis = await self.analyzer.analyze_article(a)
                header = f"<b>[AI 평점: {a['score']}점]</b>\n<i>💡 {a.get('reason', 'N/A')}</i>"
                if self.notifier.send_report(f"{header}\n\n{analysis}", a['link']):
                    self.state.add_article(a)
                    logger.info(f"📤 상세 발송: {a['title'][:20]}...")
                    await asyncio.sleep(5)

        # 4. [공통] 통합 보고서 발송 (마지막 요약)
        logger.info("📊 통합 보고서 생성 중...")
        final_report = await self.analyzer.generate_final_summary(scored)
        self.notifier.send_report(final_report, "https://github.com/wjddhks1372/it-news-bot")
        
        logger.info("🏁 운영 프로세스 정상 종료")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["regular", "summary"], default="regular")
    asyncio.run(NewsSystem().run(parser.parse_args().mode))