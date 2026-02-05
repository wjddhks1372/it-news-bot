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

    # analyzer.py 내 analyze_article 메서드 수정
    def analyze_article(self, article: dict) -> str:
        # 영문 소스 여부 판단 로직 (단순 소스 이름 매칭)
        is_global = article['source'] in ["HackerNews", "TechCrunch", "TheVerge", "AWS_Global"]
        
        # [운영자 프롬프트] 번역과 분석을 동시에 수행
        prompt = f"""
        당신은 시니어 소프트웨어 엔지니어이자 기술 전문 번역가입니다. 
        다음 IT 뉴스를 분석하여 '한국어'로 보고서를 작성하세요.

        [지침]
        1. 영문 기사라면 반드시 자연스러운 한국어로 번역하여 요약할 것.
        2. 개발자에게 중요한 기술적 가치(Stack, Architecture, Logic) 위주로 분석할 것.
        3. 감정을 배제하고 비판적·논리적 사고를 바탕으로 작성할 것.
        4. 가독성을 위해 불릿 포인트(•)를 사용하고 3줄 이내로 요약할 것.

        기사 제목: {article['title']}
        기사 내용: {article['description'][:1000]}
        """

        # 4단 엔진을 순차적으로 호출 (기존 Failover 로직 활용)
        analysis = self._call_ai_engines(prompt)
        
        if not analysis:
            return "📌 상세 분석 생략 (AI 엔진 소진으로 원문을 참조해주세요)"
            
        return analysis