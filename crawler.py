import os
import re
import time
import hashlib
import logging
from datetime import datetime
import xml.etree.ElementTree as ET
import requests
import feedparser
from bs4 import BeautifulSoup
import pandas as pd

# 로그 설정
log_dir = "project1_info_crawler_resend/logs"
os.makedirs(log_dir, exist_ok=True)
error_log_path = os.path.join(log_dir, "crawler_error_log.txt")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(error_log_path, encoding="utf-8"),
        logging.StreamSender if hasattr(logging, "StreamSender") else logging.StreamHandler()
    ]
)

# 기본 HTTP 헤더 설정
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
}

def clean_html_tags(text):
    """HTML 태그 및 불필요한 공백을 정제합니다."""
    if not text:
        return ""
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    # HTML 엔티티 변환
    text = re.sub(r'&[^;]+;', ' ', text)
    # 연속된 공백 및 줄바꿈 정제
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_date(date_val):
    """다양한 날짜 형식을 YYYY-MM-DD 형식으로 변환합니다."""
    if not date_val:
        return datetime.today().strftime("%Y-%m-%d")
    
    # 1. 만약 time.struct_time 또는 tuple인 경우
    if isinstance(date_val, (time.struct_time, tuple)):
        try:
            return time.strftime("%Y-%m-%d", date_val)
        except Exception:
            pass
            
    # 그 외의 경우 문자열로 변환하여 처리
    date_str = str(date_val).strip()
    
    # 대표적인 날짜 형식 파싱 시도
    formats = [
        "%a, %d %b %Y %H:%M:%S %z", # RFC 822 (e.g. Thu, 20 Aug 2026 15:40:00 +0900)
        "%a, %d %b %Y %H:%M:%S %Z", # RFC 822 (e.g. Thu, 20 Aug 2026 15:40:00 KST)
        "%Y-%m-%dT%H:%M:%S%z",      # ISO 8601
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y.%m.%d"
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
            
    # 정규식으로 YYYY.MM.DD 또는 YYYY-MM-DD 추출 시도
    match = re.search(r'(\d{4})[-./](\d{1,2})[-./](\d{1,2})', date_str)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
        
    return datetime.today().strftime("%Y-%m-%d")

def generate_article_id(url):
    """URL을 기반으로 고유한 article_id (MD5)를 생성합니다."""
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def scrape_full_content(url):
    """기사 URL에 접근하여 본문을 스크래핑합니다."""
    try:
        # 사이트 과부하 방지를 위한 딜레이
        time.sleep(1.0)
        
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            logging.error(f"Failed to fetch content from {url} (Status: {response.status_code})")
            return ""
            
        # 인코딩 자동 감지 및 설정
        response.encoding = response.apparent_encoding
        html = response.text
        soup = BeautifulSoup(html, "lxml")
        
        # 불필요한 태그 제거
        for tag in soup(["script", "style", "header", "footer", "nav", "aside", "noscript", "iframe"]):
            tag.decompose()
            
        # 1. 사이트별 특화 본문 영역 추출
        content_div = None
        
        # 보안뉴스
        if "boannews.com" in url:
            content_div = soup.find("div", id="news_content")
        # 전자신문
        elif "etnews.com" in url:
            content_div = soup.find("div", itemprop="articleBody") or soup.find("div", class_="article_txt")
            
        # 2. 일반적인 본문 영역 추정
        if not content_div:
            # 다양한 클래스명 매핑
            selectors = [
                ("div", {"class": "article_body"}),
                ("div", {"class": "article-body"}),
                ("div", {"class": "article_content"}),
                ("div", {"class": "article-content"}),
                ("div", {"class": "entry-content"}),
                ("div", {"class": "story-content"}),
                ("div", {"class": "news_content"}),
                ("div", {"class": "news_body"}),
                ("div", {"id": "articleBody"}),
                ("div", {"id": "article_body"}),
                ("article", {})
            ]
            for tag_name, attrs in selectors:
                content_div = soup.find(tag_name, attrs)
                if content_div:
                    break
                    
        # 3. 본문 텍스트 추출 및 결합
        if content_div:
            # 본문 내의 p 태그나 텍스트 수집
            paragraphs = content_div.find_all("p")
            if paragraphs:
                text = "\n".join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
            else:
                text = content_div.get_text()
        else:
            # p 태그가 있으면 p 태그들만 결합
            paragraphs = soup.find_all("p")
            if len(paragraphs) > 3:
                text = "\n".join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
            else:
                # 최후의 수단: body 전체 텍스트
                text = soup.body.get_text() if soup.body else ""
                
        # 텍스트 정제
        cleaned_text = clean_html_tags(text)
        
        # 너무 짧은 텍스트는 제대로 긁어오지 못한 것으로 판단
        if len(cleaned_text) < 100:
            return ""
            
        return cleaned_text
        
    except Exception as e:
        logging.error(f"Error scraping {url}: {str(e)}")
        return ""

def fetch_rss_feeds():
    """정의된 RSS 피드 소스들로부터 메타데이터를 수집합니다."""
    # 1. 기본 RSS 소스 목록
    rss_sources = [
        {"name": "전자신문(AI)", "url": "http://rss.etnews.com/04046.xml"},
        {"name": "전자신문(SW)", "url": "http://rss.etnews.com/04.xml"},
        {"name": "전자신문(IT전체)", "url": "http://rss.etnews.com/03.xml"},
        {"name": "보안뉴스(보안)", "url": "http://www.boannews.com/media/news_rss.xml?mkind=1"},
        {"name": "보안뉴스(IT)", "url": "http://www.boannews.com/media/news_rss.xml?mkind=2"}
    ]
    
    # 2. 구글 뉴스 검색 RSS (키워드 기반 수집 보완)
    keywords = [
        "인공지능 AI",
        "클라우드 Cloud",
        "디지털 전환 DX",
        "자동화 RPA",
        "정보보안 정보보호"
    ]
    
    for kw in keywords:
        encoded_kw = requests.utils.quote(kw)
        google_rss_url = f"https://news.google.com/rss/search?q={encoded_kw}&hl=ko&gl=KR&ceid=KR:ko"
        rss_sources.append({"name": f"구글뉴스({kw})", "url": google_rss_url})
        
    all_entries = []
    seen_urls = set()
    
    logging.info("Starting RSS feed retrieval...")
    
    for src in rss_sources:
        try:
            logging.info(f"Parsing RSS: {src['name']} ({src['url']})")
            feed = feedparser.parse(src['url'])
            
            if feed.bozo:
                logging.warning(f"Feed parser reported non-fatal parsing warning for {src['name']}")
                
            entries_count = len(feed.entries)
            logging.info(f"Found {entries_count} entries in {src['name']}")
            
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                
                if not link or link in seen_urls:
                    continue
                    
                seen_urls.add(link)
                
                # 발행일 추출
                pub_date_raw = entry.get("published_parsed") or entry.get("published") or entry.get("updated")
                if pub_date_raw:
                    pub_date = parse_date(pub_date_raw)
                else:
                    pub_date = datetime.today().strftime("%Y-%m-%d")
                    
                # 요약문(description) 추출 및 정제
                summary_raw = entry.get("description") or entry.get("summary", "")
                summary = clean_html_tags(summary_raw)
                if len(summary) > 200:
                    summary = summary[:200] + "..."
                    
                all_entries.append({
                    "title": title,
                    "source_url": link,
                    "date": pub_date,
                    "summary": summary,
                    "source_name": src["name"]
                })
                
        except Exception as e:
            logging.error(f"Failed to parse feed {src['name']}: {str(e)}")
            
    logging.info(f"Completed RSS parsing. Total unique articles collected: {len(all_entries)}")
    return all_entries

def main():
    # 1. RSS 메타데이터 수집
    articles = fetch_rss_feeds()
    
    if len(articles) < 100:
        logging.warning("Initial RSS articles count is very low. Adding fallback RSS search keywords.")
        # 백업 키워드로 추가 구글 뉴스 검색 진행
        fallback_keywords = ["스마트 팩토리", "데이터 플랫폼", "랜섬웨어", "생성형 AI"]
        for kw in fallback_keywords:
            try:
                encoded_kw = requests.utils.quote(kw)
                google_rss_url = f"https://news.google.com/rss/search?q={encoded_kw}&hl=ko&gl=KR&ceid=KR:ko"
                logging.info(f"Parsing fallback RSS: 구글뉴스({kw})")
                feed = feedparser.parse(google_rss_url)
                for entry in feed.entries:
                    link = entry.get("link", "").strip()
                    if link and link not in [a["source_url"] for a in articles]:
                        pub_date_raw = entry.get("published_parsed") or entry.get("published")
                        pub_date = parse_date(pub_date_raw)
                        summary = clean_html_tags(entry.get("description", ""))
                        if len(summary) > 200:
                            summary = summary[:200] + "..."
                        articles.append({
                            "title": entry.get("title", "").strip(),
                            "source_url": link,
                            "date": pub_date,
                            "summary": summary,
                            "source_name": f"구글뉴스_백업({kw})"
                        })
            except Exception as e:
                logging.error(f"Failed to fetch fallback keyword {kw}: {str(e)}")
                
    logging.info(f"Final target metadata count: {len(articles)}")
    
    # 2. 본문 스크래핑 진행
    crawled_data = []
    
    # 최소 200건 성공을 위해 여유 있게 수집 대상을 잡음
    # (일부 사이트가 차단하거나 응답이 없을 수 있으므로)
    target_count = min(250, int(len(articles)))
    target_articles = articles[:target_count]
    
    logging.info(f"Starting detail page scraping for top {len(target_articles)} articles...")
    
    success_count = 0
    
    for i, art in enumerate(target_articles):
        logging.info(f"[{i+1}/{len(target_articles)}] Scraping: {art['title']} ({art['source_url']})")
        
        # 본문 스크래핑
        full_content = scrape_full_content(art["source_url"])
        
        # 결측 여부 체크용 변수
        content_source = "scraped"
        
        # 스크래핑이 실패한 경우 (또는 너무 짧은 경우) 피드의 요약 정보를 대체 본문으로 사용 (Fallback)
        if not full_content:
            full_content = art["summary"]
            content_source = "fallback_summary"
            logging.info("   -> Scraping failed. Fallback to RSS summary.")
            
        # 필수 컬럼 정의 및 결측 판단 (has_null)
        article_id = generate_article_id(art["source_url"])
        title = art["title"]
        date = art["date"]
        collected_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 필수 값 중 하나라도 진짜 비어 있으면 has_null = True
        # (fallback_summary로 content를 채운 것은 null이 아님으로 처리하되, 둘 다 비어있을 경우에만 null 처리)
        is_null_present = not title or not date or not full_content
        
        crawled_data.append({
            "article_id": article_id,
            "title": title,
            "date": date,
            "content": full_content,
            "summary": art["summary"],
            "source_url": art["source_url"],
            "source_name": art["source_name"],
            "collected_at": collected_at,
            "has_null": is_null_present
        })
        
        if not is_null_present:
            success_count += 1
            
        # 실시간 진행 상황 보고 (로그)
        if success_count % 10 == 0:
            logging.info(f"Progress: Collected {success_count} non-null articles so far.")
            
    # 3. CSV 데이터 저장 및 후속 평가
    df = pd.DataFrame(crawled_data)
    
    # 중복 제거 (article_id 기준 최종 점검)
    df.drop_duplicates(subset=["article_id"], keep="first", inplace=True)
    
    raw_data_dir = "project1_info_crawler_resend/data/raw"
    os.makedirs(raw_data_dir, exist_ok=True)
    csv_output_path = os.path.join(raw_data_dir, "crawled_policy_news.csv")
    
    df.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    logging.info(f"Saved crawled data to {csv_output_path}")
    
    # 4. 결과 평가 출력 (Evaluate)
    total_count = len(df)
    null_title_count = df["title"].isna().sum() + (df["title"] == "").sum()
    null_content_count = df["content"].isna().sum() + (df["content"] == "").sum()
    source_stats = df["source_name"].value_counts().to_dict()
    
    print("\n" + "="*50)
    print("               [CRAWLER RUN EVALUATION]               ")
    print("="*50)
    print(f"총 수집 기사 수 (Unique rows): {total_count} 건")
    print(f"결측 제목 수 (Null Title): {null_title_count} 건")
    print(f"결측 본문 수 (Null Content): {null_content_count} 건")
    print("-"*50)
    print("출처(Source)별 수집 통계:")
    for src_name, count in source_stats.items():
        print(f" - {src_name}: {count}건")
    print("="*50 + "\n")
    
    if total_count < 200:
        logging.error(f"Collected count ({total_count}) is less than the required 200. Please run again with more sources.")
    else:
        logging.info(f"Successfully collected {total_count} articles! (Target is 200+)")

if __name__ == "__main__":
    main()
