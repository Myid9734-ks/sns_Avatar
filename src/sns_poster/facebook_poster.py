"""페이스북 자동 게시 (Playwright RPA)"""
import asyncio
from typing import List
from sns_poster.base_poster import BasePoster
from shared.logger import setup_logger
from shared.config import config

logger = setup_logger(__name__)


class FacebookPoster(BasePoster):
    """페이스북 자동 게시"""
    
    PLATFORM_NAME = "facebook"
    LOGIN_URL = "https://www.facebook.com/"
    HOME_URL = "https://www.facebook.com/"
    
    def __init__(self):
        super().__init__()
        self.email = config.FACEBOOK_EMAIL
        self.password = config.FACEBOOK_PASSWORD
    
    async def is_logged_in(self) -> bool:
        """로그인 상태 확인 (현재 페이지에서 확인, 이동하지 않음)"""
        try:
            current_url = self.page.url
            
            # 로그인 관련 페이지면 비로그인
            if 'login' in current_url.lower() or 'checkpoint' in current_url.lower():
                # 로그인 폼이 있는지 확인
                login_form = await self.page.query_selector('input[name="email"], input[name="pass"]')
                if login_form:
                    logger.info("[facebook] Not logged in - login form found")
                    return False
            
            # 프로필 아이콘이나 홈 피드가 있으면 로그인 상태
            logged_in_indicators = [
                '[aria-label="내 프로필"]',
                '[aria-label="Your profile"]',
                '[aria-label="계정"]',
                '[aria-label="Account"]',
                '[aria-label="메뉴"]',
                '[aria-label="Menu"]',
                'div[role="feed"]',
                '[data-pagelet="Stories"]',
                '[data-pagelet="LeftRail"]',
            ]
            
            for selector in logged_in_indicators:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        logger.info(f"[facebook] Logged in - found: {selector}")
                        return True
                except:
                    continue
            
            # facebook.com 홈이고 로그인 폼이 없으면 로그인 상태
            if 'facebook.com' in current_url and 'login' not in current_url.lower():
                login_form = await self.page.query_selector('input[name="email"]')
                if not login_form:
                    # 메인 콘텐츠 확인
                    main_content = await self.page.query_selector('div[role="main"]')
                    if main_content:
                        logger.info("[facebook] Logged in - main content found")
                        return True
            
            return False
            
        except Exception as e:
            logger.debug(f"[facebook] Error checking login status: {e}")
            return False
    
    async def login(self, email: str = None, password: str = None) -> bool:
        """페이스북 로그인"""
        email = email or self.email
        password = password or self.password
        
        if not email or not password:
            logger.error("[facebook] Email or password not configured")
            return False
        
        try:
            logger.info("[facebook] Starting login process...")
            
            await self.page.goto(self.LOGIN_URL, wait_until='domcontentloaded')
            await self.random_delay(2, 3)
            
            # 쿠키 배너 닫기 (있는 경우)
            try:
                cookie_btn = await self.page.query_selector('[data-cookiebanner="accept_button"]')
                if cookie_btn:
                    await cookie_btn.click()
                    await self.random_delay(1, 2)
            except:
                pass
            
            # 이메일 입력
            logger.info("[facebook] Entering email...")
            await self.human_type('input[name="email"]', email)
            await self.random_delay(0.5, 1)
            
            # 비밀번호 입력
            logger.info("[facebook] Entering password...")
            await self.human_type('input[name="pass"]', password)
            await self.random_delay(0.5, 1)
            
            # 로그인 버튼 클릭
            logger.info("[facebook] Clicking login button...")
            await self.safe_click('button[name="login"]')
            
            # 로그인 완료 대기
            await self.random_delay(5, 8)
            
            # 2FA 또는 보안 확인 체크
            # 이 경우 사용자가 수동으로 처리해야 함
            security_check = await self.page.query_selector('input[name="approvals_code"]')
            if security_check:
                logger.warning("[facebook] 2FA required! Please complete manually.")
                logger.warning("[facebook] Waiting 60 seconds for manual 2FA...")
                await asyncio.sleep(60)
            
            # 로그인 성공 확인
            if await self.is_logged_in():
                logger.info("[facebook] Login successful!")
                return True
            else:
                logger.error("[facebook] Login failed - please check credentials")
                await self.take_screenshot("login_failed")
                return False
                
        except Exception as e:
            logger.error(f"[facebook] Login error: {e}")
            await self.take_screenshot("login_error")
            return False
    
    async def post(self, text: str, image_paths: List[str] = None) -> bool:
        """
        페이스북에 게시글 작성
        
        Args:
            text: 게시글 내용
            image_paths: 이미지 파일 경로 리스트 (선택)
            
        Returns:
            bool: 게시 성공 여부
        """
        try:
            logger.info("[facebook] Starting post creation...")
            
            # 바로 페이스북 홈으로 이동 (세션 저장되어 있으므로 자동 로그인)
            logger.info("[facebook] Navigating to Facebook...")
            await self.page.goto("https://www.facebook.com/", wait_until='domcontentloaded')
            await self.random_delay(4, 6)
            
            # "무슨 생각을 하고 계신가요?" 버튼 클릭하여 글쓰기 창 열기
            logger.info("[facebook] Opening post composer...")
            
            # 다양한 셀렉터 시도 (페이스북 UI 변경 대응)
            composer_selectors = [
                '[aria-label="무슨 생각을 하고 계신가요"]',
                '[aria-label="What\'s on your mind"]',
                'div[role="button"]:has-text("무슨 생각")',
                'span:has-text("무슨 생각을 하고 계신가요")',
                '[data-pagelet="ProfileComposer"] div[role="button"]',
                'div[role="main"] div[role="button"]:first-child',
            ]
            
            composer_opened = False
            for selector in composer_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.click()
                        composer_opened = True
                        logger.info(f"[facebook] Composer opened with: {selector}")
                        break
                except:
                    continue
            
            if not composer_opened:
                logger.error("[facebook] Could not find post composer button")
                await self.take_screenshot("composer_not_found")
                return False
            
            await self.random_delay(3, 5)
            
            # ===== 순서 변경: 이미지 먼저, 텍스트 나중에 =====
            
            # 1. 이미지 업로드 (있는 경우)
            if image_paths:
                logger.info(f"[facebook] Uploading {len(image_paths)} image(s)...")
                
                # 모달 안에서 file input 직접 찾기 (버튼 클릭 없이)
                file_input = await self.page.query_selector('input[type="file"][accept*="image"]')
                
                if file_input:
                    # 숨겨진 file input에 직접 파일 설정
                    await file_input.set_input_files(image_paths)
                    logger.info("[facebook] Images uploaded via hidden input")
                else:
                    # file input이 없으면 사진/동영상 추가 버튼 클릭 후 다시 시도
                    logger.info("[facebook] Looking for photo add button...")
                    
                    add_photo_selectors = [
                        'div[role="dialog"] [aria-label*="사진/동영상 추가"]',
                        'div[role="dialog"] [aria-label*="Add photos"]',
                        '[aria-label="사진/동영상 추가"]',
                        'div:has-text("사진/동영상 추가")',
                    ]
                    
                    for selector in add_photo_selectors:
                        try:
                            add_btn = await self.page.query_selector(selector)
                            if add_btn:
                                await add_btn.click(force=True)
                                logger.info(f"[facebook] Add photo button clicked: {selector}")
                                await self.random_delay(2, 3)
                                break
                        except:
                            continue
                    
                    # 다시 file input 찾기
                    file_input = await self.page.wait_for_selector(
                        'input[type="file"]',
                        state='attached',
                        timeout=10000
                    )
                    
                    if file_input:
                        await file_input.set_input_files(image_paths)
                        logger.info("[facebook] Images uploaded")
                
                # 이미지 처리 대기
                await self.random_delay(5, 8)
            
            # 2. 텍스트 입력 (이미지 업로드 후 포커스가 텍스트 영역에 있음 - 바로 타이핑)
            logger.info("[facebook] Entering post text...")
            
            await self.page.keyboard.type(text, delay=30)
            logger.info("[facebook] Text entered successfully")
            
            await self.random_delay(1, 2)
            
            # 3. "다음" 버튼 클릭 (게시 화면으로 전환)
            logger.info("[facebook] Clicking next button...")
            
            next_btn_selectors = [
                'div[aria-label="다음"][role="button"]',
                '[aria-label="다음"]',
                'div[aria-label="Next"][role="button"]',
                '[aria-label="Next"]',
            ]
            
            next_clicked = False
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
                        next_clicked = True
                        logger.info(f"[facebook] Next button clicked (JS, last visible): {selector}")
                        break
                except:
                    continue
            
            if not next_clicked:
                logger.error("[facebook] Could not find next button")
                await self.take_screenshot("next_button_not_found")
                return False
            
            await self.random_delay(3, 5)
            
            # 게시 버튼 클릭
            logger.info("[facebook] Clicking post button...")
            
            post_btn_selectors = [
                'div[aria-label="게시"][role="button"]',
                '[aria-label="게시"]',
                'div[aria-label="Post"][role="button"]',
                '[aria-label="Post"]',
                'div[role="button"]:has-text("게시")',
                'div[role="button"]:has-text("Post")',
            ]
            
            posted = False
            for selector in post_btn_selectors:
                try:
                    # 모든 매칭 버튼 찾기
                    post_btns = await self.page.query_selector_all(selector)
                    # visible한 버튼들만 필터링
                    visible_btns = []
                    for btn in post_btns:
                        if await btn.is_visible():
                            visible_btns.append(btn)
                    
                    if visible_btns:
                        # 마지막 visible 버튼 클릭 (모달 안의 버튼)
                        post_btn = visible_btns[-1]
                        await self.page.evaluate('el => el.click()', post_btn)
                        posted = True
                        logger.info(f"[facebook] Post button clicked (JS, last visible): {selector}")
                        break
                except:
                    continue
            
            if not posted:
                logger.error("[facebook] Could not find post button")
                await self.take_screenshot("post_button_not_found")
                return False
            
            # 게시 완료 대기
            await self.random_delay(5, 8)
            
            logger.info("[facebook] Post created successfully!")
            return True
            
        except Exception as e:
            logger.error(f"[facebook] Post creation failed: {e}")
            await self.take_screenshot("post_error")
            return False
    
    async def post_with_content(self, content: dict, image_paths: List[str] = None) -> bool:
        """
        content.json 데이터로 게시
        
        Args:
            content: AI가 생성한 콘텐츠 딕셔너리
            image_paths: 이미지 파일 경로 리스트
            
        Returns:
            bool: 게시 성공 여부
        """
        # facebook_text 필드 사용
        text = content.get('facebook_text', content.get('text', ''))
        
        if not text:
            logger.error("[facebook] No text content found")
            return False
        
        return await self.post(text, image_paths)
