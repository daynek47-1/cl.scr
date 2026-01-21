# Automation & Porting Plan (WSL/Playwright)

**Target Environment:** Windows 11 (WSL2 - Ubuntu/Debian)
**Shell:** ZSH
**Framework:** Playwright (Python)

## 1. Environment Migration (WSL Setup)

Moving from Termux/Android to WSL requires setting up the proper dependencies for browser automation.

### 1.1 Prerequisites
In your WSL terminal:
```zsh
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and Pip
sudo apt install python3 python3-pip python3-venv -y

# Install browser dependencies (crucial for WSL)
sudo apt install libgtk-3-0 libasound2 libgbm1 libnspr4 libnss3 libx11-xcb1 libxss1 libxtst6 xdg-utils -y
```

### 1.2 Project Setup
```zsh
# Clone your repo (if not copying files directly)
git clone <your-repo-url>
cd cl.scr

# Create Virtual Environment (Recommended)
python3 -m venv venv
source venv/bin/activate

# Install Dependencies
pip install -r requirements.txt
pip install playwright

# Install Playwright Browsers
playwright install chromium
playwright install-deps  # Installs any missing system libs
```

### 1.3 Running Headless vs. Headed
- **Headless (Default):** Runs without UI. Perfect for WSL.
- **Headed (UI):** Requires WSLg (built-in to Windows 11) or an X Server (VcXsrv). Windows 11 handles this automatically mostly.
    - Test it: `python3 -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(headless=False); page=b.new_page(); page.goto('http://google.com'); print(page.title()); b.close()"`

## 2. Automation Architecture (Auto-Claiming)

We will implement a `Claimer` engine using **Playwright**.

### 2.1 Why Playwright?
- **Speed:** Faster than Selenium.
- **Resilience:** Auto-waits for elements (no more `time.sleep(2)`).
- **Stealth:** Better at avoiding bot detection than standard Selenium.
- **Contexts:** Can maintain separate browser contexts (cookies/sessions) for different casino accounts easily.

### 2.2 New Module: `src/engine/claimer.py`

```python
from playwright.async_api import async_playwright
import asyncio

class BonusClaimer:
    async def claim_bonus(self, url, username, password, bonus_code=None):
        async with async_playwright() as p:
            # Launch browser (Headless for production)
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."
            )
            page = await context.new_page()
            
            # 1. Login
            await page.goto("https://casino-site.com/login")
            await page.fill("input[name='username']", username)
            await page.fill("input[name='password']", password)
            await page.click("button[type='submit']")
            
            # Wait for login success (e.g., check for 'Logout' button or balance)
            await page.wait_for_selector(".user-balance", timeout=10000)
            
            # 2. Navigate to Bonus
            await page.goto(url)
            
            # 3. Perform Claim Action
            if bonus_code:
                await page.fill("#bonus-code-input", bonus_code)
                await page.click("#redeem-btn")
            else:
                await page.click(".claim-bonus-btn")
            
            # 4. Verify Success
            success = await page.is_visible(".success-message")
            screenshot_path = f"logs/claims/claim_{username}_{bonus_code}.png"
            await page.screenshot(path=screenshot_path)
            
            await browser.close()
            return success, screenshot_path
```

### 2.3 Integration with Dashboard
1.  **Backend:** Add `POST /api/claim/auto` endpoint.
2.  **Worker:** Run `BonusClaimer` in a background task (async).
3.  **UI:** Add "Auto Claim" button next to "Manual Claim".
4.  **Feedback:** Stream screenshots or status logs to the dashboard via WebSocket.

## 3. Development Roadmap

### Phase 1: Setup & Prototype
- [ ] Set up WSL environment.
- [ ] Install Playwright.
- [ ] Create `src/engine/claimer.py`.
- [ ] Write a simple script to test logging into **one** specific casino site.

### Phase 2: Generalized Selectors
- [ ] Analyze different mirror sites to find common CSS selectors for:
    - Login inputs (`name="username"`, `id="login"`, etc.)
    - Claim buttons (text="Claim", class="btn-bonus").
- [ ] Create a `SelectorMap` in `src/engine/claimer.py` to map domains to selector strategies.

### Phase 3: Dashboard Integration
- [ ] Connect `BonusClaimer` to the FastAPI backend.
- [ ] Display the "Proof of Claim" screenshot in the Dashboard "Logs" tab.

## 4. Risks & Mitigations
- **Captchas:** Playwright cannot solve generic captchas automatically.
    - *Mitigation:* Use "Headed" mode on Windows to solve manually, save cookies (state), and reuse session.
- **2FA:** If sites require 2FA, automation stops.
- **Detection:** Aggressive claiming might flag accounts. Use random delays (human mimicry) and realistic mouse movements.
