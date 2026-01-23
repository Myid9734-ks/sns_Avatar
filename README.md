# SNS Avatar

AI 기반 소셜 미디어 콘텐츠 자동화 시스템

## 📋 개요

구글 드라이브에 업로드된 이미지를 AI가 분석하여 고품질 스토리텔링 문구를 생성하고, 텔레그램 승인 과정을 거쳐 페이스북/인스타그램에 자동 게시하는 시스템입니다.

## 🚀 현재 구현 상태

### ✅ 완료된 기능 (1~4단계)

1. **애플리케이션 실행**
   - `main.py` 실행으로 모든 기능 시작
   - 설정 검증 및 초기화

2. **이미지 감지 및 배치 처리**
   - 초기 스캔: 기존 이미지 파일 자동 감지
   - 실시간 감시: watchdog를 사용한 새 파일 감지
   - 파일 안정성 대기: 복사 완료 확인
   - 배치 수집: 10초 동안 수집된 파일 묶음 처리
   - 파일명 일괄 변경: no1, no2, no3... 형식으로 리네임

3. **텔레그램 컨텍스트 요청**
   - 감지된 이미지를 사용자에게 전송
   - 두 가지 옵션 제공:
     - [✍️ 정보 추가하기]: 장소, 경험 등 컨텍스트 입력
     - [🤖 이미지로만 생성]: 이미지만으로 분석 진행

4. **사용자 응답 처리**
   - 버튼 클릭 처리
   - 텍스트 입력 받기
   - 컨텍스트 저장

### 🔨 TODO (향후 구현)

5. **AI 초안 생성 및 캐싱**
6. **텔레그램으로 AI 초안 전달**
7. **텔레그램 최종 승인 및 피드백**
8. **RPA를 통한 소셜 미디어 게시**

## 📁 프로젝트 구조

```
SNS Avatar/
├── src/
│   ├── main.py                 # 애플리케이션 엔트리 포인트
│   ├── shared/                 # 공통 모듈
│   │   ├── __init__.py
│   │   ├── config.py           # 설정 관리 (Singleton)
│   │   ├── logger.py           # 로깅 설정
│   │   ├── exceptions.py       # 커스텀 예외
│   │   ├── constants.py        # 전역 상수
│   │   ├── validators.py       # 검증 함수
│   │   └── utils.py            # 유틸리티 함수
│   ├── file_watcher/           # 파일 감시 모듈
│   │   ├── __init__.py
│   │   ├── watcher.py          # 파일 감시 로직
│   │   └── batch_handler.py    # 배치 처리 로직
│   ├── telegram/               # 텔레그램 봇 모듈
│   │   ├── __init__.py
│   │   ├── bot.py              # 봇 메인
│   │   └── handlers.py         # 메시지 핸들러
│   ├── ai/                     # AI 생성 모듈 (TODO)
│   └── sns/                    # SNS 게시 모듈 (TODO)
├── .env                        # 환경 변수 (git 제외)
├── env.example                 # 환경 변수 템플릿
├── requirements.txt            # 의존성 패키지
├── 개발계획서.md
├── CODING_GUIDELINES.md        # 코딩 가이드라인
└── README.md                   # 이 문서
```

## ⚙️ 설치 및 설정

### 1. 필수 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`env.example` 파일을 복사하여 `.env` 파일을 생성하고 실제 값을 입력하세요.

```bash
copy env.example .env
```

**필수 환경 변수:**

```env
# 이미지 파일 감시 폴더 경로
WATCH_FOLDER_PATH=V:\n8n_test

# 텔레그램 봇 토큰 (BotFather에서 발급)
TELEGRAM_BOT_TOKEN=your_bot_token_here

# 텔레그램 채팅 ID
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 3. 텔레그램 봇 설정

1. **봇 생성**
   - 텔레그램에서 [@BotFather](https://t.me/botfather)와 대화
   - `/newbot` 명령어로 새 봇 생성
   - 봇 토큰을 `.env` 파일의 `TELEGRAM_BOT_TOKEN`에 입력

2. **채팅 ID 확인**
   - 생성한 봇과 대화 시작 (`/start`)
   - 브라우저에서 `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` 접속
   - `"chat":{"id":123456789}` 형식으로 표시된 ID를 확인
   - 해당 ID를 `.env` 파일의 `TELEGRAM_CHAT_ID`에 입력

## 🎯 실행 방법

### 기본 실행

```bash
cd "f:\coding_project\SNS Avatar\src"
python main.py
```

### 실행 순서

1. 프로그램이 시작되면 자동으로:
   - 설정 검증
   - 텔레그램 봇 초기화
   - 파일 감시 시작
   - 기존 이미지 파일 스캔 (있는 경우)

2. 감시 폴더에 이미지 추가 시:
   - 자동으로 파일 감지
   - 10초 동안 추가 파일 수집
   - 파일명을 no1, no2... 형식으로 변경
   - 텔레그램으로 알림 전송

3. 텔레그램에서 옵션 선택:
   - **[✍️ 정보 추가하기]**: 사진 설명 입력
   - **[🤖 이미지로만 생성]**: 즉시 진행

4. 준비 완료 (현재는 여기까지 구현됨)

### 종료

`Ctrl+C`를 누르면 안전하게 종료됩니다.

## 🛠️ 기술 스택

- **언어**: Python 3.11+
- **파일 감시**: watchdog
- **메신저**: python-telegram-bot
- **환경변수**: python-dotenv
- **AI**: Google Gemini (향후 구현)

## 📖 개발 가이드

자세한 코딩 규칙은 [CODING_GUIDELINES.md](CODING_GUIDELINES.md)를 참조하세요.

### 핵심 원칙

1. **패턴을 지키라** - 일관된 디렉토리 구조와 네이밍
2. **One Source of Truth** - 중앙 집중식 설정 관리
3. **하드코딩 하지 말자** - 모든 설정은 환경변수로
4. **에러처리를 잘하자** - 명확한 예외 처리와 로깅
5. **함수는 한 가지 책임만** - SRP 원칙 준수
6. **Shared 폴더 관리** - 공통 기능 모듈화

## 🔍 로그

로그 파일은 `logs/` 폴더에 자동으로 생성됩니다:

- `__main__.log` - 메인 애플리케이션 로그
- `file_watcher.watcher.log` - 파일 감시 로그
- `telegram.bot.log` - 텔레그램 봇 로그
- 등등...

## ⚠️ 주의사항

- `.env` 파일은 절대 Git에 커밋하지 마세요 (민감 정보 포함)
- 감시 폴더 경로가 존재하는지 확인하세요
- 텔레그램 봇 토큰과 채팅 ID를 정확히 입력하세요

## 📝 라이센스

Private Project

## 👤 작성자

myid9734

---

**최종 업데이트**: 2026-01-22
