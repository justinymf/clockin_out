import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
import time

# --- 頁面設定 ---
st.set_page_config(page_title="Decathlon Clock-In", page_icon="⏱️")
st.title("⏱️ Decathlon 員工打卡系統")

# --- 1. JavaScript GPS 獲取模組 (修復版：快速定位 + 狀態顯示) ---
def get_gps_location():
    js_code = """
    <div id="status" style="font-family: sans-serif; font-size: 14px; color: #31333F; padding: 5px; border: 1px solid #ddd; border-radius: 5px; background-color: #f0f2f6;">
        📡 準備獲取位置...
    </div>
    <script>
    function getLocation() {
        const statusDiv = document.getElementById("status");
        
        if (!navigator.geolocation) {
            statusDiv.innerHTML = "❌ 瀏覽器不支援 Geolocation";
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: "Error: 不支援"}, '*');
            return;
        }

        statusDiv.innerHTML = "📡 正在定位 (Wi-Fi/基站模式)...";

        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const coords = pos.coords.latitude + "," + pos.coords.longitude;
                statusDiv.innerHTML = "✅ 成功! 座標: " + coords;
                statusDiv.style.backgroundColor = "#d4edda"; // 綠色背景
                window.parent.postMessage({type: 'streamlit:setComponentValue', value: coords}, '*');
            },
            (err) => {
                let msg = "";
                switch(err.code) {
                    case 1: msg = "用戶拒絕權限 (User Denied)"; break;
                    case 2: msg = "無法偵測位置 (Unavailable)"; break;
                    case 3: msg = "連線逾時 (Timeout)"; break;
                    default: msg = "未知錯誤"; break;
                }
                statusDiv.innerHTML = "❌ 失敗: " + msg;
                statusDiv.style.backgroundColor = "#f8d7da"; // 紅色背景
                window.parent.postMessage({type: 'streamlit:setComponentValue', value: "Error: " + msg}, '*');
            },
            // 關鍵修正：關閉高精確度以避免 Timeout，改用 Wi-Fi 定位，速度快
            {enableHighAccuracy: false, timeout: 15000, maximumAge: 0}
        );
    }
    getLocation();
    </script>
    """
    # height=80 讓你可以看到上面的狀態文字 div
    components.html(js_code, height=80)

# --- 2. 身份驗證 ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""

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
    st.stop()

# --- 3. 打卡主畫面 ---
st.write(f"👤 當前用戶: **{st.session_state.user_email}**")

st.markdown("### 📍 步驟 1: 獲取位置")
if st.button("點擊獲取 GPS"):
    get_gps_location()

# 接收 GPS 數據
gps_loc = st.text_input("座標結果", key="gps_val", disabled=True, placeholder="等待定位數據...")

# 檢查 GPS 是否有效
is_gps_ready = gps_loc and "Error" not in gps_loc

# --- 4. Google Sheets 連接與寫入 ---
# 注意：這裡會自動尋找 st.secrets["connections"]["gsheets"]
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("⚠️ 無法連接 Google Sheet，請檢查 Secrets 設定。")
    conn = None

st.divider()
st.markdown("### 🎬 步驟 2: 選擇打卡動作")

col1, col2 = st.columns(2)
col3, col4 = st.columns(2)

actions = {
    "上班": col1, "午飯開始": col2, "午飯結束": col3, "下班": col4
}

for action_name, col in actions.items():
    # 如果 GPS 未準備好，按鈕會變灰 (disabled)
    if col.button(f"{action_name}", use_container_width=True, disabled=not is_gps_ready):
        if conn:
            try:
                with st.spinner(f"正在紀錄 {action_name}..."):
                    # 1. 讀取 (ttl=0 防止緩存)
                    existing_data = conn.read(worksheet="Sheet1", usecols=list(range(4)), ttl=0)
                    
                    # 2. 寫入
                    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    new_row = pd.DataFrame([{
                        "Email": st.session_state.user_email,
                        "Action": action_name,
                        "Time": now_time,
                        "Location": gps_loc
                    }])
                    
                    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=updated_df)
                    
                    st.success(f"✅ 打卡成功！{action_name} @ {now_time}")
                    st.balloons()
            except Exception as e:
                st.error(f"❌ 寫入失敗: {e}")
        else:
            st.error("系統錯誤：資料庫未連接")

# --- 5. 顯示紀錄 ---
st.divider()
st.markdown("### 📋 最近紀錄 (唯讀)")
if conn:
    try:
        df_show = conn.read(worksheet="Sheet1", usecols=list(range(4)), ttl=5)
        # 只顯示自己的紀錄
        user_records = df_show[df_show["Email"] == st.session_state.user_email].tail(5)
        st.dataframe(user_records, use_container_width=True, hide_index=True)
    except:
        st.caption("暫時沒有紀錄")
