"""로깅 설정"""
import logging
from pathlib import Path
import sys


def setup_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """
    로거 설정 (Single Source of Truth)
    
    Args:
        name: 로거 이름
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        logging.Logger: 설정된 로거
    """
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 있으면 재설정하지 않음
    if logger.handlers:
        return logger
    
    # 로그 레벨 설정
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # 파일 핸들러
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(
        log_dir / f"{name}.log",
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 포맷터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger
