from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("--- 사용 가능한 모델 목록 ---")
try:
    # 속성명 대신 객체 자체를 출력하여 가능한 이름을 확인합니다.
    for model in client.models.list():
        print(f"Name: {model.name}")
except Exception as e:
    print(f"에러 발생: {e}")