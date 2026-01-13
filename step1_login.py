# FILE: step1_login.py
import time
from selenium.webdriver.common.by import By
from gmx_core import get_driver, find_element_safe, reload_if_ad_popup

# --- DATA TEST DEFAULT ---
DEF_USER = "saucycut1@gmx.de"
DEF_PASS = "muledok5P"

def login_process(driver, user, password):
    """
    Standard Login Function.
    Returns True if login success, False if failed.
    """
    try:
        print(f"--- START LOGIN PROCESS: {user} ---")
        
        # 1. Enter site
        driver.get("https://www.gmx.net/")
        time.sleep(3)
        driver.get("https://www.gmx.net/") # Reload

        def abort_if_ad_popup():
            if reload_if_ad_popup(driver):
                print("?? Ad popup detected. Reloaded to GMX home.")
                return True
            return False

        if abort_if_ad_popup():
            return False
        
        # 2. Handle Consent
        print("-> Check Consent...")
        find_element_safe(driver, By.ID, "onetrust-accept-btn-handler", timeout=5, click=True)
        if abort_if_ad_popup():
            return False

        # 3. LOGIC FIND LOGIN FORM (FAST-SCAN MAIN/IFRAME)
        print("-> Scanning for Login Form (Main or Iframe)...")

        user_selectors = [
            (By.CSS_SELECTOR, "input[data-testid='input-email']"),
            (By.NAME, "username"),
            (By.ID, "username"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.XPATH, "//input[@autocomplete='username']")
        ]

        button_selectors = [
            (By.CSS_SELECTOR, "button[data-testid='login-submit']"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.ID, "login-submit")
        ]

        password_selectors = [
            (By.CSS_SELECTOR, "input[data-testid='input-password']"),
            (By.ID, "password"),
            (By.NAME, "password"),
            (By.XPATH, "//input[@type='password']")
        ]

        fast_scan_interval = 0.2

        if abort_if_ad_popup():
            return False

        def fast_find_any(selectors):
            for by_f, val_f in selectors:
                try:
                    elements = driver.find_elements(by_f, val_f)
                except Exception:
                    elements = []
                if elements:
                    return elements[0], (by_f, val_f)
            return None, None

        def fast_locate_in_frames(selectors, timeout=6, prefer_iframe_index=None):
            end_time = time.time() + timeout
            while time.time() < end_time:
                if abort_if_ad_popup():
                    return None, None

                if prefer_iframe_index is not None:
                    try:
                        driver.switch_to.default_content()
                        iframes = driver.find_elements(By.TAG_NAME, "iframe")
                        if prefer_iframe_index < len(iframes):
                            driver.switch_to.frame(iframes[prefer_iframe_index])
                            element, _ = fast_find_any(selectors)
                            if element:
                                return prefer_iframe_index, element
                    except Exception:
                        pass

                try:
                    driver.switch_to.default_content()
                except Exception:
                    pass

                element, _ = fast_find_any(selectors)
                if element:
                    return None, element

                try:
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                except Exception:
                    iframes = []

                for idx, iframe in enumerate(iframes):
                    try:
                        driver.switch_to.default_content()
                        driver.switch_to.frame(iframe)
                        element, _ = fast_find_any(selectors)
                        if element:
                            return idx, element
                    except Exception:
                        continue

                time.sleep(fast_scan_interval)

            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            return None, None

        def click_element(element):
            try:
                element.click()
                return True
            except Exception:
                try:
                    driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception:
                    return False

        def type_into_element(element, text):
            try:
                element.clear()
            except Exception:
                pass
            try:
                element.send_keys(text)
                return True
            except Exception:
                try:
                    driver.execute_script("arguments[0].value = arguments[1];", element, text)
                    driver.execute_script(
                        "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
                        element
                    )
                    return True
                except Exception:
                    return False

        current_iframe_index, user_input = fast_locate_in_frames(user_selectors, timeout=8)
        if abort_if_ad_popup():
            return False
        if user_input:
            location = "Main Content" if current_iframe_index is None else f"Iframe #{current_iframe_index + 1}"
            print(f"   Found Login Input in {location} (fast scan)")
        else:
            print("? Login input not found in main/iframes.")
            return False

        # 5. ENTER USERNAME (Context is correct after scan)
        print("-> Entering Username...")
        if abort_if_ad_popup():
            return False
        filled = type_into_element(user_input, user)
        if not filled:
            for by_u, val_u in user_selectors:
                if find_element_safe(driver, by_u, val_u, send_keys=user):
                    filled = True
                    break

        if not filled:
            print("? Still cannot enter Username after scan.")
            return False

        print(f"   Entered: {user}")

        # 6. CLICK NEXT/WEITER
        print("-> Clicking Next/Weiter...")
        if abort_if_ad_popup():
            return False
        # Priority: data-testid -> type=submit -> id
        current_iframe_index, next_button = fast_locate_in_frames(
            button_selectors,
            timeout=4,
            prefer_iframe_index=current_iframe_index
        )
        if not next_button or not click_element(next_button):
            if not find_element_safe(driver, By.CSS_SELECTOR, "button[data-testid='login-submit']", click=True):
                if not find_element_safe(driver, By.CSS_SELECTOR, "button[type='submit']", click=True):
                    if not find_element_safe(driver, By.ID, "login-submit", click=True):
                        print("? Next button not found.")
                        # return False # Try continuing

        # 7. ENTER PASSWORD
        print("-> Entering Password...")
        if abort_if_ad_popup():
            return False
        # Priority: data-testid -> id -> name -> xpath
        current_iframe_index, password_input = fast_locate_in_frames(
            password_selectors,
            timeout=10,
            prefer_iframe_index=current_iframe_index
        )
        if not password_input or not type_into_element(password_input, password):
            if not find_element_safe(driver, By.CSS_SELECTOR, "input[data-testid='input-password']", timeout=10, send_keys=password):
                if not find_element_safe(driver, By.ID, "password", send_keys=password):
                    if not find_element_safe(driver, By.NAME, "password", send_keys=password):
                        if not find_element_safe(driver, By.XPATH, "//input[@type='password']", send_keys=password):
                            print("? Password input not found.")
                            return False
        print("   Password entered.")

        # 8. CLICK LOGIN FINAL
        # Priority: data-testid -> type=submit
        if abort_if_ad_popup():
            return False
        current_iframe_index, login_button = fast_locate_in_frames(
            button_selectors,
            timeout=4,
            prefer_iframe_index=current_iframe_index
        )
        if not login_button or not click_element(login_button):
            if not find_element_safe(driver, By.CSS_SELECTOR, "button[data-testid='login-submit']", click=True):
                find_element_safe(driver, By.CSS_SELECTOR, "button[type='submit']", click=True)
        print("-> Clicked Login.")

        # 9. CHECK RESULT
        driver.switch_to.default_content()
        print("-> Waiting for redirection...")
        
        for _ in range(20):
            if "navigator" in driver.current_url:
                print(f"✅ [PASS] Login Success! URL: {driver.current_url}")
                return True
            time.sleep(1)
            
        print("❌ [FAIL] Timeout: Did not reach navigator page.")
        return False

    except Exception as e:
        print(f"❌ [FAIL] Login Error: {e}")
        return False

# Test run if file executed directly
if __name__ == "__main__":
    import os
    INPUT_TEST = "input.txt"
    
    if os.path.exists(INPUT_TEST):
        print(f"--- BULK TEST MODE: Reading {INPUT_TEST} ---")

        output_path = "output.txt"
        try:
            with open(INPUT_TEST, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # Skip header if present
            start_line = 0
            if len(lines) > 0 and "UID" in lines[0]:
                start_line = 1
            # Prepare output file (overwrite)
            with open(output_path, "w", encoding="utf-8") as fout:
                fout.write("uid\tresult\n")
                for idx, line in enumerate(lines[start_line:]):
                    line = line.strip()
                    if not line: continue
                    parts = line.split('\t')
                    if len(parts) < 2: parts = line.split()
                    # Assume Format: ... [User Col 5] [Pass Col 6]
                    if len(parts) >= 7:
                        t_uid = parts[0]
                        t_user = parts[5]
                        t_pass = parts[6]
                        print(f"\n[{idx+1}] Testing Account: {t_user}")
                        driver = get_driver(headless=False)
                        try:
                            login_success = login_process(driver, t_user, t_pass)
                            print(f"Result {t_user}: {'OK' if login_success else 'FAIL'}")
                            fout.write(f"{t_uid}\t{'success' if login_success else 'fail'}\n")
                        except Exception as e:
                            print(f"Error {t_user}: {e}")
                            fout.write(f"{t_uid}\tfail\n")
                        finally:
                            try: driver.quit()
                            except: pass
                    else:
                        print(f"Skipping invalid line: {line}")
        except Exception as e:
            print(f"File read error: {e}")
            
    else:
        print("--- SINGLE TEST DEFAULT ---")
        driver = get_driver()
        try:
            login_process(driver, DEF_USER, DEF_PASS)
        except Exception:
            pass
        finally:
            try: driver.quit()
            except: pass
# FILE: gmx_core.py