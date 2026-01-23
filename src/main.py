"""
SNS Avatar - AI 기반 소셜 미디어 콘텐츠 자동화 시스템
메인 애플리케이션
"""
import asyncio
import signal
import sys
from typing import List
from shared.logger import setup_logger
from shared.config import config
from shared.exceptions import ConfigurationError
from file_watcher import FileWatcher
from telegram_bot import TelegramBot

logger = setup_logger(__name__)


class SNSAvatarApp:
    """SNS Avatar 메인 애플리케이션"""
    
    def __init__(self):
        """초기화"""
        import threading
        self.file_watcher: FileWatcher | None = None
        self.telegram_bot: TelegramBot | None = None
        self.running = False
        self.loop: asyncio.AbstractEventLoop | None = None  # 이벤트 루프 저장
        self.sent_batches: set = set()  # 이미 전송한 배치 ID 저장
        self.batch_lock = threading.Lock()  # 배치 중복 체크용 Lock
        logger.info("SNS Avatar Application initialized")
    
    async def initialize(self):
        """애플리케이션 초기화"""
        try:
            logger.info("=" * 60)
            logger.info("Starting SNS Avatar Application")
            logger.info("=" * 60)
            
            # 설정 검증
            logger.info("Validating configuration...")
            config.validate()
            logger.info("[OK] Configuration validated")
            
            # 텔레그램 봇 초기화
            logger.info("Initializing Telegram bot...")
            self.telegram_bot = TelegramBot()
            await self.telegram_bot.initialize()
            logger.info("[OK] Telegram bot initialized")
            
            # 파일 감시 초기화
            logger.info("Initializing file watcher...")
            self.file_watcher = FileWatcher(on_batch_ready=self._on_batch_ready)
            logger.info("[OK] File watcher initialized")
            
            logger.info("=" * 60)
            logger.info("Application initialized successfully")
            logger.info("=" * 60)
            
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}", exc_info=True)
            raise
    
    def _on_batch_ready(self, file_paths: List[str]):
        """
        배치 준비 완료 콜백 (watchdog 스레드에서 호출됨)
        
        Args:
            file_paths: 처리할 파일 경로 리스트
        """
        # 배치 ID 생성 (파일 경로 기반)
        batch_id = "|".join(sorted(file_paths))
        
        logger.info(f"[CALLBACK] on_batch_ready called with {len(file_paths)} file(s)")
        
        # 중복 배치 체크
        with self.batch_lock:
            if batch_id in self.sent_batches:
                logger.warning(f"[CALLBACK] Duplicate batch SKIPPED!")
                return
            self.sent_batches.add(batch_id)
            logger.info(f"[CALLBACK] New batch registered, will send notification")
        
        # 메인 이벤트 루프에 작업 스케줄링
        if self.loop and self.loop.is_running():
            logger.info("[CALLBACK] Scheduling telegram notification...")
            asyncio.run_coroutine_threadsafe(
                self._send_telegram_notification(file_paths),
                self.loop
            )
        else:
            logger.error("[CALLBACK] Event loop not running!")
    
    async def _send_telegram_notification(self, file_paths: List[str]):
        """
        텔레그램 알림 전송
        
        Args:
            file_paths: 파일 경로 리스트
        """
        try:
            logger.info("[TELEGRAM] Sending notification...")
            batch_id = await self.telegram_bot.send_batch_notification(file_paths)
            logger.info(f"[TELEGRAM] OK - batch_id: {batch_id}")
            
        except Exception as e:
            logger.error(f"[TELEGRAM] Failed: {e}", exc_info=True)
    
    async def start(self):
        """애플리케이션 시작"""
        try:
            self.running = True
            
            # 이벤트 루프 저장
            self.loop = asyncio.get_running_loop()
            logger.info(f"Event loop stored: {self.loop}")
            
            # 텔레그램 Polling 시작
            logger.info("Starting Telegram bot polling...")
            await self.telegram_bot.start_polling()
            logger.info("[OK] Telegram bot polling started")
            
            # 파일 감시 시작
            logger.info("Starting file watcher...")
            self.file_watcher.start()
            logger.info("[OK] File watcher started")
            
            # 시작 메시지 전송
            await self.telegram_bot.send_message(
                "[START] SNS Avatar 시스템이 시작되었습니다!\n\n"
                f"감시 폴더: {config.WATCH_FOLDER}\n"
                f"배치 대기 시간: {config.BATCH_WAIT_TIME}초\n\n"
                "이미지 파일을 감시 폴더에 추가하면 자동으로 감지됩니다."
            )
            
            logger.info("=" * 60)
            logger.info("Application is running...")
            logger.info(f"Watch folder: {config.WATCH_FOLDER}")
            logger.info(f"Batch wait time: {config.BATCH_WAIT_TIME}s")
            logger.info("Press Ctrl+C to stop")
            logger.info("=" * 60)
            
            # 이벤트 루프 유지
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Error during application run: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """애플리케이션 종료"""
        try:
            logger.info("=" * 60)
            logger.info("Shutting down application...")
            logger.info("=" * 60)
            
            self.running = False
            
            # 파일 감시 중지
            if self.file_watcher is not None:
                logger.info("Stopping file watcher...")
                self.file_watcher.stop()
                logger.info("[OK] File watcher stopped")
            
            # 텔레그램 봇 종료
            if self.telegram_bot is not None:
                logger.info("Shutting down Telegram bot...")
                await self.telegram_bot.shutdown()
                logger.info("[OK] Telegram bot shut down")
            
            logger.info("=" * 60)
            logger.info("Application shut down successfully")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)


async def main():
    """메인 함수"""
    app = SNSAvatarApp()
    
    try:
        # 초기화
        await app.initialize()
        
        # 시작
        await app.start()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # 이벤트 루프 실행
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated")
    except Exception as e:
        logger.error(f"Failed to run application: {e}", exc_info=True)
        sys.exit(1)
