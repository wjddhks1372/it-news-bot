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
        prompt = f"다음 IT 헤드라인의 기술적 가치를 1-10점으로 평가해 숫자 리스트로 응답하세요.\n\n{headlines}"
        
        try:
            response = self.client.models.generate_content(model=self.model_id, contents=prompt)
            scores = [int(s) for s in re.findall(r'\d+', response.text)]
            for i, a in enumerate(articles):
                a['score'] = scores[i] if i < len(scores) else 1
            return articles
        except:
            return [dict(a, score=1) for a in articles]

    def analyze_article(self, article: dict) -> str:
        # 단일 기사 분석 프롬프트: 기호 제거 및 줄바꿈 강조
        prompt = f"""
        당신은 시니어 DevOps 엔지니어입니다. 다음 뉴스를 분석하십시오.
        
        [지침]
        1. 문장 앞에 '*', '-', '•' 등 어떤 기호도 붙이지 마십시오.
        2. HTML <b>, <i> 태그만 사용하고 마크다운 기호를 사용하지 마십시오.
        3. 각 섹션 사이는 반드시 두 줄의 줄바꿈을 넣으십시오.

        기사 제목: {article['title']}
        내용: {article['description']}
        
        [응답 형식]
        <b>[기술적 시사점]</b>
        (기호 없이 내용 기술)

        <b>[해석 및 분석]</b>
        (기호 없이 내용 기술)

        <b>[요약]</b>
        ✅ (한 줄 요약)
        """
        try:
            return self.client.models.generate_content(model=self.model_id, contents=prompt).text
        except: return "분석 실패"

    def analyze_daily_summary(self, articles: list) -> str:
        # 종합 요약 프롬프트: 가독성 최적화
        if not articles: return "요약할 뉴스 없음"
        
        content = "\n".join([f"제목: {a['title']} (점수: {a['score']})" for a in articles])
        prompt = f"""
        당신은 IT 기술 분석가입니다. 오늘의 주요 뉴스를 종합 보고하십시오.

        [지침]
        1. 텍스트 앞에 '*', '-', '•' 등 목록 기호를 절대 사용하지 마십시오.
        2. 항목은 제목을 <b> 태그로 감싸고 다음 줄에 내용을 적으십시오.
        3. 섹션 사이는 명확히 구분하십시오.

        [뉴스 목록]
        {content}

        [응답 형식]
        <b>[오늘의 핵심 기술 트렌드]</b>

        <b>1. (주요 주제 명칭)</b>
        (설명 내용 기술)

        <b>2. (주요 주제 명칭)</b>
        (설명 내용 기술)

        <b>✅ 최종 요약</b>
        (전체 내용을 관통하는 한 줄 평)
        """
        try:
            return self.client.models.generate_content(model=self.model_id, contents=prompt).text
        except: return "종합 요약 실패"