"""Gemini API 클라이언트 (새 google-genai 패키지)"""
from google import genai
from google.genai import types
from pathlib import Path
from typing import List
from shared.logger import setup_logger
from shared.config import config

logger = setup_logger(__name__)


class GeminiClient:
    """Gemini API 클라이언트"""
    
    def __init__(self):
        """초기화"""
        self.api_key = config.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-2.0-flash"
        logger.info("GeminiClient initialized")
    
    def analyze_and_generate(self, image_paths: List[str], user_context: str = None) -> dict:
        """
        이미지 분석 및 SNS 글 생성
        
        Args:
            image_paths: 이미지 파일 경로 리스트
            user_context: 사용자 추가 정보 (선택)
            
        Returns:
            dict: 생성된 콘텐츠 (instagram_text, instagram_hashtags, facebook_text, facebook_hashtags)
        """
        try:
            # 이미지 로드
            contents = []
            
            # 프롬프트 추가
            prompt = self._build_prompt(len(image_paths), user_context)
            contents.append(prompt)
            
            # 이미지 추가
            for path in image_paths:
                with open(path, 'rb') as f:
                    image_data = f.read()
                
                # 파일 확장자로 MIME 타입 결정
                ext = Path(path).suffix.lower()
                mime_map = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp',
                    '.heic': 'image/heic',
                    '.heif': 'image/heif',
                }
                mime_type = mime_map.get(ext, 'image/jpeg')
                
                contents.append(types.Part.from_bytes(data=image_data, mime_type=mime_type))
                logger.debug(f"Image added: {Path(path).name}")
            
            # API 호출
            logger.info(f"Calling Gemini API with {len(image_paths)} image(s)")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents
            )
            
            # 응답 파싱
            result = self._parse_response(response.text)
            logger.info("Content generated successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate content: {e}", exc_info=True)
            raise
    
    def _build_prompt(self, image_count: int, user_context: str = None) -> str:
        """프롬프트 생성"""
        context_text = user_context if user_context else "없음"
        
        prompt = f"""이 사진(들)을 분석해서 SNS 게시글을 작성해줘.

[사진 정보]
- 사진 수: {image_count}장
- 추가 정보: {context_text}

[사진 분석]
- 사진이 여러 장이면: 각 사진의 내용과 전체 스토리 흐름 파악
- 사진이 한 장이면: 그 사진의 핵심 요소와 분위기 집중 분석

[인스타그램 버전] - 감정 & 분위기 중심
- 사진 속 감정, 분위기, 시각적 요소를 감각적으로 표현
- 2-3줄의 짧고 임팩트 있는 캡션
- 이모지 적절히 활용
- 해시태그 15개 (한글 5개, 영문 10개)
- 톤: 감성적이고 세련되게

[페이스북 버전] - 스토리 & 설명 중심
- 사진(들)에 담긴 배경 스토리를 구체적으로 설명
- 언제, 어디서, 왜, 무엇을, 어떻게 + 느낀 점
- 4-6문단의 읽을거리 있는 글
- 정보와 팁 포함 (있다면)
- 톤: 친근하고 진솔하게, 대화하듯이

**반드시 아래 JSON 형식으로만 출력해. 다른 텍스트 없이 JSON만 출력해:**
{{
  "instagram_text": "본문 (이모지 포함)",
  "instagram_hashtags": "#태그1 #태그2 #태그3...",
  "facebook_text": "본문",
  "facebook_hashtags": "#키워드1 #키워드2..."
}}"""
        
        return prompt
    
    def _parse_response(self, response_text: str) -> dict:
        """응답 파싱"""
        import json
        
        # JSON 추출 (```json ... ``` 형태일 수 있음)
        text = response_text.strip()
        
        if text.startswith("```"):
            # 코드 블록 제거
            lines = text.split("\n")
            json_lines = []
            in_json = False
            for line in lines:
                if line.startswith("```json") or line.startswith("```"):
                    if in_json:
                        break
                    in_json = True
                    continue
                if in_json:
                    json_lines.append(line)
            text = "\n".join(json_lines)
        
        # JSON 파싱
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            # JSON 부분만 추출 시도
            import re
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                result = json.loads(match.group())
            else:
                raise ValueError(f"Failed to parse JSON from response: {text[:200]}")
        
        # 필수 필드 확인
        required_fields = ['instagram_text', 'instagram_hashtags', 'facebook_text', 'facebook_hashtags']
        for field in required_fields:
            if field not in result:
                result[field] = ""
        
        return result
