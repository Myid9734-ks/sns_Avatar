"""파일 감시 및 배치 수집 (폴링 방식)"""
import os
import time
from pathlib import Path
from typing import List, Callable, Set
from threading import Thread, Lock
from shared.logger import setup_logger
from shared.config import config
from shared.exceptions import FileWatcherError
from file_watcher.batch_handler import (
    is_image_file,
    validate_file_stability,
    rename_batch_files,
    collect_existing_images
)

logger = setup_logger(__name__)


class FileWatcher:
    """파일 감시 관리자 (폴링 방식)"""
    
    def __init__(self, on_batch_ready: Callable[[List[str]], None]):
        """
        초기화
        
        Args:
            on_batch_ready: 배치 준비 완료 시 호출될 콜백 함수
        """
        self.watch_folder = config.WATCH_FOLDER
        self.on_batch_ready = on_batch_ready
        self.known_files: Set[str] = set()  # 이미 감지된 파일들
        self.pending_files: List[str] = []
        self.last_change_time: float = 0
        self.batch_wait_time = config.BATCH_WAIT_TIME
        self.poll_interval = 2.0  # 2초마다 스캔
        self.running = False
        self.poll_thread: Thread | None = None
        self.lock = Lock()
        logger.info(f"FileWatcher initialized for: {self.watch_folder}")
    
    def start(self):
        """파일 감시 시작 (폴링 방식)"""
        try:
            # 감시 폴더 확인
            watch_path = Path(self.watch_folder)
            if not watch_path.exists():
                raise FileWatcherError(f"Watch folder does not exist: {self.watch_folder}")
            
            logger.info("Starting file watcher (polling mode)...")
            
            # 초기 스캔: 기존 파일 처리
            self._process_existing_files()
            
            # 폴링 스레드 시작
            self.running = True
            self.poll_thread = Thread(target=self._poll_loop, daemon=True)
            self.poll_thread.start()
            
            logger.info(f"File watcher started successfully: {self.watch_folder}")
            
        except Exception as e:
            logger.error(f"Failed to start file watcher: {e}")
            raise FileWatcherError(f"Failed to start file watcher: {e}")
    
    def stop(self):
        """파일 감시 중지"""
        logger.info("Stopping file watcher...")
        self.running = False
        if self.poll_thread is not None:
            self.poll_thread.join(timeout=5)
        logger.info("File watcher stopped")
    
    def _poll_loop(self):
        """폴링 루프 (별도 스레드에서 실행)"""
        while self.running:
            try:
                self._scan_folder()
                self._check_batch_timeout()
                time.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in poll loop: {e}", exc_info=True)
    
    def _scan_folder(self):
        """폴더 스캔하여 새 파일 감지"""
        try:
            watch_path = Path(self.watch_folder)
            current_files: Set[str] = set()
            new_files: List[str] = []
            
            # 폴더 내 이미지 파일 찾기
            for file_path in watch_path.iterdir():
                if file_path.is_file() and is_image_file(str(file_path)):
                    # resolve() 대신 abspath 사용 (네트워크 드라이브 호환)
                    abs_path = os.path.abspath(str(file_path))
                    current_files.add(abs_path)
                    
                    # 새 파일 발견 (즉시 known_files에 추가)
                    if abs_path not in self.known_files:
                        logger.debug(f"[SCAN] New file found: {file_path.name}")
                        logger.debug(f"[SCAN] known_files count: {len(self.known_files)}")
                        self.known_files.add(abs_path)
                        new_files.append(abs_path)
                    else:
                        logger.debug(f"[SCAN] Already known: {file_path.name}")
            
            # 새 파일들에 대해 안정성 체크 (블로킹)
            for resolved_path in new_files:
                logger.debug(f"[STABILITY] Checking: {Path(resolved_path).name}")
                if validate_file_stability(resolved_path):
                    with self.lock:
                        if resolved_path not in self.pending_files:
                            self.pending_files.append(resolved_path)
                            self.last_change_time = time.time()
                            logger.info(f"[ADD] New file added to batch: {Path(resolved_path).name}")
                            logger.info(f"[ADD] pending_files: {len(self.pending_files)}")
                        else:
                            logger.debug(f"[ADD] Already in pending: {Path(resolved_path).name}")
            
            # 삭제된 파일 제거
            deleted_files = self.known_files - current_files
            for file_path in deleted_files:
                self.known_files.discard(file_path)
                logger.debug(f"[SCAN] Removed deleted file: {Path(file_path).name}")
                
        except Exception as e:
            logger.error(f"Error scanning folder: {e}")
    
    def _check_batch_timeout(self):
        """배치 타임아웃 확인 및 처리"""
        with self.lock:
            if not self.pending_files:
                return
            
            elapsed = time.time() - self.last_change_time
            logger.debug(f"[TIMEOUT] pending: {len(self.pending_files)}, elapsed: {elapsed:.1f}s")
            
            # 마지막 변경 후 batch_wait_time 경과 확인
            if elapsed >= self.batch_wait_time:
                logger.info(f"[TIMEOUT] Batch timeout reached, processing...")
                self._process_batch()
    
    def _process_batch(self):
        """배치 처리 (lock 안에서 호출됨)"""
        if not self.pending_files:
            logger.debug("[BATCH] No pending files, skipping")
            return
        
        logger.info(f"[BATCH] === START === Processing {len(self.pending_files)} file(s)")
        
        batch_files = self.pending_files.copy()
        self.pending_files.clear()
        logger.debug(f"[BATCH] pending_files cleared")
        
        try:
            # 파일명 변경
            logger.info(f"[BATCH] Renaming files...")
            renamed_files = rename_batch_files(batch_files)
            logger.info(f"[BATCH] Renamed {len(renamed_files)} file(s)")
            
            # 변경된 파일명도 known_files에 추가 (재감지 방지)
            for renamed_path in renamed_files:
                abs_path = os.path.abspath(renamed_path)
                self.known_files.add(abs_path)
                logger.debug(f"[BATCH] Added to known_files: {Path(renamed_path).name}")
            
            logger.info(f"[BATCH] known_files count: {len(self.known_files)}")
            
            # 콜백 호출
            if renamed_files:
                logger.info(f"[BATCH] Calling on_batch_ready...")
                self.on_batch_ready(renamed_files)
                logger.info(f"[BATCH] === END === Callback completed")
            else:
                logger.warning("[BATCH] No files were successfully renamed")
                
        except Exception as e:
            logger.error(f"[BATCH] Error: {e}", exc_info=True)
    
    def _process_existing_files(self):
        """초기 스캔: 기존 이미지 파일 처리"""
        logger.info("[EXISTING] === START ===")
        
        existing_files = collect_existing_images(self.watch_folder)
        
        if not existing_files:
            logger.info("[EXISTING] No files found, skipping")
            return
        
        logger.info(f"[EXISTING] Found {len(existing_files)} file(s)")
        
        # 기존 파일들을 known_files에 추가
        for file_path in existing_files:
            abs_path = os.path.abspath(file_path)
            self.known_files.add(abs_path)
        
        try:
            # 파일명 변경
            logger.info("[EXISTING] Renaming files...")
            renamed_files = rename_batch_files(existing_files)
            logger.info(f"[EXISTING] Renamed {len(renamed_files)} file(s)")
            
            # 변경된 파일명도 known_files에 추가 (재감지 방지!)
            for renamed_path in renamed_files:
                abs_path = os.path.abspath(renamed_path)
                self.known_files.add(abs_path)
            
            logger.info(f"[EXISTING] known_files count: {len(self.known_files)}")
            
            # 콜백 호출
            if renamed_files:
                logger.info("[EXISTING] Calling on_batch_ready...")
                self.on_batch_ready(renamed_files)
                logger.info("[EXISTING] === END === Callback completed")
            else:
                logger.warning("[EXISTING] No files renamed")
                
        except Exception as e:
            logger.error(f"[EXISTING] Error: {e}", exc_info=True)
    
    def is_running(self) -> bool:
        """
        파일 감시가 실행 중인지 확인
        
        Returns:
            bool: 실행 중이면 True
        """
        return self.running and self.poll_thread is not None and self.poll_thread.is_alive()
