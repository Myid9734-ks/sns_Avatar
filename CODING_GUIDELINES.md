# 코딩 가이드라인

## 📐 핵심 원칙

### 1. 패턴을 지키라 (Follow Patterns)

#### 디렉토리 구조 패턴
```
SNS Avatar/
├── src/
│   ├── main.py                 # 애플리케이션 엔트리 포인트
│   ├── shared/                 # 공통 모듈 (원칙 6 참고)
│   │   ├── __init__.py
│   │   ├── config.py           # 설정 관리 (원칙 2, 3)
│   │   ├── logger.py           # 로깅 설정 (원칙 2)
│   │   ├── exceptions.py       # 커스텀 예외 클래스
│   │   └── utils.py            # 유틸리티 함수
│   ├── file_watcher/
│   │   ├── __init__.py
│   │   ├── watcher.py          # 파일 감시 로직
│   │   └── batch_handler.py    # 배치 처리 로직
│   ├── telegram/
│   │   ├── __init__.py
│   │   ├── bot.py              # 텔레그램 봇 메인
│   │   └── handlers.py         # 메시지 핸들러
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── generator.py        # AI 초안 생성
│   │   └── cache_manager.py    # 캐시 관리
│   └── sns/
│       ├── __init__.py
│       └── publisher.py        # SNS 게시 로직
├── .env                        # 환경 변수 (git 제외)
├── .env.example                # 환경 변수 템플릿
├── requirements.txt            # 의존성 패키지
├── 개발계획서.md
└── CODING_GUIDELINES.md        # 이 문서
```

#### 네이밍 패턴
- **파일명**: `snake_case.py`
- **클래스명**: `PascalCase`
- **함수/변수명**: `snake_case`
- **상수명**: `UPPER_SNAKE_CASE`
- **환경변수명**: `UPPER_SNAKE_CASE`

```python
# Good
class ImageProcessor:
    MAX_BATCH_SIZE = 10
    
    def process_image_batch(self, file_paths):
        pass

# Bad
class imageProcessor:
    maxBatchSize = 10
    
    def ProcessImageBatch(self, filePaths):
        pass
```

---

### 2. One Source of Truth (단일 진실 공급원)

**원칙**: 모든 설정과 상태는 단 하나의 출처에서만 관리한다.

#### ✅ Good: 중앙 집중식 설정 관리

```python
# shared/config.py
from dotenv import load_dotenv
import os

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
            
        load_dotenv()
        
        # 파일 경로 설정
        self.WATCH_FOLDER = os.getenv('WATCH_FOLDER_PATH')
        self.CACHE_FOLDER = os.getenv('CACHE_FOLDER_PATH', './cache')
        
        # 텔레그램 설정
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
        
        # AI 설정
        self.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
        self.GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-pro')
        
        # 배치 설정
        self.BATCH_WAIT_TIME = int(os.getenv('BATCH_WAIT_TIME', 10))
        self.MAX_BATCH_SIZE = int(os.getenv('MAX_BATCH_SIZE', 10))
        
        self._initialized = True
    
    def validate(self):
        """필수 설정 검증"""
        required = [
            'WATCH_FOLDER',
            'TELEGRAM_BOT_TOKEN',
            'GEMINI_API_KEY'
        ]
        
        missing = [key for key in required if not getattr(self, key)]
        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")

# 사용
config = Config()
```

```python
# 다른 모듈에서 사용
from shared.config import config

watch_path = config.WATCH_FOLDER  # ✅ Good
```

#### ❌ Bad: 중복된 설정

```python
# file_watcher/watcher.py
WATCH_FOLDER = "V:\\n8n_test"  # ❌ Bad: 하드코딩

# telegram/bot.py
WATCH_FOLDER = "V:\\n8n_test"  # ❌ Bad: 중복된 설정
```

---

### 3. 하드코딩 하지 말자 (No Hard-Coding)

**원칙**: 모든 설정값은 환경변수나 설정 파일에서 읽어온다.

#### ✅ Good: 환경변수 사용

```python
# .env 파일
WATCH_FOLDER_PATH=V:\n8n_test
BATCH_WAIT_TIME=10
MAX_BATCH_SIZE=10
TELEGRAM_BOT_TOKEN=your_bot_token_here
GEMINI_API_KEY=your_api_key_here
```

```python
# 코드
from shared.config import config

def start_watching():
    folder = config.WATCH_FOLDER  # ✅ Good
    wait_time = config.BATCH_WAIT_TIME  # ✅ Good
```

#### ❌ Bad: 하드코딩

```python
def start_watching():
    folder = "V:\\n8n_test"  # ❌ Bad
    wait_time = 10  # ❌ Bad
    api_key = "AIzaSyC..."  # ❌ Bad: 보안 위험!
```

#### 예외: 비즈니스 로직 상수는 코드에 정의 가능

```python
# 이런 것들은 코드에 정의해도 OK
SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
FILE_NAME_PREFIX = "no"
MIN_FILE_SIZE = 1024  # bytes
```

---

### 4. 에러처리를 잘하자 (Proper Error Handling)

**원칙**: 예상 가능한 모든 에러를 처리하고, 명확한 로깅을 남긴다.

#### 커스텀 예외 정의

```python
# shared/exceptions.py
class SNSAvatarException(Exception):
    """기본 예외 클래스"""
    pass

class FileWatcherError(SNSAvatarException):
    """파일 감시 관련 에러"""
    pass

class TelegramError(SNSAvatarException):
    """텔레그램 봇 관련 에러"""
    pass

class AIGenerationError(SNSAvatarException):
    """AI 생성 관련 에러"""
    pass

class ConfigurationError(SNSAvatarException):
    """설정 관련 에러"""
    pass
```

#### ✅ Good: 구체적인 에러 처리

```python
# shared/logger.py
import logging
from pathlib import Path

def setup_logger(name: str) -> logging.Logger:
    """로거 설정 (Single Source of Truth)"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
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
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger
```

```python
# file_watcher/batch_handler.py
from shared.logger import setup_logger
from shared.exceptions import FileWatcherError
import os

logger = setup_logger(__name__)

def rename_batch_files(file_paths: list[str]) -> list[str]:
    """
    배치 파일들의 이름을 순차적으로 변경
    
    Args:
        file_paths: 원본 파일 경로 리스트
        
    Returns:
        list[str]: 변경된 파일 경로 리스트
        
    Raises:
        FileWatcherError: 파일명 변경 실패 시
    """
    renamed_paths = []
    
    try:
        for index, file_path in enumerate(file_paths, start=1):
            try:
                # 파일 존재 확인
                if not os.path.exists(file_path):
                    logger.warning(f"File not found: {file_path}")
                    continue
                
                # 확장자 추출
                directory = os.path.dirname(file_path)
                extension = os.path.splitext(file_path)[1]
                
                # 새 파일명 생성
                new_name = f"no{index}{extension}"
                new_path = os.path.join(directory, new_name)
                
                # 중복 확인
                if os.path.exists(new_path):
                    logger.warning(f"File already exists: {new_path}, skipping")
                    renamed_paths.append(file_path)
                    continue
                
                # 파일명 변경
                os.rename(file_path, new_path)
                renamed_paths.append(new_path)
                logger.info(f"Renamed: {os.path.basename(file_path)} -> {new_name}")
                
            except PermissionError as e:
                logger.error(f"Permission denied: {file_path} - {e}")
                raise FileWatcherError(f"Cannot rename {file_path}: Permission denied")
                
            except OSError as e:
                logger.error(f"OS error while renaming {file_path}: {e}")
                raise FileWatcherError(f"Cannot rename {file_path}: {e}")
        
        return renamed_paths
        
    except Exception as e:
        logger.error(f"Unexpected error in rename_batch_files: {e}", exc_info=True)
        raise FileWatcherError(f"Batch rename failed: {e}")
```

#### ❌ Bad: 에러 무시 또는 불충분한 처리

```python
def rename_files(files):
    try:
        for f in files:
            os.rename(f, "new_name")  # ❌ Bad: 구체적이지 않음
    except:  # ❌ Bad: 모든 예외를 무시
        pass
```

---

### 5. 함수는 한 가지 책임만 가진다 (Single Responsibility)

**원칙**: 하나의 함수는 하나의 작업만 수행한다.

#### ✅ Good: 책임 분리

```python
# file_watcher/batch_handler.py
from pathlib import Path
from shared.logger import setup_logger

logger = setup_logger(__name__)

def validate_file_stability(file_path: str, timeout: int = 5) -> bool:
    """
    파일이 안정적인지 확인 (복사 완료 대기)
    
    Args:
        file_path: 확인할 파일 경로
        timeout: 최대 대기 시간 (초)
        
    Returns:
        bool: 파일이 안정적이면 True
    """
    import time
    
    try:
        previous_size = -1
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if not os.path.exists(file_path):
                return False
                
            current_size = os.path.getsize(file_path)
            
            if current_size == previous_size and current_size > 0:
                logger.debug(f"File is stable: {file_path}")
                return True
                
            previous_size = current_size
            time.sleep(0.5)
        
        logger.warning(f"File stability timeout: {file_path}")
        return False
        
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
    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    extension = Path(file_path).suffix.lower()
    return extension in SUPPORTED_EXTENSIONS


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
    return f"no{index}{extension}"


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
        
    except Exception as e:
        logger.error(f"Failed to rename file: {e}")
        raise FileWatcherError(f"Rename failed: {e}")
```

#### ❌ Bad: 여러 책임을 가진 함수

```python
def process_files(files):
    """❌ Bad: 여러 책임이 섞여 있음"""
    # 파일 검증
    valid_files = []
    for f in files:
        if f.endswith('.jpg'):
            valid_files.append(f)
    
    # 파일명 변경
    renamed = []
    for i, f in enumerate(valid_files):
        new_name = f"no{i}.jpg"
        os.rename(f, new_name)
        renamed.append(new_name)
    
    # 텔레그램 전송
    for f in renamed:
        send_telegram(f)
    
    # AI 생성
    ai_result = generate_ai_content(renamed)
    
    return ai_result
```

---

### 6. Shared 폴더 관리를 잘하자 (Shared Module Management)

**원칙**: 공통으로 사용되는 코드는 `shared/` 폴더에 모듈화하여 관리한다.

#### Shared 폴더 구조

```
src/shared/
├── __init__.py           # 공통 임포트
├── config.py             # 설정 관리 (Singleton)
├── logger.py             # 로깅 설정
├── exceptions.py         # 커스텀 예외
├── utils.py              # 유틸리티 함수
├── validators.py         # 검증 함수
└── constants.py          # 전역 상수
```

#### shared/constants.py

```python
"""전역 상수 정의"""

# 지원하는 이미지 확장자
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

# 파일명 패턴
FILE_NAME_PREFIX = "no"
FILE_NAME_PATTERN = r"^no\d+\.(jpg|jpeg|png|gif|webp)$"

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

# 텔레그램
TELEGRAM_MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10MB
TELEGRAM_MESSAGE_MAX_LENGTH = 4096
```

#### shared/validators.py

```python
"""검증 함수 모음"""
from pathlib import Path
from shared.constants import SUPPORTED_IMAGE_EXTENSIONS
from shared.logger import setup_logger

logger = setup_logger(__name__)


def validate_file_path(file_path: str) -> bool:
    """파일 경로 유효성 검증"""
    try:
        path = Path(file_path)
        return path.exists() and path.is_file()
    except Exception as e:
        logger.error(f"Invalid file path: {e}")
        return False


def validate_image_file(file_path: str) -> bool:
    """이미지 파일 유효성 검증"""
    if not validate_file_path(file_path):
        return False
    
    extension = Path(file_path).suffix.lower()
    return extension in SUPPORTED_IMAGE_EXTENSIONS


def validate_directory(dir_path: str) -> bool:
    """디렉토리 유효성 검증"""
    try:
        path = Path(dir_path)
        return path.exists() and path.is_dir()
    except Exception as e:
        logger.error(f"Invalid directory path: {e}")
        return False


def validate_batch_size(size: int, max_size: int) -> bool:
    """배치 크기 유효성 검증"""
    return 0 < size <= max_size
```

#### shared/utils.py

```python
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
        logger.error(f"Failed to calculate hash: {e}")
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
        logger.error(f"Failed to create directory: {e}")
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
        logger.error(f"Failed to save JSON: {e}")
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
        logger.error(f"Invalid JSON format: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load JSON: {e}")
        return None
```

#### shared/__init__.py

```python
"""Shared 모듈 - 공통 기능"""

from shared.config import Config, config
from shared.logger import setup_logger
from shared.exceptions import (
    SNSAvatarException,
    FileWatcherError,
    TelegramError,
    AIGenerationError,
    ConfigurationError
)

__all__ = [
    'Config',
    'config',
    'setup_logger',
    'SNSAvatarException',
    'FileWatcherError',
    'TelegramError',
    'AIGenerationError',
    'ConfigurationError',
]
```

#### ✅ Good: Shared 모듈 사용

```python
# 다른 모듈에서 사용
from shared import config, setup_logger
from shared.exceptions import FileWatcherError
from shared.validators import validate_image_file
from shared.utils import calculate_file_hash

logger = setup_logger(__name__)

def process_image(file_path: str):
    # 검증
    if not validate_image_file(file_path):
        raise FileWatcherError("Invalid image file")
    
    # 설정 사용
    cache_dir = config.CACHE_FOLDER
    
    # 유틸리티 사용
    file_hash = calculate_file_hash(file_path)
    
    logger.info(f"Processing: {file_path}")
```

---

## 📋 체크리스트

새로운 기능을 추가할 때 다음을 확인하세요:

- [ ] 적절한 디렉토리 구조에 배치되었는가?
- [ ] 하드코딩된 값이 없는가? (환경변수 사용)
- [ ] 설정이 `config.py`에 중앙화되어 있는가?
- [ ] 적절한 에러 처리와 로깅이 있는가?
- [ ] 각 함수가 하나의 책임만 가지는가?
- [ ] 공통 기능은 `shared/`에 모듈화되어 있는가?
- [ ] 커스텀 예외를 사용하는가?
- [ ] 함수에 docstring이 작성되어 있는가?
- [ ] 타입 힌트가 추가되어 있는가?

---

## 🔄 코드 리뷰 시 확인사항

1. **패턴 준수**: 네이밍, 디렉토리 구조가 일관적인가?
2. **중복 제거**: 같은 설정/로직이 여러 곳에 있지 않은가?
3. **하드코딩**: 매직 넘버나 고정 경로가 없는가?
4. **에러 처리**: try-except가 적절하고, 로깅이 충분한가?
5. **함수 크기**: 함수가 너무 크지 않은가? (50줄 이하 권장)
6. **재사용성**: 공통 로직이 `shared/`로 분리되었는가?

---

**마지막 업데이트**: 2026-01-22
