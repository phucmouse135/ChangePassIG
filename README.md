# ChangePasswordIG

Automation flow:
- Load Instagram cookies from `Wed New Instgram  2026 .json`
- Login GMX mailbox
- Find unread Instagram reset mail
- Open reset link and set new password
- Confirm "password changed" mail

## Requirements
- Python 3.10+
- Google Chrome installed
- Packages: `selenium`, `undetected-chromedriver`

Install dependencies:
```bash
pip install -r requirements.txt
```

## Input format
Tab-separated file (e.g. `input.txt`) with 8 columns:
```
UID add	MAIL LK IG	USER	PASS IG	2FA	PHOI GOC	PASS MAIL	MAIL KHOI PHUC
aufiei	aufiei@gmx.de	zjsigjywkg	eaaqork1S		virtualcultural2@gmx.de	eaaqork1S	virtualcultural2@teml.net
```

Notes:
- `MAIL LK IG` = GMX email login
- `PASS MAIL` = GMX password (also used as new IG password)
- `USER` is used only for output logging

## Run CLI
1. Put data into `input.txt` in the project folder.
2. Run:
```bash
python main.py
```
3. Output is written to `output.txt`.

## Run GUI
```bash
python gui.py
```
GUI features:
- Browse and load input file (auto loads into table)
- Paste data dialog
- Thread count + headless toggle
- Start/Stop processing
- Export success rows or all rows

## Test guidance
1. Start with 1 row and `Threads=1` (headless off).
2. Verify GMX login and inbox load.
3. Check the reset flow completes and a "password changed" mail appears.
4. Increase thread count after single row works.

## Notes
- Cookie file path is hardcoded in `main.py` (`IG_COOKIE_PATH`).
- If GMX UI changes, update selectors in `mail_handler.py`.
