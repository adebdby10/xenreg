"""Deep debug: find form elements on Facebook reg page"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from faker import Faker
import time

fake = Faker()
options = uc.ChromeOptions()
options.binary_location = "/usr/bin/google-chrome"
options.add_argument("--proxy-server=http://127.0.0.1:3128")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1366,768")

d = uc.Chrome(options=options, version_main=150, headless=True)
d.set_page_load_timeout(30)
d.get("https://facebook.com/reg")
time.sleep(5)

first = fake.first_name_male()
last = fake.last_name()

# Fill inputs
js_fill = """var inputs = document.querySelectorAll('input');
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
return textInputs.length;"""

filled = d.execute_script(js_fill, [first, last, "62812xxxxx", "TestPass123!"])
print(f"1. Filled {filled} inputs")
time.sleep(1)

# Find gender radio
js_gender = """var results = [];
// Look for input type radio
document.querySelectorAll('input').forEach(function(inp) {
    var t = inp.getAttribute('type') || '';
    var val = inp.getAttribute('value') || '';
    var aria = inp.getAttribute('aria-label') || '';
    if (t === 'radio' || val === 'Male' || val === 'Female' || aria.indexOf('gender') >= 0 || aria.indexOf('Gender') >= 0) {
        results.push('input type=' + t + ' value=' + val + ' aria=' + aria);
    }
});
return results;"""

gender_inputs = d.execute_script(js_gender)
print(f"2. Gender inputs: {gender_inputs}")

# Find all buttons/submit elements
js_btns = """var results = [];
document.querySelectorAll('div, span, button, [role="button"]').forEach(function(el) {
    var txt = (el.textContent || '').trim();
    if (txt.length > 0 && txt.length < 60 && txt.indexOf('Sub') >= 0 || txt.indexOf('Sig') >= 0 || txt.indexOf('sub') >= 0) {
        results.push(el.tagName + ' role=' + (el.getAttribute('role') || 'none') + ' txt=' + txt.substring(0, 30));
    }
});
return results;"""

btns = d.execute_script(js_btns)
print(f"3. Submit-like elements: {btns[:10]}")

# Also check what aria attributes look like
js_form_area = """var results = [];
// Find elements that look like interactive form parts
document.querySelectorAll('[role="option"], [role="listbox"], [role="combobox"], [role="radio"]').forEach(function(el) {
    var role = el.getAttribute('role') || '';
    var text = (el.textContent || '').trim().substring(0, 40);
    results.push(role + ':' + text);
});
// Also check gender-specific elements
document.querySelectorAll('span, div').forEach(function(el) {
    var txt = (el.textContent || '').trim();
    if (txt === 'Male' || txt === 'Female' || txt === 'Custom') {
        var role = el.getAttribute('role') || 'none';
        results.push('GENDER:' + txt + ' role=' + role + ' tag=' + el.tagName);
    }
});
return results;"""

form_els = d.execute_script(js_form_area)
print(f"4. Form elements:")
for e in form_els:
    print(f"   {e}")

# Now try selecting dropdowns and check what happens
d.execute_script("""document.querySelector('[aria-label="Select day"]').click();""")
time.sleep(0.8)
d.execute_script("""document.querySelectorAll('[role="option"]')[14].click();""")  # 15th = day 15
time.sleep(0.3)
d.execute_script("""document.querySelector('[aria-label="Select month"]').click();""")
time.sleep(0.8)
months = d.execute_script("""var opts = document.querySelectorAll('[role="option"]');
var names = [];
opts.forEach(function(o) { names.push(o.textContent.trim()); });
return names;""")
print(f"5. Month options: {months[:15]}")

d.quit()
