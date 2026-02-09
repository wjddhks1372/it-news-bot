import os, logging, asyncio, re
from groq import Groq
import google.generativeai as genai

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self, state_manager):
        self.state = state_manager
        self.gemini_keys = [k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",") if k.strip()]
        self.groq_key = os.getenv("GROQ_API_KEY")
        
        self.user_persona = ""
        self.current_gemini_idx = 0
        self._init_engines()

    def _init_engines(self):
        if self.groq_key:
            self.groq_client = Groq(api_key=self.groq_key)
            logger.info("⚡ Groq 엔진 가동 (Primary)")
        
        if self.gemini_keys:
            genai.configure(api_key=self.gemini_keys[self.current_gemini_idx % len(self.gemini_keys)])
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("🤖 Gemini 엔진 대기 (Secondary)")

    def learn_user_feedback(self):
        try:
            pref = self.state.db.table("user_preferences").select("*").eq("persona_type", "main").execute()
            if pref.data:
                self.user_persona = pref.data[0].get("description", "")
                logger.info("♻️ 사용자 취향 동기화 완료")
        except Exception as e:
            logger.error(f"❌ 취향 로드 실패: {e}")

    async def _call_ai_engines(self, prompt: str, temp: float = 0.2) -> str:
        # [운영] Groq 우선 시도
        if self.groq_key:
            try:
                await asyncio.sleep(1)
                completion = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temp
                )
                return completion.choices[0].message.content
            except Exception as e:
                logger.warning(f"⚠️ Groq 실패, Gemini로 전환: {e}")

        # [운영] Gemini 백업 시도
        try:
            await asyncio.sleep(5)
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(temperature=temp)
            )
            return response.text
        except Exception as e:
            logger.error(f"❌ 모든 엔진 응답 없음: {e}")
            return None

    async def score_articles(self, articles: list) -> list:
        scored = []
        for a in articles:
            prompt = f"취향: {self.user_persona}\n제목: {a['title']}\n이 뉴스의 가치를 1-10점으로 평가하고 이유를 한국어 한 줄로 적어줘."
            result = await self._call_ai_engines(prompt, temp=0.3)
            if result:
                nums = re.findall(r'\d+', result)
                score = int(nums[0]) if nums else 5
                scored.append({**a, "score": score, "reason": result[:100]})
            else:
                scored.append({**a, "score": 4, "reason": "생존 모드: 자동 선정"})
        return scored

    async def analyze_article(self, article: dict) -> str:
        prompt = f"""
        IT 전문가로서 다음 기사를 상세 분석하세요. 반드시 한국어만 사용하세요.
        제목: {article['title']}
        내용: {article.get('description', '')[:800]}

        [응답 형식]
        1. 개발자 관점에서 핵심 요약:
        (기사의 핵심 내용을 3줄 이내로 요약)

        2. 기술의 영향력 분석:
        (이 기술이 업계나 개발 환경에 미칠 영향을 분석)

        3. 논리적인 분석:
        (전문가 시선에서 이 기술의 한계점이나 과제를 비평)
        """
        analysis = await self._call_ai_engines(prompt, temp=0.2)
        return analysis or "📌 상세 분석 생략 (엔진 소진)"

    async def generate_final_summary(self, scored_articles: list) -> str:
        context = "\n".join([f"- {a['title']} ({a['score']}점)" for a in scored_articles])
        prompt = f"""
        당신은 기술 분석가입니다. 아래 뉴스를 종합하여 보고서를 작성하세요. 반드시 한국어만 사용하세요.
        뉴스 목록:
        {context}
        
        [리포트 구성]
        1. 핵심 키워드: #해시태그 형태 3개
        2. 기술 총평: 오늘 IT 흐름 3줄 요약
        3. 🚀 오늘의 추천 액션: 오늘 학습해야 할 기술 개념 1개와 이유
        """
        summary = await self._call_ai_engines(prompt, temp=0.2)
        
        # [운영자 패치] Null 체크로 AttributeError 방지
        if summary is None:
            return "⚠️ 오늘 IT 트렌드 요약 분석에 실패했습니다. (엔진 소진)"

        summary = summary.strip().replace('*', '') 
        return f"📊 **IT TREND INTELLIGENCE**\n━━━━━━━━━━━━━━━━━━━━\n{summary}\n\n📝 분석 대상: {len(scored_articles)}개 기사\n━━━━━━━━━━━━━━━━━━━━"