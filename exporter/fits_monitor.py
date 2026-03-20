import os
import time
import random
from astropy.io import fits as astropy_fits
from prometheus_client import start_http_server, Gauge

DATA_DIR = "../data/raw_fits"

# --- Mevcut metrikler ---
fits_files_total        = Gauge("dag_fits_files_total",            "Total FITS files")
fits_data_bytes         = Gauge("dag_fits_data_bytes_total",       "Total FITS data size in bytes")
last_fits_timestamp     = Gauge("dag_last_fits_timestamp_seconds", "Last FITS file modification time (unix)")

# --- Validasyon ---
fits_valid_total        = Gauge("dag_fits_valid_total",            "Number of valid FITS files")
fits_invalid_total      = Gauge("dag_fits_invalid_total",          "Number of invalid/corrupted FITS files")

# --- Sky metrikleri ---
target_ra               = Gauge("dag_target_ra",                   "Current observation target RA (degrees)")
target_dec              = Gauge("dag_target_dec",                  "Current observation target DEC (degrees)")

# --- Target observation sayacı (label'lı) ---
target_observation      = Gauge("dag_target_observation_total",    "Total observations per target", ["object"])

# --- Hava durumu: 0=CLEAR, 1=CLOUDY, 2=WINDY ---
weather_condition       = Gauge("dag_weather_condition",           "Simulated weather (0=CLEAR,1=CLOUDY,2=WINDY)")
weather_seeing          = Gauge("dag_weather_seeing_arcsec",       "Simulated seeing in arcseconds")
weather_humidity        = Gauge("dag_weather_humidity_percent",    "Simulated humidity percentage")


def update_weather():
    hour = int(time.strftime("%H"))
    if 20 <= hour or hour < 6:
        r = random.random()
        if r < 0.70:
            cond, seeing, hum = 0, round(random.uniform(0.8, 1.5), 2), round(random.uniform(20, 45), 1)
        elif r < 0.90:
            cond, seeing, hum = 1, round(random.uniform(1.5, 3.0), 2), round(random.uniform(60, 85), 1)
        else:
            cond, seeing, hum = 2, round(random.uniform(2.0, 4.0), 2), round(random.uniform(30, 60), 1)
    else:
        cond, seeing, hum = 1, 0.0, round(random.uniform(40, 70), 1)

    weather_condition.set(cond)
    weather_seeing.set(seeing)
    weather_humidity.set(hum)
    labels = ["CLEAR", "CLOUDY", "WINDY"]
    print(f"[WEATHER] {labels[cond]} | Seeing: {seeing}\" | Humidity: {hum}%")


def scan_directory():
    if not os.path.exists(DATA_DIR):
        print(f"[WARN] DATA_DIR bulunamadi: {DATA_DIR}")
        return

    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".fits")]
    fits_files_total.set(len(files))

    total_size, last_time, valid, invalid = 0, 0, 0, 0
    latest_ra, latest_dec, latest_mtime = None, None, 0
    target_counts = {}

    for f in files:
        path = os.path.join(DATA_DIR, f)
        stat = os.stat(path)
        total_size += stat.st_size
        if stat.st_mtime > last_time:
            last_time = stat.st_mtime

        try:
            with astropy_fits.open(path, memmap=False) as hdul:
                header = hdul[0].header
                valid += 1
                if stat.st_mtime > latest_mtime:
                    latest_mtime = stat.st_mtime
                    ra  = header.get("RA",  None)
                    dec = header.get("DEC", None)
                    if ra  is not None: latest_ra  = float(ra)
                    if dec is not None: latest_dec = float(dec)
                obj = header.get("OBJECT", None)
                if obj:
                    target_counts[obj] = target_counts.get(obj, 0) + 1
        except Exception as e:
            invalid += 1
            print(f"[WARN] Gecersiz FITS: {f} -> {e}")

    fits_data_bytes.set(total_size)
    last_fits_timestamp.set(last_time)
    fits_valid_total.set(valid)
    fits_invalid_total.set(invalid)
    if latest_ra  is not None: target_ra.set(latest_ra)
    if latest_dec is not None: target_dec.set(latest_dec)
    for obj, count in target_counts.items():
        target_observation.labels(object=obj).set(count)

    print(f"[OK] {len(files)} dosya | {total_size/1024/1024:.1f} MB | Gecerli: {valid} | Gecersiz: {invalid} | Hedefler: {target_counts}")


def main():
    print("FITS Exporter port 9100'de baslatildi...")
    start_http_server(9100)
    i = 0
    while True:
        scan_directory()
        if i % 5 == 0:
            update_weather()
        i += 1
        time.sleep(30)


if __name__ == "__main__":
    main()