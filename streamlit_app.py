import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import time
from streamlit_geolocation import streamlit_geolocation

# --- 1. 基礎設定 ---
st.set_page_config(page_title="Decathlon Smart Clock-In", page_icon="⏱️")

# --- 讀取 Web App URL ---
try:
    SCRIPT_URL = st.secrets["gsheet_app"]["script_url"]
except:
    st.error("⚠️ 請在 Secrets 設定 script_url！")
    st.stop()

# --- 2. 身份驗證 ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""

# 未登入畫面
if not st.session_state.authenticated:
    st.title("🔐 Decathlon 員工登入")
    with st.form("login_form"):
        email_input = st.text_input("請輸入公司 Email", placeholder="your.name@decathlon.com")
        submit_btn = st.form_submit_button("進入系統")
        
        if submit_btn:
            if email_input.strip().lower().endswith("@decathlon.com"):
                st.session_state.authenticated = True
                st.session_state.user_email = email_input.strip()
                st.success("✅ 登入成功！")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ 驗證失敗：只限 @decathlon.com 員工")
    st.stop()

# ==========================================
#  主程式 (已登入)
# ==========================================

# --- 側邊欄 (登出) ---
with st.sidebar:
    st.title("👤 用戶檔案")
    st.write(f"Email:\n**{st.session_state.user_email}**")
    st.divider()
    if st.button("👋 登出系統", type="secondary", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_email = ""
        st.rerun()

st.title("⏱️ Decathlon 智能打卡 (GAS版)")

# --- 步驟 1: 獲取 GPS ---
st.info("👇 請先點擊下方按鈕獲取位置")
location = streamlit_geolocation()
gps_loc = None

if location['latitude'] is not None:
    gps_loc = f"{location['latitude']},{location['longitude']}"
    st.success(f"✅ 成功鎖定座標: {gps_loc}")
else:
    st.caption("等待定位中... (如無反應請 Refresh)")

is_gps_ready = gps_loc is not None

# --- 步驟 2: 查詢狀態 & 決定下一步 ---
st.divider()

# 獲取香港時間
def get_hk_time():
    utc_now = datetime.utcnow()
    hk_now = utc_now + timedelta(hours=8)
    return hk_now.strftime("%Y-%m-%d %H:%M:%S")

# 透過 Google Script 讀取最後狀態
last_action = "讀取中..."
try:
    # 發送 GET 請求
    response = requests.get(SCRIPT_URL, params={"email": st.session_state.user_email})
    if response.status_code == 200:
        data = response.json()
        # 這裡對應 Google Script 回傳的 JSON key
        last_action = data.get("last_action", "無紀錄")
        if not last_action: last_action = "無紀錄"
    else:
        last_action = "連線錯誤"
except Exception as e:
    st.error(f"連線失敗: {e}")
    last_action = "未知"

# 邏輯判斷
next_action_map = {
    "無紀錄": "上班",
    "下班": "上班",
    "上班": "午飯開始",
    "午飯開始": "午飯結束",
    "午飯結束": "下班"
}
next_step = next_action_map.get(last_action, "上班")

# 顯示狀態
st.markdown(f"### 📋 上次狀態：{last_action}")

# --- 步驟 3: 打卡按鈕 ---
btn_label = f"👉 確認打卡：{next_step}"

if st.button(btn_label, type="primary", use_container_width=True, disabled=not is_gps_ready):
    try:
        with st.spinner(f"正在紀錄 {next_step}..."):
            now_time = get_hk_time()
            
            # 準備要傳送的資料 (JSON)
            payload = {
                "Email": st.session_state.user_email,
                "Action": next_step,
                "Time": now_time,
                "Location": gps_loc
            }
            
            # 發送 POST 請求寫入 Google Sheet
            # 使用 requests.post 並帶上 json=payload
            # 必須加上 allow_redirects=True 因為 Google Script 會轉址
            requests.post(SCRIPT_URL, json=payload)
            
            st.balloons()
            st.success(f"✅ 打卡成功! {next_step} @ {now_time}")
            time.sleep(2)
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ 寫入失敗: {e}")

# --- 手動修正區 ---
with st.expander("🛠️ 手動修正 / 補打卡"):
    st.warning("如需手動補打卡，請點擊下方按鈕：")
    col1, col2, col3, col4 = st.columns(4)
    manual_actions = ["上班", "午飯開始", "午飯結束", "下班"]
    for act in manual_actions:
        if col1.button(act, key=f"manual_{act}", disabled=not is_gps_ready):
             now_time = get_hk_time()
             payload = {
                "Email": st.session_state.user_email,
                "Action": act,
                "Time": now_time,
                "Location": gps_loc
             }
             requests.post(SCRIPT_URL, json=payload)
             st.success(f"已手動紀錄: {act}")
             time.sleep(1)
             st.rerun()
