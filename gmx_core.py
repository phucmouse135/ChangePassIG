import time
import os
import tempfile
import threading
import subprocess  
from selenium import webdriver 
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager 

# --- CẤU HÌNH ---
TIMEOUT_MAX = 15 
SLEEP_INTERVAL = 1 
PROXY_HOST = "127.0.0.1"

# Lock & Cache cho Driver Installer (Singleton Pattern từ config_utils)
_DRIVER_LOCK = threading.Lock()
_INSTALLER_LOCK = threading.Lock()
_CACHED_DRIVER_PATH = None

# --- CÁC HÀM HỖ TRỢ DỌN DẸP ---
def kill_orphaned_chrome():
    """Dọn dẹp các process Chrome bị treo để tránh lỗi 'cannot connect'."""
    try:
        if os.name == 'nt': # Windows
            subprocess.run("taskkill /f /im chromedriver.exe /T", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else: # Linux/Mac
            os.system("pkill -f chromedriver")
    except Exception:
        pass

def _install_driver_once():
    """Chỉ install driver 1 lần duy nhất trong suốt vòng đời app."""
    global _CACHED_DRIVER_PATH
    if _CACHED_DRIVER_PATH:
        return _CACHED_DRIVER_PATH
    
    with _INSTALLER_LOCK:
        if not _CACHED_DRIVER_PATH:
            try:
                _CACHED_DRIVER_PATH = ChromeDriverManager().install()
                print(f"[CORE] Driver installed at: {_CACHED_DRIVER_PATH}")
            except Exception as e:
                print(f"[CORE] Lỗi install driver: {e}")
                raise e
    return _CACHED_DRIVER_PATH

# --- HÀM KHỞI TẠO DRIVER (TỐI ƯU HIỆU SUẤT) ---
def get_driver(headless=False, proxy_port=None):
    """
    Initialize browser with Standard Selenium + Anti-Detect + Performance Tuning.
    Kết hợp logic của gmx_core cũ và config_utils.
    """
    
    # 1. Dọn dẹp process cũ (chỉ chạy nếu cần thiết, hoặc bỏ qua nếu chạy đa luồng liên tục)
    # kill_orphaned_chrome() 

    options = Options()
    
    # --- Proxy ---
    if proxy_port:
        proxy_server = f"http://{PROXY_HOST}:{proxy_port}"
        options.add_argument(f'--proxy-server={proxy_server}')
    
    # --- User Agent ---
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    options.add_argument(f'--user-agent={user_agent}')

    # --- Cấu hình Headless & GPU ---
    if headless:
        options.add_argument('--headless=new')
    
    options.add_argument("--window-size=1280,720") # Giảm size để nhẹ hơn
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    
    # --- PERFORMANCE OPTIMIZATIONS (Từ config_utils) ---
    # Tắt load ảnh để chạy nhanh
    options.add_argument("--blink-settings=imagesEnabled=false") 
    
    # Tắt cache ổ cứng (Disk I/O optimization)
    options.add_argument("--disable-application-cache")
    options.add_argument("--disk-cache-size=0") 
    
    # Tắt extension và infobars
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    
    # Page Load Strategy: 'eager' (DOMContentLoaded là chạy, không chờ ảnh/css)
    options.page_load_strategy = 'eager'

    # --- ANTI-DETECT ---
    options.add_argument("--disable-blink-features=AutomationControlled") 
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # --- Profile Temp ---
    profile_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={profile_dir}")
    
    prefs = {
        "profile.managed_default_content_settings.images": 2, # Block image
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)
    
    # print(f"[CORE] Opening Chrome (Headless: {headless})...")
    
    try:
        # Sử dụng Cached Driver Path
        driver_path = _install_driver_once()
        service = Service(driver_path)
        
        driver = webdriver.Chrome(service=service, options=options)
        
        # Set timeouts
        driver.set_page_load_timeout(60)
        driver.set_script_timeout(60)

        # Bypass navigator.webdriver
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })
        
        return driver
    except Exception as e:
        print(f"[CORE] Lỗi khởi tạo Driver: {e}")
        raise e

# --- CÁC HÀM LOGIC NGHIỆP VỤ (GIỮ NGUYÊN) ---

def find_element_safe(driver, by, value, timeout=TIMEOUT_MAX, click=False, send_keys=None):
    """
    Hàm tìm kiếm an toàn có tích hợp check popup GMX.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        # Check Popup quảng cáo
        if reload_if_ad_popup(driver):
             # Nếu vừa reload, reset vòng lặp để tìm lại
             pass
        
        try:
            element = driver.find_element(by, value)
            
            if click:
                try:
                    element.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", element)
                return True
            
            if send_keys:
                element.clear()
                element.send_keys(send_keys)
                return True
            
            return element 
        except Exception:
            time.sleep(SLEEP_INTERVAL)
            continue
    
    # print(f"[ERROR] Không tìm thấy: {value}")
    return None

def reload_if_ad_popup(driver, url="https://www.gmx.net/"):
    """
    Logic quan trọng: Reload về trang chủ nếu gặp popup quảng cáo "Wir finanzieren uns".
    """
    try:
        try:
            current_url = driver.current_url
        except Exception:
            current_url = ""

        # Logic 1: URL redirect
        if current_url.startswith("https://suche.gmx.net/web"):
            driver.get(url)
            time.sleep(2)
            return True

        # Logic 2: Check elements
        # Fast check by Title/Button text
        page_source = ""
        try:
            page_source = driver.page_source.lower()
        except Exception:
            pass

        if "wir finanzieren uns" in page_source:
            # Check kỹ hơn để tránh false positive
            popup_hints = [
                "werbung",
                "akzeptieren und weiter",
                "zum abo ohne fremdwerbung",
                "postfach ohne fremdwerbebanner",
            ]
            if any(hint in page_source for hint in popup_hints):
                print(">> [CORE] Phát hiện Popup Quảng cáo -> Reload GMX.")
                driver.get(url)
                time.sleep(2)
                return True

    except Exception:
        pass
    return False

# --- CÁC HÀM TIỆN ÍCH TỪ CONFIG_UTILS (MỚI THÊM) ---
def wait_element(driver, by, value, timeout=10, visible=True):
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            elements = driver.find_elements(by, value)
            if elements:
                el = elements[0]
                if not visible or el.is_displayed():
                    return el
        except Exception:
            pass
        time.sleep(0.2)
    return None

def wait_and_click(driver, by, value, timeout=10):
    el = wait_element(driver, by, value, timeout=timeout, visible=True)
    if not el: return False
    try:
        el.click()
        return True
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", el)
            return True
        except:
            return False