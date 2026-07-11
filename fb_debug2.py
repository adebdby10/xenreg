"""Debug FB check - scroll to trigger full form"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

options = uc.ChromeOptions()
options.binary_location = "/usr/bin/google-chrome"
options.add_argument("--proxy-server=http://127.0.0.1:3128")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--headless=new")
options.add_argument("--window-size=1366,768")

d = uc.Chrome(options=options, version_main=150)
d.set_page_load_timeout(30)

d.get("https://facebook.com/reg")
print("1. Page loaded")
time.sleep(3)

# Scroll to trigger JS rendering
d.execute_script("window.scrollTo(0, document.body.scrollHeight);")
time.sleep(1)
d.execute_script("window.scrollTo(0, 0);")
time.sleep(1)

# Click on first name field to trigger form expansion
inputs = d.find_elements(By.TAG_NAME, "input")
print(f"   Inputs before click: {len(inputs)}")
if inputs:
    inputs[0].click()
    time.sleep(1)

# Check again after expansion
inputs = d.find_elements(By.TAG_NAME, "input")
selects = d.find_elements(By.TAG_NAME, "select")
buttons = d.find_elements(By.TAG_NAME, "button")
print(f"   After: {len(inputs)} inputs, {len(selects)} selects, {len(buttons)} buttons")

for inp in inputs:
    aria = inp.get_attribute("aria-label") or ""
    ph = inp.get_attribute("placeholder") or ""
    name = inp.get_attribute("name") or ""
    t = inp.get_attribute("type") or ""
    print(f"   input: t={t} name={name[:20]} aria={aria[:30]} ph={ph[:30]}")

for sel in selects:
    name = sel.get_attribute("name") or ""
    aria = sel.get_attribute("aria-label") or ""
    print(f"   select: name={name[:20]} aria={aria[:30]}")

for btn in buttons:
    txt = btn.text.strip()[:40]
    if txt:
        print(f"   button: '{txt}'")

# Try clicking anywhere in the form area
d.execute_script("""
    // Find and click the first text element in the form
    var elements = document.querySelectorAll('input[name="firstname"], [aria-label*="First"], [placeholder*="First"]');
    if (elements.length > 0) {
        elements[0].focus();
        elements[0].click();
    }
""")
time.sleep(1)

# Check again
inputs2 = d.find_elements(By.TAG_NAME, "select")
print(f"\n   After JS click: {len(inputs2)} selects, {len(d.find_elements(By.TAG_NAME, 'button'))} buttons")

d.save_screenshot("/tmp/fb_form.png")
print("\nScreenshot saved")

d.quit()
