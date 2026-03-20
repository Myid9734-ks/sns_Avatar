"""텔레그램 봇 메인"""
from typing import List, Callable
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from shared.logger import setup_logger
from shared.config import config
from shared.exceptions import TelegramError
from telegram_bot.handlers import TelegramHandlers

logger = setup_logger(__name__)


class TelegramBot:
    """텔레그램 봇 관리자"""
    
    def __init__(self):
        """초기화"""
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.application: Application | None = None
        self.bot: Bot | None = None
        self.handlers = TelegramHandlers()
        logger.info("TelegramBot initialized")
    
    async def initialize(self):
        """봇 초기화"""
        try:
            logger.info("Initializing Telegram bot...")
            
            # Application 생성 (타임아웃 설정: 이미지 전송 시 시간이 오래 걸릴 수 있음)
            self.application = (
                Application.builder()
                .token(self.bot_token)
                .connect_timeout(30)
                .read_timeout(30)
                .write_timeout(60)
                .pool_timeout(10)
                .get_updates_connect_timeout(30)
                .get_updates_read_timeout(30)
                .get_updates_write_timeout(30)
                .get_updates_pool_timeout(10)
                .build()
            )
            self.bot = self.application.bot
            
            # 핸들러 등록
            self._register_handlers()
            
            # Application 초기화 (polling은 나중에 시작)
            await self.application.initialize()
            
            logger.info("Telegram bot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            raise TelegramError(f"Failed to initialize bot: {e}")
    
    def _register_handlers(self):
        """핸들러 등록"""
        # 명령어 핸들러
        self.application.add_handler(
            CommandHandler("start", self._handle_start_command)
        )
        self.application.add_handler(
            CommandHandler("help", self._handle_help_command)
        )
        
        # 버튼 콜백 핸들러
        self.application.add_handler(
            CallbackQueryHandler(self.handlers.handle_button_callback)
        )
        
        # 텍스트 메시지 핸들러
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_text_message)
        )
        
        # 에러 핸들러 등록 (모든 텔레그램 에러를 로그에 기록)
        self.application.add_error_handler(self._handle_error)
        
        logger.info("Telegram handlers registered")
    
    async def _handle_start_command(self, update, context):
        """
        /start 명령어 처리
        
        Args:
            update: 업데이트 객체
            context: 컨텍스트 객체
        """
        await update.message.reply_text(
            "🤖 **SNS Avatar Bot**\n\n"
            "이미지 파일을 자동으로 감지하고 AI 게시글을 생성합니다.\n\n"
            "프로그램이 실행 중이면 이미지가 감지될 때마다 알림을 받게 됩니다.",
            parse_mode='Markdown'
        )
    
    async def _handle_help_command(self, update, context):
        """
        /help 명령어 처리
        
        Args:
            update: 업데이트 객체
            context: 컨텍스트 객체
        """
        await update.message.reply_text(
            "📖 **사용 방법**\n\n"
            "1. 감시 폴더에 이미지를 추가하세요\n"
            "2. 봇이 이미지를 감지하면 알림을 보냅니다\n"
            "3. [정보 추가하기] 또는 [이미지로만 생성] 중 선택하세요\n"
            "4. AI가 게시글 초안을 생성합니다\n\n"
            "**명령어**\n"
            "/start - 봇 시작\n"
            "/help - 도움말",
            parse_mode='Markdown'
        )
    
    async def send_batch_notification(self, file_paths: List[str]) -> str:
        """
        배치 파일 감지 알림 전송
        
        Args:
            file_paths: 이미지 파일 경로 리스트
            
        Returns:
            str: 배치 ID
        """
        try:
            batch_id = await self.handlers.send_context_request(
                self.bot,
                self.chat_id,
                file_paths
            )
            return batch_id
            
        except Exception as e:
            logger.error(f"Failed to send batch notification: {e}", exc_info=True)
            raise TelegramError(f"Failed to send notification: {e}")
    
    async def send_message(self, text: str, parse_mode: str = None):
        """
        메시지 전송
        
        Args:
            text: 전송할 텍스트
            parse_mode: 파싱 모드 (None, 'Markdown', 'HTML')
        """
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode
            )
            logger.debug(f"Message sent: {text[:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise TelegramError(f"Failed to send message: {e}")
    
    async def _handle_error(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """
        텔레그램 에러 핸들러 (모든 에러를 로그에 기록)
        
        Args:
            update: 업데이트 객체 (없을 수 있음)
            context: 컨텍스트 객체
        """
        import traceback
        
        error = context.error
        error_type = type(error).__name__
        error_message = str(error)
        
        # 상세한 에러 정보 로깅
        logger.error(
            f"Telegram error occurred: {error_type} - {error_message}",
            exc_info=True
        )
        
        # Conflict 에러는 특별히 처리
        if "Conflict" in error_type or "terminated by other getUpdates" in error_message:
            logger.error(
                "⚠️ 텔레그램 Conflict 에러 발생: "
                "다른 봇 인스턴스가 실행 중일 수 있습니다. "
                "기존 프로세스를 종료하고 다시 시작하세요."
            )
        
        # 사용자에게 에러 알림 (가능한 경우)
        if update and hasattr(update, 'effective_chat'):
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"❌ 오류가 발생했습니다: {error_type}\n\n{error_message}"
                )
            except:
                pass  # 알림 실패해도 무시
    
    async def start_polling(self):
        """Polling 시작"""
        try:
            logger.info("Starting Telegram bot polling...")
            await self.application.start()
            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                poll_interval=1.0,
                error_callback=lambda exc: logger.warning(f"Polling error (auto-retry): {exc}")
            )
            logger.info("Telegram bot polling started")
        except Exception as e:
            logger.error(f"Failed to start polling: {e}", exc_info=True)
            raise TelegramError(f"Failed to start polling: {e}")
    
    async def shutdown(self):
        """봇 종료"""
        try:
            if self.application is not None:
                logger.info("Shutting down Telegram bot...")
                if self.application.updater and self.application.updater.running:
                    await self.application.updater.stop()
                if self.application.running:
                    await self.application.stop()
                await self.application.shutdown()
                logger.info("Telegram bot shut down successfully")
                
        except Exception as e:
            logger.error(f"Error during bot shutdown: {e}")
    
    def get_batch_data(self, batch_id: str):
        """
        배치 데이터 가져오기
        
        Args:
            batch_id: 배치 ID
            
        Returns:
            배치 데이터
        """
        return self.handlers.get_batch_data(batch_id)
    
    def clear_batch(self, batch_id: str):
        """
        배치 데이터 삭제
        
        Args:
            batch_id: 배치 ID
        """
        self.handlers.clear_batch(batch_id)
