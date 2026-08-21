import os
import re
import logging
import pandas as pd
from bs4 import BeautifulSoup

# 로그 설정
log_dir = "project1_info_crawler_resend/logs"
os.makedirs(log_dir, exist_ok=True)
error_log_path = os.path.join(log_dir, "crawler_error_log.txt") # 기존 에러 로그에 누적 기록

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(error_log_path, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# 추천 가중치 키워드 정의
KEYWORDS = ["AI", "생성형 AI", "자동화", "클라우드", "데이터", "보안", "디지털 전환"]

def clean_html_and_formatting(text):
    """HTML 태그 제거 및 연속된 공백 정제"""
    if not text or pd.isna(text):
        return ""
    # BeautifulSoup을 이용해 HTML 잔여 태그 완벽히 정제
    soup = BeautifulSoup(str(text), "lxml")
    cleaned = soup.get_text()
    # 개행 및 불필요한 특수 공백 정제
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def clean_boilerplate_and_ads(text):
    """광고, 저작권, 이메일, 기자 서명 등 기사 내 노이즈 및 Boilerplate 제거"""
    if not text:
        return ""
        
    # 1. 이메일 주소 제거
    text = re.sub(r'[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]+', '', text)
    
    # 2. 문장 단위 분할 및 필터링
    # 문장 끝(. )을 기준으로 쪼개어 검사
    sentences = re.split(r'\.\s+', text)
    cleaned_sentences = []
    
    ad_keywords = [
        "무단전재", "재배포금지", "재배포 금지", "저작권자", "Copyright", "copyright",
        "기자 =", "기자=", "제보", "구독", "네이버 채널", "네이버뉴스", "공식 홈페이지",
        "▶", "ⓒ", "일러스트=", "사진=", "출처=", "협찬", "광고", "다운로드 받으세요"
    ]
    
    for sent in sentences:
        sent_strip = sent.strip()
        if not sent_strip:
            continue
            
        # 광고 및 기자 정보 성향 문장 필터링
        if any(kw in sent_strip for kw in ad_keywords):
            continue
            
        # 기자의 이름 등 짧은 서명 문장 제외
        if len(sent_strip) < 12 and ("기자" in sent_strip or "특파원" in sent_strip or "필자" in sent_strip):
            continue
            
        cleaned_sentences.append(sent_strip)
        
    # 문장들을 마침표로 재결합
    if cleaned_sentences:
        joined_text = ". ".join(cleaned_sentences)
        if not joined_text.endswith("."):
            joined_text += "."
        return joined_text
    return ""

def get_jaccard_similarity(str1, str2):
    """두 문자열의 단어(2글자 이상 한글/영문/숫자) 집합을 기반으로 Jaccard 유사도를 계산합니다."""
    words1 = set([w for w in re.findall(r'[가-힣a-zA-Z0-9]{2,}', str1)])
    words2 = set([w for w in re.findall(r'[가-힣a-zA-Z0-9]{2,}', str2)])
    
    if not words1 or not words2:
        return 0.0
        
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    return len(intersection) / len(union)

def deduplicate_articles(df):
    """제목의 Jaccard 유사도를 비교하여 유사 기사를 탐지 및 제거합니다."""
    # 본문 길이가 긴 기사를 우선순위로 남겨 정보 수집력을 최대화합니다.
    df['content_len'] = df['content'].apply(lambda x: len(str(x)))
    df = df.sort_values(by='content_len', ascending=False).copy()
    
    unique_indices = []
    seen_titles = []
    removed_count = 0
    
    for idx, row in df.iterrows():
        title = str(row['title']).strip()
        is_duplicate = False
        
        for seen_title in seen_titles:
            # 1. 완전 일치 중복 제거
            if title == seen_title:
                is_duplicate = True
                break
            # 2. 제목 Jaccard 유사도 비교 (임계치 0.5 초과 시 유사 기사로 간주)
            sim = get_jaccard_similarity(title, seen_title)
            if sim > 0.5:
                is_duplicate = True
                break
                
        if not is_duplicate:
            unique_indices.append(idx)
            seen_titles.append(title)
        else:
            removed_count += 1
            
    df_dedup = df.loc[unique_indices].copy()
    df_dedup.drop(columns=['content_len'], inplace=True)
    return df_dedup, removed_count

def calculate_score(title, content):
    """제목(가중치 10) 및 본문(가중치 1) 내 추천 키워드 매칭 스코어를 산출합니다."""
    if not title or not content:
        return 0.0
        
    title_upper = str(title).upper()
    content_upper = str(content).upper()
    
    score = 0.0
    
    for kw in KEYWORDS:
        kw_upper = kw.upper()
        # 제목 매칭 수 * 10
        title_matches = title_upper.count(kw_upper)
        # 본문 매칭 수 * 1
        content_matches = content_upper.count(kw_upper)
        
        score += (title_matches * 10) + content_matches
        
    return score

def main():
    raw_csv_path = "project1_info_crawler_resend/data/raw/crawled_policy_news.csv"
    processed_dir = "project1_info_crawler_resend/data/processed"
    os.makedirs(processed_dir, exist_ok=True)
    
    cleaned_csv_path = os.path.join(processed_dir, "cleaned_policy_news.csv")
    recommended_csv_path = os.path.join(processed_dir, "recommended_policy_news.csv")
    
    if not os.path.exists(raw_csv_path):
        logging.error(f"Raw data file not found: {raw_csv_path}")
        return
        
    logging.info(f"Loading raw data from {raw_csv_path}...")
    df = pd.read_csv(raw_csv_path)
    initial_count = len(df)
    
    # 1. 결측 제목/본문 제거
    logging.info("Step 1: Removing missing titles and contents...")
    # 비어있는 문자열도 결측으로 변환 후 제거
    df['title'] = df['title'].fillna("").astype(str).str.strip()
    df['content'] = df['content'].fillna("").astype(str).str.strip()
    
    null_rows_df = df[(df['title'] == "") | (df['content'] == "")]
    null_removed_count = len(null_rows_df)
    
    df_filtered = df[(df['title'] != "") & (df['content'] != "")].copy()
    
    # 2. 너무 짧은 본문 필터링 (100자 미만 기사 제거)
    logging.info("Step 2: Filtering out very short article contents...")
    df_filtered = df_filtered[df_filtered['content'].apply(lambda x: len(str(x)) >= 100)].copy()
    short_removed_count = (initial_count - null_removed_count) - len(df_filtered)
    
    # 3. HTML 태그 및 광고 문구 정제 (Boilerplate Cleaning)
    logging.info("Step 3: Cleaning HTML tags, formatting, and ads/boilerplate text...")
    df_filtered['content'] = df_filtered['content'].apply(clean_html_and_formatting)
    df_filtered['content'] = df_filtered['content'].apply(clean_boilerplate_and_ads)
    
    # 4. 중복 및 유사 기사 제거 (Deduplication)
    logging.info("Step 4: Performing similarity deduplication on titles...")
    df_cleaned, duplicates_removed_count = deduplicate_articles(df_filtered)
    
    # 5. 추천 점수 계산
    logging.info("Step 5: Calculating recommendation scores...")
    df_cleaned['recommend_score'] = df_cleaned.apply(
        lambda row: calculate_score(row['title'], row['content']), axis=1
    )
    
    # 6. 최종 정제 데이터 저장 (cleaned_policy_news.csv)
    logging.info(f"Saving cleaned dataset (total: {len(df_cleaned)} rows) to {cleaned_csv_path}...")
    df_cleaned.to_csv(cleaned_csv_path, index=False, encoding="utf-8-sig")
    
    # 7. 추천 상위 20건 정렬 및 추출 (recommended_policy_news.csv)
    logging.info("Step 6: Extracting top 20 recommended articles...")
    df_recommended = df_cleaned.sort_values(by='recommend_score', ascending=False).head(20).copy()
    df_recommended.to_csv(recommended_csv_path, index=False, encoding="utf-8-sig")
    logging.info(f"Saved top 20 recommendations to {recommended_csv_path}")
    
    # 결과 평가 출력 (Evaluate)
    total_cleaned_count = len(df_cleaned)
    top_5_recommendations = df_recommended.head(5)[['title', 'recommend_score']].to_dict(orient='records')
    
    print("\n" + "="*50)
    print("               [CLEANER RUN EVALUATION]               ")
    print("="*50)
    print(f"초기 수집 기사 수: {initial_count} 건")
    print(f"제거된 결측/무효 기사 수: {null_removed_count} 건")
    print(f"제거된 너무 짧은 본문 수 (<100자): {short_removed_count} 건")
    print(f"제거된 중복/유사 기사 수: {duplicates_removed_count} 건")
    print(f"최종 정제 완료 기사 수: {total_cleaned_count} 건")
    print("-"*50)
    print("추천 상위 5건 기사 목록 (Top 5 Recommended):")
    for i, rec in enumerate(top_5_recommendations):
        print(f" {i+1}. [점수: {int(rec['recommend_score'])}점] {rec['title']}")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
