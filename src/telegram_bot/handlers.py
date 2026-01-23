"""텔레그램 메시지 핸들러"""
import os
from typing import Dict, List, Callable
from threading import Lock
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from shared.logger import setup_logger
from shared.config import config

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
        self.chat_id = config.TELEGRAM_CHAT_ID
        logger.info("TelegramHandlers initialized")
    
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
                [InlineKeyboardButton("🤖 이미지로만 생성", callback_data=f"{batch_id}:no_context")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # 메시지 전송 (버튼 포함)
            await bot.send_message(
                chat_id=chat_id,
                text=f"🔔 새 이미지 {file_count}개가 감지되었습니다.\n\n게시글을 생성할까요?",
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
                await query.edit_message_text("❌ 오류: 배치 정보를 찾을 수 없습니다.")
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
            
            # 승인/피드백 버튼
            keyboard = [
                [InlineKeyboardButton("✅ 승인", callback_data=f"{batch_id}:approve")],
                [InlineKeyboardButton("✏️ 피드백 제공", callback_data=f"{batch_id}:feedback")]
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
    
    async def _post_to_sns(self, batch_id: str, bot):
        """
        SNS에 게시 (페이스북 + 인스타그램)
        
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
            folder_path = config.WATCH_FOLDER
            
            # PostManager 가져오기
            from sns_poster import PostManager
            post_manager = PostManager()
            
            results = {'facebook': False, 'instagram': False}
            
            # 페이스북 게시
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
            
            # 인스타그램 게시
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
            
            # 최종 결과 메시지
            fb_status = "✅" if results['facebook'] else "❌"
            ig_status = "✅" if results['instagram'] else "❌"
            
            await bot.send_message(
                chat_id=self.chat_id,
                text=f"🎉 게시 완료!\n\n"
                     f"페이스북: {fb_status}\n"
                     f"인스타그램: {ig_status}"
            )
            
            # 상태 업데이트
            batch_state['state'] = 'posted'
            batch_state['post_results'] = results
            
            logger.info(f"SNS posting completed [batch_id: {batch_id}]: {results}")
            
        except Exception as e:
            logger.error(f"Failed to post to SNS: {e}", exc_info=True)
            await bot.send_message(
                chat_id=self.chat_id,
                text=f"❌ SNS 게시 중 오류가 발생했습니다.\n\n{str(e)}"
            )
