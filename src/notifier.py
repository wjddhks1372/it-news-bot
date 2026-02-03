import requests
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def _send(self, text: str) -> bool:
        """메시지를 실제 발송하고 성공 여부를 반환합니다."""
        try:
            payload = {
                "chat_id": str(self.chat_id).strip(),
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            response = requests.post(self.api_url, json=payload, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"❌ 텔레그램 응답 에러 ({response.status_code}): {response.text}")
                return False
            
            logger.info("🚀 텔레그램 메시지 발송 성공")
            return True
        except Exception as e:
            logger.error(f"❌ 텔레그램 전송 실패: {e}")
            return False

    def send_report(self, analysis_result: str, source_url: str):
        message = (
            f"📊 <b>정기 IT 기술 분석 보고</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"{analysis_result}\n\n"
            f"🔗 <a href='{source_url}'>원문 링크</a>"
        )
        return self._send(message)

    def send_combined_summary(self, summary_text: str):
        message = (
            f"📅 <b>오늘의 IT 기술 종합</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"{summary_text}\n\n"
            f"✅ 오늘 하루도 고생하셨습니다."
        )
        return self._send(message)