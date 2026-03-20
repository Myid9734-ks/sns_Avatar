"""유틸리티 함수 모음"""
import hashlib
import json
from pathlib import Path
from typing import Any, List
from PIL import Image
from shared.logger import setup_logger

# HEIC 파일 지원
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORT = True
except ImportError:
    HEIC_SUPPORT = False

logger = setup_logger(__name__)

if HEIC_SUPPORT:
    logger.info("HEIC support enabled")
else:
    logger.warning("pillow-heif not installed, HEIC files may not be supported")

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
    HEIC 파일은 JPG로 변환하여 저장
    
    Args:
        image_path: 이미지 파일 경로
        max_width: 최대 너비 (기본 1080)
        max_height: 최대 높이 (기본 1350)
        
    Returns:
        bool: 성공 여부
    """
    try:
        image_path_obj = Path(image_path)
        is_heic = image_path_obj.suffix.upper() in ['.HEIC', '.HEIF']
        
        with Image.open(image_path) as img:
            original_size = img.size
            
            # 이미 작으면 스킵 (HEIC는 변환 필요)
            if not is_heic and img.width <= max_width and img.height <= max_height:
                logger.debug(f"Image already small enough: {image_path} ({img.width}x{img.height})")
                return True
            
            # 비율 유지하면서 리사이즈
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # HEIC 파일은 JPG로 변환하여 저장
            if is_heic:
                # RGB 모드로 변환 (HEIC는 RGBA일 수 있음)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # 투명 배경을 흰색으로
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # JPG로 저장 (원본 파일명 변경)
                jpg_path = image_path_obj.with_suffix('.jpg')
                img.save(jpg_path, format='JPEG', quality=90, optimize=True)
                logger.info(f"HEIC converted to JPG: {image_path_obj.name} -> {jpg_path.name} ({original_size[0]}x{original_size[1]} -> {img.width}x{img.height})")
                
                # 원본 HEIC 파일 삭제
                try:
                    image_path_obj.unlink()
                    logger.debug(f"Deleted original HEIC: {image_path_obj.name}")
                except:
                    pass
                
                return True
            else:
                # 원본 형식 유지하면서 저장
                img_format = img.format or 'JPEG'
                if img_format == 'JPEG':
                    img.save(image_path, format=img_format, quality=90, optimize=True)
                else:
                    img.save(image_path, format=img_format, optimize=True)
                
                logger.info(f"Image resized: {image_path_obj.name} ({original_size[0]}x{original_size[1]} -> {img.width}x{img.height})")
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
        List[str]: 리사이징된 이미지 경로 리스트 (실패한 것 제외, HEIC는 JPG로 변환됨)
    """
    resized_paths = []
    
    for path in image_paths:
        original_path = Path(path)
        is_heic = original_path.suffix.upper() in ['.HEIC', '.HEIF']
        
        if resize_image(path):
            # HEIC 파일은 JPG로 변환되었으므로 경로 변경
            if is_heic:
                jpg_path = original_path.with_suffix('.jpg')
                if jpg_path.exists():
                    resized_paths.append(str(jpg_path))
                else:
                    logger.warning(f"HEIC converted but JPG not found: {jpg_path}")
            else:
                resized_paths.append(path)
        else:
            logger.warning(f"Skipping failed resize: {path}")
    
    logger.info(f"Resized {len(resized_paths)}/{len(image_paths)} images")
    return resized_paths
