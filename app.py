import streamlit as st
import re
import io
import os
import time
import json
import base64
import hashlib
from datetime import datetime
from pathlib import Path
from html import escape as html_escape
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai

# Streamlit 페이지 설정
st.set_page_config(page_title="강의 콘텐츠 자동 생성기",
                   page_icon="🎥", layout="wide")

# ============================================================
# Miro 스타일 테마
# 토큰 출처: miro.com/brand — Miro Yellow #FFD02F, Indigo #4262FF,
# warm beige 캔버스 + 도트 그리드, 스티키 노트(라운드 2px)
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');

:root{
  --miro-yellow:#FFD02F; --miro-yellow-600:#E6BB1E; --miro-yellow-700:#B8941A;
  --miro-yellow-50:#FFF9E0; --miro-yellow-100:#FFF1B5; --miro-yellow-200:#FFE883;
  --miro-indigo:#4262FF; --miro-navy:#050038;
  --sticky-coral:#FF6F61; --sticky-cyan:#A0E7E5; --sticky-purple:#B4A0FF;
  --miro-canvas:#F5F5F0; --miro-dot:#D0D0C8;
  --miro-fg:#050038; --miro-fg2:#5A5A66; --miro-fg3:#87878F;
  --miro-line:#E0E0E0; --miro-line-soft:#ECECE4;
  --sh-sticky:2px 3px 0 rgba(5,0,56,.06);
  --sh-sm:0 1px 3px rgba(5,0,56,.06);
  --sh-md:0 4px 12px rgba(5,0,56,.10);
}

/* 무한 캔버스 — 도트 그리드 베이지 (Miro 시그니처) */
.stApp{
  background-color:var(--miro-canvas);
  background-image:radial-gradient(var(--miro-dot) 1px, transparent 1px);
  background-size:18px 18px;
}
html, body, .stApp, [class*="css"]{
  font-family:'Inter','Pretendard',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  color:var(--miro-fg);
}

/* 본문을 흰 보드 위에 올린다 */
.stMain .block-container{
  background:rgba(255,255,255,.86);
  border:1px solid var(--miro-line);
  border-radius:8px;
  box-shadow:var(--sh-sm);
  padding:30px 34px 46px;
  max-width:1180px;
}

/* 타이포 위계 */
h1,h2,h3{color:var(--miro-fg);letter-spacing:-.02em;}
h1{font-size:38px!important;font-weight:800!important;line-height:1.08!important;
   letter-spacing:-.035em!important;}
h2{font-size:26px!important;font-weight:700!important;}
h3{font-size:19px!important;font-weight:600!important;}

/* 상단 보드바 */
.stMain .block-container > div:first-child h1{
  display:flex;align-items:center;gap:12px;
  padding-bottom:16px;margin-bottom:4px;
  border-bottom:1px solid var(--miro-line-soft);
}

/* 버튼 — 기본은 흰 카드, primary는 Miro Yellow */
.stButton > button{
  font-family:inherit;font-weight:600;font-size:14px;
  border-radius:6px;min-height:38px;padding:0 15px;
  background:#fff;color:var(--miro-fg);border:1px solid var(--miro-line);
  box-shadow:none;transition:background 100ms ease, transform 100ms ease;
}
.stButton > button:hover{background:var(--miro-canvas);border-color:var(--miro-fg3);}
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"]{
  background:var(--miro-yellow);color:var(--miro-navy);border:0;font-weight:700;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover{
  background:var(--miro-yellow-600);transform:translateY(-1px);
}

/* 다운로드 버튼 — 캔버스 밖 액션이므로 Indigo */
.stDownloadButton > button{
  font-family:inherit;font-weight:700;font-size:13.5px;
  border-radius:6px;min-height:36px;padding:0 14px;
  background:var(--miro-indigo);color:#fff;border:0;
}
.stDownloadButton > button:hover{background:#2F4FE8;color:#fff;}

/* 입력 필드 */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div{
  background:#fff!important;border:1px solid var(--miro-line)!important;
  border-radius:6px!important;color:var(--miro-fg)!important;font-family:inherit!important;
}
.stTextInput input:focus, .stTextArea textarea:focus{
  border-color:var(--miro-indigo)!important;
  box-shadow:0 0 0 2px rgba(66,98,255,.20)!important;
}

/* 탭 — 도구바처럼 */
.stTabs [data-baseweb="tab-list"]{
  gap:4px;background:#fff;padding:6px;border-radius:10px;
  border:1px solid var(--miro-line);box-shadow:var(--sh-sm);flex-wrap:wrap;
}
.stTabs [data-baseweb="tab"]{
  height:auto;padding:9px 14px;border-radius:6px;background:transparent;
  font-size:13.5px;font-weight:600;color:var(--miro-fg2);
}
.stTabs [data-baseweb="tab"]:hover{background:var(--miro-canvas);color:var(--miro-fg);}
.stTabs [aria-selected="true"]{
  background:var(--miro-yellow)!important;color:var(--miro-navy)!important;font-weight:700!important;
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"]{display:none;}

/* 알림 — 스티키 노트 (라운드 2px이 시그니처) */
div[data-testid="stAlert"]{
  border-radius:2px;border:0;box-shadow:var(--sh-sticky);
  font-size:13.5px;font-weight:500;color:var(--miro-navy);
}
div[data-testid="stAlertContentSuccess"]{background:#DCF7E5;}
div[data-testid="stAlertContentInfo"]{background:var(--sticky-cyan);}
div[data-testid="stAlertContentWarning"]{background:var(--miro-yellow-200);}
div[data-testid="stAlertContentError"]{background:#FFC9C4;}

/* 사이드바 — 왼쪽 도구 패널 */
section[data-testid="stSidebar"]{
  background:#fff;border-right:1px solid var(--miro-line);
}
section[data-testid="stSidebar"] .block-container{padding-top:24px;}
section[data-testid="stSidebar"] h3{font-size:15px!important;font-weight:700!important;}

/* 진행 바 */
.stProgress > div > div > div > div{background:var(--miro-indigo);}
.stProgress > div > div > div{background:var(--miro-line-soft);border-radius:9999px;}

/* 확장 패널 */
details, div[data-testid="stExpander"]{
  background:#fff;border:1px solid var(--miro-line)!important;
  border-radius:8px!important;box-shadow:none;
}
div[data-testid="stExpander"] summary{font-weight:600;font-size:13.5px;}

/* 캡션 */
div[data-testid="stCaptionContainer"], .stCaption{
  color:var(--miro-fg3)!important;font-size:12px!important;
}

/* 구분선 */
hr{border-color:var(--miro-line-soft);}

/* 임베드된 결과물 미리보기 */
iframe{border-radius:8px;background:#fff;}

@media (max-width:820px){
  .stMain .block-container{padding:20px 16px 32px;border-radius:6px;}
  h1{font-size:28px!important;}
}
</style>
""", unsafe_allow_html=True)

st.title("🎥 유튜브 강의 콘텐츠 자동 생성기")

LOCAL_ARCHIVE = Path("archive")
LOCAL_ARCHIVE.mkdir(exist_ok=True)
DRIVE_SUBFOLDER = "강의콘텐츠생성기"

def find_drive_folder():
    """구글 드라이브 데스크톱 앱이 만든 동기화 폴더를 찾습니다.
    찾으면 그 안에 저장해 드라이브로 자동 업로드되게 합니다."""
    home = Path.home()
    candidates = [home / "My Drive", home / "Google Drive", home / "내 드라이브"]
    # 드라이브를 별도 드라이브 문자로 마운트한 경우(G:, H: 등)까지 훑는다
    for letter in "GHIJKLMNOPQRSTUVWXYZ":
        root = Path(f"{letter}:/")
        candidates += [root / "My Drive", root / "내 드라이브"]
    for path in candidates:
        try:
            if path.is_dir():
                return path
        except OSError:
            continue
    return None

@st.cache_data(ttl=60, show_spinner=False)
def drive_status():
    """(사용중여부, 저장경로) — 60초간 캐시해 매번 디스크를 훑지 않습니다."""
    if is_shared_host():
        return False, None
    base = find_drive_folder()
    if not base:
        return False, None
    target = base / DRIVE_SUBFOLDER
    try:
        target.mkdir(parents=True, exist_ok=True)
        return True, target
    except OSError:
        return False, None

def archive_dirs():
    """저장을 읽을 폴더 목록. 드라이브가 있으면 드라이브를 우선합니다."""
    using, drive = drive_status()
    return [drive, LOCAL_ARCHIVE] if using else [LOCAL_ARCHIVE]

def save_project(project_id, payload):
    """결과를 저장합니다. 드라이브 폴더가 있으면 거기에도 함께 씁니다."""
    text = json.dumps(payload, ensure_ascii=False)
    written = []
    for folder in archive_dirs():
        try:
            (folder / f"{project_id}.json").write_text(text, encoding="utf-8")
            written.append(folder)
        except OSError:
            continue
    return written

def load_project(project_id):
    for folder in archive_dirs():
        path = folder / f"{project_id}.json"
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
    return None

def list_projects():
    """저장된 결과 목록. 드라이브와 로컬을 합치고 같은 id는 한 번만 보여줍니다."""
    seen = {}
    for folder in archive_dirs():
        try:
            paths = sorted(folder.glob("*.json"))
        except OSError:
            continue
        for path in paths:
            if path.stem in seen:
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            seen[path.stem] = {
                "id": path.stem,
                "title": data.get("title", "제목 없음"),
                "saved_at": data.get("saved_at", ""),
            }
    return sorted(seen.values(), key=lambda x: x["saved_at"], reverse=True)

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

def handout_pdf_bytes(hd, speaker):
    """학생 배포용 자료를 PDF로 만듭니다(인쇄 배포용)."""
    title = hd.get("title", "요약 학습자료")
    body = (f"<h1>{title}</h1>"
            f"<p class='lead'>{hd.get('subtitle','')} · {speaker} 강의 요약</p>")
    if hd.get("intro"):
        body += f"<p>{hd['intro']}</p>"

    for idx, sec in enumerate(hd.get("sections") or [], 1):
        no = sec.get("no") or f"{idx:02d}"
        body += f"<h2>{no}. {sec.get('heading','')}</h2>"
        if sec.get("summary"):
            body += f"<p>{sec['summary']}</p>"
        if sec.get("key_points"):
            body += "<ul>" + "".join(f"<li>{p}</li>" for p in sec["key_points"]) + "</ul>"

        table = sec.get("table") or {}
        if table.get("headers") and table.get("rows"):
            if table.get("caption"):
                body += f"<h3>{table['caption']}</h3>"
            body += "<table><tr>" + "".join(f"<th>{h}</th>" for h in table["headers"]) + "</tr>"
            for row in table["rows"]:
                body += "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
            body += "</table>"

        chart = sec.get("chart") or {}
        items = [it for it in (chart.get("items") or [])
                 if isinstance(it.get("value"), (int, float))]
        if items:
            unit = chart.get("unit", "")
            body += f"<h3>{chart.get('caption','수치 비교')}</h3><ul>"
            body += "".join(f"<li>{it.get('name','')} — <b>{it['value']:g}{unit}</b></li>"
                            for it in items)
            body += "</ul>"

        co = sec.get("callout") or {}
        if co.get("text"):
            label = CALLOUT_STYLE.get(co.get("kind", "tip"), CALLOUT_STYLE["tip"])[0]
            body += f"<div class='box'><b>{co.get('title') or label}</b> — {co['text']}</div>"

    flow = hd.get("flow") or {}
    if flow.get("steps"):
        body += f"<h2>{flow.get('caption','절차 흐름')}</h2><ul>"
        body += "".join(f"<li>{i}. {s}</li>" for i, s in enumerate(flow["steps"], 1))
        body += "</ul>"

    if hd.get("terms"):
        body += "<h2>꼭 알아야 할 용어</h2><ul>"
        body += "".join(f"<li><b>{t.get('term','')}</b> — {t.get('meaning','')}</li>"
                        for t in hd["terms"])
        body += "</ul>"

    if hd.get("checklist"):
        body += "<h2>시험 직전 최종 점검</h2><ul>"
        body += "".join(f"<li>☐ {c}</li>" for c in hd["checklist"])
        body += "</ul>"

    return build_pdf_bytes(body, title)

def onepager_pdf_bytes(od, speaker):
    """A4 한 장 체계도를 PDF로 만듭니다."""
    title = od.get("title", "핵심 체계도")
    body = (f"<h1>{title}</h1>"
            f"<p class='lead'>핵심: {od.get('center','')} · {speaker} 강의 한 장 요약</p>")

    nums = od.get("key_numbers") or []
    if nums:
        body += "<table><tr>"
        body += "".join(f"<th>{n.get('label','')}</th>" for n in nums)
        body += "</tr><tr>"
        body += "".join(f"<td><b>{n.get('value','')}</b></td>" for n in nums)
        body += "</tr></table>"

    for i, b in enumerate(od.get("branches") or [], 1):
        body += f"<h2>{b.get('no') or i}. {b.get('heading','')}</h2><ul>"
        body += "".join(f"<li>{it}</li>" for it in b.get("items") or [])
        body += "</ul>"

    if od.get("footer_note"):
        body += f"<div class='box'><b>꼭 기억하세요</b> — {od['footer_note']}</div>"
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

# ============================================================
# API 키 저장 / 불러오기
# 내 컴퓨터에서 실행할 때만 파일로 저장한다.
# 공용 서버(Streamlit Cloud)는 다른 사람도 접속하므로 저장하지 않는다.
# ============================================================
API_KEY_FILE = Path.home() / ".youtube_lecture_generator" / "api_key.txt"
API_KEY_COOKIE = "ylg_gemini_key"

def is_shared_host():
    """여러 사람이 접속하는 공용 서버에서 실행 중인지 판단합니다."""
    return os.path.exists("/mount/src") or bool(os.environ.get("STREAMLIT_SHARING_MODE"))

def read_key_cookie():
    """브라우저 쿠키에 저장된 키를 읽습니다. 쿠키는 이 브라우저에만 남습니다."""
    try:
        return (st.context.cookies.get(API_KEY_COOKIE) or "").strip()
    except Exception:
        return ""

def write_key_cookie(key):
    """브라우저에 키를 저장합니다(1년). 같은 컴퓨터·브라우저에서는 다시 넣지 않아도 됩니다."""
    payload = base64.b64encode(key.encode("utf-8")).decode("ascii")
    st.components.v1.html(
        f"""<script>
(function() {{
  try {{
    var v = decodeURIComponent(escape(atob("{payload}")));
    var secure = location.protocol === "https:" ? ";Secure" : "";
    document.cookie = "{API_KEY_COOKIE}=" + encodeURIComponent(v)
      + ";path=/;max-age=31536000;SameSite=Lax" + secure;
  }} catch (e) {{}}
}})();
</script>""",
        height=0,
    )

def clear_key_cookie():
    st.components.v1.html(
        f"""<script>
document.cookie = "{API_KEY_COOKIE}=;path=/;max-age=0;SameSite=Lax";
</script>""",
        height=0,
    )

def load_saved_api_key():
    """저장된 키를 불러옵니다. 내 컴퓨터면 파일, 아니면 브라우저 쿠키에서 읽습니다."""
    if not is_shared_host():
        try:
            saved = API_KEY_FILE.read_text(encoding="utf-8").strip()
            if saved:
                return saved
        except Exception:
            pass
    return read_key_cookie()

def save_api_key(key):
    """키를 저장합니다. 어느 환경에서든 최소 브라우저에는 저장됩니다."""
    write_key_cookie(key)
    if is_shared_host():
        return "cookie"
    try:
        API_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        API_KEY_FILE.write_text(key, encoding="utf-8")
        return "file"
    except Exception:
        return "cookie"

def delete_saved_api_key():
    clear_key_cookie()
    try:
        API_KEY_FILE.unlink()
    except Exception:
        pass
    return True

saved_api_key = load_saved_api_key()

st.sidebar.subheader("🔑 Gemini API 키")
api_key = st.sidebar.text_input(
    "API 키", type="password", value=saved_api_key,
    placeholder="AIza... 로 시작하는 키", label_visibility="collapsed",
)

if api_key and api_key != saved_api_key:
    where = save_api_key(api_key)
    if where == "file":
        st.sidebar.success("키를 저장했습니다. 이 컴퓨터에서는 다시 넣지 않아도 됩니다.")
    else:
        st.sidebar.success("키를 이 브라우저에 저장했습니다. 다음 접속부터 자동으로 입력됩니다.")
elif api_key and api_key == saved_api_key:
    st.sidebar.success("저장된 키를 불러왔습니다. 다시 넣지 않아도 됩니다.")
else:
    st.sidebar.info("아래 안내를 보고 키를 발급받아 넣어주세요. 한 번만 넣으면 됩니다.")

if saved_api_key and st.sidebar.button("저장된 키 지우기", key="clear_api_key"):
    delete_saved_api_key()
    st.rerun()

with st.sidebar.expander("❓ API 키 발급받는 방법 (처음 한 번만)"):
    st.markdown(
        """
**1단계 · 발급 페이지 열기**

👉 [Google AI Studio에서 키 발급받기](https://aistudio.google.com/apikey)

**2단계 · 구글 계정으로 로그인**

평소 쓰시는 구글(Gmail) 계정으로 로그인하세요.

**3단계 · 키 만들기**

`Create API key` (API 키 만들기) 버튼을 누릅니다.
프로젝트를 고르라고 나오면 아무거나 선택하거나 새로 만드시면 됩니다.

**4단계 · 복사해서 붙여넣기**

`AIza...`로 시작하는 긴 글자가 나옵니다.
복사 버튼을 눌러 복사한 뒤, 위 입력칸에 붙여넣으세요.

---

💡 **무료입니다.** 개인이 쓰는 정도는 요금이 들지 않습니다.

🔒 **키는 이렇게 보관됩니다.**
바탕화면 아이콘으로 실행하면 내 컴퓨터 안에만 저장되어, 다음부터 자동으로 채워집니다.
인터넷 주소로 접속했을 때는 누구나 들어올 수 있는 공용 서버라 저장하지 않으며,
접속할 때마다 입력하셔야 합니다. 어느 쪽이든 키를 남에게 알려주지는 마세요.
        """
    )

def extract_video_id(url):
    regex = r"(?:v=|youtu\.be\/|\/embed\/|\/v\/)([^\"&?\/\s]{11})"
    match = re.search(regex, url)
    return match.group(1) if match else None

def build_transcript_api():
    """프록시 설정이 있으면 적용해 YouTubeTranscriptApi를 만듭니다.
    Streamlit Cloud 등 데이터센터 IP는 유튜브가 차단하므로 프록시가 필요할 수 있습니다."""
    def secret(name):
        # st.secrets는 값을 읽는 시점에 파일을 찾으므로, 읽기 자체를 감싸야 한다.
        try:
            return st.secrets.get(name)
        except Exception:
            return None

    ws_user = secret("WEBSHARE_PROXY_USERNAME")
    ws_pass = secret("WEBSHARE_PROXY_PASSWORD")
    if ws_user and ws_pass:
        from youtube_transcript_api.proxies import WebshareProxyConfig
        return YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(proxy_username=ws_user, proxy_password=ws_pass)
        )

    http_url = secret("HTTP_PROXY_URL")
    if http_url:
        from youtube_transcript_api.proxies import GenericProxyConfig
        return YouTubeTranscriptApi(
            proxy_config=GenericProxyConfig(http_url=http_url, https_url=http_url)
        )

    return YouTubeTranscriptApi()

def get_youtube_transcript(video_id):
    """(자막문자열, 오류메시지) 튜플을 반환합니다. 성공 시 오류메시지는 None입니다."""
    try:
        api = build_transcript_api()
        try:
            fetched = api.fetch(video_id, languages=["ko"])
        except Exception:
            # 한국어가 없으면 사용 가능한 첫 번째 자막으로 대체
            listing = api.list(video_id)
            transcript = next(iter(listing))
            fetched = transcript.fetch()
        return " ".join(snippet.text for snippet in fetched), None
    except Exception as e:
        name = type(e).__name__
        detail = str(e).strip().splitlines()
        detail = detail[0] if detail else name
        if "IpBlocked" in name or "RequestBlocked" in name:
            return None, ("유튜브가 이 서버의 IP를 차단했습니다. "
                          "클라우드(Streamlit Cloud) 환경에서 흔히 발생하며, 영상이나 자막 문제가 아닙니다. "
                          "아래에 스크립트를 직접 붙여넣거나, 내 컴퓨터에서 앱을 실행하면 정상 동작합니다.")
        if "Disabled" in name:
            return None, "이 영상은 자막이 꺼져 있습니다. 아래에 스크립트를 직접 붙여넣어 주세요."
        if "NoTranscriptFound" in name or "NotTranslatable" in name:
            return None, "이 영상에서 사용할 수 있는 자막을 찾지 못했습니다. 아래에 직접 붙여넣어 주세요."
        if "VideoUnavailable" in name:
            return None, "영상을 찾을 수 없습니다. 주소를 다시 확인해주세요."
        return None, f"자막을 가져오지 못했습니다 ({name}): {detail}"

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

def escape_control_chars_in_strings(raw):
    """JSON 문자열 값 안에 그대로 들어온 줄바꿈·탭을 escape 시퀀스로 바꿉니다.
    AI가 블로그 본문처럼 여러 줄인 글을 넣을 때 자주 발생합니다."""
    out = []
    in_string = False
    escaped = False
    for ch in raw:
        if not in_string:
            if ch == '"':
                in_string = True
            out.append(ch)
            continue
        if escaped:
            out.append(ch)
            escaped = False
        elif ch == "\\":
            out.append(ch)
            escaped = True
        elif ch == '"':
            out.append(ch)
            in_string = False
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        else:
            out.append(ch)
    return "".join(out)

def parse_model_json(text):
    """AI 응답에서 JSON을 최대한 살려서 읽어냅니다."""
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    raw = (match.group(1) if match else text).strip()

    # 앞뒤에 붙은 설명 문장을 걷어내고 실제 JSON 범위만 남긴다.
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        raw = raw[start : end + 1]

    # strict=False는 문자열 안의 제어문자를 허용한다.
    try:
        return json.loads(raw, strict=False)
    except json.JSONDecodeError:
        return json.loads(escape_control_chars_in_strings(raw), strict=False)

def call_json(model, prompt, attempts=3):
    """JSON 응답을 요구하고, 형식이 깨지면 다시 물어봅니다."""
    last_error = None
    for i in range(attempts):
        ask = prompt if i == 0 else (
            prompt + "\n\n[중요] 앞선 응답의 JSON 형식이 깨졌습니다. "
            "설명 없이 올바른 JSON만 출력하세요. "
            "문자열 안에서 줄을 바꿀 때는 실제 줄바꿈이 아니라 \\n 으로 쓰세요."
        )
        try:
            return parse_model_json(model.generate_content(ask).text)
        except Exception as e:
            last_error = e
    raise ValueError(
        "AI가 올바른 형식으로 응답하지 않았습니다. 다시 시도해주세요. "
        f"(원인: {type(last_error).__name__}: {last_error})"
    )

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

AUDIO_TYPES = ["mp3", "wav", "m4a", "aac", "ogg", "flac", "mp4", "mpeg", "mpga", "webm"]
AUDIO_MIME = {
    "mp3": "audio/mp3", "mpga": "audio/mpeg", "mpeg": "audio/mpeg",
    "wav": "audio/wav", "m4a": "audio/m4a", "aac": "audio/aac",
    "ogg": "audio/ogg", "flac": "audio/flac",
    "mp4": "video/mp4", "webm": "video/webm",
}

def transcribe_audio(model, file_bytes, filename):
    """오디오·영상 파일을 전사하면서 오타·법령 용어까지 한 번에 정리합니다.
    전사와 정리를 한 호출로 합쳐 API 비용을 절반으로 줍니다."""
    import tempfile

    suffix = Path(filename).suffix.lower().lstrip(".")
    mime = AUDIO_MIME.get(suffix, "audio/mpeg")

    tmp_path = None
    uploaded = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix or 'mp3'}") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        uploaded = genai.upload_file(path=tmp_path, mime_type=mime)

        # 업로드 직후에는 아직 처리 중(PROCESSING)일 수 있어 준비될 때까지 기다린다.
        waited = 0.0
        while getattr(uploaded.state, "name", "") == "PROCESSING" and waited < 600:
            time.sleep(3)
            waited += 3
            uploaded = genai.get_file(uploaded.name)
        if getattr(uploaded.state, "name", "") == "FAILED":
            raise RuntimeError("업로드한 파일을 처리하지 못했습니다. 다른 형식으로 저장해 다시 올려주세요.")

        prompt = """이 오디오는 부동산 공법 강의입니다. 전체 내용을 한국어로 받아쓰세요.

[작성 지침]
1. 말한 내용을 빠뜨리지 말고 전부 옮기세요. 요약하지 마세요.
2. 오탈자와 띄어쓰기를 바로잡고, 문맥에 맞게 문장을 자연스럽게 다듬으세요.
3. 법령명·조문·용어가 구어체로 축약되면 공식 명칭으로 정리하세요.
   (예: "국토계획법" → "국토의 계획 및 이용에 관한 법률")
   확실하지 않으면 들린 그대로 두세요.
4. "음", "어" 같은 추임새와 의미 없는 반복은 지우세요.
5. 화자가 여러 명이면 문단을 나누세요.
6. 설명이나 머리말 없이 정리된 본문만 출력하세요."""

        response = model.generate_content([prompt, uploaded])
        return response.text.strip()
    finally:
        if uploaded is not None:
            try:
                genai.delete_file(uploaded.name)
            except Exception:
                pass
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

def generate_handout_data(model, transcript):
    """학생에게 그대로 배포할 수 있는 요약 학습자료 데이터를 만듭니다."""
    prompt = f"""당신은 공인중개사 수험 교재를 만드는 편집자입니다.
아래 강의 내용을 학생에게 그대로 배포할 수 있는 요약 학습자료로 재구성하세요.

[작성 원칙]
- 강의에 나온 내용만 쓰세요. 강의에 없는 법령·수치를 추측해서 넣지 마세요.
- 학생이 이 자료만 보고도 강의 내용을 복습할 수 있을 만큼 충실하게 쓰세요.
- 비교할 대상이 있으면 table을, 수치를 견줄 수 있으면 chart를 넣으세요.
  비교나 수치가 없는 단원은 table·chart를 넣지 말고 빈 값으로 두세요.
- chart의 value는 반드시 숫자만 쓰세요(단위는 unit에 따로).

[강의 내용]
{transcript[:14000]}

아래 JSON 형태로만 응답하세요. 문자열 안에서 줄을 바꿀 때는 \\n 을 쓰세요:
```json
{{
  "title": "자료 제목",
  "subtitle": "한 줄 부제",
  "intro": "이 자료로 무엇을 배우는지 2~3문장",
  "sections": [
    {{
      "no": "01",
      "heading": "단원 제목",
      "summary": "단원 요약 2~3문장",
      "key_points": ["핵심 정리 3~5개"],
      "table": {{"caption": "표 제목", "headers": ["구분", "내용"], "rows": [["항목", "설명"]]}},
      "chart": {{"caption": "그래프 제목", "unit": "m", "items": [{{"name": "항목", "value": 5}}]}},
      "callout": {{"kind": "law", "title": "근거 법령", "text": "설명"}}
    }}
  ],
  "terms": [{{"term": "용어", "meaning": "뜻풀이"}}],
  "flow": {{"caption": "절차 흐름", "steps": ["1단계", "2단계"]}},
  "checklist": ["시험 직전 점검 항목 5~8개"]
}}
```
callout의 kind는 law(법령근거) / tip(공략팁) / warn(주의) 중 하나입니다."""
    return call_json(model, prompt)

def generate_onepager_data(model, transcript):
    """A4 한 장에 들어가는 체계도 데이터를 만듭니다."""
    prompt = f"""당신은 공인중개사 수험 요약 전문가입니다.
아래 강의 내용을 A4 딱 한 장짜리 체계도로 압축하세요.

[제약 — 반드시 지키세요]
- 종이 한 장에 들어가야 하므로 분량이 넘치면 안 됩니다.
- 가지(branch)는 4~6개, 각 가지의 항목(items)은 3~5개.
- 각 항목은 한 줄로 끝나게 25자 이내로 쓰세요. 문장이 아니라 요약 어구로 쓰세요.
- 강의에 나온 내용만 쓰고, 없는 내용을 만들지 마세요.
- key_numbers는 강의에 실제로 나온 숫자·기준만 쓰세요. 없으면 빈 배열로 두세요.

[강의 내용]
{transcript[:14000]}

아래 JSON 형태로만 응답하세요:
```json
{{
  "title": "체계도 제목",
  "center": "가장 중심이 되는 주제 (12자 이내)",
  "key_numbers": [{{"value": "5m", "label": "이격거리"}}],
  "branches": [
    {{"no": "1", "heading": "가지 제목 (14자 이내)", "items": ["요약 어구", "요약 어구"]}}
  ],
  "footer_note": "꼭 기억할 한 줄"
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

# ============================================================
# 8·9. Google Material Design 스타일 (학생 배포용 / A4 체계도)
# 토큰 출처: m3.material.io — Roboto+Noto Sans KR, Google 4색,
# tonal elevation 우선, 라운드 12/16/28
# ============================================================
MATERIAL_CSS = """
  :root{
    --m-blue:#4285F4; --m-red:#EA4335; --m-yellow:#FBBC04; --m-green:#34A853;
    --p50:#E8F0FE; --p100:#D2E3FC; --p200:#AECBFA; --p300:#8AB4F8;
    --p500:#4285F4; --p600:#1A73E8; --p700:#1967D2; --p800:#185ABC; --p900:#174EA6;
    --n0:#FFFFFF; --n50:#F8F9FA; --n100:#F1F3F4; --n200:#E8EAED;
    --n300:#DADCE0; --n500:#9AA0A6; --n700:#5F6368; --n800:#3C4043; --n900:#202124;
    --success-bg:#E6F4EA; --success-fg:#34A853;
    --warning-bg:#FEF7E0; --warning-fg:#C58B00;
    --error-bg:#FCE8E6; --error-fg:#EA4335;
    --info-bg:#E8F0FE; --info-fg:#4285F4;
    --surface:#FFFFFF; --surface-low:#F8F9FA;
    --surface-container:#F1F3F4; --surface-high:#E8EAED;
    --fg:#1F1F1F; --fg2:#5F6368; --fg3:#80868B;
    --line:#DADCE0; --line-soft:#E8EAED;
    --r-sm:8px; --r-md:12px; --r-lg:16px; --r-xl:28px; --r-full:9999px;
    --sh-1:0 1px 2px rgba(0,0,0,.30),0 1px 3px 1px rgba(0,0,0,.15);
    --sh-3:0 4px 8px 3px rgba(0,0,0,.15),0 1px 3px rgba(0,0,0,.30);
  }
  *{box-sizing:border-box;margin:0;padding:0;}
  body{
    font-family:'Roboto','Noto Sans KR',-apple-system,BlinkMacSystemFont,sans-serif;
    color:var(--fg);background:var(--surface);
    line-height:1.43;letter-spacing:.25px;word-break:keep-all;
    -webkit-font-smoothing:antialiased;
  }
  h1,h2,h3{font-weight:500;letter-spacing:-.2px;line-height:1.25;}
  .g-dots{display:inline-flex;gap:4px;align-items:center;}
  .g-dots i{width:8px;height:8px;border-radius:50%;display:block;}
  .g-dots i:nth-child(1){background:var(--m-blue);}
  .g-dots i:nth-child(2){background:var(--m-red);}
  .g-dots i:nth-child(3){background:var(--m-yellow);}
  .g-dots i:nth-child(4){background:var(--m-green);}
  .mark{
    display:grid;place-items:center;background:var(--p500);color:#fff;
    font-weight:700;letter-spacing:-.5px;border-radius:var(--r-lg) var(--r-lg) var(--r-lg) 5px;
  }
"""

def _svg_bar_chart(chart):
    """수치 비교용 가로 막대 그래프를 SVG로 그립니다(인쇄에서도 선명)."""
    items = [it for it in (chart.get("items") or []) if isinstance(it.get("value"), (int, float))]
    if not items:
        return ""
    unit = chart.get("unit", "")
    top = max(float(it["value"]) for it in items) or 1.0
    palette = ["var(--m-blue)", "var(--m-green)", "var(--m-yellow)", "var(--m-red)", "var(--p700)"]

    row_h, gap, label_w, pad = 30, 10, 108, 8
    height = len(items) * (row_h + gap) - gap + pad * 2
    bar_max = 560 - label_w - 62

    rows = []
    for i, it in enumerate(items):
        y = pad + i * (row_h + gap)
        width = max(4.0, float(it["value"]) / top * bar_max)
        color = palette[i % len(palette)]
        name = html_escape(str(it.get("name", "")))
        value = it["value"]
        shown = f"{value:g}{unit}" if isinstance(value, float) else f"{value}{unit}"
        rows.append(
            f'<text x="{label_w - 10}" y="{y + row_h / 2 + 4}" text-anchor="end" '
            f'font-size="12" fill="#5F6368">{name}</text>'
            f'<rect x="{label_w}" y="{y}" width="{width:.1f}" height="{row_h}" '
            f'rx="6" fill="{color}"/>'
            f'<text x="{label_w + width + 8:.1f}" y="{y + row_h / 2 + 4}" '
            f'font-size="12" font-weight="500" fill="#3C4043">{html_escape(shown)}</text>'
        )
    caption = chart.get("caption", "")
    head = (f'<div class="chart-cap"><span class="g-dots"><i></i><i></i><i></i><i></i></span>'
            f'{html_escape(caption)}</div>') if caption else ""
    return (f'<div class="chart">{head}'
            f'<svg viewBox="0 0 560 {height}" width="100%" height="{height}" '
            f'role="img" aria-label="{html_escape(caption)}">{"".join(rows)}</svg></div>')

def _table_html(table):
    headers = table.get("headers") or []
    rows = table.get("rows") or []
    if not headers or not rows:
        return ""
    caption = table.get("caption", "")
    head = (f'<div class="tbl-cap">{html_escape(caption)}</div>') if caption else ""
    ths = "".join(f"<th>{html_escape(str(h))}</th>" for h in headers)
    trs = ""
    for row in rows:
        tds = "".join(f"<td>{html_escape(str(c))}</td>" for c in row)
        trs += f"<tr>{tds}</tr>"
    return (f'<div class="tbl-wrap">{head}<table><thead><tr>{ths}</tr></thead>'
            f"<tbody>{trs}</tbody></table></div>")

CALLOUT_STYLE = {
    "law": ("법령 근거", "law"),
    "tip": ("공략 팁", "tip"),
    "warn": ("주의", "warn"),
}

def generate_handout_html(hd, speaker):
    """학생에게 그대로 배포할 수 있는 요약 학습자료 (Material Design)"""
    title = hd.get("title", "요약 학습자료")
    subtitle = hd.get("subtitle", "")
    intro = hd.get("intro", "")
    sections = hd.get("sections") or []
    terms = hd.get("terms") or []
    flow = hd.get("flow") or {}
    checklist = hd.get("checklist") or []

    body = ""
    for idx, sec in enumerate(sections, 1):
        no = html_escape(str(sec.get("no") or f"{idx:02d}"))
        body += f"""
    <section class="sec">
      <div class="sec-head">
        <span class="sec-no">{no}</span>
        <div>
          <h2>{html_escape(sec.get('heading',''))}</h2>
          <p class="sec-sum">{html_escape(sec.get('summary',''))}</p>
        </div>
      </div>"""
        points = sec.get("key_points") or []
        if points:
            body += '<ul class="points">'
            for p in points:
                body += f"<li>{html_escape(str(p))}</li>"
            body += "</ul>"
        if isinstance(sec.get("table"), dict):
            body += _table_html(sec["table"])
        if isinstance(sec.get("chart"), dict):
            body += _svg_bar_chart(sec["chart"])
        co = sec.get("callout")
        if isinstance(co, dict) and co.get("text"):
            label, cls = CALLOUT_STYLE.get(co.get("kind", "tip"), CALLOUT_STYLE["tip"])
            co_title = html_escape(co.get("title") or label)
            body += (f'<div class="callout {cls}"><strong>{co_title}</strong>'
                     f'<span>{html_escape(co["text"])}</span></div>')
        body += "</section>"

    if isinstance(flow, dict) and (flow.get("steps") or []):
        steps = flow["steps"]
        body += f"""
    <section class="sec">
      <div class="sec-head"><span class="sec-no flow-no">▸</span>
        <div><h2>{html_escape(flow.get('caption') or '절차 흐름')}</h2></div></div>
      <div class="flow">"""
        for i, s in enumerate(steps):
            if i:
                body += '<span class="flow-arrow">›</span>'
            body += f'<div class="flow-step"><b>{i+1}</b>{html_escape(str(s))}</div>'
        body += "</div></section>"

    if terms:
        body += """
    <section class="sec">
      <div class="sec-head"><span class="sec-no term-no">用</span>
        <div><h2>꼭 알아야 할 용어</h2></div></div>
      <div class="terms">"""
        for t in terms:
            body += (f'<div class="term"><b>{html_escape(str(t.get("term","")))}</b>'
                     f'<span>{html_escape(str(t.get("meaning","")))}</span></div>')
        body += "</div></section>"

    if checklist:
        body += """
    <section class="sec check-sec">
      <div class="sec-head"><span class="sec-no chk-no">✓</span>
        <div><h2>시험 직전 최종 점검</h2></div></div>
      <div class="checks">"""
        for c in checklist:
            body += f'<label class="chk"><span class="box"></span>{html_escape(str(c))}</label>'
        body += "</div></section>"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_escape(title)} — 요약 학습자료</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Noto+Sans+KR:wght@400;500;700&display=swap">
<style>
{MATERIAL_CSS}
  body{{background:var(--surface-low);}}
  .wrap{{max-width:900px;margin:0 auto;padding:28px 20px 64px;}}
  .hero{{
    background:
      radial-gradient(circle at 92% 8%, rgba(251,188,4,.22) 0 20%, transparent 21%),
      radial-gradient(circle at 6% 96%, rgba(234,67,53,.16) 0 18%, transparent 19%),
      var(--p50);
    border:1px solid var(--line-soft);
    border-radius:var(--r-xl) var(--r-xl) var(--r-md) var(--r-xl);
    padding:30px 30px 28px;margin-bottom:20px;
  }}
  .hero-top{{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:20px;}}
  .brand{{display:flex;align-items:center;gap:11px;font-size:14px;font-weight:500;}}
  .brand .mark{{width:40px;height:40px;font-size:13px;}}
  .chip{{
    display:inline-flex;align-items:center;gap:7px;padding:7px 13px;
    background:var(--surface);border:1px solid var(--line);border-radius:var(--r-full);
    font-size:12px;font-weight:500;color:var(--fg2);
  }}
  .hero h1{{font-size:32px;line-height:1.2;margin-bottom:10px;}}
  .hero .sub{{font-size:16px;font-weight:500;color:var(--p700);margin-bottom:14px;}}
  .hero .intro{{font-size:14px;color:var(--fg2);line-height:1.6;max-width:64ch;}}
  .sec{{
    background:var(--surface);border:1px solid var(--line-soft);
    border-radius:var(--r-lg);padding:24px 26px;margin-bottom:14px;
  }}
  .sec:nth-of-type(even){{border-radius:var(--r-lg) var(--r-lg) var(--r-lg) var(--r-md);}}
  .sec-head{{display:flex;align-items:flex-start;gap:14px;margin-bottom:14px;}}
  .sec-no{{
    flex:none;width:40px;height:40px;display:grid;place-items:center;
    background:var(--p100);color:var(--p800);font-weight:700;font-size:14px;
    border-radius:var(--r-md);
  }}
  .flow-no{{background:var(--success-bg);color:var(--success-fg);}}
  .term-no{{background:var(--warning-bg);color:var(--warning-fg);}}
  .chk-no{{background:var(--p500);color:#fff;}}
  .sec h2{{font-size:21px;margin-bottom:5px;}}
  .sec-sum{{font-size:13.5px;color:var(--fg2);line-height:1.6;}}
  .points{{list-style:none;display:flex;flex-direction:column;gap:8px;margin:14px 0 0;}}
  .points li{{
    position:relative;padding:10px 14px 10px 34px;background:var(--surface-container);
    border-radius:var(--r-md);font-size:14px;line-height:1.55;
  }}
  .points li::before{{
    content:"";position:absolute;left:14px;top:17px;width:9px;height:9px;
    border-radius:50%;background:var(--p500);
  }}
  .tbl-wrap{{margin-top:16px;overflow-x:auto;}}
  .tbl-cap,.chart-cap{{
    display:flex;align-items:center;gap:8px;font-size:12px;font-weight:500;
    color:var(--fg2);margin-bottom:8px;letter-spacing:.4px;
  }}
  table{{width:100%;border-collapse:collapse;font-size:13.5px;min-width:min(100%,420px);}}
  th{{
    background:var(--p50);color:var(--p900);font-weight:500;text-align:left;
    padding:11px 13px;border-bottom:1px solid var(--line);
  }}
  td{{padding:11px 13px;border-bottom:1px solid var(--line-soft);color:var(--fg2);}}
  tbody tr:nth-child(even) td{{background:var(--n50);}}
  .chart{{margin-top:18px;padding:16px;background:var(--surface-low);border-radius:var(--r-md);}}
  .callout{{
    display:flex;flex-direction:column;gap:5px;margin-top:16px;
    padding:14px 16px;border-radius:var(--r-md);font-size:13.5px;line-height:1.6;
  }}
  .callout strong{{font-size:12px;font-weight:700;letter-spacing:.5px;}}
  .callout.law{{background:var(--info-bg);color:var(--p900);}}
  .callout.law strong{{color:var(--p700);}}
  .callout.tip{{background:var(--success-bg);color:#14532d;}}
  .callout.tip strong{{color:var(--success-fg);}}
  .callout.warn{{background:var(--warning-bg);color:#6b4b00;}}
  .callout.warn strong{{color:var(--warning-fg);}}
  .flow{{display:flex;flex-wrap:wrap;align-items:center;gap:9px;}}
  .flow-step{{
    display:flex;align-items:center;gap:9px;padding:11px 15px;
    background:var(--p50);border-radius:var(--r-full);font-size:13.5px;font-weight:500;
  }}
  .flow-step b{{
    width:21px;height:21px;display:grid;place-items:center;border-radius:50%;
    background:var(--p500);color:#fff;font-size:11px;
  }}
  .flow-arrow{{color:var(--p300);font-size:19px;font-weight:700;}}
  .terms{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px;}}
  .term{{
    display:flex;flex-direction:column;gap:5px;padding:13px 15px;
    background:var(--surface-container);border-radius:var(--r-md);
  }}
  .term b{{font-size:14px;font-weight:700;color:var(--p800);}}
  .term span{{font-size:13px;color:var(--fg2);line-height:1.55;}}
  .check-sec{{background:var(--p50);border-color:var(--p200);}}
  .checks{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:9px;}}
  .chk{{
    display:flex;align-items:center;gap:11px;padding:12px 15px;background:var(--surface);
    border:1px solid var(--line);border-radius:var(--r-md);font-size:13.5px;font-weight:500;
  }}
  .chk .box{{
    flex:none;width:18px;height:18px;border:2px solid var(--p500);
    border-radius:var(--r-sm)/2;border-radius:5px;
  }}
  footer{{
    margin-top:26px;padding-top:20px;border-top:1px solid var(--line);
    display:flex;align-items:center;justify-content:space-between;gap:12px;
    font-size:12px;color:var(--fg3);
  }}
  @media print{{
    body{{background:#fff;-webkit-print-color-adjust:exact;print-color-adjust:exact;}}
    .wrap{{max-width:none;padding:0;}}
    .sec{{break-inside:avoid;page-break-inside:avoid;}}
    .hero{{break-after:avoid;}}
  }}
  @media (max-width:640px){{
    .hero{{padding:22px 20px;}} .hero h1{{font-size:26px;}} .sec{{padding:20px 18px;}}
  }}
</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <div class="hero-top">
      <div class="brand"><span class="mark">강의</span><span>{html_escape(speaker)} 강의 요약</span></div>
      <span class="chip"><span class="g-dots"><i></i><i></i><i></i><i></i></span>학습자료</span>
    </div>
    <h1>{html_escape(title)}</h1>
    <div class="sub">{html_escape(subtitle)}</div>
    <p class="intro">{html_escape(intro)}</p>
  </header>
{body}
  <footer>
    <span>{html_escape(title)} · {html_escape(speaker)} 강의 기반</span>
    <span class="g-dots"><i></i><i></i><i></i><i></i></span>
  </footer>
</div>
</body>
</html>"""

def generate_onepager_html(od, speaker):
    """A4 한 장에 맞춘 체계도 (Material Design)"""
    title = od.get("title", "핵심 체계도")
    center = od.get("center", "")
    branches = od.get("branches") or []
    key_numbers = od.get("key_numbers") or []
    note = od.get("footer_note", "")

    accents = ["var(--m-blue)", "var(--m-green)", "var(--m-yellow)", "var(--m-red)",
               "var(--p700)", "var(--p300)"]
    tints = ["var(--p50)", "var(--success-bg)", "var(--warning-bg)", "var(--error-bg)",
             "var(--p100)", "var(--surface-container)"]

    cards = ""
    for i, b in enumerate(branches):
        items = b.get("items") or []
        lis = "".join(f"<li>{html_escape(str(x))}</li>" for x in items)
        cards += f"""
      <article class="br" style="--accent:{accents[i % len(accents)]};--tint:{tints[i % len(tints)]}">
        <div class="br-head"><span class="br-no">{html_escape(str(b.get('no') or i + 1))}</span>
          <h3>{html_escape(str(b.get('heading','')))}</h3></div>
        <ul>{lis}</ul>
      </article>"""

    nums = ""
    if key_numbers:
        cells = "".join(
            f'<div class="kn"><b>{html_escape(str(k.get("value","")))}</b>'
            f'<span>{html_escape(str(k.get("label","")))}</span></div>'
            for k in key_numbers[:5]
        )
        nums = f'<div class="knums">{cells}</div>'

    count = len(branches)
    cols = 2 if count <= 4 else 3
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_escape(title)} — A4 체계도</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Noto+Sans+KR:wght@400;500;700&display=swap">
<style>
{MATERIAL_CSS}
  @page{{size:A4 portrait;margin:0;}}
  body{{background:var(--n200);display:flex;justify-content:center;padding:16px;}}
  .page{{
    width:210mm;height:297mm;flex:none;background:var(--surface);
    padding:12mm 11mm 9mm;display:flex;flex-direction:column;overflow:hidden;
    box-shadow:var(--sh-3);
  }}
  .top{{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:5mm;}}
  .brand{{display:flex;align-items:center;gap:9px;font-size:11px;font-weight:500;color:var(--fg2);}}
  .brand .mark{{width:30px;height:30px;font-size:11px;}}
  h1{{font-size:23px;line-height:1.15;}}
  .center{{
    display:flex;align-items:center;gap:11px;margin-bottom:5mm;padding:11px 16px;
    background:linear-gradient(100deg,var(--p600),var(--p800));color:#fff;
    border-radius:var(--r-xl) var(--r-xl) var(--r-md) var(--r-xl);
  }}
  .center .lab{{
    font-size:9.5px;font-weight:500;letter-spacing:1px;text-transform:uppercase;
    background:rgba(255,255,255,.22);padding:4px 9px;border-radius:var(--r-full);flex:none;
  }}
  .center strong{{font-size:17px;font-weight:500;letter-spacing:-.2px;}}
  .knums{{display:flex;gap:6px;margin-bottom:4mm;}}
  .kn{{
    flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;
    padding:8px 5px;background:var(--surface-container);border-radius:var(--r-md);
  }}
  .kn b{{font-size:16px;font-weight:700;color:var(--p700);letter-spacing:-.3px;}}
  .kn span{{font-size:9px;color:var(--fg2);text-align:center;line-height:1.3;}}
  .grid{{
    flex:1;display:grid;grid-template-columns:repeat({cols},1fr);
    gap:4mm;min-height:0;align-content:start;
  }}
  .br{{
    background:var(--tint);border-left:4px solid var(--accent);
    border-radius:var(--r-md);padding:10px 12px;min-height:0;overflow:hidden;
  }}
  .br-head{{display:flex;align-items:center;gap:8px;margin-bottom:7px;}}
  .br-no{{
    flex:none;width:20px;height:20px;display:grid;place-items:center;border-radius:6px;
    background:var(--accent);color:#fff;font-size:11px;font-weight:700;
  }}
  .br h3{{font-size:13px;font-weight:700;line-height:1.25;}}
  .br ul{{list-style:none;display:flex;flex-direction:column;gap:4px;}}
  .br li{{
    position:relative;padding-left:11px;font-size:10.5px;line-height:1.45;color:var(--n800);
  }}
  .br li::before{{
    content:"";position:absolute;left:0;top:6px;width:5px;height:5px;
    border-radius:50%;background:var(--accent);
  }}
  .note{{
    margin-top:4mm;padding:9px 14px;background:var(--p50);
    border-radius:var(--r-md);font-size:11px;font-weight:500;color:var(--p900);
    display:flex;align-items:center;gap:9px;
  }}
  .foot{{
    margin-top:3mm;padding-top:2.5mm;border-top:1px solid var(--line-soft);
    display:flex;align-items:center;justify-content:space-between;
    font-size:9px;color:var(--fg3);
  }}
  @media print{{
    body{{background:#fff;padding:0;-webkit-print-color-adjust:exact;print-color-adjust:exact;}}
    .page{{box-shadow:none;width:210mm;height:297mm;}}
  }}
</style>
</head>
<body>
  <div class="page">
    <div class="top">
      <div class="brand"><span class="mark">체계</span><span>{html_escape(speaker)} 강의 · 한 장 요약</span></div>
      <span class="g-dots"><i></i><i></i><i></i><i></i></span>
    </div>
    <h1>{html_escape(title)}</h1>
    <div class="center"><span class="lab">핵심</span><strong>{html_escape(center)}</strong></div>
    {nums}
    <div class="grid">{cards}
    </div>
    {f'<div class="note"><span class="g-dots"><i></i><i></i><i></i><i></i></span>{html_escape(note)}</div>' if note else ''}
    <div class="foot"><span>{html_escape(title)} · {html_escape(speaker)}</span><span>A4 1장 · 인쇄용</span></div>
  </div>
</body>
</html>"""

# ================= ==========================================
# 10. Streamlit 사용자 인터페이스
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

_drive_on, _drive_path = drive_status()
if _drive_on:
    st.sidebar.success(f"☁️ 구글 드라이브에 자동 저장 중\n\n`{_drive_path.name}` 폴더")
    st.sidebar.caption("다른 컴퓨터에서도 드라이브만 연결돼 있으면 이 목록이 그대로 보입니다.")
elif is_shared_host():
    st.sidebar.caption("⚠️ 온라인(웹 주소)에서는 저장분이 앱 재시작 시 사라집니다. "
                       "중요한 결과는 다운로드해 두세요.")
else:
    with st.sidebar.expander("☁️ 드라이브에 자동 저장하기"):
        st.markdown(
            """
결과를 여러 컴퓨터에서 함께 보려면 **구글 드라이브 데스크톱 앱**을 설치하세요.
설치하면 이 앱이 알아서 찾아 드라이브에 저장합니다. 별도 설정은 없습니다.

👉 [구글 드라이브 데스크톱 내려받기](https://www.google.com/drive/download/)

설치 후 로그인하고 이 앱을 다시 켜면, 위에 `자동 저장 중`으로 바뀝니다.
그때부터 결과가 `내 드라이브 / 강의콘텐츠생성기` 폴더에 쌓입니다.
            """
        )
    st.sidebar.caption("지금은 이 컴퓨터에만 저장됩니다.")

# --- 1단계: 입력 ---
if st.session_state.stage == "input":
    st.components.v1.html(
        """
<div style="font-family:'Pretendard',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     display:flex;gap:10px;align-items:stretch;flex-wrap:wrap;">

  <div style="flex:1;min-width:150px;background:#FAF8F1;border:1px solid #E7E1D5;
       border-radius:12px;padding:14px 16px;">
    <div style="display:inline-block;background:#C96442;color:#fff;font-weight:800;
         font-size:12px;border-radius:999px;padding:2px 9px;margin-bottom:8px;">1단계</div>
    <div style="font-weight:800;font-size:14px;color:#28251E;margin-bottom:4px;">넣기</div>
    <div style="font-size:12.5px;color:#57534A;line-height:1.5;">
      유튜브 주소를 넣습니다.<br>
      자막이 없으면 강의 내용을<br>직접 붙여넣어도 됩니다.
    </div>
  </div>

  <div style="display:flex;align-items:center;color:#C96442;font-size:20px;font-weight:900;">›</div>

  <div style="flex:1;min-width:150px;background:#FAF8F1;border:1px solid #E7E1D5;
       border-radius:12px;padding:14px 16px;">
    <div style="display:inline-block;background:#C96442;color:#fff;font-weight:800;
         font-size:12px;border-radius:999px;padding:2px 9px;margin-bottom:8px;">2단계</div>
    <div style="font-weight:800;font-size:14px;color:#28251E;margin-bottom:4px;">정리하기</div>
    <div style="font-size:12.5px;color:#57534A;line-height:1.5;">
      버튼을 누르면 AI가<br>
      오타를 고치고 법령 용어를<br>바로잡아 정리합니다.
    </div>
  </div>

  <div style="display:flex;align-items:center;color:#C96442;font-size:20px;font-weight:900;">›</div>

  <div style="flex:1.35;min-width:190px;background:#F5E4DA;border:1px solid #E0876A;
       border-radius:12px;padding:14px 16px;">
    <div style="display:inline-block;background:#AD4F30;color:#fff;font-weight:800;
         font-size:12px;border-radius:999px;padding:2px 9px;margin-bottom:8px;">3단계</div>
    <div style="font-weight:800;font-size:14px;color:#28251E;margin-bottom:6px;">7종이 한 번에</div>
    <div style="font-size:12px;color:#57534A;line-height:1.85;">
      <span style="background:#fff;border-radius:5px;padding:1px 6px;margin-right:3px;">슬라이드</span>
      <span style="background:#fff;border-radius:5px;padding:1px 6px;margin-right:3px;">웹 학습지</span>
      <span style="background:#fff;border-radius:5px;padding:1px 6px;margin-right:3px;">블로그 글</span>
      <span style="background:#fff;border-radius:5px;padding:1px 6px;margin-right:3px;">한눈 요약</span>
      <span style="background:#fff;border-radius:5px;padding:1px 6px;margin-right:3px;">체계도</span>
      <span style="background:#fff;border-radius:5px;padding:1px 6px;margin-right:3px;">5지선다</span>
      <span style="background:#fff;border-radius:5px;padding:1px 6px;">O/X</span>
    </div>
  </div>

</div>
""",
        height=175,
    )

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
                    raw, fetch_error = get_youtube_transcript(video_id)
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
                    st.warning(fetch_error or "자막을 자동으로 가져올 수 없습니다.")

    st.divider()
    st.subheader("🎙 녹음 파일로 시작하기")
    st.caption("강의 녹음(mp3·wav·m4a 등)을 올리면 AI가 받아쓰고 오타·법령 용어까지 한 번에 정리합니다. "
               "유튜브 자막이 없는 강의도 이 방법으로 됩니다.")
    audio_file = st.file_uploader(
        "녹음 파일 올리기", type=AUDIO_TYPES, key="audio_upload",
        help="mp3, wav, m4a, aac, ogg, flac, mp4, webm — 영상 파일도 소리만 뽑아 전사합니다.",
    )
    if audio_file is not None:
        size_mb = len(audio_file.getvalue()) / (1024 * 1024)
        st.caption(f"올린 파일: **{audio_file.name}** · {size_mb:.1f}MB")

    if st.button("🎙 녹음 파일 전사하고 정리하기", type="primary", key="btn_audio"):
        if not api_key:
            st.error("사이드바에 Gemini API Key를 먼저 입력해주세요.")
        elif audio_file is None:
            st.error("녹음 파일을 먼저 올려주세요.")
        else:
            genai.configure(api_key=api_key)
            with st.spinner("녹음을 받아쓰고 정리하는 중입니다. 길이에 따라 몇 분 걸릴 수 있습니다..."):
                try:
                    model = get_working_model()
                    text = transcribe_audio(model, audio_file.getvalue(), audio_file.name)
                    if not text:
                        st.error("전사 결과가 비어 있습니다. 소리가 들어 있는 파일인지 확인해주세요.")
                    else:
                        st.session_state.raw_transcript = text
                        st.session_state.transcript = text
                        st.session_state.stage = "review"
                        st.rerun()
                except Exception as e:
                    st.error(f"전사 중 오류가 발생했습니다: {e}")

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

    st.divider()
    st.subheader("만들 것만 골라주세요")
    st.caption("항목마다 AI를 한 번씩 부르기 때문에, 고른 개수만큼만 비용이 듭니다. "
               "필요한 것만 고르면 그만큼 저렴합니다. 나중에 결과 화면에서 더 추가할 수도 있습니다.")

    # (세션키, 화면이름, 설명, 기본선택) — 슬라이드와 학습지는 한 번의 호출을 함께 쓴다
    PICKS = [
        ("pick_data", "슬라이드 + 웹 학습지", "발표용 슬라이드와 웹 학습지 (한 번에 같이 만들어짐)", True),
        ("pick_blog", "블로그 글", "네이버·티스토리에 바로 올릴 SEO 글", True),
        ("pick_summary", "한눈 요약", "핵심 수치·비교표·절차를 한 화면에", True),
        ("pick_mindmap", "체계도", "단원 구조를 계층으로 정리", True),
        ("pick_mcq", "5지선다 문제", "정답·해설 포함 5문제", True),
        ("pick_ox", "O/X 문제", "정답·해설 포함 10문제", True),
        ("pick_handout", "학생 배포용 자료", "표·그래프·용어·점검표가 든 인쇄용 자료", False),
        ("pick_onepager", "A4 한 장 체계도", "인쇄하면 딱 한 장으로 나오는 요약", False),
    ]
    for key, _, _, default in PICKS:
        if key not in st.session_state:
            st.session_state[key] = default

    b1, b2, b3 = st.columns([1, 1, 2.2])
    with b1:
        if st.button("전부 선택", key="pick_all"):
            for key, _, _, _ in PICKS:
                st.session_state[key] = True
            st.rerun()
    with b2:
        if st.button("전부 해제", key="pick_none"):
            for key, _, _, _ in PICKS:
                st.session_state[key] = False
            st.rerun()

    left, right = st.columns(2)
    for i, (key, label, help_text, _) in enumerate(PICKS):
        with (left if i % 2 == 0 else right):
            st.checkbox(label, key=key, help=help_text)

    chosen = [key for key, _, _, _ in PICKS if st.session_state.get(key)]
    calls = len(chosen)
    if calls:
        st.info(f"고른 항목 **{calls}개** · AI 호출 **{calls}번**  \n"
                f"전부(8개) 고를 때보다 약 **{round((1 - calls / len(PICKS)) * 100)}%** 적게 듭니다.")
    else:
        st.warning("적어도 하나는 골라주세요.")

    col_a, col_b = st.columns([1.4, 1])
    with col_a:
        if st.button(f"🚀 고른 {calls}개 만들기", type="primary", disabled=(calls == 0)):
            st.session_state.transcript = edited
            genai.configure(api_key=api_key)
            transcript = edited
            results = {"transcript": transcript,
                       "saved_at": datetime.now().isoformat(timespec="seconds"),
                       "title": "강의 자료", "speaker": "고상철"}
            progress = st.progress(0.0, text="생성 준비 중...")
            done = [0]

            def step(label):
                done[0] += 1
                progress.progress(done[0] / calls, text=f"{done[0]}/{calls} {label}")

            try:
                model = get_working_model()

                if st.session_state.pick_data:
                    step("슬라이드·학습지를 만드는 중...")
                    data = generate_structured_data(model, transcript)
                    results.update({"title": data.get("title", "강의 자료"),
                                    "speaker": data.get("speaker", "고상철"),
                                    "data": data})
                if st.session_state.pick_blog:
                    step("블로그 글을 작성하는 중...")
                    results["blog"] = generate_blog_post(model, transcript)
                if st.session_state.pick_summary:
                    step("한눈 요약을 만드는 중...")
                    results["summary"] = generate_summary_data(model, transcript)
                if st.session_state.pick_mindmap:
                    step("체계도를 만드는 중...")
                    results["mindmap"] = generate_mindmap_data(model, transcript)
                if st.session_state.pick_mcq:
                    step("5지선다 문제를 출제하는 중...")
                    results["mcq"] = generate_mcq(model, transcript, count=5).get("questions", [])
                if st.session_state.pick_ox:
                    step("O/X 문제를 출제하는 중...")
                    results["ox"] = generate_ox(model, transcript, count=10).get("questions", [])
                if st.session_state.pick_handout:
                    step("학생 배포용 자료를 만드는 중...")
                    results["handout"] = generate_handout_data(model, transcript)
                if st.session_state.pick_onepager:
                    step("A4 체계도를 만드는 중...")
                    results["onepager"] = generate_onepager_data(model, transcript)

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
        "🎒 8. 학생 배포용",
        "📐 9. A4 체계도",
    ])

    def ensure_part(result_key, label, generator, btn_key):
        """이 항목을 안 골랐으면 지금 만들 수 있게 버튼을 보여줍니다.
        이미 있으면 True를 돌려줘 결과를 그리게 합니다."""
        if r.get(result_key):
            return True
        st.info(f"‘{label}’은 아직 만들지 않았습니다. 지금 만들면 AI 호출 1번이 듭니다.")
        if st.button(f"✨ {label} 지금 만들기", key=btn_key, type="primary"):
            if not api_key:
                st.error("사이드바에 Gemini API Key를 먼저 입력해주세요.")
            else:
                genai.configure(api_key=api_key)
                with st.spinner(f"{label}을 만드는 중입니다..."):
                    try:
                        model = get_working_model()
                        r[result_key] = generator(model, r["transcript"])
                        if result_key == "data":
                            r["title"] = r["data"].get("title", r.get("title", "강의 자료"))
                            r["speaker"] = r["data"].get("speaker", r.get("speaker", "고상철"))
                        save_project(st.session_state.project_id, r)
                        st.rerun()
                    except Exception as e:
                        st.error(f"생성 실패: {e}")
        return False

    with tabs[0]:
        st.text_area("정리된 스크립트", value=r.get("transcript", ""), height=400, key="view_transcript")
        copy_box("원고", r.get("transcript", ""), "res_transcript")

    with tabs[1]:
        if ensure_part("data", "슬라이드 + 웹 학습지", generate_structured_data, "gen_data_slides"):
            html = generate_slides_html(r["data"])
            st.download_button("📥 슬라이드 HTML 다운로드", data=html,
                               file_name="slides.html", mime="text/html", key="dl_slides")
            st.components.v1.html(html, height=620, scrolling=True)

    with tabs[2]:
        if ensure_part("data", "슬라이드 + 웹 학습지", generate_structured_data, "gen_data_study"):
            html = generate_study_html(r["data"])
            st.download_button("📥 학습지 HTML 다운로드", data=html,
                               file_name="study_guide.html", mime="text/html", key="dl_study")
            st.components.v1.html(html, height=620, scrolling=True)

    with tabs[3]:
      if ensure_part("blog", "블로그 글", generate_blog_post, "gen_blog"):
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
      if ensure_part("summary", "한눈 요약", generate_summary_data, "gen_summary"):
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
      if ensure_part("mindmap", "체계도", generate_mindmap_data, "gen_mindmap"):
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
      if ensure_part("mcq", "5지선다 문제",
                     lambda m, t: generate_mcq(m, t, count=5).get("questions", []),
                     "gen_mcq"):
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
      if ensure_part("ox", "O/X 문제",
                     lambda m, t: generate_ox(m, t, count=10).get("questions", []),
                     "gen_ox"):
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

    # --- 8. 학생 배포용 요약 학습자료 (선택 생성) ---
    with tabs[8]:
        st.markdown("**학생에게 그대로 나눠줄 수 있는 요약 학습자료**입니다. "
                    "표·그래프·용어 정리·절차 흐름·최종 점검표가 들어갑니다. "
                    "디자인은 구글 머티리얼(Material Design) 스타일입니다.")

        if not r.get("handout"):
            st.info("필요할 때만 만들도록 따로 두었습니다. 아래 버튼을 누르면 생성합니다.")
            if st.button("🎒 학생 배포용 자료 만들기", type="primary", key="gen_handout"):
                if not api_key:
                    st.error("사이드바에 Gemini API Key를 먼저 입력해주세요.")
                else:
                    genai.configure(api_key=api_key)
                    with st.spinner("학생 배포용 자료를 만드는 중입니다..."):
                        try:
                            model = get_working_model()
                            r["handout"] = generate_handout_data(model, r["transcript"])
                            save_project(st.session_state.project_id, r)
                            st.rerun()
                        except Exception as e:
                            st.error(f"생성 실패: {e}")
        else:
            hd = r["handout"]
            html = generate_handout_html(hd, speaker)
            col1, col2, col3 = st.columns([1.1, 1.1, 1])
            with col1:
                st.download_button("📥 HTML 다운로드", data=html,
                                   file_name="handout.html", mime="text/html", key="dl_handout")
            with col2:
                try:
                    st.download_button("📄 PDF 다운로드", data=handout_pdf_bytes(hd, speaker),
                                       file_name="handout.pdf", mime="application/pdf",
                                       key="dl_handout_pdf")
                except Exception as e:
                    st.caption(f"PDF 변환 실패: {e}")
            with col3:
                if st.button("🔄 다시 만들기", key="regen_handout"):
                    r.pop("handout", None)
                    save_project(st.session_state.project_id, r)
                    st.rerun()
            st.caption("브라우저에서 열어 인쇄(Ctrl+P)하면 학생 배포용으로 바로 쓸 수 있습니다.")
            st.components.v1.html(html, height=760, scrolling=True)

    # --- 9. A4 한 장 체계도 (선택 생성) ---
    with tabs[9]:
        st.markdown("**A4 한 장에 전부 들어가는 체계도**입니다. "
                    "인쇄하면 딱 한 장으로 나오도록 분량을 맞춰 만듭니다. "
                    "디자인은 구글 머티리얼(Material Design) 스타일입니다.")

        if not r.get("onepager"):
            st.info("필요할 때만 만들도록 따로 두었습니다. 아래 버튼을 누르면 생성합니다.")
            if st.button("📐 A4 체계도 만들기", type="primary", key="gen_onepager"):
                if not api_key:
                    st.error("사이드바에 Gemini API Key를 먼저 입력해주세요.")
                else:
                    genai.configure(api_key=api_key)
                    with st.spinner("A4 한 장 체계도를 만드는 중입니다..."):
                        try:
                            model = get_working_model()
                            r["onepager"] = generate_onepager_data(model, r["transcript"])
                            save_project(st.session_state.project_id, r)
                            st.rerun()
                        except Exception as e:
                            st.error(f"생성 실패: {e}")
        else:
            od = r["onepager"]
            html = generate_onepager_html(od, speaker)
            col1, col2, col3 = st.columns([1.1, 1.1, 1])
            with col1:
                st.download_button("📥 HTML 다운로드", data=html,
                                   file_name="onepager_a4.html", mime="text/html",
                                   key="dl_onepager")
            with col2:
                try:
                    st.download_button("📄 PDF(A4) 다운로드", data=onepager_pdf_bytes(od, speaker),
                                       file_name="onepager_a4.pdf", mime="application/pdf",
                                       key="dl_onepager_pdf")
                except Exception as e:
                    st.caption(f"PDF 변환 실패: {e}")
            with col3:
                if st.button("🔄 다시 만들기", key="regen_onepager"):
                    r.pop("onepager", None)
                    save_project(st.session_state.project_id, r)
                    st.rerun()
            st.caption("인쇄할 때 배율은 100%, 여백은 '없음'으로 두면 A4 한 장에 정확히 맞습니다.")
            st.components.v1.html(html, height=1180, scrolling=True)
