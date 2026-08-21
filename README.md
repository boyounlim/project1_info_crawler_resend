# 📊 AI & IT 정책·트렌드 자동 수집 및 맞춤형 메일링 솔루션

이 프로젝트는 비전공자 및 초보자도 뉴스 데이터 수집(Crawling), 데이터 정제(Cleaning), 가중치 기반 추천 스코어링, 미려한 이메일 리포트 작성 및 Resend API 라이브 메일 발송까지 **자동화 파이프라인의 모든 과정을 직접 배우고 구동할 수 있도록 설계된 실무형 솔루션**입니다.

---

## 📂 1. 최종 산출물 목록 (Artifacts)

프로젝트 폴더 구조는 아래와 같으며, 수강생이 실습을 완료하는 시점에서 최적화된 결과물들이 각 위치에 저장됩니다.

```text
project1_info_crawler_resend/
├── app/
│   └── dashboard.py           # 📊 실무 보고용 Streamlit 대시보드 애플리케이션
├── data/
│   ├── raw/
│   │   └── crawled_policy_news.csv  # 📥 RSS로 실시간 수집된 원천 뉴스 데이터 (250건)
│   └── processed/
│       ├── cleaned_policy_news.csv  # 🧼 노이즈/중복 제거 및 점수가 연산된 정제 뉴스 (104건)
│       └── recommended_policy_news.csv # 🌟 가중치로 선별된 최종 추천 뉴스 20선
├── reports/
│   ├── email_preview.html     # ✉️ 초보자 가독성을 고려한 모던 이메일 HTML 파일 (TOP 10)
│   ├── email_preview.txt      # 📝 텍스트 전용 뷰어 가독성 맞춤형 plain text 파일 (TOP 10)
│   └── resend_send_log.csv    # 💾 실제 이메일 발송 시간과 발송 ID가 기록되는 데이터베이스
├── logs/
│   ├── crawler_error_log.txt  # ⚠️ 크롤링 중 예외 사항이 누적 기록되는 전체 시스템 로그
│   └── resend_error_log.txt   # ❌ 이메일 전송 API 오류 트래킹 로그
├── crawler.py                 # 🕷️ 다중 RSS 파싱 및 폴백 본문 저장 제어 크롤러
├── cleaner.py                 # 🧼 불필요 텍스트 문장 스크리닝 및 Jaccard 유사도 중복 필터
├── email_report_builder.py    # 🎨 추천 탑 10 뉴스 기반 흰색 배경/남색/연회색 템플릿 메일 빌더
├── send_resend_email.py       # 🚀 시뮬레이션 모드 지원 및 이중 중복 전송 방지 탑재 메일 발송기
├── requirements.txt           # 📦 필요 라이브러리 일괄 정의 문서
├── .env.example               # 🔑 환경설정 템플릿 양식 파일
└── README.md                  # 📘 현재 설명 가이드 (본 문서)
```

---

## ⚙️ 2. 초보자를 위한 단계별 실행 가이드

모든 스크립트는 터미널(PowerShell 또는 CMD)에서 파이썬 명령어로 손쉽게 실행할 수 있습니다.

### [0단계] 필수 패키지 일괄 설치
프로젝트 구동에 필요한 모든 외부 라이브러리를 한 번에 설치합니다.
```powershell
pip install -r project1_info_crawler_resend/requirements.txt
```

### [1단계] 실시간 뉴스 수집 실행 (crawler.py)
구글 뉴스 키워드 RSS와 주요 IT 미디어 RSS 10개 소스를 통해 기사 200건 이상을 수집하여 CSV로 저장합니다.
```powershell
python project1_info_crawler_resend/crawler.py
```

### [2단계] 인공지능 데이터 정제 및 가중치 점수 부여 (cleaner.py)
기사의 불필요한 이메일이나 광고 문구를 제거하고, 제목 간 유사도를 판별해 중복 기사를 스크리닝합니다. 핵심 타겟 키워드 7종에 맞춰 점수를 자동 채점합니다.
```powershell
python project1_info_crawler_resend/cleaner.py
```

### [3단계] 이메일 리포트 미리보기 빌딩 (email_report_builder.py)
정제된 추천 뉴스 중 최상위 **TOP 10**을 선별하여, 실무 보고용 고급 템플릿 스타일(흰색 배경, 남색 헤더, 회색 카드, 초록색 배지)의 HTML 및 텍스트 리포트 파일을 자동으로 생성합니다.
```powershell
python project1_info_crawler_resend/email_report_builder.py
```

### [4단계] 📊 실무 보고용 Streamlit 대시보드 실행
로컬 브라우저를 열고 수집 및 정제된 데이터를 다채로운 차트(매체별 점수 분포, 키워드 순위) 및 카드형 추천 뉴스로 생생하게 모니터링할 수 있습니다.
```powershell
streamlit run project1_info_crawler_resend/app/dashboard.py
```

### [5단계] 🚀 Resend API 실제 메일 발송 가이드
1. `project1_info_crawler_resend/.env` 파일을 만들고 발급받은 API 키와 수신/발신 이메일 주소를 기입합니다.
2. 아래 발송 명령어를 호출하면, **오늘의 이메일 이력 중복 발송을 방지하는 스마트 안심 장치**가 작동하며 수신자 이메일로 1건의 테스트 리포트 메일을 정성스럽게 쏩니다.
```powershell
python project1_info_crawler_resend/send_resend_email.py
```

---

## 🎯 3. 데이터 및 인프라 설계 규격

1. **가중치 적합도 기준:**
   - 핵심 타겟 키워드: `AI`, `생성형 AI`, `자동화`, `클라우드`, `데이터`, `보안`, `디지털 전환`
   - 가중치: **제목 10점**, **본문 1점** 합산 점수 정렬
2. **이메일 및 대시보드 테마 스타일 가이드:**
   - 배경: 흰색 (`#ffffff`) 기반의 플랫한 보고 양식 스타일
   - 헤더 & 버튼: 진한 남색 (`#0f172a`)을 사용해 진중하고 전문적인 실무 신뢰감 부여
   - 카드: 눈의 피로도를 낮추는 연한 회색 (`#f3f4f6` 및 `#f9fafb`)의 카드 레이아웃
   - 점수 배지: 성공 상태를 암시하는 파스텔톤 초록색 (`#dcfce7` 배경 및 `#15803d` 글자)의 성공 상태 배지 디자인
