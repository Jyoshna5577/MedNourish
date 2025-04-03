import google.generativeai as genai

GOOGLE_API_KEY = "AIzaSyD_sO8GUYaCBaDhI3PQmPiTTihiyQ9oia8"  # Replace with your actual Google API Key

genai.configure(api_key=GOOGLE_API_KEY)

try:
    gemini_model = genai.GenerativeModel("gemini-1.5-pro-latest")  # ✅ Correct Function
    response = gemini_model.generate_content("Test prompt")
    print(response.text)  # Check if API works
except Exception as e:
    print(f"⚠️ API Error: {e}")
