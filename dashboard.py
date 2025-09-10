# C:\Users\Admin\AI_smartfarm\streamlit\dashboard.py
import json, time
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from paho.mqtt import client as mqtt

st.set_page_config(page_title="SmartFarm Live", layout="wide")

# ===== 기본값 =====
DEFAULT_BROKER = "192.168.14.12"   # 라즈베리 MQTT 브로커 IP
DEFAULT_PORT   = 1883
DEFAULT_PUB    = "smartfarm/esp32s3/cmd"
DEFAULT_SUB    = "smartfarm/esp32s3/telemetry"

# ===== MQTT 브리지 클래스 =====
class MqttBridge:
    def __init__(self, broker, port, pub, sub):
        self.broker, self.port, self.pub, self.sub = broker, port, pub, sub
        self.connected = False
        self.last_json = {}
        self.last_ts = None

        self.cli = mqtt.Client()
        self.cli.on_connect = self._on_connect
        self.cli.on_disconnect = self._on_disconnect
        self.cli.on_message = self._on_message

        self._connect()

    def _connect(self):
        try:
            self.cli.connect(self.broker, self.port, 60)
            self.cli.loop_start()
        except Exception as e:
            print("❌ MQTT connect error:", e)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            try:
                self.cli.subscribe(self.sub)
                print(f"✅ Subscribed to {self.sub}")
            except Exception as e:
                print("❌ Subscribe error:", e)
        else:
            self.connected = False
            print(f"❌ MQTT connect failed (rc={rc})")

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        print("⚠️ MQTT disconnected")

    def _on_message(self, client, userdata, msg):
        try:
            obj = json.loads(msg.payload.decode("utf-8", errors="ignore"))
            self.last_json = obj
            self.last_ts = time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print("❌ JSON parse error:", e)

    def publish_cmd(self, text):
        try:
            self.cli.publish(self.pub, text)
            return True
        except Exception as e:
            print("❌ Publish error:", e)
            return False

# ===== 캐시 (브로커 바뀌면 새 인스턴스 생성) =====
@st.cache_resource(show_spinner=False)
def get_bridge(broker, port, pub, sub):
    return MqttBridge(broker, port, pub, sub)

# ===== 사이드바 =====
st.sidebar.header("🔗 Connection")
broker = st.sidebar.text_input("MQTT Broker", value=DEFAULT_BROKER)
port   = st.sidebar.number_input("Port", value=DEFAULT_PORT, step=1)
pub    = st.sidebar.text_input("Publish Topic (commands)", value=DEFAULT_PUB)
sub    = st.sidebar.text_input("Subscribe Topic (telemetry)", value=DEFAULT_SUB)

bridge = get_bridge(broker, int(port), pub, sub)

# 자동 새로고침 (3초)
st_autorefresh(interval=3000, key="auto_refresh")

st.title("🌱 SmartFarm — Live Dashboard")

# ===== 상태 표시 =====
st.caption(f"Broker: **{broker}:{port}** | Pub: `{pub}` | Sub: `{sub}`")
st.markdown(
    f"**MQTT:** {'🟢 CONNECTED' if bridge.connected else '🔴 DISCONNECTED'}  "
    f"• Last update: `{bridge.last_ts or '-'}`"
)

# ===== 데이터 표시 =====
data = {
    "temp": bridge.last_json.get("temp"),
    "hum":  bridge.last_json.get("hum"),
    "soil": bridge.last_json.get("soil"),
    "lux":  bridge.last_json.get("lux"),
    "pump": bridge.last_json.get("pump"),
    "fan":  bridge.last_json.get("fan"),
    "led":  bridge.last_json.get("led"),
}

c1, c2, c3, c4 = st.columns(4)
c1.metric("🌡 Temp (°C)", f"{data['temp']:.1f}" if data["temp"] else "-")
c2.metric("💧 Hum  (%)",  f"{data['hum']:.1f}"  if data["hum"]  else "-")
c3.metric("🌱 Soil (%)",  f"{data['soil']:.1f}" if data["soil"] else "-")
c4.metric("☀️ Lux",       f"{data['lux']:.0f}"  if data["lux"]  else "-")

# ===== 액추에이터 제어 =====
st.subheader("⚙️ Actuators")
colA, colB, colC = st.columns(3)
with colA:
    st.write("💧 Pump")
    if st.button("Pump ON"):  bridge.publish_cmd("pump on")
    if st.button("Pump OFF"): bridge.publish_cmd("pump off")
with colB:
    st.write("🌀 Fan")
    if st.button("Fan ON"):   bridge.publish_cmd("fan on")
    if st.button("Fan OFF"):  bridge.publish_cmd("fan off")
with colC:
    st.write("💡 LED")
    if st.button("LED ON"):   bridge.publish_cmd("led on")
    if st.button("LED OFF"):  bridge.publish_cmd("led off")

# ===== 기타 명령 =====
st.subheader("📝 Commands")
col1, col2 = st.columns([1,2])
with col1:
    interval = st.number_input("interval (sec)", min_value=1, max_value=3600, value=5, step=1)
    if st.button("Apply interval"):
        bridge.publish_cmd(f"interval {interval}")
with col2:
    if st.button("Request status"):
        bridge.publish_cmd("status")

# ===== Raw JSON 보기 =====
with st.expander("📦 Raw JSON data"):
    st.code(json.dumps(bridge.last_json, indent=2, ensure_ascii=False) if bridge.last_json else "No data yet.")
