"""텔레그램 메시지 핸들러"""
import os
from typing import Dict, List, Callable
from threading import Lock
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from shared.logger import setup_logger
from shared.config import config
from shared.utils import resize_images

logger = setup_logger(__name__)


class TelegramHandlers:
    """텔레그램 봇 핸들러 모음"""
    
    def __init__(self):
        """초기화"""
        # 배치별 대기 상태 저장
        # {batch_id: {'files': [...], 'state': 'waiting_for_choice', 'context': None}}
        self.batch_states: Dict[str, Dict] = {}
        self.current_batch_id: str | None = None
        self.batch_lock = Lock()  # 배치 생성 동기화
        self.content_generator = None  # 지연 초기화
        self.bot_instance = None  # 봇 인스턴스 저장
        self.file_watcher = None  # FileWatcher 참조 (감시 재개용)
        self.chat_id = config.TELEGRAM_CHAT_ID
        logger.info("TelegramHandlers initialized")
    
    def set_file_watcher(self, file_watcher):
        """FileWatcher 참조 설정"""
        self.file_watcher = file_watcher
        logger.info("FileWatcher reference set in handlers")
    
    def _get_content_generator(self):
        """ContentGenerator 지연 초기화"""
        if self.content_generator is None:
            from ai_generator.content_generator import ContentGenerator
            self.content_generator = ContentGenerator()
        return self.content_generator
    
    async def send_context_request(
        self,
        bot,
        chat_id: str,
        file_paths: List[str]
    ) -> str:
        """
        사용자에게 컨텍스트 입력 요청 전송 (이미지 그룹으로)
        
        Args:
            bot: 텔레그램 봇 인스턴스
            chat_id: 채팅 ID
            file_paths: 이미지 파일 경로 리스트
            
        Returns:
            str: 배치 ID
        """
        # 이미지 리사이징 (1080px로 최적화)
        logger.info(f"Resizing {len(file_paths)} image(s) for optimization...")
        file_paths = resize_images(file_paths)
        
        if not file_paths:
            logger.error("No valid images after resizing")
            raise ValueError("No valid images to process")
        
        # Lock으로 batch_id 생성 및 체크 보호
        with self.batch_lock:
            # 파일 경로를 기반으로 고유한 batch_id 생성 (중복 방지)
            import hashlib
            file_signature = '|'.join(sorted(file_paths))
            batch_hash = hashlib.md5(file_signature.encode()).hexdigest()[:8]
            batch_id = f"batch_{batch_hash}"
            
            # 이미 처리 중인 배치면 무시
            if batch_id in self.batch_states:
                logger.warning(f"Batch already exists, skipping duplicate: {batch_id}")
                return batch_id
            
            # 배치 상태 즉시 생성 (다른 호출이 중복 체크를 통과하지 못하도록)
            self.batch_states[batch_id] = {
                'files': file_paths,
                'state': 'waiting_for_choice',
                'context': None
            }
        
        try:
            file_count = len(file_paths)
            
            logger.info(f"Sending context request for {file_count} file(s) [batch_id: {batch_id}]")
            
            self.current_batch_id = batch_id
            
            # 이미지들을 Media Group으로 전송
            from telegram import InputMediaPhoto
            
            media_group = []
            for idx, file_path in enumerate(file_paths):
                with open(file_path, 'rb') as photo:
                    # 첫 번째 이미지에만 캡션 추가
                    caption = f"📸 새 이미지 {file_count}개 감지" if idx == 0 else None
                    media_group.append(
                        InputMediaPhoto(media=photo.read(), caption=caption)
                    )
            
            # 미디어 그룹 전송
            await bot.send_media_group(
                chat_id=chat_id,
                media=media_group
            )
            
            # 버튼 생성
            keyboard = [
                [InlineKeyboardButton("✍️ 정보 추가하기", callback_data=f"{batch_id}:add_context")],
                [InlineKeyboardButton("🤖 이미지로만 생성", callback_data=f"{batch_id}:no_context")],
                [
                    InlineKeyboardButton("🔄 재스캔", callback_data=f"{batch_id}:rescan"),
                    InlineKeyboardButton("🚫 중단", callback_data=f"{batch_id}:cancel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # 메시지 전송 (버튼 포함)
            await bot.send_message(
                chat_id=chat_id,
                text=f"🔔 새 이미지 {file_count}개가 감지되었습니다.\n\n"
                     f"이미지 개수가 맞지 않으면 '재스캔'을 눌러주세요.\n"
                     f"게시글을 생성할까요?",
                reply_markup=reply_markup
            )
            
            logger.info(f"Context request sent successfully [batch_id: {batch_id}]")
            return batch_id
            
        except Exception as e:
            logger.error(f"Failed to send context request: {e}", exc_info=True)
            raise
    
    async def handle_button_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """
        인라인 버튼 클릭 처리
        
        Args:
            update: 업데이트 객체
            context: 컨텍스트 객체
        """
        query = update.callback_query
        await query.answer()
        
        try:
            # callback_data 파싱: "batch_id:action"
            data = query.data
            batch_id, action = data.split(':')
            
            logger.info(f"Button callback: {action} [batch_id: {batch_id}]")
            
            if batch_id not in self.batch_states:
                # 이미 처리 완료된 배치인 경우
                await query.edit_message_text(
                    "ℹ️ 이 작업은 이미 완료되었거나 취소되었습니다.\n\n"
                    "새 이미지가 감지되면 다시 알림을 받게 됩니다."
                )
                logger.warning(f"Batch not found (already processed): {batch_id}")
                return
            
            batch_state = self.batch_states[batch_id]
            
            if action == "add_context":
                # 정보 추가하기 선택
                batch_state['state'] = 'waiting_for_text'
                await query.edit_message_text(
                    "✍️ 사진에 대한 설명을 자유롭게 입력해주세요.\n\n"
                    "(장소, 경험, 느낌 등을 자유롭게 작성해주세요)"
                )
                logger.info(f"Waiting for user text input [batch_id: {batch_id}]")
                
            elif action == "no_context":
                # 이미지로만 생성 선택
                batch_state['state'] = 'generating'
                batch_state['context'] = None
                await query.edit_message_text(
                    "🤖 AI가 이미지를 분석하고 게시글을 생성 중입니다...\n\n"
                    "잠시만 기다려주세요 ⏳"
                )
                logger.info(f"Starting AI generation (no context) [batch_id: {batch_id}]")
                
                # AI 생성 호출
                await self._generate_content(batch_id, context.bot)
            
            elif action == "approve":
                # 승인 → SNS 게시 시작
                batch_state['state'] = 'posting'
                await query.edit_message_text(
                    "✅ 승인되었습니다!\n\n"
                    "🚀 SNS에 게시 중입니다...\n"
                    "잠시만 기다려주세요 ⏳"
                )
                logger.info(f"Content approved, starting SNS posting [batch_id: {batch_id}]")
                
                # SNS 게시 호출
                await self._post_to_sns(batch_id, context.bot)
            
            elif action == "feedback":
                # 피드백 제공
                batch_state['state'] = 'waiting_for_feedback'
                await query.edit_message_text(
                    "✏️ 수정할 내용을 입력해주세요.\n\n"
                    "(예: 더 캐주얼하게, 해시태그 줄여줘, 이모지 더 넣어줘 등)"
                )
                logger.info(f"Waiting for feedback [batch_id: {batch_id}]")
            
            elif action == "facebook_only":
                # 페이스북만 게시
                batch_state['state'] = 'posting'
                await query.edit_message_text(
                    "📘 페이스북에만 게시합니다...\n\n"
                    "잠시만 기다려주세요 ⏳"
                )
                logger.info(f"Posting to Facebook only [batch_id: {batch_id}]")
                await self._post_to_sns(batch_id, context.bot, platforms=['facebook'])
            
            elif action == "instagram_only":
                # 인스타그램만 게시
                batch_state['state'] = 'posting'
                await query.edit_message_text(
                    "📱 인스타그램에만 게시합니다...\n\n"
                    "잠시만 기다려주세요 ⏳"
                )
                logger.info(f"Posting to Instagram only [batch_id: {batch_id}]")
                await self._post_to_sns(batch_id, context.bot, platforms=['instagram'])
            
            elif action == "rescan":
                # 폴더 재스캔
                await query.edit_message_text(
                    "🔄 폴더를 다시 스캔 중입니다...\n\n"
                    "잠시만 기다려주세요 ⏳"
                )
                logger.info(f"Rescanning folder [batch_id: {batch_id}]")
                
                # 기존 배치 정리
                self.clear_batch(batch_id)
                
                # 폴더 재스캔
                await self._rescan_folder(context.bot)
            
            elif action == "cancel":
                # 중단 및 폴더 정리
                await query.edit_message_text(
                    "🚫 작업을 중단하고 폴더를 정리합니다..."
                )
                logger.info(f"Cancelling and cleaning up [batch_id: {batch_id}]")
                
                # 폴더 정리 (이미지 + JSON 삭제)
                folder_path = config.WATCH_FOLDER
                await self._cleanup_folder(folder_path, context.bot, batch_id)
                
        except Exception as e:
            logger.error(f"Error handling button callback: {e}", exc_info=True)
            await query.edit_message_text(f"❌ 오류가 발생했습니다: {str(e)}")
    
    async def handle_text_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """
        텍스트 메시지 처리 (컨텍스트 입력)
        
        Args:
            update: 업데이트 객체
            context: 컨텍스트 객체
        """
        user_text = update.message.text
        
        try:
            # 현재 대기 중인 배치 확인
            if self.current_batch_id is None:
                logger.debug("No active batch, ignoring text message")
                return
            
            batch_id = self.current_batch_id
            
            if batch_id not in self.batch_states:
                logger.warning(f"Batch not found: {batch_id}")
                return
            
            batch_state = self.batch_states[batch_id]
            
            # 텍스트 입력 대기 상태인지 확인
            if batch_state['state'] == 'waiting_for_text':
                # 컨텍스트 저장
                batch_state['context'] = user_text
                batch_state['state'] = 'generating'
                
                logger.info(f"User context received [batch_id: {batch_id}]: {user_text[:50]}...")
                
                # 확인 메시지 전송
                await update.message.reply_text(
                    "🤖 AI가 이미지를 분석하고 게시글을 생성 중입니다...\n\n"
                    "잠시만 기다려주세요 ⏳"
                )
                
                # AI 생성 호출
                bot = update.get_bot()
                await self._generate_content(batch_id, bot)
            
            elif batch_state['state'] == 'waiting_for_feedback':
                # 피드백 저장
                batch_state['feedback'] = user_text
                batch_state['state'] = 'regenerating'
                
                logger.info(f"User feedback received [batch_id: {batch_id}]: {user_text[:50]}...")
                
                # 확인 메시지 전송
                await update.message.reply_text(
                    "🤖 피드백을 반영하여 글을 다시 작성 중입니다...\n\n"
                    "잠시만 기다려주세요 ⏳"
                )
                
                # AI 재생성 호출
                bot = update.get_bot()
                await self._regenerate_content(batch_id, bot)
            
            else:
                logger.debug(f"Batch not waiting for input, ignoring [batch_id: {batch_id}]")
                return
            
        except Exception as e:
            logger.error(f"Error handling text message: {e}", exc_info=True)
            await update.message.reply_text(f"❌ 오류가 발생했습니다: {str(e)}")
    
    def get_batch_data(self, batch_id: str) -> Dict | None:
        """
        배치 데이터 가져오기
        
        Args:
            batch_id: 배치 ID
            
        Returns:
            Dict | None: 배치 데이터 또는 None
        """
        return self.batch_states.get(batch_id)
    
    def clear_batch(self, batch_id: str):
        """
        배치 데이터 삭제
        
        Args:
            batch_id: 배치 ID
        """
        if batch_id in self.batch_states:
            del self.batch_states[batch_id]
            logger.info(f"Batch cleared [batch_id: {batch_id}]")
            
            if self.current_batch_id == batch_id:
                self.current_batch_id = None
    
    async def _generate_content(self, batch_id: str, bot):
        """
        AI 콘텐츠 생성 및 결과 전송
        
        Args:
            batch_id: 배치 ID
            bot: 텔레그램 봇 인스턴스
        """
        try:
            batch_state = self.batch_states.get(batch_id)
            if not batch_state:
                logger.error(f"Batch not found: {batch_id}")
                return
            
            file_paths = batch_state['files']
            user_context = batch_state.get('context')
            
            # 감시 폴더 경로
            folder_path = config.WATCH_FOLDER
            
            # ContentGenerator 가져오기
            generator = self._get_content_generator()
            
            # 이미 content.json이 있는지 확인
            if generator.check_content_exists(folder_path):
                content = generator.load_content(folder_path)
                logger.info(f"Using existing content [batch_id: {batch_id}]")
            else:
                # AI 글 생성
                logger.info(f"Generating new content [batch_id: {batch_id}]")
                content = generator.generate_and_save(folder_path, file_paths, user_context)
            
            # 결과 전송
            await self._send_generated_content(bot, content, batch_id)
            
            # 상태 업데이트
            batch_state['state'] = 'completed'
            batch_state['content'] = content
            
        except Exception as e:
            logger.error(f"Failed to generate content: {e}", exc_info=True)
            await bot.send_message(
                chat_id=self.chat_id,
                text=f"❌ AI 글 생성 중 오류가 발생했습니다.\n\n{str(e)}"
            )
    
    async def _send_generated_content(self, bot, content: dict, batch_id: str):
        """
        생성된 콘텐츠를 텔레그램으로 전송 (승인/피드백 버튼 포함)
        
        Args:
            bot: 텔레그램 봇 인스턴스
            content: 생성된 콘텐츠
            batch_id: 배치 ID
        """
        try:
            # Instagram 버전
            instagram_msg = (
                "📱 **Instagram 버전**\n\n"
                f"{content.get('instagram_text', '')}\n\n"
                f"{content.get('instagram_hashtags', '')}"
            )
            
            # Facebook 버전
            facebook_msg = (
                "📘 **Facebook 버전**\n\n"
                f"{content.get('facebook_text', '')}\n\n"
                f"{content.get('facebook_hashtags', '')}"
            )
            
            # 결과 전송
            await bot.send_message(
                chat_id=self.chat_id,
                text=f"✅ AI 글 생성 완료!"
            )
            
            await bot.send_message(
                chat_id=self.chat_id,
                text=instagram_msg,
                parse_mode='Markdown'
            )
            
            await bot.send_message(
                chat_id=self.chat_id,
                text=facebook_msg,
                parse_mode='Markdown'
            )
            
            # 승인/피드백/개별 게시/중단 버튼
            keyboard = [
                [InlineKeyboardButton("✅ 전체 승인 (FB+IG)", callback_data=f"{batch_id}:approve")],
                [InlineKeyboardButton("✏️ 피드백 제공", callback_data=f"{batch_id}:feedback")],
                [
                    InlineKeyboardButton("📘 페이스북만", callback_data=f"{batch_id}:facebook_only"),
                    InlineKeyboardButton("📱 인스타만", callback_data=f"{batch_id}:instagram_only")
                ],
                [InlineKeyboardButton("🚫 중단", callback_data=f"{batch_id}:cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await bot.send_message(
                chat_id=self.chat_id,
                text="이 글이 마음에 드시나요?",
                reply_markup=reply_markup
            )
            
            logger.info(f"Generated content sent with buttons [batch_id: {batch_id}]")
            
        except Exception as e:
            logger.error(f"Failed to send generated content: {e}", exc_info=True)
            raise
    
    async def _regenerate_content(self, batch_id: str, bot):
        """
        피드백 반영하여 AI 콘텐츠 재생성
        
        Args:
            batch_id: 배치 ID
            bot: 텔레그램 봇 인스턴스
        """
        try:
            batch_state = self.batch_states.get(batch_id)
            if not batch_state:
                logger.error(f"Batch not found: {batch_id}")
                return
            
            # 기존 콘텐츠와 피드백 가져오기
            existing_content = batch_state.get('content', {})
            feedback = batch_state.get('feedback', '')
            
            # ContentGenerator 가져오기
            generator = self._get_content_generator()
            
            # AI 재생성
            logger.info(f"Regenerating content with feedback [batch_id: {batch_id}]")
            content = generator.regenerate_with_feedback(existing_content, feedback)
            
            # JSON 저장 (덮어쓰기)
            folder_path = config.WATCH_FOLDER
            generator.save_content(folder_path, content)
            
            # 결과 전송
            await self._send_generated_content(bot, content, batch_id)
            
            # 상태 업데이트
            batch_state['state'] = 'completed'
            batch_state['content'] = content
            
        except Exception as e:
            logger.error(f"Failed to regenerate content: {e}", exc_info=True)
            await bot.send_message(
                chat_id=self.chat_id,
                text=f"❌ AI 글 재생성 중 오류가 발생했습니다.\n\n{str(e)}"
            )
    
    async def _post_to_sns(self, batch_id: str, bot, platforms: List[str] = None):
        """
        SNS에 게시
        
        Args:
            batch_id: 배치 ID
            bot: 텔레그램 봇 인스턴스
            platforms: 게시할 플랫폼 리스트 (None이면 전체)
        """
        try:
            batch_state = self.batch_states.get(batch_id)
            if not batch_state:
                logger.error(f"Batch not found: {batch_id}")
                return
            
            file_paths = batch_state['files']
            folder_path = config.WATCH_FOLDER
            
            # 플랫폼 설정 (기본: 전체)
            if platforms is None:
                platforms = ['facebook', 'instagram']
            
            # PostManager 가져오기
            from sns_poster import PostManager
            post_manager = PostManager()
            
            results = {'facebook': None, 'instagram': None}
            success_count = 0
            
            # 페이스북 게시
            if 'facebook' in platforms:
                await bot.send_message(
                    chat_id=self.chat_id,
                    text="📘 페이스북에 게시 중..."
                )
                
                try:
                    results['facebook'] = await post_manager.post_to_facebook(folder_path, file_paths)
                    if results['facebook']:
                        await bot.send_message(
                            chat_id=self.chat_id,
                            text="✅ 페이스북 게시 완료!"
                        )
                        success_count += 1
                    else:
                        await bot.send_message(
                            chat_id=self.chat_id,
                            text="⚠️ 페이스북 게시 스킵 (이미 게시됨 또는 실패)"
                        )
                except Exception as e:
                    logger.error(f"Facebook posting failed: {e}")
                    await bot.send_message(
                        chat_id=self.chat_id,
                        text=f"❌ 페이스북 게시 실패: {str(e)}"
                    )
                    results['facebook'] = False
            
            # 인스타그램 게시
            if 'instagram' in platforms:
                await bot.send_message(
                    chat_id=self.chat_id,
                    text="📱 인스타그램에 게시 중..."
                )
                
                try:
                    results['instagram'] = await post_manager.post_to_instagram(folder_path, file_paths)
                    if results['instagram']:
                        await bot.send_message(
                            chat_id=self.chat_id,
                            text="✅ 인스타그램 게시 완료!"
                        )
                        success_count += 1
                    else:
                        await bot.send_message(
                            chat_id=self.chat_id,
                            text="⚠️ 인스타그램 게시 스킵 (이미 게시됨 또는 실패)"
                        )
                except Exception as e:
                    logger.error(f"Instagram posting failed: {e}")
                    await bot.send_message(
                        chat_id=self.chat_id,
                        text=f"❌ 인스타그램 게시 실패: {str(e)}"
                    )
                    results['instagram'] = False
            
            # 최종 결과 메시지
            result_lines = []
            if 'facebook' in platforms:
                fb_status = "✅" if results['facebook'] else "❌"
                result_lines.append(f"페이스북: {fb_status}")
            if 'instagram' in platforms:
                ig_status = "✅" if results['instagram'] else "❌"
                result_lines.append(f"인스타그램: {ig_status}")
            
            await bot.send_message(
                chat_id=self.chat_id,
                text=f"🎉 게시 완료!\n\n" + "\n".join(result_lines)
            )
            
            # 상태 업데이트
            batch_state['state'] = 'posted'
            batch_state['post_results'] = results
            
            logger.info(f"SNS posting completed [batch_id: {batch_id}]: {results}")
            
            # 성공한 게시가 있으면 폴더 정리
            if success_count > 0:
                await self._cleanup_folder(folder_path, bot, batch_id)
            
        except Exception as e:
            logger.error(f"Failed to post to SNS: {e}", exc_info=True)
            await bot.send_message(
                chat_id=self.chat_id,
                text=f"❌ SNS 게시 중 오류가 발생했습니다.\n\n{str(e)}"
            )
    
    async def _cleanup_folder(self, folder_path: str, bot, batch_id: str):
        """
        게시 완료 후 폴더 내용물 삭제
        
        Args:
            folder_path: 폴더 경로
            bot: 텔레그램 봇 인스턴스
            batch_id: 배치 ID
        """
        import shutil
        from pathlib import Path
        
        try:
            folder = Path(folder_path)
            
            if not folder.exists():
                logger.warning(f"Folder not found: {folder_path}")
                return
            
            # 폴더 내 모든 파일 삭제
            deleted_count = 0
            for item in folder.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                        deleted_count += 1
                    elif item.is_dir():
                        shutil.rmtree(item)
                        deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete {item}: {e}")
            
            logger.info(f"Folder cleaned up: {deleted_count} items deleted [batch_id: {batch_id}]")
            
            await bot.send_message(
                chat_id=self.chat_id,
                text=f"🗑️ 폴더 정리 완료! ({deleted_count}개 파일 삭제)\n\n"
                     f"📂 새 이미지를 기다리는 중..."
            )
            
            # 배치 상태 정리
            self.clear_batch(batch_id)
            
            # 파일 감시 재개
            if self.file_watcher:
                self.file_watcher.resume()
            
        except Exception as e:
            logger.error(f"Failed to cleanup folder: {e}", exc_info=True)
            await bot.send_message(
                chat_id=self.chat_id,
                text=f"⚠️ 폴더 정리 중 오류: {str(e)}"
            )
            # 오류가 발생해도 감시 재개
            if self.file_watcher:
                self.file_watcher.resume()
    
    async def _rescan_folder(self, bot):
        """
        폴더를 다시 스캔하여 이미지 재감지
        
        Args:
            bot: 텔레그램 봇 인스턴스
        """
        from pathlib import Path
        from file_watcher.batch_handler import is_image_file, validate_file_stability
        
        try:
            folder_path = config.WATCH_FOLDER
            folder = Path(folder_path)
            
            if not folder.exists():
                await bot.send_message(
                    chat_id=self.chat_id,
                    text="❌ 감시 폴더를 찾을 수 없습니다."
                )
                return
            
            # 이미지 파일 수집
            image_files = []
            for file_path in folder.iterdir():
                if file_path.is_file() and is_image_file(str(file_path)):
                    abs_path = str(file_path.absolute())
                    # 안정성 검사
                    if validate_file_stability(abs_path):
                        image_files.append(abs_path)
            
            if not image_files:
                await bot.send_message(
                    chat_id=self.chat_id,
                    text="📂 폴더에 이미지가 없습니다.\n\n새 이미지를 기다리는 중..."
                )
                # 파일이 없으면 감시 재개
                if self.file_watcher:
                    self.file_watcher.resume()
                return
            
            # 정렬
            image_files = sorted(image_files)
            logger.info(f"Rescan found {len(image_files)} image(s)")
            
            # 모든 파일을 임시 이름으로 변경 후 순차적으로 재정렬
            renamed_files = self._rename_files_sequentially(image_files)
            logger.info(f"Rescan renamed {len(renamed_files)} file(s)")
            
            # 새 컨텍스트 요청 전송
            await self.send_context_request(bot, self.chat_id, renamed_files)
            
        except Exception as e:
            logger.error(f"Failed to rescan folder: {e}", exc_info=True)
            await bot.send_message(
                chat_id=self.chat_id,
                text=f"❌ 폴더 재스캔 중 오류: {str(e)}"
            )
    
    def _rename_files_sequentially(self, file_paths: List[str]) -> List[str]:
        """
        파일들을 no1, no2, no3... 순서로 재정렬
        기존 파일명과 충돌 방지를 위해 임시 이름으로 먼저 변경
        
        Args:
            file_paths: 원본 파일 경로 리스트 (정렬된 상태)
            
        Returns:
            List[str]: 변경된 파일 경로 리스트
        """
        import os
        import uuid
        from pathlib import Path
        
        if not file_paths:
            return []
        
        # 1단계: 모든 파일을 임시 이름으로 변경
        temp_files = []
        for file_path in file_paths:
            try:
                path = Path(file_path)
                ext = path.suffix
                temp_name = f"_temp_{uuid.uuid4().hex[:8]}{ext}"
                temp_path = path.parent / temp_name
                
                os.rename(file_path, temp_path)
                temp_files.append(str(temp_path))
                logger.debug(f"Temp rename: {path.name} -> {temp_name}")
            except Exception as e:
                logger.error(f"Failed to temp rename {file_path}: {e}")
                temp_files.append(file_path)  # 실패 시 원본 유지
        
        # 2단계: 임시 파일들을 no1, no2, no3... 순서로 변경
        renamed_files = []
        for idx, temp_path in enumerate(temp_files, start=1):
            try:
                path = Path(temp_path)
                ext = path.suffix
                new_name = f"no{idx}{ext}"
                new_path = path.parent / new_name
                
                os.rename(temp_path, new_path)
                renamed_files.append(str(new_path))
                logger.info(f"Renamed: {path.name} -> {new_name}")
            except Exception as e:
                logger.error(f"Failed to rename {temp_path}: {e}")
                renamed_files.append(temp_path)  # 실패 시 임시 이름 유지
        
        return renamed_files
