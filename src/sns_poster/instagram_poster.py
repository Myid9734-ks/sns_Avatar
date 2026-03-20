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
            await self.random_delay(4, 6)
            
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
            
            await self.random_delay(3, 5)
            
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
            
            await self.random_delay(5, 8)
            
            # "다음" 버튼 클릭 (자르기 화면)
            logger.info("[instagram] Clicking next (crop screen)...")
            next_clicked = await self._click_next_button()
            if not next_clicked:
                return False
            
            await self.random_delay(3, 5)
            
            # "다음" 버튼 클릭 (필터 화면)
            logger.info("[instagram] Clicking next (filter screen)...")
            next_clicked = await self._click_next_button()
            if not next_clicked:
                return False
            
            await self.random_delay(3, 5)
            
            # 캡션 입력
            logger.info("[instagram] Entering caption...")
            
            caption_selectors = [
                'div[contenteditable="true"][role="textbox"][data-lexical-editor="true"]',  # Lexical 에디터 우선
                'div[aria-label="문구를 입력하세요..."][contenteditable="true"]',
                'div[aria-label="Write a caption..."][contenteditable="true"]',
                'textarea[aria-label="문구를 입력하세요..."]',
                'textarea[aria-label="Write a caption..."]',
                'div[contenteditable="true"][role="textbox"]',
                'textarea[placeholder*="문구"]',
                'textarea[placeholder*="caption"]',
            ]
            
            caption_entered = False
            for selector in caption_selectors:
                try:
                    caption_area = await self.page.query_selector(selector)
                    if caption_area:
                        # Lexical 에디터인지 확인
                        is_lexical = await caption_area.evaluate('el => el.hasAttribute("data-lexical-editor")')
                        
                        await caption_area.click()
                        await self.random_delay(0.8, 1.2)  # 클릭 후 충분한 대기
                        
                        # 요소 타입 확인
                        tag_name = await caption_area.evaluate('el => el.tagName.toLowerCase()')
                        
                        if tag_name == 'textarea':
                            # textarea인 경우 fill 사용
                            await caption_area.fill('')  # 기존 텍스트 지우기
                            await self.random_delay(0.3, 0.5)
                            await caption_area.fill(text)
                            logger.info("[instagram] Caption entered via fill (textarea)")
                        elif is_lexical:
                            # Lexical 에디터인 경우 - 실제 키보드 타이핑 사용
                            logger.info("[instagram] Detected Lexical editor, using keyboard typing...")
                            
                            # 기존 내용 선택 및 삭제
                            await self.page.keyboard.press('Control+A')  # 전체 선택
                            await self.random_delay(0.2, 0.3)
                            await self.page.keyboard.press('Delete')  # 삭제
                            await self.random_delay(0.3, 0.5)
                            
                            # 실제 키보드 타이핑으로 텍스트 입력 (Lexical이 인식하도록)
                            await self.page.keyboard.type(text, delay=30)  # delay를 늘려서 확실하게
                            logger.info("[instagram] Caption entered via keyboard.type (Lexical)")
                            
                            # Lexical 에디터의 내부 상태 업데이트를 위한 추가 이벤트
                            await caption_area.evaluate('''
                                el => {
                                    // input 이벤트
                                    const inputEvent = new Event('input', { bubbles: true, cancelable: true });
                                    el.dispatchEvent(inputEvent);
                                    
                                    // compositionend 이벤트 (한글 입력 완료 시뮬레이션)
                                    const compositionEvent = new CompositionEvent('compositionend', { bubbles: true, cancelable: true });
                                    el.dispatchEvent(compositionEvent);
                                    
                                    // beforeinput 이벤트
                                    const beforeInputEvent = new InputEvent('beforeinput', { bubbles: true, cancelable: true, inputType: 'insertText' });
                                    el.dispatchEvent(beforeInputEvent);
                                }
                            ''')
                            await self.random_delay(0.5, 0.8)
                        else:
                            # 일반 contenteditable div인 경우
                            # innerText 설정 + 이벤트 발생
                            await caption_area.evaluate(f'''
                                el => {{
                                    el.innerText = {repr(text)};
                                    
                                    // 여러 이벤트 발생
                                    const inputEvent = new Event('input', {{ bubbles: true }});
                                    el.dispatchEvent(inputEvent);
                                    
                                    const changeEvent = new Event('change', {{ bubbles: true }});
                                    el.dispatchEvent(changeEvent);
                                }}
                            ''')
                            logger.info("[instagram] Caption entered via innerText (contenteditable)")
                            await self.random_delay(0.5, 0.8)
                        
                        caption_entered = True
                        
                        # 텍스트가 실제로 입력되었는지 확인
                        await self.random_delay(1, 1.5)  # 확인 전 충분한 대기
                        entered_text = await caption_area.evaluate('el => el.innerText || el.textContent || el.value || ""')
                        
                        # 텍스트 확인 (처음 50자 비교)
                        if entered_text and (text[:50].strip() in entered_text[:100] or entered_text[:50].strip() in text[:100]):
                            logger.info(f"[instagram] Caption verified: {len(entered_text)} chars entered")
                        else:
                            logger.warning(f"[instagram] Caption verification failed. Expected: {text[:50]}, Got: {entered_text[:50]}")
                            # 재시도: 한 번 더 키보드 타이핑
                            if is_lexical:
                                logger.info("[instagram] Retrying with keyboard typing...")
                                await caption_area.click()
                                await self.random_delay(0.5, 0.8)
                                await self.page.keyboard.press('Control+A')
                                await self.random_delay(0.2, 0.3)
                                await self.page.keyboard.type(text, delay=40)
                                await self.random_delay(1, 1.5)
                        
                        # 포커스를 잃어서 인스타그램이 텍스트를 인식하도록 함
                        await self.random_delay(0.5, 0.8)
                        try:
                            # 에디터 밖을 클릭하거나 Tab으로 포커스 이동
                            await self.page.keyboard.press('Tab')
                            await self.random_delay(0.3, 0.5)
                        except:
                            pass
                        
                        break
                except Exception as e:
                    logger.debug(f"[instagram] Failed to enter caption with {selector}: {e}")
                    continue
            
            if not caption_entered:
                logger.warning("[instagram] Could not enter caption, continuing...")
            
            # 텍스트 입력 후 충분한 대기 시간 (인스타그램이 텍스트를 처리할 시간)
            await self.random_delay(2, 3)
            
            # 공유하기 버튼이 활성화될 때까지 대기 (텍스트 입력 완료 확인)
            logger.info("[instagram] Waiting for share button to be enabled...")
            try:
                # 공유하기 버튼이 활성화될 때까지 최대 10초 대기
                await self.page.wait_for_function(
                    '''
                    () => {
                        const shareBtns = Array.from(document.querySelectorAll('div[role="button"], button'))
                            .filter(btn => {
                                const text = btn.innerText || btn.textContent || '';
                                return text.includes('공유하기') || text.includes('Share');
                            });
                        return shareBtns.length > 0 && shareBtns.some(btn => !btn.disabled && btn.offsetParent !== null);
                    }
                    ''',
                    timeout=10000
                )
                logger.info("[instagram] Share button is enabled")
            except:
                logger.warning("[instagram] Share button check timeout, proceeding anyway...")
            
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
            '[aria-label="다음"]',
            '[aria-label="Next"]',
            'span:has-text("다음")',
            'span:has-text("Next")',
        ]
        
        # 먼저 잠시 대기 (이미지 로딩)
        await self.random_delay(1, 2)
        
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
