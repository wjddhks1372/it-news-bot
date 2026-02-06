import sys, argparse, logging, asyncio, re
from src.collector import NewsCollector
from src.analyzer import NewsAnalyzer
from src.notifier import TelegramNotifier
from src.utils import StateManager

# 운영자 관점의 로그 포맷: 시각과 에러 레벨 위주로 표기
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 분석 제외 키워드 (운영 효율화)
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

        # 1. 뉴스 데이터 수집
        articles = await self.collector.collect_all()
        filtered = []
        
        for a in articles:
            # 중복 체크 (DB 조회)
            if self.state.is_already_sent(a['link']): continue
            # 키워드 필터링
            if any(re.search(p, a['title']) for p in BLACKLIST): continue
            
            filtered.append(a)
            
            # [운영 정책] 1회 실행 시 최대 20개만 처리 (API 할당량 보호 전략)
            if len(filtered) >= 10: 
                logger.info("⚠️ 시스템 부하 방지를 위해 최신 20개 기사로 제한합니다.")
                break 

        if not filtered: 
            return logger.info("✅ 처리할 신규 뉴스가 없습니다.")

        # 2. AI 스코어링 (4단 엔진 가동)
        scored = self.analyzer.score_articles(filtered)
        
        # 스코어링 단계에서 이미 429 에러(생존 모드)가 났는지 확인
        is_survival = any("생존 모드" in a.get('reason', '') for a in scored)

        # 3. 고득점 기사 선별 (최상위 3개)
        candidates = [a for a in scored if a['score'] >= 7] or [a for a in scored if a['score'] >= 4]
        high_priority = sorted(candidates, key=lambda x: x['score'], reverse=True)[:3]

        for a in high_priority:
            # [운영 최적화] 이미 엔진이 소진되었다면 상세 분석(AI)을 호출하지 않고 원문 링크만 발송
            if is_survival:
                analysis = "📌 AI 엔진 소진으로 상세 분석을 생략합니다. 링크를 참조하세요."
            else:
                analysis = self.analyzer.analyze_article(a)
            
            header = f"<b>[AI 평점: {a['score']}점]</b>\n<i>💡 {a.get('reason', 'N/A')}</i>"
            
            # 발송 품질 관리 (5초 간격 유지)
            if self.notifier.send_report(f"{header}\n\n{analysis}", a['link']):
                self.state.add_article(a)
                logger.info(f"📤 발송 완료: {a['title'][:20]}...")
                await asyncio.sleep(5) 
        
        self.state.clean_old_state()
        logger.info("🏁 운영 프로세스 정상 종료")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["regular", "summary"], default="regular")
    asyncio.run(NewsSystem().run(parser.parse_args().mode))