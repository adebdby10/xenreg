"""
Facebook Registration Flow - v4
Fixed: null-safe combobox click, debug submit
"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from faker import Faker
import re, time, random

fake = Faker()
PROXY_PORT = 3128

def extract_cc(phone):
    phone = phone.lstrip("+")
    cc3 = {"212","213","216","218","220","221","222","223","224","225","226","227","228","229",
           "230","231","232","233","234","235","236","237","238","239","240","241","242","243",
           "244","245","246","247","248","249","250","251","252","253","254","255","256","257",
           "258","260","261","262","263","264","265","266","267","268","269","290","291","297",
           "298","299","350","351","352","353","354","355","356","357","358","359","370","371",
           "372","373","374","375","376","377","378","379","380","381","382","385","386","387",
           "389","420","421","423","500","501","502","503","504","505","506","507","508","509",
           "590","592","593","594","595","596","597","598","599","670","672","673","674","675",
           "676","677","678","679","680","681","682","683","685","686","687","688","689","690",
           "691","692","800","808","850","852","853","855","856","858","859","870","878","880",
           "881","882","883","886","960","961","962","963","964","965","966","967","968","970",
           "971","972","973","974","975","976","977","992","993","994","995","996","998"}
    if phone.startswith("1") and len(phone) >= 11:
        return "1", phone[1:]
    if len(phone) >= 3 and phone[:3] in cc3:
        return phone[:3], phone[3:]
    return phone[:2], phone[2:]

def generate_profile():
    gender = random.choice(["male", "female"])
    first = fake.first_name_male() if gender == "male" else fake.first_name_female()
    last = fake.last_name()
    birth = fake.date_of_birth(minimum_age=18, maximum_age=50)
    pw = fake.password(14, True, True, True, True)
    return {
        "first_name": first, "last_name": last,
        "gender": gender.title(),
        "birth_day": str(birth.day),
        "birth_month": str(birth.month),
        "birth_month_name": birth.strftime("%B"),
        "birth_year": str(birth.year),
        "password": pw
    }

FILL_FORM = """
var inputs = document.querySelectorAll('input');
var textInputs = [];
inputs.forEach(function(inp) {
    if (inp.type === 'text') textInputs.push(inp);
    if (inp.type === 'password') textInputs.push(inp);
});
var vals = arguments[0];
function setValue(el, val) {
    var s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    s.call(el, val);
    el.dispatchEvent(new Event('input', {bubbles: true}));
    el.dispatchEvent(new Event('change', {bubbles: true}));
}
for (var i = 0; i < Math.min(textInputs.length, vals.length); i++) {
    setValue(textInputs[i], vals[i]);
}
return textInputs.length;
"""

async def fb_check(phone: str) -> tuple:
    profile = generate_profile()
    options = uc.ChromeOptions()
    options.binary_location = "/usr/bin/google-chrome"
    options.add_argument("--proxy-server=http://127.0.0.1:3128")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1366,768")
    
    driver = None
    try:
        driver = uc.Chrome(options=options, version_main=150, headless=True)
        driver.set_page_load_timeout(35)
        driver.get("https://facebook.com/reg")
        time.sleep(4)
        
        # 1. Fill text inputs
        driver.execute_script(FILL_FORM, [
            profile["first_name"], profile["last_name"],
            phone.lstrip("+"), profile["password"]
        ])
        time.sleep(1)
        
        # 2. Select comboboxes with null safety
        selects = [
            ("Select day", profile["birth_day"]),
            ("Select month", profile["birth_month_name"]),
            ("Select year", profile["birth_year"]),
            ("Select your gender", profile["gender"]),
        ]
        
        for aria_label, value in selects:
            click_js = 'var el = document.querySelector(\'[aria-label="' + aria_label + '"]\'); if (el) el.click();'
            driver.execute_script(click_js)
            time.sleep(1.2)
            
            r = driver.execute_script("""
                var opts = document.querySelectorAll('[role="option"]');
                var target = arguments[0];
                for (var i = 0; i < opts.length; i++) {
                    if (opts[i].textContent.trim() === target) {
                        opts[i].click();
                        return 'OK:' + target;
                    }
                }
                return 'NOT_FOUND:' + target;
            """, value)
            time.sleep(0.3)
        
        # 3. Debug: find all submit-like elements
        sub_result = driver.execute_script("""
            var results = [];
            var all = document.querySelectorAll('div, span, button');
            for (var i = 0; i < all.length; i++) {
                var txt = (all[i].textContent || '').trim();
                if (txt.length > 0 && txt.length < 50 && 
                    (txt.indexOf('Submit') >= 0 || txt.indexOf('submit') >= 0 ||
                     txt.indexOf('Sign') >= 0 || txt.indexOf('sign') >= 0)) {
                    results.push(all[i].tagName + '|' + txt.substring(0,30));
                }
            }
            return results;
        """)
        
        # 4. Try click submit
        if sub_result:
            driver.execute_script("""
                var all = document.querySelectorAll('div, span, button');
                for (var i = 0; i < all.length; i++) {
                    var txt = (all[i].textContent || '').trim();
                    if (txt.indexOf('Submit') >= 0 || txt.indexOf('submit') >= 0 ||
                        txt.indexOf('Sign') >= 0 || txt.indexOf('sign') >= 0) {
                        if (txt.length < 50) {
                            all[i].click();
                            return;
                        }
                    }
                }
            """)
        
        time.sleep(10)
        result = detect(driver)
        return result, profile
        
    except Exception as e:
        print("[FB] Error: " + str(e))
        try:
            result = detect(driver) if driver else "UNKNOWN"
            return result, profile
        except:
            return "UNKNOWN", profile
    finally:
        if driver:
            try: driver.quit()
            except: pass


async def fb_register(phone: str, otp: str, profile: dict) -> str:
    options = uc.ChromeOptions()
    options.binary_location = "/usr/bin/google-chrome"
    options.add_argument("--proxy-server=http://127.0.0.1:3128")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1366,768")
    
    driver = None
    try:
        driver = uc.Chrome(options=options, version_main=150, headless=True)
        driver.set_page_load_timeout(30)
        driver.get("https://facebook.com/reg")
        time.sleep(4)
        
        code_field = driver.execute_script("""
            var inputs = document.querySelectorAll('input');
            for (var i = 0; i < inputs.length; i++) {
                var ph = inputs[i].placeholder || '';
                if (ph.toLowerCase().indexOf('code') >= 0) return inputs[i];
                var aria = inputs[i].getAttribute('aria-label') || '';
                if (aria.toLowerCase().indexOf('code') >= 0) return inputs[i];
            }
            return null;
        """)
        
        if code_field:
            code_field.send_keys(otp)
            time.sleep(1)
            driver.execute_script("""
                var btns = document.querySelectorAll('div, span, button');
                for (var i = 0; i < btns.length; i++) {
                    var t = (btns[i].textContent || '').trim().toLowerCase();
                    if (t === 'continue' || t === 'next' || t === 'confirm') {
                        btns[i].click(); return;
                    }
                }
            """)
            time.sleep(8)
            result = detect(driver)
            if result == "SUCCESS": return "SUCCESS"
            elif result in ("OTP_SENT", "EMAIL_VERIFICATION", "FORM_ERROR"): return "WRONG_CODE"
            elif result == "CHECKPOINT": return "CHECKPOINT"
            elif result == "ADD_EMAIL": return "ADD_EMAIL"
            else: return "UNKNOWN"
        else:
            result = detect(driver)
            if result == "SUCCESS": return "SUCCESS"
            return "WRONG_CODE"
            
    except Exception as e:
        print("[FB Reg] Error: " + str(e))
        return "TIMEOUT"
    finally:
        if driver:
            try: driver.quit()
            except: pass


def detect(driver):
    time.sleep(2)
    try:
        WebDriverWait(driver, 10).until(
            lambda d: any(x in d.current_url for x in [
                "facebook.com/?", "facebook.com/?sk=", 
                "facebook.com/checkpoint", "facebook.com/reg",
                "facebook.com/login"
            ])
        )
    except:
        pass
    
    body = driver.find_element(By.TAG_NAME, "body").text.lower()
    url = driver.current_url.lower()
    
    if any(x in url for x in ["welcome", "facebook.com/?"]):
        return "SUCCESS"
    if "enter the code" in body or "check your" in body:
        return "OTP_SENT"
    if "code" in body and ("sent" in body or "send" in body):
        return "OTP_SENT"
    if "email" in body and ("code" in body or "verify" in body):
        return "EMAIL_VERIFICATION"
    if any(w in body for w in ["invalid", "wrong number", "enter a valid"]):
        return "INVALID_NUMBER"
    if any(w in body for w in ["unusual", "suspicious", "blocked", "cannot create", "confirm your identity"]):
        return "CHECKPOINT"
    if "add email" in body or "add an email" in body:
        return "ADD_EMAIL"
    return "UNKNOWN"
