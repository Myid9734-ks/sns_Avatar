"""유틸리티 함수 모음"""
import hashlib
import json
from pathlib import Path
from typing import Any
from shared.logger import setup_logger

logger = setup_logger(__name__)


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
