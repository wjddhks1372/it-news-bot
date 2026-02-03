import logging, re
from google import genai
from config.settings import settings
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self, state_manager=None):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_id = "gemini-2.0-flash-lite"
        self.state = state_manager
        self.pref_cache = ""
        self.dislike_cache = ""

    def learn_user_feedback(self, force=False):
        if not force:
            cached = self.state.get_user_persona()
            if cached and cached.get('preference_summary') != '초기 학습 중...':
                self.pref_cache = cached['preference_summary']
                self.dislike_cache = cached['dislike_summary']
                logger.info("♻️ 캐싱된 취향 데이터를 로드했습니다.")
                return

        try:
            likes = self.state.client.table("news_articles").select("title,reason").eq("feedback", "up").limit(20).execute().data
            dislikes = self.state.client.table("news_articles").select("title,reason").eq("feedback", "down").limit(20).execute().data
            
            prompt = f"사용자 피드백 분석:\n좋아요: {likes}\n싫어요: {dislikes}\nPREF: (요약)\nDISLIKE: (요약)"
            res = self.client.models.generate_content(model=self.model_id, contents=prompt).text
            self.pref_cache = re.search(r"PREF:\s*(.*)", res).group(1) if "PREF:" in res else "IT 기술 심층 분석"
            self.dislike_cache = re.search(r"DISLIKE:\s*(.*)", res).group(1) if "DISLIKE:" in res else "단순 광고"
            self.state.save_user_persona(self.pref_cache, self.dislike_cache)
            logger.info("🎯 피드백 학습 및 DB 저장 완료")
        except Exception as e:
            logger.error(f"학습 실패: {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(60))
    def score_articles(self, articles: list) -> list:
        if not articles: return []
        if not self.pref_cache: self.learn_user_feedback()
        headlines = "\n".join([f"[{i}] {a['title']}" for i, a in enumerate(articles)])
        prompt = f"시니어 엔지니어 관점에서 점수(1-10) 부여.\n선호: {self.pref_cache}\n기피: {self.dislike_cache}\n형식: [점수: 근거]\n{headlines}"
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
            logger.warning(f"⚠️ API 제한 발생, 재시도합니다.")
            raise e

    def analyze_article(self, article: dict) -> str:
        prompt = f"다음 뉴스를 분석 보고서 형식으로 작성. 이탤릭 기호(_, *) 절대 금지. <b>와 • 사용:\n{article['title']}"
        try:
            res = self.client.models.generate_content(model=self.model_id, contents=prompt).text
            return res.replace('_', '').replace('* ', '• ')
        except: return "분석 장애"

    def analyze_daily_summary(self, articles: list) -> str:
        content = "\n".join([f"- {a['title']}" for a in articles])
        prompt = f"기술 트렌드 요약 (이탤릭 금지):\n{content}"
        try:
            res = self.client.models.generate_content(model=self.model_id, contents=prompt).text
            return res.replace('_', '')
        except: return "요약 실패"