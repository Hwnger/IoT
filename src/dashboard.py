
import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
from streamlit_autorefresh import st_autorefresh

load_dotenv()

URL = os.getenv("INFLUX_URL")
ORG = os.getenv("INFLUX_ORG")
BUCKET = os.getenv("INFLUX_BUCKET")
TOKEN = os.getenv("INFLUX_TOKEN")

DEVICE = "ESP32_01"
RAW_MEASUREMENT = "environment"
PROCESSED_MEASUREMENT = "environment_processed"

SENSORS = {
    "temperature": ("Nhiet do", "°C"),
    "humidity": ("Do am", "%"),
    "light": ("Anh sang", "gia tri cam bien")
}

st.set_page_config(
    page_title="IoT Monitoring",
    page_icon="📡",
    layout="wide"
)

st.title("📡 IoT Monitoring Dashboard")
st.caption("Du lieu MQTT va InfluxDB 2.x")

if not all([URL, ORG, BUCKET, TOKEN]):
    st.error("Thieu cau hinh InfluxDB trong file .env")
    st.stop()

st.sidebar.header("Cau hinh")

period = st.sidebar.selectbox(
    "Khoang thoi gian",
    ["15m", "1h", "6h", "24h", "7d"],
    index=1
)

refresh_seconds = st.sidebar.selectbox(
    "Tu dong lam moi (giay)",
    [5, 10, 30, 60],
    index=0
)

show_processed = st.sidebar.checkbox(
    "Hien thi du lieu da xu ly",
    value=True
)

st_autorefresh(
    interval=refresh_seconds * 1000,
    key="iot_dashboard_refresh"
)


def query_measurement(client, measurement, period):
    query = f'''
    from(bucket: "{BUCKET}")
      |> range(start: -{period})
      |> filter(fn: (r) =>
          r._measurement == "{measurement}" and
          r.device_id == "{DEVICE}"
      )
      |> filter(fn: (r) =>
          r._field == "temperature" or
          r._field == "humidity" or
          r._field == "light" or
          r._field == "temperature_rolling_mean" or
          r._field == "humidity_rolling_mean" or
          r._field == "light_rolling_mean" or
          r._field == "temperature_delta" or
          r._field == "humidity_delta" or
          r._field == "light_delta" or
          r._field == "temperature_normalized" or
          r._field == "humidity_normalized" or
          r._field == "light_normalized"
      )
      |> pivot(
          rowKey: ["_time", "device_id"],
          columnKey: ["_field"],
          valueColumn: "_value"
      )
      |> keep(columns: [
          "_time", "device_id",
          "temperature", "humidity", "light",
          "temperature_rolling_mean",
          "humidity_rolling_mean",
          "light_rolling_mean",
          "temperature_delta",
          "humidity_delta",
          "light_delta",
          "temperature_normalized",
          "humidity_normalized",
          "light_normalized"
      ])
      |> sort(columns: ["_time"])
    '''

    result = client.query_api().query_data_frame(
        query=query, org=ORG
    )

    if isinstance(result, list):
        frames = [x for x in result if not x.empty]
        if not frames:
            return pd.DataFrame()
        df = pd.concat(frames, ignore_index=True)
    else:
        df = result

    if df.empty or "_time" not in df.columns:
        return pd.DataFrame()

    df = df.loc[:, ~df.columns.duplicated()].copy()
    df["_time"] = pd.to_datetime(df["_time"], utc=True)

    for col in SENSORS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.sort_values("_time")


def anomaly_report(df, columns):
    rows = []

    for col in columns:
        if col not in df.columns:
            continue

        values = pd.to_numeric(df[col], errors="coerce").dropna()

        if len(values) < 4:
            continue

        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1

        if iqr > 0:
            iqr_mask = (
                (values < q1 - 1.5 * iqr) |
                (values > q3 + 1.5 * iqr)
            )
        else:
            iqr_mask = pd.Series(False, index=values.index)

        std = values.std(ddof=0)

        if std > 0:
            z_mask = ((values - values.mean()).abs() / std) > 3
        else:
            z_mask = pd.Series(False, index=values.index)

        rows.append({
            "Cam bien": col,
            "So mau": len(values),
            "Outlier IQR": int(iqr_mask.sum()),
            "Outlier Z-score": int(z_mask.sum())
        })

    return pd.DataFrame(rows)


try:
    with InfluxDBClient(
        url=URL, token=TOKEN, org=ORG, timeout=15000
    ) as client:
        raw = query_measurement(client, RAW_MEASUREMENT, period)

        processed = (
            query_measurement(client, PROCESSED_MEASUREMENT, period)
            if show_processed else pd.DataFrame()
        )

except Exception as e:
    st.error(f"Khong doc duoc InfluxDB: {e}")
    st.stop()

if raw.empty:
    st.warning(
        "Chua co du lieu goc trong khoang thoi gian nay. "
        "Hay kiem tra Publisher, Subscriber va bucket."
    )
    st.stop()

latest_time = raw["_time"].max()
now_utc = pd.Timestamp.now(tz="UTC")
freshness = max(0.0, (now_utc - latest_time).total_seconds())

latest = raw.sort_values("_time").iloc[-1]

st.subheader("Tong quan")

c1, c2, c3, c4 = st.columns(4)

c1.metric("So ban ghi goc", f"{len(raw):,}")
c2.metric(
    "Nhiet do moi nhat",
    f"{latest['temperature']:.2f} °C"
    if pd.notna(latest.get("temperature", np.nan)) else "N/A"
)
c3.metric(
    "Do am moi nhat",
    f"{latest['humidity']:.2f}%"
    if pd.notna(latest.get("humidity", np.nan)) else "N/A"
)
c4.metric("Do tuoi du lieu (giay)", f"{freshness:.1f}")

if freshness > refresh_seconds * 3:
    st.warning(
        "Du lieu co the dang bi cham hoac Publisher/Subscriber "
        "khong con hoat dong."
    )

st.caption(
    f"Ban ghi moi nhat: {latest_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
)

st.subheader("Du lieu cam bien theo thoi gian")

for col, (label, unit) in SENSORS.items():
    if col not in raw.columns:
        continue

    chart_df = raw[["_time", col]].dropna()

    if chart_df.empty:
        st.info(f"Chua co du lieu cho {label}.")
        continue

    fig = px.line(
        chart_df,
        x="_time",
        y=col,
        title=f"{label} ({unit})",
        labels={"_time": "Thoi gian", col: label}
    )

    fig.update_layout(
        hovermode="x unified",
        margin=dict(l=10, r=10, t=50, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

if show_processed:
    st.subheader("Du lieu da xu ly")

    if processed.empty:
        st.info(
            "Chua co du lieu da xu ly trong khoang thoi gian nay. "
            "Hay chay preprocess.py."
        )
    else:
        processed_columns = [
            col for col in [
                "temperature",
                "temperature_rolling_mean",
                "humidity",
                "humidity_rolling_mean",
                "light",
                "light_rolling_mean"
            ]
            if col in processed.columns
        ]

        for col in processed_columns:
            fig = px.line(
                processed,
                x="_time",
                y=col,
                title=col
            )
            st.plotly_chart(fig, use_container_width=True)

        normalized_cols = [
            c for c in [
                "temperature_normalized",
                "humidity_normalized",
                "light_normalized"
            ]
            if c in processed.columns
        ]

        if normalized_cols:
            st.markdown("**Du lieu chuan hoa (0–1)**")
            fig = px.line(
                processed,
                x="_time",
                y=normalized_cols
            )
            st.plotly_chart(fig, use_container_width=True)

st.subheader("Thong ke mo ta")

stats_rows = []

for col, (label, unit) in SENSORS.items():
    if col not in raw.columns:
        continue

    values = raw[col].dropna()

    if values.empty:
        continue

    stats_rows.append({
        "Cam bien": label,
        "Don vi": unit,
        "Trung binh": values.mean(),
        "Nho nhat": values.min(),
        "Lon nhat": values.max(),
        "Do lech chuan": values.std()
    })

if stats_rows:
    st.dataframe(
        pd.DataFrame(stats_rows).round(3),
        use_container_width=True,
        hide_index=True
    )

st.subheader("Phat hien gia tri bat thuong")

st.caption(
    "IQR va Z-score duoc tinh tren khoang du lieu dang chon. "
    "Diem nghi ngo khong dong nghia voi loi cam bien."
)

report = anomaly_report(raw, list(SENSORS.keys()))

if report.empty:
    st.info("Chua du du lieu de tinh IQR/Z-score.")
else:
    st.dataframe(report, use_container_width=True, hide_index=True)

st.subheader("Ban ghi gan nhat")

visible_columns = [
    c for c in [
        "_time", "temperature", "humidity", "light"
    ] if c in raw.columns
]

st.dataframe(
    raw[visible_columns].tail(20).sort_values(
        "_time", ascending=False
    ),
    use_container_width=True,
    hide_index=True
)

st.caption(
    "Dashboard tu lam moi theo chu ky da chon. "
    "Do tuoi du lieu la thoi gian tu timestamp ban tin den hien tai, "
    "khong phai phep do chinh xac thoi gian MQTT-to-database."
)
