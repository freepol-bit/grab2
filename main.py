from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
import requests
import re
import os

app = FastAPI()

# 📂 저장용 폴더 설정
TMP_DIR = "tmp"
if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)

# 🌐 생성된 파일을 웹에서 직접 접근 가능하게 설정 (예: /tmp/파일명.txt)
app.mount("/tmp", StaticFiles(directory=TMP_DIR), name="tmp")

# ✨ 텍스트 정제 함수
def clean_text(raw_html):
    if not raw_html:
        return ""
    clean = re.sub(r'<[^>]*>', ' ', raw_html)
    clean = re.sub(r'\?.*?\?', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

@app.get("/", response_class=PlainTextResponse)
def root():
    return "SKEY를 입력하세요. 예: /4920032005919"

@app.get("/{skey}", response_class=PlainTextResponse)
def get_patent_data(skey: str):
    # 1️⃣ 이미 저장된 파일이 있는지 확인
    file_path = os.path.join(TMP_DIR, f"{skey}.txt")
    
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    # 2️⃣ 파일이 없으면 데이터 수집 시작
    base_url = "https://sd.wips.co.kr/wipslink/doc/docContJson.wips"
    tabs = ["DS", "AB", "CL"]
    headers = {"User-Agent": "Mozilla/5.0"}
    raw = {}

    try:
        for tab in tabs:
            url = f"{base_url}?skey={skey}&tabGb={tab}"
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            raw[tab] = resp.json()

        ab = raw.get("AB", {})
        ds = raw.get("DS", {})
        cl = raw.get("CL", {})

        # 데이터 추출 및 가공
        title = "제목 없음"
        try:
            inv_ti_list = ab.get("docPageSummaryRsltVO", {}).get("invTiList", [])
            if inv_ti_list: title = clean_text(inv_ti_list[0].get("invTi"))
        except: pass

        pub_num = ab.get("docPageSummaryRsltVO", {}).get("mngNum") or "정보 없음"
        app_num = ab.get("docPageSummaryRsltVO", {}).get("applNum") or "정보 없음"

        abstract = "요약 정보가 없습니다."
        try:
            ab_list = ab.get("docPageSummaryRsltVO", {}).get("abList", [])
            if len(ab_list) > 1: abstract = clean_text(ab_list[1].get("ab"))
        except: pass

        lines = [
            "========================================",
            f" 특허 정보 보고서 (SKEY: {skey})",
            "========================================",
            f"제목    : {title}",
            f"공개번호: {pub_num}",
            f"출원번호: {app_num}",
            "\n[요약]",
            f"{abstract}",
            "\n[청구항]"
        ]
        
        claims = [c.get("cl") for c in cl.get("clList", []) if c.get("cl")]
        if claims:
            for i, claim in enumerate(claims, 1):
                lines.append(f"제 {i}항: {clean_text(claim)}")
        else:
            lines.append("청구항 정보가 없습니다.")

        lines.append("\n[상세설명]")
        description = [d.get("dtlDesc") for d in ds.get("descList", []) if d.get("dtlDesc")]
        if description:
            for d in description:
                lines.append(clean_text(d))
        else:
            lines.append("상세설명 정보가 없습니다.")

        lines.append("\n--- 리포트 끝 ---")
        
        result_text = "\n".join(lines)

        # 3️⃣ 결과를 tmp 폴더에 저장
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(result_text)

        return result_text

    except Exception as e:
        return f"데이터 처리 중 오류 발생: {str(e)}"
