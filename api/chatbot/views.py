from google import genai
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import requests
import re

from google import genai
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import requests
import re

@api_view(['POST'])
def chat_with_gemini(request):
    """
    API endpoint để chat với Gemini AI
    Tự động lấy thông tin sản phẩm nếu user hỏi về sản phẩm
    """
    try:
        # Lấy message từ request
        message = request.data.get('message', '').strip()
        
        if not message:
            return Response({
                'success': False,
                'error': 'Message không được để trống'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Lấy API key
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            return Response({
                'success': False,
                'error': 'GEMINI_API_KEY chưa được cấu hình'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Lấy thông tin sản phẩm từ database
        products_context = ""
        products_data = []
        
        try:
            # Gọi API lấy thông tin sản phẩm
            products_response = requests.get(
                f"http://localhost:8000/api/products/chatbot-info/",
                params={'limit': 20},
                timeout=5
            )
            
            if products_response.status_code == 200:
                api_data = products_response.json()
                
                # Format thông tin sản phẩm cho Gemini
                if api_data.get('success') and api_data.get('products'):
                    products_data = api_data['products']  # Lưu để trả về
                    products_context = "\n\n📦 THÔNG TIN SẢN PHẨM CỬA HÀNG:\n"
                    
                    for idx, product in enumerate(products_data[:15], 1):
                        products_context += f"\n[{idx}] Tên: {product['name']}"
                        
                        # Brand
                        if product.get('brand') and isinstance(product['brand'], dict):
                            brand_name = product['brand'].get('name', '')
                            if brand_name:
                                products_context += f" (Thương hiệu: {brand_name})"
                        
                        # Price
                        try:
                            price_int = int(product['price'])
                            products_context += f"\n    Giá: {price_int:,}đ"
                        except:
                            products_context += f"\n    Giá: {product['price']}đ"
                        
                        # Discount price
                        if product.get('discount_price'):
                            try:
                                discount_int = int(product['discount_price'])
                                original_int = int(product['price'])
                                percent = round(((original_int - discount_int) / original_int) * 100)
                                products_context += f" → {discount_int:,}đ (-{percent}%)"
                            except:
                                pass
                        
                        # Rating
                        products_context += f"\n    Đánh giá: {product['rating']}⭐ ({product['num_reviews']} reviews)"
                        products_context += f"\n    Đã bán: {product['sold']}"
                        
                        # Category
                        if product.get('category'):
                            products_context += f"\n    Danh mục: {product['category']}"
                        
                        products_context += "\n"
                    
                    # Thêm thông tin categories
                    if api_data.get('categories'):
                        products_context += "\n📁 DANH MỤC SẢN PHẨM:\n"
                        for cat in api_data['categories'][:15]:
                            products_context += f"- {cat['name']}"
                            if cat.get('parent'):
                                products_context += f" (thuộc {cat['parent']})"
                            products_context += "\n"
        
        except Exception as e:
            print(f"⚠️ Không thể lấy thông tin sản phẩm: {e}")
        
        # Tạo prompt với context
        system_prompt = """Bạn là trợ lý AI của cửa hàng thương mại điện tử. 
Nhiệm vụ của bạn là:
1. Tư vấn sản phẩm dựa trên thông tin được cung cấp
2. Giải đáp thắc mắc về chính sách mua hàng, đổi trả
3. Giúp khách hàng tìm sản phẩm phù hợp
4. Trả lời thân thiện, chuyên nghiệp bằng tiếng Việt

Lưu ý:
- Chỉ đề xuất sản phẩm có trong danh sách được cung cấp (đánh số từ [1] đến [15])
- Khi giới thiệu sản phẩm, hãy đề cập số thứ tự [X] để dễ tham chiếu
- Nêu rõ giá, đánh giá, số lượng đã bán
- Nếu có giảm giá, nhấn mạnh điều này
- Nếu không có thông tin, hãy thành thật nói không biết
- Giới thiệu tối đa 3 sản phẩm phù hợp nhất
"""
        
        full_message = system_prompt + products_context + f"\n\n👤 KHÁCH HÀNG HỎI: {message}"
        
        # Gọi Gemini API
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_message
        )
        
        ai_response = response.text
        
        # Tìm các sản phẩm được đề cập trong response (theo số thứ tự [1], [2], [3]...)
        recommended_products = []
        if products_data:
            # Tìm pattern [1], [2], [3]... trong response
            mentioned_indices = re.findall(r'\[(\d+)\]', ai_response)
            
            # Lấy tối đa 3 sản phẩm đầu tiên được đề cập
            seen_indices = set()
            for idx_str in mentioned_indices[:3]:
                idx = int(idx_str) - 1  # Convert to 0-based index
                if 0 <= idx < len(products_data) and idx not in seen_indices:
                    recommended_products.append(products_data[idx])
                    seen_indices.add(idx)
        
        print(f'✅ Recommended {len(recommended_products)} products')
        if recommended_products:
            print(f'📦 First product: {recommended_products[0]}')
        
        return Response({
            'success': True,
            'response': ai_response,
            'metadata': {
                'products': recommended_products  # Trả về products để Flutter hiển thị
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def chat_health_check(request):
    """
    Health check endpoint - kiểm tra kết nối với Gemini API
    """
    try:
        # Kiểm tra API key
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            return Response({
                'status': 'unhealthy',
                'service': 'Chatbot API',
                'error': 'GEMINI_API_KEY not configured'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Test connection với Gemini
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents='Hi'
        )
        
        return Response({
            'status': 'healthy',
            'service': 'Chatbot API',
            'gemini_status': 'connected',
            'model': 'gemini-2.5-flash'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'service': 'Chatbot API',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)