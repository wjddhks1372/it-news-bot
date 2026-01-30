from google import genai
import logging
import time
from config.settings import settings

logger = logging.getLogger(__name__)

class NewsAnalyzer: # <--- 이 클래스 이름이 main.py의 import 문과 일치해야 합니다.
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_id = "models/gemini-2.5-flash-lite"

    def _generate_prompt(self, title: str, description: str) -> str:
        return f"""
        당신은 시니어 DevOps 엔지니어입니다. 다음 IT 뉴스를 분석하여 보고하세요.
        
        [지침]
        1. HTML 태그(<b>, <i>)만 사용하고 마크다운 기호(#, *, -, `)는 '절대' 사용하지 마세요.
        2. 가독성을 위해 불렛 포인트 대신 이모지(🔹, ✅, 🚀)를 사용하세요.
        3. 섹션 구분은 명확하게 줄바꿈을 활용하세요.

        [기사 정보]
        - 제목: {title}
        - 내용: {description}

        [보고 형식]
        <b>[1. 기술적 시사점]</b> (Linux, Cloud, DevOps 관점)
        (내용 작성)

        <b>[2. 해석 및 분석]</b> (트렌드 전망)
        (내용 작성)

        <b>[3. 최종 요약]</b>
        ✅ (한 줄 요약)
        """

    def analyze_article(self, article: dict) -> str:
        for attempt in range(3):
            try:
                prompt = self._generate_prompt(article['title'], article['description'])
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                if "429" in str(e):
                    wait_time = (attempt + 1) * 15
                    logger.warning(f"429 에러 발생. {wait_time}초 후 재시도... ({attempt+1}/3)")
                    time.sleep(wait_time)
                    continue
                logger.error(f"Gemini 분석 중 오류 발생: {e}")
                return f"분석 실패: {str(e)[:50]}"
        return "할당량 초과로 분석 실패"

    def analyze_daily_summary(self, articles: list) -> str:
        if not articles: return "요약할 뉴스 없음"
        
        titles = "\n".join([f"- {a['title']}" for a in articles])
        
        # 더욱 엄격한 HTML 가이드라인 제공
        prompt = f"""
        당신은 시니어 DevOps 엔지니어입니다. 오늘의 IT 뉴스를 종합 분석하여 보고하세요.
        
        [지침]
        1. 텔레그램 호환을 위해 <b>, <i> 태그만 사용하세요.
        2. <h1>, <h2>, <ul>, <li> 등 다른 태그는 '절대' 사용하지 마세요.
        3. 섹션 제목은 <b>[제목]</b> 형식을 사용하세요.
        4. 불렛 포인트는 이모지(🔹)를 사용하세요.

        [오늘의 뉴스 목록]
        {titles}

        [보고 형식]
        <b>[오늘의 기술 트렌드 요약]</b>
        🔹 (분석 내용 1)
        🔹 (분석 내용 2)
        
        <b>[결론]</b>
        (한 줄 요약)
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"종합 분석 오류: {e}")
            return "종합 분석 실패"