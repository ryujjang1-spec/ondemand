import tempfile
from datetime import datetime
import pandas as pd
import streamlit as st

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

st.set_page_config(page_title="온디멘드 AI콜센터 컨시어지", page_icon="☎️", layout="wide")

SERVICES = {
    "vehicle_repair": {
        "group": "Vehicle Care", "name": "차량 정비 대행", "icon": "🔧", "trust": False,
        "sample": "다음 주 월요일에 차 서비스센터 입고 좀 대신해줘",
        "outbound": "고객님, 내일 오전 9시 차량 정비 입고 대행 일정이 있습니다. 예정대로 차량을 픽업해도 될까요?",
        "ai": "고객님, 차량 정비 입고 대행 요청으로 확인했습니다. 서비스센터 예약과 차량 픽업 장소를 확인한 뒤 입고부터 출고까지 대행하고, 수리 내역은 문자로 브리핑해 드리겠습니다. 진행할까요?",
        "fields": ["차량번호", "서비스센터명", "입고 희망 시간", "픽업 장소", "수리 요청 내용", "차량 키 위치", "수리 내역 브리핑 방식"],
        "prefill": ["12가 3456", "현대 블루핸즈 청주점", "다음 주 월요일 오전 9시", "고객 회사 지하 2층", "엔진오일 및 브레이크 점검", "경비실 보관", "문자 + 사진 브리핑"],
    },
    "carwash_fuel": {
        "group": "Vehicle Care", "name": "세차/주유 대행", "icon": "⛽", "trust": False,
        "sample": "내가 회의 중이라 차 좀 가져가서 세차하고 주유해서 다시 갖다줘",
        "outbound": "고객님, 오늘 오후 2시 세차와 주유 대행 일정이 있습니다. 차량 키 위치와 주유 방식을 확인해도 될까요?",
        "ai": "고객님, 업무 중 차량을 가져가 손세차와 주유를 진행한 후 원위치 반납하는 일정으로 확인했습니다. 차량 키 위치와 주유 방식을 확인해도 될까요?",
        "fields": ["차량 위치", "차량 키 위치", "세차 방식", "주유/충전 방식", "주유 금액", "반납 위치", "완료 사진 보고 여부"],
        "prefill": ["판교 사무실 주차장 B3", "안내데스크 보관", "손세차", "휘발유", "5만 원", "기존 주차 위치", "완료 사진 문자 발송"],
    },
    "inspection": {
        "group": "Vehicle Care", "name": "자동차 검사 대행", "icon": "🧾", "trust": False,
        "sample": "자동차 정기검사 기간인데 대신 받아줘",
        "outbound": "고객님, 내일 자동차 정기검사 대행 일정이 있습니다. 오전 10시에 차량을 가져가도 될까요?",
        "ai": "자동차 정기검사 대행 요청으로 확인했습니다. 차량번호와 검사 만료일, 픽업 시간을 확인한 뒤 검사소 방문부터 결과 브리핑까지 대행하겠습니다. 진행할까요?",
        "fields": ["차량번호", "검사 만료일", "검사소", "픽업 시간", "반납 시간", "검사 결과 브리핑 방식"],
        "prefill": ["34나 7890", "2026-05-15", "성남 자동차검사소", "내일 오전 10시", "오후 1시 전후", "문자 + 사진 브리핑"],
    },
    "child_pickup": {
        "group": "Human & Goods Care", "name": "자녀 픽업/통학", "icon": "🧒", "trust": True,
        "sample": "오늘 4시에 아이 학원 끝나는데 집까지 데려다줘",
        "outbound": "고객님, 오늘 오후 4시 자녀 픽업 일정이 있습니다. 아동 케어 교육 이수 기사로 배정되며, 보호자 확인 후 진행됩니다. 예정대로 진행할까요?",
        "ai": "고객님, 자녀 픽업 서비스는 고신뢰 서비스로 아동 케어 교육 이수 기사만 배정됩니다. 보호자 확인과 위치 공유 후 진행됩니다. 예정대로 진행할까요?",
        "fields": ["자녀 이름", "픽업 장소", "도착 장소", "보호자 연락처", "인계 확인 방식", "기사 자격", "위치 공유 여부", "도착 알림 여부"],
        "prefill": ["김민준", "판교 수학학원", "자택", "010-9999-1111", "보호자 문자 코드 확인", "아동 케어 교육 이수 기사", "실시간 공유", "도착 즉시 알림"],
    },
    "senior_escort": {
        "group": "Human & Goods Care", "name": "시니어 병원 동행", "icon": "🏥", "trust": True,
        "sample": "내일 아버지 병원 진료가 있는데 모시고 가서 접수까지 도와줘",
        "outbound": "고객님, 내일 오전 10시 부모님 병원 동행 서비스가 예약되어 있습니다. 병원 접수와 대기 지원까지 진행할까요?",
        "ai": "부모님 병원 동행 서비스로 확인했습니다. 병원 접수와 대기 지원까지 포함하여 진행 가능하며, 보호자에게 진행 상황을 안내드리겠습니다.",
        "fields": ["대상자 성함", "병원명", "진료 시간", "출발지", "보호자 연락처", "접수 대행 여부", "대기 지원 여부", "귀가 동행 여부", "긴급 연락 기준"],
        "prefill": ["홍길동", "분당서울대병원", "내일 오전 10시", "자택", "010-8888-2222", "포함", "포함", "포함", "상태 이상 시 보호자 즉시 연락"],
    },
    "goods_delivery": {
        "group": "Human & Goods Care", "name": "물품 픽업/전달", "icon": "📦", "trust": True,
        "sample": "중요한 서류를 거래처에 전달해줘",
        "outbound": "고객님, 오늘 오후 3시 중요 서류 전달 일정이 있습니다. 수령인과 전달 장소를 다시 확인하겠습니다.",
        "ai": "중요 물품 전달 요청으로 확인했습니다. 픽업 장소, 전달 장소, 수령인 정보를 확인하고 사진 또는 서명으로 완료 인증을 남기겠습니다. 진행할까요?",
        "fields": ["물품 종류", "픽업 장소", "전달 장소", "수령인 이름", "수령인 연락처", "전달 완료 인증 방식", "사진/서명 확인 여부"],
        "prefill": ["계약 서류 봉투", "고객 사무실", "거래처 접수대", "박대리", "010-7777-3333", "수령인 서명", "사진 + 서명 확인"],
    },
}

FAILURES = {
    "STT 장애": ["고객 음성이 텍스트로 변환되지 않음", "2회 이상 인식 실패", "천천히 다시 말해달라고 안내", "상담원 이관", "STT 실패 콜로 등록"],
    "GPT/LLM 장애": ["AI 응답 지연 또는 의도 오해", "응답 5초 이상 지연", "룰 기반 안내 멘트", "상담원 연결", "LLM 장애 로그 저장"],
    "TTS 장애": ["AI 음성 출력 실패", "음성 끊김/무응답", "문자 안내 병행", "상담원 연결", "TTS 오류 기록"],
    "배차/예약 API 장애": ["예약/배차 시스템 응답 없음", "API 타임아웃", "임시 접수번호 발급", "관리자 확인", "후속 연락 필요 등록"],
    "주문/제휴 API 장애": ["제휴 매장·파트너 연동 실패", "재고/일정 확인 불가", "접수 보류 안내", "운영자 확인", "재연락 필요 등록"],
    "고객 DB 장애": ["고객 이력 조회 실패", "고객 식별 불가", "최소 정보 수기 접수", "상담원 이관", "복구 후 재등록"],
    "통신 장애": ["전화 끊김 또는 콜백 실패", "통화 종료/무응답", "자동 콜백 예약", "상담원 후속 처리", "콜백 로그 저장"],
    "긴급상황": ["사고·응급·고령자 혼란", "긴급 키워드 감지", "즉시 상담원 이관", "119/112 안내", "긴급 콜 최상단 표시"],
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800;900&display=swap');
:root{--bg:#f5f7fb;--ink:#111827;--muted:#667085;--line:#e5e7eb;--brand:#ffd400;--red:#e53935;--green:#16a34a;--shadow:0 18px 50px rgba(15,23,42,.11);--shadow-sm:0 8px 26px rgba(15,23,42,.08)}
.stApp{background:radial-gradient(circle at 10% 0%,rgba(255,212,0,.22),transparent 28%),radial-gradient(circle at 90% 8%,rgba(37,99,235,.10),transparent 26%),var(--bg)!important;color:var(--ink)!important;font-family:'Noto Sans KR',sans-serif!important}*{font-family:'Noto Sans KR',sans-serif!important}.block-container{max-width:1180px;padding-top:1.3rem;padding-bottom:4rem}header,footer,#MainMenu{visibility:hidden}
.hero{background:linear-gradient(135deg,#111827 0%,#1f2937 56%,#2b2408 100%);border-radius:34px;padding:34px;box-shadow:var(--shadow);margin-bottom:18px;position:relative;overflow:hidden}.hero:after{content:'';position:absolute;right:-70px;top:-80px;width:250px;height:250px;border-radius:50%;background:rgba(255,212,0,.22)}.hero *{color:white!important;position:relative;z-index:1}.kicker{display:inline-flex;padding:8px 13px;border-radius:999px;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.16);font-size:14px;font-weight:900}.hero-title{font-size:44px;line-height:1.12;font-weight:900;letter-spacing:-1.3px;margin:10px 0}.hero-sub{font-size:17px;line-height:1.7;color:#d1d5db!important;max-width:860px}
.card{background:rgba(255,255,255,.96)!important;color:var(--ink)!important;border:1px solid rgba(229,231,235,.92);border-radius:26px;padding:24px;margin-bottom:16px;box-shadow:var(--shadow-sm)}.card *{color:var(--ink)!important}.sec{font-size:24px;font-weight:900;letter-spacing:-.5px;margin:8px 0 14px;color:var(--ink)!important}.subtle{color:var(--muted)!important;font-weight:700;line-height:1.6}.badge{display:inline-flex;align-items:center;background:#eef2ff;color:#3730a3!important;border:1px solid #c7d2fe;padding:7px 11px;border-radius:999px;font-size:13px;font-weight:900;margin-right:6px;margin-bottom:8px}.badge-warning{background:#fff7ed;color:#c2410c!important;border-color:#fed7aa}.badge-success{background:#ecfdf3;color:#027a48!important;border-color:#abefc6}.badge-dark{background:#111827;color:white!important;border-color:#111827}.badge-red{background:#fef2f2;color:#b42318!important;border-color:#fecaca}
.kpi-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:14px 0 18px}.kpi{background:#fff;border:1px solid var(--line);border-radius:24px;padding:19px;box-shadow:0 8px 24px rgba(15,23,42,.07)}.kpi-label{font-size:13px;font-weight:900;color:var(--muted)!important;margin-bottom:8px}.kpi-value{font-size:28px;font-weight:900;letter-spacing:-.6px;color:var(--ink)!important}.kpi-note{font-size:12px;font-weight:700;color:var(--muted)!important;margin-top:4px}
.phone-card{background:linear-gradient(180deg,#111827 0%,#0b1220 100%)!important;border-radius:34px;padding:26px;min-height:560px;box-shadow:var(--shadow);border:1px solid rgba(255,255,255,.08)}.phone-card *{color:white!important}.avatar{width:92px;height:92px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#ffd400,#ffb800);color:#111827!important;font-size:38px;font-weight:900;margin:24px auto 10px;box-shadow:0 12px 30px rgba(255,212,0,.25)}.phone-name{font-size:32px;font-weight:900;text-align:center}.phone-number{text-align:center;color:#d1d5db!important;font-size:16px;font-weight:700}.phone-status{display:flex;justify-content:space-between;color:#9ca3af!important;font-size:14px;font-weight:800}.wave{display:flex;justify-content:center;align-items:end;gap:5px;height:54px;margin:22px 0}.wave span{width:7px;border-radius:999px;background:#ffd400;display:block}.wave span:nth-child(1){height:18px}.wave span:nth-child(2){height:34px}.wave span:nth-child(3){height:22px}.wave span:nth-child(4){height:46px}.wave span:nth-child(5){height:28px}.wave span:nth-child(6){height:39px}.wave span:nth-child(7){height:20px}.wave span:nth-child(8){height:31px}.call-pill{border-radius:18px;padding:13px 8px;text-align:center;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);font-size:13px;font-weight:900}.call-buttons{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:18px}
.bubble{font-size:20px;line-height:1.75;font-weight:800;border-radius:24px;padding:22px;margin-bottom:14px;box-shadow:0 10px 28px rgba(15,23,42,.08)}.user{background:#fff!important;border:1px solid #cbd5e1;color:var(--ink)!important}.ai{background:linear-gradient(135deg,#fff8d6 0%,#fff 100%)!important;border:2px solid var(--brand);color:var(--ink)!important}.user *,.ai *{color:var(--ink)!important}.red{color:var(--red)!important;font-size:30px;font-weight:900}.info-row{display:flex;justify-content:space-between;gap:18px;border-bottom:1px dashed #e5e7eb;padding:12px 0;font-size:16px}.info-row:last-child{border-bottom:none}.info-key{color:var(--muted)!important;font-weight:900;min-width:150px}.info-val{color:var(--ink)!important;font-weight:900;text-align:right}.stButton>button{width:100%;min-height:3.35rem;border-radius:18px;font-size:17px;font-weight:900;background:linear-gradient(135deg,#ffd400 0%,#ffc000 100%)!important;color:#111827!important;border:1px solid rgba(17,24,39,.08)!important;box-shadow:0 8px 18px rgba(255,184,0,.22)}div[data-testid="stMetric"]{background:#fff!important;color:var(--ink)!important;border:1px solid var(--line);border-radius:22px;padding:16px;box-shadow:0 8px 22px rgba(15,23,42,.06)}div[data-testid="stMetric"] *{color:var(--ink)!important}[data-testid="stDataFrame"]{border-radius:18px;overflow:hidden;box-shadow:0 10px 24px rgba(15,23,42,.06)}@media(max-width:780px){.kpi-grid{grid-template-columns:repeat(2,1fr)}.info-row{flex-direction:column}.info-val{text-align:left}.hero-title{font-size:32px}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def init_state():
    defaults = {
        "page": "main", "service": "vehicle_repair", "call_mode": "inbound", "call_status": "idle",
        "transcript": "", "ai_response": "", "handoff_reason": "", "logs": [], "last_outcome": ""
    }
    for k, v in defaults.items(): st.session_state.setdefault(k, v)

def secret_key():
    try: return st.secrets.get("OPENAI_API_KEY", "")
    except Exception: return ""

def go(page): st.session_state.page = page; st.rerun()
def active(): return SERVICES[st.session_state.service]
def money(n): return f"{int(n):,}원"
def info_row(k, v): return f'<div class="info-row"><span class="info-key">{k}</span><span class="info-val">{v}</span></div>'
def hero(step, title, subtitle):
    st.markdown(f'<div class="hero"><div class="kicker">☎️ {step}</div><div class="hero-title">{title}</div><div class="hero-sub">{subtitle}</div></div>', unsafe_allow_html=True)

def nav():
    c1,c2,c3,c4,c5=st.columns(5)
    if c1.button("🏠 홈"): go("main")
    if c2.button("☎️ 콜 콘솔"): go("phone")
    if c3.button("⚠️ 장애"): go("failure")
    if c4.button("📊 관리자"): go("admin")
    if c5.button("💰 비용"): go("cost")

def add_log(status, result, reason="-"):
    svc=active()
    st.session_state.logs.append({"시간":datetime.now().strftime("%H:%M:%S"),"서비스":svc["name"],"구분":st.session_state.call_mode,"처리상태":status,"이관사유":reason,"결과":result,"고신뢰":"Y" if svc["trust"] else "N"})

def handoff(reason):
    st.session_state.handoff_reason=reason; add_log("상담원 이관","상담원 처리 대기",reason); go("handoff")

def cost_data():
    base=5*3_500_000
    extra={"4대보험/퇴직충당":int(base*.22),"야간/휴일수당":int(base*.18),"교육/품질관리":1_200_000,"관리자/대체인력":3_000_000,"장비/통신/공간":2_500_000}
    human=base+sum(extra.values())
    return base, extra, human, 15_500_000, 10_800_000

def classify(text):
    t=(text or "").lower()
    if any(k in t for k in ["학원","아이","자녀","통학","학교"]): return "child_pickup"
    if any(k in t for k in ["아버지","어머니","부모","병원","진료","동행"]): return "senior_escort"
    if any(k in t for k in ["서류","물품","선물","전달","거래처"]): return "goods_delivery"
    if any(k in t for k in ["세차","주유","충전"]): return "carwash_fuel"
    if any(k in t for k in ["검사","정기검사"]): return "inspection"
    if any(k in t for k in ["정비","서비스센터","입고","수리"]): return "vehicle_repair"
    return st.session_state.service

def transcribe(audio, api_key):
    if OpenAI is None: return None, "openai 패키지가 설치되지 않았습니다."
    if not api_key: return None, "OpenAI API Key가 없습니다. 사이드바 또는 secrets.toml에 입력하세요."
    try:
        client=OpenAI(api_key=api_key)
        with tempfile.NamedTemporaryFile(delete=False,suffix=".wav") as tmp:
            tmp.write(audio.getvalue()); path=tmp.name
        with open(path,"rb") as f:
            res=client.audio.transcriptions.create(model="gpt-4o-mini-transcribe",file=f,language="ko")
        return res.text, None
    except Exception as e: return None, str(e)

def render_phone(status):
    svc=active(); label="AI 아웃바운드 확인콜" if st.session_state.call_mode=="outbound" else "고객 인바운드 접수콜"
    st.markdown(f'<div class="phone-card"><div class="phone-status"><span>{label}</span><span>{status}</span></div><div class="avatar">{svc["icon"]}</div><div class="phone-name">{svc["name"]}</div><div class="phone-number">010-1234-5678 · {svc["group"]}</div><div class="wave"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div><div class="call-buttons"><div class="call-pill">🎙️ STT</div><div class="call-pill">🤖 AI</div><div class="call-pill">🧑‍💼 이관</div><div class="call-pill">📍 위치</div><div class="call-pill">✅ 인증</div><div class="call-pill">🔚 종료</div></div></div>', unsafe_allow_html=True)

def render_service_card(key, svc):
    trust='<span class="badge badge-warning">고신뢰 확인 필요</span>' if svc["trust"] else '<span class="badge badge-success">AI 1차 처리 가능</span>'
    st.markdown(f'<div class="card"><span class="badge badge-dark">{svc["group"]}</span>{trust}<div class="sec">{svc["icon"]} {svc["name"]}</div><div class="subtle">샘플 요청: “{svc["sample"]}”</div></div>', unsafe_allow_html=True)
    c1,c2=st.columns(2)
    if c1.button("인바운드 접수", key=f"in_{key}"):
        st.session_state.service=key; st.session_state.call_mode="inbound"; st.session_state.call_status="ringing"; st.session_state.transcript=""; st.session_state.ai_response=""; go("phone")
    if c2.button("아웃바운드 확인콜", key=f"out_{key}"):
        st.session_state.service=key; st.session_state.call_mode="outbound"; st.session_state.call_status="ringing"; st.session_state.transcript=""; st.session_state.ai_response=""; go("phone")

def main():
    hero("On-demand Concierge", "온디멘드 AI콜센터 컨시어지", "차량 케어와 라이프 케어를 전화 기반 AI 상담, STT, 아웃바운드 확인콜, 상담원 이관으로 시연합니다.")
    st.markdown('<div class="kpi-grid"><div class="kpi"><div class="kpi-label">서비스</div><div class="kpi-value">6종</div><div class="kpi-note">Vehicle + Life Care</div></div><div class="kpi"><div class="kpi-label">콜 방식</div><div class="kpi-value">2종</div><div class="kpi-note">인바운드/아웃바운드</div></div><div class="kpi"><div class="kpi-label">STT</div><div class="kpi-value">지원</div><div class="kpi-note">마이크/시뮬레이션</div></div><div class="kpi"><div class="kpi-label">고신뢰</div><div class="kpi-value">3종</div><div class="kpi-note">보호자/기사 검증</div></div></div>', unsafe_allow_html=True)
    for i in range(0, len(SERVICES), 2):
        cols=st.columns(2)
        for col,(key,svc) in zip(cols, list(SERVICES.items())[i:i+2]):
            with col: render_service_card(key,svc)

def phone():
    svc=active(); mode=st.session_state.call_mode; status=st.session_state.call_status
    hero("Call Console", f"{svc['icon']} {svc['name']}", "통화 연결, STT 발화 인식, 필수 정보 확인, 아웃바운드 일정 확인, 상담원 이관을 시연합니다.")
    left,right=st.columns([.85,1.15])
    with left: render_phone("수신 대기" if status=="ringing" else "통화 중" if status=="active" else "통화 종료")
    with right:
        if status=="ringing":
            call_text=svc["outbound"] if mode=="outbound" else f"고객 요청 예상: {svc['sample']}"
            st.markdown(f'<div class="card"><span class="badge badge-success">{mode}</span><div class="sec">콜 이벤트</div>{info_row("서비스",svc["name"])}{info_row("통화 목적",call_text)}{info_row("고신뢰", "필요" if svc["trust"] else "일반")}</div>', unsafe_allow_html=True)
            c1,c2=st.columns(2)
            if c1.button("✅ 통화 연결"):
                st.session_state.call_status="active"; go("phone")
            if c2.button("📵 부재중/거절"):
                add_log("미연결","콜백 필요"); st.session_state.call_status="ended"; go("phone")
        elif status=="active":
            if mode=="outbound":
                st.markdown(f'<div class="bubble ai">🤖 AI 아웃바운드콜<br>{svc["outbound"]}</div>', unsafe_allow_html=True)
            render_stt()
            if st.session_state.ai_response:
                st.markdown(f'<div class="bubble ai">🤖 AI 상담원<br>{st.session_state.ai_response}</div>', unsafe_allow_html=True)
                render_fields()
                render_actions()
        else:
            st.markdown('<div class="card"><span class="badge badge-red">통화 종료</span><div class="sec">통화가 종료되었습니다</div>결과는 관리자 로그에 반영됩니다.</div>', unsafe_allow_html=True)
    nav()

def render_stt():
    svc=active(); key=secret_key()
    with st.sidebar:
        st.markdown("### STT 설정")
        input_key=st.text_input("OpenAI API Key", type="password")
        if input_key: key=input_key
    if hasattr(st,"audio_input"):
        audio=st.audio_input("고객 음성 녹음")
        if audio is not None:
            st.audio(audio)
            if st.button("🎙️ STT 실행"):
                txt,err=transcribe(audio,key)
                if err: st.error(err)
                else:
                    st.session_state.transcript=txt; st.session_state.service=classify(txt); st.session_state.ai_response=active()["ai"]; st.rerun()
    st.markdown('<div class="card"><div class="sec">시뮬레이션 발화</div><div class="subtle">API Key 없이도 모든 서비스 시나리오를 테스트할 수 있습니다.</div></div>', unsafe_allow_html=True)
    sample_choice=st.selectbox("시나리오 발화 선택", list(SERVICES.keys()), format_func=lambda x: SERVICES[x]["name"])
    if st.button("🧪 선택 발화로 진행"):
        st.session_state.service=sample_choice; st.session_state.transcript=SERVICES[sample_choice]["sample"]; st.session_state.ai_response=SERVICES[sample_choice]["ai"]; st.rerun()
    if st.session_state.transcript:
        st.markdown(f'<div class="bubble user">🎤 고객 발화/STT 결과<br>“{st.session_state.transcript}”</div>', unsafe_allow_html=True)

def render_fields():
    svc=active(); rows=""
    for f,v in zip(svc["fields"],svc["prefill"]): rows += info_row(f,v)
    badge='<span class="badge badge-warning">고신뢰 확인 필요</span>' if svc["trust"] else '<span class="badge badge-success">필수 정보 확인</span>'
    st.markdown(f'<div class="card">{badge}<div class="sec">필수 정보 추출</div>{rows}</div>', unsafe_allow_html=True)
    if svc["trust"]:
        st.markdown('<div class="card"><span class="badge badge-warning">안전 로직</span><div class="sec">고신뢰 서비스 검증</div>'+info_row("상담원 확인","필수")+info_row("기사 자격 검증","필수")+info_row("위치 공유 동의","필수")+info_row("완료 인증","사진/서명/보호자 확인")+'</div>', unsafe_allow_html=True)

def render_actions():
    svc=active(); mode=st.session_state.call_mode
    c1,c2,c3=st.columns(3)
    if c1.button("✅ 진행 확정"):
        result="아웃바운드 진행 확정" if mode=="outbound" else "접수 확정"
        add_log("AI 단독 처리" if not svc["trust"] else "고신뢰 확인 대기", result)
        if svc["trust"]: handoff("고신뢰 서비스 확인 필요")
        else: go("done")
    if c2.button("📅 일정 변경 요청"):
        add_log("일정 변경 요청","상담원 확인 필요","일정 변경"); handoff("일정 변경 요청")
    if c3.button("❌ 취소 요청"):
        add_log("취소 요청","취소 처리 필요","취소 요청"); handoff("취소 요청")
    c4,c5=st.columns(2)
    if c4.button("🧑‍💼 상담원 이관"):
        handoff("고객/서비스 특성상 상담원 확인")
    if c5.button("🔚 통화 종료"):
        add_log("통화 종료","상담 종료"); st.session_state.call_status="ended"; go("phone")

def done():
    svc=active(); rows="".join(info_row(f,v) for f,v in zip(svc["fields"],svc["prefill"]))
    hero("Completed", f"{svc['icon']} {svc['name']} 접수 완료", "AI 상담 결과가 접수 정보와 고객 알림 문구로 정리됩니다.")
    st.markdown(f'<div class="card"><span class="badge badge-success">처리 완료</span><div class="sec">접수 정보</div>{rows}</div><div class="card"><span class="badge">알림톡/문자</span><div class="sec">고객 안내</div>[온디멘드] {svc["name"]} 요청이 접수되었습니다. 진행 상황은 문자로 안내드립니다.</div>', unsafe_allow_html=True)
    nav()

def handoff_page():
    svc=active(); reason=st.session_state.handoff_reason or "상담원 이관"; urgency="높음" if svc["trust"] or "긴급" in reason else "보통"
    rows=info_row("서비스",svc["name"])+info_row("고객 발화",st.session_state.transcript or svc["sample"])+info_row("AI 요약",st.session_state.ai_response or svc["ai"])+info_row("필수 정보 상태","확인 필요")+info_row("이관 사유",reason)+info_row("긴급도",f'<span class="red">{urgency}</span>')+info_row("고신뢰 여부","Y" if svc["trust"] else "N")
    hero("Human Handoff", "상담원 이관", "고신뢰 서비스, 일정 변경, 취소, 장애, 민원은 상담원이 이어받습니다.")
    st.markdown(f'<div class="card"><span class="badge badge-warning">상담원 처리 필요</span><div class="sec">상담원 화면</div>{rows}</div>', unsafe_allow_html=True)
    c1,c2,c3=st.columns(3)
    if c1.button("✅ 접수 확정"):
        add_log("상담원 처리","접수 확정",reason); go("done")
    if c2.button("📅 일정 변경"):
        add_log("상담원 처리","일정 변경",reason); st.success("일정 변경 처리됨")
    if c3.button("❌ 취소 처리"):
        add_log("상담원 처리","취소 처리",reason); st.warning("취소 처리됨")
    c4,c5,c6=st.columns(3)
    if c4.button("👨‍👩‍👧 보호자 연락"):
        add_log("상담원 처리","보호자 연락",reason); st.info("보호자 연락 등록")
    if c5.button("🚕 기사 재배정"):
        add_log("상담원 처리","기사 재배정",reason); st.info("기사 재배정 요청")
    if c6.button("🚨 긴급 대응"):
        add_log("상담원 처리","긴급 대응",reason); st.error("긴급 대응 등록")
    nav()

def failure():
    hero("Failure Control", "장애 대응", "STT, LLM, TTS, API, DB, 통신, 긴급상황을 상담원 이관으로 처리합니다.")
    name=st.selectbox("장애 유형", list(FAILURES.keys()))
    labels=["장애 상황","감지 기준","AI 1차 대응","상담원 이관 기준","사후 기록"]
    rows="".join(info_row(k,v) for k,v in zip(labels,FAILURES[name]))
    st.markdown(f'<div class="card"><span class="badge badge-warning">{name}</span><div class="sec">장애 대응 프로세스</div>{rows}</div>', unsafe_allow_html=True)
    if st.button("☎️ 이 장애 상황으로 상담원 이관"): handoff(name)
    nav()

def admin():
    logs=st.session_state.logs; total=max(len(logs),1); ai=sum(1 for x in logs if "AI" in x["처리상태"]); ho=sum(1 for x in logs if "이관" in x["처리상태"] or "상담원" in x["처리상태"]); trust=sum(1 for x in logs if x.get("고신뢰")=="Y"); outbound=sum(1 for x in logs if x.get("구분")=="outbound"); changes=sum(1 for x in logs if "변경" in x.get("결과","") or "변경" in x.get("이관사유","") ); cancels=sum(1 for x in logs if "취소" in x.get("결과","") or "취소" in x.get("이관사유","") ); base,extra,human,premium,standard=cost_data()
    hero("Admin Dashboard", "관리자 대시보드", "콜 현황, 고신뢰 이관, 일정 변경, 취소, 장애, 비용 절감액을 확인합니다.")
    cols=st.columns(4); vals=[("총 콜",len(logs)),("AI 처리",ai),("상담원 이관",ho),("고신뢰 콜",trust)]
    for col,(k,v) in zip(cols,vals): col.metric(k,v)
    cols2=st.columns(4); vals2=[("아웃바운드",outbound),("일정 변경",changes),("취소 요청",cancels),("월 절감액",money(human-premium))]
    for col,(k,v) in zip(cols2,vals2): col.metric(k,v)
    if logs: st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
    else: st.info("아직 상담 로그가 없습니다.")
    nav()

def cost():
    base,extra,human,premium,standard=cost_data(); hero("Cost Simulation", "운영비 절감 분석", "24시간 365일 인간 콜센터와 AI+인간 백업 운영 구조를 비교합니다.")
    st.markdown(f'<div class="kpi-grid"><div class="kpi"><div class="kpi-label">최소 인력</div><div class="kpi-value">5명</div><div class="kpi-note">24/365</div></div><div class="kpi"><div class="kpi-label">1인 월급</div><div class="kpi-value">350만</div><div class="kpi-note">기본급</div></div><div class="kpi"><div class="kpi-label">월 기본</div><div class="kpi-value">1,750만</div><div class="kpi-note">수당 제외</div></div><div class="kpi"><div class="kpi-label">연 기본</div><div class="kpi-value">2.1억</div><div class="kpi-note">수당 제외</div></div></div>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame([{"항목":k,"월 비용":v} for k,v in extra.items()]), use_container_width=True, hide_index=True)
    df=pd.DataFrame([{"운영 구조":"전면 인간 상담","월 비용":human,"연 비용":human*12},{"운영 구조":"AI 1차 상담 + 인간 예외 대응","월 비용":premium,"연 비용":premium*12},{"운영 구조":"AI 중심 + 관리자 모니터링","월 비용":standard,"연 비용":standard*12},{"운영 구조":"고신뢰 서비스 인간 확인 포함","월 비용":int(premium*1.15),"연 비용":int(premium*1.15)*12}])
    st.dataframe(df, use_container_width=True, hide_index=True); st.bar_chart(df.set_index("운영 구조")[["월 비용"]])
    nav()

init_state()
pages={"main":main,"phone":phone,"done":done,"handoff":handoff_page,"failure":failure,"admin":admin,"cost":cost}
pages.get(st.session_state.page,main)()
