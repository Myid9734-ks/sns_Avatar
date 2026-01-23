"""콘텐츠 생성 및 저장"""
import json
import os
from pathlib import Path
from typing import List, Optional
from shared.logger import setup_logger
from shared.config import config
from shared.constants import SUPPORTED_IMAGE_EXTENSIONS

logger = setup_logger(__name__)

CONTENT_JSON_FILENAME = "content.json"


class ContentGenerator:
    """SNS 콘텐츠 생성기"""
    
    def __init__(self):
        """초기화"""
        # AI 제공자에 따라 클라이언트 선택
        self.ai_provider = config.AI_PROVIDER or "openai"
        
        if self.ai_provider == "gemini":
            from ai_generator.gemini_client import GeminiClient
            self.ai_client = GeminiClient()
        else:
            from ai_generator.openai_client import OpenAIClient
            self.ai_client = OpenAIClient()
        
        logger.info(f"ContentGenerator initialized with {self.ai_provider}")
    
    def check_content_exists(self, folder_path: str) -> bool:
        """
        폴더에 이미 생성된 콘텐츠(JSON)가 있는지 확인
        
        Args:
            folder_path: 감시 폴더 경로
            
        Returns:
            bool: content.json 존재 여부
        """
        json_path = Path(folder_path) / CONTENT_JSON_FILENAME
        exists = json_path.exists()
        
        if exists:
            logger.info(f"Content already exists: {json_path}")
        
        return exists
    
    def generate_and_save(
        self, 
        folder_path: str, 
        image_paths: List[str], 
        user_context: str = None
    ) -> dict:
        """
        콘텐츠 생성 및 JSON 저장
        
        Args:
            folder_path: 저장할 폴더 경로
            image_paths: 이미지 파일 경로 리스트
            user_context: 사용자 추가 정보 (선택)
            
        Returns:
            dict: 생성된 콘텐츠
        """
        # 이미 존재하면 스킵
        if self.check_content_exists(folder_path):
            logger.info("Skipping AI generation - content already exists")
            return self.load_content(folder_path)
        
        # AI 글 생성
        logger.info(f"Generating content for {len(image_paths)} image(s)")
        content = self.ai_client.analyze_and_generate(image_paths, user_context)
        
        # JSON 저장
        self.save_content(folder_path, content)
        
        return content
    
    def save_content(self, folder_path: str, content: dict):
        """
        콘텐츠를 JSON 파일로 저장
        
        Args:
            folder_path: 저장할 폴더 경로
            content: 저장할 콘텐츠
        """
        json_path = Path(folder_path) / CONTENT_JSON_FILENAME
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Content saved: {json_path}")
    
    def load_content(self, folder_path: str) -> Optional[dict]:
        """
        저장된 콘텐츠 로드
        
        Args:
            folder_path: 폴더 경로
            
        Returns:
            dict: 로드된 콘텐츠 또는 None
        """
        json_path = Path(folder_path) / CONTENT_JSON_FILENAME
        
        if not json_path.exists():
            return None
        
        with open(json_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        logger.info(f"Content loaded: {json_path}")
        return content
    
    def get_image_files(self, folder_path: str) -> List[str]:
        """
        폴더에서 이미지 파일 목록 가져오기
        
        Args:
            folder_path: 폴더 경로
            
        Returns:
            List[str]: 이미지 파일 경로 리스트
        """
        folder = Path(folder_path)
        image_files = []
        
        for file_path in folder.iterdir():
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in SUPPORTED_IMAGE_EXTENSIONS:
                    image_files.append(str(file_path))
        
        # 파일명 순 정렬
        image_files.sort()
        
        return image_files
    
    def regenerate_with_feedback(self, existing_content: dict, feedback: str) -> dict:
        """
        피드백을 반영하여 콘텐츠 재생성 (이미지 없이)
        
        Args:
            existing_content: 기존 생성된 콘텐츠
            feedback: 사용자 피드백
            
        Returns:
            dict: 재생성된 콘텐츠
        """
        logger.info("Regenerating content with feedback")
        content = self.ai_client.regenerate_with_feedback(existing_content, feedback)
        return content
