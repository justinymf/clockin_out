import streamlit as st
from pyairtable import Api
from datetime import datetime, timedelta
import time
from streamlit_geolocation import streamlit_geolocation

# --- 1. 基礎設定 ---
st.set_page_config(page_title="Decathlon Smart Clock-In", page_icon="⏱️")

# --- 2. 連接 Airtable ---
try:
    api_key = st.secrets["airtable"]["api_key"]
    base_id = st.secrets["airtable"]["base_id"]
    table_id = st.secrets["airtable"]["table_id"]
    api = Api(api_key)
    table = api.table(base_id, table_id)
except:
    st.error("⚠️ Secrets 設定錯誤，請檢查 Streamlit Cloud！")
    st.stop()

# --- 3. 身份驗證初始化 ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""

# ==========================================
#  第一關：檢查登入狀態
#  (如果未登入，顯示登入框後直接 Stop，不執行下面代碼)
# ==========================================
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
    
    st.stop()  # <--- 關鍵！未登入就停在這裡，防止下面代碼亂跑

# ==========================================
#  第二關：主程式 (只有已登入才會執行到這裡)
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

# --- 主標題 ---
st.title("⏱️ Decathlon 智能打卡")

# --- 步驟 1: 獲取 GPS ---
st.info("👇 請先點擊下方按鈕獲取位置")
location = streamlit_geolocation()
gps_loc = None

if location['latitude'] is not None:
    gps_loc = f"{location['latitude']},{location['longitude']}"
    st.success(f"✅ 成功鎖定座標: {gps_loc}")
else:
    st.caption("等待定位中... (如果按鈕無反應，請 Refresh 網頁)")

is_gps_ready = gps_loc is not None

# --- 步驟 2: 查詢狀態 & 決定下一步 ---
st.divider()

# 獲取香港時間
def get_hk_time():
    utc_now = datetime.utcnow()
    hk_now = utc_now + timedelta(hours=8)
    return hk_now.strftime("%Y-%m-%d %H:%M:%S")

# 讀取 Airtable 最後紀錄
last_action = "未知"
try:
    records = table.all(formula=f"{{Email}}='{st.session_state.user_email}'", sort=["-Time"], max_records=1)
    if records:
        last_action = records[0]['fields'].get('Action', '未知')
    else:
        last_action = "無紀錄"
except Exception as e:
    st.error(f"連線 Airtable 失敗: {e}")

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

# --- 步驟 3: 打卡按鈕 (保證顯示) ---
# 這個按鈕現在位於最外層，不會被隱藏
btn_label = f"👉 確認打卡：{next_step}"
if st.button(btn_label, type="primary", use_container_width=True, disabled=not is_gps_ready):
    try:
        with st.spinner(f"正在紀錄 {next_step}..."):
            now_time = get_hk_time()
            table.create({
                "Email": st.session_state.user_email,
                "Action": next_step,
                "Time": now_time,
                "Location": gps_loc
            })
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
             table.create({
                "Email": st.session_state.user_email,
                "Action": act,
                "Time": get_hk_time(),
                "Location": gps_loc
             })
             st.success(f"已手動紀錄: {act}")
             time.sleep(1)
             st.rerun()

# --- 顯示紀錄 ---
st.divider()
st.subheader("📋 最近紀錄")
try:
    user_records = table.all(formula=f"{{Email}}='{st.session_state.user_email}'", sort=["-Time"], max_records=5)
    data = [r['fields'] for r in user_records]
    if data:
        st.dataframe(data, use_container_width=True)
except:
    pass
