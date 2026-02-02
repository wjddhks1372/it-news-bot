from google import genai
import logging
import re
from config.settings import settings

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_id = "models/gemini-2.5-flash-lite"

    def score_articles(self, articles: list) -> list:
        if not articles: return []
        
        headlines = "\n".join([f"[{i}] {a['title']}" for i, a in enumerate(articles)])
        prompt = f"""
        다음 IT 헤드라인의 기술적 중요도를 1-10점으로 평가하고, 그 이유를 한 문장으로 설명하세요.
        
        [응답 형식]
        각 항목은 반드시 [점수: 근거] 형태로 작성하세요.
        예시:
        [8: 새로운 오픈소스 LLM의 등장으로 개발 생태계 변화 예상]
        [3: 특정 기업의 단순한 이벤트 홍보성 뉴스]

        [목록]
        {headlines}
        """
        
        try:
            response = self.client.models.generate_content(model=self.model_id, contents=prompt)
            # [점수: 근거] 패턴 추출
            pattern = r"\[(\d+):\s*(.*?)\]"
            matches = re.findall(pattern, response.text)
            
            for i, a in enumerate(articles):
                if i < len(matches):
                    a['score'] = int(matches[i][0])
                    a['reason'] = matches[i][1]
                else:
                    a['score'] = 1
                    a['reason'] = "평가 실패"
            return articles
        except Exception as e:
            logger.error(f"스코어링 실패: {e}")
            return [dict(a, score=1, reason="오류 발생") for a in articles]

    def analyze_article(self, article: dict) -> str:
        prompt = f"""
        당신은 시니어 DevOps 엔지니어입니다. 다음 뉴스를 분석하십시오.
        지침: <b>, <i> 태그만 사용. 기호(*, -, •) 절대 금지. 섹션간 두 줄 줄바꿈.

        기사 제목: {article['title']}
        기사 설명: {article['description']}
        
        [응답 형식]
        <b>[기술적 시사점]</b>
        (내용)

        <b>[해석 및 분석]</b>
        (내용)

        <b>[요약]</b>
        ✅ (한 줄 요약)
        """
        try:
            return self.client.models.generate_content(model=self.model_id, contents=prompt).text
        except: return "분석 실패"

    def analyze_daily_summary(self, articles: list) -> str:
        if not articles: return "요약할 뉴스 없음"
        content = "\n".join([f"제목: {a['title']} (점수: {a['score']}, 근거: {a['reason']})" for a in articles])
        prompt = f"""
        오늘의 기술 뉴스를 요약 보고하십시오. 기호(*, -, •) 절대 사용 금지.
        {content}
        
        [응답 형식]
        <b>[오늘의 핵심 기술 트렌드]</b>

        <b>1. (주제)</b>
        (내용)

        ✅ <b>최종 요약</b>
        (내용)
        """
        try:
            return self.client.models.generate_content(model=self.model_id, contents=prompt).text
        except: return "요약 실패"