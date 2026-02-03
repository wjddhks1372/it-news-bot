import logging
import re
from google import genai
from config.settings import settings
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self, state_manager=None):
        # settings를 직접 참조하거나 주입받을 수 있도록 유연하게 구성
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_id = "gemini-2.0-flash-lite"
        self.state = state_manager  # Supabase StateManager 연결
        self.user_pref_summary = "" # 학습된 취향 저장용

    def update_user_preference(self):
        """DB의 'up' 피드백을 분석하여 사용자 취향 요약문을 생성합니다."""
        if not self.state or not self.state.client:
            self.user_pref_summary = "일반적인 DevOps 및 IT 인프라 기술에 집중하세요."
            return

        try:
            # 1. 긍정 피드백 기사 가져오기 (최근 20건)
            response = self.state.client.table("news_articles") \
                .select("title, reason") \
                .eq("feedback", "up") \
                .order("created_at", desc={"ascending": False}) \
                .limit(20) \
                .execute()

            liked_articles = response.data
            if not liked_articles:
                self.user_pref_summary = "데이터가 부족합니다. 최신 인프라 및 소프트웨어 공학 트렌드에 집중하세요."
                return

            # 2. Gemini에게 취향 분석 요청
            context = "\n".join([f"- {a['title']}: {a['reason']}" for a in liked_articles])
            
            prompt = f"""
            사용자가 '유용함'이라고 평가한 IT 뉴스들입니다. 이 사용자의 기술적 관심사를 3줄 이내로 요약하세요.
            이 내용은 향후 뉴스 필터링의 핵심 기준으로 사용됩니다.

            [피드백 데이터]
            {context}
            """
            
            result = self.client.models.generate_content(model=self.model_id, contents=prompt)
            self.user_pref_summary = result.text.strip()
            logger.info(f"🎯 사용자 취향 업데이트 완료: {self.user_pref_summary[:50]}...")
            
        except Exception as e:
            logger.error(f"사용자 취향 분석 실패: {e}")
            self.user_pref_summary = "오류 발생으로 인한 기본 취향 유지."

    def score_articles(self, articles: list) -> list:
        """수집된 뉴스들에 대해 1차 스코어링을 수행합니다."""
        if not articles: return []
        
        # 취향 데이터가 없으면 로드
        if not self.user_pref_summary: self.update_user_preference()

        headlines = "\n".join([f"[{i}] {a['title']}" for i, a in enumerate(articles)])
        prompt = f"""
        당신은 시니어 DevOps 엔지니어입니다. 다음 IT 뉴스의 기술적 가치를 1-10점으로 평가하세요.
        
        [사용자 선호도 기준]
        {self.user_pref_summary}

        [응답 형식]
        반드시 [점수: 근거] 형태로 작성하세요. (한 줄에 하나씩)
        예: [8: 대규모 분산 시스템의 트래픽 관리 기법으로 실무 가치 높음]

        [목록]
        {headlines}
        """
        
        try:
            response = self.client.models.generate_content(model=self.model_id, contents=prompt)
            pattern = r"\[(\d+):\s*(.*?)\]"
            matches = re.findall(pattern, response.text)
            
            for i, a in enumerate(articles):
                if i < len(matches):
                    a['score'] = int(matches[i][0])
                    a['reason'] = matches[i][1]
                else:
                    a['score'] = 1
                    a['reason'] = "평가 누락"
            return articles
        except Exception as e:
            logger.error(f"스코어링 실패: {e}")
            return [dict(a, score=1, reason="평가 프로세스 에러") for a in articles]

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def analyze_article(self, article: dict) -> str:
        """개별 기사에 대한 심층 분석을 수행합니다 (가독성 최적화)."""
        prompt = f"""
        당신은 IT 기술 전문가이자 시니어 엔지니어입니다. 다음 기사를 분석하십시오.

        [제약 사항 - 가독성을 위해 반드시 준수]
        1. 모든 내용은 글머리 기호(*)를 사용한 리스트 형식으로만 작성하세요. 줄글 금지.
        2. 이탤릭체 유발 기호(_, *)를 문장 중간에 절대 사용하지 마세요. (예: _단어_ 금지)
        3. 강조는 오직 <b> 태그만 사용하세요. (HTML 파싱 모드)
        4. 섹션 구분은 명확하게 하세요.

        [사용자 선호도]
        {self.user_pref_summary}

        기사 제목: {article['title']}
        설명: {article['description']}
        
        [출력 양식]
        <b>[기술적 시사점]</b>
        * (내용1)
        * (내용2)

        <b>[비판적 분석]</b>
        * (내용1)
        * (내용2)

        <b>[최종 요약]</b>
        ✅ (한 줄 요약)
        """
        try:
            res_text = self.client.models.generate_content(model=self.model_id, contents=prompt).text
            # 혹시 모델이 실수로 넣은 이탤릭 기호(_) 강제 제거 로직 (방어 코드)
            return res_text.replace('_', '')
        except Exception as e:
            logger.error(f"기사 분석 실패: {e}")
            return "분석 엔진 일시 장애"

    def analyze_daily_summary(self, articles: list) -> str:
        """여러 기사를 묶어 종합 트렌드를 보고합니다."""
        if not articles: return "발송할 새로운 기술 소식이 없습니다."
        
        content = "\n".join([f"- {a['title']} (이유: {a['reason']})" for a in articles])
        prompt = f"""
        오늘의 IT 기술 트렌드를 요약 보고하세요. 
        이탤릭체 기호(_, *) 사용을 금지하고 리스트 형식(*)으로 작성하세요.

        [뉴스 목록]
        {content}
        
        [응답 형식]
        <b>[오늘의 핵심 기술 트렌드]</b>

        <b>1. (대주제)</b>
        * (상세 설명)

        <b>2. (대주제)</b>
        * (상세 설명)

        ✅ <b>종합 결론</b>
        (요약 문구)
        """
        try:
            res_text = self.client.models.generate_content(model=self.model_id, contents=prompt).text
            return res_text.replace('_', '')
        except Exception as e:
            logger.error(f"종합 요약 실패: {e}")
            return "종합 요약 생성 중 에러 발생"