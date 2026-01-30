import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import time
from streamlit_geolocation import streamlit_geolocation
import pandas as pd

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
        submit_btn = st.form_submit_button("進入系統", use_container_width=True)
        
        if submit_btn:
            with st.status("🔐 正在驗證身份...", expanded=True) as status:
                time.sleep(0.5)
                if email_input.strip().lower().endswith("@decathlon.com"):
                    st.session_state.authenticated = True
                    st.session_state.user_email = email_input.strip()
                    status.update(label="✅ 登入成功！", state="complete", expanded=False)
                    time.sleep(0.5)
                    st.rerun()
                else:
                    status.update(label="❌ 驗證失敗", state="error", expanded=False)
                    st.error("❌ 只限 @decathlon.com 員工")
    st.stop()

# ==========================================
#  主程式 (已登入)
# ==========================================

with st.sidebar:
    st.title("👤 用戶檔案")
    st.write(f"Email:\n**{st.session_state.user_email}**")
    st.divider()
    if st.button("👋 登出系統", type="secondary", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_email = ""
        st.rerun()

st.title("⏱️ Decathlon 智能打卡")

if 'first_load' not in st.session_state:
    st.toast(f"歡迎回來，{st.session_state.user_email}", icon="👋")
    st.session_state.first_load = True

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

def get_hk_time():
    utc_now = datetime.utcnow()
    hk_now = utc_now + timedelta(hours=8)
    return hk_now.strftime("%Y-%m-%d %H:%M:%S")

# 變數初始化
last_action = "讀取中..."
recent_records = []  # 準備裝紀錄

try:
    # 這裡顯示狀態
    status_text = st.empty()
    status_text.caption("🔄 正在同步雲端數據...")
    
    # 呼叫 Google Script
    response = requests.get(SCRIPT_URL, params={"email": st.session_state.user_email})
    
    if response.status_code == 200:
        data = response.json()
        
        # 獲取 Last Action
        last_action = data.get("last_action", "無紀錄")
        if not last_action: last_action = "無紀錄"
        
        # 獲取最近紀錄 (這是新加的)
        recent_records = data.get("recent_records", [])
        
        status_text.empty()
    else:
        last_action = "連線錯誤"
        status_text.error("連線不穩定")
except Exception as e:
    st.error(f"連線失敗: {e}")
    last_action = "未知"

# 邏輯判斷
next_action_map = {
    "無紀錄": "上班", "下班": "上班",
    "上班": "午飯開始", "午飯開始": "午飯結束", "午飯結束": "下班"
}
next_step = next_action_map.get(last_action, "上班")

st.markdown(f"### 📋 上次狀態：{last_action}")

# --- 步驟 3: 打卡按鈕 ---
btn_label = f"👉 確認打卡：{next_step}"

if st.button(btn_label, type="primary", use_container_width=True, disabled=not is_gps_ready):
    with st.status(f"🚀 正在提交【{next_step}】...", expanded=True) as status:
        now_time = get_hk_time()
        payload = {
            "Email": st.session_state.user_email,
            "Action": next_step,
            "Time": now_time,
            "Location": gps_loc
        }
        try:
            st.write("📤 正在寫入 Google Sheet...")
            requests.post(SCRIPT_URL, json=payload)
            status.update(label=f"✅ 打卡完成：{next_step}", state="complete", expanded=False)
            st.balloons()
            time.sleep(2)
            st.rerun()
        except Exception as e:
            status.update(label="❌ 連線失敗", state="error")
            st.error(f"網絡錯誤: {e}")

# --- 手動修正區 ---
with st.expander("🛠️ 手動修正 / 補打卡"):
    col1, col2, col3, col4 = st.columns(4)
    manual_actions = ["上班", "午飯開始", "午飯結束", "下班"]
    for act in manual_actions:
        if col1.button(act, key=f"manual_{act}", disabled=not is_gps_ready):
             with st.status(f"🛠️ 補打卡：{act}...", expanded=True) as status:
                 now_time = get_hk_time()
                 requests.post(SCRIPT_URL, json={
                    "Email": st.session_state.user_email,
                    "Action": act,
                    "Time": now_time,
                    "Location": gps_loc
                 })
                 status.update(label="✅ 成功", state="complete", expanded=False)
                 time.sleep(1)
                 st.rerun()

# --- 步驟 4: 顯示最近紀錄 (新加部分) ---
st.divider()
st.subheader("📋 最近 5 次打卡紀錄")

# 確保 recent_records 唔係 None 
if recent_records and len(recent_records) > 0:
    df = pd.DataFrame(recent_records)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("暫無紀錄 (新用戶或未有打卡資料)")
