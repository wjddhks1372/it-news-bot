import sys
import argparse
import logging
import time
from src.collector import NewsCollector
from src.analyzer import NewsAnalyzer
from src.notifier import TelegramNotifier
from src.utils import StateManager
from config.settings import settings

# 로깅 설정
logging.basicConfig(level=logging.INFO, format=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)

class NewsSystem:
    def __init__(self):
        self.collector = NewsCollector()
        self.analyzer = NewsAnalyzer()
        self.notifier = TelegramNotifier()
        self.state = StateManager()

    def run(self, mode: str):
        logger.info(f"시스템 가동: {mode} 모드")
        
        # 1. 뉴스 수집
        articles = self.collector.collect_all()
        
        # 2. 중복 제거 (아직 발송하지 않은 기사만 필터링)
        new_articles = [a for a in articles if not self.state.is_already_sent(a['link'])]
        
        if not new_articles:
            logger.info("새로운 뉴스가 없습니다.")
            return

        # 3. 긴급 알림 체크 (키워드 매칭 시 즉시 발송)
        urgent_list = self.collector.filter_by_keywords(new_articles, settings.TARGET_KEYWORDS)
        for urgent in urgent_list:
            # 긴급 알림은 AI 분석 없이 원문 위주로 즉시 보냄 (429 에러 영향 없음)
            self.notifier.send_urgent_alert(urgent)
            self.state.add_article(urgent['link'])
            logger.info(f"긴급 알림 발송 완료: {urgent['title']}")

        # 4. 모드별 동작
        if mode == "regular":
            # 무료 티어 안정성을 위해 한 번 실행 시 최대 3개까지만 분석
            target_articles = new_articles[:3]
            for article in target_articles:
                # 이미 위에서 긴급으로 보낸 기사는 제외
                if self.state.is_already_sent(article['link']):
                    continue

                analysis = self.analyzer.analyze_article(article)
                
                # 분석에 성공했을 때만 리포트 전송 및 상태 업데이트
                if "분석 실패" not in analysis:
                    self.notifier.send_report(analysis, article['link'])
                    self.state.add_article(article['link'])
                    logger.info(f"정기 리포트 발송 완료: {article['title']}")
                    
                    # 429 에러 방지를 위해 기사 간 간격을 10초로 늘림 (실무적 안전 수치)
                    logger.info("Next request in 10 seconds...")
                    time.sleep(10)
                else:
                    logger.warning(f"분석 실패로 인해 발송 건너뜀: {article['title']}")

        elif mode == "summary":
            # 일일 종합 분석
            summary = self.analyzer.analyze_daily_summary(new_articles)
            if "실패" not in summary:
                self.notifier.send_combined_summary(summary)
                # 요약에 포함된 모든 기사를 처리 완료 상태로 기록
                for a in new_articles:
                    self.state.add_article(a['link'])
                logger.info("일일 종합 요약 발송 완료.")

        # 5. 상태 정리 (7일 이상 된 기록 삭제)
        self.state.clean_old_state()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["regular", "summary"], default="regular")
    args = parser.parse_args()

    try:
        system = NewsSystem()
        system.run(args.mode)
    except Exception as e:
        logger.error(f"시스템 실행 중 치명적 오류: {e}")
        sys.exit(1)