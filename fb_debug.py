"""Debug FB check - step by step with screenshots"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import asyncio, time, sys

phone = "+62812xxxxx"
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
time.sleep(5)
d.save_screenshot("/tmp/fb_1_load.png")
print("1. Page loaded")

# Find and fill ALL inputs
inputs = d.find_elements(By.TAG_NAME, "input")
print(f"   Found {len(inputs)} input elements")

filled = 0
for i, inp in enumerate(inputs):
    i_type = inp.get_attribute("type") or ""
    i_name = inp.get_attribute("name") or ""
    i_aria = inp.get_attribute("aria-label") or ""
    i_ph = inp.get_attribute("placeholder") or ""
    print(f"   [{i}] type={i_type} name={i_name[:20]} aria={i_aria[:30]} ph={i_ph[:30]}")
    
    if i_type == "text" and i in (0, 1):
        # First two text fields are first/last name
        inp.send_keys("John" if i == 0 else "Doe")
        filled += 1
        time.sleep(0.2)
    elif "phone" in i_ph.lower() or "email" in i_ph.lower() or "mobile" in i_ph.lower():
        inp.send_keys(phone.lstrip("+"))
        filled += 1
        time.sleep(0.2)
    elif i_type == "password":
        inp.send_keys("TestPass123!")
        filled += 1
        time.sleep(0.2)

print(f"2. Filled {filled} input fields")

# Select birth date
selects = d.find_elements(By.TAG_NAME, "select")
print(f"   Found {len(selects)} select elements")
for sel in selects:
    name = sel.get_attribute("name") or ""
    aria = sel.get_attribute("aria-label") or ""
    print(f"   select: name={name} aria={aria[:30]}")
    if "day" in name or "day" in aria.lower():
        Select(sel).select_by_value("15")
        time.sleep(0.2)
    elif "month" in name or "month" in aria.lower():
        Select(sel).select_by_value("6")
        time.sleep(0.2)
    elif "year" in name or "year" in aria.lower():
        Select(sel).select_by_value("1995")
        time.sleep(0.2)

# Gender radio
for inp in d.find_elements(By.TAG_NAME, "input"):
    if inp.get_attribute("type") == "radio":
        val = inp.get_attribute("value") or ""
        print(f"   radio: value={val}")
        d.execute_script("arguments[0].click();", inp)
        time.sleep(0.2)
        break

# Submit
buttons = d.find_elements(By.TAG_NAME, "button")
print(f"   Found {len(buttons)} buttons")
for btn in buttons:
    txt = btn.text.strip()
    print(f"   button: '{txt[:30]}'")
    if "submit" in txt.lower() or "sign" in txt.lower() or "create" in txt.lower():
        print(f"   -> Clicking: {txt[:30]}")
        d.execute_script("arguments[0].click();", btn)
        time.sleep(0.3)
        break

print("3. Submitted form")
time.sleep(8)

url = d.current_url
print(f"4. URL: {url}")
body = d.find_element(By.TAG_NAME, "body").text[:800]
print(f"5. Body: {body[:500]}")
d.save_screenshot("/tmp/fb_2_after.png")

# Check result
import re
bl = body.lower()
if "code" in bl and ("enter" in bl or "sent" in bl):
    print(">>> OTP_SENT")
elif "invalid" in bl or "wrong number" in bl or "valid" in bl:
    print(">>> INVALID_NUMBER")
elif "unusual" in bl or "suspicious" in bl or "blocked" in bl:
    print(">>> CHECKPOINT")
elif "email" in bl and ("code" in bl or "verify" in bl):
    print(">>> EMAIL_VERIFICATION")
elif "create" in bl or "sign up" in bl or "first name" in bl:
    print(">>> FORM_ERROR (still on reg page)")
else:
    print(">>> UNKNOWN")

d.quit()
