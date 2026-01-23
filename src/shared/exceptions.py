"""커스텀 예외 클래스"""


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
