import google.generativeai as genai
import os

# 환경 변수에 등록된 첫 번째 키를 직접 넣어보세요
genai.configure(api_key="AIzaSyAbJLSdyFxaKfhTaD5tMBXaz29f1GloJ60")
model = genai.GenerativeModel('gemini-2.0-flash')

try:
    response = model.generate_content("안녕?")
    print("✅ 성공: 키와 당신의 IP는 정상입니다.")
except Exception as e:
    print(f"❌ 실패: {e}")