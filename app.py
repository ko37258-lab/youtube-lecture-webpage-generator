import streamlit as st
import re
import json
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai

# Streamlit 페이지 설정
st.set_page_config(page_title="유튜브 강의 2종 웹페이지 자동 생성기", layout="wide")
st.title("🎥 유튜브 자막 기반 슬라이드 & 웹 학습지 자동 생성기")

# API 키 및 설정
api_key = st.sidebar.text_input("Gemini API Key 입력", type="password")

def extract_video_id(url):
    regex = r"(?:v=|\/\|youtu\.be\/|\/embed\/|\/v\/)([^\"&?\/\s]{11})"
    match = re.search(regex, url)
    return match.group(1) if match else None

def get_youtube_transcript(video_id):
    try:
        ytt_api = YouTubeTranscriptApi()
        fetched_transcript = ytt_api.fetch(video_id, languages=['ko'])
        return " ".join([snippet.text for snippet in fetched_transcript])
    except Exception as e:
        return None

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

# ================= ==========================================
# 3. Streamlit 사용자 인터페이스
# ============================================================
youtube_url = st.text_input("유튜브 영상 주소를 입력하세요:", placeholder="https://www.youtube.com/watch?v=...")

if st.button("🚀 2종 웹페이지 생성하기"):
    if not api_key:
        st.error("사이드바에 Gemini API Key를 먼저 입력해주세요.")
    else:
        video_id = extract_video_id(youtube_url)
        if not video_id:
            st.error("올바른 유튜브 URL이 아닙니다.")
        else:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-pro')

            with st.spinner("1/3 유튜브 자막을 추출하는 중입니다..."):
                transcript = get_youtube_transcript(video_id)

            if not transcript:
                st.error("자막을 가져올 수 없습니다. 한국어 자막이 있는 영상인지 확인해주세요.")
            else:
                st.success("자막 추출 완료!")
                with st.spinner("2/3 AI가 강의를 분석하고 구조화 데이터를 생성 중입니다..."):
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
                    try:
                        response = model.generate_content(prompt)
                        json_match = re.search(r"```json\s*(.*?)\s*```", response.text, re.DOTALL)
                        json_str = json_match.group(1) if json_match else response.text
                        data = json.loads(json_str)

                        with st.spinner("3/3 2종 HTML 웹페이지를 완성하는 중입니다..."):
                            slides_html = generate_slides_html(data)
                            study_html = generate_study_html(data)

                        st.success("🎉 생성 완료!")

                        tab1, tab2 = st.tabs(["📊 1. 프레젠테이션 슬라이드 (HTML)", "📄 2. 웹 요약 학습지 (HTML)"])

                        with tab1:
                            st.download_button("📥 슬라이드 HTML 다운로드", data=slides_html, file_name="slides_presentation.html", mime="text/html")
                            st.components.v1.html(slides_html, height=650, scrolling=True)

                        with tab2:
                            st.download_button("📥 웹 학습지 HTML 다운로드", data=study_html, file_name="study_guide.html", mime="text/html")
                            st.components.v1.html(study_html, height=650, scrolling=True)

                    except Exception as e:
                        st.error(f"처리 중 오류가 발생했습니다: {e}")
