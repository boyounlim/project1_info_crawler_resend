import os
import logging
import pandas as pd
from datetime import datetime

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

# HTML 이메일 템플릿 정의 (흰색 배경, 진한 남색 헤더, 연한 회색 카드, 초록색 성공 상태 배지)
HTML_HEADER = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI & IT 트렌드 / 정책 주간 리포트</title>
    <style>
        body {
            font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
            background-color: #ffffff; /* 흰색 배경 */
            color: #1f2937;
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }
        .container {
            max-width: 680px;
            margin: 30px auto;
            background-color: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #e5e7eb;
        }
        .header {
            background-color: #0f172a; /* 진한 남색 헤더 */
            color: #ffffff;
            padding: 35px 25px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        .header p {
            margin: 8px 0 0 0;
            font-size: 14px;
            color: #94a3b8;
        }
        .content {
            padding: 25px;
        }
        .subtitle {
            font-size: 18px;
            font-weight: 700;
            color: #0f172a;
            border-bottom: 2px solid #0f172a;
            padding-bottom: 8px;
            margin-top: 0;
            margin-bottom: 20px;
        }
        .article-card {
            background-color: #f9fafb; /* 연한 회색 카드 */
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 18px;
            margin-bottom: 18px;
        }
        .article-meta {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 12px;
            color: #6b7280;
        }
        .source-tag {
            background-color: #e5e7eb;
            color: #374151;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
        }
        .score-badge {
            background-color: #dcfce7; /* 초록색 성공 상태 배지 */
            color: #16a34a; /* 초록색 텍스트 */
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
        }
        .article-title {
            margin: 0 0 8px 0;
            font-size: 16px;
            font-weight: 700;
            color: #111827;
            line-height: 1.4;
        }
        .article-summary {
            margin: 0 0 14px 0;
            font-size: 13px;
            color: #4b5563;
            text-align: justify;
        }
        .article-link {
            display: inline-block;
            background-color: #0f172a; /* 진한 남색 버튼 */
            color: #ffffff;
            text-decoration: none;
            font-size: 12px;
            font-weight: 600;
            padding: 6px 12px;
            border-radius: 4px;
        }
        .footer {
            background-color: #f9fafb;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #9ca3af;
            border-top: 1px solid #e5e7eb;
        }
        .footer p {
            margin: 4px 0;
        }
        .footer a {
            color: #0f172a;
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 헤더 영역 -->
        <div class="header">
            <h1>AI & IT 정책·트렌드 리포트</h1>
            <p>실무 보고용 맞춤형 기술 및 산업 주간 리포트 (추천 TOP 10)</p>
        </div>
        
        <!-- 본문 기사 영역 -->
        <div class="content">
            <div class="subtitle">🔥 최우수 추천 뉴스 TOP 10</div>
"""

HTML_FOOTER = """
        </div>
        
        <!-- 푸터 영역 -->
        <div class="footer">
            <p>본 메일은 수강생님의 맞춤 키워드 선호도를 기반으로 자동 매칭하여 발송된 리포트입니다.</p>
            <p>수집 소스: 전자신문(ETNews), 보안뉴스(Boannews), Google News</p>
            <p>© 2026 AI Policy News Crawler Project. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""

def build_html_article_card(row, index):
    """기사 한 건에 대해 흰색 배경, 남색 헤더, 연회색 카드, 초록 배지 스타일의 HTML 블록을 생성합니다."""
    title = row.get("title", "제목 없음")
    summary = row.get("summary", "요약 정보가 없습니다.")
    if not summary or pd.isna(summary):
        content = str(row.get("content", ""))
        summary = content[:150] + "..." if len(content) > 150 else content
        
    date = row.get("date", "-")
    source_name = row.get("source_name", "기타 출처")
    source_url = row.get("source_url", "#")
    score = int(row.get("recommend_score", 0))
    
    score_html = f'<span class="score-badge">적합도: {score}점 ⭐</span>'
        
    card = f"""
            <!-- 기사 {index} -->
            <div class="article-card">
                <div class="article-meta">
                    <div>
                        <span class="source-tag">{source_name}</span>
                        <span style="margin-left: 8px;">{date}</span>
                    </div>
                    {score_html}
                </div>
                <h3 class="article-title">{index}. {title}</h3>
                <p class="article-summary">{summary}</p>
                <a href="{source_url}" target="_blank" class="article-link">기사 본문 읽기 &rarr;</a>
            </div>
    """
    return card

def build_txt_article(row, index):
    """기사 한 건에 대해 텍스트 기반 포맷의 문자열을 생성합니다."""
    title = row.get("title", "제목 없음")
    summary = row.get("summary", "요약 정보가 없습니다.")
    if not summary or pd.isna(summary):
        content = str(row.get("content", ""))
        summary = content[:150] + "..." if len(content) > 150 else content
        
    date = row.get("date", "-")
    source_name = row.get("source_name", "기타 출처")
    source_url = row.get("source_url", "#")
    score = int(row.get("recommend_score", 0))
    
    txt_block = f"""[{index}] {title}
 - 추천 점수: {score}점 | 출처: {source_name} | 발행일: {date}
 - 요약: {summary.strip()}
 - 원문 링크: {source_url}
----------------------------------------------------------------------
"""
    return txt_block

def main():
    recommended_csv_path = "project1_info_crawler_resend/data/processed/recommended_policy_news.csv"
    reports_dir = "project1_info_crawler_resend/reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    preview_html_path = os.path.join(reports_dir, "email_preview.html")
    preview_txt_path = os.path.join(reports_dir, "email_preview.txt")
    
    if not os.path.exists(recommended_csv_path):
        logging.error(f"Recommended articles file not found: {recommended_csv_path}")
        return
        
    logging.info(f"Loading recommended articles from {recommended_csv_path}...")
    df = pd.read_csv(recommended_csv_path)
    
    # TOP 10으로 제한
    df = df.head(10)
    article_count = len(df)
    logging.info(f"Loaded {article_count} articles to build preview reports (TOP 10 restricted).")
    
    # 1. HTML 리포트 미리보기 생성
    logging.info("Generating HTML email preview report...")
    html_content = HTML_HEADER
    
    for i, (_, row) in enumerate(df.iterrows()):
        html_content += build_html_article_card(row, i+1)
        
    html_content += HTML_FOOTER
    
    with open(preview_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
            
    # 2. Plain Text 리포트 미리보기 생성
    logging.info("Generating TXT email preview report...")
    today_str = datetime.now().strftime("%Y년 %m월 %d일")
    txt_content = f"""======================================================================
📢 AI & IT 정책·트렌드 리포트 (실무 보고용 추천 TOP {article_count})
======================================================================
발행일자: {today_str}
구독 주소: 수강생님 맞춤형 키워드 리포트
수집 대상: 전자신문, 보안뉴스, Google News

AI, 생성형 AI, 자동화, 클라우드, 데이터, 보안, 디지털 전환 트렌드 소식을 받아보세요.

======================================================================
🔥 이번 주 최우수 추천 뉴스 목록 TOP 10
======================================================================

"""
    for i, (_, row) in enumerate(df.iterrows()):
        txt_content += build_txt_article(row, i+1)
        
    txt_content += """
본 메일은 Resend API 연동을 앞두고 생성한 미리보기(Preview) 텍스트 파일입니다.
© 2026 AI Policy News Crawler Project. All rights reserved.
"""
    
    with open(preview_txt_path, "w", encoding="utf-8") as f:
        f.write(txt_content)
        
    logging.info(f"Successfully generated HTML preview: {preview_html_path}")
    logging.info(f"Successfully generated TXT preview: {preview_txt_path}")
    
    print("\n" + "="*50)
    print("             [EMAIL PREVIEW GENERATED]                ")
    print("="*50)
    print(f"HTML 미리보기 경로: {preview_html_path}")
    print(f"TXT 미리보기 경로: {preview_txt_path}")
    print(f"포함된 기사 건수: {article_count} 건")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
