import logging
import re
from google import genai
from config.settings import settings

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self, state_manager=None):
        self.keys = settings.GEMINI_API_KEYS
        self.current_index = 0
        self.state = state_manager
        self._init_client()
        
        # 페르소나 기본값 (학습 데이터 없을 시 대비)
        self.pref_cache = "DevOps, 인프라 자동화, AI 신기술"
        self.dislike_cache = "단순 채용, 가비지 뉴스"

    def _init_client(self):
        """현재 인덱스의 API 키로 클라이언트를 생성합니다."""
        if not self.keys:
            raise ValueError("GEMINI_API_KEYS가 설정되지 않았습니다.")
        
        key = self.keys[self.current_index]
        self.client = genai.Client(api_key=key, http_options={'api_version': 'v1'})
        logger.info(f"🔑 {self.current_index + 1}번 엔진 활성화 (총 {len(self.keys)}개 중)")

    def _rotate_engine(self):
        """다음 API 키로 교체합니다. 교체 성공 시 True, 모든 키 소진 시 False 반환."""
        if self.current_index < len(self.keys) - 1:
            self.current_index += 1
            self._init_client()
            return True
        return False

    def score_articles(self, articles: list) -> list:
        if not articles: return []
        
        prompt = f"평가 기준: {self.pref_cache}\n기피: {self.dislike_cache}\n기사 목록 점수 산정..."

        # 최대 4번(키 개수만큼) 반복 시도
        for _ in range(len(self.keys)):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=prompt
                )
                # 데이터 파싱 로직...
                return self._parse_scores(articles, response.text)
                
            except Exception as e:
                # 429(할당량 초과) 발생 시 엔진 교체 후 루프 계속 실행
                if "429" in str(e) and self._rotate_engine():
                    logger.warning(f"⚠️ {self.current_index}번 키 소진됨. 엔진 교체 후 재시도.")
                    continue 
                else:
                    logger.error(f"❌ 모든 API 엔진 정지 또는 치명적 에러: {e}")
                    break

        # [최종 방어] 모든 키가 죽었을 때 작동하는 생존 모드
        return self._survival_fallback(articles)

    def _survival_fallback(self, articles):
        """AI 없이 도메인 우선순위만으로 점수 부여"""
        logger.info("🛡️ 생존 모드 가동: 룰 기반 점수 부여")
        for a in articles:
            a['score'] = 8 if any(k in a['source'].upper() for k in ["TOSS", "KARROT"]) else 5
            a['reason'] = "API 소진으로 인한 자동 선정"
        return articles

    def _parse_scores(self, articles, text):
        # 기존 re.findall 파싱 로직 유지
        matches = re.findall(r"\[(\d+):\s*(.*?)\]", text)
        for i, a in enumerate(articles):
            if i < len(matches):
                a['score'], a['reason'] = int(matches[i][0]), matches[i][1]
            else:
                a['score'], a['reason'] = 1, "응답 누락"
        return articles