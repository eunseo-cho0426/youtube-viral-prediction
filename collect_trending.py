"""
YouTube 국가별 인기 급상승(mostPopular) 영상 수집 스크립트

실행 전 준비
1) pip install requests pandas python-dotenv tqdm
2) 같은 폴더에 .env 파일을 만들고 아래 한 줄 입력 (이 파일은 GitHub에 올리지 않음)
   YOUTUBE_API_KEY=발급받은_키
"""
import os

import pandas as pd
import requests
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
if not API_KEY:
    raise SystemExit("YOUTUBE_API_KEY가 없습니다. .env 파일을 확인하세요.")

BASE = "https://www.googleapis.com/youtube/v3"
REGIONS = ["US", "GB", "DE", "KR", "JP", "IN", "BR", "MX", "ID", "PH"]
MAX_PAGES = 4  # 50개씩 최대 4페이지


def get_category_map(region: str) -> dict:
    params = {"part": "snippet", "hl": "en", "regionCode": region, "key": API_KEY}
    r = requests.get(f"{BASE}/videoCategories", params=params, timeout=30).json()
    return {item["id"]: item["snippet"]["title"] for item in r.get("items", [])}


def get_trending_videos(region: str) -> list:
    items, page_token = [], None
    for _ in range(MAX_PAGES):
        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": region,
            "maxResults": 50,
            "key": API_KEY,
        }
        if page_token:
            params["pageToken"] = page_token  # 다음 페이지 요청
        r = requests.get(f"{BASE}/videos", params=params, timeout=30).json()
        items.extend(r.get("items", []))
        page_token = r.get("nextPageToken")
        if not page_token:
            break
    return items


def main():
    rows = []
    for region in tqdm(REGIONS):
        cat = get_category_map(region)
        for v in get_trending_videos(region):
            s, st = v["snippet"], v.get("statistics", {})
            rows.append({
                "region": region,
                "videoId": v["id"],
                "title": s.get("title", ""),
                "channelTitle": s.get("channelTitle", ""),
                "categoryId": s.get("categoryId", ""),
                "categoryName": cat.get(s.get("categoryId", ""), "Unknown"),
                "publishedAt": s.get("publishedAt", ""),
                "tags": ",".join(s.get("tags", [])),
                "viewCount": int(st.get("viewCount", 0)),
                "likeCount": int(st.get("likeCount", 0)),
                "commentCount": int(st.get("commentCount", 0)),
            })

    df = pd.DataFrame(rows).drop_duplicates(["region", "videoId"])
    # Excel은 시간대 정보가 있는 날짜를 저장하지 못하므로 UTC 기준으로 변환 후 제거
    df["publishedAt"] = pd.to_datetime(df["publishedAt"], utc=True).dt.tz_localize(None)
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/youtube_trending.csv", index=False, encoding="utf-8-sig")
    print(df.groupby("region").size())


if __name__ == "__main__":
    main()
