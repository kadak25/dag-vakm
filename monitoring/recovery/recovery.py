import os
import time
import shutil
import logging
import requests
from datetime import datetime

# --- Config ---
DATA_DIR        = "../data/raw_fits"
BACKUP_DIR      = "../data/backup"
LOG_FILE        = "../logs/recovery.log"
TELEGRAM_TOKEN  = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT   = os.environ.get("TELEGRAM_CHAT_ID", "")

# --- Logging ---
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("recovery")


def telegram(msg: str):
    """Telegram'a mesaj gönder."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        log.warning("Telegram token/chat_id eksik, mesaj atlanamadı.")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT, "text": msg}, timeout=10)
        log.info(f"Telegram mesajı gönderildi: {msg}")
    except Exception as e:
        log.error(f"Telegram hatası: {e}")


def check_data_dir() -> bool:
    """Veri klasörü var mı ve erişilebilir mi?"""
    if not os.path.exists(DATA_DIR):
        log.error(f"DATA_DIR bulunamadı: {DATA_DIR}")
        return False
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".fits")]
    log.info(f"DATA_DIR kontrol: {len(files)} FITS dosyası bulundu.")
    return True


def simulate_rsync_retry() -> tuple[bool, int]:
    """
    Gerçek sistemde: rsync -avz --partial source/ dest/
    Burada simüle ediyoruz.
    """
    log.info("rsync retry başlatılıyor...")
    time.sleep(2)  # rsync simülasyonu

    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".fits")] if os.path.exists(DATA_DIR) else []
    recovered = len(files)

    log.info(f"rsync tamamlandı. {recovered} dosya kontrol edildi.")
    return True, recovered


def backup_to_local(alert_name: str) -> tuple[bool, int]:
    """
    Veriyi local backup klasörüne kopyala.
    Gerçek sistemde MinIO/S3'e push edilir.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"{alert_name}_{timestamp}")

    try:
        os.makedirs(backup_path, exist_ok=True)

        if not os.path.exists(DATA_DIR):
            log.warning("DATA_DIR yok, yedekleme atlandı.")
            return False, 0

        files = [f for f in os.listdir(DATA_DIR) if f.endswith(".fits")]
        copied = 0
        for f in files:
            src = os.path.join(DATA_DIR, f)
            dst = os.path.join(backup_path, f)
            shutil.copy2(src, dst)
            copied += 1

        log.info(f"Yedekleme tamamlandı: {backup_path} — {copied} dosya")
        return True, copied

    except Exception as e:
        log.error(f"Yedekleme hatası: {e}")
        return False, 0


def run_recovery(alert_name: str, alert_description: str):
    """Ana kurtarma fonksiyonu."""
    log.info(f"=== KURTARMA BAŞLADI: {alert_name} ===")
    telegram(f"🔧 Kurtarma başlatıldı!\nAlert: {alert_name}\n{alert_description}")

    success_steps = []
    failed_steps  = []

    # Adım 1: Klasör kontrolü
    if check_data_dir():
        success_steps.append("✅ Klasör kontrolü")
    else:
        failed_steps.append("❌ Klasör kontrolü")

    # Adım 2: rsync retry
    rsync_ok, recovered = simulate_rsync_retry()
    if rsync_ok:
        success_steps.append(f"✅ rsync retry ({recovered} dosya)")
    else:
        failed_steps.append("❌ rsync retry")

    # Adım 3: Yedekleme
    backup_ok, copied = backup_to_local(alert_name)
    if backup_ok:
        success_steps.append(f"✅ Yedekleme ({copied} dosya)")
    else:
        failed_steps.append("❌ Yedekleme")

    # Sonuç
    log.info(f"Başarılı: {success_steps}")
    log.info(f"Başarısız: {failed_steps}")

    if not failed_steps:
        msg = (
            f"✅ Kurtarma tamamlandı!\n"
            f"Alert: {alert_name}\n"
            f"Adımlar:\n" + "\n".join(success_steps)
        )
        log.info("KURTARMA BAŞARILI")
    else:
        msg = (
            f"⚠️ Kurtarma kısmen başarısız!\n"
            f"Alert: {alert_name}\n"
            f"Başarılı: {chr(10).join(success_steps)}\n"
            f"Başarısız: {chr(10).join(failed_steps)}\n"
            f"Manuel müdahale gerekebilir!"
        )
        log.warning("KURTARMA KISMI BAŞARISIZ")

    telegram(msg)
    log.info(f"=== KURTARMA TAMAMLANDI: {alert_name} ===\n")


if __name__ == "__main__":
    # Manuel test
    run_recovery(
        alert_name="FITSVeriAkisiDurdu",
        alert_description="Son FITS dosyası 45 dakikadır gelmedi."
    )