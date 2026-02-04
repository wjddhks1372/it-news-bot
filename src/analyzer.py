import logging, re
from google import genai
from config.settings import settings

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self, state_manager=None):
        self.keys = settings.GEMINI_API_KEYS
        self.current_index = 0
        self.state = state_manager
        self._init_client()
        self.pref_cache = "IT 기술"
        self.dislike_cache = "광고"

    def _init_client(self):
        """현재 인덱스의 키로 엔진을 초기화합니다."""
        if not self.keys: raise ValueError("API 키가 없습니다.")
        key = self.keys[self.current_index]
        self.client = genai.Client(api_key=key, http_options={'api_version': 'v1'})
        logger.info(f"🔄 {self.current_index + 1}번 AI 엔진 가동 중...")

    def _rotate_engine(self):
        """다음 키로 교체합니다. 성공 시 True, 소진 시 False."""
        if self.current_index < len(self.keys) - 1:
            self.current_index += 1
            self._init_client()
            return True
        return False

    def learn_user_feedback(self):
        try:
            cached = self.state.get_user_persona()
            if cached:
                self.pref_cache = cached.get('preference_summary', self.pref_cache)
                self.dislike_cache = cached.get('dislike_summary', self.dislike_cache)
                logger.info("♻️ 취향 캐시 로드 성공")
        except: pass

    def score_articles(self, articles: list) -> list:
        prompt = f"취향: {self.pref_cache}\n기사 평가 (1-10점):\n" + "\n".join([f"[{i}] {a['title']}" for i, a in enumerate(articles)])
        
        # 쿼드 엔진(4개 키) 순회
        for _ in range(len(self.keys)):
            try:
                res = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                matches = re.findall(r"\[(\d+):\s*(.*?)\]", res.text)
                for i, a in enumerate(articles):
                    if i < len(matches):
                        a['score'], a['reason'] = int(matches[i][0]), matches[i][1]
                return articles
            except Exception as e:
                if "429" in str(e) and self._rotate_engine():
                    continue
                break
        
        # 모든 키 실패 시 생존 모드
        logger.warning("🛡️ 모든 AI 엔진 소진. 생존 모드 발동.")
        for a in articles:
            a['score'] = 8 if any(k in a['title'].upper() for k in ["토스", "당근", "K8S"]) else 5
            a['reason'] = "키워드 기반 자동 선정"
        return articles

    def analyze_article(self, article: dict) -> str:
        """기사 분석 시에도 엔진 로테이션 적용"""
        for _ in range(len(self.keys)):
            try:
                res = self.client.models.generate_content(model="gemini-2.0-flash", contents=f"요약: {article['title']}")
                return res.text.replace('_', '').replace('* ', '• ')
            except:
                if self._rotate_engine(): continue
                return "상세 분석 생략 (엔진 소진)"