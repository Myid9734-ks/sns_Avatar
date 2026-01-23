"""SNS 게시 베이스 클래스"""
import asyncio
import random
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from shared.logger import setup_logger
from shared.config import config

logger = setup_logger(__name__)


class BasePoster(ABC):
    """SNS 게시 베이스 클래스 (Playwright RPA)"""
    
    # 서브클래스에서 오버라이드
    PLATFORM_NAME: str = "base"
    LOGIN_URL: str = ""
    
    def __init__(self):
        """초기화"""
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.playwright = None
        
        # 브라우저 데이터 디렉토리 (세션 유지용) - 절대 경로로 설정
        browser_data_path = config.BROWSER_DATA_DIR
        if not Path(browser_data_path).is_absolute():
            # 상대 경로면 프로젝트 루트 기준으로 변환
            project_root = Path(__file__).parent.parent.parent
            browser_data_path = project_root / browser_data_path
        
        self.user_data_dir = Path(browser_data_path) / self.PLATFORM_NAME
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"{self.PLATFORM_NAME} Poster initialized")
    
    async def start_browser(self):
        """브라우저 시작 (persistent context로 세션 유지)"""
        try:
            logger.info(f"[{self.PLATFORM_NAME}] Starting browser...")
            
            self.playwright = await async_playwright().start()
            
            # Persistent context 사용 (쿠키, 로컬스토리지 자동 저장)
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=config.BROWSER_HEADLESS,
                slow_mo=config.RPA_SLOW_MO,
                viewport={'width': 1280, 'height': 800},
                locale='ko-KR',
                timezone_id='Asia/Seoul',
                # 탐지 우회 설정
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                ]
            )
            
            # 첫 번째 페이지 사용 또는 새 페이지 생성
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()
            
            logger.info(f"[{self.PLATFORM_NAME}] Browser started successfully")
            
        except Exception as e:
            logger.error(f"[{self.PLATFORM_NAME}] Failed to start browser: {e}")
            raise
    
    async def close_browser(self):
        """브라우저 종료"""
        try:
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info(f"[{self.PLATFORM_NAME}] Browser closed")
        except Exception as e:
            logger.error(f"[{self.PLATFORM_NAME}] Error closing browser: {e}")
    
    async def random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """랜덤 딜레이 (봇 탐지 우회)"""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)
    
    async def human_type(self, selector: str, text: str, delay_per_char: int = 50):
        """사람처럼 타이핑 (글자별 딜레이)"""
        element = await self.page.wait_for_selector(selector, timeout=10000)
        await element.click()
        await self.random_delay(0.3, 0.7)
        
        for char in text:
            await self.page.keyboard.type(char, delay=delay_per_char + random.randint(-20, 20))
    
    async def is_logged_in(self) -> bool:
        """로그인 상태 확인 (서브클래스에서 구현)"""
        raise NotImplementedError
    
    @abstractmethod
    async def login(self, email: str, password: str) -> bool:
        """로그인 (서브클래스에서 구현)"""
        pass
    
    @abstractmethod
    async def post(self, text: str, image_paths: List[str] = None) -> bool:
        """게시글 작성 (서브클래스에서 구현)"""
        pass
    
    async def ensure_logged_in(self) -> bool:
        """
        로그인 상태 확인 (세션 기반)
        
        첫 실행 시 수동 로그인 필요 → 이후 세션 자동 유지
        
        Returns:
            bool: 로그인 상태 여부
        """
        try:
            # 로그인 상태 확인
            if await self.is_logged_in():
                logger.info(f"[{self.PLATFORM_NAME}] Already logged in (session restored)")
                return True
            
            # 로그인 안됨 → 수동 로그인 안내
            logger.warning(f"[{self.PLATFORM_NAME}] Not logged in!")
            logger.warning(f"[{self.PLATFORM_NAME}] Please login manually in the browser.")
            return False
            
        except Exception as e:
            logger.error(f"[{self.PLATFORM_NAME}] Login check failed: {e}")
            return False
    
    async def wait_for_manual_login(self, timeout: int = 120) -> bool:
        """
        수동 로그인 대기
        
        Args:
            timeout: 대기 시간 (초)
            
        Returns:
            bool: 로그인 성공 여부
        """
        import time
        
        logger.info(f"[{self.PLATFORM_NAME}] Waiting for manual login... ({timeout}s)")
        print(f"\n[{self.PLATFORM_NAME.upper()}] 브라우저에서 직접 로그인하세요!")
        print(f"[{self.PLATFORM_NAME.upper()}] {timeout}초 안에 로그인을 완료해주세요.\n")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 페이지 로딩 완료 대기
                await self.page.wait_for_load_state('domcontentloaded', timeout=5000)
                await asyncio.sleep(2)  # 페이지 안정화 대기
                
                if await self.is_logged_in():
                    logger.info(f"[{self.PLATFORM_NAME}] Manual login successful!")
                    print(f"\n[{self.PLATFORM_NAME.upper()}] 로그인 성공! 세션이 저장되었습니다.")
                    return True
                    
            except Exception as e:
                # 페이지 전환 중 오류는 무시 (새로고침, 리다이렉트 등)
                logger.debug(f"[{self.PLATFORM_NAME}] Page transition: {e}")
                
            await asyncio.sleep(3)  # 3초마다 확인
        
        logger.error(f"[{self.PLATFORM_NAME}] Login timeout")
        return False
    
    async def upload_images(self, file_input_selector: str, image_paths: List[str]):
        """
        이미지 업로드
        
        Args:
            file_input_selector: 파일 input 셀렉터
            image_paths: 업로드할 이미지 경로 리스트
        """
        if not image_paths:
            return
        
        try:
            # 파일 input 요소 찾기
            file_input = await self.page.wait_for_selector(
                file_input_selector, 
                state='attached',
                timeout=10000
            )
            
            # 이미지 파일 업로드
            await file_input.set_input_files(image_paths)
            logger.info(f"[{self.PLATFORM_NAME}] Uploaded {len(image_paths)} image(s)")
            
            await self.random_delay(2, 4)  # 업로드 대기
            
        except Exception as e:
            logger.error(f"[{self.PLATFORM_NAME}] Failed to upload images: {e}")
            raise
    
    async def safe_click(self, selector: str, timeout: int = 10000):
        """안전한 클릭 (요소 대기 후 클릭)"""
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            await self.random_delay(0.3, 0.8)
            await element.click()
            return True
        except Exception as e:
            logger.error(f"[{self.PLATFORM_NAME}] Click failed for {selector}: {e}")
            return False
    
    async def take_screenshot(self, name: str = "screenshot"):
        """디버깅용 스크린샷"""
        screenshot_dir = Path(config.LOG_FOLDER) / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        path = screenshot_dir / f"{self.PLATFORM_NAME}_{name}.png"
        await self.page.screenshot(path=str(path))
        logger.debug(f"[{self.PLATFORM_NAME}] Screenshot saved: {path}")
