import os
import numpy as np
import pandas as pd

from dotenv import load_dotenv
from sklearn.preprocessing import MinMaxScaler
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


load_dotenv()

URL = os.getenv("INFLUX_URL")
ORG = os.getenv("INFLUX_ORG")
BUCKET = os.getenv("INFLUX_BUCKET")
TOKEN = os.getenv("INFLUX_TOKEN")

if not all([URL, ORG, BUCKET, TOKEN]):
    raise RuntimeError("Thieu cau hinh InfluxDB trong file .env")

MEASUREMENT = "environment"
OUTPUT_MEASUREMENT = "environment_processed"
DEVICE_ID = "ESP32_01"

SENSORS = ["temperature", "humidity", "light"]
INT_SENSORS = {"light"}         
WINDOW = "1min"
ROLLING_WINDOW = 5


def read_data(client):
    query = f'''
    from(bucket: "{BUCKET}")
      |> range(start: -24h)
      |> filter(fn: (r) =>
          r._measurement == "{MEASUREMENT}" and
          r.device_id == "{DEVICE_ID}"
      )
      |> filter(fn: (r) =>
          r._field == "temperature" or
          r._field == "humidity" or
          r._field == "light"
      )
      |> pivot(
          rowKey: ["_time", "device_id"],
          columnKey: ["_field"],
          valueColumn: "_value"
      )
      |> keep(columns: [
          "_time", "device_id",
          "temperature", "humidity", "light"
      ])
      |> sort(columns: ["_time"])
    '''

    result = client.query_api().query_data_frame(
        query=query, org=ORG
    )

    if isinstance(result, list):
        frames = [df for df in result if not df.empty]
        if not frames:
            return pd.DataFrame()
        df = pd.concat(frames, ignore_index=True)
    else:
        df = result

    if df.empty:
        return df

    df = df.loc[:, [
        c for c in ["_time", "device_id"] + SENSORS
        if c in df.columns
    ]].copy()

    for col in SENSORS:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in INT_SENSORS:
        df[col] = df[col].round().astype("Int64")

    df["_time"] = pd.to_datetime(df["_time"], utc=True)
    df = df.dropna(subset=["_time"])
    df = df.sort_values("_time")
    df = df.drop_duplicates(
        subset=["_time", "device_id"], keep="last"
    )

    return df


def clean_outliers(df):
    df = df.copy()
    flags = {}

    for col in SENSORS:
        values = df[col]
        valid = values.dropna()

        if len(valid) < 4:
            flags[col] = pd.Series(False, index=df.index)
            continue

        q1 = valid.quantile(0.25)
        q3 = valid.quantile(0.75)
        iqr = q3 - q1

        if iqr > 0:
            iqr_outlier = (
                (values < q1 - 1.5 * iqr) |
                (values > q3 + 1.5 * iqr)
            )
        else:
            iqr_outlier = pd.Series(False, index=df.index)

        mean = valid.mean()
        std = valid.std(ddof=0)

        if std > 0:
            zscore = (values - mean).abs() / std
            z_outlier = zscore > 3
        else:
            z_outlier = pd.Series(False, index=df.index)

        flags[col] = (
            iqr_outlier.fillna(False) |
            z_outlier.fillna(False)
        )

        df.loc[flags[col], col] = np.nan

    for col in INT_SENSORS:
        df[col] = df[col].astype("Int64")

    for col in SENSORS:
        df[col + "_outlier"] = flags[col].astype(int)

    return df


def resample_data(df):
    df = df.copy()
    df = df.set_index("_time").sort_index()

    sampled = df[SENSORS].resample(WINDOW).mean()

    sampled[SENSORS] = sampled[SENSORS].interpolate(
        method="time",
        limit=2,
        limit_area="inside"
    )

    sampled = sampled.dropna(subset=SENSORS, how="any")

    for col in INT_SENSORS:
        sampled[col] = sampled[col].round().astype("Int64")

    return sampled

def create_features(df):
    df = df.copy()

    for col in SENSORS:
        df[col + "_rolling_mean"] = (
            df[col].rolling(
                window=ROLLING_WINDOW,
                min_periods=1
            ).mean()
        )

        df[col + "_delta"] = df[col].diff().fillna(0)

    scaler = MinMaxScaler()
    normalized = scaler.fit_transform(df[SENSORS])

    for i, col in enumerate(SENSORS):
        df[col + "_normalized"] = normalized[:, i]

    return df


def save_data(client, df):
    write_api = client.write_api(
        write_options=SYNCHRONOUS
    )

    count = 0

    try:
        for timestamp, row in df.iterrows():
            point = (
                Point(OUTPUT_MEASUREMENT)
                .tag("device_id", DEVICE_ID)
                .time(timestamp.to_pydatetime())
            )

            for col in df.columns:
                value = row[col]

                if pd.isna(value) or not np.isfinite(value):
                    continue

                if col in INT_SENSORS:
                    point = point.field(col, int(value))
                else:
                    point = point.field(col, float(value))

            write_api.write(
                bucket=BUCKET,
                org=ORG,
                record=point
            )
            count += 1
    finally:
        write_api.close()

    return count


def main():
    with InfluxDBClient(
        url=URL, token=TOKEN, org=ORG
    ) as client:

        raw = read_data(client)

        if raw.empty:
            print("Khong co du lieu trong 24 gio gan nhat.")
            print("Hay chay Publisher va Subscriber truoc.")
            return

        print("So ban ghi goc:", len(raw))

        cleaned = clean_outliers(raw)

        for col in SENSORS:
            n = int(cleaned[col + "_outlier"].sum())
            print(f"{col}: phat hien {n} diem ngoai le")

        sampled = resample_data(cleaned)

        if sampled.empty:
            print("Khong du du lieu sau khi resampling.")
            return

        print("So cua so sau resampling:", len(sampled))

        featured = create_features(sampled)

        print("\nDu lieu sau tien xu ly:")
        print(featured.tail())

        saved = save_data(client, featured)

        print("\nDa ghi", saved, "ban ghi vao", OUTPUT_MEASUREMENT)


if __name__ == "__main__":
    main()