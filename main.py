import sys, argparse, logging, asyncio, re
from src.collector import NewsCollector
from src.analyzer import NewsAnalyzer
from src.notifier import TelegramNotifier
from src.utils import StateManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# [최적화] AI 분석 가치 없는 키워드들
BLACKLIST = [r"채용", r"모집", r"이벤트", r"할인", r"특가", r"웨비나", r"공고"]

class NewsSystem:
    def __init__(self):
        self.state = StateManager()
        self.analyzer = NewsAnalyzer(state_manager=self.state)
        self.collector = NewsCollector()
        self.notifier = TelegramNotifier()

    async def run(self, mode: str):
        logger.info(f"🚀 가동 모드: {mode}")
        
        # 1. 사용자 피드백 학습 (DB 캐시 활용)
        self.analyzer.learn_user_feedback()

        # 2. 뉴스 수집 및 1차 필터링
        # main.py 내 run 메서드 일부 수정
    async def run(self, mode: str):
        logger.info(f"🚀 가동 모드: {mode}")
        self.analyzer.learn_user_feedback()

        articles = await self.collector.collect_all()
        filtered = []
        for a in articles:
            if self.state.is_already_sent(a['link']): continue
            if any(re.search(p, a['title']) for p in BLACKLIST): continue
            filtered.append(a)
            
            # [운영자 설정] 1회 실행 당 최대 처리량을 20개로 제한 (API Quota 방어)
            if len(filtered) >= 20: 
                logger.info("⚠️ 부하 방지를 위해 상위 20개 기사만 선별 분석합니다.")
                break 

        if not filtered: 
            return logger.info("✅ 새로 분석할 신규 뉴스가 없습니다.")

        # 3. AI 스코어링 (제한된 20개에 대해서만 수행)
        scored = self.analyzer.score_articles(filtered)
        
        # 생존 모드 체크 및 발송 로직 동일...
        
        # [비판적 방어] 스코어링 중 생존 모드(AI 소진)가 발동되었는지 체크
        is_survival = any("생존 모드" in a.get('reason', '') for a in scored)

        # 7점 이상 우선, 없으면 4점 이상 차선책 선정
        candidates = [a for a in scored if a['score'] >= 7] or [a for a in scored if a['score'] >= 4]
        high_priority = sorted(candidates, key=lambda x: x['score'], reverse=True)[:3]

        for a in high_priority:
            # [토큰 효율화] 이미 엔진이 소진된 상태라면 상세 분석 AI 호출을 건너뜁니다.
            if is_survival:
                analysis = "📌 AI 엔진 소진으로 인해 상세 분석을 생략합니다. 원문 링크를 확인해주세요."
            else:
                analysis = self.analyzer.analyze_article(a)
            
            header = f"<b>[AI 평점: {a['score']}점]</b>\n<i>💡 {a.get('reason', 'N/A')}</i>"
            
            # 발송 및 상태 업데이트
            if self.notifier.send_report(f"{header}\n\n{analysis}", a['link']):
                self.state.add_article(a)
                logger.info(f"📤 발송 완료: {a['title'][:20]}...")
                # 텔레그램 도마뱀(Flood) 방지를 위해 5초 대기
                await asyncio.sleep(5)
        
        # 4. 오래된 데이터 정리 (DB 관리)
        self.state.clean_old_state()
        logger.info("🏁 모든 프로세스가 정상 종료되었습니다.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["regular", "summary"], default="regular")
    asyncio.run(NewsSystem().run(parser.parse_args().mode))