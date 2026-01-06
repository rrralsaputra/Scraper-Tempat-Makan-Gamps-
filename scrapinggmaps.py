from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import pandas as pd


# Konfigurasi
KATA_KUNCI = "tempat makan di surabaya"
JUMLAH_DATA_MAKSIMAL = 100
NAMA_FILE_OUTPUT = "tempat_makan_surabaya.csv"
DELAY = 2

# Setup browser
def inisialisasi_browser():
    opsi = Options()
    opsi.add_argument("--lang=id")
    opsi.add_argument("--start-maximized")
    opsi.add_argument("--disable-blink-features=AutomationControlled")
    opsi.add_experimental_option("excludeSwitches", ["enable-automation"])
    opsi.add_experimental_option("useAutomationExtension", False)
    opsi.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=opsi)


def tunggu(detik=2):
    time.sleep(detik)

def buka_tab_ulasan(driver):
    try:
        tombol = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(@aria-label,'Ulasan')]")
            )
        )
        driver.execute_script("arguments[0].click();", tombol)
        time.sleep(2)
        return True
    except:
        return False


def scroll_panel(driver, kali=3):
    try:
        panel = driver.find_element(By.CSS_SELECTOR, "div[role='main']")
        for _ in range(kali):
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight",
                panel
            )
            time.sleep(1)
    except:
        pass


def ambil_ulasan_pertama(driver):
    selectors = [
        "span.wiI7pd",
        "div.MyEned span",
    ]

    for sel in selectors:
        try:
            review = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, sel))
            ).text.strip()
            if review:
                return review.replace("\n", " ")
        except:
            continue

    return "Tidak ada ulasan teks"


def mulai_ambil_data():
    driver = inisialisasi_browser()
    wait = WebDriverWait(driver, 15)

    hasil = []
    visited_urls = set()

    try:
        # Buka Google Maps
        url_search = f"https://www.google.com/maps/search/{KATA_KUNCI.replace(' ', '+')}"
        driver.get(url_search)
        print(f"Mencari: {KATA_KUNCI}")
        tunggu(3)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")))
        feed = driver.find_element(By.CSS_SELECTOR, "div[role='feed']")

        # Scroll & kumpulkan URL unik
        print("Mengumpulkan URL tempat...")
        prev_count = 0
        stagnan = 0

        while len(visited_urls) < JUMLAH_DATA_MAKSIMAL and stagnan < 3:
            cards = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")

            for c in cards:
                href = c.get_attribute("href")
                if href:
                    visited_urls.add(href)

            if len(visited_urls) == prev_count:
                stagnan += 1
            else:
                stagnan = 0

            prev_count = len(visited_urls)
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight",
                feed
            )
            tunggu(2)

        daftar_url = list(visited_urls)[:JUMLAH_DATA_MAKSIMAL]
        print(f"{len(daftar_url)} URL unik terkumpul\n")

        # Loop berdasarkan URL
        for i, url in enumerate(daftar_url, 1):
            print(f"📍 [{i}/{len(daftar_url)}] Mengambil data...")
            driver.get(url)

            try:
                nama = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.DUwDvf"))
                ).text
            except TimeoutException:
                print(" Gagal load, skip")
                continue

            tunggu(1)

            # Alamat
            alamat = "Tidak diketahui"
            try:
                alamat_btn = driver.find_element(By.CSS_SELECTOR, "button[data-item-id='address']")
                alamat = alamat_btn.get_attribute("aria-label").replace("Alamat: ", "").strip()
            except:
                pass

            # No Telepon
            no_telepon = "Tidak diketahui"
            try:
                tel_btn = driver.find_element(By.CSS_SELECTOR, "button[data-item-id^='phone']")
                tel = tel_btn.get_attribute("aria-label")
                if tel:
                    no_telepon = tel.replace("Telepon: ", "").strip()
            except:
                pass

            # Rating 
            rating = None
            rating_selectors = [
                "span.ceNzKf",
                "div.F7nice span",
                "span[aria-label*='bintang']"
            ]

            for sel in rating_selectors:
                try:
                    rating = driver.find_element(By.CSS_SELECTOR, sel).text
                    if rating:
                        break
                except:
                    continue

            # Ambil ulasan
            buka_tab_ulasan(driver)
            scroll_panel(driver)
            ulasan = ambil_ulasan_pertama(driver)

            hasil.append({
                "Nama Tempat": nama,
                "Alamat": alamat,
                "No Telepon": no_telepon,
                "Rating": rating,
                "Ulasan Singkat": ulasan,
                "URL": url
            })

            print(f"✓ {nama}")
            tunggu(DELAY)

        print(f"\nTotal data diambil: {len(hasil)}")

    finally:
        driver.quit()

        if hasil:
            df = pd.DataFrame(hasil)

            # Dedup FINAL
            df.drop_duplicates(subset=["URL"], inplace=True)

            # Normalisasi data
            df["Ulasan Singkat"] = df["Ulasan Singkat"].fillna("Tidak ada ulasan teks")

            df.to_csv(NAMA_FILE_OUTPUT, index=False, encoding="utf-8-sig")
            print(f"🎉 Data disimpan ke: {NAMA_FILE_OUTPUT}")
            print("\n📋 Preview:")
            print(df.head().to_string())
        else:
            print("Tidak ada data tersimpan")

if __name__ == "__main__":
    mulai_ambil_data()
