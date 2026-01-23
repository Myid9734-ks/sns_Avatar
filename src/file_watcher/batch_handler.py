"""배치 처리 및 파일명 변경"""
import os
import time
from pathlib import Path
from typing import List
from shared.logger import setup_logger
from shared.exceptions import FileWatcherError
from shared.constants import (
    FILE_NAME_PREFIX,
    FILE_STABILITY_TIMEOUT,
    FILE_STABILITY_CHECK_INTERVAL,
    SUPPORTED_IMAGE_EXTENSIONS
)
from shared.validators import validate_file_path

logger = setup_logger(__name__)


def validate_file_stability(file_path: str, timeout: int = FILE_STABILITY_TIMEOUT) -> bool:
    """
    파일이 안정적인지 확인 (복사 완료 대기)
    
    Args:
        file_path: 확인할 파일 경로
        timeout: 최대 대기 시간 (초)
        
    Returns:
        bool: 파일이 안정적이면 True
    """
    try:
        previous_size = -1
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if not os.path.exists(file_path):
                logger.warning(f"File disappeared during stability check: {file_path}")
                return False
                
            current_size = os.path.getsize(file_path)
            
            if current_size == previous_size and current_size > 0:
                logger.debug(f"File is stable: {Path(file_path).name}")
                return True
                
            previous_size = current_size
            time.sleep(FILE_STABILITY_CHECK_INTERVAL)
        
        logger.warning(f"File stability timeout: {Path(file_path).name}")
        return current_size > 0  # 타임아웃되었지만 파일 크기가 있으면 True
        
    except Exception as e:
        logger.error(f"Error checking file stability: {e}")
        return False


def is_image_file(file_path: str) -> bool:
    """
    이미지 파일인지 확인
    
    Args:
        file_path: 확인할 파일 경로
        
    Returns:
        bool: 이미지 파일이면 True
    """
    extension = Path(file_path).suffix.lower()
    return extension in SUPPORTED_IMAGE_EXTENSIONS


def get_file_extension(file_path: str) -> str:
    """
    파일 확장자 추출
    
    Args:
        file_path: 파일 경로
        
    Returns:
        str: 확장자 (예: '.jpg')
    """
    return Path(file_path).suffix


def generate_sequential_name(index: int, extension: str) -> str:
    """
    순차적 파일명 생성
    
    Args:
        index: 순서 번호 (1부터 시작)
        extension: 파일 확장자
        
    Returns:
        str: 생성된 파일명 (예: 'no1.jpg')
    """
    return f"{FILE_NAME_PREFIX}{index}{extension}"


def rename_single_file(old_path: str, new_path: str) -> bool:
    """
    단일 파일 이름 변경
    
    Args:
        old_path: 원본 파일 경로
        new_path: 새 파일 경로
        
    Returns:
        bool: 성공 여부
        
    Raises:
        FileWatcherError: 파일명 변경 실패 시
    """
    try:
        if not os.path.exists(old_path):
            raise FileWatcherError(f"File not found: {old_path}")
            
        if os.path.exists(new_path):
            raise FileWatcherError(f"Target file already exists: {new_path}")
        
        os.rename(old_path, new_path)
        logger.info(f"Renamed: {Path(old_path).name} -> {Path(new_path).name}")
        return True
        
    except FileWatcherError:
        raise
    except Exception as e:
        logger.error(f"Failed to rename file: {e}")
        raise FileWatcherError(f"Rename failed: {e}")


def rename_batch_files(file_paths: List[str]) -> List[str]:
    """
    배치 파일들의 이름을 순차적으로 변경
    
    Args:
        file_paths: 원본 파일 경로 리스트
        
    Returns:
        List[str]: 변경된 파일 경로 리스트
        
    Raises:
        FileWatcherError: 파일명 변경 실패 시
    """
    renamed_paths = []
    
    try:
        logger.info(f"Starting batch rename for {len(file_paths)} files")
        
        for index, file_path in enumerate(file_paths, start=1):
            try:
                # 파일 존재 확인
                if not os.path.exists(file_path):
                    logger.warning(f"File not found, skipping: {file_path}")
                    continue
                
                # 확장자 추출
                directory = os.path.dirname(file_path)
                extension = get_file_extension(file_path)
                
                # 새 파일명 생성
                new_name = generate_sequential_name(index, extension)
                new_path = os.path.join(directory, new_name)
                
                # 중복 확인
                if os.path.exists(new_path):
                    logger.warning(f"File already exists: {new_name}, skipping")
                    renamed_paths.append(file_path)
                    continue
                
                # 파일명 변경
                rename_single_file(file_path, new_path)
                renamed_paths.append(new_path)
                
            except FileWatcherError as e:
                logger.error(f"Error renaming {Path(file_path).name}: {e}")
                # 에러가 발생해도 계속 진행
                renamed_paths.append(file_path)
        
        logger.info(f"Batch rename completed: {len(renamed_paths)} files")
        return renamed_paths
        
    except Exception as e:
        logger.error(f"Unexpected error in rename_batch_files: {e}", exc_info=True)
        raise FileWatcherError(f"Batch rename failed: {e}")


def collect_existing_images(watch_folder: str) -> List[str]:
    """
    감시 폴더에 있는 기존 이미지 파일들을 수집
    
    Args:
        watch_folder: 감시할 폴더 경로
        
    Returns:
        List[str]: 이미지 파일 경로 리스트
    """
    image_files = []
    
    try:
        watch_path = Path(watch_folder)
        
        if not watch_path.exists():
            logger.error(f"Watch folder does not exist: {watch_folder}")
            return []
        
        # 폴더 내 모든 파일 검사
        for file_path in watch_path.iterdir():
            if file_path.is_file() and is_image_file(str(file_path)):
                image_files.append(str(file_path))
        
        logger.info(f"Found {len(image_files)} existing image(s) in {watch_folder}")
        return sorted(image_files)  # 정렬하여 일관된 순서 보장
        
    except Exception as e:
        logger.error(f"Error collecting existing images: {e}")
        return []
