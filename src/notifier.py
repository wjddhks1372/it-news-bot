import requests
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

# 반드시 클래스 이름이 main.py에서 부르는 이름과 같아야 합니다.
class TelegramNotifier:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def _send(self, text: str):
        try:
            payload = {
                "chat_id": str(self.chat_id).strip(),
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            response = requests.post(self.api_url, json=payload)
            if response.status_code != 200:
                logger.error(f"텔레그램 응답 에러: {response.text}")
            response.raise_for_status()
        except Exception as e:
            logger.error(f"텔레그램 전송 실패: {e}")

    def send_urgent_alert(self, article: dict, analysis: str = None):
        content = analysis if analysis else "핵심 키워드 긴급 소식입니다."
        message = (
            f"🚨 <b>[긴급 기술 알림]</b>\n\n"
            f"📌 <b>제목:</b> {article['title']}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{content}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <a href='{article['link']}'>원문 보기</a>"
        )
        self._send(message)

    def send_report(self, analysis_result: str, source_url: str):
        message = (
            f"📊 <b>정기 IT 기술 분석 보고</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"{analysis_result}\n\n"
            f"🔗 <a href='{source_url}'>원문 링크</a>"
        )
        self._send(message)

    def send_combined_summary(self, summary_text: str):
        message = (
            f"📅 <b>오늘의 IT 기술 종합</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"{summary_text}\n\n"
            f"✅ 오늘 하루도 고생하셨습니다."
        )
        self._send(message)