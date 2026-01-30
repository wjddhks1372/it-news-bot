from google import genai
import logging
import time
import re
from config.settings import settings

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_id = "models/gemini-2.5-flash-lite"

    def score_articles(self, articles: list) -> list:
        """기사들의 중요도를 1-10점으로 배치 스코어링합니다."""
        if not articles: return []
        
        headlines = "\n".join([f"[{i}] {a['title']}" for i, a in enumerate(articles)])
        prompt = f"다음 IT 헤드라인의 기술적 가치를 1-10점으로 평가해 리스트로 응답하세요. 예: [5, 8, 3]\n\n{headlines}"
        
        try:
            response = self.client.models.generate_content(model=self.model_id, contents=prompt)
            scores = [int(s) for s in re.findall(r'\d+', response.text)]
            for i, a in enumerate(articles):
                a['score'] = scores[i] if i < len(scores) else 1
            return articles
        except:
            return [dict(a, score=1) for a in articles]

    def analyze_article(self, article: dict) -> str:
        """고득점 기사에 대한 상세 분석 리포트를 생성합니다."""
        prompt = f"""
        당신은 시니어 DevOps 엔지니어입니다. 다음 뉴스를 전문적으로 분석하세요.
        지침: <b>, <i> 태그만 사용. 마크다운 기호 금지. 이모지 활용.
        
        제목: {article['title']}
        내용: {article['description']}
        
        보고 형식:
        <b>[기술적 시사점]</b>
        🔹 (내용)
        <b>[해석 및 분석]</b>
        🚀 (내용)
        <b>[최종 요약]</b>
        ✅ (한 줄 요약)
        """
        try:
            return self.client.models.generate_content(model=self.model_id, contents=prompt).text
        except: return "분석 실패"

    def analyze_daily_summary(self, articles: list) -> str:
        """중간 점수(4-6점) 기사들을 모아 '오늘 놓치면 아쉬운 뉴스'로 요약합니다."""
        if not articles: return "오늘 요약할 추가 뉴스가 없습니다."
        
        content = "\n".join([f"🔹 <b>{a['title']}</b> (점수: {a['score']}점)" for a in articles])
        prompt = f"다음 뉴스들의 핵심 내용을 묶어 '오늘의 기술 트렌드'로 HTML 요약 보고서를 작성하세요.\n\n{content}"
        
        try:
            return self.client.models.generate_content(model=self.model_id, contents=prompt).text
        except: return "종합 요약 실패"