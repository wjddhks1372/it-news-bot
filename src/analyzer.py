import logging, re
from google import genai
from config.settings import settings
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self, state_manager=None):
        # 2026년 표준인 v1 API를 사용하도록 설정
        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options={'api_version': 'v1'} 
        )
        # 가장 안정적인 2.0 정식 모델로 고정
        self.model_id = "gemini-2.0-flash" 
        self.state = state_manager
        self.pref_cache = "IT 기술 및 DevOps 트렌드"
        self.dislike_cache = "단순 광고 및 채용 공고"

    def learn_user_feedback(self):
        """DB에서 취향 데이터를 로드합니다."""
        try:
            cached = self.state.get_user_persona()
            if cached:
                self.pref_cache = cached.get('preference_summary', self.pref_cache)
                self.dislike_cache = cached.get('dislike_summary', self.dislike_cache)
                logger.info("♻️ 취향 캐시 로드 성공")
        except Exception as e:
            logger.warning(f"⚠️ 취향 데이터 읽기 실패 (기본값 사용): {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(30))
    def score_articles(self, articles: list) -> list:
        if not articles: return []
        
        headlines = "\n".join([f"[{i}] {a['title']}" for i, a in enumerate(articles)])
        prompt = f"""
        당신은 시니어 엔지니어입니다. 다음 IT 뉴스를 1-10점으로 평가하세요.
        선호 기준: {self.pref_cache}
        기피 기준: {self.dislike_cache}
        형식: [점수: 근거]
        
        뉴스크롤링 목록:
        {headlines}
        """
        
        try:
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
            # 404가 나더라도 절대 죽지 않고 1.5 모델로 마지막 시도
            if "404" in str(e):
                logger.warning("⚠️ 모델명 불일치 감지, 대체 모델(1.5-flash) 시도")
                self.model_id = "gemini-1.5-flash"
            raise e

    def analyze_article(self, article: dict) -> str:
        prompt = f"다음 기사를 분석하여 보고서로 작성 (이탤릭 금지, 볼드와 • 사용):\n{article['title']}"
        try:
            res = self.client.models.generate_content(model=self.model_id, contents=prompt).text
            return res.replace('_', '').replace('* ', '• ')
        except:
            return "상세 분석 일시 장애 (원문 링크를 참조하세요)"

    def analyze_daily_summary(self, articles: list) -> str:
        content = "\n".join([f"- {a['title']}" for a in articles])
        try:
            res = self.client.models.generate_content(model=self.model_id, contents=f"요약:\n{content}").text
            return res.replace('_', '')
        except:
            return "요약본 생성 실패"