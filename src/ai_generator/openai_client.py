"""OpenAI API 클라이언트"""
import base64
from openai import OpenAI
from pathlib import Path
from typing import List
from shared.logger import setup_logger
from shared.config import config

logger = setup_logger(__name__)


class OpenAIClient:
    """OpenAI API 클라이언트"""
    
    def __init__(self):
        """초기화"""
        self.api_key = config.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key)
        self.model = config.OPENAI_MODEL or "gpt-4o-mini"
        logger.info(f"OpenAIClient initialized with model: {self.model}")
    
    def analyze_and_generate(self, image_paths: List[str], user_context: str = None) -> dict:
        """
        이미지 분석 및 SNS 글 생성
        
        Args:
            image_paths: 이미지 파일 경로 리스트
            user_context: 사용자 추가 정보 (선택)
            
        Returns:
            dict: 생성된 콘텐츠
        """
        try:
            # 메시지 구성
            messages = [
                {
                    "role": "system",
                    "content": "당신은 SNS 게시글 작성 전문가입니다. 이미지를 분석하고 매력적인 게시글을 작성합니다."
                }
            ]
            
            # 사용자 메시지 (프롬프트 + 이미지들)
            content = []
            
            # 프롬프트 추가
            prompt = self._build_prompt(len(image_paths), user_context)
            content.append({"type": "text", "text": prompt})
            
            # 이미지 추가
            for path in image_paths:
                base64_image = self._encode_image(path)
                ext = Path(path).suffix.lower()
                mime_map = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp',
                }
                mime_type = mime_map.get(ext, 'image/jpeg')
                
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{base64_image}"
                    }
                })
                logger.debug(f"Image added: {Path(path).name}")
            
            messages.append({"role": "user", "content": content})
            
            # API 호출
            logger.info(f"Calling OpenAI API with {len(image_paths)} image(s)")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=2000
            )
            
            # 응답 파싱
            response_text = response.choices[0].message.content
            result = self._parse_response(response_text)
            logger.info("Content generated successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate content: {e}", exc_info=True)
            raise
    
    def _encode_image(self, image_path: str) -> str:
        """이미지를 base64로 인코딩"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    
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
        
        text = response_text.strip()
        
        # 코드 블록 제거
        if text.startswith("```"):
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
    
    def regenerate_with_feedback(self, existing_content: dict, feedback: str) -> dict:
        """
        피드백을 반영하여 콘텐츠 재생성 (이미지 없이)
        
        Args:
            existing_content: 기존 생성된 콘텐츠
            feedback: 사용자 피드백
            
        Returns:
            dict: 재생성된 콘텐츠
        """
        try:
            prompt = f"""기존에 작성한 SNS 게시글을 사용자의 피드백을 반영하여 수정해줘.

[기존 인스타그램 글]
{existing_content.get('instagram_text', '')}

{existing_content.get('instagram_hashtags', '')}

[기존 페이스북 글]
{existing_content.get('facebook_text', '')}

{existing_content.get('facebook_hashtags', '')}

[사용자 피드백]
{feedback}

피드백을 반영하여 수정한 글을 작성해줘.

**반드시 아래 JSON 형식으로만 출력해. 다른 텍스트 없이 JSON만 출력해:**
{{
  "instagram_text": "본문 (이모지 포함)",
  "instagram_hashtags": "#태그1 #태그2 #태그3...",
  "facebook_text": "본문",
  "facebook_hashtags": "#키워드1 #키워드2..."
}}"""
            
            messages = [
                {
                    "role": "system",
                    "content": "당신은 SNS 게시글 작성 전문가입니다. 사용자의 피드백을 반영하여 글을 수정합니다."
                },
                {"role": "user", "content": prompt}
            ]
            
            logger.info("Calling OpenAI API for regeneration")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=2000
            )
            
            response_text = response.choices[0].message.content
            result = self._parse_response(response_text)
            logger.info("Content regenerated successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to regenerate content: {e}", exc_info=True)
            raise
