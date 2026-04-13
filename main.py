from fastapi import FastAPI, Response
from fastapi.responses import PlainTextResponse # 텍스트 출력을 위한 라이브러리
import requests
import re

app = FastAPI()

# ✨ 텍스트 정제 함수
def clean_text(raw_html):
    if not raw_html:
        return ""
    clean = re.sub(r'<[^>]*>', ' ', raw_html)
    clean = re.sub(r'\?.*?\?', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

@app.get("/")
def root():
    return {"message": "SKEY를 입력하면 텍스트 결과가 출력됩니다. 예: /{skey}"}

@app.get("/{skey}", response_class=PlainTextResponse) # 반환 타입을 텍스트로 지정
def get_data(skey: str):
    base_url = "https://sd.wips.co.kr/wipslink/doc/docContJson.wips"
    tabs = ["DS", "AB", "CL"]
    headers = {"User-Agent": "Mozilla/5.0"}
    raw = {}

    try:
        for tab in tabs:
            url = f"{base_url}?skey={skey}&tabGb={tab}"
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            raw[tab] = resp.json()

        ab = raw.get("AB", {})
        ds = raw.get("DS", {})
        cl = raw.get("CL", {})

        # 데이터 추출
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

        # 📄 텍스트 결과물 조립
        lines = []
        lines.append(f"========================================")
        lines.append(f" 특허 정보 보고서 (SKEY: {skey})")
        lines.append(f"========================================")
        lines.append(f"제목    : {title}")
        lines.append(f"공개번호: {pub_num}")
        lines.append(f"출원번호: {app_num}")
        lines.append(f"\n[요약]")
        lines.append(f"{abstract}")
        
        lines.append(f"\n[청구항]")
        claims = [c.get("cl") for c in cl.get("clList", []) if c.get("cl")]
        if claims:
            for i, claim in enumerate(claims, 1):
                lines.append(f"제 {i}항: {clean_text(claim)}")
        else:
            lines.append("청구항 정보가 없습니다.")

        lines.append(f"\n[상세설명]")
        description = [d.get("dtlDesc") for d in ds.get("descList", []) if d.get("dtlDesc")]
        if description:
            for d in description:
                lines.append(clean_text(d))
        else:
            lines.append("상세설명 정보가 없습니다.")

        lines.append(f"\n--- 리포트 끝 ---")

        # 리스트를 하나의 문자열로 합쳐서 반환
        return "\n".join(lines)

    except Exception as e:
        return f"데이터를 가져오는 중 오류가 발생했습니다:\n{str(e)}"
