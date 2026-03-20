import os
import json
import random
import time
from datetime import datetime
import numpy as np
from astropy.io import fits
from astropy import wcs
from datetime import timezone

# Klasörler
DATA_DIR = "../data/raw_fits"
CATALOG_FILE = "catalog.json"
LOG_FILE = "../logs/generator.log"

FILTERS = ["Y", "J", "H", "K"]

def log_message(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(msg)

def load_catalog():
    if not os.path.exists(CATALOG_FILE):
        log_message("Katalog dosyası bulunamadı!")
        return []
    with open(CATALOG_FILE) as f:
        return json.load(f)

def create_fake_image(size=1024):
    # Noise tabanı
    img = np.random.normal(1000, 15, (size, size)).astype(np.float32)
    
    # 5-15 arası rastgele yıldız ekle
    for _ in range(random.randint(5, 15)):
        x = random.randint(50, size-50)
        y = random.randint(50, size-50)
        flux = random.uniform(2000, 8000)
        sigma = random.uniform(2, 5)
        
        # Gaussian yıldız
        for i in range(max(0, y-20), min(size, y+20)):
            for j in range(max(0, x-20), min(size, x+20)):
                r2 = (i - y)**2 + (j - x)**2
                img[i, j] += flux * np.exp(-r2 / (2 * sigma**2))
    
    return img

def write_fits(target):
    data = create_fake_image()
    
    hdu = fits.PrimaryHDU(data)
    hdr = hdu.header
    
    # Gerçekçi header
    hdr['SIMPLE']   = True
    hdr['BITPIX']   = -32
    hdr['NAXIS']    = 2
    hdr['NAXIS1']   = data.shape[1]
    hdr['NAXIS2']   = data.shape[0]
    
    hdr['TELESCOP'] = 'DAG 4m'
    hdr['INSTRUME'] = 'DIRAC'
    hdr['OBJECT']   = target['name']
    hdr['FILTER']   = random.choice(FILTERS)
    hdr['EXPTIME']  = round(random.uniform(20, 180), 1)  # 20-180 saniye
    hdr['AIRMASS']  = round(random.uniform(1.0, 2.5), 2)
    hdr['SEEING']   = round(random.uniform(0.8, 2.5), 2)
    hdr['MOONPHAS'] = round(random.uniform(0.0, 1.0), 2)
    hdr['RA']       = target['ra']
    hdr['DEC']      = target['dec']
    hdr['EQUINOX']  = 2000.0
    hdr['DATE-OBS'] = datetime.now(timezone.utc).isoformat()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    # Basit WCS
    w = wcs.WCS(naxis=2)
    w.wcs.crpix = [data.shape[1]/2 + 0.5, data.shape[0]/2 + 0.5]
    w.wcs.crval = [target['ra'], target['dec']]
    w.wcs.cdelt = [-0.0002778, 0.0002778]  # ~1 arcsec/pixel
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    
    hdr.update(w.to_header())
    
    # Filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    exp_num = random.randint(1, 999)
    filename = f"DAG_{timestamp}_{hdr['FILTER']}_{target['name']}_{exp_num:03d}.fits"
    
    path = os.path.join(DATA_DIR, filename)
    hdu.writeto(path, overwrite=True)
    
    log_message(f"Generated: {filename} ({os.path.getsize(path)/1024/1024:.1f} MB)")
    return path

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    catalog = load_catalog()
    if not catalog:
        log_message("Katalog boş veya yok – çıkılıyor.")
        return
    
    log_message("Fake Telescope Generator başladı. Ctrl+C ile durdurabilirsiniz.")
    
    while True:
        # Basit gece kontrolü (şimdilik saat bazlı)
        hour = datetime.now().hour
        if 20 <= hour or hour < 6:
            target = random.choice(catalog)
            write_fits(target)
        else:
            log_message("Gündüz modu – veri üretimi durduruldu.")
        
        # 5-15 dk arası bekle
        wait = random.randint(300, 900)
        log_message(f"Bir sonraki exposure {wait} saniye sonra.")
        time.sleep(wait)

if __name__ == "__main__":
    main()