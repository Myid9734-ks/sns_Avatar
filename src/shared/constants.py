"""전역 상수 정의"""

# 지원하는 이미지 확장자
SUPPORTED_IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp',
    '.heic', '.heif',  # Apple
    '.bmp', '.tiff', '.tif',  # 일반
    '.raw', '.cr2', '.nef', '.arw', '.dng',  # RAW
    '.svg', '.ico', '.avif'  # 기타
}

# 파일명 패턴
FILE_NAME_PREFIX = "no"

# 배치 처리
DEFAULT_BATCH_WAIT_TIME = 10  # 초
DEFAULT_MAX_BATCH_SIZE = 10

# 파일 안정성
FILE_STABILITY_TIMEOUT = 5  # 초
FILE_STABILITY_CHECK_INTERVAL = 0.5  # 초

# 캐시
CACHE_FILE_EXTENSION = ".json"
CACHE_VERSION = "1.0"

# AI 생성
AI_MAX_RETRIES = 3
AI_RETRY_DELAY = 2  # 초
AI_PROVIDERS = ['openai', 'gemini']  # 지원하는 AI 제공자

# 텔레그램
TELEGRAM_MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10MB
TELEGRAM_MESSAGE_MAX_LENGTH = 4096
