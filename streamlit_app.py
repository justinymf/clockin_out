import streamlit as st
from pyairtable import Api
from datetime import datetime
import time
from streamlit_geolocation import streamlit_geolocation

# --- 頁面設定 ---
st.set_page_config(page_title="Decathlon Clock-In", page_icon="⏱️")
st.title("⏱️ Decathlon 員工打卡 (Airtable版)")

# --- 1. 連接 Airtable ---
try:
    # 直接從 Secrets 讀取你剛才設定的 Token
    api_key = st.secrets["airtable"]["api_key"]
    base_id = st.secrets["airtable"]["base_id"]
    table_id = st.secrets["airtable"]["table_id"]
    
    api = Api(api_key)
    table = api.table(base_id, table_id)
except Exception as e:
    st.error("⚠️ Secrets 設定未完成，請檢查 Streamlit Cloud Settings！")
    st.stop()

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

# --- 3. 獲取 GPS ---
st.write(f"👤 當前用戶: **{st.session_state.user_email}**")
st.info("👇 請點擊下方按鈕獲取位置")

location = streamlit_geolocation()
gps_loc = None

if location['latitude'] is not None:
    gps_loc = f"{location['latitude']},{location['longitude']}"
    st.success(f"✅ 成功鎖定座標: {gps_loc}")
else:
    st.caption("等待定位中...")

is_gps_ready = gps_loc is not None

# --- 4. 打卡動作 ---
st.divider()
st.markdown("### 🎬 步驟 2: 選擇動作")

col1, col2 = st.columns(2)
col3, col4 = st.columns(2)
actions = {"上班": col1, "午飯開始": col2, "午飯結束": col3, "下班": col4}

for action_name, col in actions.items():
    # 只有 GPS 準備好，按鈕才可用
    if col.button(action_name, use_container_width=True, disabled=not is_gps_ready):
        try:
            with st.spinner("正在寫入 Airtable..."):
                now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 寫入資料
                table.create({
                    "Email": st.session_state.user_email,
                    "Action": action_name,
                    "Time": now_time,
                    "Location": gps_loc
                })
                
                st.success(f"✅ 打卡成功! {action_name} @ {now_time}")
                st.balloons()
                
        except Exception as e:
            st.error(f"❌ 寫入失敗: {e}")
            st.info("💡 請檢查 Airtable 的欄位名稱是否正確 (Email, Action, Time, Location)")

# --- 5. 顯示紀錄 ---
st.divider()
st.markdown("### 📋 最近紀錄")
try:
    records = table.all(max_records=5, sort=["Time"])
    data = [r['fields'] for r in records]
    if data:
        st.dataframe(data, use_container_width=True)
    else:
        st.info("暫時未有紀錄")
except:
    st.caption("讀取紀錄時發生輕微錯誤")
