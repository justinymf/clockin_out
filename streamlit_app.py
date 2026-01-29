import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime

# --- GPS 獲取組件 (加強版) ---
def get_gps_location():
    js_code = """
    <script>
    function getLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const coords = position.coords.latitude + "," + position.coords.longitude;
                    window.parent.postMessage({type: 'streamlit:setComponentValue', value: coords}, '*');
                },
                (error) => {
                    window.parent.postMessage({type: 'streamlit:setComponentValue', value: "Error: " + error.message}, '*');
                }
            );
        }
    }
    getLocation();
    </script>
    """
    components.html(js_code, height=0)

st.title("🕒 Decathlon 安全打卡系統")

# --- 第一步：自動獲取 GPS ---
if st.button("📍 點擊獲取當前位置"):
    get_gps_location()
    st.info("正在連線衛星，請稍候...")

# 關鍵位：使用 disabled=True 限制用戶輸入
# 用戶只能透過上面的按鈕來填入內容，唔可以自己打字
current_loc = st.text_input(
    "系統偵測位置 (唯讀)", 
    key="location_val", 
    disabled=True, 
    placeholder="請先點擊上方按鈕獲取定位"
)

st.divider()

# --- 第二步：打卡動作 (加入防呆機制) ---
st.markdown("### 選擇打卡動作")

# 如果未有 GPS 數據，或者出現 Error，就唔俾打卡
is_gps_ready = current_loc and "Error" not in current_loc

col1, col2 = st.columns(2)
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 使用 disabled 參數連動 GPS 狀態
if col1.button("🎬 上班", use_container_width=True, disabled=not is_gps_ready):
    st.success(f"【上班】紀錄成功！\n時間：{now}\n位置：{current_loc}")

if col2.button("🏠 下班", use_container_width=True, disabled=not is_gps_ready):
    st.success(f"【下班】紀錄成功！\n時間：{now}\n位置：{current_loc}")

if not is_gps_ready:
    st.warning("⚠️ 必須成功獲取 GPS 位置後才能進行打卡。")