# FILE: mail_handler.py
import imaplib
import email
from email.header import decode_header
import re

# --- CẤU HÌNH SERVER ---
IMAP_PORT = 993
GMX_HOST = "imap.gmx.net"
MAIL_COM_HOST = "imap.mail.com"

# --- REGEX & KEYWORDS (Pre-compile để tăng tốc) ---
RE_USER_HI = re.compile(r'Hi\s+([a-zA-Z0-9_.]+),', re.IGNORECASE)
RE_UID_LINK = re.compile(r'uid=([0-9]{6,30})')
RE_UID_FOOTER = re.compile(r'\(uid:\s*(\d{6,30})\)')

RESET_KEYWORDS = {
    "reset your password", "get back on instagram", "recover your password",
    "đặt lại mật khẩu", "truy cập lại vào instagram", "log in as"
}

CONFIRM_KEYWORDS = {
    "password has been changed", "password changed",
    "your instagram password has been changed",
    "mật khẩu đã được thay đổi", "bạn vừa thay đổi mật khẩu"
}

SENDER_FILTER = "Instagram"

def _decode_header_fast(header_value):
    """Giải mã header nhanh gọn."""
    if not header_value: return ""
    try:
        decoded_list = decode_header(header_value)
        result = []
        for content, encoding in decoded_list:
            if isinstance(content, bytes):
                result.append(content.decode(encoding or "utf-8", errors="ignore"))
            else:
                result.append(str(content))
        return "".join(result)
    except:
        return str(header_value)

def _get_body_fast(msg):
    """Lấy body nhanh, ưu tiên text/html để regex chính xác."""
    if msg.is_multipart():
        for part in msg.walk():
            # Chỉ lấy phần text/html hoặc text/plain, bỏ qua attachment
            if part.get_content_type() in ["text/html", "text/plain"]:
                try:
                    return part.get_payload(decode=True).decode("utf-8", errors="ignore")
                except: pass
    else:
        try:
            return msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        except: pass
    return ""

def verify_account_live(email_login, password, ig_user_fallback=None):
    """
    Tối ưu: Chỉ fetch Header trước, khớp Subject mới fetch Body.
    """
    host = MAIL_COM_HOST if "@mail.com" in email_login else GMX_HOST
    
    try:
        # 1. KẾT NỐI
        mail = imaplib.IMAP4_SSL(host, IMAP_PORT)
        try:
            mail.login(email_login, password)
        except:
            return "Login Mail Failed"
            
        mail.select("INBOX", readonly=True) # Readonly để an toàn và nhanh hơn
        
        # 2. TÌM KIẾM (Chỉ lấy ID)
        # Tìm mail từ Instagram
        status, messages = mail.search(None, f'(FROM "{SENDER_FILTER}")')
        
        # Fallback nếu search FROM ko ra (do server lởm) thì search ALL
        if status != "OK" or not messages[0]:
            status, messages = mail.search(None, 'ALL')
            
        if not messages[0]:
            mail.logout()
            return "Mail Empty"

        # Chỉ lấy tối đa 15 mail gần nhất
        mail_ids = messages[0].split()
        recent_ids = mail_ids[-15:] 
        
        candidate_users = set()
        if ig_user_fallback:
            candidate_users.add(ig_user_fallback.lower())
        
        found_success_mail = False
        final_user = ""

        # --- SINGLE PASS LOOP (Quét 1 lần duy nhất) ---
        for mid in reversed(recent_ids):
            try:
                # [QUAN TRỌNG] Chỉ fetch HEADER trước (Rất nhẹ)
                _, data = mail.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT)])")
                
                # Parse Subject từ data raw
                raw_header = data[0][1]
                msg_header = email.message_from_bytes(raw_header)
                subject = _decode_header_fast(msg_header["Subject"]).lower()
                
                # Cờ đánh dấu cần fetch body không
                need_body = False
                is_reset = any(kw in subject for kw in RESET_KEYWORDS)
                is_confirm = any(kw in subject for kw in CONFIRM_KEYWORDS)

                if is_reset or is_confirm:
                    need_body = True
                
                if not need_body:
                    continue

                # Nếu cần thiết mới fetch BODY (Nặng hơn)
                _, data_body = mail.fetch(mid, "(BODY.PEEK[])")
                msg_body = email.message_from_bytes(data_body[0][1])
                body_content = _get_body_fast(msg_body)
                
                # 1. Logic thu thập User/UID từ mail Reset
                if is_reset:
                    # Regex tìm user
                    m_user = RE_USER_HI.search(body_content)
                    if m_user: candidate_users.add(m_user.group(1).lower())
                    
                    # Regex tìm UID
                    m_uid = RE_UID_LINK.search(body_content)
                    if m_uid: candidate_users.add(m_uid.group(1))

                # 2. Logic check Success
                if is_confirm:
                    # Check xem user trong mail confirm có khớp candidates không
                    lower_body = body_content.lower()
                    for u in candidate_users:
                        if u in lower_body or u in subject:
                            found_success_mail = True
                            final_user = u
                            break
                    
                    # Nếu chưa có candidate nào, tạm thời tin tưởng mail confirm mới nhất
                    if not candidate_users:
                         # Cố trích xuất user từ chính mail confirm này
                         m_user = RE_USER_HI.search(body_content)
                         if m_user:
                             final_user = m_user.group(1).lower()
                             found_success_mail = True
                
                if found_success_mail:
                    break

            except Exception:
                continue

        mail.logout()
        
        if found_success_mail:
            return f"success|USER={final_user}" 
        
        if not candidate_users:
             return "Fail: No Reset/Confirm mails found"
             
        return "Fail: Confirmed Mail mismatch"

    except Exception as e:
        return f"Error: {str(e)}"