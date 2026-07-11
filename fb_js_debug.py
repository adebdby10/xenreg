"""FB form - JavaScript approach for React form"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from faker import Faker
import time, re, random

fake = Faker()

phone = "+62812xxxxx"
gender = random.choice(["male", "female"])
first = fake.first_name_male() if gender == "male" else fake.first_name_female()
last = fake.last_name()
pw = fake.password(14, True, True, True, True)

print(f"Name: {first} {last}")

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

# Use JavaScript to fill form
fill_js = """
// Helper to set React-friendly input value
function setInputValue(el, val) {
    var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    nativeSetter.call(el, val);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.dispatchEvent(new Event('blur', { bubbles: true }));
}

// Find inputs by type
var inputs = document.querySelectorAll('input');
var textInputs = [];
var pwdInput = null;

inputs.forEach(function(inp) {
    if (inp.type === 'password') {
        pwdInput = inp;
    } else if (inp.type === 'text') {
        textInputs.push(inp);
    }
});

if (textInputs.length >= 1) setInputValue(textInputs[0], arguments[0]); // first name
if (textInputs.length >= 2) setInputValue(textInputs[1], arguments[1]); // last name  
if (textInputs.length >= 3) setInputValue(textInputs[2], arguments[2]); // phone
if (pwdInput) setInputValue(pwdInput, arguments[3]); // password

return textInputs.length;
"""

filled = d.execute_script(fill_js, first, last, phone.lstrip("+"), pw)
print(f"1. Filled {filled} text inputs")

time.sleep(1)

# Click the day dropdown to trigger the full form
day_js = """
var labels = document.querySelectorAll('span, div, label');
var clicked = false;
labels.forEach(function(el) {
    var text = (el.textContent || '').trim().toLowerCase();
    if (text === 'day' && !clicked) {
        el.click();
        clicked = true;
    }
});
return clicked;
"""

clicked_day = d.execute_script(day_js)
print(f"2. Clicked day: {clicked_day}")
time.sleep(1)

# Now dump all elements to see what's available
dump_js = """
var results = [];
// Check all interactive elements
document.querySelectorAll('div[role="listbox"], div[role="option"], div[role="button"], div[role="radio"], [aria-label], span, button').forEach(function(el) {
    var role = el.getAttribute('role') || '';
    var text = (el.textContent || '').trim().substring(0, 40);
    var aria = el.getAttribute('aria-label') || '';
    if (text || aria) {
        results.push(role + '|' + aria + '|' + text);
    }
});
return results;
"""

elems = d.execute_script(dump_js)
print(f"3. Elements found:")
for e in elems[:30]:
    print(f"   {e}")

d.save_screenshot("/tmp/fb_js.png")

# Try clicking submit using JavaScript
submit_js = """
var all = document.querySelectorAll('div, span, button');
for (var i = 0; i < all.length; i++) {
    var text = (all[i].textContent || '').trim().toLowerCase();
    if (text === 'submit' || text === 'sign up' || text === 'create account' || text === 'register') {
        all[i].click();
        return 'Clicked: ' + text;
    }
}
return 'No submit found';
"""
result = d.execute_script(submit_js)
print(f"4. Submit: {result}")

time.sleep(8)
body = d.find_element(By.TAG_NAME, "body").text[:600]
print(f"5. After submit: {body[:400]}")

bl = body.lower()
if "code" in bl and ("enter" in bl or "sent" in bl or "check" in bl):
    print(">>> OTP_SENT")
elif "invalid" in bl or "wrong number" in bl:
    print(">>> INVALID_NUMBER")
elif "unusual" in bl or "suspicious" in bl or "blocked" in bl:
    print(">>> CHECKPOINT")
elif "email" in bl and ("code" in bl or "verify" in bl):
    print(">>> EMAIL")
elif "create" in bl or "first name" in bl:
    print(">>> FORM_ERROR (still on page)")
elif "welcome" in d.current_url:
    print(">>> SUCCESS!")
else:
    print(">>> UNKNOWN")

d.quit()
