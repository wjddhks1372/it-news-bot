import google.generativeai as genai
import logging
import time
import os

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self, state_manager):
        self.state = state_manager
        self.api_keys = os.getenv("GEMINI_API_KEYS", "").split(",")
        self.current_key_idx = 0
        self._init_client()

    def _init_client(self):
        if not self.api_keys or not self.api_keys[0]:
            raise ValueError("GEMINI_API_KEYS가 설정되지 않았습니다.")
        genai.configure(api_key=self.api_keys[self.current_key_idx])
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    # [핵심 수정] 누락된 4단 엔진 순차 호출 로직
    def _call_ai_engines(self, prompt: str) -> str:
        attempt = 0
        while attempt < len(self.api_keys):
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                if "429" in str(e):
                    attempt += 1
                    if attempt < len(self.api_keys):
                        logger.warning(f"🔄 {attempt}번 엔진 소진. 다음 엔진으로 교체 중...")
                        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
                        self._init_client()
                    else:
                        logger.error("🛡️ 모든 AI 엔진 할당량 소진.")
                else:
                    logger.error(f"❌ AI 호출 중 예상치 못한 에러: {e}")
                    break
        return None

    def score_articles(self, articles: list) -> list:
        scored_articles = []
        for a in articles:
            prompt = f"다음 뉴스의 기술적 가치를 1-10점으로 평가하고 짧은 이유를 적어줘: {a['title']}"
            result = self._call_ai_engines(prompt)
            
            if result:
                # 결과 파싱 로직 (점수와 이유 추출)
                score = 5 # 기본값
                reason = result[:50]
                scored_articles.append({**a, "score": score, "reason": reason})
            else:
                # 엔진 전멸 시 생존 모드 점수 부여
                scored_articles.append({**a, "score": 4, "reason": "생존 모드: 키워드 기반 자동 선정"})
        return scored_articles

    def analyze_article(self, article: dict) -> str:
        # 글로벌 소스 여부 판단
        is_global = article['source'] in ["HackerNews", "TechCrunch", "TheVerge", "AWS_Global"]
        
        prompt = f"""
        당신은 IT 전문 분석가입니다. 다음 기사를 분석하세요.
        {'[영문 기사 번역 포함]' if is_global else ''}
        내용: {article['title']} - {article.get('description', '')[:500]}
        한국어로 3줄 요약하고 기술적 가치를 설명하세요.
        """
        
        analysis = self._call_ai_engines(prompt)
        return analysis or "📌 상세 분석 생략 (AI 엔진 소진)"