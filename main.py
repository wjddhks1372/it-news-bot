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

        articles = await self.collector.collect_all()
        filtered = []
        
        for a in articles:
            if self.state.is_already_sent(a['link']): continue
            if any(re.search(p, a['title']) for p in BLACKLIST): continue
            filtered.append(a)
            if len(filtered) >= 5: # 운영 안정성을 위해 5개로 제한
                logger.info("⚠️ API Quota 방어를 위해 상위 5개 기사만 선별합니다.")
                break 

        if not filtered: 
            return logger.info("✅ 처리할 신규 뉴스가 없습니다.")

        # [수정] 비동기 함수이므로 await 필수
        scored = await self.analyzer.score_articles(filtered)
        
        is_survival = any("생존 모드" in a.get('reason', '') for a in scored)
        candidates = [a for a in scored if a['score'] >= 7] or [a for a in scored if a['score'] >= 4]
        high_priority = sorted(candidates, key=lambda x: x['score'], reverse=True)[:3]

        for a in high_priority:
            if is_survival:
                analysis = "📌 AI 엔진 소진으로 상세 분석을 생략합니다. 링크를 참조하세요."
            else:
                # [수정] 비동기 함수이므로 await 필수
                analysis = await self.analyzer.analyze_article(a)
            
            header = f"<b>[AI 평점: {a['score']}점]</b>\n<i>💡 {a.get('reason', 'N/A')}</i>"
            
            if self.notifier.send_report(f"{header}\n\n{analysis}", a['link']):
                self.state.add_article(a)
                logger.info(f"📤 발송 완료: {a['title'][:20]}...")
                await asyncio.sleep(5) 
        
        logger.info("🏁 운영 프로세스 정상 종료")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["regular", "summary"], default="regular")
    asyncio.run(NewsSystem().run(parser.parse_args().mode))