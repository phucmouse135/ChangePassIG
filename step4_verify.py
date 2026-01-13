import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

# --- CONFIG ---
CONFIRM_KEYWORDS = [
    "password has been changed",
    "password changed",
    "your instagram password has been changed",
]
SENDER_NAME = "instagram"
MAIL_FRAME_ID = "thirdPartyFrame_mail"
MAIL_ITEMS_JS = """
const listHost =
  document.querySelector("#list > mail-list-container") ||
  document.querySelector("mail-list-container");
if (!listHost || !listHost.shadowRoot) return [];
let listMailList = listHost.shadowRoot.querySelector(
  "div > div.webmailer-mail-list__list-container > list-mail-list"
);
if (!listMailList) {
  listMailList = listHost.shadowRoot.querySelector("list-mail-list");
}
if (!listMailList || !listMailList.shadowRoot) return [];
let list = listMailList.shadowRoot.querySelector("div > div.list-mail-list");
if (!list) {
  list = listMailList.shadowRoot.querySelector("div.list-mail-list");
}
if (!list) {
  list = listMailList.shadowRoot;
}
return Array.from(list.querySelectorAll("list-mail-item"));
"""


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


def _safe_call(label, func, default=None):
    try:
        return func()
    except Exception as exc:
        print(f"?? [{label}] {exc}")
        return default


def _safe_text(root, selector):
    try:
        return root.find_element(By.CSS_SELECTOR, selector).text.strip().lower()
    except Exception:
        return ""


def _is_unread(item):
    class_attr = (item.get_attribute("class") or "").lower()
    return "list-mail-item--unread" in class_attr


def _matches_confirm(item):
    sender = _safe_text(item, "div.list-mail-item__sender-trusted-text")
    subject = _safe_text(item, "div.list-mail-item__subject")
    full_text = (sender + " " + subject).strip()
    if SENDER_NAME not in full_text:
        full_text = (item.text or "").lower()
        if not full_text:
            try:
                full_text = (item.get_attribute("innerText") or "").lower()
            except Exception:
                full_text = ""
        if SENDER_NAME not in full_text:
            return False
    keywords = [kw.lower() for kw in CONFIRM_KEYWORDS]
    return any(kw in full_text for kw in keywords)


def _switch_to_mail_frame(driver):
    try:
        driver.switch_to.default_content()
    except Exception:
        pass
    frame = None
    try:
        frame = driver.find_element(By.ID, MAIL_FRAME_ID)
    except Exception:
        pass
    if not frame:
        try:
            frame = driver.find_element(
                By.CSS_SELECTOR, "#thirdPartyFrame_mail, iframe[name='mail']"
            )
        except Exception:
            return False
    try:
        driver.switch_to.frame(frame)
        return True
    except Exception:
        return False


def wait_mail_frame_ready(driver, timeout=15):
    end_time = time.time() + timeout
    while time.time() < end_time:
        if not _switch_to_mail_frame(driver):
            time.sleep(0.5)
            continue
        try:
            ready = driver.execute_script(
                "return !!document.querySelector('#list > mail-list-container');"
            )
            if ready:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _get_mail_items_shadow(driver):
    if not _switch_to_mail_frame(driver):
        return []
    try:
        items = driver.execute_script(MAIL_ITEMS_JS)
        return items or []
    except Exception:
        return []


def wait_page_ready(driver, timeout=15):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass


def wait_mail_list_loaded(driver, timeout=15):
    if not wait_mail_frame_ready(driver, timeout=min(8, timeout)):
        return False
    end_time = time.time() + timeout
    while time.time() < end_time:
        items = _get_mail_items_shadow(driver)
        if items:
            return True
        container = _find_mail_list_container(driver)
        if container:
            items = container.find_elements(By.CSS_SELECTOR, "list-mail-item")
            if items:
                return True
        time.sleep(0.5)
    return False


def _find_mail_list_container(driver):
    try:
        driver.switch_to.default_content()
    except Exception:
        pass
    container = _find_element_in_frames(driver, By.CSS_SELECTOR, "div.list-mail-list")
    return container


def scan_mail_items(driver):
    items = _get_mail_items_shadow(driver)
    if items:
        return items
    container = _find_mail_list_container(driver)
    if container:
        items = container.find_elements(By.CSS_SELECTOR, "list-mail-item")
        if items:
            return items
    return _find_elements_in_frames(driver, By.TAG_NAME, "list-mail-item")


def execute_step4(driver):
    print("--- [STEP 4] VERIFY CONFIRM MAIL ---")

    _safe_call("PageReady", lambda: wait_page_ready(driver, timeout=15))
    _safe_call("MailFrameReady", lambda: wait_mail_frame_ready(driver, timeout=15))
    _safe_call("MailListReady", lambda: wait_mail_list_loaded(driver, timeout=15))

    max_retries = 4
    for i in range(max_retries):
        print(f"   -> Check {i+1}/{max_retries}...")
        _safe_call("Refresh", driver.refresh)
        _safe_call("PageReady", lambda: wait_page_ready(driver, timeout=15))
        _safe_call("MailFrameReady", lambda: wait_mail_frame_ready(driver, timeout=15))
        _safe_call("MailListReady", lambda: wait_mail_list_loaded(driver, timeout=15))

        mail_items = _safe_call("ScanMail", lambda: scan_mail_items(driver), [])
        if not mail_items:
            print("   ... Mail list not loaded, retry.")
            continue

        found = False
        for item in mail_items:
            try:
                if _is_unread(item) and _matches_confirm(item):
                    print(f"? [SUCCESS] Confirm mail found: {(item.text or '')[:60]}...")
                    found = True
                    break
            except Exception:
                continue

        if found:
            return True

        print("   ... Not found yet, wait 10s.")
        time.sleep(10)

    print("? [FAIL] Timeout waiting for confirm mail.")
    return False


if __name__ == "__main__":
    print("Run after Step 1-3 are done.")
