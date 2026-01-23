"""검증 함수 모음"""
from pathlib import Path
from shared.constants import SUPPORTED_IMAGE_EXTENSIONS


def validate_file_path(file_path: str) -> bool:
    """
    파일 경로 유효성 검증
    
    Args:
        file_path: 확인할 파일 경로
        
    Returns:
        bool: 파일이 존재하고 유효하면 True
    """
    try:
        path = Path(file_path)
        return path.exists() and path.is_file()
    except Exception:
        return False


def validate_image_file(file_path: str) -> bool:
    """
    이미지 파일 유효성 검증
    
    Args:
        file_path: 확인할 파일 경로
        
    Returns:
        bool: 이미지 파일이면 True
    """
    if not validate_file_path(file_path):
        return False
    
    extension = Path(file_path).suffix.lower()
    return extension in SUPPORTED_IMAGE_EXTENSIONS


def validate_directory(dir_path: str) -> bool:
    """
    디렉토리 유효성 검증
    
    Args:
        dir_path: 확인할 디렉토리 경로
        
    Returns:
        bool: 디렉토리가 존재하면 True
    """
    try:
        path = Path(dir_path)
        return path.exists() and path.is_dir()
    except Exception:
        return False


def validate_batch_size(size: int, max_size: int) -> bool:
    """
    배치 크기 유효성 검증
    
    Args:
        size: 현재 배치 크기
        max_size: 최대 배치 크기
        
    Returns:
        bool: 유효한 크기면 True
    """
    return 0 < size <= max_size
