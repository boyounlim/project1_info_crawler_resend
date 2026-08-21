import os
import logging
from datetime import datetime
import csv
from dotenv import load_dotenv
import resend

# 로그 설정
log_dir = "project1_info_crawler_resend/logs"
os.makedirs(log_dir, exist_ok=True)
error_log_path = os.path.join(log_dir, "crawler_error_log.txt")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(error_log_path, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def check_and_generate_previews():
    """미리보기 리포트 파일이 존재하는지 검증하고, 없으면 생성합니다."""
    html_path = "project1_info_crawler_resend/reports/email_preview.html"
    txt_path = "project1_info_crawler_resend/reports/email_preview.txt"
    
    if not os.path.exists(html_path) or not os.path.exists(txt_path):
        logging.info("미리보기 리포트 파일이 발견되지 않았습니다. 자동으로 생성기(email_report_builder.py)를 실행합니다...")
        try:
            from email_report_builder import main as build_previews
            build_previews()
        except Exception as e:
            logging.error(f"미리보기 리포트 자동 생성 실패: {e}")
            raise e
            
    return html_path, txt_path

def is_duplicate_send(receiver_email, subject):
    """중복 발송 방지를 위해 같은 날짜, 같은 제목, 같은 수신자 발송 이력을 검사합니다."""
    log_csv_path = "project1_info_crawler_resend/reports/resend_send_log.csv"
    if not os.path.exists(log_csv_path):
        return False
        
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    try:
        with open(log_csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # csv의 헤더 컬럼: sent_at, receiver_email, subject, status, resend_email_id
                sent_at = row.get("sent_at", "")
                logged_receiver = row.get("receiver_email", "")
                logged_subject = row.get("subject", "")
                logged_status = row.get("status", "")
                
                # 오늘 날짜에 같은 이메일, 같은 제목으로 성공적으로 보낸 기록이 있는 경우 중복으로 처리
                if (sent_at.startswith(today_str) and 
                    logged_receiver.strip() == receiver_email.strip() and 
                    logged_subject.strip() == subject.strip() and 
                    logged_status == "SUCCESS"):
                    return True
    except Exception as e:
        logging.warning(f"발송 로그(CSV) 분석 중 에러 발생 (무시하고 계속 진행): {e}")
        
    return False

def log_send_success(receiver_email, subject, resend_email_id):
    """발송 성공 이력을 reports/resend_send_log.csv 에 저장합니다."""
    log_csv_path = "project1_info_crawler_resend/reports/resend_send_log.csv"
    file_exists = os.path.exists(log_csv_path)
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(log_csv_path, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not file_exists:
                # 헤더 정의
                writer.writerow(["sent_at", "receiver_email", "subject", "status", "resend_email_id"])
            writer.writerow([now_str, receiver_email, subject, "SUCCESS", resend_email_id])
        logging.info(f"Successfully logged send history to {log_csv_path}")
    except Exception as e:
        logging.error(f"발송 로그(CSV) 기록 실패: {e}")

def log_send_failure(error_msg):
    """발송 실패 시 logs/resend_error_log.txt 에 상세 내용을 기록합니다."""
    failure_log_path = "project1_info_crawler_resend/logs/resend_error_log.txt"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(failure_log_path, "a", encoding="utf-8") as f:
            f.write(f"[{now_str}] {error_msg}\n")
        logging.info(f"Logged failure detail to {failure_log_path}")
    except Exception as e:
        logging.error(f"에러 로그 파일 쓰기 실패: {e}")

def main():
    # 1. 환경 변수 로드 (.env 파일이 있으면 읽어옴)
    env_path = "project1_info_crawler_resend/.env"
    
    if os.path.exists(env_path):
        logging.info(f"Loading .env from {env_path}...")
        load_dotenv(dotenv_path=env_path)
    else:
        logging.warning("'.env' 파일이 발견되지 않았습니다. (.env.example 파일을 복사하여 만드실 수 있습니다)")
        load_dotenv() # 시스템 환경 변수 대체 로드
        
    api_key = os.environ.get("RESEND_API_KEY")
    sender = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
    receiver = os.environ.get("RECEIVER_EMAIL")
    enable_send_str = os.environ.get("ENABLE_REAL_EMAIL_SEND", "false").lower()
    enable_send = enable_send_str == "true"
    
    # 이메일 제목 정의
    subject = "[AI & IT 트렌드 리포트] 이번 주 맞춤형 뉴스 추천 20선"
    
    # 미리보기 보고서 경로 확보
    try:
        html_path, txt_path = check_and_generate_previews()
    except Exception:
        logging.error("미리보기 파일을 확보할 수 없어 발송 작업을 중단합니다.")
        return
        
    # 미리보기 내용 읽기
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    with open(txt_path, "r", encoding="utf-8") as f:
        txt_content = f.read()
        
    # 2. 발송 조건(Evaluate) 검증
    if not api_key or not enable_send:
        # 조건 미충족 시 Preview Mode 안내 출력
        print("\n" + "="*70)
        print("               [Resend EMAIL SENDER - PREVIEW MODE]               ")
        print("="*70)
        print("[Tip] 실제 이메일을 발송하려면 다음 단계의 설정이 필요합니다:")
        print("  1. 'project1_info_crawler_resend/.env' 파일을 생성합니다.")
        print("  2. 발급받은 'RESEND_API_KEY'를 입력합니다.")
        print("  3. 'SENDER_EMAIL' 및 'RECEIVER_EMAIL' 주소를 설정합니다.")
        print("  4. 'ENABLE_REAL_EMAIL_SEND' 값을 'true'로 설정합니다.")
        print("-"*70)
        print(f"SENDER_EMAIL (현재 설정): {sender}")
        print(f"RECEIVER_EMAIL (현재 설정): {receiver if receiver else '미지정 (SENDER_EMAIL과 동일하게 전송됨)'}")
        print(f"ENABLE_REAL_EMAIL_SEND: {enable_send_str} (false이므로 시뮬레이션 모드)")
        print("-"*70)
        print("[Check] 생성된 미리보기 파일 확인 경로:")
        print(f"  - HTML: {html_path}")
        print(f"  - TXT: {txt_path}")
        print("="*70 + "\n")
        return

    # 수신자 이메일 주소 확보
    target_receiver = receiver if receiver else sender
    
    # 3. 중복 발송 방지 가드 (Duplicate Prevention)
    if is_duplicate_send(target_receiver, subject):
        print("\n" + "="*70)
        print("               [Resend EMAIL SENDER - SKIP]               ")
        print("="*70)
        print("[Duplicate Avoided] 중복 발송 방지 시스템이 작동했습니다.")
        print(f"  - 오늘 날짜에 이미 동일한 수신자와 동일한 제목으로 보낸 기록이 있습니다.")
        print(f"  - 대상 수신자: {target_receiver}")
        print(f"  - 제목: {subject}")
        print("  - 실제 전송이 스킵되었습니다. (데이터 무결성 및 스팸 차단)")
        print("="*70 + "\n")
        return

    # 4. 실제 메일 발송 수행
    logging.info("Preparing to send real email via Resend API...")
    resend.api_key = api_key
    
    try:
        params = {
            "from": sender,
            "to": [target_receiver],
            "subject": subject,
            "html": html_content,
            "text": txt_content
        }
        
        logging.info(f"Sending email from '{sender}' to '{target_receiver}'...")
        r = resend.Emails.send(params)
        
        email_id = r.get("id")
        logging.info(f"Successfully sent email! ID: {email_id}")
        
        # 성공 이력 로그 파일에 저장
        log_send_success(target_receiver, subject, email_id)
        
        print("\n" + "="*70)
        print("               [Resend EMAIL SENDER - SUCCESS]               ")
        print("="*70)
        print("[Success] 성공적으로 이메일 발송 요청을 처리했습니다!")
        print(f"  - 발송 ID: {email_id}")
        print(f"  - 보낸 사람: {sender}")
        print(f"  - 받는 사람: {target_receiver}")
        print(f"  - 제목: {subject}")
        print("="*70 + "\n")
        
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Resend API 호출 중 에러 발생: {error_msg}")
        
        # 실패 이력 logs/resend_error_log.txt 에 저장
        log_send_failure(error_msg)
        
        print("\n" + "="*70)
        print("               [Resend EMAIL SENDER - ERROR]               ")
        print("="*70)
        print("[Error] 이메일 발송 중 에러가 발생했습니다.")
        print(f"  상세 에러 내용: {error_msg}")
        print("-"*70)
        
        # 403 오류 또는 도메인 검증 안내 (Iterate)
        if "403" in error_msg or "unauthorized" in error_msg.lower() or "validation" in error_msg.lower() or "permission" in error_msg.lower():
            print("[403 Forbidden / 도메인 인증 오류 해결 가이드]")
            print("  Resend 서비스는 스팸 방지를 위해 매우 엄격한 보안을 유지합니다.")
            print("  따라서 무료 티어(Free Tier)의 경우 아래의 규칙을 반드시 준수하셔야 합니다:")
            print("")
            print("  1. SENDER_EMAIL 설정:")
            print("     - 도메인 검증을 마치지 않았다면, 반드시 기본 발신자 주소인")
            print("       'onboarding@resend.dev' 로 지정해야 전송됩니다.")
            print("  2. RECEIVER_EMAIL 설정:")
            print("     - 무료 계정은 오직 'Resend 가입 시 회원가입용으로 인증된 본인 이메일'")
            print("       로만 메일을 보낼 수 있습니다. 임의의 외부 주소 전송은 차단됩니다.")
            print("  3. 도메인 직접 추가 및 DNS 레코드 등록 (옵션):")
            print("     - 본인의 고유 도메인 이메일로 불특정 다수에게 발송하고 싶다면,")
            print("       Resend 대시보드의 'Domains' 탭에서 도메인을 추가하고 MX/TXT 등")
            print("       DNS 레코드 검증을 완료하셔야 도메인 발신권한이 허용됩니다.")
        else:
            print("[Tip] Resend API Key가 올바른지, 인터넷 연결이 유효한지 검사해주십시오.")
        print("="*70 + "\n")

if __name__ == "__main__":
    main()
