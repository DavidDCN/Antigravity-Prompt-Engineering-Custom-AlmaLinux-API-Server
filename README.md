# ATTRial: Emulated Image Server

An AlmaLinux VM (VirtualBox) acts as a realistic "production" server running a custom
**Python FastAPI** API. The server hands **background images** to a **Windows desktop
app (PySide6)**, and users upload **text and/or images** back to it. An uploaded image
can either be kept separate or also be added to the background rotation.

```
Desktop app (Windows) ──HTTP over your network──▶ AlmaLinux VM
                                                  firewalld :80 → nginx :80 → uvicorn/FastAPI :8000 (systemd)
                                                  /srv/imgserver/data/{backgrounds,uploads,metadata.db}
```

## Repository layout
| Path | What it is |
|---|---|
| `server/app/` | FastAPI API (`main.py`, `db.py`, `storage.py`, `config.py`) |
| `server/tests/` | pytest suite |
| `deploy/` | `setup.sh` (provisioning), systemd unit, nginx config, env template |
| `desktop/` | PySide6 desktop client |

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
From PowerShell on Windows, in `d:\ATTRial`:
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
user, opens port 80 in firewalld, configures SELinux and starts everything. It prints the
**admin API key** (saved in `/etc/imgserver/imgserver.env`) and the URL to use.

To deploy a new version, copy the files again and re-run `setup.sh`. Your data and API
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

## API reference
Interactive docs: **`http://<server-ip>/docs`**

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/api/health` | status, version, background count |
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

Admin endpoints need the header `X-API-Key: <key>`. Limits: JPEG, PNG or WebP only (the
file's actual contents are checked), 10 MB per image, 5,000 characters of text. Change
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
