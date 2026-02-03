import requests
import logging
import json
from config.settings import settings

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def _send(self, text: str, callback_url: str = None) -> bool:
        """메시지를 발송하며, url이 제공될 경우 피드백 버튼을 부착합니다."""
        try:
            payload = {
                "chat_id": str(self.chat_id).strip(),
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }

            if callback_url:
                # callback_data 제한(64자)을 고려해 URL 뒷부분 50자만 식별자로 활용
                article_id = callback_url[-50:] 
                keyboard = {
                    "inline_keyboard": [[
                        {"text": "👍 유용함", "callback_data": f"up|{article_id}"},
                        {"text": "👎 별로임", "callback_data": f"down|{article_id}"}
                    ]]
                }
                payload["reply_markup"] = json.dumps(keyboard)

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
        # 개별 리포트 발송 시 버튼 부착
        return self._send(message, callback_url=source_url)

    def send_combined_summary(self, summary_text: str):
        message = (
            f"📅 <b>오늘의 IT 기술 종합</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"{summary_text}\n\n"
            f"✅ 오늘 하루도 고생하셨습니다."
        )
        return self._send(message) # 종합 요약은 버튼 제외 (선택 사항)