# ChangePasswordIG

Cong cu tu dong reset mat khau Instagram thong qua GMX mail.

## Tong quan luong chay
- Load cookie Instagram tu file JSON.
- Login GMX mail.
- Tim mail reset Instagram.
- Mo link reset va nhap mat khau moi.
- Xac nhan mail "password changed".

## Setup moi truong
Yeu cau:
- Python 3.10+
- Google Chrome
- Thu vien: `selenium`, `undetected-chromedriver`

Cai dat:
```bash
pip install -r requirements.txt
```

Goi y (neu bi loi download chromedriver):
- Thu chay lai, hoac dam bao mang on dinh.

## Cau hinh can co
- File cookie Instagram: duong dan mac dinh trong `main.py` (bien `IG_COOKIE_PATH`).
- File input: `input.txt` (tab-separated).

Mau input (8 cot):
```
UID add	MAIL LK IG	USER	PASS IG	2FA	PHOI GOC	PASS MAIL	MAIL KHOI PHUC
aufiei	aufiei@gmx.de	zjsigjywkg	eaaqork1S		virtualcultural2@gmx.de	eaaqork1S	virtualcultural2@teml.net
```

Giai thich cot:
- `MAIL LK IG`: GMX email login
- `PASS MAIL`: mat khau GMX (cung la mat khau IG moi)
- `PASS IG`: neu de trong, GUI se tu gan bang `PASS MAIL`
- `USER`: se duoc cap nhat tu subject mail neu tim duoc

## Chay CLI
1. Dat du lieu vao `input.txt`.
2. Chay:
```bash
python main.py
```
3. Ket qua ghi ra `output.txt`.

## Chay GUI
```bash
python gui.py
```

### Y nghia cac thanh phan giao dien
Input:
- Browse/Load: chon file input, nap vao bang.
- Paste Data: dan nhanh du lieu tab-separated.

Config:
- Threads: so luong luong chay song song.
- Headless: tat/bat giao dien trinh duyet.
- Delete Selected/All: xoa dong.

Bang du lieu:
- 8 cot tuong ung input, cot cuoi `NOTE` la trang thai.

Control:
- START: chi chay cac dong chua "Success".
- STOP: dung sau khi xu ly xong hang dang chay.
- Progress/Success/Status: thong ke tien trinh.
- Export Success/All: xuat ra file txt.

Luu y:
- GUI se tu gan `PASS IG` = `PASS MAIL` neu `PASS IG` bi trong.
- Khi chay lai, cac dong da "Success" se duoc bo qua.

## Goi y test
1. Thu 1 dong voi `Threads=1`, headless off.
2. Kiem tra GMX login va mo mail ok.
3. Khi on dinh moi tang so luong threads.

## Notes
- Duong dan cookie Instagram nam trong `main.py` (`IG_COOKIE_PATH`).
- Neu GMX UI thay doi, cap nhat selector trong `step2_get_link.py` hoac `mail_handler.py`.
