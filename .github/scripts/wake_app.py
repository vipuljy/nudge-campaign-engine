"""Open the app like a visitor; if Streamlit shows its sleep page, press the wake-up button and wait for the app to start."""
import re
import sys

from playwright.sync_api import sync_playwright

url = sys.argv[1]
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(url, wait_until='domcontentloaded', timeout=120_000)
    page.wait_for_timeout(8_000)
    button = page.get_by_role('button', name=re.compile('get this app back up', re.I))
    if button.count():
        button.first.click()
        print('The app was asleep: wake-up button pressed.')
        page.wait_for_timeout(90_000)          # give the app time to start
    else:
        print('The app is awake.')
        page.wait_for_timeout(20_000)          # stay a moment, like a real visit
    browser.close()
