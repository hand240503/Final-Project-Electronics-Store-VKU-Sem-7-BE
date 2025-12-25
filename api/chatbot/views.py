from google import genai
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings

@api_view(['POST'])
def chat_with_gemini(request):
    """
    View xử lý chat với Gemini API.
    Input: JSON {"message": "Câu hỏi của bạn"}
    """
    try:
        # 1. Lấy API Key từ settings.py
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            return Response({
                'success': False, 
                'error': 'Cấu hình GEMINI_API_KEY thiếu trong settings.py'
            }, status=500)

        # 2. Khởi tạo Client
        client = genai.Client(api_key=api_key)
        
        # 3. Lấy nội dung người dùng gửi lên từ Postman/Frontend
        user_prompt = request.data.get('message', 'Explain how AI works in a few words')
        
        # 4. Gọi Gemini API (Sử dụng model 2.0 Flash mới nhất)
        # Lưu ý: Không dùng gemini-3... vì chưa tồn tại
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=user_prompt,
        )
        
        return Response({
            'success': True, 
            'response': response.text
        })

    except Exception as e:
        error_message = str(e)
        
        # Xử lý lỗi 429 (Hết hạn mức/gọi quá nhanh)
        if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
            return Response({
                'success': False, 
                'error': 'Hết hạn mức (Quota). Vui lòng đợi 60s hoặc đổi API Key mới từ AI Studio.',
                'details': error_message
            }, status=429)
        
        # Xử lý các lỗi khác (Sai Key, Model không đúng, Mạng...)
        return Response({
            'success': False, 
            'error': 'Lỗi kết nối API Gemini',
            'details': error_message
        }, status=500)