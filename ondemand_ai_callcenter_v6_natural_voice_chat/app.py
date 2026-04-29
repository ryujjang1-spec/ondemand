# -*- coding: utf-8 -*-
"""
온디멘드 AI콜센터 통합 데모앱 v6 - 동적 분석/GPT 자연어/TTS 개선
- 모빌리티 / 컨시어지 선택형 메인
- 인바운드 접수 / 아웃바운드 확인콜
- STT: requests 직접 호출 방식. 파일 경로 저장 없음.
- TTS: requests 직접 호출 방식. 파일 경로 저장 없음.
- API Key가 없어도 시뮬레이션 발화로 전체 시연 가능
- 고객 1차 요청과 2차 재응답을 분석하여 접수/변경/취소/이관 처리
- 1차: 고객 발화 기반 동적 필드/응답 생성
- 2차: API Key가 있으면 GPT로 자연스러운 상담 문장 생성, 실패 시 룰 기반 응답으로 대체
- 3차: 젊고 밝은 여성 상담원 톤의 TTS 설정

실행:
py -m pip install -r requirements.txt
py -m streamlit run app.py
"""
import re
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="온디멘드 AI콜센터 시나리오_데모앱", page_icon="☎️", layout="wide")

SERVICES = {
    "taxi": {"domain":"mobility","domain_label":"모빌리티 AI콜센터","category":"기본 AI콜센터","title":"택시 배차/예약","icon":"🚕","trust":False,"customer":"홍길순","phone":"010-1234-5678","type":"시니어 고객","inbound":"내수역인데 서당1리 가는 택시 좀 보내줘","outbound":"고객님, 오늘 오후 2시 20분 택시 예약 일정이 있습니다. 예정대로 진행할까요?","fields":{"출발지":"내수역","목적지":"서당1리","즉시 배차":"불가","예상 대기시간":"57분","예약 제안 시간":"오후 2시 20분","차량":"우동택시 / 충북 70 자 1234"},"ai":"고객님, 지금 주변에 바로 갈 수 있는 차량이 없어 예상 대기시간은 57분입니다. 대신 오후 2시 20분 예약 배차로 진행할 수 있습니다. 예약해 드릴까요?","result":"택시 예약 접수 완료"},
    "order": {"domain":"mobility","domain_label":"모빌리티 AI콜센터","category":"기본 AI콜센터","title":"물건 주문/생활 심부름","icon":"🛒","trust":False,"customer":"박영자","phone":"010-2222-7788","type":"생활 심부름 고객","inbound":"생수 두 묶음이랑 휴지 하나 집으로 배달 주문해줘","outbound":"고객님, 오늘 생활물품 배송 접수 건 확인 전화입니다. 생수 두 묶음과 휴지 하나 주문을 진행할까요?","fields":{"주문 품목":"생수 2묶음, 화장지 1개","배송지":"청주시 내수읍 고객 자택","제휴 매장":"내수 생활마트","재고 상태":"확인 완료","배송 예상":"오후 4시 전후","결제 방식":"등록 카드 결제"},"ai":"고객님, 생수 두 묶음과 화장지 한 개 주문 요청으로 확인했습니다. 제휴 매장 재고 확인 후 오후 4시 전후 배송 가능합니다. 이대로 주문 접수할까요?","result":"주문 접수 완료"},
    "schedule": {"domain":"mobility","domain_label":"모빌리티 AI콜센터","category":"기본 AI콜센터","title":"병원/이동 일정 예약","icon":"📅","trust":False,"customer":"김정호","phone":"010-3333-9911","type":"정기 이동 고객","inbound":"다음 주 화요일 오전 9시에 병원 가야 하니까 차 예약해줘","outbound":"고객님, 다음 주 화요일 오전 9시 병원 이동 예약 확인 전화입니다. 예정대로 진행할까요?","fields":{"일정 유형":"병원 이동 예약","예약 일시":"다음 주 화요일 오전 9시","목적지":"청주성모병원","보호자 알림":"필요","리마인드":"전일 오후 6시 / 당일 오전 8시","이동 지원":"왕복 가능"},"ai":"고객님, 다음 주 화요일 오전 9시 병원 이동 예약 요청으로 확인했습니다. 전일과 당일에 리마인드 알림을 보내고, 필요 시 보호자에게도 안내하겠습니다. 예약할까요?","result":"스케줄 예약 완료"},
    "complaint": {"domain":"mobility","domain_label":"모빌리티 AI콜센터","category":"기본 AI콜센터","title":"민원/예외 응대","icon":"⚠️","trust":True,"customer":"이순자","phone":"010-4444-1212","type":"민원 가능 고객","inbound":"기사님이 아직 안 왔어. 왜 이렇게 늦어? 상담원 바꿔줘","outbound":"고객님, 지연 접수 건 확인을 위해 연락드렸습니다. 상담원이 처리 상황을 안내드리겠습니다.","fields":{"민원 유형":"기사 미도착 / 배차 지연","이관 사유":"고객 상담원 요청","긴급도":"보통","상담원 처리":"필요","고객 안내":"사과 후 상담원 연결","사후 기록":"민원 로그 저장"},"ai":"불편을 드려 죄송합니다. 기사 미도착 및 배차 지연 민원으로 확인됩니다. 현재 상황은 상담원이 직접 확인해야 하므로 상담원에게 바로 연결하겠습니다.","result":"상담원 이관"},
    "vehicle_repair": {"domain":"concierge","domain_label":"컨시어지 AI콜센터","category":"Vehicle Care","title":"차량 정비 대행","icon":"🔧","trust":False,"customer":"최민수","phone":"010-5555-1111","type":"차량 케어 고객","inbound":"다음 주 월요일에 차 서비스센터 입고 좀 대신해줘","outbound":"고객님, 내일 오전 9시 차량 정비 입고 대행 일정이 있습니다. 예정대로 차량을 픽업해도 될까요?","fields":{"차량번호":"12가 3456","서비스센터명":"현대 서비스센터 청주점","입고 희망 시간":"다음 주 월요일 오전 9시","픽업 장소":"고객 회사 지하주차장 B2","수리 요청 내용":"엔진오일 교환 및 브레이크 점검","차량 키 위치":"보안 데스크 보관","브리핑 방식":"문자 + 사진 리포트"},"ai":"고객님, 차량 정비 입고 대행 요청으로 확인했습니다. 서비스센터 예약과 차량 픽업 장소를 확인한 뒤 입고부터 출고까지 대행하고, 수리 내역은 문자로 브리핑해 드리겠습니다. 진행할까요?","result":"정비 대행 접수 완료"},
    "carwash_fuel": {"domain":"concierge","domain_label":"컨시어지 AI콜센터","category":"Vehicle Care","title":"세차/주유 대행","icon":"⛽","trust":False,"customer":"정유진","phone":"010-5555-2222","type":"차량 케어 고객","inbound":"내가 회의 중이라 차 좀 가져가서 세차하고 주유해서 다시 갖다줘","outbound":"고객님, 오늘 오후 2시 세차와 주유 대행 일정이 있습니다. 차량 키 위치와 주유 방식을 확인해도 될까요?","fields":{"차량 위치":"회사 주차장 A구역","차량 키 위치":"1층 안내 데스크","세차 방식":"손세차","주유/충전 방식":"휘발유 5만원","주유 금액":"50,000원","반납 위치":"회사 주차장 원위치","완료 사진":"필요"},"ai":"고객님, 업무 중 차량을 가져가 손세차와 주유를 진행한 후 원위치 반납하는 일정으로 확인했습니다. 차량 키 위치와 주유 방식을 확인해도 될까요?","result":"세차/주유 대행 접수 완료"},
    "inspection": {"domain":"concierge","domain_label":"컨시어지 AI콜센터","category":"Vehicle Care","title":"자동차 검사 대행","icon":"🧾","trust":False,"customer":"오세훈","phone":"010-5555-3333","type":"차량 케어 고객","inbound":"자동차 정기검사 기간인데 대신 받아줘","outbound":"고객님, 내일 자동차 정기검사 대행 일정이 있습니다. 오전 10시에 차량을 가져가도 될까요?","fields":{"차량번호":"45나 7788","검사 만료일":"2026년 5월 10일","검사소":"청주 자동차검사소","픽업 시간":"오전 10시","반납 시간":"오후 1시 예상","결과 브리핑":"문자 리포트"},"ai":"고객님, 자동차 정기검사 대행 요청으로 확인했습니다. 검사소 예약 후 차량을 픽업하여 검사 완료 뒤 원위치 반납하고 결과를 문자로 안내드리겠습니다. 진행할까요?","result":"검사 대행 접수 완료"},
    "child_pickup": {"domain":"concierge","domain_label":"컨시어지 AI콜센터","category":"Human & Goods Care","title":"자녀 픽업/통학","icon":"🧒","trust":True,"customer":"이현정","phone":"010-5555-4444","type":"고신뢰 서비스 고객","inbound":"오늘 4시에 아이 학원 끝나는데 집까지 데려다줘","outbound":"고객님, 오늘 오후 4시 자녀 픽업 일정이 있습니다. 아동 케어 교육 이수 기사로 배정되며, 보호자 확인 후 진행됩니다. 예정대로 진행할까요?","fields":{"자녀 이름":"이서준","픽업 장소":"서현 수학학원","도착 장소":"분당 자택","보호자 연락처":"고객 등록 번호","인계 확인 방식":"보호자 통화 + 사진","기사 자격":"아동 케어 교육 이수 기사","위치 공유":"필수","도착 알림":"필수"},"ai":"고객님, 자녀 픽업 서비스는 고신뢰 서비스로 아동 케어 교육 이수 기사만 배정됩니다. 보호자 확인과 실시간 위치 공유 후 진행됩니다. 상담원 확인 후 접수하겠습니다.","result":"고신뢰 확인 대기"},
    "senior_escort": {"domain":"concierge","domain_label":"컨시어지 AI콜센터","category":"Human & Goods Care","title":"시니어 병원 동행","icon":"🏥","trust":True,"customer":"박지훈","phone":"010-5555-5555","type":"고신뢰 서비스 고객","inbound":"내일 아버지 병원 진료가 있는데 모시고 가서 접수까지 도와줘","outbound":"고객님, 내일 오전 10시 부모님 병원 동행 서비스가 예약되어 있습니다. 병원 접수와 대기 지원까지 진행할까요?","fields":{"대상자 성함":"박영수","병원명":"분당서울대병원","진료 시간":"내일 오전 10시","출발지":"정자동 자택","보호자 연락처":"고객 등록 번호","접수 대행":"포함","대기 지원":"포함","귀가 동행":"필요","긴급 연락 기준":"진료 지연/응급상황 발생 시 즉시 보호자 연락"},"ai":"부모님 병원 동행 서비스로 확인했습니다. 병원 접수와 대기 지원까지 포함하여 진행 가능하며, 보호자에게 진행 상황을 안내드리겠습니다. 고신뢰 서비스라 상담원 확인 후 진행합니다.","result":"고신뢰 확인 대기"},
    "goods_delivery": {"domain":"concierge","domain_label":"컨시어지 AI콜센터","category":"Human & Goods Care","title":"물품 픽업/전달","icon":"📦","trust":True,"customer":"강민재","phone":"010-5555-6666","type":"고신뢰 서비스 고객","inbound":"중요한 서류를 거래처에 전달해줘","outbound":"고객님, 오늘 오후 3시 중요 서류 전달 일정이 있습니다. 수령인과 전달 장소를 다시 확인하겠습니다.","fields":{"물품 종류":"중요 계약 서류","픽업 장소":"고객 사무실","전달 장소":"거래처 본사","수령인 이름":"김대리","수령인 연락처":"거래처 등록 번호","완료 인증":"수령 서명 + 사진","사진/서명 확인":"필수"},"ai":"고객님, 중요한 서류 전달 요청으로 확인했습니다. 픽업 장소와 수령인을 재확인하고, 전달 완료 후 사진 또는 서명 인증을 남기겠습니다. 고신뢰 확인 후 진행합니다.","result":"고신뢰 확인 대기"},
}

FAILURES = {
    "STT 장애": "고객 음성이 텍스트로 변환되지 않거나 잡음/사투리/통화품질 저하로 인식 실패. 2회 재질문 후 상담원 이관.",
    "GPT/LLM 장애": "AI 응답 지연, 의도 오분류, 잘못된 답변 가능성 발생. 룰 기반 예비 멘트 후 상담원 이관.",
    "TTS 장애": "AI 음성 출력 실패 또는 지연. 문자 안내와 상담원 연결로 대체.",
    "배차/예약 API 장애": "예약 등록 실패, 차량 조회 실패. 임시 접수번호 발급 후 관리자 확인.",
    "주문/제휴 API 장애": "제휴 매장 연동 실패, 재고 확인 실패. 접수 보류 후 운영자 확인.",
    "고객 DB 장애": "고객 정보, 보호자 정보, 이전 상담 이력 조회 실패. 최소 정보 수기 접수 후 복구 시 재등록.",
    "통신 장애": "전화 끊김, 무응답, 콜백 실패. 자동 콜백 및 문자 안내.",
    "긴급상황": "응급, 사고, 실종, 고령자 혼란 키워드 감지. 즉시 상담원 최우선 이관 및 119/112 안내.",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800;900&display=swap');
:root{--bg:#F5F7FB;--ink:#0F172A;--muted:#667085;--line:#E5E7EB;--brand:#FFD400;--red:#EF4444;--green:#16A34A;--shadow:0 18px 50px rgba(15,23,42,.12);--shadow-sm:0 8px 26px rgba(15,23,42,.08)}
.stApp{background:radial-gradient(circle at 10% 0%,rgba(255,212,0,.22),transparent 28%),radial-gradient(circle at 90% 8%,rgba(37,99,235,.10),transparent 26%),var(--bg)!important;color:var(--ink)!important;font-family:'Noto Sans KR',sans-serif!important}*{font-family:'Noto Sans KR',sans-serif!important}.block-container{max-width:1180px;padding-top:1.2rem;padding-bottom:4rem}header,footer,#MainMenu{visibility:hidden}.hero{background:linear-gradient(135deg,#111827 0%,#1F2937 55%,#2B2408 100%);border-radius:34px;padding:34px;box-shadow:var(--shadow);margin-bottom:18px;position:relative;overflow:hidden}.hero:after{content:'';position:absolute;right:-70px;top:-80px;width:250px;height:250px;border-radius:50%;background:rgba(255,212,0,.22)}.hero *{color:white!important;position:relative;z-index:1}.kicker{display:inline-flex;padding:8px 13px;border-radius:999px;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.16);font-size:14px;font-weight:900}.hero-title{font-size:44px;line-height:1.12;font-weight:900;letter-spacing:-1.3px;margin:10px 0}.hero-sub{font-size:17px;line-height:1.7;color:#D1D5DB!important;max-width:860px}.card,.console{background:rgba(255,255,255,.96)!important;color:var(--ink)!important;border:1px solid rgba(229,231,235,.92);border-radius:26px;padding:24px;margin-bottom:16px;box-shadow:var(--shadow-sm)}.card *,.console *{color:var(--ink)!important}.kpi-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:14px 0 18px}.kpi{background:#fff;border:1px solid var(--line);border-radius:24px;padding:19px;box-shadow:0 8px 24px rgba(15,23,42,.07)}.kpi-label{font-size:13px;font-weight:900;color:var(--muted)!important}.kpi-value{font-size:28px;font-weight:900;letter-spacing:-.6px}.kpi-note{font-size:12px;font-weight:700;color:var(--muted)!important;margin-top:4px}.badge{display:inline-flex;align-items:center;background:#EEF2FF;color:#3730A3!important;border:1px solid #C7D2FE;padding:7px 11px;border-radius:999px;font-size:13px;font-weight:900;margin-right:6px;margin-bottom:8px}.badge-success{background:#ECFDF3;color:#027A48!important;border-color:#ABEFC6}.badge-warning{background:#FFF7ED;color:#C2410C!important;border-color:#FED7AA}.badge-dark{background:#111827;color:white!important;border-color:#111827}.badge-red{background:#FEF2F2;color:#B42318!important;border-color:#FECDCA}.sec{font-size:24px;font-weight:900;letter-spacing:-.5px;margin:8px 0 14px}.subtle{color:var(--muted)!important;font-weight:700;line-height:1.6}.red{color:var(--red)!important;font-weight:900}.phone-card{background:linear-gradient(180deg,#111827 0%,#0B1220 100%)!important;border-radius:34px;padding:26px;min-height:560px;box-shadow:var(--shadow);border:1px solid rgba(255,255,255,.08)}.phone-card *{color:white!important}.phone-top{display:flex;justify-content:space-between;margin-bottom:22px}.phone-status{font-size:14px;color:#9CA3AF!important;font-weight:800}.avatar{width:92px;height:92px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#FFD400,#FFB800);color:#111827!important;font-size:38px;font-weight:900;margin:24px auto 10px;box-shadow:0 12px 30px rgba(255,212,0,.25)}.phone-name{text-align:center;font-size:32px;font-weight:900}.phone-number{text-align:center;color:#D1D5DB!important;font-weight:800}.call-timer{text-align:center;color:#D1D5DB!important;font-weight:800;margin-top:8px}.wave{display:flex;justify-content:center;align-items:end;gap:5px;height:54px;margin:22px 0 10px}.wave span{width:7px;border-radius:999px;background:#FFD400;display:block}.wave span:nth-child(1){height:18px}.wave span:nth-child(2){height:34px}.wave span:nth-child(3){height:22px}.wave span:nth-child(4){height:46px}.wave span:nth-child(5){height:28px}.wave span:nth-child(6){height:39px}.wave span:nth-child(7){height:20px}.wave span:nth-child(8){height:31px}.call-buttons{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:18px}.call-pill{border-radius:18px;padding:13px 8px;text-align:center;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);font-size:13px;font-weight:900}.call-end{background:#EF4444!important}.bubble{font-size:20px;line-height:1.75;font-weight:800;border-radius:24px;padding:22px;margin-bottom:14px;box-shadow:0 10px 28px rgba(15,23,42,.08)}.user{background:#fff!important;border:1px solid #CBD5E1;color:var(--ink)!important}.ai{background:linear-gradient(135deg,#FFF8D6 0%,#FFFFFF 100%)!important;border:2px solid var(--brand);color:var(--ink)!important}.info-row{display:flex;justify-content:space-between;gap:18px;border-bottom:1px dashed #E5E7EB;padding:12px 0;font-size:16px}.info-row:last-child{border-bottom:none}.info-key{color:var(--muted)!important;font-weight:900;min-width:130px}.info-val{font-weight:900;text-align:right}.stButton>button{width:100%;min-height:3.35rem;border-radius:18px;font-size:17px;font-weight:900;background:linear-gradient(135deg,#FFD400 0%,#FFC000 100%)!important;color:#111827!important;border:1px solid rgba(17,24,39,.08)!important;box-shadow:0 8px 18px rgba(255,184,0,.22)}.stButton>button:hover{transform:translateY(-1px);box-shadow:0 12px 26px rgba(255,184,0,.28)}div[data-testid="stMetric"]{background:#fff!important;color:var(--ink)!important;border:1px solid var(--line);border-radius:22px;padding:16px;box-shadow:0 8px 22px rgba(15,23,42,.06)}
@media(max-width:780px){.block-container{padding-left:1rem;padding-right:1rem}.hero{padding:25px;border-radius:26px}.hero-title{font-size:32px}.kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.info-row{flex-direction:column;gap:4px}.info-val{text-align:left}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def init_state():
    st.session_state.setdefault("page", "home")
    st.session_state.setdefault("domain", "")
    st.session_state.setdefault("service_key", "taxi")
    st.session_state.setdefault("call_mode", "inbound")
    st.session_state.setdefault("call_status", "idle")
    st.session_state.setdefault("transcript", "")
    st.session_state.setdefault("ai_response", "")
    st.session_state.setdefault("handoff_reason", "")
    st.session_state.setdefault("logs", [])
    st.session_state.setdefault("audio_key", 0)
    st.session_state.setdefault("tts_audio", None)
    st.session_state.setdefault("dynamic_fields", {})
    st.session_state.setdefault("conversation_step", "awaiting_request")
    st.session_state.setdefault("reply_text", "")
    st.session_state.setdefault("reply_analysis", "")
    st.session_state.setdefault("final_result", "")
    st.session_state.setdefault("conversation_history", [])

def get_service():
    return SERVICES[st.session_state.service_key]


def go(page):
    st.session_state.page = page
    st.rerun()


def set_service(key, mode="inbound"):
    st.session_state.service_key = key
    st.session_state.domain = SERVICES[key]["domain"]
    st.session_state.call_mode = mode
    st.session_state.call_status = "ringing"
    st.session_state.transcript = ""
    st.session_state.reply_text = ""
    st.session_state.reply_analysis = ""
    st.session_state.final_result = ""
    st.session_state.tts_audio = None
    st.session_state.audio_key += 1
    st.session_state.conversation_history = []

    if mode == "outbound":
        # 아웃바운드 확인콜은 AI가 먼저 확인 멘트를 말하고 고객 재응답을 기다리는 구조
        st.session_state.dynamic_fields = dict(SERVICES[key]["fields"])
        st.session_state.ai_response = SERVICES[key]["outbound"]
        st.session_state.conversation_history.append({"role": "assistant", "text": SERVICES[key]["outbound"]})
        st.session_state.conversation_step = "awaiting_confirmation"
    else:
        # 인바운드 접수는 고객의 1차 요청부터 분석
        st.session_state.dynamic_fields = {}
        st.session_state.ai_response = ""
        st.session_state.conversation_step = "awaiting_request"

    st.session_state.page = "phone"
    st.rerun()

def hero(step, title, subtitle):
    st.markdown(f'<div class="hero"><div class="kicker">☎️ {step}</div><div class="hero-title">{title}</div><div class="hero-sub">{subtitle}</div></div>', unsafe_allow_html=True)


def info_row(k, v):
    return f'<div class="info-row"><span class="info-key">{k}</span><span class="info-val">{v}</span></div>'


def clean_api_key(raw_key):
    key = str(raw_key or "").strip()
    match = re.search(r"sk-[A-Za-z0-9_\-]+", key)
    if match:
        return match.group(0)
    key = key.replace("\n", "").replace("\r", "").replace(" ", "")
    key = key.strip().strip('"').strip("'")
    return key


def api_key_value():
    key = st.session_state.get("OPENAI_API_KEY_INPUT", "")
    if key:
        return clean_api_key(key)
    try:
        return clean_api_key(st.secrets.get("OPENAI_API_KEY", ""))
    except Exception:
        return ""

def sidebar():
    with st.sidebar:
        st.markdown("### STT/TTS 설정")
        key = st.text_input("OpenAI API Key", value="", type="password")
        if key:
            st.session_state["OPENAI_API_KEY_INPUT"] = clean_api_key(key)
        st.caption("Secrets 또는 입력칸 중 하나에 API Key가 있으면 STT/TTS가 동작합니다.")
        st.divider()
        st.markdown("### 빠른 이동")
        if st.button("홈"):
            go("home")
        if st.button("서비스 선택"):
            go("select")
        if st.button("관리자 대시보드"):
            go("admin")
        if st.button("장애 대응"):
            go("failure")
        if st.button("비용 분석"):
            go("cost")


def classify_intent(text):
    t = (text or "").lower()
    if any(x in t for x in ["아이", "자녀", "학원", "학교", "통학", "픽업"]): return "child_pickup"
    if any(x in t for x in ["아버지", "어머니", "부모", "병원", "진료", "동행", "접수"]): return "senior_escort"
    if any(x in t for x in ["서류", "선물", "소형", "물품", "전달", "거래처"]): return "goods_delivery"
    if any(x in t for x in ["검사", "정기검사"]): return "inspection"
    if any(x in t for x in ["세차", "주유", "충전"]): return "carwash_fuel"
    if any(x in t for x in ["정비", "서비스센터", "입고", "수리", "출고"]): return "vehicle_repair"
    if any(x in t for x in ["주문", "생수", "휴지", "배달", "장보기"]): return "order"
    if any(x in t for x in ["일정", "스케줄", "예약", "리마인드"]): return "schedule"
    if any(x in t for x in ["늦", "안 왔", "상담원", "불만", "화", "민원"]): return "complaint"
    if any(x in t for x in ["택시", "배차", "내수", "서당", "차 보내"]): return "taxi"
    return st.session_state.service_key



QTY_WORDS = {
    "한": 1, "하나": 1, "한개": 1, "한통": 1, "한묶음": 1,
    "두": 2, "둘": 2, "두개": 2, "두통": 2, "두묶음": 2,
    "세": 3, "셋": 3, "세개": 3, "네": 4, "넷": 4, "네개": 4,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
}
PRODUCTS = ["수박", "생수", "휴지", "화장지", "우유", "쌀", "라면", "커피", "계란", "빵", "과일", "선물", "서류", "약", "반찬", "도시락"]
UNITS = ["개", "통", "묶음", "박스", "병", "봉지", "팩", "장", "개입"]


def extract_order_items(text):
    raw = text or ""
    normalized = raw.replace(",", " ").replace("랑", " ").replace("하고", " ").replace("그리고", " ").replace("및", " ")
    words = normalized.split()
    found = []
    for i, word in enumerate(words):
        product = next((p for p in PRODUCTS if p in word), None)
        if not product:
            continue
        qty = 1
        unit = "개"
        joined = "".join(words[i + 1:i + 4])
        for q_word, q_value in QTY_WORDS.items():
            if q_word in joined:
                qty = q_value
                break
        for u in UNITS:
            if u in joined:
                unit = u
                break
        found.append(f"{product} {qty}{unit}")
    return ", ".join(dict.fromkeys(found)) if found else raw


def extract_route(text):
    text = text or ""
    origin = "고객 위치 확인 필요"
    dest = "목적지 확인 필요"
    if "에서" in text and "까지" in text:
        origin = text.split("에서", 1)[0].strip()[-20:] or origin
        dest = text.split("에서", 1)[1].split("까지", 1)[0].strip() or dest
    elif "인데" in text and "가는" in text:
        origin = text.split("인데", 1)[0].strip() or origin
        dest = text.split("인데", 1)[1].split("가는", 1)[0].strip() or dest
    return origin, dest


def make_rule_based_request_response(service_key, fields, customer_text):
    svc = SERVICES[service_key]

    if service_key == "order":
        items = fields.get("주문 품목", "요청하신 물품")
        return (
            f"고객님, {items} 주문 요청으로 확인했습니다. "
            "가까운 제휴 매장에서 재고와 배송 가능 시간을 확인한 뒤 안내드리겠습니다. "
            "확인되면 등록된 주소로 배송 접수를 진행해 드릴까요?"
        )

    if service_key == "taxi":
        origin = fields.get("출발지", "")
        dest = fields.get("목적지", "")
        if "확인 필요" in origin or "확인 필요" in dest:
            return (
                "고객님, 택시 요청으로 확인했습니다. "
                "출발지와 목적지를 다시 확인한 뒤 바로 배차 가능 여부를 조회하겠습니다. "
                "지금 가능한 차량이 없으면 가장 빠른 예약 시간을 안내드릴게요."
            )
        return (
            f"고객님, {origin}에서 {dest}까지 가는 택시 요청으로 확인했습니다. "
            "먼저 즉시 배차 가능 여부를 확인하겠습니다. "
            "어려울 경우 가장 빠른 예약 배차 시간을 제안드릴게요."
        )

    if service_key == "schedule":
        return (
            "고객님, 일정 예약 요청으로 확인했습니다. "
            "말씀하신 날짜와 시간, 목적지를 기준으로 예약 가능 여부를 확인하겠습니다. "
            "필요하면 보호자 알림도 함께 설정해 드릴까요?"
        )

    if service_key == "complaint":
        return (
            "불편을 드려 죄송합니다. "
            "말씀하신 내용은 상담원이 직접 확인하는 것이 좋겠습니다. "
            "지금까지의 내용을 정리해서 상담원에게 바로 전달하겠습니다."
        )

    if service_key == "vehicle_repair":
        return (
            "고객님, 차량 정비 대행 요청으로 확인했습니다. "
            "서비스센터 예약과 차량 픽업 장소를 확인한 뒤 입고부터 출고까지 대행하겠습니다. "
            "진행해 드릴까요?"
        )

    if service_key == "carwash_fuel":
        return (
            "고객님, 세차와 주유 대행 요청으로 확인했습니다. "
            "차량 위치, 키 위치, 주유 금액을 확인한 뒤 원래 위치로 반납해 드리겠습니다. "
            "이대로 진행해 드릴까요?"
        )

    if service_key == "inspection":
        return (
            "고객님, 자동차 검사 대행 요청으로 확인했습니다. "
            "검사 가능 시간과 차량 픽업 장소를 확인한 뒤 진행하겠습니다. "
            "검사 결과는 문자로 안내드릴게요."
        )

    if service_key == "child_pickup":
        return (
            "고객님, 자녀 픽업 요청으로 확인했습니다. "
            "이 서비스는 보호자 확인과 기사 자격 확인이 필요한 고신뢰 서비스입니다. "
            "상담원이 한 번 더 확인한 뒤 안전하게 배정하겠습니다."
        )

    if service_key == "senior_escort":
        return (
            "고객님, 병원 동행 요청으로 확인했습니다. "
            "접수와 대기 지원까지 포함해 진행할 수 있습니다. "
            "안전 확인이 필요한 서비스라 상담원이 확인 후 배정하겠습니다."
        )

    if service_key == "goods_delivery":
        return (
            "고객님, 물품 전달 요청으로 확인했습니다. "
            "픽업 장소와 수령인 정보를 확인한 뒤 전달 완료 인증까지 남기겠습니다. "
            "진행해 드릴까요?"
        )

    return (
        f"고객님, 말씀하신 내용은 {svc['title']} 요청으로 확인했습니다. "
        "필요한 정보를 확인한 뒤 진행 가능 여부를 안내드리겠습니다."
    )


def append_dialogue(role, text):
    if not text:
        return
    history = st.session_state.setdefault("conversation_history", [])
    history.append({"role": role, "text": str(text).strip()})
    st.session_state.conversation_history = history[-12:]


def dialogue_context():
    history = st.session_state.get("conversation_history", [])[-8:]
    if not history:
        return "이전 대화 없음"
    labels = {"user": "고객", "assistant": "AI상담원"}
    return "\n".join(f"{labels.get(item.get('role'), item.get('role'))}: {item.get('text', '')}" for item in history)


def generate_natural_response_with_gpt(service_key, fields, customer_text, api_key, fallback_text, stage="request"):
    """2차 개선: GPT 자연 대화 응답. API 오류/한도 부족 시 fallback_text를 그대로 사용."""
    api_key = clean_api_key(api_key)
    if not api_key:
        return fallback_text

    svc = SERVICES[service_key]
    history_text = dialogue_context()
    prompt = f"""
너는 온디멘드 AI콜센터의 실제 한국어 전화 상담원이다.
고객과 통화 중이며, 고객에게 바로 읽어줄 말만 작성한다.

핵심 목표:
- 스크립트를 읽는 느낌이 아니라 실제 사람 상담원처럼 자연스럽게 말한다.
- 너무 길게 설명하지 않는다. 보통 2~3문장으로 말한다.
- 한 문장은 35자 안팎으로 짧게 쓴다.
- 내부 필드명, 시스템 용어, 데이터 키 이름을 절대 말하지 않는다.
- '확인 필요에서 확인 필요까지', '고객 위치 확인 필요' 같은 어색한 표현을 절대 사용하지 않는다.
- 모르는 정보는 자연스럽게 다시 묻는다. 예: "출발지는 어디로 보면 될까요?"
- 이미 확인된 내용은 짧게 요약하고, 다음 행동을 묻는다.
- 고객이 동의하면 접수 진행 안내, 변경하면 변경 반영 안내, 취소하면 취소 안내, 상담원 요청이면 이관 안내를 한다.
- 말투는 밝고 친절하되 과장하지 않는다.
- 콜센터 상담원처럼 "네, 고객님"을 적절히 쓰되 매 문장 반복하지 않는다.

상담 단계: {stage}
서비스명: {svc['title']}
고신뢰 여부: {'예' if svc['trust'] else '아니오'}
최근 대화:
{history_text}

이번 고객 발화: {customer_text}
현재 추출 정보: {fields}
기본 응답 초안: {fallback_text}

출력 형식:
- 고객에게 말할 상담원 멘트만 출력
- 불릿, 제목, 따옴표, 설명문 금지
"""
    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "input": prompt,
                "temperature": 0.55,
            },
            timeout=90,
        )
        if response.status_code >= 400:
            return fallback_text
        data = response.json()
        text = data.get("output_text", "")
        if not text:
            chunks = []
            for item in data.get("output", []):
                for content in item.get("content", []):
                    if content.get("type") in ["output_text", "text"]:
                        chunks.append(content.get("text", ""))
            text = "".join(chunks)
        text = (text or "").strip()
        return text or fallback_text
    except Exception:
        return fallback_text

def analyze_customer_request(text, use_gpt=False, api_key=""):
    service_key = classify_intent(text)
    svc = SERVICES[service_key]
    fields = dict(svc["fields"])

    if service_key == "order":
        order_items = extract_order_items(text)
        fields.update({
            "주문 품목": order_items,
            "배송지": "등록된 고객 주소 확인 필요",
            "제휴 매장": "인근 제휴 매장 확인 필요",
            "재고 상태": "확인 필요",
            "배송 예상": "매장 확인 후 안내",
            "결제 방식": "등록 카드 또는 고객 확인 필요",
            "고객 원문": text,
        })
    elif service_key == "taxi":
        origin, dest = extract_route(text)
        fields.update({
            "출발지": origin,
            "목적지": dest,
            "즉시 배차": "확인 필요",
            "예상 대기시간": "조회 필요",
            "예약 제안 시간": "배차 실패 시 제안",
            "고객 원문": text,
        })
    elif service_key == "schedule":
        fields.update({
            "일정 요청": text,
            "예약 일시": "고객 발화 기준 확인 필요",
            "보호자 알림": "필요 여부 확인",
            "리마인드": "전일/당일 알림 가능",
            "고객 원문": text,
        })
    elif service_key == "complaint":
        fields.update({"민원 원문": text, "상담원 처리": "필요", "고객 안내": "사과 후 즉시 확인"})
    else:
        fields.update({"고객 원문": text})

    fallback = make_rule_based_request_response(service_key, fields, text)
    ai_response = generate_natural_response_with_gpt(service_key, fields, text, api_key, fallback, stage="first_request") if use_gpt else fallback
    return service_key, fields, ai_response

def analyze_customer_reply(text, use_gpt=False, api_key=""):
    t = (text or "").lower().strip()
    svc = get_service()
    fields = dict(st.session_state.get("dynamic_fields") or svc["fields"])

    if any(x in t for x in ["상담원", "사람", "직원", "연결"]):
        fallback = "상담원 연결 요청으로 확인했습니다. 지금까지의 상담 내용과 필요한 정보를 정리해서 상담원에게 전달하겠습니다. 잠시만 기다려 주세요."
        ai_response = generate_natural_response_with_gpt(st.session_state.service_key, fields, text, api_key, fallback, stage="handoff_request") if use_gpt else fallback
        return "handoff", "상담원 연결 요청", fields, ai_response, "handoff"

    if any(x in t for x in ["취소", "하지마", "안 할", "안해", "필요 없어", "그만"]):
        fallback = "알겠습니다. 요청 건은 취소로 처리하겠습니다. 필요하시면 언제든 다시 말씀해 주세요."
        ai_response = generate_natural_response_with_gpt(st.session_state.service_key, fields, text, api_key, fallback, stage="cancel") if use_gpt else fallback
        return "cancel", "고객 취소", fields, ai_response, "decision_made"

    if any(x in t for x in ["변경", "바꿔", "말고", "대신", "시간", "주소", "장소", "수량", "추가"]):
        if st.session_state.service_key == "order":
            items = extract_order_items(text)
            if items:
                fields["주문 품목"] = items
        fields["고객 변경 요청"] = text
        fallback = "변경 요청으로 확인했습니다. 수정된 내용을 반영해 다시 확인하겠습니다. 이 내용으로 진행해 드릴까요?"
        ai_response = generate_natural_response_with_gpt(st.session_state.service_key, fields, text, api_key, fallback, stage="change_request") if use_gpt else fallback
        return "change", "고객 변경/추가 요청", fields, ai_response, "awaiting_confirmation"

    if any(x in t for x in ["네", "응", "그래", "좋아", "진행", "해줘", "예약", "접수", "맞아", "확인"]):
        fallback = f"확인했습니다. {svc['title']} 요청을 접수하겠습니다. 진행 상황은 문자나 알림으로 안내드리겠습니다."
        ai_response = generate_natural_response_with_gpt(st.session_state.service_key, fields, text, api_key, fallback, stage="confirmation") if use_gpt else fallback
        return "confirm", "고객 동의", fields, ai_response, "decision_made"

    fields["고객 재응답"] = text
    fallback = "말씀은 확인했습니다. 정확한 처리를 위해 진행, 변경, 취소 중 하나로 다시 말씀해 주시거나 상담원 연결을 요청해 주세요."
    ai_response = generate_natural_response_with_gpt(st.session_state.service_key, fields, text, api_key, fallback, stage="unclear_reply") if use_gpt else fallback
    return "unclear", "재확인 필요", fields, ai_response, "awaiting_confirmation"

def apply_customer_text(text):
    text = (text or "").strip()
    if not text:
        return

    api_key = api_key_value()
    use_gpt = bool(api_key)
    step = st.session_state.get("conversation_step", "awaiting_request")

    append_dialogue("user", text)

    if step == "awaiting_confirmation" and st.session_state.get("ai_response"):
        decision, label, fields, ai_response, next_step = analyze_customer_reply(text, use_gpt=use_gpt, api_key=api_key)
        st.session_state.reply_text = text
        st.session_state.reply_analysis = label
        st.session_state.dynamic_fields = fields
        st.session_state.ai_response = ai_response
        st.session_state.conversation_step = next_step
        st.session_state.final_result = label
    else:
        service_key, fields, ai_response = analyze_customer_request(text, use_gpt=use_gpt, api_key=api_key)
        st.session_state.service_key = service_key
        st.session_state.dynamic_fields = fields
        st.session_state.ai_response = ai_response
        st.session_state.conversation_step = "awaiting_confirmation"
        st.session_state.reply_text = ""
        st.session_state.reply_analysis = ""
        st.session_state.final_result = ""

    append_dialogue("assistant", st.session_state.ai_response)
    st.session_state.transcript = text
    st.session_state.tts_audio = None

def transcribe_audio(audio_file, api_key):
    api_key = clean_api_key(api_key)
    if not api_key:
        return None, "OpenAI API Key가 없습니다. API Key를 넣거나 시뮬레이션 발화를 사용하세요."
    if not api_key.startswith("sk-"):
        return None, "OpenAI API Key 형식이 올바르지 않습니다. sk-로 시작하는 실제 키를 입력하세요."
    try:
        audio_bytes = audio_file.getvalue()
        if not audio_bytes:
            return None, "녹음 파일이 비어 있습니다. 다시 녹음해 주세요."
        response = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            data={"model": "gpt-4o-mini-transcribe", "language": "ko"},
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            timeout=90,
        )
        if response.status_code >= 400:
            return None, f"STT API 오류 {response.status_code}: {response.text}"
        return response.json().get("text", ""), None
    except Exception as e:
        return None, f"STT 처리 오류: {e}"


def text_to_speech(text, api_key):
    api_key = clean_api_key(api_key)
    if not api_key:
        return None, "OpenAI API Key가 없습니다. API Key를 넣거나 시뮬레이션만 사용하세요."
    if not api_key.startswith("sk-"):
        return None, "OpenAI API Key 형식이 올바르지 않습니다. sk-로 시작하는 실제 키를 입력하세요."
    if not text:
        return None, "음성으로 변환할 AI 답변이 없습니다."
    try:
        response = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini-tts",
                "voice": "shimmer",
                "input": text,
                "instructions": (
                    "젊고 밝은 한국인 여성 콜센터 상담원처럼 자연스럽게 말하세요. "
                    "친절하지만 스크립트를 읽는 느낌은 피하고, 실제 통화처럼 부드럽게 이어서 말하세요. "
                    "말끝을 길게 끌지 말고 경쾌하게 마무리하세요. "
                    "문장은 또박또박 읽되 끊어 읽기가 과하지 않게 하세요. "
                    "고객에게 확인하는 문장은 자연스럽게 질문하듯 말하세요."
                ),
                "speed": 1.15,
            },
            timeout=90,
        )
        if response.status_code >= 400:
            return None, f"TTS API 오류 {response.status_code}: {response.text}"
        return response.content, None
    except UnicodeEncodeError:
        return None, "API Key에 한글, 공백, 따옴표, 줄바꿈 등 잘못된 문자가 섞여 있습니다. API Key를 새로 복사해 다시 입력하세요."
    except Exception as e:
        return None, f"TTS 처리 오류: {e}"

def add_log(status, result, reason="-"):
    svc = get_service()
    st.session_state.logs.append({"시간": datetime.now().strftime("%H:%M:%S"), "고객명": svc["customer"], "전화번호": svc["phone"], "도메인": svc["domain_label"], "서비스": svc["title"], "콜 방식": "아웃바운드" if st.session_state.call_mode == "outbound" else "인바운드", "처리 상태": status, "이관 사유": reason, "결과": result})


def handoff(reason):
    st.session_state.handoff_reason = reason
    add_log("상담원 이관", "인간 상담원 처리 대기", reason)
    go("handoff")


def phone_visual():
    svc = get_service()
    mode_label = "아웃바운드 확인콜" if st.session_state.call_mode == "outbound" else "인바운드 접수콜"
    status_label = {"ringing":"통화 연결 대기", "active":"AI 상담 통화 중", "ended":"통화 종료"}.get(st.session_state.call_status, "대기")
    timer = "00:00" if st.session_state.call_status == "ringing" else "00:42" if st.session_state.call_status == "active" else "01:18"
    st.markdown(f'<div class="phone-card"><div class="phone-top"><div class="phone-status">{mode_label}</div><div class="phone-status">{status_label}</div></div><div class="avatar">{svc["icon"]}</div><div class="phone-name">{svc["title"]}</div><div class="phone-number">{svc["phone"]} · {svc["type"]}</div><div class="call-timer">{timer}</div><div class="wave"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div><div class="call-buttons"><div class="call-pill">🎙️ STT</div><div class="call-pill">🤖 AI 상담</div><div class="call-pill">🧑‍💼 이관</div><div class="call-pill">📝 로그</div><div class="call-pill">💬 알림</div><div class="call-pill call-end">종료</div></div></div>', unsafe_allow_html=True)


def service_info_card():
    svc = get_service()
    fields = st.session_state.get("dynamic_fields") or svc["fields"]
    rows = "".join(info_row(k, v) for k, v in fields.items())
    trust = '<span class="badge badge-warning">고신뢰 확인 필요</span>' if svc["trust"] else '<span class="badge badge-success">AI 1차 처리 가능</span>'
    step_label = {
        "awaiting_request": "1차 고객 요청 대기",
        "awaiting_confirmation": "AI 답변 후 고객 재응답 대기",
        "decision_made": "고객 재응답 분석 완료",
        "handoff": "상담원 이관 필요",
    }.get(st.session_state.get("conversation_step", "awaiting_request"), "상담 진행 중")
    extra = info_row("현재 단계", step_label)
    if st.session_state.get("reply_analysis"):
        extra += info_row("재응답 분석", st.session_state.reply_analysis)
    st.markdown(f'<div class="card"><span class="badge badge-dark">{svc["domain_label"]}</span>{trust}<div class="sec">서비스 처리 정보</div>{extra}{rows}</div>', unsafe_allow_html=True)

def render_stt_area():
    svc = get_service()
    api_key = api_key_value()
    step = st.session_state.get("conversation_step", "awaiting_request")
    guide = "고객의 1차 요청을 녹음하세요." if step == "awaiting_request" else "AI 상담원 답변에 대한 고객의 재응답을 녹음하세요. 예: 네 진행해줘 / 시간 바꿔줘 / 취소해줘 / 상담원 연결"
    st.markdown(f'<div class="console"><span class="badge">STT</span><div class="sec">마이크 음성 인식 / 동적 시뮬레이션</div><div class="subtle">{guide}<br>STT 결과를 기준으로 서비스 정보와 AI 답변이 동적으로 갱신됩니다.</div></div>', unsafe_allow_html=True)
    if hasattr(st, "audio_input"):
        audio_value = st.audio_input("고객 음성을 녹음하세요", key=f"audio_input_{st.session_state.audio_key}", sample_rate=16000)
        if audio_value is not None:
            st.audio(audio_value)
            if st.button("🎙️ STT 실행"):
                text, err = transcribe_audio(audio_value, api_key)
                if err:
                    st.error(err)
                elif text and text.strip():
                    apply_customer_text(text.strip())
                    st.session_state.audio_key += 1
                    st.success("STT 분석 완료")
                    st.rerun()
                else:
                    st.warning("음성은 처리됐지만 인식된 문장이 없습니다. 다시 녹음해 주세요.")
    else:
        st.warning("현재 Streamlit 버전에서 st.audio_input을 지원하지 않습니다.")

    st.markdown('<div class="subtle">마이크 없이도 실제 GPT 대화처럼 테스트하려면 아래에 고객 발화를 입력하세요.</div>', unsafe_allow_html=True)
    typed_text = st.text_input(
        "고객 발화 직접 입력",
        value="",
        placeholder="예: 수박 하나랑 생수 한 통 배달 주문해줘 / 네, 그렇게 진행해줘",
        key=f"typed_customer_text_{st.session_state.audio_key}_{step}",
    )
    if st.button("💬 텍스트 발화 분석/전송"):
        if typed_text.strip():
            apply_customer_text(typed_text.strip())
            st.success("텍스트 발화 분석 완료")
            st.rerun()
        else:
            st.warning("분석할 고객 발화를 입력해 주세요.")

    if step == "awaiting_request":
        sample = svc["inbound"]
        label = "🧪 1차 고객 요청 시뮬레이션"
    else:
        sample = "네, 그렇게 진행해줘"
        label = "🧪 고객 재응답 동의 시뮬레이션"

    c1, c2, c3 = st.columns(3)
    if c1.button(label):
        apply_customer_text(sample)
        st.success("시뮬레이션 분석 완료")
        st.rerun()
    if c2.button("🛠️ 변경 요청 시뮬레이션"):
        change_sample = "생수 말고 우유 두 개로 바꿔줘" if st.session_state.service_key == "order" else "시간을 오후 4시로 바꿔줘"
        apply_customer_text(change_sample)
        st.success("변경 요청 분석 완료")
        st.rerun()
    if c3.button("☎️ 상담원 요청 시뮬레이션"):
        apply_customer_text("상담원 연결해줘")
        st.success("상담원 요청 분석 완료")
        st.rerun()

    if st.session_state.transcript:
        st.markdown(f'<div class="bubble user">🎤 고객 발화/STT 결과<br>“{st.session_state.transcript}”</div>', unsafe_allow_html=True)
        if st.session_state.get("reply_text"):
            st.markdown(f'<div class="card"><span class="badge badge-warning">고객 재응답 분석</span><div class="sec">{st.session_state.reply_analysis}</div><div class="subtle">재응답 원문: “{st.session_state.reply_text}”</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card"><span class="badge badge-success">의도 분석</span><div class="sec">{get_service()["icon"]} {get_service()["title"]}</div></div>', unsafe_allow_html=True)

def ai_response_area():
    svc = get_service()
    api_key = api_key_value()
    if not st.session_state.ai_response:
        return
    st.markdown(f'<div class="bubble ai">🤖 AI 상담원<br>{st.session_state.ai_response}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔊 AI 음성 답변 생성/TTS"):
            audio_bytes, err = text_to_speech(st.session_state.ai_response, api_key)
            if err:
                st.error(err)
            else:
                st.session_state.tts_audio = audio_bytes
                st.success("AI 음성 답변 생성 완료")
                st.rerun()
    with c2:
        if st.button("♻️ 새 상담/녹음 준비"):
            st.session_state.audio_key += 1
            st.session_state.transcript = ""
            st.session_state.reply_text = ""
            st.session_state.reply_analysis = ""
            st.session_state.ai_response = ""
            st.session_state.tts_audio = None
            st.session_state.dynamic_fields = {}
            st.session_state.final_result = ""
            st.session_state.conversation_history = []
            st.session_state.conversation_step = "awaiting_request"
            st.rerun()
    if st.session_state.tts_audio:
        st.audio(st.session_state.tts_audio, format="audio/mp3")

    c3, c4, c5 = st.columns(3)
    if c3.button("✅ 접수 확정"):
        if svc["trust"]:
            handoff("고신뢰 서비스 확인 필요")
        else:
            result = st.session_state.get("final_result") or svc["result"]
            add_log("AI 단독 처리", result)
            go("done")
    if c4.button("☎️ 상담원 이관"):
        handoff("고객 또는 AI 판단에 따른 상담원 이관")
    if c5.button("🔚 통화 종료"):
        add_log("통화 종료", "상담 종료")
        st.session_state.call_status = "ended"
        st.rerun()

    if st.session_state.get("conversation_step") == "decision_made":
        st.info("고객 재응답 분석이 완료되었습니다. 접수 확정 또는 통화 종료를 선택하세요.")
    elif st.session_state.get("conversation_step") == "handoff":
        st.warning("고객이 상담원 연결을 요청했습니다. 상담원 이관 버튼을 선택하세요.")

def home():
    hero("On-demand AI Callcenter", "온디멘드 AI콜센터 시나리오_데모앱", "모빌리티 AI콜센터와 컨시어지 AI콜센터를 구분하여 선택하고, 인바운드 접수와 아웃바운드 확인콜을 시연합니다.")
    st.markdown('<div class="kpi-grid"><div class="kpi"><div class="kpi-label">도메인</div><div class="kpi-value">2개</div><div class="kpi-note">모빌리티 / 컨시어지</div></div><div class="kpi"><div class="kpi-label">서비스 시나리오</div><div class="kpi-value">10개</div><div class="kpi-note">기본 + 확장</div></div><div class="kpi"><div class="kpi-label">콜 방식</div><div class="kpi-value">2종</div><div class="kpi-note">인바운드 / 아웃바운드</div></div><div class="kpi"><div class="kpi-label">음성</div><div class="kpi-value">STT/TTS</div><div class="kpi-note">API Key 선택</div></div></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="card"><span class="badge badge-dark">Mobility</span><div class="sec">🚕 모빌리티 AI콜센터</div>택시 배차/예약, 물건 주문, 고객 스케줄링, 민원 응대 업무를 처리합니다.</div>', unsafe_allow_html=True)
        if st.button("🚕 모빌리티 시나리오 선택"):
            st.session_state.domain = "mobility"
            go("select")
    with c2:
        st.markdown('<div class="card"><span class="badge badge-success">Concierge</span><div class="sec">🧑‍💼 컨시어지 AI콜센터</div>Vehicle Care와 Human & Goods Care를 고객 일정에 맞춰 접수하고 확인합니다.</div>', unsafe_allow_html=True)
        if st.button("🧑‍💼 컨시어지 시나리오 선택"):
            st.session_state.domain = "concierge"
            go("select")


def select_page():
    domain = st.session_state.domain or "mobility"
    title = "모빌리티 AI콜센터" if domain == "mobility" else "컨시어지 AI콜센터"
    hero("Service Selection", title, "원하는 서비스 카드를 선택해 인바운드 접수 또는 아웃바운드 확인콜을 시연합니다.")
    keys = [k for k, v in SERVICES.items() if v["domain"] == domain]
    for i in range(0, len(keys), 2):
        cols = st.columns(2)
        for col, key in zip(cols, keys[i:i+2]):
            svc = SERVICES[key]
            with col:
                trust = '<span class="badge badge-warning">고신뢰 확인 필요</span>' if svc["trust"] else '<span class="badge badge-success">AI 1차 처리 가능</span>'
                st.markdown(f'<div class="card"><span class="badge badge-dark">{svc["category"]}</span>{trust}<div class="sec">{svc["icon"]} {svc["title"]}</div><div class="subtle">샘플 요청: “{svc["inbound"]}”</div></div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("인바운드 접수", key=f"in_{key}"):
                    set_service(key, "inbound")
                if c2.button("아웃바운드 확인콜", key=f"out_{key}"):
                    set_service(key, "outbound")


def call_console():
    svc = get_service()
    mode_title = "인바운드 접수콜" if st.session_state.call_mode == "inbound" else "아웃바운드 스케줄 확인콜"
    hero("Call Console", f"{svc['icon']} {svc['title']}", f"{mode_title}, STT 발화 인식, 필수 정보 확인, AI 음성 답변, 상담원 이관을 시연합니다.")
    left, right = st.columns([0.9, 1.2])
    with left:
        phone_visual()
    with right:
        if st.session_state.call_status == "ringing":
            st.markdown(f'<div class="console"><span class="badge badge-success">통화 연결 대기</span><div class="sec">{mode_title}</div>{info_row("고객명", svc["customer"])}{info_row("전화번호", svc["phone"])}{info_row("서비스", svc["title"])}{info_row("고신뢰 여부", "필요" if svc["trust"] else "일반")}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✅ 통화 연결"):
                st.session_state.call_status = "active"
                st.rerun()
            if c2.button("❌ 미연결/거절"):
                add_log("통화 미연결", "콜백 필요")
                st.session_state.call_status = "ended"
                st.rerun()
        elif st.session_state.call_status == "active":
            render_stt_area()
            service_info_card()
            ai_response_area()
        else:
            st.markdown('<div class="console"><span class="badge badge-red">통화 종료</span><div class="sec">통화가 종료되었습니다</div>상담 로그는 관리자 대시보드에 반영됩니다.</div>', unsafe_allow_html=True)


def done():
    svc = get_service()
    hero("Completed", f"{svc['icon']} {svc['title']} 완료", "AI 상담 또는 상담원 확인 결과가 접수 정보와 고객 안내 문자로 정리됩니다.")
    fields = st.session_state.get("dynamic_fields") or svc["fields"]
    rows = "".join(info_row(k, v) for k, v in fields.items())
    final_result = st.session_state.get("final_result") or svc["result"]
    summary = st.session_state.get("reply_analysis") or "고객 동의/접수 확정"
    st.markdown(f'<div class="card"><span class="badge badge-success">처리 완료</span><div class="sec">접수 정보</div>{info_row("고객명", svc["customer"])}{info_row("전화번호", svc["phone"])}{info_row("서비스", svc["title"])}{info_row("최근 고객 발화", st.session_state.get("transcript", ""))}{info_row("고객 재응답 분석", summary)}{rows}{info_row("처리 결과", final_result)}</div><div class="card"><span class="badge">알림톡/문자</span><div class="sec">고객 안내 문구</div>[온디멘드 AI콜센터] {svc["customer"]}님, {svc["title"]} 접수가 완료되었습니다. 진행 상황은 알림톡으로 안내드리겠습니다.</div>', unsafe_allow_html=True)

def handoff_page():
    svc = get_service()
    reason = st.session_state.handoff_reason or "상담원 이관"
    urgency = "높음" if svc["trust"] or "긴급" in reason else "보통"
    hero("Human Handoff", "상담원 이관", "고신뢰 서비스, 장애, 민원, 고객 요청은 상담원에게 요약 정보와 함께 전달됩니다.")
    st.markdown(f'<div class="card"><span class="badge badge-warning">이관 필요</span><span class="badge">긴급도 {urgency}</span><div class="sec">상담원에게 전달되는 정보</div>{info_row("고객명", svc["customer"])}{info_row("전화번호", svc["phone"])}{info_row("서비스 유형", svc["title"])}{info_row("고객 발화 원문", st.session_state.transcript or svc["inbound"])}{info_row("AI 요약", st.session_state.ai_response or svc["ai"])}{info_row("고객 재응답", st.session_state.get("reply_text", ""))}{info_row("재응답 분석", st.session_state.get("reply_analysis", ""))}{info_row("이관 사유", reason)}{info_row("고신뢰 여부", "고신뢰 확인 필요" if svc["trust"] else "일반")}{info_row("긴급도", urgency)}</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    if c1.button("✅ 상담원 접수 확정"):
        add_log("상담원 처리", svc["result"], reason)
        go("done")
    if c2.button("📅 일정 변경"):
        add_log("상담원 처리", "일정 변경 요청", reason)
        st.success("일정 변경 요청으로 등록되었습니다.")
    if c3.button("🚨 긴급 대응"):
        add_log("상담원 처리", "긴급 대응", reason)
        st.error("긴급 대응 콜로 등록되었습니다.")


def failure_page():
    hero("Failure Control", "장애 대응", "STT, LLM, TTS, API, DB, 통신, 긴급상황 등 장애 발생 시 인간 상담원 이관 절차를 확인합니다.")
    name = st.selectbox("장애 유형", list(FAILURES.keys()))
    st.markdown(f'<div class="card"><span class="badge badge-warning">{name}</span><div class="sec">대응 프로세스</div>{FAILURES[name]}<br><br><b>처리:</b> 고객 안내 → 상담 요약 → 상담원 콘솔 표시 → 후속 처리 → 상담 로그 저장</div>', unsafe_allow_html=True)
    if st.button("☎️ 이 장애 상황으로 상담원 이관"):
        handoff(name)


def admin():
    logs = st.session_state.logs
    total = max(len(logs), 1)
    ai_done = sum(1 for x in logs if x["처리 상태"] == "AI 단독 처리")
    hand = sum(1 for x in logs if "이관" in x["처리 상태"])
    hero("Admin Dashboard", "관리자 대시보드", "실시간 콜 현황, 상담원 이관, 고신뢰 서비스, 장애 콜, 비용 절감 효과를 확인합니다.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 콜", len(logs)); c2.metric("AI 단독 처리", ai_done); c3.metric("상담원 이관", hand); c4.metric("AI 처리율", f"{ai_done / total * 100:.0f}%")
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("고신뢰 서비스 콜", "데모"); c6.metric("아웃바운드 확인 완료", sum(1 for x in logs if x["콜 방식"] == "아웃바운드")); c7.metric("장애 발생", sum(1 for x in logs if "장애" in x["이관 사유"])); c8.metric("월 예상 절감", "1,740만원")
    st.markdown('<div class="card"><div class="sec">상담 로그</div></div>', unsafe_allow_html=True)
    if logs:
        st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
    else:
        st.info("아직 상담 로그가 없습니다. 서비스 시나리오를 먼저 실행하세요.")


def cost_page():
    hero("Cost Simulation", "운영비 절감 분석", "24시간 365일 인간 콜센터 운영비와 AI콜센터 도입 후 비용 구조를 비교합니다.")
    base = 5 * 3_500_000
    extra = {"4대보험/퇴직충당": int(base * 0.22), "야간/휴일수당": int(base * 0.18), "교육/품질관리": 1_200_000, "관리자/대체인력": 3_000_000, "장비/통신/공간": 2_500_000}
    human = base + sum(extra.values())
    rows = [
        {"운영 구조": "전면 인간 상담", "월 비용": human, "연 비용": human * 12, "리스크": "인건비 높음"},
        {"운영 구조": "AI 1차 상담 + 인간 예외 대응", "월 비용": 13_500_000, "연 비용": 13_500_000 * 12, "리스크": "초기 구축 필요"},
        {"운영 구조": "AI 중심 + 관리자 모니터링", "월 비용": 9_800_000, "연 비용": 9_800_000 * 12, "리스크": "고신뢰 서비스 확인 필요"},
        {"운영 구조": "고신뢰 서비스 인간 확인 포함", "월 비용": 16_000_000, "연 비용": 16_000_000 * 12, "리스크": "상담원 백업 필수"},
    ]
    st.markdown(f'<div class="kpi-grid"><div class="kpi"><div class="kpi-label">최소 인력</div><div class="kpi-value">5명</div><div class="kpi-note">24시간 365일</div></div><div class="kpi"><div class="kpi-label">1인 월 급여</div><div class="kpi-value">350만</div><div class="kpi-note">기본 급여</div></div><div class="kpi"><div class="kpi-label">월 기본 인건비</div><div class="kpi-value">1,750만</div><div class="kpi-note">수당 제외</div></div><div class="kpi"><div class="kpi-label">월 총 추정</div><div class="kpi-value">{human//10000:,}만</div><div class="kpi-note">추가비 포함</div></div></div>', unsafe_allow_html=True)
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.bar_chart(df.set_index("운영 구조")[["월 비용"]])


def nav_bottom():
    st.divider()
    cols = st.columns(5)
    if cols[0].button("🏠 홈", key="nav_home"): go("home")
    if cols[1].button("🧭 서비스 선택", key="nav_select"): go("select")
    if cols[2].button("📊 관리자", key="nav_admin"): go("admin")
    if cols[3].button("⚠️ 장애", key="nav_fail"): go("failure")
    if cols[4].button("💰 비용", key="nav_cost"): go("cost")


def main():
    init_state()
    sidebar()
    page = st.session_state.page
    if page == "home": home()
    elif page == "select": select_page()
    elif page == "phone": call_console()
    elif page == "done": done()
    elif page == "handoff": handoff_page()
    elif page == "failure": failure_page()
    elif page == "admin": admin()
    elif page == "cost": cost_page()
    else: home()
    nav_bottom()


if __name__ == "__main__":
    main()
