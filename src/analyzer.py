import google.generativeai as genai
import logging, os, asyncio, re

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self, state_manager):
        self.state = state_manager
        self.api_keys = [k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",") if k.strip()]
        self.current_key_idx = 0
        self.user_persona = ""
        self._init_client()

    def _init_client(self):
        genai.configure(api_key=self.api_keys[self.current_key_idx % len(self.api_keys)])
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def learn_user_feedback(self):
        try:
            pref = self.state.db.table("user_preferences").select("*").eq("persona_type", "main").execute()
            if pref.data:
                self.user_persona = pref.data[0].get("description", "")
                logger.info("♻️ 사용자 취향 로드 성공")
        except Exception as e:
            logger.error(f"❌ 취향 로드 실패: {e}")

    async def _call_ai_engines(self, prompt: str) -> str:
        attempt = 0
        while attempt < len(self.api_keys):
            try:
                # [운영 핵심] RPM(분당 15회) 제한을 위해 5초 강제 대기
                await asyncio.sleep(5) 
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                if "429" in str(e):
                    attempt += 1
                    logger.warning(f"⚠️ 엔진 {attempt}차 소진. 교체...")
                    self.current_key_idx += 1
                    self._init_client()
                    await asyncio.sleep(10)
                else:
                    break
        return None

    async def score_articles(self, articles: list) -> list:
        scored_articles = []
        for a in articles:
            prompt = f"취향: {self.user_persona}\n제목: {a['title']}\n가치 평가 1-10점 및 이유 한 줄."
            result = await self._call_ai_engines(prompt)
            if result:
                nums = re.findall(r'\d+', result)
                score = int(nums[0]) if nums else 5
                scored_articles.append({**a, "score": score, "reason": result[:60]})
            else:
                scored_articles.append({**a, "score": 4, "reason": "생존 모드: 자동 선정"})
        return scored_articles

    async def analyze_article(self, article: dict) -> str:
        is_global = article['source'] in ["HackerNews", "TechCrunch", "TheVerge", "AWS_Global"]
        prompt = f"IT 전문가로서 기사 분석 및 한국어 번역 요약:\n{article['title']}\n{article.get('description', '')[:500]}"
        analysis = await self._call_ai_engines(prompt)
        return analysis or "📌 상세 분석 생략 (엔진 소진)"