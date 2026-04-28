import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="온디멘드 AI콜센터", page_icon="☎️", layout="centered")

CUSTOMER = {
    "고객명": "홍길순",
    "전화번호": "010-1234-5678",
    "고객유형": "시니어 고객",
    "요청": "내수역인데 서당1리 가는 택시 좀 보내줘",
    "출발지": "내수역",
    "목적지": "서당1리",
    "요청유형": "택시 배차",
}
DISPATCH = {
    "즉시배차": "불가",
    "대기시간": "57분",
    "예약시간": "오후 2시 20분",
    "차량": "우동택시",
    "차량번호": "충북 70 자 1234",
    "기사": "김우동 기사님",
}
FAILURES = {
    "STT 음성 인식 실패": {
        "장애상황": "잡음, 사투리, 통화품질 저하로 고객 음성이 텍스트로 변환되지 않음",
        "AI대응": "천천히 다시 말해달라고 요청하고 2회 실패 시 상담원 연결",
        "이관기준": "동일 항목 인식 실패 2회 이상",
        "고객멘트": "죄송합니다. 말씀을 정확히 듣지 못했습니다. 천천히 다시 말씀해 주세요.",
        "관리자알림": "STT 실패 콜로 등록하고 상담원 콘솔에 표시",
        "후속처리": "상담원이 고객 발화를 직접 확인하고 접수 완료 처리",
    },
    "GPT 응답 지연": {
        "장애상황": "AI 답변 생성이 지연되거나 고객 의도 판단이 불안정함",
        "AI대응": "룰 기반 안내 멘트를 먼저 송출하고 상담원 연결 준비",
        "이관기준": "응답 지연 5초 이상 또는 의도 분류 신뢰도 낮음",
        "고객멘트": "잠시만 기다려 주세요. 요청 내용을 확인하고 있습니다.",
        "관리자알림": "LLM 지연 콜로 등록하고 상담원 대기열로 이동",
        "후속처리": "상담원이 이어받아 상담 완료 후 로그를 개선 데이터로 분류",
    },
    "TTS 음성 출력 실패": {
        "장애상황": "AI 답변 문장은 생성되었지만 음성 출력이 끊기거나 실패함",
        "AI대응": "고정 안내 멘트를 송출하고 문자 안내를 병행",
        "이관기준": "음성 출력 실패 1회 이상",
        "고객멘트": "안내 음성이 원활하지 않아 문자로도 안내드리겠습니다.",
        "관리자알림": "TTS 장애 콜로 등록하고 상담원 확인 요청",
        "후속처리": "문자 발송 후 상담원이 필요 시 재통화",
    },
    "배차 API 장애": {
        "장애상황": "배차 시스템이 응답하지 않아 차량 조회 또는 예약 등록이 실패함",
        "AI대응": "임시 접수번호를 발급하고 상담원이 확인 후 재연락한다고 안내",
        "이관기준": "배차 API 타임아웃 또는 예약 등록 실패",
        "고객멘트": "현재 차량 조회가 지연되고 있습니다. 우선 접수해 두고 확인 후 다시 연락드리겠습니다.",
        "관리자알림": "배차 장애 콜로 등록하고 관리자 대시보드 최상단 표시",
        "후속처리": "관리자가 배차 시스템 복구 후 수동 예약 처리",
    },
    "고객 DB 조회 실패": {
        "장애상황": "고객 정보, 이전 예약 이력, 보호자 정보 조회가 실패함",
        "AI대응": "고객의 최소 필수 정보만 다시 확인하고 상담원에게 이관",
        "이관기준": "고객 식별 실패 또는 과거 이력 확인 불가",
        "고객멘트": "고객 정보를 다시 확인하겠습니다. 성함과 전화번호를 말씀해 주세요.",
        "관리자알림": "고객 DB 장애 콜로 등록",
        "후속처리": "상담원이 수기로 접수 후 시스템 복구 시 재등록",
    },
    "전화 끊김": {
        "장애상황": "상담 중 통화가 끊기거나 고객이 무응답 상태가 됨",
        "AI대응": "자동 콜백 예약 및 문자 안내 발송",
        "이관기준": "통화 종료 또는 10초 이상 무응답",
        "고객멘트": "통화가 끊겨 다시 연락드리겠습니다.",
        "관리자알림": "콜백 필요 콜로 등록",
        "후속처리": "상담원이 우선순위에 따라 재통화",
    },
    "긴급상황": {
        "장애상황": "고객이 아프다, 길을 잃었다, 사고가 났다 등 긴급 가능성을 언급함",
        "AI대응": "긴급 여부를 확인하고 즉시 상담원에게 최우선 이관",
        "이관기준": "응급, 사고, 실종, 고령자 혼란 키워드 감지",
        "고객멘트": "위급한 상황이면 119 또는 112로 바로 연락하셔야 합니다. 상담원에게 바로 연결하겠습니다.",
        "관리자알림": "긴급 콜로 최상단 표시 및 알림음 발생",
        "후속처리": "상담원이 보호자 또는 긴급기관 안내 절차 진행",
    },
}

CSS = '''
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800;900&display=swap');

:root {
    --bg:#F6F8FC;
    --surface:#FFFFFF;
    --ink:#111827;
    --muted:#667085;
    --line:#E5E7EB;
    --brand:#FFD400;
    --brand2:#FFB800;
    --navy:#111827;
    --blue:#2563EB;
    --red:#E53935;
    --green:#16A34A;
    --orange:#F97316;
    --shadow:0 18px 50px rgba(15,23,42,.11);
    --shadow-sm:0 8px 26px rgba(15,23,42,.08);
}

.stApp {
    background:
        radial-gradient(circle at 10% 0%, rgba(255,212,0,.22), transparent 28%),
        radial-gradient(circle at 90% 8%, rgba(37,99,235,.10), transparent 26%),
        var(--bg) !important;
    color:var(--ink) !important;
    font-family:'Noto Sans KR', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

* {
    font-family:'Noto Sans KR', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

.block-container {
    max-width:1120px;
    padding-top:1.25rem;
    padding-bottom:4rem;
}

header, footer, #MainMenu {
    visibility:hidden;
}

.card {
    background:rgba(255,255,255,.96) !important;
    color:var(--ink) !important;
    border:1px solid rgba(229,231,235,.92);
    border-radius:26px;
    padding:24px;
    margin-bottom:16px;
    box-shadow:var(--shadow-sm);
    backdrop-filter:blur(6px);
}

.card * {
    color:var(--ink) !important;
}

.yellow {
    background:linear-gradient(135deg,#FFF7C2 0%,#FFFDF0 100%) !important;
    color:var(--ink) !important;
    border:1px solid rgba(255,212,0,.85);
    border-radius:26px;
    padding:22px;
    margin-bottom:16px;
    box-shadow:0 12px 34px rgba(255,184,0,.16);
}

.yellow * {
    color:var(--ink) !important;
}

.title {
    font-size:40px;
    font-weight:900;
    letter-spacing:-1.2px;
    text-align:left;
    color:#FFFFFF !important;
}

.sub {
    color:#D1D5DB !important;
    font-size:17px;
    margin-top:8px;
    line-height:1.65;
    text-align:left;
}

.sec {
    font-size:24px;
    font-weight:900;
    letter-spacing:-.55px;
    margin:8px 0 14px;
    color:var(--ink) !important;
}

.header-card {
    background:linear-gradient(135deg, #111827 0%, #1F2937 58%, #2B2408 100%);
    border-radius:34px;
    padding:34px;
    box-shadow:var(--shadow);
    margin-bottom:18px;
    position:relative;
    overflow:hidden;
}

.header-card:after {
    content:'';
    position:absolute;
    right:-70px;
    top:-80px;
    width:250px;
    height:250px;
    border-radius:50%;
    background:rgba(255,212,0,.22);
}

.header-card * {
    position:relative;
    z-index:1;
}

.kicker {
    display:inline-flex;
    align-items:center;
    gap:8px;
    padding:8px 13px;
    background:rgba(255,255,255,.10);
    border:1px solid rgba(255,255,255,.16);
    border-radius:999px;
    font-size:14px;
    font-weight:900;
    color:#FFFFFF !important;
    margin-bottom:12px;
}

.flow {
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:10px;
    margin-top:22px;
}

.flow-step {
    background:rgba(255,255,255,.10);
    border:1px solid rgba(255,255,255,.15);
    border-radius:17px;
    padding:12px;
    text-align:center;
    font-size:14px;
    font-weight:900;
    color:#E5E7EB !important;
}

.flow-step.active {
    background:#FFD400;
    color:#111827 !important;
    border-color:#FFD400;
}

.badge {
    display:inline-flex;
    align-items:center;
    background:#EEF2FF;
    color:#3730A3 !important;
    border:1px solid #C7D2FE;
    padding:7px 11px;
    border-radius:999px;
    font-size:13px;
    font-weight:900;
    margin-right:6px;
    margin-bottom:8px;
}

.badge-warning {
    background:#FFF7ED;
    color:#C2410C !important;
    border-color:#FED7AA;
}

.badge-success {
    background:#ECFDF3;
    color:#027A48 !important;
    border-color:#ABEFC6;
}

.badge-dark {
    background:#111827;
    color:white !important;
    border-color:#111827;
}

.bubble {
    font-size:22px;
    line-height:1.75;
    font-weight:800;
    border-radius:26px;
    padding:24px;
    color:var(--ink) !important;
    box-shadow:0 10px 28px rgba(15,23,42,.08);
    margin-bottom:16px;
}

.user {
    background:#FFFFFF !important;
    border:1px solid #CBD5E1;
}

.ai {
    background:linear-gradient(135deg,#FFF8D6 0%,#FFFFFF 100%) !important;
    border:2px solid var(--brand);
}

.red {
    color:var(--red) !important;
    font-size:30px;
    font-weight:900;
    letter-spacing:-.4px;
}

.stButton>button {
    width:100%;
    min-height:3.35rem;
    border-radius:18px;
    font-size:17px;
    font-weight:900;
    background:linear-gradient(135deg,#FFD400 0%,#FFC000 100%) !important;
    color:#111827 !important;
    border:1px solid rgba(17,24,39,.08) !important;
    box-shadow:0 8px 18px rgba(255,184,0,.22);
    transition:all .16s ease;
}

.stButton>button:hover {
    transform:translateY(-1px);
    box-shadow:0 12px 26px rgba(255,184,0,.28);
    border-color:#FFB800 !important;
}

div[data-testid="stMetric"] {
    background:#FFFFFF !important;
    color:var(--ink) !important;
    border:1px solid var(--line);
    border-radius:22px;
    padding:16px;
    box-shadow:0 8px 22px rgba(15,23,42,.06);
}

div[data-testid="stMetric"] * {
    color:var(--ink) !important;
}

[data-testid="stDataFrame"] {
    border-radius:18px;
    overflow:hidden;
    box-shadow:0 10px 24px rgba(15,23,42,.06);
}

@media (max-width: 780px) {
    .block-container {
        padding-left:1rem;
        padding-right:1rem;
    }

    .title {
        font-size:31px;
    }

    .header-card {
        padding:25px;
        border-radius:26px;
    }

    .flow {
        grid-template-columns:repeat(2,1fr);
    }
}
</style>
'''
st.markdown(CSS, unsafe_allow_html=True)

def init_state():
    st.session_state.setdefault("page", "main")
    st.session_state.setdefault("handoff_reason", "")
    st.session_state.setdefault("logs", [])

def go(page):
    st.session_state.page = page
    st.rerun()

def add_log(status, result, reason="-"):
    st.session_state.logs.append({
        "시간": datetime.now().strftime("%H:%M:%S"),
        "고객": CUSTOMER["고객명"],
        "전화번호": CUSTOMER["전화번호"],
        "요청": CUSTOMER["요청유형"],
        "출발지": CUSTOMER["출발지"],
        "목적지": CUSTOMER["목적지"],
        "처리상태": status,
        "이관사유": reason,
        "결과": result,
    })

def handoff(reason):
    st.session_state.handoff_reason = reason
    add_log("상담원 이관", "인간 상담원 처리 대기", reason)
    go("handoff")

def money(n):
    return f"{int(n):,}원"

def cost_data():
    base = 5 * 3_500_000
    extra = {
        "4대보험/퇴직충당": int(base * 0.22),
        "야간/휴일수당": int(base * 0.18),
        "교육/품질관리": 1_200_000,
        "관리자/대체인력": 3_000_000,
        "장비/통신/공간": 2_500_000,
    }
    human = base + sum(extra.values())
    return base, extra, human, 13_500_000, 9_800_000

def header():
    st.markdown('''
    <div class="header-card">
        <div class="kicker">☎️ AI Call Center Demo</div>
        <div class="title">온디멘드 AI콜센터</div>
        <div class="sub">
            반복 상담은 AI가 즉시 처리하고, 장애·민원·긴급상황은 인간 상담원이 이어받는
            하이브리드 콜센터 데모입니다.
        </div>
        <div class="flow">
            <div class="flow-step active">콜 인입</div>
            <div class="flow-step">AI 분석</div>
            <div class="flow-step">예약/이관</div>
            <div class="flow-step">관리자 확인</div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

def nav():
    c1, c2 = st.columns(2)
    if c1.button("🏠 처음으로"):
        go("main")
    if c2.button("📊 관리자"):
        go("admin")

def main():
    header()
    st.markdown('''
<div class="card">
    <span class="badge badge-dark">Demo Scenario</span>
    <span class="badge">택시 예약</span>
    <span class="badge badge-warning">장애 대응</span>
    <span class="badge badge-success">비용 절감</span>
    <div class="sec">데모 목적</div>
    차량 배차, 예약, 주문, 스케줄링 업무를 AI가 먼저 상담하고
    장애·민원·긴급상황은 인간 상담원이 이어받는 구조를 보여줍니다.
</div>
''', unsafe_allow_html=True)
    if st.button("☎️ AI 상담 시작"):
        go("inbound")
    if st.button("⚠️ 장애 대응 데모 보기"):
        go("failure")
    if st.button("💰 운영비 절감 분석 보기"):
        go("cost")
    if st.button("📊 관리자 대시보드 보기"):
        go("admin")
    st.markdown('<div class="yellow"><div class="sec">핵심 메시지</div>AI콜센터는 상담원을 없애는 시스템이 아니라 반복 상담은 AI가 처리하고, 장애·민원·긴급상황은 인간이 처리하는 하이브리드 콜센터입니다.</div>', unsafe_allow_html=True)

def inbound():
    header()
    st.markdown('<div class="sec">1. 고객 전화 인입</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card"><h3>{CUSTOMER["고객명"]} · {CUSTOMER["고객유형"]}</h3><p><b>전화번호:</b> {CUSTOMER["전화번호"]}</p><div class="bubble user">🎤 고객 요청<br>“{CUSTOMER["요청"]}”</div></div>', unsafe_allow_html=True)
    if st.button("🤖 AI가 요청 분석"):
        go("analysis")
    nav()

def analysis():
    header()
    st.markdown('<div class="sec">2. AI 요청 분석</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("출발지", CUSTOMER["출발지"])
    c1.metric("목적지", CUSTOMER["목적지"])
    c2.metric("요청 유형", CUSTOMER["요청유형"])
    c2.metric("고객 유형", CUSTOMER["고객유형"])
    st.markdown(f'<div class="card"><div class="sec">배차 판단</div><p><b>즉시 배차 상태:</b> <span class="red">불가</span></p><p><b>예상 대기시간:</b> <span class="red">{DISPATCH["대기시간"]}</span></p><p><b>AI 판단:</b> 즉시 배차 대신 예약 배차 대안을 제시해야 합니다.</p></div>', unsafe_allow_html=True)
    if st.button("💬 AI 응답 생성"):
        go("response")
    nav()

def response():
    header()
    st.markdown('<div class="sec">3. AI 상담 응답</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="bubble ai">🤖 AI 상담원<br><br>어르신, 지금 주변에 바로 갈 수 있는 빈 차가 없어서<br><span class="red">{DISPATCH["대기시간"]}</span> 정도 기다리셔야 해요.<br><br>대신 <span class="red">{DISPATCH["예약시간"]}</span>에 맞춰 도착하는 택시를 미리 예약해 드릴까요?</div>', unsafe_allow_html=True)
    if st.button("✅ 고객이 예약 동의"):
        add_log("AI 단독 처리", "예약 완료")
        go("done")
    if st.button("☎️ 고객이 상담원 연결 요청"):
        handoff("고객 상담원 요청")
    if st.button("🎧 AI 인식 실패 발생"):
        handoff("STT/의도 인식 실패")
    if st.button("🚧 배차 시스템 장애 발생"):
        handoff("배차 API 장애")
    if st.button("🚨 긴급 상황 발생"):
        handoff("긴급상황")
    nav()

def done():
    header()
    st.success("예약 완료")
    st.balloons()
    st.markdown(f'''<div class="card"><div class="sec">예약 정보</div>
    <p><b>고객명:</b> {CUSTOMER["고객명"]}</p>
    <p><b>전화번호:</b> {CUSTOMER["전화번호"]}</p>
    <p><b>출발지:</b> {CUSTOMER["출발지"]}</p>
    <p><b>목적지:</b> {CUSTOMER["목적지"]}</p>
    <p><b>예약시간:</b> {DISPATCH["예약시간"]}</p>
    <p><b>차량:</b> {DISPATCH["차량"]} · {DISPATCH["차량번호"]}</p>
    <p><b>기사:</b> {DISPATCH["기사"]}</p>
    <p><b>상담요약:</b> 즉시 배차 불가로 예약 배차를 제안했고 고객이 동의했습니다.</p></div>
    <div class="yellow"><div class="sec">고객 안내 문자</div>[온디멘드 AI콜센터] {CUSTOMER["고객명"]}님, {DISPATCH["예약시간"]} {CUSTOMER["출발지"]} → {CUSTOMER["목적지"]} 이동 예약이 완료되었습니다.<br>차량: {DISPATCH["차량번호"]} / 기사: {DISPATCH["기사"]}</div>''', unsafe_allow_html=True)
    if st.button("📊 관리자 화면 보기"):
        go("admin")
    nav()

def handoff_page():
    header()
    reason = st.session_state.handoff_reason or "상담원 이관"
    urgency = "높음" if "긴급" in reason else "보통"
    st.warning(f"인간 상담원 이관: {reason}")
    st.markdown(f'''<div class="card"><div class="sec">상담원에게 전달되는 정보</div>
    <p><b>고객명:</b> {CUSTOMER["고객명"]}</p>
    <p><b>전화번호:</b> {CUSTOMER["전화번호"]}</p>
    <p><b>고객 발화 원문:</b> “{CUSTOMER["요청"]}”</p>
    <p><b>AI 요약:</b> {CUSTOMER["출발지"]}에서 {CUSTOMER["목적지"]}까지 택시 요청</p>
    <p><b>요청 유형:</b> {CUSTOMER["요청유형"]}</p>
    <p><b>실패/이관 원인:</b> {reason}</p>
    <p><b>긴급도:</b> <span class="red">{urgency}</span></p>
    <p><b>현재 처리 상태:</b> 상담원 처리 대기</p></div>''', unsafe_allow_html=True)
    if st.button("✅ 상담원이 예약 확정"):
        add_log("상담원 처리", "상담원이 예약 확정", reason)
        go("done")
    if st.button("📞 상담원이 재통화 예약"):
        add_log("상담원 처리", "재통화 예약", reason)
        st.success("재통화 예약이 등록되었습니다.")
    if st.button("👨‍👩‍👧 보호자 연락 필요"):
        add_log("상담원 처리", "보호자 연락 필요", reason)
        st.info("보호자 연락 필요 콜로 등록되었습니다.")
    if st.button("🚨 긴급 안내 필요"):
        add_log("상담원 처리", "긴급 안내 필요", reason)
        st.error("긴급 대응 콜로 등록되었습니다.")
    nav()

def admin():
    header()
    logs = st.session_state.logs
    total = max(len(logs), 1)
    ai = sum(1 for x in logs if x["처리상태"] == "AI 단독 처리")
    ho = sum(1 for x in logs if "이관" in x["처리상태"])
    ok = sum(1 for x in logs if "예약" in x["결과"])
    fail = sum(1 for x in logs if "장애" in x["이관사유"] or "실패" in x["이관사유"])
    emer = sum(1 for x in logs if "긴급" in x["이관사유"] or "긴급" in x["결과"])
    _, _, human, premium, _ = cost_data()
    st.markdown('<div class="sec">관리자 대시보드</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("오늘 총 인입 콜", len(logs))
    c1.metric("AI 단독 처리 콜", ai)
    c1.metric("배차 성공 콜", ok)
    c1.metric("AI 단독 처리율", f"{ai / total * 100:.0f}%")
    c2.metric("상담원 이관 콜", ho)
    c2.metric("장애 발생 콜", fail)
    c2.metric("긴급 대응 콜", emer)
    c2.metric("월 예상 절감액", money(human - premium))
    if logs:
        st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
    else:
        st.info("아직 상담 로그가 없습니다. AI 상담 시나리오를 먼저 실행해 주세요.")
    nav()

def failure():
    header()
    st.markdown('<div class="sec">장애 대응 데모</div>', unsafe_allow_html=True)
    name = st.selectbox("장애 유형 선택", list(FAILURES.keys()))
    s = FAILURES[name]
    html = "".join(f"<p><b>{k}:</b><br>{v}</p>" for k, v in s.items())
    st.markdown(f'<div class="card">{html}</div>', unsafe_allow_html=True)
    if st.button("☎️ 이 장애 상황으로 상담원 이관"):
        handoff(name)
    nav()

def cost():
    header()
    base, extra, human, premium, standard = cost_data()
    st.markdown('<div class="sec">운영비 절감 분석</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card"><div class="sec">기본 가정</div><p><b>24시간 365일 운영 최소 인력:</b> 5명</p><p><b>1인당 월 급여:</b> {money(3500000)}</p><p><b>월 기본 인건비:</b> <span class="red">{money(base)}</span></p><p><b>연 기본 인건비:</b> <span class="red">{money(base*12)}</span></p></div>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame([{"항목": k, "월 비용": v} for k, v in extra.items()]), use_container_width=True, hide_index=True)
    df = pd.DataFrame([
        {"운영 구조": "전면 인간 상담", "월 비용": human, "연 비용": human * 12},
        {"운영 구조": "AI 1차 상담 + 인간 예외 대응", "월 비용": premium, "연 비용": premium * 12},
        {"운영 구조": "AI 중심 + 관리자 모니터링", "월 비용": standard, "연 비용": standard * 12},
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.bar_chart(df.set_index("운영 구조")[["월 비용"]])
    saving = human - premium
    st.markdown(f'<div class="yellow"><div class="sec">절감 효과 예시</div>AI 1차 상담 + 인간 예외 대응 구조 적용 시<br>월 약 <span class="red">{money(saving)}</span> 절감 가능<br>추정 절감률은 <span class="red">{saving / human * 100:.1f}%</span>입니다.</div>', unsafe_allow_html=True)
    nav()

init_state()
pages = {
    "main": main,
    "inbound": inbound,
    "analysis": analysis,
    "response": response,
    "done": done,
    "handoff": handoff_page,
    "admin": admin,
    "failure": failure,
    "cost": cost,
}
pages.get(st.session_state.page, main)()
