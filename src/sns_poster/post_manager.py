"""SNS 게시 관리자 - content.json 읽고 게시 후 필드 삭제"""
import json
from pathlib import Path
from typing import List, Optional
from shared.logger import setup_logger
from shared.config import config
from sns_poster.facebook_poster import FacebookPoster
from sns_poster.instagram_poster import InstagramPoster

logger = setup_logger(__name__)

CONTENT_JSON_FILENAME = "content.json"


class PostManager:
    """SNS 게시 관리자"""
    
    def __init__(self):
        """초기화"""
        self.facebook_poster: FacebookPoster | None = None
        self.instagram_poster: InstagramPoster | None = None
        logger.info("PostManager initialized")
    
    def load_content(self, folder_path: str) -> Optional[dict]:
        """
        content.json 로드
        
        Args:
            folder_path: 폴더 경로
            
        Returns:
            dict: 콘텐츠 또는 None
        """
        json_path = Path(folder_path) / CONTENT_JSON_FILENAME
        
        if not json_path.exists():
            logger.warning(f"Content file not found: {json_path}")
            return None
        
        with open(json_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        logger.info(f"Content loaded: {json_path}")
        return content
    
    def save_content(self, folder_path: str, content: dict):
        """
        content.json 저장
        
        Args:
            folder_path: 폴더 경로
            content: 저장할 콘텐츠
        """
        json_path = Path(folder_path) / CONTENT_JSON_FILENAME
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Content saved: {json_path}")
    
    def get_image_files(self, folder_path: str) -> List[str]:
        """
        폴더에서 이미지 파일 목록 가져오기
        
        Args:
            folder_path: 폴더 경로
            
        Returns:
            List[str]: 이미지 파일 경로 리스트
        """
        from shared.constants import SUPPORTED_IMAGE_EXTENSIONS
        
        folder = Path(folder_path)
        image_files = []
        
        for file_path in folder.iterdir():
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in SUPPORTED_IMAGE_EXTENSIONS:
                    image_files.append(str(file_path))
        
        image_files.sort()
        return image_files
    
    async def post_to_facebook(self, folder_path: str, image_paths: List[str] = None) -> bool:
        """
        페이스북에 게시
        
        Args:
            folder_path: content.json이 있는 폴더 경로
            image_paths: 이미지 경로 리스트 (없으면 폴더에서 자동 탐색)
            
        Returns:
            bool: 게시 성공 여부
        """
        # 콘텐츠 로드
        content = self.load_content(folder_path)
        if not content:
            return False
        
        # 페이스북 필드 확인
        facebook_text = content.get('facebook_text', '')
        facebook_hashtags = content.get('facebook_hashtags', '')
        
        if not facebook_text:
            logger.info("[facebook] Already posted or no content - skipping")
            return False
        
        # 이미지 경로
        if not image_paths:
            image_paths = self.get_image_files(folder_path)
        
        # 게시글 조합
        post_text = facebook_text
        if facebook_hashtags:
            post_text = f"{facebook_text}\n\n{facebook_hashtags}"
        
        try:
            # 페이스북 게시
            if not self.facebook_poster:
                self.facebook_poster = FacebookPoster()
            
            await self.facebook_poster.start_browser()
            success = await self.facebook_poster.post(post_text, image_paths)
            await self.facebook_poster.close_browser()
            
            if success:
                # 게시 성공 → 필드 삭제
                logger.info("[facebook] Post successful - removing fields from content.json")
                del content['facebook_text']
                del content['facebook_hashtags']
                self.save_content(folder_path, content)
                return True
            else:
                logger.error("[facebook] Post failed")
                return False
                
        except Exception as e:
            logger.error(f"[facebook] Error: {e}", exc_info=True)
            if self.facebook_poster:
                await self.facebook_poster.close_browser()
            return False
    
    async def post_to_instagram(self, folder_path: str, image_paths: List[str] = None) -> bool:
        """
        인스타그램에 게시
        
        Args:
            folder_path: content.json이 있는 폴더 경로
            image_paths: 이미지 경로 리스트 (없으면 폴더에서 자동 탐색)
            
        Returns:
            bool: 게시 성공 여부
        """
        # 콘텐츠 로드
        content = self.load_content(folder_path)
        if not content:
            return False
        
        # 인스타그램 필드 확인
        instagram_text = content.get('instagram_text', '')
        instagram_hashtags = content.get('instagram_hashtags', '')
        
        if not instagram_text:
            logger.info("[instagram] Already posted or no content - skipping")
            return False
        
        # 이미지 경로 (인스타그램은 이미지 필수)
        if not image_paths:
            image_paths = self.get_image_files(folder_path)
        
        if not image_paths:
            logger.error("[instagram] No images found - cannot post")
            return False
        
        # 게시글 조합
        post_text = instagram_text
        if instagram_hashtags:
            post_text = f"{instagram_text}\n\n{instagram_hashtags}"
        
        try:
            # 인스타그램 게시
            if not self.instagram_poster:
                self.instagram_poster = InstagramPoster()
            
            await self.instagram_poster.start_browser()
            success = await self.instagram_poster.post(post_text, image_paths)
            await self.instagram_poster.close_browser()
            
            if success:
                # 게시 성공 → 필드 삭제
                logger.info("[instagram] Post successful - removing fields from content.json")
                del content['instagram_text']
                del content['instagram_hashtags']
                self.save_content(folder_path, content)
                return True
            else:
                logger.error("[instagram] Post failed")
                return False
                
        except Exception as e:
            logger.error(f"[instagram] Error: {e}", exc_info=True)
            if self.instagram_poster:
                await self.instagram_poster.close_browser()
            return False
    
    async def post_to_all(self, folder_path: str, image_paths: List[str] = None) -> dict:
        """
        모든 SNS에 게시
        
        Args:
            folder_path: content.json이 있는 폴더 경로
            image_paths: 이미지 경로 리스트
            
        Returns:
            dict: 각 플랫폼별 결과 {'facebook': bool, 'instagram': bool}
        """
        results = {
            'facebook': False,
            'instagram': False
        }
        
        # 이미지 경로
        if not image_paths:
            image_paths = self.get_image_files(folder_path)
        
        # 페이스북 게시
        results['facebook'] = await self.post_to_facebook(folder_path, image_paths)
        
        # 인스타그램 게시
        results['instagram'] = await self.post_to_instagram(folder_path, image_paths)
        
        return results
