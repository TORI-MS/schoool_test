import streamlit as st
import streamlit.components.v1 as components
import requests
import re
import json
from datetime import datetime, timedelta
from pathlib import Path

st.set_page_config(page_title="🏫 3-11 전용", page_icon="🏫", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #f0f2f8; color: #1a1a2e; }
    html, body, [class*="css"] { color: #1a1a2e; }
    .main .block-container { max-width: 720px; padding: 1rem 1.5rem 3rem; }
    .stAlert p { color: #1a1a2e !important; }
    .streamlit-expanderHeader { color: #1a1a2e !important; font-weight: 600; }
    .stSelectbox label { color: #1a1a2e !important; font-weight: 600; }
    h2, h3, h4 { color: #1a1a2e !important; }
    div[data-testid="stExpander"] { background: #fff; border-radius: 10px; margin-bottom: 6px; }
    div[data-testid="stMarkdownContainer"] { overflow: visible !important; height: auto !important; }
    div[data-testid="stMarkdownContainer"] > div { overflow: visible !important; height: auto !important; }
    .element-container { overflow: visible !important; }
    iframe { display: block; }
</style>
""", unsafe_allow_html=True)

# ── 기본 정보 ────────────────────────────────────────────────
API_KEY            = "ee1619138aef47d7a9a8200b7dbe52b5"
ATPT_OFCDC_SC_CODE = "E10"
SD_SCHUL_CODE      = "7310405"

# ── 날짜 계산 ────────────────────────────────────────────────
now = datetime.now()

def calc_target(dt: datetime):
    mins = dt.hour * 60 + dt.minute
    if dt.hour < 12:          # 자정~정오: 오늘
        return dt, False
    if mins >= 13 * 60 + 20:  # 13:20 이후: 내일
        return dt + timedelta(days=1), True
    return dt, False           # 12:00~13:19: 오늘

target_dt, is_tomorrow = calc_target(now)
weekday_names = ["월요일","화요일","수요일","목요일","금요일","토요일","일요일"]
weekday_num = target_dt.weekday()
weekday_kr  = weekday_names[weekday_num]

# 주말이면 → 다음 월요일로 급식/시간표 표시
is_weekend = weekday_num >= 5
if is_weekend:
    days_ahead = 7 - weekday_num   # 토요일=2, 일요일=1
    meal_dt    = target_dt + timedelta(days=days_ahead)
    display_day = "월요일"
else:
    meal_dt     = target_dt
    display_day = weekday_kr

target_str  = meal_dt.strftime("%Y%m%d")
target_disp = meal_dt.strftime("%Y년 %m월 %d일")

# ── 시간표 JSON 로드 ─────────────────────────────────────────
@st.cache_data(ttl=0)
def load_timetable():
    p = Path(__file__).parent / "timetable.json"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

timetable_data = load_timetable()

# ── D-day 이벤트 로드 ────────────────────────────────────────
@st.cache_data
def load_events():
    p = Path(__file__).parent / "time.json"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f).get("events", [])

events_data = load_events()


# ── 급식 API ─────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_meal(date_str: str):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "KEY": API_KEY, "Type": "json",
        "pIndex": 1, "pSize": 10,
        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": SD_SCHUL_CODE,
        "MLSV_YMD": date_str,
    }
    try:
        res = requests.get(url, params=params, timeout=8)
        res.raise_for_status()
        data = res.json()
        if "RESULT" in data:
            return [], None
        return data["mealServiceDietInfo"][1]["row"], None
    except requests.exceptions.ConnectionError:
        return [], "🌐 네트워크 연결 실패"
    except requests.exceptions.Timeout:
        return [], "⏱️ 요청 시간 초과"
    except Exception as e:
        return [], f"오류: {e}"

def parse_menu(raw: str) -> list:
    items = re.split(r"<br\s*/>", raw, flags=re.IGNORECASE)
    cleaned = []
    for item in items:
        item = re.sub(r"^\d+\.", "", item).strip()
        item = re.sub(r"\(\d+(\.\d+)*\)", "", item).strip()
        item = re.sub(r"\s+", " ", item)
        if item:
            cleaned.append(item)
    return cleaned

# ── 과목 색상 ─────────────────────────────────────────────────
# JSON 과목명 그대로 키로 등록 (띄어쓰기 변형 모두 포함)
subject_colors = {
    # 기본 / 공통
    "화작":               "#e17055",
    "영독":               "#0984e3",
    "진로":               "#636e72",
    "음악3":              "#e67e22",
    "확통":               "#e84393",
    "미적분":             "#d63031",
    "사물인터넷":         "#00b894",
    "여행지리":           "#1289A7",
    "심리학":             "#00cec9",
    "논술":               "#5758BB",
    "철학":               "#B53471",
    "세계사":             "#9980FA",
    "생명과학Ⅱ":         "#009432",
    "지구과학Ⅱ":         "#006266",
    "물리학Ⅱ":           "#5f27cd",
    "화학Ⅱ":             "#F79F1F",
    "교육학":             "#EA2027",
    "세계지리":           "#12CBC4",
    "영어권 문화":        "#D980FA",
    # 띄어쓰기 있는 변형
    "스포":               "#fd79a8",
    "스포츠":             "#fd79a8",
    "지식3":              "#6c5ce7",
    "지식재산일반":       "#6c5ce7",
    "미술 창작":          "#a29bfe",
    "미술창작":           "#a29bfe",
    "언어와 매체":        "#0652DD",
    "언어와매체":         "#0652DD",
    "윤리와 사상":        "#f9a825",
    "윤리와사상":         "#f9a825",
    "정치와 법":          "#C4380D",
    "정치와법":           "#C4380D",
    "음악 감상과 비평":   "#EE5A24",
    "음악감상과비평":     "#EE5A24",
    # 공통 과목
    "국어":   "#e17055",
    "수학":   "#00b894",
    "영어":   "#0984e3",
    "과학":   "#6c5ce7",
    "사회":   "#e0a800",
    "체육":   "#fd79a8",
    "음악":   "#e67e22",
    "미술":   "#a29bfe",
    "도덕":   "#00cec9",
    "자율":   "#636e72",
    "동아리": "#74b9ff",
    "청소":   "#fab1a0",
}

# ══════════════════════════════════════════════════════════════
#  1. 헤더
# ══════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="
    background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
    border-radius: 16px; padding: 20px 30px; color: #fff;
    font-family: sans-serif; margin-bottom: 0;
">
    <h1 style="margin:0; font-size:1.8rem; color:#fff;">🏫 3학년 11반 전용 사이트</h1>
    <p style="margin:6px 0 0; font-size:1rem; color:#cdd6f4;">
        📅 {target_disp} &nbsp;|&nbsp; {display_day}
    </p>
</div>
""", unsafe_allow_html=True)

# ── 실시간 시계 (헤더 바로 아래) ─────────────────────────────
components.html("""
<div style="font-family:sans-serif; padding:10px 4px 0;">
    <div style="display:flex; align-items:center; gap:14px;">
        <span id="clock" style="font-size:2rem; font-weight:800;
              letter-spacing:3px; color:#1a1a2e;">00:00:00</span>
        <span id="badge" style="background:#fd7272; color:#fff;
              border-radius:20px; padding:3px 14px;
              font-size:.88rem; font-weight:600; display:none;">내일 급식</span>
    </div>
</div>
<script>
function pad(n) { return String(n).padStart(2,"0"); }
function tick() {
    var d = new Date();
    var h = d.getHours(), m = d.getMinutes(), s = d.getSeconds();
    var tot = h * 60 + m;
    document.getElementById("clock").textContent = pad(h)+":"+pad(m)+":"+pad(s);
    var show = (h >= 12) && (tot >= 13*60+20);
    document.getElementById("badge").style.display = show ? "inline-block" : "none";
}
tick();
setInterval(tick, 1000);
</script>
""", height=55)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  2. D-day
# ══════════════════════════════════════════════════════════════
st.markdown('<h2 style="color:#1a1a2e; margin-bottom:8px;">📅 D-day</h2>', unsafe_allow_html=True)

_today = now.date()
_dday_html = ""
for ev in events_data:
    try:
        ev_date = datetime.strptime(ev["date"], "%Y-%m-%d").date()
    except Exception:
        continue
    diff = (ev_date - _today).days
    if diff < 0:
        label = f"D+{abs(diff)}"
        label_color = "#b2bec3"
        bg_color = "#f5f6fa"
        border_color = "#dfe6e9"
    elif diff == 0:
        label = "D-Day"
        label_color = "#fff"
        bg_color = ev.get("color", "#0f3460")
        border_color = ev.get("color", "#0f3460")
    else:
        label = f"D-{diff}"
        label_color = "#fff"
        bg_color = ev.get("color", "#0f3460")
        border_color = ev.get("color", "#0f3460")

    icon = ev.get("icon", "📌")
    name = ev.get("name", "")
    date_str = ev_date.strftime("%Y.%m.%d")

    _dday_html += f"""
<div style="background:#fff; border-radius:12px; padding:14px 20px;
            margin-bottom:10px; box-shadow:0 2px 10px rgba(0,0,0,0.07);
            border-left:5px solid {border_color};
            display:flex; align-items:center; justify-content:space-between;">
    <div>
        <div style="font-size:1rem; font-weight:700; color:#1a1a2e;">{icon} {name}</div>
        <div style="font-size:.82rem; color:#888; margin-top:2px;">{date_str}</div>
    </div>
    <div style="background:{bg_color}; color:{label_color};
                border-radius:20px; padding:5px 18px;
                font-size:1.1rem; font-weight:800; letter-spacing:1px; white-space:nowrap;">
        {label}
    </div>
</div>"""

st.markdown(_dday_html, unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  3. 급식
# ══════════════════════════════════════════════════════════════
st.markdown('<h2 style="color:#1a1a2e; margin-bottom:8px;">🍱 급식</h2>', unsafe_allow_html=True)

if is_weekend:
    st.markdown(
        '<p style="color:#888;font-size:.85rem;margin:-4px 0 8px;">📌 주말이라 다음주 월요일 급식을 보여드려요</p>',
        unsafe_allow_html=True
    )
meal_rows, meal_err = fetch_meal(target_str)
if meal_err:
    st.warning(meal_err)
elif not meal_rows:
    st.info("급식 정보가 없어요! 🏖️")
else:
    for row in meal_rows:
        meal_type = row.get("MMEAL_SC_NM", "급식")
        menu_list = parse_menu(row.get("DDISH_NM", ""))
        kcal      = row.get("CAL_INFO", "")
        menu_html = "".join(
            f'<div style="padding:3px 0; font-size:.97rem; color:#2d3436;">• {m}</div>'
            for m in menu_list
        )
        extra = (
            f'<span style="background:#fff3cd; color:#856404; border-radius:12px; '
            f'padding:2px 10px; font-size:.82rem;">🔥 {kcal}</span>'
            if kcal else ""
        )
        st.markdown(f"""
<div style="background:#fff; border-radius:12px; padding:18px 22px;
            margin-bottom:10px; box-shadow:0 2px 10px rgba(0,0,0,0.07);
            border-top: 4px solid #0f3460;">
    <div style="font-size:1rem; font-weight:700; color:#0f3460; margin-bottom:10px;">🥢 {meal_type}</div>
    {menu_html}
    <div style="margin-top:10px;">{extra}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  4. 시간표
# ══════════════════════════════════════════════════════════════
st.markdown(
    '<h2 style="color:#1a1a2e; margin-bottom:4px;">📚 시간표</h2>'
    '<p style="color:#888; font-size:.85rem; margin-bottom:12px;">3학년 11반</p>',
    unsafe_allow_html=True
)

student_num = st.selectbox(
    "👤 번호 선택",
    options=list(range(1, 31)),
    format_func=lambda x: f"{x}번",
    index=20,   # 기본값 21번
)

student_tt = timetable_data.get(str(student_num), {})
has_room   = "교실" in student_tt

def show_day(day: str, highlight: bool = False):
    subs  = student_tt.get(day, [])
    rooms = student_tt.get("교실", {}).get(day, []) if has_room else []
    if not subs:
        return

    bg           = "#eef2ff" if highlight else "#fff"
    border_color = "#0f3460" if highlight else "#dee2e6"
    border_thick = "3px"    if highlight else "1px"
    star         = "⭐ "    if highlight else ""

    st.markdown(
        f'<div style="background:{bg}; border:{border_thick} solid {border_color}; '
        f'border-radius:12px 12px 0 0; padding:10px 16px;">'
        f'<span style="font-weight:700; color:#0f3460; font-size:.97rem;">{star}{day}</span></div>',
        unsafe_allow_html=True
    )
    for i, subj in enumerate(subs):
        if not subj:
            continue
        room = rooms[i] if i < len(rooms) else ""

        # "업데이트" 과목 특별 표시
        if subj == "업데이트":
            st.markdown(
                f'<div style="display:flex; align-items:center; padding:6px 16px; '
                f'background:{bg}; '
                f'border-left:{border_thick} solid {border_color}; '
                f'border-right:{border_thick} solid {border_color}; '
                f'border-bottom:1px solid {"#dce3f5" if highlight else "#f0f0f0"};">'
                f'<span style="min-width:44px; font-size:.8rem; color:#868e96; font-weight:600;">{i+1}교시</span>'
                f'<span style="background:#f0f0f0; color:#aaa; border:1.5px dashed #ccc; '
                f'border-radius:16px; padding:3px 14px; font-weight:600; font-size:.85rem;">🔄 업데이트 예정</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            continue

        c    = subject_colors.get(subj, "#74b9ff")
        room_tag = (
            f'<span style="font-size:.73rem; color:#999; margin-left:8px;">📍{room}</span>'
            if room else ""
        )
        st.markdown(
            f'<div style="display:flex; align-items:center; padding:6px 16px; '
            f'background:{bg}; '
            f'border-left:{border_thick} solid {border_color}; '
            f'border-right:{border_thick} solid {border_color}; '
            f'border-bottom:1px solid {"#dce3f5" if highlight else "#f0f0f0"};">'
            f'<span style="min-width:44px; font-size:.8rem; color:#868e96; font-weight:600;">{i+1}교시</span>'
            f'<span style="background:{c}22; color:{c}; border:1.5px solid {c}; '
            f'border-radius:16px; padding:3px 14px; font-weight:700; font-size:.9rem;">{subj}</span>'
            f'{room_tag}</div>',
            unsafe_allow_html=True
        )
    st.markdown(
        f'<div style="background:{bg}; border:{border_thick} solid {border_color}; '
        f'border-top:none; border-radius:0 0 12px 12px; height:10px; margin-bottom:10px;"></div>',
        unsafe_allow_html=True
    )

if is_weekend:
    st.markdown(
        '<p style="color:#888;font-size:.85rem;margin:-4px 0 8px;">📌 주말이라 다음주 월요일 시간표를 보여드려요</p>',
        unsafe_allow_html=True
    )
other_days = [d for d in ["월요일","화요일","수요일","목요일","금요일"] if d != display_day]
show_day(display_day, highlight=True)
for day in other_days:
    with st.expander(f"📋 {day}"):
        show_day(day)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 푸터 ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#aaa; font-size:.8rem;'>"
    "데이터 출처: 나이스(NEIS) 교육정보 개방 포털</p>",
    unsafe_allow_html=True,
)
