"""
DAG-VAKM Webhook Server
Alertmanager'dan gelen alert'leri dinler ve recovery.py'ı tetikler.
"""

from flask import Flask, request, jsonify
import logging
import threading
import recovery

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("webhook")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "DAG-VAKM Webhook"}), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "invalid payload"}), 400

    alerts = data.get("alerts", [])
    log.info(f"{len(alerts)} alert alındı.")

    for alert in alerts:
        status      = alert.get("status", "unknown")
        alert_name  = alert.get("labels", {}).get("alertname", "Bilinmeyen Alert")
        description = alert.get("annotations", {}).get("description", "")
        severity    = alert.get("labels", {}).get("severity", "info")

        log.info(f"Alert: {alert_name} | Status: {status} | Severity: {severity}")

        # Sadece firing (tetiklenen) ve critical/warning alert'lerde recovery başlat
        if status == "firing" and severity in ("critical", "warning"):
            log.info(f"Recovery tetikleniyor: {alert_name}")
            t = threading.Thread(
                target=recovery.run_recovery,
                args=(alert_name, description),
                daemon=True
            )
            t.start()
        else:
            log.info(f"Recovery atlandı (status={status}, severity={severity})")

    return jsonify({"received": len(alerts)}), 200


if __name__ == "__main__":
    log.info("DAG-VAKM Webhook Server port 5001'de başlatıldı...")
    app.run(host="0.0.0.0", port=5001, debug=False)