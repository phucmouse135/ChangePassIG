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
SUBMIT_KEYWORDS = [
    "reset",
    "continue",
    "submit",
    "save",
    "change password",
    "change",
    "next",
]
SUBMIT_NEGATIVE_KEYWORDS = ["cancel", "back"]
WAIT_AFTER_SUBMIT_SECONDS = 7
EXPIRED_LINK_MARKERS = [
    "page isn't available",
    "page isnt available",
    "this page isn't available",
    "sorry, this page isn't available",
    "the link may be broken",
    "link may be broken",
    "link has expired",
    "link is invalid",
    "invalid link",
]


class ResetLinkExpiredError(RuntimeError):
    pass


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


def _page_has_expired_marker(driver):
    try:
        source = driver.page_source or ""
    except Exception:
        source = ""
    try:
        title = driver.title or ""
    except Exception:
        title = ""
    blob = f"{title}\n{source}".lower()
    return any(marker in blob for marker in EXPIRED_LINK_MARKERS)


def _wait_for_expired_page(driver, timeout=6):
    end_time = time.time() + timeout
    while time.time() < end_time:
        if _page_has_expired_marker(driver):
            return True
        time.sleep(0.3)
    return False


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


def _normalize_text(text):
    if not text:
        return ""
    return " ".join(text.replace("\xa0", " ").split()).strip().lower()


def _button_text(el):
    try:
        text = el.text or ""
    except Exception:
        text = ""
    if not text:
        try:
            text = el.get_attribute("value") or ""
        except Exception:
            text = ""
    if not text:
        try:
            text = el.get_attribute("aria-label") or ""
        except Exception:
            text = ""
    return _normalize_text(text)


def _click_element(driver, element):
    if not element:
        return False
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
            element,
        )
    except Exception:
        pass
    try:
        element.click()
        return True
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception:
            return False


def _find_best_submit_button(driver, pass_input):
    form = None
    try:
        form = pass_input.find_element(By.XPATH, "./ancestor::form[1]")
    except Exception:
        form = None

    candidates = []
    if form:
        try:
            candidates = form.find_elements(
                By.CSS_SELECTOR, "button, input[type='submit'], input[type='button']"
            )
        except Exception:
            candidates = []
    if not candidates:
        try:
            candidates = driver.find_elements(
                By.CSS_SELECTOR, "button, input[type='submit'], input[type='button']"
            )
        except Exception:
            candidates = []

    best = None
    best_score = -1
    for el in candidates:
        text = _button_text(el)
        if text and any(bad in text for bad in SUBMIT_NEGATIVE_KEYWORDS):
            continue
        score = 0
        try:
            el_type = (el.get_attribute("type") or "").lower()
        except Exception:
            el_type = ""
        if el_type == "submit":
            score += 3
        if text:
            score += 1
        if any(k in text for k in SUBMIT_KEYWORDS):
            score += 5
        if score > best_score:
            best = el
            best_score = score
    return best, form


def _submit_password_form(driver, pass_input):
    submit_btn, form = _find_best_submit_button(driver, pass_input)
    if submit_btn and _click_element(driver, submit_btn):
        return True
    try:
        pass_input.send_keys(Keys.ENTER)
        return True
    except Exception:
        try:
            driver.execute_script(
                "arguments[0].dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', code:'Enter', bubbles:true}));"
                "arguments[0].dispatchEvent(new KeyboardEvent('keyup', {key:'Enter', code:'Enter', bubbles:true}));",
                pass_input,
            )
            return True
        except Exception:
            pass
    if form:
        try:
            driver.execute_script("arguments[0].submit();", form)
            return True
        except Exception:
            pass
    return False


def _fill_confirm_password(driver, pass_input, new_password):
    try:
        form = pass_input.find_element(By.XPATH, "./ancestor::form[1]")
    except Exception:
        form = None
    if not form:
        return
    try:
        inputs = form.find_elements(By.CSS_SELECTOR, "input[type='password']")
    except Exception:
        inputs = []
    for el in inputs:
        if el == pass_input:
            continue
        try:
            el.clear()
        except Exception:
            pass
        try:
            el.send_keys(new_password)
        except Exception:
            try:
                driver.execute_script(
                    "arguments[0].value = arguments[1];"
                    "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
                    "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                    el,
                    new_password,
                )
            except Exception:
                pass
            
def _check_if_page_broken(driver):
    """Kiểm tra xem trang có bị lỗi 'Something went wrong' hay không"""
    try:
        # Check title và body text
        src = (driver.page_source or "").lower()
        title = (driver.title or "").lower()
        text = f"{title} {src}"
        
        for marker in EXPIRED_LINK_MARKERS:
            if marker in text:
                return True
    except: pass
    return False


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
        try:
            pass_input.send_keys(new_password)
        except Exception:
            driver.execute_script(
                "arguments[0].value = arguments[1];"
                "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
                "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                pass_input,
                new_password,
            )
        try:
            current_val = pass_input.get_attribute("value") or ""
        except Exception:
            current_val = ""
        if not current_val:
            try:
                driver.execute_script(
                    "arguments[0].value = arguments[1];"
                    "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
                    "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                    pass_input,
                    new_password,
                )
            except Exception:
                pass
        _fill_confirm_password(driver, pass_input, new_password)
        time.sleep(0.4)
        if not _submit_password_form(driver, pass_input):
            print("? Warning: submit action not executed.")
    except Exception as e:
        print(f"? Error entering password: {e}")
        driver.close()
        driver.switch_to.window(original_window)
        return False

    print(f"? Waiting {WAIT_AFTER_SUBMIT_SECONDS}s after submit...")
    time.sleep(WAIT_AFTER_SUBMIT_SECONDS)

    print("   -> Back to GMX (keep reset tab open).")
    if original_window:
        driver.switch_to.window(original_window)
    return True


if __name__ == "__main__":
    mock_data = "123\tdata2\tdata3\tdata4\tdata5\tuser_ig\tMY_NEW_PASS_123"
    print("Run after Step 2 opened the reset tab.")
