import streamlit as st
import re
import io
import json
import base64
import hashlib
from datetime import datetime
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
from streamlit_local_storage import LocalStorage

# Streamlit 페이지 설정
st.set_page_config(page_title="유튜브 강의 콘텐츠 7종 자동 생성기", layout="wide")
st.title("🎥 유튜브 강의 콘텐츠 7종 자동 생성기")

ARCHIVE_DIR = Path("archive")
ARCHIVE_DIR.mkdir(exist_ok=True)

def archive_path(project_id):
    return ARCHIVE_DIR / f"{project_id}.json"

def save_project(project_id, payload):
    archive_path(project_id).write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )

def load_project(project_id):
    path = archive_path(project_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

def list_projects():
    items = []
    for path in ARCHIVE_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append({
                "id": path.stem,
                "title": data.get("title", "제목 없음"),
                "saved_at": data.get("saved_at", ""),
            })
        except Exception:
            continue
    return sorted(items, key=lambda x: x["saved_at"], reverse=True)

def make_project_id(transcript):
    digest = hashlib.sha1(transcript.encode("utf-8")).hexdigest()[:10]
    return f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{digest}"

PDF_CSS = """
@page { size: A4; margin: 14mm; }
body { font-family: 'HYGothic-Medium'; font-size: 10pt; color: #28251E; }
h1 { font-size: 17pt; color: #AD4F30; margin-bottom: 4mm; }
h2 { font-size: 12pt; color: #AD4F30; margin-top: 5mm; margin-bottom: 2mm;
     border-bottom: 1pt solid #C96442; padding-bottom: 1mm; }
h3 { font-size: 10.5pt; margin-top: 3mm; margin-bottom: 1mm; }
p { margin-bottom: 2mm; line-height: 1.5; }
table { width: 100%; border-collapse: collapse; margin-bottom: 4mm; font-size: 9.5pt; }
th { background-color: #C96442; color: #FFFFFF; padding: 2mm; text-align: left; }
td { border-bottom: 0.5pt solid #E7E1D5; padding: 2mm; }
ul { margin-left: 5mm; margin-bottom: 3mm; }
li { margin-bottom: 1.2mm; line-height: 1.45; }
.lead { color: #57534A; margin-bottom: 4mm; }
.box { background-color: #FBF3DF; padding: 2.5mm; margin-bottom: 2.5mm; }
"""

def build_pdf_bytes(body_html, doc_title):
    """단순 CSS 기반 HTML을 PDF 바이트로 변환합니다.
    xhtml2pdf는 CSS 변수·의사요소를 지원하지 않으므로 전용 마크업을 사용합니다."""
    from reportlab.pdfbase.pdfmetrics import registerFont
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from xhtml2pdf import pisa

    registerFont(UnicodeCIDFont("HYGothic-Medium"))
    doc = (f'<html><head><meta charset="utf-8"><title>{doc_title}</title>'
           f"<style>{PDF_CSS}</style></head><body>{body_html}</body></html>")
    buffer = io.BytesIO()
    result = pisa.CreatePDF(doc, dest=buffer, encoding="utf-8")
    if result.err:
        raise RuntimeError("PDF 변환에 실패했습니다.")
    return buffer.getvalue()

def summary_pdf_bytes(sd, title, speaker):
    body = f"<h1>{title}</h1><p class='lead'>{sd.get('headline','')} — {speaker} 강의 요약</p>"

    numbers = sd.get("key_numbers") or []
    if numbers:
        body += "<h2>핵심 수치</h2><ul>"
        body += "".join(f"<li><b>{n.get('value','')}</b> — {n.get('label','')}</li>" for n in numbers)
        body += "</ul>"

    table = sd.get("comparison_table") or {}
    if table.get("headers") and table.get("rows"):
        body += f"<h2>{table.get('title','비교표')}</h2><table><tr>"
        body += "".join(f"<th>{h}</th>" for h in table["headers"])
        body += "</tr>"
        for row in table["rows"]:
            body += "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
        body += "</table>"

    steps = sd.get("flow_steps") or []
    if steps:
        body += "<h2>절차 흐름</h2><ul>"
        body += "".join(f"<li><b>{s.get('step','')}. {s.get('title','')}</b> — {s.get('desc','')}</li>"
                        for s in steps)
        body += "</ul>"

    points = sd.get("core_points") or []
    if points:
        body += "<h2>반드시 기억할 핵심</h2><ul>"
        body += "".join(f"<li>{p}</li>" for p in points)
        body += "</ul>"

    cautions = sd.get("cautions") or []
    if cautions:
        body += "<h2>주의사항</h2>"
        body += "".join(f"<div class='box'>{c}</div>" for c in cautions)

    return build_pdf_bytes(body, title)

def mindmap_pdf_bytes(md, speaker):
    title = md.get("title", "강의 체계도")
    body = f"<h1>{title}</h1><p class='lead'>{speaker} 강의 체계도</p>"
    for sec in md.get("sections") or []:
        body += f"<h2>{sec.get('name','')}</h2>"
        for grp in sec.get("groups") or []:
            body += f"<h3>{grp.get('name','')}</h3><ul>"
            body += "".join(f"<li>{it}</li>" for it in grp.get("items") or [])
            body += "</ul>"
    return build_pdf_bytes(body, title)

def markdown_to_rich_html(md_text):
    """마크다운을 블로그 편집기에 붙여넣을 수 있는 서식 HTML로 변환합니다.
    외부 CSS가 따라가지 않으므로 표·인용 등에 인라인 스타일을 직접 넣습니다."""
    import markdown as md_lib

    html = md_lib.markdown(md_text, extensions=["tables", "nl2br"])
    replacements = [
        ("<table>", '<table style="border-collapse:collapse;width:100%;margin:16px 0;">'),
        ("<th>", '<th style="border:1px solid #ccc;background:#f5f5f5;padding:8px;text-align:left;">'),
        ("<td>", '<td style="border:1px solid #ccc;padding:8px;">'),
        ("<h2>", '<h2 style="font-size:22px;font-weight:bold;margin:28px 0 12px;">'),
        ("<h3>", '<h3 style="font-size:18px;font-weight:bold;margin:22px 0 10px;">'),
        ("<blockquote>", '<blockquote style="border-left:4px solid #C96442;margin:16px 0;padding:8px 16px;color:#555;">'),
    ]
    for old, new in replacements:
        html = html.replace(old, new)
    # 정렬 스타일이 붙은 th/td도 동일하게 테두리를 갖도록 보정
    html = re.sub(
        r'<(th|td) style="text-align: (left|center|right);">',
        lambda m: (f'<{m.group(1)} style="border:1px solid #ccc;padding:8px;'
                   f'text-align:{m.group(2)};'
                   f'{"background:#f5f5f5;font-weight:bold;" if m.group(1) == "th" else ""}">'),
        html,
    )
    return html

def copy_rich_box(label, html_content, key):
    """서식(굵게·제목·표)이 살아있는 상태로 클립보드에 복사하는 버튼을 렌더링합니다."""
    encoded = base64.b64encode(html_content.encode("utf-8")).decode("ascii")
    st.components.v1.html(
        f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <button id="rb-{key}" style="padding:9px 18px;border-radius:8px;border:none;
    background:#1B7F3B;color:#fff;font-weight:700;cursor:pointer;font-size:14px;">
    ✨ {label} (서식 유지 복사)
  </button>
  <span id="rm-{key}" style="margin-left:10px;color:#1B7F3B;font-weight:700;"></span>
  <div id="rs-{key}" contenteditable="true"
       style="position:fixed;left:-9999px;top:0;width:800px;"></div>
</div>
<script>
(function() {{
  var btn = document.getElementById("rb-{key}");
  var msg = document.getElementById("rm-{key}");
  var stage = document.getElementById("rs-{key}");
  var html = decodeURIComponent(escape(atob("{encoded}")));

  function ok() {{
    msg.textContent = "복사 완료! 블로그에 붙여넣으세요";
    setTimeout(function() {{ msg.textContent = ""; }}, 3000);
  }}

  function legacyCopy() {{
    stage.innerHTML = html;
    var range = document.createRange();
    range.selectNodeContents(stage);
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    var done = document.execCommand("copy");
    sel.removeAllRanges();
    stage.innerHTML = "";
    if (done) {{ ok(); }} else {{ msg.textContent = "복사 실패 — 다시 눌러주세요"; }}
  }}

  btn.addEventListener("click", function() {{
    if (window.ClipboardItem && navigator.clipboard && navigator.clipboard.write) {{
      var item = new ClipboardItem({{
        "text/html": new Blob([html], {{type: "text/html"}}),
        "text/plain": new Blob([stage.textContent || html.replace(/<[^>]+>/g, "")], {{type: "text/plain"}})
      }});
      navigator.clipboard.write([item]).then(ok).catch(legacyCopy);
    }} else {{
      legacyCopy();
    }}
  }});
}})();
</script>
""",
        height=52,
    )

def copy_box(label, text, key):
    """복사 가능한 텍스트 박스를 렌더링합니다."""
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    st.components.v1.html(
        f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <button id="btn-{key}" style="padding:8px 16px;border-radius:8px;border:1px solid #C96442;
    background:#C96442;color:#fff;font-weight:700;cursor:pointer;font-size:14px;">
    📋 {label} 복사하기
  </button>
  <span id="msg-{key}" style="margin-left:10px;color:#2E7D32;font-weight:700;"></span>
</div>
<script>
  document.getElementById("btn-{key}").addEventListener("click", function() {{
    var text = decodeURIComponent(escape(atob("{encoded}")));
    navigator.clipboard.writeText(text).then(function() {{
      document.getElementById("msg-{key}").textContent = "복사 완료!";
      setTimeout(function() {{ document.getElementById("msg-{key}").textContent = ""; }}, 2000);
    }});
  }});
</script>
""",
        height=50,
    )

# API 키 저장/불러오기 (브라우저 localStorage에만 저장, 서버에는 저장되지 않음)
local_storage = LocalStorage()
saved_api_key = local_storage.getItem("gemini_api_key") or ""
api_key = st.sidebar.text_input("Gemini API Key 입력", type="password", value=saved_api_key)
if api_key and api_key != saved_api_key:
    local_storage.setItem("gemini_api_key", api_key, key="save_gemini_api_key")
st.sidebar.caption("🔒 입력한 키는 이 브라우저에만 저장되며, 서버로 전송되지 않습니다.")

def extract_video_id(url):
    regex = r"(?:v=|youtu\.be\/|\/embed\/|\/v\/)([^\"&?\/\s]{11})"
    match = re.search(regex, url)
    return match.group(1) if match else None

def get_youtube_transcript(video_id):
    try:
        ytt_api = YouTubeTranscriptApi()
        fetched_transcript = ytt_api.fetch(video_id, languages=['ko'])
        return " ".join([snippet.text for snippet in fetched_transcript])
    except Exception as e:
        return None

def get_working_model():
    """지금 이 API 키로 실제 사용 가능한 Gemini 모델을 찾아서 반환합니다.
    모델명이 서비스 종료되어도 자동으로 대체 모델을 사용합니다."""
    preferred = [
        "gemini-flash-latest",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-pro-latest",
        "gemini-2.5-pro",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ]
    available = set()
    try:
        for m in genai.list_models():
            if "generateContent" in getattr(m, "supported_generation_methods", []):
                available.add(m.name.split("/")[-1])
    except Exception:
        pass

    candidates = [name for name in preferred if not available or name in available]
    if not candidates and available:
        candidates = list(available)
    if not candidates:
        candidates = preferred

    last_error = None
    for name in candidates:
        try:
            model = genai.GenerativeModel(name)
            return model
        except Exception as e:
            last_error = e
            continue
    raise RuntimeError(f"사용 가능한 Gemini 모델을 찾지 못했습니다: {last_error}")

def clean_transcript_with_ai(model, raw_text):
    prompt = f"""당신은 부동산 공법 강의 전문 편집자입니다.
아래는 유튜브 강의를 그대로 받아쓰기한 원본 스크립트이며, 음성 인식 오타·띄어쓰기 오류·불필요한 추임새가 섞여 있을 수 있습니다.

[처리 지침]
1. 오탈자와 띄어쓰기를 바로잡으세요.
2. 강사가 실제로 말한 내용·순서·의미는 절대 바꾸거나 삭제하지 말고, 문맥에 맞게 문장만 자연스럽게 다듬으세요.
3. 법령명·조문번호·용어가 구어체로 축약되었거나 부정확하면(예: "국토계획법" → "국토의 계획 및 이용에 관한 법률") 공식 법령 명칭과 정확한 용어로 정리하세요. 확실하지 않으면 원문 그대로 두세요.
4. 요약하지 말고, 정리된 전체 전사문(transcript)만 출력하세요. 설명이나 머리말 없이 본문만 출력하세요.

[원본 스크립트]
{raw_text[:15000]}
"""
    response = model.generate_content(prompt)
    return response.text.strip()

def generate_structured_data(model, transcript):
    prompt = f"""
    당신은 전문 법률/강의 콘텐츠 에디터입니다.
    아래 유튜브 강의 전사 내용을 분석하여 웹페이지 생성용 구조화 JSON 데이터를 작성하세요.

    [전사 내용]:
    {transcript[:12000]}

    [요청 사항]:
    - 강의를 5~7개의 파트(Part 1, Part 2 등)로 나누세요.
    - 각 파트별 핵심 제목, 설명, 대표 강사 발언(key_quotes), 주요 학습 포인트(bullet_points), 공략 팁(tips)을 추출하세요.
    - 전체 강의 점검용 체크리스트 항목 5~8개를 작성하세요.

    반드시 아래 JSON 형태로만 응답하세요:
    ```json
    {{
        "title": "강의 제목",
        "speaker": "강사명",
        "summary": "강의 한 줄 요약",
        "parts": [
            {{
                "part_num": "PART 1",
                "title": "파트 제목",
                "subtitle": "파트 설명",
                "key_quotes": ["대표 발언 문구"],
                "bullet_points": ["주요 포인트 1", "주요 포인트 2"],
                "tips": ["공략 팁"]
            }}
        ],
        "checklist": ["체크리스트 1", "체크리스트 2"]
    }}
    ```
    """
    return call_json(model, prompt)

def call_json(model, prompt):
    response = model.generate_content(prompt)
    text = response.text
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return json.loads(match.group(1) if match else text)

def generate_blog_post(model, transcript):
    prompt = f"""당신은 공인중개사 실무 블로그를 운영하는 부동산 전문 작가이자 SEO/AEO 전문가입니다.
아래 강의 내용을 바탕으로, 공인중개사가 자기 블로그에 그대로 올릴 수 있는 완성된 글 한 편을 작성하세요.

[SEO/AEO 작성 원칙]
- 검색 의도를 충족하는 제목: 핵심 키워드를 앞쪽에 배치, 30자 내외
- 첫 문단에서 독자의 질문에 즉시 답하는 요약(AEO 대응, 2~3문장)
- H2/H3 소제목으로 구조화하고, 각 소제목은 검색될 법한 질문형·키워드형으로
- 실제 검색될 롱테일 키워드를 본문에 자연스럽게 배치(키워드 스터핑 금지)
- 표를 최소 1개 포함해 수치·기준을 정리
- "자주 묻는 질문(FAQ)" 섹션 3~5개, 각 답변은 2~3문장 (AEO/스니펫 대응)
- 마지막에 상담 유도 CTA 한 문단
- 문체는 실무자가 고객에게 설명하듯 신뢰감 있고 쉬운 존댓말

[정확성 원칙]
- 강의에 없는 수치·법령·판례를 지어내지 마세요.
- 법령명은 공식 명칭으로 쓰고, 시행 시점이 불확실하면 "확인 필요"로 표시하세요.

[강의 내용]
{transcript[:14000]}

아래 JSON 형태로만 응답하세요:
```json
{{
  "title": "블로그 제목",
  "meta_description": "검색결과에 노출될 요약 (150자 내외)",
  "keywords": ["키워드1", "키워드2", "키워드3"],
  "markdown": "완성된 블로그 본문 전체 (마크다운 형식, 소제목·표·FAQ·CTA 모두 포함)"
}}
```"""
    return call_json(model, prompt)

def generate_summary_data(model, transcript):
    prompt = f"""당신은 부동산 공법 강의 콘텐츠 설계자입니다.
아래 강의 내용을 한눈에 파악할 수 있도록 시각 요약용 데이터를 구성하세요.

[강의 내용]
{transcript[:14000]}

[요청]
- headline: 강의 전체를 한 문장으로
- key_numbers: 강의에 실제 등장한 핵심 수치 3~6개 (없으면 빈 배열)
- comparison_table: 비교·대조가 되는 항목을 표로 (예: 현행법 vs 개정법). headers와 rows 구성
- flow_steps: 절차·순서가 있으면 단계별로 3~7개
- core_points: 반드시 기억할 핵심 4~8개
- cautions: 주의사항·함정 2~5개

강의에 없는 내용은 지어내지 말고, 해당 항목이 없으면 빈 배열로 두세요.

아래 JSON 형태로만 응답하세요:
```json
{{
  "headline": "한 문장 요약",
  "key_numbers": [{{"value": "10m", "label": "현행법 이격 기준"}}],
  "comparison_table": {{"title": "표 제목", "headers": ["구분", "현행법", "개정법"], "rows": [["4층", "1/2 이격", "1/1 이격"]]}},
  "flow_steps": [{{"step": "1", "title": "단계명", "desc": "설명"}}],
  "core_points": ["핵심1", "핵심2"],
  "cautions": ["주의1"]
}}
```"""
    return call_json(model, prompt)

def generate_mindmap_data(model, transcript):
    prompt = f"""당신은 시험 대비 체계도(요약 한 장)를 설계하는 전문가입니다.
아래 강의 내용 전체를 A4 한 장(부족하면 2~3장)에 빈 공백 없이 촘촘히 담을 체계도 데이터를 만드세요.

[강의 내용]
{transcript[:14000]}

[요청]
- 강의의 모든 중요 내용을 빠짐없이 담되, 문장이 아닌 키워드·짧은 구 위주로 압축하세요.
- 대분류(section) 4~8개, 각 대분류마다 중분류(group) 2~5개, 각 중분류마다 항목(items) 2~6개
- 각 항목은 한 줄(최대 40자)로 압축

아래 JSON 형태로만 응답하세요:
```json
{{
  "title": "체계도 제목",
  "sections": [
    {{
      "name": "대분류명",
      "groups": [
        {{"name": "중분류명", "items": ["항목1", "항목2"]}}
      ]
    }}
  ]
}}
```"""
    return call_json(model, prompt)

def generate_mcq(model, transcript, count=5, avoid=None):
    avoid_text = ""
    if avoid:
        avoid_text = "\n\n[이미 출제된 문제 — 중복 금지]\n" + "\n".join(f"- {q}" for q in avoid)
    prompt = f"""당신은 공인중개사 시험 출제위원입니다.
아래 강의 내용을 바탕으로 5지선다 객관식 문제 {count}문제를 출제하세요.

[출제 원칙]
- 강의에서 다룬 법령·기준·수치에 근거해서만 출제하고, 강의에 없는 내용은 출제하지 마세요.
- 실제 시험 문체(~것은?, ~옳은 것은?, ~틀린 것은?)를 사용하세요.
- 보기 5개는 모두 그럴듯해야 하며, 정답은 1~5 중 고르게 분포시키세요.
- 해설은 정답 근거와 오답 이유를 함께 3~5문장으로 쓰세요.{avoid_text}

[강의 내용]
{transcript[:14000]}

아래 JSON 형태로만 응답하세요:
```json
{{
  "questions": [
    {{
      "question": "문제 지문",
      "choices": ["① 보기1", "② 보기2", "③ 보기3", "④ 보기4", "⑤ 보기5"],
      "answer": "③",
      "explanation": "해설"
    }}
  ]
}}
```"""
    return call_json(model, prompt)

def generate_ox(model, transcript, count=10, avoid=None):
    avoid_text = ""
    if avoid:
        avoid_text = "\n\n[이미 출제된 문제 — 중복 금지]\n" + "\n".join(f"- {q}" for q in avoid)
    prompt = f"""당신은 공인중개사 시험 출제위원입니다.
아래 강의 내용을 바탕으로 O/X 문제 {count}문제를 출제하세요.

[출제 원칙]
- 강의에서 다룬 법령·기준·수치에 근거해서만 출제하세요.
- O와 X가 고르게 섞이도록 하세요.
- 틀린 지문은 수치나 요건을 미묘하게 바꿔 실제 시험처럼 만드세요.
- 해설은 2~4문장으로 근거를 밝히세요.{avoid_text}

[강의 내용]
{transcript[:14000]}

아래 JSON 형태로만 응답하세요:
```json
{{
  "questions": [
    {{"question": "지문", "answer": "O", "explanation": "해설"}}
  ]
}}
```"""
    return call_json(model, prompt)

# ================= ==========================================
# 1. SLIDES HTML 템플릿 생성 함수 (juntaekslides.html 스타일)
# ============================================================
def generate_slides_html(data):
    title = data.get("title", "강의 체계도")
    speaker = data.get("speaker", "고상철")
    summary = data.get("summary", "")
    parts = data.get("parts", [])
    checklist = data.get("checklist", [])

    slides_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | {speaker}</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@500;700;900&display=swap">
<style>
  :root{{
    --font:'Pretendard','Pretendard Variable',-apple-system,BlinkMacSystemFont,sans-serif;
    --serif:'Noto Serif KR',serif;
    --cream:#F4F2EB; --cream2:#FAF8F1; --surface:#fff;
    --ink:#28251E; --ink2:#57534A; --ink3:#8B8678;
    --coral:#C96442; --coral2:#AD4F30; --coral-soft:#F5E4DA; --coral-light:#E0876A;
    --line:#E7E1D5; --line2:#D8D1C2;
    --night:#1B1712; --night2:#2A241C;
    --mark-bg:#F6E2B2; --mark-text:#4A3A10;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  html,body{{width:100%;height:100%;overflow:hidden;background:#000}}
  body{{font-family:var(--font);color:var(--ink);-webkit-font-smoothing:antialiased;line-height:1.5;word-break:keep-all;}}
  .deck{{position:relative;width:100vw;height:100vh}}
  .page{{position:absolute;inset:0;padding:7vh 7.5vw;display:flex;flex-direction:column;justify-content:center;opacity:0;pointer-events:none;transition:opacity .5s ease;overflow:hidden}}
  .page.active{{opacity:1;pointer-events:auto}}
  .s-cream{{background:radial-gradient(120% 95% at 50% -8%,#FBF9F3 0%,#F3EFE6 52%,#EFEADF 100%)}}
  .s-night{{background:var(--night);color:#F4F2EB}}
  .s-coral{{background:linear-gradient(140deg,#CF6B47,#AD4A2B);color:#fff}}
  .brand{{position:absolute;top:4.2vh;right:7.5vw;z-index:6;display:inline-flex;align-items:center;gap:.5rem;font-weight:800;font-size:clamp(.85rem,1.3vw,1.12rem);color:var(--ink3)}}
  .brand .bdot{{width:.6rem;height:.6rem;border-radius:50%;background:var(--coral)}}
  .s-night .brand{{color:rgba(244,242,235,.6)}}.s-night .brand .bdot{{background:var(--coral-light)}}
  .s-coral .brand{{color:rgba(255,255,255,.72)}}.s-coral .brand .bdot{{background:#fff}}
  .eyebrow{{display:inline-flex;align-items:center;gap:.5rem;font-size:clamp(.85rem,1.35vw,1.18rem);font-weight:800;color:var(--coral2);background:var(--coral-soft);padding:.5rem 1.1rem;border-radius:999px;margin-bottom:1.4rem}}
  .s-night .eyebrow{{background:rgba(201,100,66,.2);color:#EFA98C}}
  .s-coral .eyebrow{{background:rgba(255,255,255,.18);color:#fff}}
  h1{{font-size:clamp(2.8rem,6.4vw,6rem);font-weight:900;line-height:1.1;letter-spacing:-.035em}}
  h2{{font-size:clamp(2.1rem,4.6vw,4rem);font-weight:900;line-height:1.16;letter-spacing:-.03em}}
  h3{{font-size:clamp(1.5rem,2.8vw,2.4rem);font-weight:900;line-height:1.2;letter-spacing:-.02em}}
  .pop{{color:var(--coral)}}.s-night .pop{{color:var(--coral-light)}}.s-coral .pop,.s-coral h1,.s-coral h2{{color:#fff}}
  .lead{{font-size:clamp(1.15rem,2vw,1.85rem);font-weight:500;line-height:1.55;color:var(--ink2);max-width:42ch;margin-top:1.4rem}}
  .s-night .lead{{color:rgba(244,242,235,.78)}}.s-coral .lead{{color:rgba(255,255,255,.92)}}
  .divline{{height:2px;width:min(520px,55%);background:linear-gradient(90deg,var(--coral),transparent);margin-top:1.8rem}}
  .s-night .divline{{background:linear-gradient(90deg,var(--coral-light),transparent)}}
  .divnumwrap{{position:absolute;right:0;bottom:0;width:60%;height:80%;overflow:hidden;pointer-events:none}}
  .divnum{{position:absolute;right:4vw;bottom:-6vh;font-size:clamp(9rem,24vw,20rem);font-weight:900;line-height:.8;color:rgba(255,255,255,.1)}}
  .divbadge{{display:inline-flex;align-items:center;gap:.6rem;font-size:clamp(1rem,1.7vw,1.5rem);font-weight:900;color:#fff;background:rgba(255,255,255,.16);padding:.5rem 1.3rem;border-radius:999px;margin-bottom:1.5rem}}
  .divsub{{font-size:clamp(1.05rem,1.9vw,1.65rem);font-weight:600;color:rgba(255,255,255,.9);margin-top:1.3rem;max-width:46ch;line-height:1.5}}
  .stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:clamp(1rem,2.5vw,2rem);margin-top:.6rem}}
  .stat .num{{font-size:clamp(2.6rem,6vw,5.4rem);font-weight:900;color:var(--coral)}}
  .stat .unit{{font-size:.42em;font-weight:800;margin-left:.1em}}
  .stat .lab{{font-size:clamp(.95rem,1.5vw,1.3rem);font-weight:700;color:var(--ink2);margin-top:.5rem}}
  .fgrid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:clamp(.7rem,1.4vw,1.2rem);margin-top:.6rem}}
  .fcard{{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:clamp(1.1rem,2.4vh,1.7rem) clamp(.8rem,1.4vw,1.2rem)}}
  .fcard .fname{{font-size:clamp(1.05rem,1.7vw,1.45rem);font-weight:900;margin-bottom:.5rem}}
  .fcard .fmeta{{font-size:clamp(.82rem,1.2vw,1.05rem);color:var(--ink2)}}
  .bul{{margin-top:.6rem;display:flex;flex-direction:column;gap:.6rem;font-size:clamp(1.05rem,1.7vw,1.5rem);font-weight:500;color:var(--ink2)}}
  .bul li{{list-style:none;padding-left:1.7rem;position:relative}}
  .bul li::before{{content:"";position:absolute;left:0;top:.55em;width:.7rem;height:.7rem;border-radius:50%;background:var(--coral)}}
  .quotemark{{font-family:var(--serif);font-size:clamp(3rem,7vw,6rem);font-weight:900;line-height:.6;opacity:.4}}
  .bigstate{{font-size:clamp(2rem,4.6vw,4rem);font-weight:900;line-height:1.22}}
  .checklist{{display:grid;grid-template-columns:1fr 1fr;gap:.5rem .9rem;margin-top:.5rem}}
  .check{{display:flex;align-items:center;gap:.8rem;background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:.7rem 1rem;font-size:clamp(.92rem,1.35vw,1.18rem);font-weight:600}}
  .bar-top{{position:fixed;top:0;left:0;height:5px;background:var(--coral);width:0;z-index:50;transition:width .45s ease}}
  .hud{{position:fixed;left:0;right:0;bottom:0;display:flex;justify-content:space-between;align-items:center;padding:.7rem 1.5rem;font-size:.82rem;font-weight:700;z-index:40}}
  .hud.dark{{color:rgba(40,37,30,.5)}}.hud.light{{color:rgba(255,255,255,.62)}}
</style>
</head>
<body>
<div class="bar-top" id="bar"></div>
<div class="deck" id="deck">

  <!-- S1 표지 -->
  <section class="page s-night active" data-sec="오프닝">
    <span class="brand"><span class="bdot"></span>{speaker} · {title}</span>
    <div class="eyebrow" style="margin-top:2.4rem">강의 체계도 오리엔테이션</div>
    <h1>{title}<br><span class="pop">핵심 체계도</span> 정리</h1>
    <p class="lead">{summary}</p>
    <div class="divline"></div>
    <p style="margin-top:1.4rem;font-weight:800;color:rgba(244,242,235,.85)">완전 정복 | <span style="color:var(--coral-light)">{speaker}</span></p>
  </section>
"""

    # 각 파트별 슬라이드 반복 생성
    for idx, part in enumerate(parts, 1):
        p_num = part.get("part_num", f"PART {idx}")
        p_title = part.get("title", "")
        p_sub = part.get("subtitle", "")
        p_quotes = part.get("key_quotes", [])
        p_bullets = part.get("bullet_points", [])
        p_stats = part.get("stats", [])

        # 디바이더 슬라이드
        slides_html += f"""
  <section class="page s-coral" data-sec="{p_num} · {p_title}">
    <span class="brand"><span class="bdot"></span>{speaker} · {title}</span>
    <div class="divnumwrap"><div class="divnum">0{idx}</div></div>
    <div class="divbadge">{p_num}</div>
    <h2>{p_title}</h2>
    <p class="divsub">{p_sub}</p>
  </section>
"""
        # 내용 슬라이드 1: 포인트
        if p_bullets:
            slides_html += f"""
  <section class="page s-cream" data-sec="{p_num} · {p_title}">
    <span class="brand"><span class="bdot"></span>{speaker} · {title}</span>
    <h3>{p_title} — <span class="pop">핵심 포인트</span></h3>
    <ul class="bul">
"""
            for b in p_bullets:
                slides_html += f"<li>{b}</li>"
            slides_html += "</ul></section>"

        # 내용 슬라이드 2: 인용구 (있을 경우)
        if p_quotes:
            slides_html += f"""
  <section class="page s-night" data-sec="{p_num} · {p_title}">
    <span class="brand"><span class="bdot"></span>{speaker} · {title}</span>
    <div class="quotemark">"</div>
    <div class="bigstate" style="color:#F4F2EB">{p_quotes[0]}</div>
  </section>
"""

    # 마침/체크리스트 슬라이드
    slides_html += f"""
  <section class="page s-cream" data-sec="마무리">
    <span class="brand"><span class="bdot"></span>{speaker} · {title}</span>
    <h3>오늘 배운 내용 최종 점검</h3>
    <div class="checklist">
"""
    for chk in checklist:
        slides_html += f'<div class="check"><span>✓</span> <span>{chk}</span></div>'

    slides_html += f"""
    </div>
  </section>

</div>

<div class="hud dark" id="hud">
  <span>{title} · {speaker}</span>
  <span id="sec"></span>
  <span id="pg"></span>
</div>

<script>
  var pages=[].slice.call(document.querySelectorAll('.page'));
  var cur=0;
  var bar=document.getElementById('bar');
  var hud=document.getElementById('hud');
  var secEl=document.getElementById('sec');
  var pgEl=document.getElementById('pg');
  function show(i){{
    cur=Math.max(0,Math.min(pages.length-1,i));
    pages.forEach(function(p,idx){{p.classList.toggle('active',idx===cur);}});
    bar.style.width=((cur+1)/pages.length*100)+'%';
    var p=pages[cur];
    secEl.textContent=p.getAttribute('data-sec')||'';
    pgEl.textContent=(cur+1)+' / '+pages.length;
    var lightTone=p.classList.contains('s-night')||p.classList.contains('s-coral');
    hud.classList.toggle('light',lightTone);
    hud.classList.toggle('dark',!lightTone);
  }}
  document.addEventListener('keydown',function(e){{
    if(e.key==='ArrowRight'||e.key==='PageDown'||e.key===' '){{e.preventDefault();show(cur+1);}}
    else if(e.key==='ArrowLeft'||e.key==='PageUp'){{e.preventDefault();show(cur-1);}}
  }});
  document.addEventListener('click',function(e){{ show(cur+1); }});
  show(0);
</script>
</body>
</html>"""
    return slides_html

# ============================================================
# 2. STUDY GUIDE HTML 템플릿 생성 함수 (juntaekstudy.html 스타일)
# ============================================================
def generate_study_html(data):
    title = data.get("title", "강의 요약가이드")
    speaker = data.get("speaker", "고상철")
    summary = data.get("summary", "")
    parts = data.get("parts", [])

    study_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — 요약 학습가이드</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
  :root{{
    --font:'Pretendard','Pretendard Variable',sans-serif;
    --cream:#F4F2EB; --cream2:#FAF8F1; --surface:#fff;
    --ink:#28251E; --ink2:#57534A; --ink3:#8B8678;
    --coral:#C96442; --coral2:#AD4F30; --coral-soft:#F5E4DA; --coral-light:#E0876A;
    --line:#E7E1D5; --night:#1B1712;
    --maxw:920px;
  }}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:var(--font);background:var(--cream2);color:var(--ink);line-height:1.7;word-break:keep-all;}}
  header.hero{{position:relative;background:var(--night);color:#F4F2EB;padding:80px 24px 60px;}}
  .hero-inner{{max-width:var(--maxw);margin:0 auto;}}
  .eyebrow{{display:inline-block;font-size:14px;font-weight:800;color:#EFA98C;background:rgba(201,100,66,.2);padding:.4rem .9rem;border-radius:999px;margin-bottom:16px;}}
  h1.title{{font-size:clamp(28px,4.5vw,46px);font-weight:900;line-height:1.22;margin-bottom:16px;}}
  .subtitle{{font-size:17px;color:rgba(244,242,235,.8);max-width:620px;margin-bottom:24px;}}
  nav.toc{{max-width:var(--maxw);margin:-30px auto 40px;padding:0 24px;}}
  .toc-card{{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:24px;box-shadow:0 10px 30px rgba(0,0,0,.08);}}
  .toc-title{{font-size:13px;font-weight:900;color:var(--coral2);margin-bottom:12px;text-transform:uppercase;}}
  .toc-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px 16px;}}
  .toc-grid a{{font-size:14px;font-weight:600;color:var(--ink);text-decoration:none;}}
  main{{padding-bottom:60px;}}
  section.block{{max-width:var(--maxw);margin:0 auto;padding:40px 24px;border-bottom:1px solid var(--line);}}
  .sec-head{{display:flex;align-items:center;gap:12px;margin-bottom:18px;}}
  .sec-badge{{display:flex;align-items:center;justify-content:center;width:38px;height:38px;border-radius:10px;background:var(--coral);color:#fff;font-weight:900;}}
  h2.sec-title{{font-size:clamp(20px,2.5vw,26px);font-weight:900;}}
  p{{color:var(--ink2);font-size:15.5px;margin-bottom:14px;}}
  .quote-box{{background:var(--night);color:#F4F2EB;border-radius:14px;padding:20px;margin:18px 0;}}
  .tip-box{{background:#FBF3DF;border-left:4px solid #C9962E;padding:16px;margin:16px 0;border-radius:0 12px 12px 0;}}
  .bul-list{{margin:14px 0;padding-left:20px;}}
  .bul-list li{{margin-bottom:8px;color:var(--ink2);}}
  footer{{max-width:var(--maxw);margin:0 auto;padding:30px 24px;text-align:center;color:var(--ink3);font-size:13px;}}
</style>
</head>
<body>

<header class="hero">
  <div class="hero-inner">
    <div class="eyebrow">{speaker} 강의 요약</div>
    <h1 class="title">{title}<br>전체 요약 가이드</h1>
    <p class="subtitle">{summary}</p>
  </div>
</header>

<nav class="toc">
  <div class="toc-card">
    <div class="toc-title">목차</div>
    <div class="toc-grid">
"""
    for idx, part in enumerate(parts, 1):
        study_html += f'<a href="#part{idx}">{part.get("part_num", f"PART {idx}")}. {part.get("title")}</a>'

    study_html += """
    </div>
  </div>
</nav>

<main>
"""
    for idx, part in enumerate(parts, 1):
        study_html += f"""
  <section class="block" id="part{idx}">
    <div class="sec-head">
      <div class="sec-badge">{idx:02d}</div>
      <div><h2 class="sec-title">{part.get('title')}</h2></div>
    </div>
    <p>{part.get('subtitle', '')}</p>
"""
        if part.get('key_quotes'):
            study_html += f"""
    <div class="quote-box">
      <strong>💬 핵심 강의 강조:</strong> "{part.get('key_quotes')[0]}"
    </div>
"""

        if part.get('bullet_points'):
            study_html += '<ul class="bul-list">'
            for bp in part.get('bullet_points'):
                study_html += f"<li><b>{bp}</b></li>"
            study_html += "</ul>"

        if part.get('tips'):
            study_html += f"""
    <div class="tip-box">
      <b>💡 공략 팁:</b> {part.get('tips')[0]}
    </div>
"""
        study_html += "</section>"

    study_html += f"""
</main>

<footer>{title} · {speaker} 강의 기반 정리</footer>
</body>
</html>"""
    return study_html

# ============================================================
# 4. 요약 대시보드 HTML (표·수치·플로우)
# ============================================================
SHARED_CSS = """
  :root{
    --font:'Pretendard','Pretendard Variable',-apple-system,BlinkMacSystemFont,sans-serif;
    --cream2:#FAF8F1; --surface:#fff;
    --ink:#28251E; --ink2:#57534A; --ink3:#8B8678;
    --coral:#C96442; --coral2:#AD4F30; --coral-soft:#F5E4DA;
    --line:#E7E1D5; --night:#1B1712;
  }
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:var(--font);background:var(--cream2);color:var(--ink);line-height:1.65;word-break:keep-all;}
"""

def generate_summary_html(sd, title, speaker):
    numbers = sd.get("key_numbers", []) or []
    table = sd.get("comparison_table", {}) or {}
    steps = sd.get("flow_steps", []) or []
    points = sd.get("core_points", []) or []
    cautions = sd.get("cautions", []) or []

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — 한눈에 보는 요약</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
{SHARED_CSS}
  .wrap{{max-width:1000px;margin:0 auto;padding:40px 24px 60px;}}
  header{{background:var(--night);color:#F4F2EB;border-radius:20px;padding:36px 32px;margin-bottom:28px;}}
  header .eyebrow{{display:inline-block;font-size:13px;font-weight:800;color:#EFA98C;
    background:rgba(201,100,66,.22);padding:5px 14px;border-radius:999px;margin-bottom:14px;}}
  header h1{{font-size:clamp(24px,3.6vw,36px);font-weight:900;line-height:1.25;}}
  header p{{margin-top:12px;font-size:16px;color:rgba(244,242,235,.85);}}
  h2.sec{{font-size:20px;font-weight:900;margin:32px 0 14px;padding-left:12px;border-left:5px solid var(--coral);}}
  .numgrid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;}}
  .numcard{{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:20px;text-align:center;}}
  .numcard .v{{font-size:30px;font-weight:900;color:var(--coral);}}
  .numcard .l{{font-size:13px;font-weight:700;color:var(--ink2);margin-top:6px;}}
  table{{width:100%;border-collapse:collapse;background:var(--surface);
    border:1px solid var(--line);border-radius:14px;overflow:hidden;font-size:14.5px;}}
  th{{background:var(--coral);color:#fff;font-weight:800;padding:12px;text-align:left;}}
  td{{padding:12px;border-top:1px solid var(--line);color:var(--ink2);}}
  tr:nth-child(even) td{{background:#FCFAF5;}}
  .steps{{display:flex;flex-direction:column;gap:10px;}}
  .step{{display:flex;gap:14px;background:var(--surface);border:1px solid var(--line);
    border-radius:14px;padding:16px 18px;}}
  .step .n{{flex:none;width:34px;height:34px;border-radius:10px;background:var(--coral);
    color:#fff;font-weight:900;display:flex;align-items:center;justify-content:center;}}
  .step .t{{font-weight:800;margin-bottom:3px;}}
  .step .d{{font-size:14px;color:var(--ink2);}}
  ul.plain{{list-style:none;display:grid;gap:9px;}}
  ul.plain li{{background:var(--surface);border:1px solid var(--line);border-radius:12px;
    padding:13px 16px;font-size:15px;font-weight:600;}}
  ul.plain li::before{{content:"✓ ";color:var(--coral);font-weight:900;}}
  .caution li{{background:#FDF4F1;border-color:#EFCBBD;}}
  .caution li::before{{content:"⚠ ";}}
  footer{{margin-top:40px;text-align:center;color:var(--ink3);font-size:13px;}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="eyebrow">{speaker} 강의 · 한눈에 보는 요약</div>
  <h1>{title}</h1>
  <p>{sd.get('headline','')}</p>
</header>
"""
    if numbers:
        html += '<h2 class="sec">핵심 수치</h2><div class="numgrid">'
        for n in numbers:
            html += f'<div class="numcard"><div class="v">{n.get("value","")}</div><div class="l">{n.get("label","")}</div></div>'
        html += "</div>"

    if table.get("headers") and table.get("rows"):
        html += f'<h2 class="sec">{table.get("title","비교표")}</h2><table><thead><tr>'
        for h in table["headers"]:
            html += f"<th>{h}</th>"
        html += "</tr></thead><tbody>"
        for row in table["rows"]:
            html += "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
        html += "</tbody></table>"

    if steps:
        html += '<h2 class="sec">절차 흐름</h2><div class="steps">'
        for i, s in enumerate(steps, 1):
            html += (f'<div class="step"><div class="n">{s.get("step", i)}</div>'
                     f'<div><div class="t">{s.get("title","")}</div>'
                     f'<div class="d">{s.get("desc","")}</div></div></div>')
        html += "</div>"

    if points:
        html += '<h2 class="sec">반드시 기억할 핵심</h2><ul class="plain">'
        html += "".join(f"<li>{p}</li>" for p in points)
        html += "</ul>"

    if cautions:
        html += '<h2 class="sec">주의사항</h2><ul class="plain caution">'
        html += "".join(f"<li>{c}</li>" for c in cautions)
        html += "</ul>"

    html += f'<footer>{title} · {speaker} 강의 기반 정리</footer></div></body></html>'
    return html

# ============================================================
# 5. 체계도 한 장 HTML (A4 밀집형)
# ============================================================
def generate_mindmap_html(md, speaker):
    title = md.get("title", "강의 체계도")
    sections = md.get("sections", []) or []

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{title} — 체계도</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
{SHARED_CSS}
  body{{background:#EDEAE1;}}
  @page{{size:A4;margin:8mm;}}
  .sheet{{width:210mm;min-height:297mm;margin:14px auto;background:#fff;padding:9mm;
    display:flex;flex-direction:column;box-shadow:0 4px 18px rgba(0,0,0,.12);}}
  .head{{background:var(--night);color:#F4F2EB;border-radius:8px;padding:9px 14px;
    display:flex;justify-content:space-between;align-items:center;margin-bottom:7px;}}
  .head h1{{font-size:16px;font-weight:900;}}
  .head span{{font-size:10.5px;color:rgba(244,242,235,.8);}}
  .cols{{flex:1;column-count:2;column-gap:7px;}}
  .sec{{break-inside:avoid;border:1.4px solid var(--coral);border-radius:8px;
    overflow:hidden;margin-bottom:7px;}}
  .sec > .nm{{background:var(--coral);color:#fff;font-size:11.5px;font-weight:900;padding:5px 9px;}}
  .grp{{border-top:1px solid var(--line);padding:5px 8px;}}
  .grp:first-of-type{{border-top:none;}}
  .grp .gn{{font-size:10.5px;font-weight:900;color:var(--coral2);margin-bottom:3px;}}
  .grp ul{{list-style:none;display:flex;flex-direction:column;gap:2px;}}
  .grp li{{font-size:9.8px;line-height:1.38;color:var(--ink2);padding-left:8px;position:relative;}}
  .grp li::before{{content:"·";position:absolute;left:1px;color:var(--coral);font-weight:900;}}
  .foot{{margin-top:5px;text-align:center;font-size:9px;color:var(--ink3);}}
  @media print{{body{{background:#fff;}} .sheet{{margin:0;box-shadow:none;}}}}
</style>
</head>
<body>
<div class="sheet">
  <div class="head"><h1>{title}</h1><span>{speaker} 강의 체계도</span></div>
  <div class="cols">
"""
    for sec in sections:
        html += f'<div class="sec"><div class="nm">{sec.get("name","")}</div>'
        for grp in sec.get("groups", []) or []:
            html += f'<div class="grp"><div class="gn">{grp.get("name","")}</div><ul>'
            html += "".join(f"<li>{it}</li>" for it in grp.get("items", []) or [])
            html += "</ul></div>"
        html += "</div>"

    html += f"""  </div>
  <div class="foot">{title} · {speaker} 강의 기반 체계도</div>
</div>
</body>
</html>"""
    return html

# ============================================================
# 6. 5지선다 문제 HTML
# ============================================================
def generate_mcq_html(questions, title, speaker):
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — 5지선다 문제</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
{SHARED_CSS}
  .wrap{{max-width:860px;margin:0 auto;padding:40px 24px 60px;}}
  header{{background:var(--night);color:#F4F2EB;border-radius:18px;padding:30px 28px;margin-bottom:26px;}}
  header h1{{font-size:26px;font-weight:900;}}
  header p{{margin-top:8px;font-size:14.5px;color:rgba(244,242,235,.82);}}
  .q{{background:var(--surface);border:1px solid var(--line);border-radius:16px;
    padding:22px 24px;margin-bottom:18px;}}
  .qn{{display:inline-block;background:var(--coral);color:#fff;font-weight:900;font-size:13px;
    padding:4px 12px;border-radius:999px;margin-bottom:10px;}}
  .qt{{font-size:16.5px;font-weight:800;line-height:1.55;margin-bottom:14px;}}
  .ch{{display:flex;flex-direction:column;gap:7px;margin-bottom:16px;}}
  .ch div{{font-size:15px;color:var(--ink2);padding:9px 13px;background:#FCFAF5;
    border:1px solid var(--line);border-radius:9px;}}
  .ans{{background:var(--coral-soft);border-left:4px solid var(--coral);border-radius:0 10px 10px 0;
    padding:11px 15px;font-weight:900;color:var(--coral2);margin-bottom:9px;}}
  .exp{{background:#FBF3DF;border-left:4px solid #C9962E;border-radius:0 10px 10px 0;
    padding:13px 16px;font-size:14.5px;color:var(--ink2);}}
  footer{{margin-top:34px;text-align:center;color:var(--ink3);font-size:13px;}}
</style>
</head>
<body>
<div class="wrap">
<header><h1>{title} — 5지선다 문제</h1><p>{speaker} 강의 기반 · 총 {len(questions)}문제</p></header>
"""
    for i, q in enumerate(questions, 1):
        html += f'<div class="q"><div class="qn">문제 {i}</div><div class="qt">{q.get("question","")}</div><div class="ch">'
        html += "".join(f"<div>{c}</div>" for c in q.get("choices", []) or [])
        html += (f'</div><div class="ans">정답: {q.get("answer","")}</div>'
                 f'<div class="exp"><b>해설</b><br>{q.get("explanation","")}</div></div>')

    html += f'<footer>{title} · {speaker} 강의 기반 문제</footer></div></body></html>'
    return html

def mcq_to_rich_html(questions, title):
    """5지선다 문제를 한글(HWP)·블로그에 붙여넣을 수 있는 서식 HTML로 만듭니다."""
    html = f'<h2 style="font-size:20px;font-weight:bold;">{title} — 5지선다 문제</h2>'
    for i, q in enumerate(questions, 1):
        html += f'<p style="margin:18px 0 8px;"><b>{i}. {q.get("question","")}</b></p>'
        for c in q.get("choices", []) or []:
            html += f'<p style="margin:3px 0 3px 16px;">{c}</p>'
        html += (f'<p style="margin:8px 0 4px;"><b>정답: {q.get("answer","")}</b></p>'
                 f'<p style="margin:0 0 8px;color:#555;">해설: {q.get("explanation","")}</p>')
    return html

def ox_to_rich_html(questions, title):
    """O/X 문제를 한글(HWP)·블로그에 붙여넣을 수 있는 서식 HTML로 만듭니다."""
    html = f'<h2 style="font-size:20px;font-weight:bold;">{title} — O/X 문제</h2>'
    for i, q in enumerate(questions, 1):
        html += (f'<p style="margin:14px 0 4px;"><b>{i}. {q.get("question","")}</b></p>'
                 f'<p style="margin:0 0 4px;"><b>정답: {q.get("answer","")}</b></p>'
                 f'<p style="margin:0 0 8px;color:#555;">해설: {q.get("explanation","")}</p>')
    return html

def mcq_to_text(questions, title):
    lines = [f"[{title}] 5지선다 문제", ""]
    for i, q in enumerate(questions, 1):
        lines.append(f"{i}. {q.get('question','')}")
        lines.extend(f"   {c}" for c in q.get("choices", []) or [])
        lines.append(f"   ▶ 정답: {q.get('answer','')}")
        lines.append(f"   ▶ 해설: {q.get('explanation','')}")
        lines.append("")
    return "\n".join(lines)

# ============================================================
# 7. O/X 문제 HTML
# ============================================================
def generate_ox_html(questions, title, speaker):
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — O/X 문제</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
{SHARED_CSS}
  .wrap{{max-width:820px;margin:0 auto;padding:40px 24px 60px;}}
  header{{background:var(--night);color:#F4F2EB;border-radius:18px;padding:30px 28px;margin-bottom:26px;}}
  header h1{{font-size:26px;font-weight:900;}}
  header p{{margin-top:8px;font-size:14.5px;color:rgba(244,242,235,.82);}}
  .q{{background:var(--surface);border:1px solid var(--line);border-radius:14px;
    padding:18px 20px;margin-bottom:13px;}}
  .top{{display:flex;align-items:flex-start;gap:12px;margin-bottom:10px;}}
  .qn{{flex:none;width:28px;height:28px;border-radius:8px;background:var(--coral);color:#fff;
    font-weight:900;font-size:13px;display:flex;align-items:center;justify-content:center;}}
  .qt{{font-size:15.5px;font-weight:700;line-height:1.55;}}
  .badge{{display:inline-block;font-weight:900;font-size:15px;padding:4px 16px;border-radius:999px;margin-bottom:8px;}}
  .o{{background:#E3F2E5;color:#1E6B2C;}}
  .x{{background:#FBE4E0;color:#A5301C;}}
  .exp{{background:#FBF3DF;border-left:4px solid #C9962E;border-radius:0 9px 9px 0;
    padding:11px 14px;font-size:14px;color:var(--ink2);}}
  footer{{margin-top:34px;text-align:center;color:var(--ink3);font-size:13px;}}
</style>
</head>
<body>
<div class="wrap">
<header><h1>{title} — O/X 문제</h1><p>{speaker} 강의 기반 · 총 {len(questions)}문제</p></header>
"""
    for i, q in enumerate(questions, 1):
        ans = (q.get("answer") or "").strip().upper()
        cls = "o" if ans.startswith("O") else "x"
        html += (f'<div class="q"><div class="top"><div class="qn">{i}</div>'
                 f'<div class="qt">{q.get("question","")}</div></div>'
                 f'<div class="badge {cls}">정답 {ans}</div>'
                 f'<div class="exp">{q.get("explanation","")}</div></div>')

    html += f'<footer>{title} · {speaker} 강의 기반 문제</footer></div></body></html>'
    return html

def ox_to_text(questions, title):
    lines = [f"[{title}] O/X 문제", ""]
    for i, q in enumerate(questions, 1):
        lines.append(f"{i}. {q.get('question','')}")
        lines.append(f"   ▶ 정답: {q.get('answer','')}")
        lines.append(f"   ▶ 해설: {q.get('explanation','')}")
        lines.append("")
    return "\n".join(lines)

# ================= ==========================================
# 8. Streamlit 사용자 인터페이스
# ============================================================
for key, default in [
    ("stage", "input"),          # input -> review -> done
    ("raw_transcript", None),
    ("transcript", None),
    ("results", None),
    ("project_id", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# --- 사이드바: 저장된 결과 불러오기 ---
st.sidebar.divider()
st.sidebar.subheader("💾 저장된 결과")
projects = list_projects()
if projects:
    labels = ["— 선택 —"] + [f"{p['title'][:28]} ({p['saved_at'][:16]})" for p in projects]
    picked = st.sidebar.selectbox("이전에 만든 결과 불러오기", labels, key="project_picker")
    if picked != "— 선택 —":
        chosen = projects[labels.index(picked) - 1]
        if st.sidebar.button("📂 불러오기"):
            loaded = load_project(chosen["id"])
            if loaded:
                st.session_state.results = loaded
                st.session_state.transcript = loaded.get("transcript")
                st.session_state.project_id = chosen["id"]
                st.session_state.stage = "done"
                st.rerun()
else:
    st.sidebar.caption("아직 저장된 결과가 없습니다.")
st.sidebar.caption("⚠️ 온라인(Streamlit Cloud) 저장분은 앱이 재시작되면 사라질 수 있으니, 중요한 결과는 다운로드해 두세요.")

# --- 1단계: 입력 ---
if st.session_state.stage == "input":
    st.subheader("1단계 · 강의 원본 가져오기")
    youtube_url = st.text_input("유튜브 영상 주소", placeholder="https://www.youtube.com/watch?v=...")

    if st.button("🎬 자막 가져와서 정리하기", type="primary"):
        if not api_key:
            st.error("사이드바에 Gemini API Key를 먼저 입력해주세요.")
        else:
            video_id = extract_video_id(youtube_url)
            if not video_id:
                st.error("올바른 유튜브 URL이 아닙니다.")
            else:
                with st.spinner("유튜브 자막을 가져오는 중입니다..."):
                    raw = get_youtube_transcript(video_id)
                if raw:
                    genai.configure(api_key=api_key)
                    with st.spinner("AI가 오타·법령 용어·문맥을 정리하는 중입니다..."):
                        try:
                            model = get_working_model()
                            st.session_state.raw_transcript = raw
                            st.session_state.transcript = clean_transcript_with_ai(model, raw)
                            st.session_state.stage = "review"
                            st.rerun()
                        except Exception as e:
                            st.error(f"정리 중 오류가 발생했습니다: {e}")
                else:
                    st.warning("자막을 자동으로 가져올 수 없습니다. 아래에 스크립트를 직접 붙여넣어 주세요.")

    st.divider()
    st.caption("자막이 없거나 자동 추출이 안 되는 영상은 아래에 직접 붙여넣으세요.")
    manual_text = st.text_area("강의 전체 스크립트 직접 붙여넣기", height=220, key="manual_input")

    if st.button("📝 붙여넣은 스크립트 정리하기"):
        if not api_key:
            st.error("사이드바에 Gemini API Key를 먼저 입력해주세요.")
        elif not manual_text.strip():
            st.error("스크립트를 붙여넣어 주세요.")
        else:
            genai.configure(api_key=api_key)
            with st.spinner("AI가 오타·법령 용어·문맥을 정리하는 중입니다..."):
                try:
                    model = get_working_model()
                    st.session_state.raw_transcript = manual_text
                    st.session_state.transcript = clean_transcript_with_ai(model, manual_text)
                    st.session_state.stage = "review"
                    st.rerun()
                except Exception as e:
                    st.error(f"정리 중 오류가 발생했습니다: {e}")

# --- 2단계: 정리본 검토 ---
if st.session_state.stage == "review":
    st.subheader("2단계 · 정리된 스크립트 확인")
    st.success("오타 교정 · 법령 용어 정리 · 문맥 정리가 완료되었습니다. 내용을 확인하고 필요하면 직접 수정하세요.")

    edited = st.text_area("정리된 스크립트 (직접 수정 가능)", value=st.session_state.transcript,
                          height=380, key="cleaned_editor")
    copy_box("정리된 스크립트", edited, "cleaned")

    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("🚀 이 내용으로 콘텐츠 7종 생성하기", type="primary"):
            st.session_state.transcript = edited
            genai.configure(api_key=api_key)
            transcript = edited
            results = {"transcript": transcript, "saved_at": datetime.now().isoformat(timespec="seconds")}
            progress = st.progress(0.0, text="생성 준비 중...")
            try:
                model = get_working_model()

                progress.progress(0.15, text="1/5 강의 구조를 분석하는 중...")
                data = generate_structured_data(model, transcript)
                title = data.get("title", "강의 자료")
                speaker = data.get("speaker", "고상철")
                results.update({"title": title, "speaker": speaker, "data": data})

                progress.progress(0.35, text="2/5 블로그 글을 작성하는 중...")
                results["blog"] = generate_blog_post(model, transcript)

                progress.progress(0.55, text="3/5 요약 대시보드를 만드는 중...")
                results["summary"] = generate_summary_data(model, transcript)

                progress.progress(0.70, text="4/5 체계도를 만드는 중...")
                results["mindmap"] = generate_mindmap_data(model, transcript)

                progress.progress(0.85, text="5/5 문제를 출제하는 중...")
                results["mcq"] = generate_mcq(model, transcript, count=5).get("questions", [])
                results["ox"] = generate_ox(model, transcript, count=10).get("questions", [])

                progress.progress(1.0, text="완료!")
                project_id = make_project_id(transcript)
                save_project(project_id, results)
                st.session_state.project_id = project_id
                st.session_state.results = results
                st.session_state.stage = "done"
                st.rerun()
            except Exception as e:
                st.error(f"생성 중 오류가 발생했습니다: {e}")
    with col_b:
        if st.button("↩ 처음으로 돌아가기"):
            st.session_state.stage = "input"
            st.session_state.transcript = None
            st.rerun()

# --- 3단계: 결과 ---
if st.session_state.stage == "done" and st.session_state.results:
    r = st.session_state.results
    title = r.get("title", "강의 자료")
    speaker = r.get("speaker", "고상철")

    st.success(f"🎉 생성 완료 — {title}")
    st.caption(f"저장 시각: {r.get('saved_at','')} · 사이드바에서 언제든 다시 불러올 수 있습니다.")
    if st.button("↩ 새 강의 만들기"):
        st.session_state.stage = "input"
        st.session_state.transcript = None
        st.session_state.results = None
        st.rerun()

    tabs = st.tabs([
        "📝 0. 정리된 원고",
        "📊 1. 슬라이드",
        "📄 2. 웹 학습지",
        "✍️ 3. 블로그 글",
        "📈 4. 한눈 요약",
        "🗺 5. 체계도",
        "📋 6. 5지선다",
        "⭕ 7. O/X",
    ])

    with tabs[0]:
        st.text_area("정리된 스크립트", value=r.get("transcript", ""), height=400, key="view_transcript")
        copy_box("원고", r.get("transcript", ""), "res_transcript")

    with tabs[1]:
        html = generate_slides_html(r["data"])
        st.download_button("📥 슬라이드 HTML 다운로드", data=html,
                           file_name="slides.html", mime="text/html", key="dl_slides")
        st.components.v1.html(html, height=620, scrolling=True)

    with tabs[2]:
        html = generate_study_html(r["data"])
        st.download_button("📥 학습지 HTML 다운로드", data=html,
                           file_name="study_guide.html", mime="text/html", key="dl_study")
        st.components.v1.html(html, height=620, scrolling=True)

    with tabs[3]:
        blog = r.get("blog", {})
        st.markdown(f"**제목:** {blog.get('title','')}")
        st.markdown(f"**메타 설명:** {blog.get('meta_description','')}")
        st.markdown(f"**키워드:** {', '.join(blog.get('keywords', []) or [])}")
        st.divider()
        body = blog.get("markdown", "")
        rich = markdown_to_rich_html(body)

        st.markdown("**블로그에 바로 붙여넣기** — 아래 초록 버튼을 누르고 네이버 블로그·티스토리 편집기에 그대로 붙여넣으세요. 제목·굵게·표 서식이 그대로 유지됩니다.")
        copy_rich_box("블로그 본문", rich, "res_blog_rich")

        with st.expander("다른 형식으로 복사·저장하기"):
            copy_box("마크다운 원문", body, "res_blog_md")
            st.download_button("📥 마크다운(.md) 다운로드", data=body,
                               file_name="blog_post.md", mime="text/markdown", key="dl_blog_md")
            st.download_button("📥 HTML 다운로드", data=rich,
                               file_name="blog_post.html", mime="text/html", key="dl_blog_html")

        st.divider()
        st.caption("미리보기")
        st.markdown(body)

    with tabs[4]:
        html = generate_summary_html(r.get("summary", {}), title, speaker)
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("📥 HTML 다운로드", data=html,
                               file_name="summary.html", mime="text/html", key="dl_sum_html")
        with c2:
            try:
                st.download_button("📥 PDF 다운로드",
                                   data=summary_pdf_bytes(r.get("summary", {}), title, speaker),
                                   file_name="summary.pdf", mime="application/pdf", key="dl_sum_pdf")
            except Exception as e:
                st.caption(f"PDF 변환 실패: {e}")
        st.components.v1.html(html, height=620, scrolling=True)

    with tabs[5]:
        html = generate_mindmap_html(r.get("mindmap", {}), speaker)
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("📥 HTML 다운로드", data=html,
                               file_name="mindmap.html", mime="text/html", key="dl_map_html")
        with c2:
            try:
                st.download_button("📥 PDF 다운로드",
                                   data=mindmap_pdf_bytes(r.get("mindmap", {}), speaker),
                                   file_name="mindmap.pdf", mime="application/pdf", key="dl_map_pdf")
            except Exception as e:
                st.caption(f"PDF 변환 실패: {e}")
        st.components.v1.html(html, height=760, scrolling=True)

    with tabs[6]:
        mcq = r.get("mcq", [])
        if st.button("➕ 5문제 추가 생성", key="more_mcq"):
            genai.configure(api_key=api_key)
            with st.spinner("문제를 추가로 출제하는 중..."):
                try:
                    model = get_working_model()
                    more = generate_mcq(model, r["transcript"], count=5,
                                        avoid=[q.get("question", "") for q in mcq])
                    r["mcq"] = mcq + more.get("questions", [])
                    save_project(st.session_state.project_id, r)
                    st.rerun()
                except Exception as e:
                    st.error(f"추가 생성 실패: {e}")
        html = generate_mcq_html(r.get("mcq", []), title, speaker)
        copy_rich_box("문제 전체", mcq_to_rich_html(r.get("mcq", []), title), "res_mcq_rich")
        st.caption("한글(HWP)·블로그에 붙여넣으면 문제·정답·해설 서식이 그대로 유지됩니다.")
        with st.expander("일반 텍스트로 복사·저장하기"):
            copy_box("문제 전체(일반 텍스트)", mcq_to_text(r.get("mcq", []), title), "res_mcq")
            st.download_button("📥 HTML 다운로드", data=html,
                               file_name="mcq.html", mime="text/html", key="dl_mcq")
        st.components.v1.html(html, height=620, scrolling=True)

    with tabs[7]:
        ox = r.get("ox", [])
        if st.button("➕ 10문제 추가 생성", key="more_ox"):
            genai.configure(api_key=api_key)
            with st.spinner("문제를 추가로 출제하는 중..."):
                try:
                    model = get_working_model()
                    more = generate_ox(model, r["transcript"], count=10,
                                       avoid=[q.get("question", "") for q in ox])
                    r["ox"] = ox + more.get("questions", [])
                    save_project(st.session_state.project_id, r)
                    st.rerun()
                except Exception as e:
                    st.error(f"추가 생성 실패: {e}")
        html = generate_ox_html(r.get("ox", []), title, speaker)
        copy_rich_box("문제 전체", ox_to_rich_html(r.get("ox", []), title), "res_ox_rich")
        st.caption("한글(HWP)·블로그에 붙여넣으면 문제·정답·해설 서식이 그대로 유지됩니다.")
        with st.expander("일반 텍스트로 복사·저장하기"):
            copy_box("문제 전체(일반 텍스트)", ox_to_text(r.get("ox", []), title), "res_ox")
            st.download_button("📥 HTML 다운로드", data=html,
                               file_name="ox.html", mime="text/html", key="dl_ox")
        st.components.v1.html(html, height=620, scrolling=True)
