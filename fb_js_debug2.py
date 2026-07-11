"""FB form - comprehensive JavaScript approach for full React form"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from faker import Faker
import time, random

fake = Faker()

phone = "+62812xxxxx"
gender = random.choice(["male", "female"])
first = fake.first_name_male() if gender == "male" else fake.first_name_female()
last = fake.last_name()
pw = fake.password(14, True, True, True, True)
month = 6
day = 15
year = 1995

print(f"Name: {first} {last}, Gender: {gender}")

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
time.sleep(4)

# Step 1: Fill all text inputs with React-compatible events
fill = d.execute_script("""
var inputs = document.querySelectorAll('input');
var textFields = [];
inputs.forEach(function(inp) {
    if (inp.type === 'text') textFields.push(inp);
    if (inp.type === 'password') textFields.push(inp);
});

// Fill each text input
var values = arguments[0];
for (var i = 0; i < Math.min(textFields.length, values.length); i++) {
    var el = textFields[i];
    var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    nativeSetter.call(el, values[i]);
    el.dispatchEvent(new Event('input', {bubbles: true}));
    el.dispatchEvent(new Event('change', {bubbles: true}));
}
return textFields.length;
""", [first, last, phone.lstrip("+"), pw])
print(f"1. Filled {fill} inputs")
time.sleep(1)

# Step 2: Select dropdown values using aria-label
select_js = """
function selectCombobox(ariaLabel, valueText) {
    // Find the combobox trigger
    var combobox = document.querySelector('[aria-label="' + ariaLabel + '"]');
    if (!combobox) return 'Not found: ' + ariaLabel;
    
    // Click to open dropdown
    combobox.click();
    
    // Wait briefly for dropdown to render, then find and click option
    return new Promise(function(resolve) {
        setTimeout(function() {
            var options = document.querySelectorAll('[role="option"]');
            for (var i = 0; i < options.length; i++) {
                var text = options[i].textContent.trim();
                if (text === String(valueText)) {
                    options[i].click();
                    resolve('Selected: ' + valueText + ' in ' + ariaLabel);
                    return;
                }
            }
            resolve('Option not found: ' + valueText + ' in ' + ariaLabel);
        }, 300);
    });
}

// Execute sequentially
return selectCombobox('Select day', arguments[0])
    .then(function(r1) { 
        result1 = r1;
        return selectCombobox('Select month', arguments[1]);
    })
    .then(function(r2) {
        return [result1, r2];
    });
"""

# This won't work well with async. Let me do it sync instead.
select_sync = d.execute_script("""
var results = [];
function findAndClick(ariaLabel, valueText) {
    var combobox = document.querySelector('[aria-label="' + ariaLabel + '"]');
    if (!combobox) {
        results.push('Not found: ' + ariaLabel);
        return;
    }
    combobox.click();
    // Find option in the same container - look for listbox after click
    var listbox = combobox.closest('[role="listbox"]');
    if (!listbox) {
        // Try finding any visible listbox
        listbox = document.querySelector('[role="listbox"]');
    }
    results.push('Clicked ' + ariaLabel);
}

// Select day
var dayBtn = document.querySelector('[aria-label="Select day"]');
if (dayBtn) {
    dayBtn.click();
    results.push('day opened');
    // Month list is visible by default as seen in debug
    // Find the listbox for month
}

var allCombos = document.querySelectorAll('[aria-label^="Select"]');
allCombos.forEach(function(c) { results.push(c.getAttribute('aria-label')); });

return results;
""")
print(f"2. Dropdowns: {select_sync}")
time.sleep(1)

# Let me try a different approach: directly use Playwright-style click and select
# Find all comboboxes and click them one by one
for aria in ["Select day", "Select month", "Select year"]:
    try:
        combo = d.execute_script("""
            var el = document.querySelector('[aria-label="' + arguments[0] + '"]');
            if (el) {
                el.click();
                return 'clicked';
            }
            return 'not found';
        """, aria)
        print(f"   {aria}: {combo}")
        time.sleep(0.5)
    except:
        pass

time.sleep(1)

# Now dump to see the state
elems = d.execute_script("""
var results = [];
document.querySelectorAll('[role="listbox"], [role="option"], [role="combobox"], [aria-label^="Select"], [role="radio"]').forEach(function(el) {
    var role = el.getAttribute('role') || '';
    var ariaLabel = el.getAttribute('aria-label') || '';
    var text = (el.textContent || '').trim().substring(0, 40);
    var selected = el.getAttribute('aria-selected') || '';
    results.push(role + '|' + ariaLabel + '|' + text + '|selected=' + selected);
});
return results;
""")
print("3. After clicks:", len(elems))
for e in elems[:20]:
    print(f"   {e}")

d.save_screenshot("/tmp/fb_dd.png")
print("4. Screenshot saved")

d.quit()
