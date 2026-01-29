import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
import time

# --- 頁面設定 ---
st.set_page_config(page_title="Decathlon Clock-In", page_icon="⏱️")
st.title("⏱️ Decathlon 員工打卡系統")

# --- 1. JavaScript GPS 獲取模組 ---
def get_gps_location():
    js_code = """
    <script>
    function getLocation() {
        if (!navigator.geolocation) {
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: "Error: 瀏覽器不支援"}, '*');
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const coords = pos.coords.latitude + "," + pos.coords.longitude;
                window.parent.postMessage({type: 'streamlit:setComponentValue', value: coords}, '*');
            },
            (err) => {
                window.parent.postMessage({type: 'streamlit:setComponentValue', value: "Error: " + err.message}, '*');
            },
            {enableHighAccuracy: true, timeout: 10000, maximumAge: 0}
        );
    }
    getLocation();
    </script>
    """
    components.html(js_code, height=0)

# --- 2. 身份驗證 (Session State) ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""

# --- 登入介面 ---
if not st.session_state.authenticated:
    st.subheader("🔐 請先登入")
    email_input = st.text_input("輸入 Decathlon Email", placeholder="your.name@decathlon.com")
    
    if st.button("進入系統"):
        if email_input.strip().lower().endswith("@decathlon.com"):
            st.session_state.authenticated = True
            st.session_state.user_email = email_input.strip()
            st.success("登入成功！")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ 只限 @decathlon.com 員工使用")
    st.stop()  # 停止執行下面的代碼直到登入

# --- 3. 打卡主畫面 ---
st.write(f"👤 當前用戶: **{st.session_state.user_email}**")

if st.button("📍 點擊獲取 GPS 位置"):
    get_gps_location()
    st.info("正在連線衛星，請稍候...")

# 接收 GPS 數據 (唯讀)
gps_loc = st.text_input("📍 GPS 座標", key="gps_val", disabled=True, placeholder="等待定位...")

# 檢查 GPS 是否有效
is_gps_ready = gps_loc and "Error" not in gps_loc

# --- 4. Google Sheets 連接與寫入 ---
# 建立連線
conn = st.connection("gsheets", type=GSheetsConnection)

st.divider()
st.subheader("選擇打卡動作")

col1, col2 = st.columns(2)
col3, col4 = st.columns(2)

# 定義按鈕邏輯
actions = {
    "上班": col1,
    "午飯開始": col2,
    "午飯結束": col3,
    "下班": col4
}

for action_name, col in actions.items():
    # 按鈕狀態依賴 GPS
    if col.button(f"{action_name}", use_container_width=True, disabled=not is_gps_ready):
        try:
            with st.spinner(f"正在紀錄 {action_name}..."):
                # 1. 讀取現有數據 (ttl=0 確保不讀取緩存)
                existing_data = conn.read(worksheet="Sheet1", usecols=list(range(4)), ttl=0)
                
                # 2. 準備新的一行
                now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_row = pd.DataFrame([{
                    "Email": st.session_state.user_email,
                    "Action": action_name,
                    "Time": now_time,
                    "Location": gps_loc
                }])
                
                # 3. 合併並寫回
                updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                
                st.success(f"✅ 成功打卡：{action_name} @ {now_time}")
                st.balloons()
                
        except Exception as e:
            st.error(f"❌ 寫入失敗，請檢查網絡或 Google Sheet 設定。\n錯誤訊息: {e}")

# 顯示最近 5 條紀錄 (唯讀)
st.divider()
st.markdown("### 📋 最近紀錄")
try:
    df_show = conn.read(worksheet="Sheet1", usecols=list(range(4)), ttl=5)
    # 只顯示該用戶的紀錄
    user_records = df_show[df_show["Email"] == st.session_state.user_email].tail(5)
    st.dataframe(user_records, use_container_width=True, hide_index=True)
except:
    st.caption("暫時無法讀取紀錄")

# 登出按鈕
if st.button("登出"):
    st.session_state.authenticated = False
    st.rerun()
