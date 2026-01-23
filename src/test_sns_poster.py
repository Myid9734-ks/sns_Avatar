"""SNS Poster 테스트 스크립트"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from sns_poster import FacebookPoster, InstagramPoster
from shared.logger import setup_logger

logger = setup_logger(__name__)


async def test_facebook_login():
    """페이스북 로그인 테스트 (수동 로그인)"""
    print("\n" + "=" * 50)
    print("페이스북 로그인 테스트")
    print("=" * 50)
    
    fb = FacebookPoster()
    
    try:
        await fb.start_browser()
        print("[INFO] 브라우저 시작됨")
        print("[INFO] 주소창에 facebook.com 입력하고 로그인하세요.")
        print("[INFO] 로그인 완료 후 여기서 Enter 키를 누르세요.")
        input("\n>>> Enter 키를 누르면 브라우저가 닫힙니다... ")
        
    finally:
        await fb.close_browser()
        print("[INFO] 브라우저 종료됨. 세션이 저장되었습니다.")


async def test_instagram_login():
    """인스타그램 로그인 테스트 (수동 로그인)"""
    print("\n" + "=" * 50)
    print("인스타그램 로그인 테스트")
    print("=" * 50)
    
    ig = InstagramPoster()
    
    try:
        await ig.start_browser()
        print("[INFO] 브라우저 시작됨")
        print("[INFO] 주소창에 instagram.com 입력하고 로그인하세요.")
        print("[INFO] 로그인 완료 후 여기서 Enter 키를 누르세요.")
        input("\n>>> Enter 키를 누르면 브라우저가 닫힙니다... ")
        
    finally:
        await ig.close_browser()
        print("[INFO] 브라우저 종료됨. 세션이 저장되었습니다.")


async def test_facebook_post(text: str, image_path: str = None):
    """페이스북 게시 테스트"""
    print("\n" + "=" * 50)
    print("페이스북 게시 테스트")
    print("=" * 50)
    
    fb = FacebookPoster()
    
    try:
        await fb.start_browser()
        
        image_paths = [image_path] if image_path else None
        success = await fb.post(text, image_paths)
        
        if success:
            print("[SUCCESS] 페이스북 게시 성공!")
        else:
            print("[FAILED] 페이스북 게시 실패")
        
        await asyncio.sleep(5)
        
    finally:
        await fb.close_browser()


async def test_instagram_post(text: str, image_path: str):
    """인스타그램 게시 테스트 (이미지 필수)"""
    print("\n" + "=" * 50)
    print("인스타그램 게시 테스트")
    print("=" * 50)
    
    if not image_path:
        print("[ERROR] 인스타그램은 이미지가 필수입니다!")
        return
    
    ig = InstagramPoster()
    
    try:
        await ig.start_browser()
        
        success = await ig.post(text, [image_path])
        
        if success:
            print("[SUCCESS] 인스타그램 게시 성공!")
        else:
            print("[FAILED] 인스타그램 게시 실패")
        
        await asyncio.sleep(5)
        
    finally:
        await ig.close_browser()


def print_menu():
    """메뉴 출력"""
    print("\n" + "=" * 50)
    print("SNS Poster 테스트 메뉴")
    print("=" * 50)
    print("1. 페이스북 로그인 테스트")
    print("2. 인스타그램 로그인 테스트")
    print("3. 페이스북 게시 테스트")
    print("4. 인스타그램 게시 테스트")
    print("5. 종료")
    print("=" * 50)


async def main():
    """메인 함수"""
    print("\n[SNS Poster 테스트]")
    print("[INFO] 첫 실행 시 브라우저에서 직접 로그인하면 세션이 저장됩니다.")
    
    while True:
        print_menu()
        choice = input("선택하세요 (1-5): ").strip()
        
        if choice == "1":
            await test_facebook_login()
            
        elif choice == "2":
            await test_instagram_login()
            
        elif choice == "3":
            text = input("게시할 텍스트: ").strip()
            image = input("이미지 경로 (없으면 Enter): ").strip() or None
            await test_facebook_post(text, image)
            
        elif choice == "4":
            text = input("캡션 텍스트: ").strip()
            image = input("이미지 경로 (필수): ").strip()
            if image:
                await test_instagram_post(text, image)
            else:
                print("[ERROR] 인스타그램은 이미지가 필수입니다!")
                
        elif choice == "5":
            print("종료합니다.")
            break
            
        else:
            print("잘못된 선택입니다.")


if __name__ == "__main__":
    asyncio.run(main())
