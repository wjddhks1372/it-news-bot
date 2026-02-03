import sys
import argparse
import logging
import asyncio
from src.collector import NewsCollector
from src.analyzer import NewsAnalyzer
from src.notifier import TelegramNotifier
from src.utils import StateManager
from config.settings import settings

# 로깅 설정 (Settings의 포맷 활용)
logging.basicConfig(level=logging.INFO, format=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)

class NewsSystem:
    def __init__(self):
        # 1. StateManager를 가장 먼저 초기화 (DB 연결)
        self.state = StateManager()
        # 2. Analyzer에 StateManager 주입 (피드백 학습을 위함)
        self.analyzer = NewsAnalyzer(state_manager=self.state)
        self.collector = NewsCollector()
        self.notifier = TelegramNotifier()

    async def run(self, mode: str):
        logger.info(f"🚀 시스템 가동: {mode} 모드")
        
        # [핵심] 뉴스 수집 전, DB에서 최신 '좋아요' 데이터를 읽어와 취향 요약 업데이트
        self.analyzer.update_user_preference()

        # 1. 뉴스 수집
        articles = await self.collector.collect_all()
        
        # 2. 중복 체크 (DB 기반)
        new_articles = [a for a in articles if not self.state.is_already_sent(a['link'])]
        
        if not new_articles:
            logger.info("✅ 새로운 뉴스가 없습니다. 시스템을 종료합니다.")
            return

        # 3. AI 1차 스코어링 (취향 가산점 반영)
        scored = self.analyzer.score_articles(new_articles)
        
        # 4. 모드별 발송 로직
        if mode == "regular":
            # 7점 이상 고득점 기사만 추출하여 점수순 정렬 (상위 3개 제한)
            high_priority = sorted(
                [a for a in scored if a['score'] >= 7], 
                key=lambda x: x['score'], 
                reverse=True
            )[:3]

            for a in high_priority:
                # 개별 기사 심층 분석 (가독성/이탤릭체 차단 로직 포함)
                analysis = self.analyzer.analyze_article(a)
                
                if "엔진 일시 장애" not in analysis:
                    # 헤더 구성 (AI 점수 및 간략 근거)
                    header = f"<b>[AI 평점: {a['score']}점]</b>\n<i>💡 {a.get('reason', 'N/A')}</i>"
                    full_message = f"{header}\n\n{analysis}"
                    
                    # 텔레그램 발송
                    success = self.notifier.send_report(full_message, a['link'])
                    
                    # 발송 성공 시에만 DB에 기록 (중복 발송 방지)
                    if success:
                        self.state.add_article(a)
                        # 텔레그램 429(Too Many Requests) 방지를 위한 짧은 대기
                        await asyncio.sleep(5) 

        elif mode == "summary":
            # 4~6점 사이의 기사들을 모아 종합 요약
            mid_priority = [a for a in scored if 4 <= a['score'] < 7]
            if mid_priority:
                summary = self.analyzer.analyze_daily_summary(mid_priority)
                success = self.notifier.send_combined_summary(summary)
                
                # 요약본에 포함된 기사들도 발송 완료 처리
                if success:
                    for a in mid_priority:
                        self.state.add_article(a)
            else:
                logger.info("요약할 중간 우선순위 기사가 없습니다.")

        # 5. 30일 이상 된 오래된 로그 정리
        self.state.clean_old_state()
        logger.info("🏁 모든 작업이 완료되었습니다.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["regular", "summary"], default="regular")
    args = parser.parse_args()
    
    try:
        system = NewsSystem()
        asyncio.run(system.run(args.mode))
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"❌ 치명적 시스템 오류: {e}")
        sys.exit(1)