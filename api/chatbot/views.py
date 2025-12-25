from google import genai
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings

@api_view(['POST'])
def chat_with_gemini(request):
    try:
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        client = genai.Client(api_key=api_key)
        
        # Thử với model 1.5 Flash (ổn định nhất cho tài khoản miễn phí)
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents="Explain how AI works in a few words"
        )
        
        return Response({'success': True, 'response': response.text})
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=429)