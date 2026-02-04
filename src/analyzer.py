import logging, re
from google import genai
from config.settings import settings
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self, state_manager=None):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # 가장 표준적인 모델 명칭으로 수정
        self.model_id = "gemini-1.5-flash" 
        self.state = state_manager
        self.pref_cache = "IT 기술 트렌드"
        self.dislike_cache = "단순 홍보성 뉴스"

    def learn_user_feedback(self):
        """취향 데이터를 로드합니다."""
        try:
            cached = self.state.get_user_persona()
            if cached:
                self.pref_cache = cached.get('preference_summary', self.pref_cache)
                self.dislike_cache = cached.get('dislike_summary', self.dislike_cache)
                logger.info("♻️ 취향 캐시 로드 성공")
        except Exception as e:
            logger.warning(f"⚠️ 취향 로드 실패: {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(30))
    def score_articles(self, articles: list) -> list:
        if not articles: return []
        headlines = "\n".join([f"[{i}] {a['title']}" for i, a in enumerate(articles)])
        prompt = f"다음 뉴스를 평가하세요 [점수: 근거]:\n{headlines}"
        
        try:
            # 모델 호출 시 명칭을 명확히 전달
            response = self.client.models.generate_content(
                model=self.model_id, 
                contents=prompt
            )
            matches = re.findall(r"\[(\d+):\s*(.*?)\]", response.text)
            for i, a in enumerate(articles):
                if i < len(matches):
                    a['score'], a['reason'] = int(matches[i][0]), matches[i][1]
                else:
                    a['score'], a['reason'] = 1, "평가 누락"
            return articles
        except Exception as e:
            # 404 에러 발생 시 2.0 모델로 즉시 스위칭 시도 (비판적 방어 로직)
            if "404" in str(e):
                logger.warning("⚠️ 1.5 모델을 찾을 수 없어 2.0 모델로 전환합니다.")
                self.model_id = "gemini-2.0-flash-exp"
            raise e

    def analyze_article(self, article: dict) -> str:
        prompt = f"기사 분석 (이탤릭 금지): {article['title']}"
        try:
            res = self.client.models.generate_content(model=self.model_id, contents=prompt).text
            return res.replace('_', '').replace('* ', '• ')
        except: return "분석 장애"

    def analyze_daily_summary(self, articles: list) -> str:
        content = "\n".join([f"- {a['title']}" for a in articles])
        try:
            res = self.client.models.generate_content(model=self.model_id, contents=f"요약:\n{content}").text
            return res.replace('_', '')
        except: return "요약 실패"