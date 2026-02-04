import logging, re
from google import genai
from config.settings import settings
from tenacity import retry, stop_after_attempt, wait_fixed, RetryError

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self, state_manager=None):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY, http_options={'api_version': 'v1'})
        self.model_id = "gemini-2.0-flash" 
        self.state = state_manager
        self.pref_cache = "IT 기술"
        self.dislike_cache = "광고"

    def learn_user_feedback(self):
        try:
            cached = self.state.get_user_persona()
            if cached:
                self.pref_cache = cached.get('preference_summary', self.pref_cache)
                self.dislike_cache = cached.get('dislike_summary', self.dislike_cache)
                logger.info("♻️ 취향 캐시 로드 성공")
        except: pass

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(30))
    def _call_ai_scoring(self, prompt):
        """실제 AI 호출부 (리트라이 적용)"""
        return self.client.models.generate_content(model=self.model_id, contents=prompt)

    def score_articles(self, articles: list) -> list:
        if not articles: return []
        
        headlines = "\n".join([f"[{i}] {a['title']}" for i, a in enumerate(articles)])
        prompt = f"평가 기준: {self.pref_cache}\n목록:\n{headlines}"
        
        try:
            response = self._call_ai_scoring(prompt)
            matches = re.findall(r"\[(\d+):\s*(.*?)\]", response.text)
            for i, a in enumerate(articles):
                if i < len(matches):
                    a['score'], a['reason'] = int(matches[i][0]), matches[i][1]
                else:
                    a['score'], a['reason'] = 1, "AI 응답 누락"
            return articles
        except Exception as e:
            logger.warning(f"⚠️ AI 스코어링 실패(할당량 초과 등): {e}")
            logger.info("🛡️ 생존 모드(룰 기반 스코어링)로 전환합니다.")
            
            # AI가 죽었을 때 작동하는 논리적 필터
            for a in articles:
                # 당신이 선호하는 도메인이나 키워드가 있으면 가산점
                if any(k in a['title'].upper() for k in ["TOSS", "토스", "당근", "KARROT", "K8S", "DEVOPS"]):
                    a['score'], a['reason'] = 8, "선호 키워드 기반 자동 선정 (생존 모드)"
                else:
                    a['score'], a['reason'] = 5, "일반 기사 (생존 모드)"
            return articles

    def analyze_article(self, article: dict) -> str:
        try:
            res = self.client.models.generate_content(model=self.model_id, contents=f"간단 요약: {article['title']}").text
            return res.replace('_', '').replace('* ', '• ')
        except:
            return "상세 분석 생략 (AI 할당량 초과)"