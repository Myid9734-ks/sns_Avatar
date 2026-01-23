"""설정 관리 (Singleton Pattern)"""
from dotenv import load_dotenv
import os
from pathlib import Path
from shared.exceptions import ConfigurationError


class Config:
    """애플리케이션 전역 설정 (Single Source of Truth)"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # .env 파일 로드
        env_path = Path(__file__).parent.parent.parent / '.env'
        load_dotenv(env_path)
        
        # 파일 경로 설정
        self.WATCH_FOLDER = os.getenv('WATCH_FOLDER_PATH')
        self.CACHE_FOLDER = os.getenv('CACHE_FOLDER_PATH', './cache')
        self.LOG_FOLDER = os.getenv('LOG_FOLDER_PATH', './logs')
        
        # 텔레그램 설정
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
        
        # AI 설정
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        self.OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')
        self.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
        self.GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-pro')
        self.AI_PROVIDER = os.getenv('AI_PROVIDER', 'openai')  # 'openai' or 'gemini'
        
        # 배치 설정
        self.BATCH_WAIT_TIME = int(os.getenv('BATCH_WAIT_TIME', 10))
        self.MAX_BATCH_SIZE = int(os.getenv('MAX_BATCH_SIZE', 10))
        
        # 파일 안정성 설정
        self.FILE_STABILITY_TIMEOUT = int(os.getenv('FILE_STABILITY_TIMEOUT', 5))
        
        # 기타 설정
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        
        # SNS 계정 설정 (RPA용)
        self.FACEBOOK_EMAIL = os.getenv('FACEBOOK_EMAIL')
        self.FACEBOOK_PASSWORD = os.getenv('FACEBOOK_PASSWORD')
        self.INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
        self.INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')
        
        # RPA 브라우저 설정
        self.BROWSER_HEADLESS = os.getenv('BROWSER_HEADLESS', 'false').lower() == 'true'
        self.BROWSER_DATA_DIR = os.getenv('BROWSER_DATA_DIR', './browser_data')
        self.RPA_SLOW_MO = int(os.getenv('RPA_SLOW_MO', 100))  # 동작 간 딜레이(ms)
        
        self._initialized = True
    
    def validate(self):
        """필수 설정 검증"""
        required = {
            'WATCH_FOLDER': self.WATCH_FOLDER,
            'TELEGRAM_BOT_TOKEN': self.TELEGRAM_BOT_TOKEN,
            'TELEGRAM_CHAT_ID': self.TELEGRAM_CHAT_ID,
        }
        
        missing = [key for key, value in required.items() if not value]
        
        if missing:
            raise ConfigurationError(
                f"Missing required configuration: {', '.join(missing)}\n"
                f"Please check your .env file."
            )
        
        # 경로 존재 확인
        if not Path(self.WATCH_FOLDER).exists():
            raise ConfigurationError(
                f"Watch folder does not exist: {self.WATCH_FOLDER}"
            )


# 싱글톤 인스턴스
config = Config()
