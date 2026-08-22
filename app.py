import streamlit as st
import json
import urllib.request
import urllib.error

# ----------------------------------------------------
# 1. 시스템 프롬프트 정의
# ----------------------------------------------------
SYSTEM_PROMPT = """
# Role & Persona: REABC 독서코칭단 전담 AI 코치
- 당신은 대치동 논술화랑 독서관리 시스템과 코칭을 융합하여 청소년의 주체적인 삶과 유쾌한 책읽기를 이끄는 전문 독서코치입니다.
- 핵심 미션: "독서와 코칭의 천상의 하모니를 위하여!" 아이들에게 '좋은 어른을 만나는 12가지 학습경험'을 제공합니다.
- 코칭 스타일: 친근하고 다정하며 따뜻한 '해요체' 사용. 구체적인 성취를 칭찬하고, 닫힌 정답형 질문을 배제하며 열린 사유를 촉진합니다.

# Core Framework: REABC 독서코칭 5단계 파이프라인
1. [R]apport (라포 형성: 친밀감 재점화 - 3분)
2. [E]xploration (탐색: 1박자 [찾고!] - 5분)
3. [A]ction (행동 실천: 2박자 [읽고!] - 10분)
4. [B]ridge (연결 및 습관 정착: 3박자 [만들고!] - 12~15분)
5. [C]hange (변화 완료: 자기주도성 내재화 - 5분)
"""

# ----------------------------------------------------
# 2. Gemini API 호출 함수
# ----------------------------------------------------
def get_available_model(api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            models = data.get("models", [])
            for m in models:
                if "generateContent" in m.get("supportedGenerationMethods", []):
                    name = m.get("name", "")
                    if "flash" in name:
                        return name
            for m in models:
                if "generateContent" in m.get("supportedGenerationMethods", []):
                    return m.get("name", "")
    except Exception:
        pass
    return "models/gemini-1.5-flash"

def call_gemini_api(api_key, messages):
    model_name = get_available_model(api_key)
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
    
    formatted_contents = [{
        "role": "user",
        "parts": [{"text": f"[시스템 코칭 가이드라인]\n{SYSTEM_PROMPT}\n\n위 REABC 모델에 맞춰 따뜻하고 유쾌하게 독서코칭을 진행하세요."}]
    }, {
        "role": "model",
        "parts": [{"text": "안녕! 반가워. 지난주에 네가 남겨준 독서노트를 보고 선생님이 정말 감동받았어! 지난주 읽은 부분 중에 가장 기억에 남는 장면은 뭐였니?"}]
    }]
    
    for msg in messages[1:]:
        role = "user" if msg["role"] == "user" else "model"
        formatted_contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })
    
    payload = {
        "contents": formatted_contents,
        "generationConfig": {"temperature": 0.7}
    }
    
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        return res_data["candidates"][0]["content"]["parts"][0]["text"]

# ----------------------------------------------------
# 3. Streamlit UI 구성
# ----------------------------------------------------
st.set_page_config(page_title="REABC 독서코칭 AI 클론", page_icon="📚", layout="centered")

st.title("📚 REABC 독서코칭 AI 클론")
st.caption("독서와 코칭의 천상의 하모니 | 청소년 주체성 중심 1:1 독서코치")

# API Key 불러오기 (서버 비밀설정 우선, 없으면 사이드바 입력창 표시)
api_key = st.secrets.get("GEMINI_API_KEY", "")
if not api_key:
    with st.sidebar:
        st.header("설정")
        api_key = st.text_input("Gemini API Key를 입력하세요", type="password")

with st.sidebar:
    st.markdown("---")
    st.markdown("**REABC 코칭 단계:**")
    st.markdown("""
    * **R (라포 형성)**: 친밀감 & 전주 성취 칭찬
    * **E (탐색)**: 표지 이야기 & 분량 선택
    * **A (행동)**: 함께 읽기 (음독/묵독)
    * **B (연결)**: 사유 확장 & 독서활동 기록
    * **C (변화)**: 차주 도서 선정 & 이유 말하기
    """)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "model", "content": "안녕! 반가워. 지난주에 네가 남겨준 독서노트를 보고 선생님이 정말 감동받았어! 지난주 읽은 부분 중에 가장 기억에 남는 장면은 뭐였니?"}
    ]

for msg in st.session_state.messages:
    display_role = "assistant" if msg["role"] == "model" else "user"
    with st.chat_message(display_role):
        st.write(msg["content"])

if user_input := st.chat_input("코치님에게 메시지를 보내보세요..."):
    if not api_key:
        st.info("API Key가 설정되지 않았습니다.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            assistant_reply = call_gemini_api(api_key, st.session_state.messages)
            message_placeholder.write(assistant_reply)
            st.session_state.messages.append({"role": "model", "content": assistant_reply})
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            st.error(f"API 호출 오류 ({e.code}):\n{err_body}")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
