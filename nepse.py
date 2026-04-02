from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv

HEADLESS = False  # Set True for headless mode

def setup_driver():
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox") # for linux/container to prevent chrome crashes
    options.add_argument("--disable-dev-shm-usage") #Disable /dev/shm usage to prevent Chrome crashes in limited-memory environments
    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3") #suppress most of the logs
    options.add_experimental_option("excludeSwitches", ["enable-logging"]) #Remove the "Chrome is being controlled by automated test software" message

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

driver = setup_driver()
driver.get("https://www.sharesansar.com/index-history-data")
wait = WebDriverWait(driver, 15)

# --- Step 1: Set "From Date" ---
from_date_input = wait.until(EC.presence_of_element_located((By.ID, "fromDate")))
driver.execute_script("arguments[0].removeAttribute('readonly')", from_date_input)
from_date_input.clear()
from_date_input.send_keys("2012-01-01")

# --- Step 2: Click Search button ---
search_button = driver.find_element(By.ID, "btn_indxhis_submit")
search_button.click()

# Wait until table element is present and rows are loaded
wait.until(EC.presence_of_element_located((By.ID, "myTable")))
# wait until at least one row is present
wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#myTable tbody tr")))

# --- Ensure we are on page 1 of pagination ---
def ensure_page_one():
    try:
        # locate the active pagination button
        active = driver.find_element(By.CSS_SELECTOR, "#myTable_paginate .paginate_button.current")
        if active.text.strip() != "1":
            # find the button with text '1' and click it
            buttons = driver.find_elements(By.CSS_SELECTOR, "#myTable_paginate .paginate_button")
            for b in buttons:
                if b.text.strip() == "1":
                    b.click()
                    # wait until rows refresh
                    time.sleep(0.5)
                    wait.until(EC.staleness_of(driver.find_elements(By.CSS_SELECTOR, "#myTable tbody tr")[0]))
                    # wait until new rows present
                    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#myTable tbody tr")))
                    break
    except Exception:
        # fallback: try to click 'first' button if exists
        try:
            first_btn = driver.find_element(By.CSS_SELECTOR, "#myTable_paginate .first")
            first_btn.click()
            time.sleep(0.5)
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#myTable tbody tr")))
        except Exception:
            pass

ensure_page_one()

# --- Step 3: Scrape table with pagination ---
all_data = []

while True:
    try:
        # Wait until table rows are present and non-empty
        rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#myTable tbody tr")))
        if len(rows) == 0:
            break

        for row in rows:
            try:
                cols = row.find_elements(By.TAG_NAME, "td")
                data = [col.text.strip() for col in cols]
                all_data.append(data)
            except Exception:
                continue  # skip problematic rows

        # Check if next button is disabled
        next_button = driver.find_element(By.ID, "myTable_next")
        if "disabled" in next_button.get_attribute("class"):
            break  # last page reached

        # Click next and wait for table to reload
        next_button.click()
        # wait until rows become stale and new rows are loaded
        wait.until(EC.staleness_of(rows[0]))
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#myTable tbody tr")))
        time.sleep(0.3)
    except Exception:
        break

driver.quit()

# --- Save to CSV ---
with open("nepse.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["S.N.", "Open", "High", "Low", "Close", "Change", "Per Change (%)", "Turnover", "Date"])
    writer.writerows(all_data)

print(f"Scraped {len(all_data)} rows successfully!")
