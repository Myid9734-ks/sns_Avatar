"""
텔레그램 Webhook 삭제 스크립트
CallbackQuery가 작동하지 않는 문제 해결
"""
from telegram import Bot
import asyncio
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def check_and_delete_webhook():
    """Webhook 상태 확인 및 삭제"""
    bot = Bot(BOT_TOKEN)
    
    print("=" * 60)
    print("1. Webhook 상태 확인 중...")
    print("=" * 60)
    
    # Webhook 정보 확인
    info = await bot.get_webhook_info()
    print(f"\nWebhook URL: {info.url or '(비어있음)'}")
    print(f"Pending Updates: {info.pending_update_count}")
    print(f"Last Error: {info.last_error_message or '없음'}")
    print(f"Has Custom Certificate: {info.has_custom_certificate}")
    
    if info.url or info.pending_update_count > 0:
        print("\n[WARNING] Webhook이 설정되어 있거나 대기 중인 업데이트가 있습니다!")
        print("=" * 60)
        print("2. Webhook 삭제 중...")
        print("=" * 60)
        
        # Webhook 완전 삭제
        await bot.delete_webhook(drop_pending_updates=True)
        print("[OK] Webhook 완전 삭제 완료!")
        print("[OK] 대기 중인 업데이트도 모두 삭제됨")
        
        # 다시 확인
        print("\n" + "=" * 60)
        print("3. 삭제 후 상태 확인...")
        print("=" * 60)
        info = await bot.get_webhook_info()
        print(f"Webhook URL: {info.url or '(비어있음)'}")
        print(f"Pending Updates: {info.pending_update_count}")
        
        if not info.url:
            print("\n[SUCCESS] Webhook이 완전히 제거되었습니다!")
            print("\n[NEXT] 이제 봇 프로그램을 다시 실행하세요:")
            print("   cd \"f:\\coding_project\\SNS Avatar\\src\"")
            print("   python main.py")
        else:
            print("\n[ERROR] Webhook 삭제 실패")
    else:
        print("\n[OK] Webhook이 설정되어 있지 않습니다.")
        print("다른 문제일 수 있습니다.")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(check_and_delete_webhook())
