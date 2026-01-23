"""인스타그램 자동 게시 (Playwright RPA)"""
import asyncio
from typing import List
from sns_poster.base_poster import BasePoster
from shared.logger import setup_logger
from shared.config import config

logger = setup_logger(__name__)


class InstagramPoster(BasePoster):
    """인스타그램 자동 게시"""
    
    PLATFORM_NAME = "instagram"
    LOGIN_URL = "https://www.instagram.com/accounts/login/"
    HOME_URL = "https://www.instagram.com/"
    
    def __init__(self):
        super().__init__()
        self.username = config.INSTAGRAM_USERNAME
        self.password = config.INSTAGRAM_PASSWORD
    
    async def is_logged_in(self) -> bool:
        """로그인 상태 확인"""
        try:
            await self.page.goto(self.HOME_URL, wait_until='domcontentloaded')
            await self.random_delay(2, 3)
            
            # 로그인 버튼이 있으면 비로그인 상태
            login_btn = await self.page.query_selector('a[href="/accounts/login/"]')
            if login_btn:
                logger.info("[instagram] Not logged in - login button found")
                return False
            
            # 로그인 상태 확인 (다양한 셀렉터)
            logged_in_indicators = [
                '[aria-label="새로운 게시물"]',
                '[aria-label="New post"]',
                '[aria-label="홈"]',
                '[aria-label="Home"]',
                'svg[aria-label="홈"]',
                'svg[aria-label="Home"]',
                '[aria-label="프로필"]',
                '[aria-label="Profile"]',
            ]
            
            for selector in logged_in_indicators:
                element = await self.page.query_selector(selector)
                if element:
                    logger.info(f"[instagram] Logged in - found: {selector}")
                    return True
            
            # URL 기반 확인
            current_url = self.page.url
            if 'login' not in current_url.lower() and 'instagram.com' in current_url:
                # 피드가 있는지 확인
                feed = await self.page.query_selector('article')
                if feed:
                    logger.info("[instagram] Logged in - feed found")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"[instagram] Error checking login status: {e}")
            return False
    
    async def login(self, username: str = None, password: str = None) -> bool:
        """인스타그램 로그인"""
        username = username or self.username
        password = password or self.password
        
        if not username or not password:
            logger.error("[instagram] Username or password not configured")
            return False
        
        try:
            logger.info("[instagram] Starting login process...")
            
            await self.page.goto(self.LOGIN_URL, wait_until='domcontentloaded')
            await self.random_delay(2, 3)
            
            # 쿠키 배너 처리 (있는 경우)
            try:
                cookie_btns = [
                    'button:has-text("Allow")',
                    'button:has-text("허용")',
                    'button:has-text("Accept")',
                ]
                for btn_selector in cookie_btns:
                    cookie_btn = await self.page.query_selector(btn_selector)
                    if cookie_btn:
                        await cookie_btn.click()
                        await self.random_delay(1, 2)
                        break
            except:
                pass
            
            # 사용자명 입력
            logger.info("[instagram] Entering username...")
            await self.human_type('input[name="username"]', username)
            await self.random_delay(0.5, 1)
            
            # 비밀번호 입력
            logger.info("[instagram] Entering password...")
            await self.human_type('input[name="password"]', password)
            await self.random_delay(0.5, 1)
            
            # 로그인 버튼 클릭
            logger.info("[instagram] Clicking login button...")
            await self.safe_click('button[type="submit"]')
            
            # 로그인 완료 대기
            await self.random_delay(5, 8)
            
            # "정보 저장" 팝업 처리
            try:
                save_info = await self.page.query_selector('button:has-text("정보 저장")')
                if not save_info:
                    save_info = await self.page.query_selector('button:has-text("Save Info")')
                if save_info:
                    await save_info.click()
                    await self.random_delay(2, 3)
            except:
                pass
            
            # "알림 설정" 팝업 처리
            try:
                not_now_btns = [
                    'button:has-text("나중에 하기")',
                    'button:has-text("Not Now")',
                ]
                for btn_selector in not_now_btns:
                    not_now = await self.page.query_selector(btn_selector)
                    if not_now:
                        await not_now.click()
                        await self.random_delay(1, 2)
                        break
            except:
                pass
            
            # 2FA 체크
            two_fa = await self.page.query_selector('input[name="verificationCode"]')
            if two_fa:
                logger.warning("[instagram] 2FA required! Please complete manually.")
                logger.warning("[instagram] Waiting 60 seconds for manual 2FA...")
                await asyncio.sleep(60)
            
            # 로그인 성공 확인
            if await self.is_logged_in():
                logger.info("[instagram] Login successful!")
                return True
            else:
                logger.error("[instagram] Login failed - please check credentials")
                await self.take_screenshot("login_failed")
                return False
                
        except Exception as e:
            logger.error(f"[instagram] Login error: {e}")
            await self.take_screenshot("login_error")
            return False
    
    async def post(self, text: str, image_paths: List[str] = None) -> bool:
        """
        인스타그램에 게시글 작성
        
        Note: 인스타그램은 이미지 필수
        
        Args:
            text: 게시글 내용 (캡션)
            image_paths: 이미지 파일 경로 리스트 (필수)
            
        Returns:
            bool: 게시 성공 여부
        """
        if not image_paths:
            logger.error("[instagram] Image is required for Instagram posts")
            return False
        
        try:
            logger.info("[instagram] Starting post creation...")
            
            # 로그인 확인
            if not await self.ensure_logged_in():
                # 수동 로그인 대기
                if not await self.wait_for_manual_login(120):
                    logger.error("[instagram] Not logged in, cannot post")
                    return False
            
            # 홈으로 이동
            await self.page.goto(self.HOME_URL, wait_until='domcontentloaded')
            await self.random_delay(3, 5)
            
            # "새 게시물" 버튼 클릭
            logger.info("[instagram] Opening post composer...")
            
            create_btn_selectors = [
                '[aria-label="새로운 게시물"]',
                '[aria-label="New post"]',
                'svg[aria-label="새로운 게시물"]',
                'svg[aria-label="New post"]',
                'a[href="/create/select/"]',
            ]
            
            composer_opened = False
            for selector in create_btn_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.click()
                        composer_opened = True
                        logger.info(f"[instagram] Composer opened with: {selector}")
                        break
                except:
                    continue
            
            if not composer_opened:
                # 더보기 메뉴에서 찾기
                try:
                    more_btn = await self.page.query_selector('[aria-label="더 보기"]')
                    if not more_btn:
                        more_btn = await self.page.query_selector('[aria-label="More"]')
                    if more_btn:
                        await more_btn.click()
                        await self.random_delay(1, 2)
                        
                        create_option = await self.page.query_selector('span:has-text("만들기")')
                        if not create_option:
                            create_option = await self.page.query_selector('span:has-text("Create")')
                        if create_option:
                            await create_option.click()
                            composer_opened = True
                except:
                    pass
            
            if not composer_opened:
                logger.error("[instagram] Could not find create post button")
                await self.take_screenshot("composer_not_found")
                return False
            
            await self.random_delay(2, 3)
            
            # 이미지 업로드
            logger.info(f"[instagram] Uploading {len(image_paths)} image(s)...")
            
            try:
                # "컴퓨터에서 선택" 버튼이 있으면 클릭
                select_btn = await self.page.query_selector('button:has-text("컴퓨터에서 선택")')
                if not select_btn:
                    select_btn = await self.page.query_selector('button:has-text("Select from computer")')
                
                # 파일 input 찾기
                file_input = await self.page.wait_for_selector(
                    'input[type="file"][accept*="image"]',
                    state='attached',
                    timeout=10000
                )
                await file_input.set_input_files(image_paths)
                logger.info("[instagram] Images uploaded")
                
            except Exception as e:
                logger.error(f"[instagram] Image upload failed: {e}")
                await self.take_screenshot("upload_failed")
                return False
            
            await self.random_delay(3, 5)
            
            # "다음" 버튼 클릭 (자르기 화면)
            logger.info("[instagram] Clicking next (crop screen)...")
            next_clicked = await self._click_next_button()
            if not next_clicked:
                return False
            
            await self.random_delay(2, 3)
            
            # "다음" 버튼 클릭 (필터 화면)
            logger.info("[instagram] Clicking next (filter screen)...")
            next_clicked = await self._click_next_button()
            if not next_clicked:
                return False
            
            await self.random_delay(2, 3)
            
            # 캡션 입력
            logger.info("[instagram] Entering caption...")
            
            caption_selectors = [
                'textarea[aria-label="문구를 입력하세요..."]',
                'textarea[aria-label="Write a caption..."]',
                'div[aria-label="문구를 입력하세요..."]',
                'div[aria-label="Write a caption..."]',
                'textarea[placeholder*="문구"]',
                'textarea[placeholder*="caption"]',
            ]
            
            caption_entered = False
            for selector in caption_selectors:
                try:
                    caption_area = await self.page.query_selector(selector)
                    if caption_area:
                        await caption_area.click()
                        await self.random_delay(0.5, 1)
                        await self.page.keyboard.type(text, delay=20)
                        caption_entered = True
                        logger.info("[instagram] Caption entered")
                        break
                except:
                    continue
            
            if not caption_entered:
                logger.warning("[instagram] Could not enter caption, continuing...")
            
            await self.random_delay(1, 2)
            
            # "공유하기" 버튼 클릭
            logger.info("[instagram] Clicking share button...")
            
            share_btn_selectors = [
                'div[role="button"]:has-text("공유하기")',
                'div[role="button"]:has-text("Share")',
                'button:has-text("공유하기")',
                'button:has-text("Share")',
            ]
            
            shared = False
            for selector in share_btn_selectors:
                try:
                    # 모든 매칭 버튼 찾기
                    share_btns = await self.page.query_selector_all(selector)
                    # visible한 버튼들만 필터링
                    visible_btns = []
                    for btn in share_btns:
                        if await btn.is_visible():
                            visible_btns.append(btn)
                    
                    if visible_btns:
                        # 마지막 visible 버튼 클릭
                        share_btn = visible_btns[-1]
                        await self.page.evaluate('el => el.click()', share_btn)
                        shared = True
                        logger.info("[instagram] Share button clicked")
                        break
                except:
                    continue
            
            if not shared:
                logger.error("[instagram] Could not find share button")
                await self.take_screenshot("share_button_not_found")
                return False
            
            # 게시 완료 대기
            await self.random_delay(5, 10)
            
            # 완료 확인 (공유됨 메시지)
            try:
                shared_msg = await self.page.query_selector('img[alt="애니메이션 확인 표시"]')
                if not shared_msg:
                    shared_msg = await self.page.query_selector('span:has-text("게시물이 공유되었습니다")')
                if shared_msg:
                    logger.info("[instagram] Post shared successfully!")
            except:
                pass
            
            logger.info("[instagram] Post created successfully!")
            return True
            
        except Exception as e:
            logger.error(f"[instagram] Post creation failed: {e}")
            await self.take_screenshot("post_error")
            return False
    
    async def _click_next_button(self) -> bool:
        """다음 버튼 클릭 헬퍼"""
        next_btn_selectors = [
            'div[role="button"]:has-text("다음")',
            'div[role="button"]:has-text("Next")',
            'button:has-text("다음")',
            'button:has-text("Next")',
        ]
        
        for selector in next_btn_selectors:
            try:
                # 모든 매칭 버튼 찾기
                next_btns = await self.page.query_selector_all(selector)
                # visible한 버튼들만 필터링
                visible_btns = []
                for btn in next_btns:
                    if await btn.is_visible():
                        visible_btns.append(btn)
                
                if visible_btns:
                    # 마지막 visible 버튼 클릭 (모달 안의 버튼)
                    next_btn = visible_btns[-1]
                    await self.page.evaluate('el => el.click()', next_btn)
                    logger.info(f"[instagram] Next button clicked: {selector}")
                    return True
            except:
                continue
        
        logger.error("[instagram] Could not find next button")
        await self.take_screenshot("next_button_not_found")
        return False
    
    async def post_with_content(self, content: dict, image_paths: List[str]) -> bool:
        """
        content.json 데이터로 게시
        
        Args:
            content: AI가 생성한 콘텐츠 딕셔너리
            image_paths: 이미지 파일 경로 리스트 (필수)
            
        Returns:
            bool: 게시 성공 여부
        """
        # instagram_text 필드 사용, 해시태그 포함
        text = content.get('instagram_text', content.get('text', ''))
        hashtags = content.get('hashtags', [])
        
        if hashtags:
            if isinstance(hashtags, list):
                hashtags_str = ' '.join(hashtags)
            else:
                hashtags_str = hashtags
            text = f"{text}\n\n{hashtags_str}"
        
        if not text:
            logger.error("[instagram] No text content found")
            return False
        
        return await self.post(text, image_paths)
