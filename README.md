# Using Antigravity Prompt Engineering to Build a Custom AlmaLinux API Server (ATTRial)

Built through **Google Antigravity prompt engineering**, this project creates and provisions a custom production-style **AlmaLinux** image and text server (**FastAPI + SQLite + Uvicorn + systemd + Nginx + SELinux + firewalld**) that users access over the network via a **REST API**, an interactive **Visual Web GUI**, and a **Windows Desktop Client (PySide6)**.

An AlmaLinux VM (VirtualBox) acts as a realistic production server. Users interact with the server through HTTP API endpoints (`/api/...`), an interactive Web GUI (`/` or `/ui`), Swagger docs (`/docs`), or the compiled Windows desktop app (`ATTRialClient.exe`), uploading **text and/or images** and browsing or rotating **background images** with automatic two-way sync to the AlmaLinux `/home/daviddcn/Downloads/background images` folder.

```
Desktop app / Browser (Windows) ──HTTP over LAN──▶ AlmaLinux VM (192.168.1.11)
                                                     firewalld :80 → nginx :80 → uvicorn/FastAPI :8000 (systemd)
                                                     /srv/imgserver/data/{backgrounds,uploads,metadata.db}
                                                     ↕ two-way sync (/home/daviddcn/Downloads/background images)
```

## Repository layout
| Path | What it is |
|---|---|
| `server/app/` | FastAPI API & Web GUI (`main.py`, `ui.py`, `db.py`, `storage.py`, `config.py`) |
| `server/tests/` | `pytest` API & GUI test suite (`test_api.py`) |
| `deploy/` | `setup.sh` (provisioning), `imgserver.service` (systemd), `nginx-imgserver.conf`, `imgserver.env.example` |
| `deploy.ps1` | One-command Windows PowerShell deploy script (`scp` + `ssh` to run `deploy/setup.sh`) |
| `desktop/` | PySide6 desktop client (`main.py`, `api_client.py`, `ui/`) |
| `ATTRial_Server_Architecture_and_Debugging_Guide.pdf` | End-to-end production architecture & AlmaLinux debugging walkthrough |
| `ATTRial_Micro_Level_Network_and_Tech_Guide.pdf` | Micro-level networking, port forwarding, Nginx, systemd, SELinux, and FastAPI guide |

---

## 1. Put the VM on your network (VirtualBox Bridged Adapter)
1. Shut down the VM.
2. In **VirtualBox → Prod-DBase-Server → Settings → Network → Adapter 1**, set
   **Attached to: Bridged Adapter** and choose the PC's active Wi-Fi or Ethernet adapter.
3. Start the VM, log in, and find its IP address:
   ```bash
   ip -4 addr        # look for something like 192.168.1.50
   ```
4. *(Recommended)* Give it a fixed IP so the address never changes: run `sudo nmtui` →
   *Edit a connection* → IPv4 *Manual*. Alternatively, reserve the IP in your router.
5. Enable SSH so you can manage the VM from Windows:
   ```bash
   sudo systemctl enable --now sshd
   ```

From Windows, `ping 192.168.1.50` should now get replies.

## 2. Deploy the server to the VM
From PowerShell on Windows, you can run the one-command deploy script (`.\deploy.ps1`), or copy manually:
```powershell
scp -r server deploy youruser@192.168.1.50:~/attrial/
ssh youruser@192.168.1.50
```
Then on the VM:
```bash
cd ~/attrial
sudo bash deploy/setup.sh
```
The script installs Python, nginx and the dependencies, creates the `imgserver` service
user, opens port 80 in firewalld, configures SELinux, syncs `/home/daviddcn/Downloads/background images`, and starts everything. It prints the
**admin API key** (saved in `/etc/imgserver/imgserver.env`) and the URL to use.

To deploy a new version, re-run `.\deploy.ps1` (or copy the files again and re-run `setup.sh`). Your data and API
key are kept.

## 3. Add background images
Use either option:
- **Copy files** into the folder, then restart the service (any new image files are registered at startup):
  ```bash
  sudo cp *.jpg /srv/imgserver/data/backgrounds/
  sudo chown imgserver:imgserver /srv/imgserver/data/backgrounds/*
  sudo systemctl restart imgserver
  ```
- **Upload through the API** (admin key required):
  ```powershell
  curl.exe -H "X-API-Key: <key>" -F "image=@C:\pics\sunset.jpg" http://192.168.1.50/api/backgrounds
  ```

## 4. Run the desktop app
```powershell
cd d:\ATTRial
python -m venv .venv
.\.venv\Scripts\pip install -r desktop\requirements.txt
.\.venv\Scripts\python desktop\main.py
```
Enter `http://192.168.1.50` and click **Connect**. The app shows a server background
(rotating every 60 s, or click **Next background**). You can upload text and images,
optionally ticking **Also use this image as a background**, and turn earlier uploads into
backgrounds with **Make background**.

**Build a standalone `.exe`:**
```powershell
.\.venv\Scripts\pip install pyinstaller
.\.venv\Scripts\pyinstaller --noconfirm --windowed --name ATTRialClient desktop\main.py
# → dist\ATTRialClient\ATTRialClient.exe
```

---

## API & Web GUI reference
- **Visual Web GUI (view backgrounds, upload images/text, live request log):** **`http://<server-ip>/`** (or `/ui`)
- **Interactive Swagger API docs:** **`http://<server-ip>/docs`**

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/` or `/ui` | Interactive Visual Web GUI |
| GET | `/api/health` | status, version, background count, upload count, mirror folder |
| GET | `/api/database` | unified SQLite metadata & disk file overview (`backgrounds` + `uploads`) |
| GET | `/api/backgrounds` | list (JSON) |
| GET | `/api/backgrounds/random` | image bytes; header `X-Background-Id` |
| GET | `/api/backgrounds/{id}` | image bytes |
| POST | `/api/backgrounds` | **admin**; form fields `image`, optional `name` |
| DELETE | `/api/backgrounds/{id}` | **admin**; the original upload is kept |
| POST | `/api/uploads` | form fields `text?`, `image?`, `add_as_background` (bool) |
| GET | `/api/uploads?limit=&offset=` | newest first; includes `is_background` |
| GET | `/api/uploads/{id}` | metadata |
| GET | `/api/uploads/{id}/image` | image bytes |
| POST | `/api/uploads/{id}/promote` | make the uploaded image a background (calling it again is safe) |
| DELETE | `/api/uploads/{id}` | **admin**; a promoted background copy is kept |

Admin endpoints need the header `X-API-Key: <key>`. Limits: JPEG, PNG, WebP, AVIF, GIF or BMP (the
file's actual magic-byte contents are checked), 10 MB per image, 5,000 characters of text. Change
these in `/etc/imgserver/imgserver.env`, then run `sudo systemctl restart imgserver`.

## Local development (no VM)
```powershell
.\.venv\Scripts\pip install -r server\requirements-dev.txt
cd server
..\.venv\Scripts\python -m pytest -q
..\.venv\Scripts\uvicorn app.main:app --reload      # http://127.0.0.1:8000/docs
```
Locally, data goes to `server/data/` and the admin key is `change-me`.

## Troubleshooting (on the VM)
| Symptom | Check |
|---|---|
| App says "Cannot reach server" | `ping` the VM; confirm Bridged mode; `sudo firewall-cmd --list-services` includes `http` |
| 502 Bad Gateway | `systemctl status imgserver`, `journalctl -u imgserver -n 50` |
| 502 with SELinux denial | `getsebool httpd_can_network_connect` should be `on` |
| 413 on upload | file larger than 10 MB (nginx limit is 11 MB, API limit 10 MB) |
| No backgrounds | add images (step 3) |
