# canva_login.py
# Usage: python canva_login.py <email> <code> <invite_link>

import sys
import time
from playwright.sync_api import sync_playwright

if len(sys.argv) != 4:
    print("Usage: python canva_login.py <email> <code> <invite_link>")
    sys.exit(1)

email = sys.argv[1]
code = sys.argv[2]
invite_link = sys.argv[3]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        page.goto("https://www.canva.com")
        page.click("text=Log in")
        page.fill("input[type=email]", email)
        page.click("text=Continue")

        # Wait for verification screen
        page.wait_for_selector("input[aria-label='Enter code']", timeout=10000)
        page.fill("input[aria-label='Enter code']", code)
        page.click("text=Submit")

        # Wait for user to land in account
        page.wait_for_url("**/home", timeout=15000)

        # Now go to invite link
        page.goto(invite_link)

        # Check if the team is full or expired
        if page.query_selector("text=This invite link is invalid") or page.query_selector("text=team is full"):
            print("failed: team full or invite expired")
            browser.close()
            sys.exit(1)

        # Click Join button if available
        join_button = page.query_selector("button:has-text('Join team')")
        if join_button:
            join_button.click()
            time.sleep(5)
            print("success")
        else:
            print("failed: join button not found")

    except Exception as e:
        print(f"error: {str(e)}")
    finally:
        browser.close()
