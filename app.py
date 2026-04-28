
import tempfile
from datetime import datetime

import pandas as pd
import streamlit as st

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


st.set_page_config(
    page_title="온디멘드 AI콜센터 시나리오_데모앱",
    page_icon="☎️",
    layout="wide",
)


SERVICES = {
    # -----------------------------
    # 1. 기존 모빌리티 AI콜센터
    # -----------------------------
    "taxi_dispatch": {
        "domain": "mobility",
        "domain_label": "모빌리티 AI콜센터",
        "title": "택시 배차/예약",
        "icon": "🚕",
        "type": "Mobility",
        "trust": False,
        "customer": "아이나비 모빌리티",
        "phone": "010-1234-5678",
        "customer_type": "시니어 고객",
        "inbound_utterance": "판교역 1번출구 인데 성남시청 가는 택시 좀 보내줘",
        "outbound_message": "고객님, 오후 2시 20분 내수역에서 서당1리 이동 예약이 있습니다. 예정대로 진행할까요?",
        "ai_response": "어르신, 지금 주변에 바로 갈 수 있는 빈 차가 없어서 57분 정도 기다리셔야 해요. 대신 오후 2시 20분에 맞춰 도착하는 택시를 미리 예약해 드릴까요?",
        "required": {
            "출발지": "판교역 1번출구",
            "목적지": "성남시청",
            "즉시 배차": "불가",
            "예상 대기시간": "30분",
            "예약 제안 시간": "오후 2시 20분",
            "차량": "우리택시 / 성남 70 자 1234",
            "기사": "김총알 기사님",
        },
        "complete_result": "택시 예약 완료",
        "sms": "[온디멘드 AI콜센터] 오후 2시 20분 판교역 → 성남시청 이동 예약이 완료되었습니다. 차량: 성남 70 자 1234 / 기사: 김총알 기사님",
        "handoff_default": "고객 상담원 요청 또는 배차 실패 반복",
    },
    "goods_order": {
        "domain": "mobility",
        "domain_label": "모빌리티 AI콜센터",
        "title": "물건 주문/생활 심부름",
        "icon": "🛒",
        "type": "Order",
        "trust": False,
        "customer": "박영자",
        "phone": "010-2222-7788",
        "customer_type": "생활 심부름 고객",
        "inbound_utterance": "생수 두 묶음이랑 휴지 하나 집으로 배달 주문해줘",
        "outbound_message": "고객님, 생수 2묶음과 화장지 1개 주문이 접수되어 있습니다. 예정대로 매장에 전달할까요?",
        "ai_response": "고객님, 생수 2묶음과 화장지 1개 주문으로 확인했습니다. 내수 생활마트에 재고 확인 후 배송 예상 시간을 안내드리겠습니다. 이대로 주문 접수할까요?",
        "required": {
            "주문 품목": "생수 2묶음, 화장지 1개",
            "수량": "생수 2 / 화장지 1",
            "배송지": "충북 청주시 청원구 내수읍 고객 자택",
            "제휴 매장": "내수 생활마트",
            "재고 상태": "확인 필요",
            "결제 방식": "고객 등록 결제수단",
            "배송 예상": "오후 4시 전후",
        },
        "complete_result": "주문 접수 완료",
        "sms": "[온디멘드 AI콜센터] 생수 2묶음, 화장지 1개 주문이 접수되었습니다. 재고 확인 후 배송 시간을 안내드리겠습니다.",
        "handoff_default": "재고 없음 또는 제휴 매장 연동 실패",
    },
    "customer_schedule": {
        "domain": "mobility",
        "domain_label": "모빌리티 AI콜센터",
        "title": "고객 스케줄링",
        "icon": "📅",
        "type": "Schedule",
        "trust": False,
        "customer": "김정호",
        "phone": "010-3333-9911",
        "customer_type": "정기 이동 고객",
        "inbound_utterance": "다음 주 화요일 오전 9시에 병원 가야 하니까 차 예약해줘",
        "outbound_message": "고객님, 다음 주 화요일 오전 9시 병원 이동 예약이 있습니다. 예정대로 진행할까요?",
        "ai_response": "고객님, 다음 주 화요일 오전 9시 병원 이동 일정으로 확인했습니다. 이동 예약과 전일 리마인드, 당일 알림까지 등록해 드릴까요?",
        "required": {
            "일정 유형": "병원 이동 예약",
            "예약 일시": "다음 주 화요일 오전 9시",
            "출발지": "고객 자택",
            "도착지": "청주성모병원",
            "보호자 알림": "선택",
            "리마인드": "전일 오후 6시 / 당일 오전 8시",
        },
        "complete_result": "스케줄 예약 완료",
        "sms": "[온디멘드 AI콜센터] 다음 주 화요일 오전 9시 병원 이동 일정이 등록되었습니다. 전일 및 당일 리마인드를 보내드리겠습니다.",
        "handoff_default": "예약 시간 변경 또는 보호자 알림 필요",
    },
    "mobility_complaint": {
        "domain": "mobility",
        "domain_label": "모빌리티 AI콜센터",
        "title": "민원 및 예외 응대",
        "icon": "⚠️",
        "type": "Exception",
        "trust": True,
        "customer": "이순자",
        "phone": "010-4444-1212",
        "customer_type": "민원 가능 고객",
        "inbound_utterance": "기사님이 아직 안 왔어. 왜 이렇게 늦어? 상담원 바꿔줘",
        "outbound_message": "고객님, 접수된 배차 지연 건에 대해 상담원이 확인 중입니다. 현재 통화 가능하신가요?",
        "ai_response": "불편을 드려 죄송합니다. 기사 미도착 및 배차 지연 건으로 확인됩니다. 이 건은 상담원이 바로 확인해야 하므로 상담원에게 연결해 드리겠습니다.",
        "required": {
            "민원 유형": "기사 미도착 / 배차 지연",
            "예약 번호": "M-2026-0428-001",
            "기존 예약 시간": "오후 2시",
            "현재 상태": "기사 위치 확인 필요",
            "고객 감정": "불만 / 상담원 요청",
            "우선순위": "높음",
        },
        "complete_result": "민원 상담원 이관",
        "sms": "[온디멘드 AI콜센터] 배차 지연 건이 접수되었습니다. 상담원이 확인 후 연락드리겠습니다.",
        "handoff_default": "고객 불만 및 상담원 요청",
    },

    # -----------------------------
    # 2. 컨시어지 확장
    # -----------------------------
    "vehicle_repair": {
        "domain": "concierge",
        "domain_label": "컨시어지 AI콜센터",
        "title": "차량 정비 대행",
        "icon": "🔧",
        "type": "Vehicle Care",
        "trust": False,
        "customer": "정민수",
        "phone": "010-5555-1200",
        "customer_type": "차량 케어 고객",
        "inbound_utterance": "다음 주 월요일에 차 서비스센터 입고 좀 대신해줘",
        "outbound_message": "고객님, 내일 오전 9시 차량 정비 입고 대행 일정이 있습니다. 예정대로 차량을 픽업해도 될까요?",
        "ai_response": "고객님, 다음 주 월요일 차량 정비 입고 대행 요청으로 확인했습니다. 서비스센터 예약과 차량 픽업 장소를 확인한 뒤 입고부터 출고까지 대행하고, 수리 내역은 문자로 브리핑해 드리겠습니다. 진행할까요?",
        "required": {
            "차량번호": "12가 3456",
            "서비스센터명": "아이나비 제휴 서비스센터",
            "입고 희망 시간": "다음 주 월요일 오전 9시",
            "픽업 장소": "고객 회사 지하주차장 B2",
            "수리 요청 내용": "엔진오일 교환 및 소음 점검",
            "차량 키 위치": "안내데스크 보관",
            "브리핑 방식": "문자 + 사진 리포트",
        },
        "complete_result": "정비 대행 접수 완료",
        "sms": "[온디멘드 컨시어지] 차량 정비 입고 대행이 접수되었습니다. 픽업 전 확인콜을 드리겠습니다.",
        "handoff_default": "서비스센터 예약 불가 또는 고객 추가 요청",
    },
    "carwash_fuel": {
        "domain": "concierge",
        "domain_label": "컨시어지 AI콜센터",
        "title": "세차/주유 대행",
        "icon": "⛽",
        "type": "Vehicle Care",
        "trust": False,
        "customer": "오지훈",
        "phone": "010-6666-3300",
        "customer_type": "차량 케어 고객",
        "inbound_utterance": "내가 회의 중이라 차 좀 가져가서 세차하고 주유해서 다시 갖다줘",
        "outbound_message": "고객님, 오늘 오후 2시 세차와 주유 대행 일정이 있습니다. 차량 키 위치와 주유 방식을 확인해도 될까요?",
        "ai_response": "고객님, 업무 중 차량을 가져가 손세차와 주유를 진행한 후 원위치 반납하는 일정으로 확인했습니다. 차량 키 위치와 주유 방식을 확인해도 될까요?",
        "required": {
            "차량 위치": "회사 지하주차장 A구역",
            "차량 키 위치": "비서실 보관",
            "세차 방식": "손세차",
            "주유/충전 방식": "휘발유 주유",
            "주유 금액": "5만 원",
            "반납 위치": "기존 주차 위치",
            "완료 사진 보고": "필요",
        },
        "complete_result": "세차/주유 대행 접수 완료",
        "sms": "[온디멘드 컨시어지] 세차/주유 대행이 접수되었습니다. 완료 후 사진과 함께 안내드리겠습니다.",
        "handoff_default": "차량 키 위치 불명확 또는 결제 확인 필요",
    },
    "inspection": {
        "domain": "concierge",
        "domain_label": "컨시어지 AI콜센터",
        "title": "자동차 검사 대행",
        "icon": "🧾",
        "type": "Vehicle Care",
        "trust": False,
        "customer": "최도윤",
        "phone": "010-7777-8800",
        "customer_type": "차량 검사 고객",
        "inbound_utterance": "자동차 정기검사 기간인데 대신 받아줘",
        "outbound_message": "고객님, 내일 자동차 정기검사 대행 일정이 있습니다. 오전 10시에 차량을 가져가도 될까요?",
        "ai_response": "고객님, 자동차 정기검사 대행 요청으로 확인했습니다. 차량번호와 검사 만료일을 확인한 뒤 검사소 예약, 픽업, 반납, 검사 결과 브리핑까지 진행하겠습니다.",
        "required": {
            "차량번호": "34나 9876",
            "검사 만료일": "2026년 5월 12일",
            "검사소": "청주 자동차검사소",
            "픽업 시간": "내일 오전 10시",
            "반납 시간": "검사 완료 후 오후 1시 예상",
            "결과 브리핑": "문자 리포트",
        },
        "complete_result": "자동차 검사 대행 접수 완료",
        "sms": "[온디멘드 컨시어지] 자동차 정기검사 대행이 접수되었습니다. 검사 결과는 문자로 브리핑해 드립니다.",
        "handoff_default": "검사소 예약 불가 또는 차량 서류 미확인",
    },
    "child_pickup": {
        "domain": "concierge",
        "domain_label": "컨시어지 AI콜센터",
        "title": "자녀 픽업/통학",
        "icon": "🧒",
        "type": "Human & Goods Care",
        "trust": True,
        "customer": "강민정",
        "phone": "010-8888-2400",
        "customer_type": "보호자 고객",
        "inbound_utterance": "오늘 4시에 아이 학원 끝나는데 집까지 데려다줘",
        "outbound_message": "고객님, 오늘 오후 4시 자녀 픽업 일정이 있습니다. 아동 케어 교육 이수 기사로 배정되며 보호자 확인 후 진행됩니다. 예정대로 진행할까요?",
        "ai_response": "고객님, 자녀 픽업 서비스는 고신뢰 서비스로 아동 케어 교육 이수 기사만 배정됩니다. 보호자 확인과 위치 공유 후 진행됩니다. 예정대로 진행할까요?",
        "required": {
            "자녀 이름": "강하준",
            "픽업 장소": "○○영어학원",
            "도착 장소": "고객 자택",
            "보호자 연락처": "010-8888-2400",
            "인계 확인 방식": "보호자 확인 코드",
            "기사 자격": "아동 케어 교육 이수 기사",
            "위치 공유": "필수",
            "도착 알림": "필수",
        },
        "complete_result": "상담원 확인 후 자녀 픽업 접수",
        "sms": "[온디멘드 컨시어지] 자녀 픽업 일정이 접수되었습니다. 보호자 확인과 기사 자격 검증 후 진행됩니다.",
        "handoff_default": "고신뢰 서비스: 보호자 확인 및 기사 자격 검증 필요",
    },
    "senior_escort": {
        "domain": "concierge",
        "domain_label": "컨시어지 AI콜센터",
        "title": "시니어 병원 동행",
        "icon": "🏥",
        "type": "Human & Goods Care",
        "trust": True,
        "customer": "윤서연",
        "phone": "010-9999-1144",
        "customer_type": "보호자 고객",
        "inbound_utterance": "내일 아버지 병원 진료가 있는데 모시고 가서 접수까지 도와줘",
        "outbound_message": "고객님, 내일 오전 10시 부모님 병원 동행 서비스가 예약되어 있습니다. 병원 접수와 대기 지원까지 진행할까요?",
        "ai_response": "부모님 병원 동행 서비스로 확인했습니다. 병원 접수와 대기 지원까지 포함하여 진행 가능하며, 보호자에게 진행 상황을 안내드리겠습니다.",
        "required": {
            "대상자 성함": "윤정식",
            "병원명": "청주성모병원",
            "진료 시간": "내일 오전 10시",
            "출발지": "대상자 자택",
            "보호자 연락처": "010-9999-1144",
            "접수 대행": "필요",
            "대기 지원": "필요",
            "귀가 동행": "필요",
            "긴급 연락 기준": "건강 이상/진료 지연 시 보호자 즉시 연락",
        },
        "complete_result": "상담원 확인 후 병원 동행 접수",
        "sms": "[온디멘드 컨시어지] 시니어 병원 동행 일정이 접수되었습니다. 보호자 알림과 진행 상황 공유가 포함됩니다.",
        "handoff_default": "고신뢰 서비스: 보호자 확인 및 긴급 기준 확인 필요",
    },
    "goods_delivery": {
        "domain": "concierge",
        "domain_label": "컨시어지 AI콜센터",
        "title": "물품 픽업/전달",
        "icon": "📦",
        "type": "Human & Goods Care",
        "trust": True,
        "customer": "문태호",
        "phone": "010-1212-5656",
        "customer_type": "물품 전달 고객",
        "inbound_utterance": "중요한 서류를 거래처에 전달해줘",
        "outbound_message": "고객님, 오늘 오후 3시 중요 서류 전달 일정이 있습니다. 수령인과 전달 장소를 다시 확인하겠습니다.",
        "ai_response": "고객님, 중요 서류 전달 요청으로 확인했습니다. 픽업 장소, 전달 장소, 수령인 정보를 확인하고 완료 인증 방식까지 설정한 뒤 진행하겠습니다.",
        "required": {
            "물품 종류": "중요 계약 서류",
            "픽업 장소": "고객 사무실",
            "전달 장소": "거래처 본사 안내데스크",
            "수령인 이름": "김담당",
            "수령인 연락처": "010-0000-7788",
            "완료 인증": "수령인 서명",
            "사진/서명 확인": "필수",
        },
        "complete_result": "상담원 확인 후 물품 전달 접수",
        "sms": "[온디멘드 컨시어지] 중요 서류 전달 일정이 접수되었습니다. 수령 확인 후 완료 인증을 보내드립니다.",
        "handoff_default": "고신뢰 서비스: 수령인 확인 및 완료 인증 필요",
    },
}


FAILURES = {
    "STT 장애": {
        "장애 상황": "고객 음성이 텍스트로 변환되지 않거나 잡음, 사투리, 통화품질 저하로 인식이 실패함",
        "감지 기준": "동일 항목 인식 실패 2회 이상 또는 필수 정보 미확인",
        "AI 1차 대응": "천천히 다시 말해달라고 요청하고 실패 횟수를 기록",
        "상담원 이관 기준": "2회 이상 재질문 후에도 필수 정보 미확인",
        "고객 안내 멘트": "죄송합니다. 말씀을 정확히 듣지 못했습니다. 상담원에게 바로 연결해 드리겠습니다.",
        "관리자 알림": "STT 실패 콜로 등록하고 상담원 콘솔에 표시",
        "사후 기록": "음성 품질, 실패 횟수, 고객 발화 원문을 개선 데이터로 저장",
    },
    "GPT/LLM 장애": {
        "장애 상황": "AI 응답 지연, 고객 의도 오인식, 잘못된 답변 생성",
        "감지 기준": "응답 지연 5초 이상 또는 의도 분류 신뢰도 낮음",
        "AI 1차 대응": "룰 기반 예비 멘트 제공 후 상담원 연결 준비",
        "상담원 이관 기준": "지연 반복 또는 고객 불만 증가",
        "고객 안내 멘트": "요청 내용을 정확히 확인하기 위해 상담원에게 연결해 드리겠습니다.",
        "관리자 알림": "LLM 장애/지연 콜로 등록",
        "사후 기록": "AI 응답, 고객 반응, 오류 유형을 품질 개선 데이터로 분류",
    },
    "TTS 장애": {
        "장애 상황": "AI 답변이 음성으로 출력되지 않거나 음성이 끊김",
        "감지 기준": "음성 출력 실패 또는 고객 무응답 증가",
        "AI 1차 대응": "고정 안내 멘트 또는 문자 안내로 대체",
        "상담원 이관 기준": "음성 출력 실패가 1회 이상 발생하고 고객 응답 확인 불가",
        "고객 안내 멘트": "안내 음성이 원활하지 않아 문자로도 안내드리겠습니다.",
        "관리자 알림": "TTS 장애 콜로 등록",
        "사후 기록": "TTS 실패 구간과 대체 안내 여부 저장",
    },
    "배차/예약 API 장애": {
        "장애 상황": "배차, 예약, 컨시어지 일정 등록 API 응답 실패",
        "감지 기준": "API 타임아웃 또는 예약 등록 실패",
        "AI 1차 대응": "임시 접수번호 발급 후 후속 연락 안내",
        "상담원 이관 기준": "예약 등록이 완료되지 않은 모든 콜",
        "고객 안내 멘트": "현재 시스템 확인이 지연되고 있습니다. 우선 접수해 두고 확인 후 다시 연락드리겠습니다.",
        "관리자 알림": "장애 콜을 관리자 대시보드 최상단 표시",
        "사후 기록": "API 오류 코드, 접수번호, 고객 후속 연락 필요 여부 저장",
    },
    "고신뢰 서비스 안전 이슈": {
        "장애 상황": "자녀 픽업, 시니어 동행, 중요 물품 전달에서 보호자 확인 또는 기사 자격 검증 미완료",
        "감지 기준": "고신뢰 서비스인데 보호자 확인, 위치 공유, 완료 인증 중 하나라도 미확인",
        "AI 1차 대응": "AI 단독 완료를 막고 상담원 확인 단계로 전환",
        "상담원 이관 기준": "고신뢰 서비스 전체",
        "고객 안내 멘트": "안전 확인이 필요한 서비스라 상담원이 최종 확인 후 진행하겠습니다.",
        "관리자 알림": "고신뢰 확인 필요 콜로 표시",
        "사후 기록": "확인자, 기사 자격, 보호자 동의, 위치 공유 동의 저장",
    },
    "긴급상황": {
        "장애 상황": "고객이 아프다, 사고, 길 잃음, 고령자 혼란 상태를 언급",
        "감지 기준": "응급, 사고, 실종, 고령자 혼란 키워드 감지",
        "AI 1차 대응": "긴급 여부 확인 후 상담원 최우선 이관",
        "상담원 이관 기준": "긴급 가능성이 있는 모든 콜",
        "고객 안내 멘트": "위급한 상황이면 119 또는 112로 바로 연락하셔야 합니다. 상담원에게 바로 연결하겠습니다.",
        "관리자 알림": "긴급 콜로 최상단 표시 및 알림음 발생",
        "사후 기록": "긴급 키워드, 위치, 보호자 연락 여부, 상담원 처리 결과 저장",
    },
}


KEYWORDS = {
    "taxi_dispatch": ["택시", "배차", "내수", "서당", "이동", "차 좀 보내"],
    "goods_order": ["주문", "생수", "휴지", "배달", "장보기", "물건"],
    "customer_schedule": ["스케줄", "일정", "예약", "리마인드"],
    "mobility_complaint": ["늦", "안 왔", "상담원", "불만", "화", "민원"],
    "vehicle_repair": ["정비", "서비스센터", "입고", "수리", "엔진오일"],
    "carwash_fuel": ["세차", "주유", "충전", "기름", "손세차"],
    "inspection": ["검사", "정기검사", "검사소"],
    "child_pickup": ["아이", "자녀", "학원", "학교", "등원", "하원", "픽업"],
    "senior_escort": ["아버지", "어머니", "부모", "병원", "진료", "동행", "접수"],
    "goods_delivery": ["서류", "전달", "거래처", "선물", "소형 화물"],
}


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800;900&display=swap');
:root{--bg:#F5F7FB;--ink:#111827;--muted:#667085;--line:#E5E7EB;--brand:#FFD400;--red:#E53935;--green:#16A34A;--blue:#2563EB;--shadow:0 18px 50px rgba(15,23,42,.11);--shadow-sm:0 8px 26px rgba(15,23,42,.08);}
.stApp{background:radial-gradient(circle at 10% 0%,rgba(255,212,0,.22),transparent 28%),radial-gradient(circle at 90% 8%,rgba(37,99,235,.10),transparent 26%),var(--bg)!important;color:var(--ink)!important;font-family:'Noto Sans KR',sans-serif!important;}
*{font-family:'Noto Sans KR',sans-serif!important}.block-container{max-width:1180px;padding-top:1.3rem;padding-bottom:4rem}header,footer,#MainMenu{visibility:hidden}
.hero{background:linear-gradient(135deg,#111827 0%,#1F2937 56%,#2B2408 100%);border-radius:34px;padding:34px;box-shadow:var(--shadow);margin-bottom:18px;position:relative;overflow:hidden}.hero:after{content:'';position:absolute;right:-70px;top:-80px;width:250px;height:250px;border-radius:50%;background:rgba(255,212,0,.22)}.hero *{color:white!important;position:relative;z-index:1}.kicker{display:inline-flex;padding:8px 13px;border-radius:999px;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.16);font-size:14px;font-weight:900}.hero-title{font-size:44px;line-height:1.12;font-weight:900;letter-spacing:-1.3px;margin:10px 0}.hero-sub{font-size:17px;line-height:1.7;color:#D1D5DB!important;max-width:860px}
.card{background:rgba(255,255,255,.96)!important;color:var(--ink)!important;border:1px solid rgba(229,231,235,.92);border-radius:26px;padding:24px;margin-bottom:16px;box-shadow:var(--shadow-sm)}.card *{color:var(--ink)!important}
.domain-card{min-height:230px}.service-card{min-height:218px}.phone-card{background:linear-gradient(180deg,#111827 0%,#0B1220 100%)!important;border-radius:34px;padding:26px;min-height:560px;box-shadow:var(--shadow);border:1px solid rgba(255,255,255,.08)}.phone-card *{color:white!important}.phone-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px}.phone-status{font-size:14px;color:#9CA3AF!important;font-weight:800}.phone-name{font-size:32px;font-weight:900;letter-spacing:-.7px;margin:8px 0 2px}.phone-number{color:#D1D5DB!important;font-size:16px;font-weight:700}.avatar{width:92px;height:92px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#FFD400,#FFB800);color:#111827!important;font-size:38px;font-weight:900;margin:24px auto 10px;box-shadow:0 12px 30px rgba(255,212,0,.25)}.call-timer{text-align:center;color:#D1D5DB!important;font-size:15px;font-weight:800;margin-top:8px}.wave{display:flex;justify-content:center;align-items:end;gap:5px;height:54px;margin:22px 0 10px}.wave span{width:7px;border-radius:999px;background:#FFD400;display:block}.wave span:nth-child(1){height:18px}.wave span:nth-child(2){height:34px}.wave span:nth-child(3){height:22px}.wave span:nth-child(4){height:46px}.wave span:nth-child(5){height:28px}.wave span:nth-child(6){height:39px}.wave span:nth-child(7){height:20px}.wave span:nth-child(8){height:31px}.call-buttons{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:18px}.call-pill{border-radius:18px;padding:13px 8px;text-align:center;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);font-size:13px;font-weight:900}.call-end{background:#EF4444!important}
.console{background:#fff;border:1px solid var(--line);border-radius:28px;padding:24px;box-shadow:var(--shadow-sm);margin-bottom:16px}.console *{color:var(--ink)!important}.badge{display:inline-flex;align-items:center;background:#EEF2FF;color:#3730A3!important;border:1px solid #C7D2FE;padding:7px 11px;border-radius:999px;font-size:13px;font-weight:900;margin-right:6px;margin-bottom:8px}.badge-warning{background:#FFF7ED;color:#C2410C!important;border-color:#FED7AA}.badge-success{background:#ECFDF3;color:#027A48!important;border-color:#ABEFC6}.badge-dark{background:#111827;color:white!important;border-color:#111827}.badge-red{background:#FEF2F2;color:#B42318!important;border-color:#FECDCA}
.sec{font-size:24px;font-weight:900;letter-spacing:-.5px;margin:8px 0 14px;color:var(--ink)!important}.subtle{color:var(--muted)!important;font-weight:700;line-height:1.6}.red{color:var(--red)!important;font-size:30px;font-weight:900}.green{color:var(--green)!important;font-weight:900}.big{font-size:34px;font-weight:900}
.kpi-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:14px 0 18px}.kpi{background:#fff;border:1px solid var(--line);border-radius:24px;padding:19px;box-shadow:0 8px 24px rgba(15,23,42,.07)}.kpi-label{font-size:13px;font-weight:900;color:var(--muted)!important;margin-bottom:8px}.kpi-value{font-size:28px;font-weight:900;letter-spacing:-.6px;color:var(--ink)!important}.kpi-note{font-size:12px;font-weight:700;color:var(--muted)!important;margin-top:4px}
.bubble{font-size:20px;line-height:1.75;font-weight:800;border-radius:24px;padding:22px;margin-bottom:14px;box-shadow:0 10px 28px rgba(15,23,42,.08)}.user{background:#fff!important;border:1px solid #CBD5E1;color:var(--ink)!important}.user *{color:var(--ink)!important}.ai{background:linear-gradient(135deg,#FFF8D6 0%,#fff 100%)!important;border:2px solid var(--brand);color:var(--ink)!important}.ai *{color:var(--ink)!important}
.info-row{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;border-bottom:1px dashed #E5E7EB;padding:12px 0;font-size:16px}.info-row:last-child{border-bottom:none}.info-key{color:var(--muted)!important;font-weight:900;min-width:130px}.info-val{color:var(--ink)!important;font-weight:900;text-align:right}
.stButton>button{width:100%;min-height:3.35rem;border-radius:18px;font-size:17px;font-weight:900;background:linear-gradient(135deg,#FFD400 0%,#FFC000 100%)!important;color:#111827!important;border:1px solid rgba(17,24,39,.08)!important;box-shadow:0 8px 18px rgba(255,184,0,.22);transition:all .16s ease}.stButton>button:hover{transform:translateY(-1px);box-shadow:0 12px 26px rgba(255,184,0,.28);border-color:#FFB800!important}
div[data-testid="stMetric"]{background:#fff!important;color:var(--ink)!important;border:1px solid var(--line);border-radius:22px;padding:16px;box-shadow:0 8px 22px rgba(15,23,42,.06)}div[data-testid="stMetric"] *{color:var(--ink)!important}[data-testid="stDataFrame"]{border-radius:18px;overflow:hidden;box-shadow:0 10px 24px rgba(15,23,42,.06)}
@media(max-width:780px){.block-container{padding-left:1rem;padding-right:1rem}.hero{padding:25px;border-radius:26px}.hero-title{font-size:32px}.kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.call-buttons{grid-template-columns:repeat(2,1fr)}.info-row{flex-direction:column;gap:4px}.info-val{text-align:left}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


try:
    from openai import OpenAI
except Exception:
    OpenAI = None


def init_state():
    st.session_state.setdefault("page", "main")
    st.session_state.setdefault("domain", None)
    st.session_state.setdefault("scenario", None)
    st.session_state.setdefault("call_mode", "inbound")
    st.session_state.setdefault("call_status", "idle")
    st.session_state.setdefault("transcript", "")
    st.session_state.setdefault("handoff_reason", "")
    st.session_state.setdefault("logs", [])
    st.session_state.setdefault("OPENAI_API_KEY_INPUT", "")


def go(page):
    st.session_state.page = page
    st.rerun()


def hero(step="AI Call Center", title="온디멘드 AI콜센터 시나리오_데모앱", subtitle="모빌리티 AI콜센터와 컨시어지 AI콜센터를 구분하여 시연합니다."):
    st.markdown(
        f"""
        <div class="hero">
            <div class="kicker">☎️ {step}</div>
            <div class="hero-title">{title}</div>
            <div class="hero-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar():
    with st.sidebar:
        st.markdown("### STT 설정")
        typed_key = st.text_input("OpenAI API Key", value="", type="password")
        if typed_key:
            st.session_state["OPENAI_API_KEY_INPUT"] = typed_key
        st.caption("Secrets 또는 이 입력칸 중 하나에 API Key가 있으면 실제 STT가 동작합니다.")
        st.divider()
        st.markdown("### 빠른 이동")
        if st.button("홈"):
            go("main")
        if st.button("서비스 선택"):
            go("services")
        if st.button("관리자 대시보드"):
            go("admin")
        if st.button("장애 대응"):
            go("failure")
        if st.button("비용 분석"):
            go("cost")


def nav():
    c1, c2, c3, c4, c5 = st.columns(5)
    if c1.button("🏠 홈"):
        go("main")
    if c2.button("📋 서비스 선택"):
        go("services")
    if c3.button("⚠️ 장애"):
        go("failure")
    if c4.button("📊 관리자"):
        go("admin")
    if c5.button("💰 비용"):
        go("cost")


def info_row(key, value):
    return f'<div class="info-row"><span class="info-key">{key}</span><span class="info-val">{value}</span></div>'


def services_by_domain(domain):
    return {k: v for k, v in SERVICES.items() if v["domain"] == domain}


def get_service():
    key = st.session_state.scenario or "taxi_dispatch"
    return SERVICES[key]


def set_service(key, mode):
    svc = SERVICES[key]
    st.session_state.scenario = key
    st.session_state.domain = svc["domain"]
    st.session_state.call_mode = mode
    st.session_state.call_status = "ringing"
    st.session_state.transcript = ""
    go("phone")


def money(n):
    return f"{int(n):,}원"


def add_log(status, result, reason="-"):
    svc = get_service()
    st.session_state.logs.append(
        {
            "시간": datetime.now().strftime("%H:%M:%S"),
            "고객명": svc["customer"],
            "전화번호": svc["phone"],
            "도메인": svc["domain_label"],
            "서비스": svc["title"],
            "인/아웃": "아웃바운드" if st.session_state.call_mode == "outbound" else "인바운드",
            "고신뢰": "Y" if svc["trust"] else "N",
            "처리상태": status,
            "이관사유": reason,
            "결과": result,
        }
    )


def classify_intent(text):
    if not text:
        return st.session_state.scenario or "taxi_dispatch"
    t = text.lower()
    scores = {}
    for key, words in KEYWORDS.items():
        scores[key] = sum(1 for w in words if w.lower() in t)
    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best
    return st.session_state.scenario or "taxi_dispatch"


def get_api_key():
    api_key = st.session_state.get("OPENAI_API_KEY_INPUT", "")
    if api_key:
        return api_key
    try:
        return st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        return ""


def transcribe_audio(audio_file):
    if OpenAI is None:
        return None, "openai 패키지가 설치되어 있지 않습니다."
    api_key = get_api_key()
    if not api_key:
        return None, "OpenAI API Key가 없습니다. 사이드바 또는 Streamlit Secrets에 입력하세요."
    try:
        client = OpenAI(api_key=api_key)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_file.getvalue())
            tmp_path = tmp.name
        with open(tmp_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=f,
                language="ko",
            )
        return result.text, None
    except Exception as e:
        return None, str(e)


def phone_visual(status="ringing", mode="inbound"):
    svc = get_service()
    status_label = {
        "ringing": "수신 대기 중" if mode == "inbound" else "발신 연결 중",
        "active": "AI 상담 통화 중",
        "ended": "통화 종료",
    }.get(status, "대기")
    timer = "00:00" if status == "ringing" else "00:42" if status == "active" else "01:18"
    call_icon = "📞" if mode == "outbound" else "☎️"
    mode_text = "아웃바운드 스케줄 확인콜" if mode == "outbound" else "인바운드 접수콜"
    st.markdown(
        f"""
        <div class="phone-card">
            <div class="phone-top"><div class="phone-status">{mode_text}</div><div class="phone-status">{status_label}</div></div>
            <div class="avatar">{call_icon}</div>
            <div style="text-align:center;">
                <div class="phone-name">{svc['customer']}</div>
                <div class="phone-number">{svc['phone']} · {svc['customer_type']}</div>
                <div class="call-timer">{timer}</div>
            </div>
            <div class="wave"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>
            <div class="call-buttons"><div class="call-pill">🎙️ STT</div><div class="call-pill">🤖 AI 상담</div><div class="call-pill">🧑‍💼 이관</div><div class="call-pill">📝 로그</div><div class="call-pill">💬 알림</div><div class="call-pill call-end">종료</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    hero(
        step="On-demand AI Callcenter",
        title="온디멘드 AI콜센터 시나리오_데모앱",
        subtitle="메인에서 모빌리티 AI콜센터와 컨시어지 AI콜센터를 구분하여 선택하고, 각 서비스의 인바운드 접수와 아웃바운드 스케줄 확인콜을 시연합니다.",
    )
    st.markdown(
        """
        <div class="kpi-grid">
            <div class="kpi"><div class="kpi-label">도메인</div><div class="kpi-value">2개</div><div class="kpi-note">모빌리티 / 컨시어지</div></div>
            <div class="kpi"><div class="kpi-label">서비스 시나리오</div><div class="kpi-value">10개</div><div class="kpi-note">기존 + 확장</div></div>
            <div class="kpi"><div class="kpi-label">콜 방식</div><div class="kpi-value">2종</div><div class="kpi-note">인바운드 / 아웃바운드</div></div>
            <div class="kpi"><div class="kpi-label">고신뢰 서비스</div><div class="kpi-value">4종</div><div class="kpi-note">인간 확인 포함</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            <div class="card domain-card">
                <span class="badge badge-dark">Mobility</span>
                <div class="sec">🚕 모빌리티 AI콜센터</div>
                기존 AI콜센터 시나리오입니다. 택시 배차/예약, 물건 주문, 고객 스케줄링, 민원 및 예외 응대를 처리합니다.
                <br><br>
                <b>포함:</b> 택시 배차, 주문, 병원/이동 예약, 민원 응대
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🚕 모빌리티 시나리오 선택"):
            st.session_state.domain = "mobility"
            go("services")
    with col2:
        st.markdown(
            """
            <div class="card domain-card">
                <span class="badge badge-success">Concierge</span>
                <div class="sec">🧑‍💼 컨시어지 AI콜센터</div>
                확장 온디멘드 시나리오입니다. Vehicle Care와 Human & Goods Care를 고객 일정에 맞춰 접수하고 확인합니다.
                <br><br>
                <b>포함:</b> 정비, 세차/주유, 검사, 자녀 픽업, 시니어 동행, 물품 전달
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🧑‍💼 컨시어지 시나리오 선택"):
            st.session_state.domain = "concierge"
            go("services")

    st.markdown(
        """
        <div class="card">
            <span class="badge">STT</span>
            <span class="badge badge-warning">아웃바운드 확인콜</span>
            <span class="badge badge-success">고신뢰 확인</span>
            <div class="sec">데모 핵심</div>
            고객이 직접 앱을 쓰지 않아도 전화 기반으로 요청을 접수하고, 예약 전 AI가 아웃바운드콜로 스케줄과 진행 의사를 확인합니다. 
            자녀 픽업, 시니어 병원 동행, 물품 전달, 민원 같은 고신뢰/예외 영역은 AI 단독 완료가 아니라 상담원 확인으로 넘어갑니다.
        </div>
        """,
        unsafe_allow_html=True,
    )


def service_selection():
    domain = st.session_state.domain or "mobility"
    title = "모빌리티 AI콜센터" if domain == "mobility" else "컨시어지 AI콜센터"
    subtitle = "기존 AI콜센터 기본 시나리오를 선택합니다." if domain == "mobility" else "차량 케어와 라이프 케어 컨시어지 시나리오를 선택합니다."
    hero(step="Scenario Select", title=title, subtitle=subtitle)
    services = services_by_domain(domain)
    keys = list(services.keys())
    for i in range(0, len(keys), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j >= len(keys):
                continue
            key = keys[i + j]
            svc = SERVICES[key]
            trust_badge = '<span class="badge badge-warning">고신뢰 확인 필요</span>' if svc["trust"] else '<span class="badge badge-success">AI 1차 처리 가능</span>'
            with col:
                st.markdown(
                    f"""
                    <div class="card service-card">
                        <span class="badge badge-dark">{svc['type']}</span>
                        {trust_badge}
                        <div class="sec">{svc['icon']} {svc['title']}</div>
                        <div class="subtle">생활 요청: “{svc['inbound_utterance']}”</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                c1, c2 = st.columns(2)
                if c1.button("인바운드 접수", key=f"in_{key}"):
                    set_service(key, "inbound")
                if c2.button("아웃바운드 확인콜", key=f"out_{key}"):
                    set_service(key, "outbound")
    nav()


def render_stt_area():
    svc = get_service()
    st.markdown(
        '<div class="console"><span class="badge">STT</span><div class="sec">마이크 음성 인식 / 시뮬레이션 발화</div><div class="subtle">OpenAI API Key가 있으면 마이크 녹음을 텍스트로 변환합니다. API Key가 없으면 아래 버튼으로 시뮬레이션 발화를 사용하세요.</div></div>',
        unsafe_allow_html=True,
    )
    if hasattr(st, "audio_input"):
        audio_value = st.audio_input("고객 음성을 녹음하세요", key="audio_input")
        if audio_value is not None:
            st.audio(audio_value)
            if st.button("🎙️ STT 실행"):
                text, err = transcribe_audio(audio_value)
                if err:
                    st.error(err)
                else:
                    st.session_state.transcript = text
                    st.session_state.scenario = classify_intent(text)
                    st.success("STT 완료")
                    st.rerun()
    else:
        st.warning("현재 Streamlit 버전에서 st.audio_input을 지원하지 않습니다. requirements.txt 기준으로 업데이트하세요.")

    sample = svc["outbound_message"] if st.session_state.call_mode == "outbound" else svc["inbound_utterance"]
    if st.button("🧪 현재 시나리오 발화로 STT 시뮬레이션"):
        st.session_state.transcript = sample
        st.rerun()

    if st.session_state.transcript:
        detected = SERVICES[classify_intent(st.session_state.transcript)]
        st.markdown(
            f"""
            <div class="bubble user">🎤 STT 결과<br>“{st.session_state.transcript}”</div>
            <div class="card">
                <span class="badge badge-success">의도 분석</span>
                <div class="sec">{detected['icon']} {detected['title']}</div>
                {info_row('도메인', detected['domain_label'])}
                {info_row('고신뢰 여부', '고신뢰 확인 필요' if detected['trust'] else 'AI 1차 처리 가능')}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if detected is not svc:
            if st.button("분석된 시나리오로 전환"):
                st.session_state.scenario = classify_intent(st.session_state.transcript)
                st.rerun()


def phone_console():
    svc = get_service()
    title = f"{svc['icon']} {svc['title']}"
    subtitle = "인바운드 접수콜" if st.session_state.call_mode == "inbound" else "아웃바운드 스케줄 확인콜"
    hero(step="Call Console", title=title, subtitle=f"{svc['domain_label']} · {subtitle}")
    left, right = st.columns([0.85, 1.15])
    with left:
        phone_visual(st.session_state.call_status, st.session_state.call_mode)
    with right:
        if st.session_state.call_status == "ringing":
            direction = "고객 전화 수신" if st.session_state.call_mode == "inbound" else "AI 아웃바운드 발신"
            first_text = svc["inbound_utterance"] if st.session_state.call_mode == "inbound" else svc["outbound_message"]
            st.markdown(
                f"""
                <div class="console">
                    <span class="badge badge-success">{direction}</span>
                    <span class="badge">{svc['type']}</span>
                    {'<span class="badge badge-warning">고신뢰 확인 필요</span>' if svc['trust'] else ''}
                    <div class="sec">콜 이벤트</div>
                    {info_row('고객명', svc['customer'])}
                    {info_row('전화번호', svc['phone'])}
                    {info_row('고객유형', svc['customer_type'])}
                    {info_row('상담 시작 멘트', first_text)}
                </div>
                """,
                unsafe_allow_html=True,
            )
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
            req_html = "".join(info_row(k, v) for k, v in svc["required"].items())
            st.markdown(
                f"""
                <div class="card">
                    <span class="badge badge-dark">필수 정보 확인</span>
                    {'<span class="badge badge-warning">고신뢰 확인 필요</span>' if svc['trust'] else '<span class="badge badge-success">AI 1차 처리 가능</span>'}
                    <div class="sec">서비스 처리 정보</div>
                    {req_html}
                </div>
                <div class="bubble ai">🤖 AI 상담원<br>{svc['ai_response']}</div>
                """,
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 고객 동의 / 접수 확정"):
                    if svc["trust"]:
                        handoff("고신뢰 서비스 확인 필요")
                    else:
                        add_log("AI 단독 처리", svc["complete_result"])
                        go("complete")
                if st.button("📆 일정 변경 요청"):
                    add_log("일정 변경 요청", "상담원 확인 필요", "고객 일정 변경")
                    handoff("일정 변경 요청")
            with c2:
                if st.button("🧑‍💼 상담원 이관"):
                    handoff(svc["handoff_default"])
                if st.button("🔚 통화 종료"):
                    add_log("통화 종료", "상담 종료")
                    st.session_state.call_status = "ended"
                    st.rerun()
        else:
            st.markdown(
                '<div class="console"><span class="badge badge-red">통화 종료</span><div class="sec">통화가 종료되었습니다</div>상담 결과는 관리자 대시보드에 반영됩니다.</div>',
                unsafe_allow_html=True,
            )
    nav()


def handoff(reason):
    st.session_state.handoff_reason = reason
    add_log("상담원 이관", "인간 상담원 처리 대기", reason)
    go("handoff")


def complete():
    svc = get_service()
    rows = "".join(info_row(k, v) for k, v in svc["required"].items())
    hero(step="Completed", title=f"{svc['icon']} {svc['title']} 처리 완료", subtitle=svc["complete_result"])
    st.markdown(
        f"""
        <div class="card">
            <span class="badge badge-success">처리 완료</span>
            <div class="sec">접수/예약 정보</div>
            {info_row('고객명', svc['customer'])}
            {info_row('전화번호', svc['phone'])}
            {info_row('서비스', svc['title'])}
            {rows}
        </div>
        <div class="card">
            <span class="badge">알림톡/문자</span>
            <div class="sec">고객 안내 문구</div>
            {svc['sms']}
        </div>
        """,
        unsafe_allow_html=True,
    )
    nav()


def handoff_page():
    svc = get_service()
    reason = st.session_state.handoff_reason or svc["handoff_default"]
    urgency = "높음" if svc["trust"] or any(k in reason for k in ["긴급", "민원", "불만", "고신뢰"]) else "보통"
    transcript = st.session_state.transcript or svc["inbound_utterance"]
    required_state = "고신뢰 확인 필요" if svc["trust"] else "필수 정보 대부분 확인"
    hero(step="Human Handoff", title="상담원 이관", subtitle="AI가 처리하기 어려운 상황은 상담원에게 요약 정보와 함께 즉시 전달됩니다.")
    st.warning(f"인간 상담원 이관: {reason}")
    st.markdown(
        f"""
        <div class="card">
            <span class="badge badge-warning">이관 필요</span>
            <span class="badge">긴급도 {urgency}</span>
            {'<span class="badge badge-red">고신뢰</span>' if svc['trust'] else ''}
            <div class="sec">상담원에게 전달되는 정보</div>
            {info_row('고객명', svc['customer'])}
            {info_row('전화번호', svc['phone'])}
            {info_row('서비스 유형', svc['title'])}
            {info_row('고객 발화 원문', transcript)}
            {info_row('AI 요약', svc['ai_response'])}
            {info_row('필수 정보 확인 상태', required_state)}
            {info_row('이관 사유', reason)}
            {info_row('긴급도', f'<span class="red">{urgency}</span>')}
            {info_row('고신뢰 여부', 'Y' if svc['trust'] else 'N')}
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    if c1.button("✅ 접수 확정"):
        add_log("상담원 처리", "상담원이 접수 확정", reason)
        go("complete")
    if c2.button("📆 일정 변경"):
        add_log("상담원 처리", "일정 변경 처리", reason)
        st.success("일정 변경 처리로 기록되었습니다.")
    if c3.button("❌ 취소 처리"):
        add_log("상담원 처리", "고객 취소 처리", reason)
        st.warning("취소 처리로 기록되었습니다.")
    c4, c5, c6 = st.columns(3)
    if c4.button("👨‍👩‍👧 보호자 연락"):
        add_log("상담원 처리", "보호자 연락 필요", reason)
        st.info("보호자 연락 필요 콜로 등록되었습니다.")
    if c5.button("🚗 기사 재배정"):
        add_log("상담원 처리", "기사 재배정 필요", reason)
        st.info("기사 재배정 필요 콜로 등록되었습니다.")
    if c6.button("🚨 긴급 대응"):
        add_log("상담원 처리", "긴급 대응", reason)
        st.error("긴급 대응 콜로 등록되었습니다.")
    nav()


def failure():
    hero(step="Failure Control", title="장애 대응 데모", subtitle="STT, LLM, TTS, API, 고신뢰 안전 이슈, 긴급상황을 상담원 이관으로 처리합니다.")
    name = st.selectbox("장애 유형 선택", list(FAILURES.keys()))
    s = FAILURES[name]
    html = "".join(info_row(k, v) for k, v in s.items())
    st.markdown(
        f'<div class="card"><span class="badge badge-warning">{name}</span><div class="sec">장애 대응 프로세스</div>{html}</div>',
        unsafe_allow_html=True,
    )
    if st.button("☎️ 이 장애 상황으로 상담원 이관"):
        handoff(name)
    nav()


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


def cost():
    hero(step="Cost Simulation", title="운영비 절감 분석", subtitle="24시간 365일 인간 콜센터 운영비와 AI콜센터 도입 후 비용 구조를 비교합니다.")
    base, extra, human, premium, standard = cost_data()
    st.markdown(
        f"""
        <div class="kpi-grid">
            <div class="kpi"><div class="kpi-label">최소 운영 인력</div><div class="kpi-value">5명</div><div class="kpi-note">24시간 365일 기준</div></div>
            <div class="kpi"><div class="kpi-label">1인 월 급여</div><div class="kpi-value">350만</div><div class="kpi-note">기본 급여</div></div>
            <div class="kpi"><div class="kpi-label">월 기본 인건비</div><div class="kpi-value">1,750만</div><div class="kpi-note">수당 제외</div></div>
            <div class="kpi"><div class="kpi-label">연 기본 인건비</div><div class="kpi-value">2.1억</div><div class="kpi-note">수당 제외</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="card"><div class="sec">추가 운영비 추정</div></div>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame([{"항목": k, "월 비용": v} for k, v in extra.items()]), use_container_width=True, hide_index=True)
    df = pd.DataFrame(
        [
            {"운영 구조": "전면 인간 상담", "월 비용": human, "연 비용": human * 12},
            {"운영 구조": "AI 1차 상담 + 인간 예외 대응", "월 비용": premium, "연 비용": premium * 12},
            {"운영 구조": "AI 중심 + 관리자 모니터링", "월 비용": standard, "연 비용": standard * 12},
            {"운영 구조": "고신뢰 서비스 인간 확인 포함", "월 비용": int(premium * 1.18), "연 비용": int(premium * 1.18) * 12},
        ]
    )
    st.markdown('<div class="card"><div class="sec">비용 비교</div></div>', unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.bar_chart(df.set_index("운영 구조")[["월 비용"]])
    saving = human - premium
    st.markdown(
        f'<div class="card"><div class="sec">절감 효과 예시</div>AI 1차 상담 + 인간 예외 대응 구조 적용 시 월 약 <span class="red">{money(saving)}</span> 절감 가능. 추정 절감률은 <span class="red">{saving / human * 100:.1f}%</span>입니다.</div>',
        unsafe_allow_html=True,
    )
    nav()


def admin():
    hero(step="Admin Dashboard", title="관리자 대시보드", subtitle="모빌리티와 컨시어지 콜을 통합 관리합니다.")
    logs = st.session_state.logs
    total = max(len(logs), 1)
    ai = sum(1 for x in logs if x["처리상태"] == "AI 단독 처리")
    handoff_count = sum(1 for x in logs if "이관" in x["처리상태"])
    trust = sum(1 for x in logs if x["고신뢰"] == "Y")
    outbound = sum(1 for x in logs if x["인/아웃"] == "아웃바운드")
    _, _, human, premium, _ = cost_data()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 인입/발신 콜", len(logs))
    c2.metric("AI 단독 처리", ai)
    c3.metric("상담원 이관", handoff_count)
    c4.metric("월 예상 절감", money(human - premium))
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("고신뢰 서비스 콜", trust)
    c6.metric("아웃바운드 확인", outbound)
    c7.metric("AI 처리율", f"{ai / total * 100:.0f}%")
    c8.metric("이관율", f"{handoff_count / total * 100:.0f}%")
    st.markdown('<div class="card"><div class="sec">상담 로그</div></div>', unsafe_allow_html=True)
    if logs:
        st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
    else:
        st.info("아직 상담 로그가 없습니다. 모빌리티 또는 컨시어지 시나리오를 먼저 실행해 주세요.")
    nav()


init_state()
sidebar()

pages = {
    "main": main,
    "services": service_selection,
    "phone": phone_console,
    "complete": complete,
    "handoff": handoff_page,
    "failure": failure,
    "admin": admin,
    "cost": cost,
}

pages.get(st.session_state.page, main)()
