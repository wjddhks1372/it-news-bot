import google.generativeai as genai
import logging
import os
import asyncio

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self, state_manager):
        self.state = state_manager
        self.api_keys = os.getenv("GEMINI_API_KEYS", "").split(",")
        self.current_key_idx = 0
        self.user_persona = "" # 학습된 페르소나 저장
        self._init_client()

    def _init_client(self):
        if not self.api_keys or not self.api_keys[0]:
            raise ValueError("GEMINI_API_KEYS가 설정되지 않았습니다.")
        # 현재 인덱스의 키로 설정
        genai.configure(api_key=self.api_keys[self.current_key_idx % len(self.api_keys)])
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    # [수정] main.py가 호출하는 사용자 피드백 학습 메서드 복구
    def learn_user_feedback(self):
        try:
            # Supabase에서 유저 취향(persona)을 가져옴
            pref = self.state.db.table("user_preferences").select("*").eq("persona_type", "main").execute()
            if pref.data:
                self.user_persona = pref.data[0].get("description", "")
                logger.info("♻️ 취향 캐시 로드 성공")
            else:
                logger.info("ℹ️ 등록된 사용자 취향이 없습니다. 기본 모드로 작동합니다.")
        except Exception as e:
            logger.error(f"❌ 취향 로드 중 오류: {e}")

    # 4단 엔진 순차 호출 및 Failover 로직
    # src/analyzer.py 수정본
async def _call_ai_engines(self, prompt: str) -> str:
    attempt = 0
    while attempt < len(self.api_keys):
        try:
            # 1분당 15회 제한을 피하기 위해 요청 간에 확실한 5초 대기
            await asyncio.sleep(5) 
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e):
                attempt += 1
                self.current_key_idx += 1
                self._init_client()
                logger.warning(f"⚠️ 엔진 교체 {attempt}차")
                await asyncio.sleep(10) # 차단 시 더 길게 대기
            else:
                break
    return None
            

    def score_articles(self, articles: list) -> list:
        scored_articles = []
        for a in articles:
            prompt = f"사용자 취향: {self.user_persona}\n뉴스 제목: {a['title']}\n위 뉴스의 기술적 가치를 1-10점으로 평가하고 이유를 한 줄로 적어줘."
            result = self._call_ai_engines(prompt)
            
            if result:
                # 간단한 점수 추출 로직 (숫자만 추출)
                score_match = [int(s) for s in result.split() if s.isdigit()]
                score = score_match[0] if score_match else 5
                reason = result[:60]
                scored_articles.append({**a, "score": score, "reason": reason})
            else:
                # 엔진 전멸 시 생존 모드 점수 부여
                scored_articles.append({**a, "score": 4, "reason": "생존 모드: 키워드 기반 자동 선정"})
        return scored_articles

    def analyze_article(self, article: dict) -> str:
        is_global = article['source'] in ["HackerNews", "TechCrunch", "TheVerge", "AWS_Global"]
        prompt = f"""
        당신은 IT 전문 분석가입니다. 
        사용자 취향: {self.user_persona}
        {'[영문 기사 번역 및 요약 포함]' if is_global else ''}
        내용: {article['title']} - {article.get('description', '')[:500]}
        한국어로 3줄 요약하고 기술적 가치를 분석하세요.
        """
        analysis = self._call_ai_engines(prompt)
        return analysis or "📌 상세 분석 생략 (AI 엔진 소진)"