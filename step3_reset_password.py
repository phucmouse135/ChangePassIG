import time
from urllib.parse import parse_qs, unquote, urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


PASSWORD_XPATH = (
    "/html/body/div[1]/div/div[1]/div[2]/div/div/div[1]/div[1]/div/div/div/"
    "div[1]/div[1]/div/div/div/div/div/div[1]/div[2]/form/div/div/div[4]/"
    "div/div/div[1]/input"
)
RESET_URL_HINTS = [
    "instagram.com/accounts/password/reset/confirm",
    "instagram.com/accounts/password/reset",
    "password/reset/confirm",
    "one_click_login_email",
    "deref-gmx.net/mail/client",
    "redirecturl=",
]


def _find_element_in_frames(driver, by, value, depth=0, max_depth=3):
    try:
        return driver.find_element(by, value)
    except Exception:
        pass

    if depth >= max_depth:
        return None

    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for frame in frames:
        try:
            driver.switch_to.frame(frame)
            found = _find_element_in_frames(driver, by, value, depth + 1, max_depth)
            if found:
                return found
            driver.switch_to.parent_frame()
        except Exception:
            try:
                driver.switch_to.parent_frame()
            except Exception:
                pass
    return None


def _find_elements_in_frames(driver, by, value, depth=0, max_depth=3):
    try:
        elements = driver.find_elements(by, value)
        if elements:
            return elements
    except Exception:
        pass

    if depth >= max_depth:
        return []

    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for frame in frames:
        try:
            driver.switch_to.frame(frame)
            elements = _find_elements_in_frames(driver, by, value, depth + 1, max_depth)
            if elements:
                return elements
            driver.switch_to.parent_frame()
        except Exception:
            try:
                driver.switch_to.parent_frame()
            except Exception:
                pass
    return []


def wait_element_any_frame(driver, by, value, timeout=10):
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass
        el = _find_element_in_frames(driver, by, value)
        if el:
            try:
                if el.is_displayed():
                    return el
            except Exception:
                return el
        time.sleep(0.5)
    return None


def _wait_for_url(driver, timeout=10):
    end_time = time.time() + timeout
    url = ""
    while time.time() < end_time:
        try:
            url = driver.current_url or ""
        except Exception:
            url = ""
        if url and url != "about:blank":
            return url
        time.sleep(0.3)
    return url


def _wait_for_new_window(driver, previous_handles, timeout=10):
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            handles = driver.window_handles
        except Exception:
            handles = []
        for handle in handles:
            if handle not in previous_handles:
                return handle
        time.sleep(0.3)
    return ""


def _is_reset_url(url):
    if not url:
        return False
    url_low = url.lower()
    return any(hint in url_low for hint in RESET_URL_HINTS)


def _open_url_in_new_tab(driver, url, timeout=10):
    if not url:
        return ""
    previous_handles = set(driver.window_handles)
    try:
        driver.execute_script("window.open(arguments[0], '_blank');", url)
    except Exception:
        try:
            driver.execute_script("window.open('about:blank', '_blank');")
        except Exception:
            return ""
    new_handle = _wait_for_new_window(driver, previous_handles, timeout=timeout)
    if not new_handle:
        return ""
    try:
        driver.switch_to.window(new_handle)
        driver.get(url)
    except Exception:
        pass
    return new_handle


def _pick_reset_handle(driver, reset_url=""):
    handles = []
    try:
        handles = driver.window_handles
    except Exception:
        handles = []

    reset_handle = getattr(driver, "reset_handle", "")
    if reset_handle and reset_handle in handles:
        return reset_handle

    for handle in handles:
        try:
            driver.switch_to.window(handle)
            url = _wait_for_url(driver, timeout=4)
        except Exception:
            url = ""
        if _is_reset_url(url):
            return handle

    if reset_url:
        new_handle = _open_url_in_new_tab(driver, reset_url, timeout=12)
        if new_handle:
            return new_handle
    return ""


def _navigate_if_deref(driver, timeout=10):
    url = _wait_for_url(driver, timeout=timeout)
    if not url:
        return ""
    url_low = url.lower()
    if "deref" not in url_low:
        return url
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        redirect_vals = qs.get("redirectUrl") or qs.get("redirecturl") or []
        if redirect_vals:
            target = unquote(redirect_vals[0])
            if target:
                driver.get(target)
                return target
    except Exception:
        pass
    return url


def find_elements_any_frame(driver, by, value):
    try:
        driver.switch_to.default_content()
    except Exception:
        pass
    return _find_elements_in_frames(driver, by, value)


def execute_step3(driver, row_data_line):
    print("--- [STEP 3] ENTER NEW PASSWORD ---")

    try:
        parts = row_data_line.split("\t")
        if len(parts) < 2:
            parts = row_data_line.split()
        new_password = parts[6].strip()
        print(f"   -> New password (Index 6): {new_password}")
    except IndexError:
        print("? Input error: not enough columns for password.")
        return False

    if not new_password:
        print("? Input error: password is empty.")
        return False

    handles = []
    try:
        handles = driver.window_handles
    except Exception:
        handles = []
    original_window = handles[0] if handles else ""
    reset_url_hint = getattr(driver, "reset_url", "")
    reset_handle = _pick_reset_handle(driver, reset_url_hint)
    if not reset_handle and len(handles) >= 2:
        reset_handle = handles[-1]
    if not reset_handle:
        print("? No reset tab found (Instagram not opened).")
        return False

    driver.switch_to.window(reset_handle)
    print(f"   -> Switched to tab: {driver.title}")
    reset_url = _navigate_if_deref(driver, timeout=12)
    if reset_url:
        print(f"   -> Reset URL: {reset_url}")

    pass_input = wait_element_any_frame(driver, By.XPATH, PASSWORD_XPATH, timeout=20)
    if not pass_input:
        inputs = find_elements_any_frame(driver, By.CSS_SELECTOR, "input[type='password']")
        if inputs:
            pass_input = inputs[0]

    if not pass_input:
        print("? Password input not found.")
        driver.close()
        driver.switch_to.window(original_window)
        return False

    try:
        pass_input.click()
        pass_input.clear()
        pass_input.send_keys(new_password)
        time.sleep(1)
        pass_input.send_keys(Keys.ENTER)
    except Exception as e:
        print(f"? Error entering password: {e}")
        driver.close()
        driver.switch_to.window(original_window)
        return False

    print("? Waiting 10s for Instagram to process...")
    time.sleep(10)

    print("   -> Back to GMX (keep reset tab open).")
    if original_window:
        driver.switch_to.window(original_window)
    return True


if __name__ == "__main__":
    mock_data = "123\tdata2\tdata3\tdata4\tdata5\tuser_ig\tMY_NEW_PASS_123"
    print("Run after Step 2 opened the reset tab.")
