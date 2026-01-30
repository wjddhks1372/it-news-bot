import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 테스트 우선순위 리스트
test_models = [
    "models/gemini-2.5-flash-lite", 
    "models/gemini-2.5-flash", 
    "models/gemini-1.5-flash"
]

for model_id in test_models:
    try:
        response = client.models.generate_content(
            model=model_id,
            contents="ping"
        )
        print(f"✅ {model_id}: 사용 가능 (응답: {response.text.strip()})")
        break # 하나라도 성공하면 중단
    except Exception as e:
        print(f"❌ {model_id}: 사용 불가 (이유: {str(e)[:50]}...)")