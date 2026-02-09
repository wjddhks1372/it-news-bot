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
        """[운영자 패치] Temperature 조절 기능 추가로 답변 일관성 확보"""
        if self.groq_key:
            try:
                await asyncio.sleep(1)
                completion = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temp, # 0.2로 설정하여 환각 및 외국어 혼용 방지
                    top_p=1,
                )
                return completion.choices[0].message.content
            except Exception as e:
                logger.warning(f"⚠️ Groq 실패, Gemini 전환: {e}")

        try:
            await asyncio.sleep(5)
            # Gemini의 경우 generation_config를 통해 온도 조절
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
        """[운영자 패치] 사용자가 요청한 상세 3단계 분석 포맷으로 회귀"""
        prompt = f"""
        IT 전문가로서 다음 기사를 상세 분석하세요. 반드시 한국어만 사용하세요.
        제목: {article['title']}
        내용: {article.get('description', '')[:800]}

        [응답 형식]
        1. 개발자 관점에서 핵심 요약:
        (기사의 핵심 내용을 3줄 이내로 요약)

        2. 기술의 영향력 분석:
        (이 기술이 업계나 개발 환경에 미칠 긍정적/부정적 영향을 불렛포인트로 분석)

        3. 논리적인 분석:
        (전문가 시선에서 이 기술의 한계점이나 향후 과제를 논리적으로 비평)
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
        1. 핵심 키워드: 뉴스들을 관통하는 키워드 3개를 #해시태그 형태로 제시.
        2. 기술 총평: 오늘 IT 업계의 주요 흐름을 3줄로 요약.
        3. 🚀 오늘의 추천 액션: 개발자가 오늘 학습하거나 검토해야 할 구체적인 기술 개념 1개와 선정 이유.
        """
        summary = await self._call_ai_engines(prompt, temp=0.2)
        
        # 가독성 정리 (불필요한 기호 제거)
        summary = summary.strip().replace('*', '') 
        
        return f"""
📊 **IT TREND INTELLIGENCE**
━━━━━━━━━━━━━━━━━━━━
{summary}

📝 분석 대상: {len(scored_articles)}개 최신 기사
━━━━━━━━━━━━━━━━━━━━
"""