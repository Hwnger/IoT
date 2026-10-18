
import json
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

BROKER = "broker.emqx.io"
PORT = 1883
TOPIC = "ptit/iot/B23DCCN370/telemetry"

def on_connect(client, userdata, flags, reason_code, properties):
    print("MQTT connection:", reason_code)
    if reason_code == 0:
        client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        received_at = datetime.now(timezone.utc).isoformat()

        print({
            **data,
            "received_at": received_at
        })


    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        print("Invalid message:", e)

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="python-subscriber-iot-73921"
)
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.loop_forever()
