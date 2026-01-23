"""유틸리티 함수 모음"""
import hashlib
import json
from pathlib import Path
from typing import Any, List
from PIL import Image
from shared.logger import setup_logger

logger = setup_logger(__name__)

# 이미지 리사이징 설정
MAX_IMAGE_WIDTH = 1080
MAX_IMAGE_HEIGHT = 1350  # 인스타그램 세로 비율 최대


def calculate_file_hash(file_path: str) -> str:
    """
    파일 해시 계산 (중복 감지용)
    
    Args:
        file_path: 파일 경로
        
    Returns:
        str: MD5 해시값
    """
    try:
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return md5.hexdigest()
    except Exception as e:
        logger.error(f"Failed to calculate hash for {file_path}: {e}")
        return ""


def ensure_directory(dir_path: str) -> bool:
    """
    디렉토리 생성 (없으면)
    
    Args:
        dir_path: 디렉토리 경로
        
    Returns:
        bool: 성공 여부
    """
    try:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {dir_path}: {e}")
        return False


def save_json(data: Any, file_path: str) -> bool:
    """
    JSON 파일 저장
    
    Args:
        data: 저장할 데이터
        file_path: 파일 경로
        
    Returns:
        bool: 성공 여부
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug(f"Saved JSON: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON to {file_path}: {e}")
        return False


def load_json(file_path: str) -> dict | None:
    """
    JSON 파일 로드
    
    Args:
        file_path: 파일 경로
        
    Returns:
        dict | None: 로드된 데이터 또는 None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.debug(f"Loaded JSON: {file_path}")
        return data
    except FileNotFoundError:
        logger.warning(f"JSON file not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load JSON from {file_path}: {e}")
        return None


def get_file_size(file_path: str) -> int:
    """
    파일 크기 가져오기
    
    Args:
        file_path: 파일 경로
        
    Returns:
        int: 파일 크기 (바이트), 실패 시 -1
    """
    try:
        return Path(file_path).stat().st_size
    except Exception as e:
        logger.error(f"Failed to get file size for {file_path}: {e}")
        return -1


def resize_image(image_path: str, max_width: int = MAX_IMAGE_WIDTH, max_height: int = MAX_IMAGE_HEIGHT) -> bool:
    """
    이미지 리사이징 (원본 덮어쓰기)
    
    Args:
        image_path: 이미지 파일 경로
        max_width: 최대 너비 (기본 1080)
        max_height: 최대 높이 (기본 1350)
        
    Returns:
        bool: 성공 여부
    """
    try:
        with Image.open(image_path) as img:
            original_size = img.size
            
            # 이미 작으면 스킵
            if img.width <= max_width and img.height <= max_height:
                logger.debug(f"Image already small enough: {image_path} ({img.width}x{img.height})")
                return True
            
            # 비율 유지하면서 리사이즈
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # 원본 형식 유지하면서 저장
            img_format = img.format or 'JPEG'
            if img_format == 'JPEG':
                img.save(image_path, format=img_format, quality=90, optimize=True)
            else:
                img.save(image_path, format=img_format, optimize=True)
            
            logger.info(f"Image resized: {Path(image_path).name} ({original_size[0]}x{original_size[1]} -> {img.width}x{img.height})")
            return True
            
    except Exception as e:
        logger.error(f"Failed to resize image {image_path}: {e}")
        return False


def resize_images(image_paths: List[str]) -> List[str]:
    """
    여러 이미지 리사이징
    
    Args:
        image_paths: 이미지 파일 경로 리스트
        
    Returns:
        List[str]: 리사이징된 이미지 경로 리스트 (실패한 것 제외)
    """
    resized_paths = []
    
    for path in image_paths:
        if resize_image(path):
            resized_paths.append(path)
        else:
            logger.warning(f"Skipping failed resize: {path}")
    
    logger.info(f"Resized {len(resized_paths)}/{len(image_paths)} images")
    return resized_paths
