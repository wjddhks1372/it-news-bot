import logging, re
from google import genai
from config.settings import settings
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self, state_manager=None):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # 할당량이 더 안정적인 1.5-flash로 변경
        self.model_id = "gemini-1.5-flash" 
        self.state = state_manager
        self.pref_cache = "IT 기술 트렌드"
        self.dislike_cache = "단순 홍보성 뉴스"

    def learn_user_feedback(self):
        """취향 데이터를 로드하되 에러 발생 시 기본값 유지"""
        try:
            cached = self.state.get_user_persona()
            if cached:
                self.pref_cache = cached.get('preference_summary', self.pref_cache)
                self.dislike_cache = cached.get('dislike_summary', self.dislike_cache)
                logger.info("♻️ 취향 캐시 로드 성공")
            else:
                # 테이블이 없거나 데이터가 없을 때 새로 학습 시도
                self._run_learning()
        except Exception as e:
            logger.warning(f"⚠️ 취향 로드 실패 (기본값 사용): {e}")

    def _run_learning(self):
        try:
            likes = self.state.client.table("news_articles").select("title,reason").eq("feedback", "up").limit(10).execute().data
            dislikes = self.state.client.table("news_articles").select("title,reason").eq("feedback", "down").limit(10).execute().data
            if not likes and not dislikes: return

            prompt = f"좋아요: {likes}\n싫어요: {dislikes}\n이 사용자의 취향을 PREF: , DISLIKE: 형식으로 요약하세요."
            res = self.client.models.generate_content(model=self.model_id, contents=prompt).text
            
            self.pref_cache = re.search(r"PREF:\s*(.*)", res).group(1) if "PREF:" in res else self.pref_cache
            self.dislike_cache = re.search(r"DISLIKE:\s*(.*)", res).group(1) if "DISLIKE:" in res else self.dislike_cache
            self.state.save_user_persona(self.pref_cache, self.dislike_cache)
        except:
            logger.error("❌ 실시간 학습 실패")

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(30))
    def score_articles(self, articles: list) -> list:
        if not articles: return []
        headlines = "\n".join([f"[{i}] {a['title']}" for i, a in enumerate(articles)])
        prompt = f"선호: {self.pref_cache}\n기피: {self.dislike_cache}\n헤드라인 평가 [점수: 근거]:\n{headlines}"
        
        try:
            response = self.client.models.generate_content(model=self.model_id, contents=prompt)
            matches = re.findall(r"\[(\d+):\s*(.*?)\]", response.text)
            for i, a in enumerate(articles):
                if i < len(matches):
                    a['score'], a['reason'] = int(matches[i][0]), matches[i][1]
                else:
                    a['score'], a['reason'] = 1, "평가 누락"
            return articles
        except Exception as e:
            logger.warning("⚠️ API 제한, 재시도 중...")
            raise e

    def analyze_article(self, article: dict) -> str:
        prompt = f"기사 분석 (볼드와 불릿만 사용, 이탤릭 금지): {article['title']}"
        try:
            res = self.client.models.generate_content(model=self.model_id, contents=prompt).text
            return res.replace('_', '').replace('* ', '• ')
        except: return "분석 장애 발생"