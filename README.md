# Voice Transcription Wrapper — Cloud Deployment

A browser-based voice input widget (hosted on Amazon S3) connected to a FastAPI +
faster-whisper transcription backend (hosted on an AWS EC2 instance). Anyone with
the S3 link can record or upload audio and get a live transcript back — no local
setup required.

**Live pipeline:**
```
Browser (S3-hosted page) → wrapper.js → EC2 backend (FastAPI) → faster-whisper → transcript
```

---

## Quick Links (fill these in once deployed)

> Before using the app: open https://54.95.19.33:8000/health in your browser first. You'll see a security warning (self-signed certificate) — click Advanced → Proceed to 54.95.19.33 (unsafe). Once it loads and shows {"status": "ok"}, the frontend link will work correctly. This is a one-time step per browser.

| Component | URL |
|---|---|
| Frontend (S3 website) | `http://your-bucket.s3-website-<region>.amazonaws.com` |
| Backend health check | `https://54.95.19.33:8000/health` |
| Backend transcribe endpoint | `https://54.95.19.33:8000/transcribe` |

### What is the `/health` link and why check it first?

`https://54.95.19.33:8000/health` is **not** something a normal user needs — it's a diagnostic endpoint that just returns `{"status": "ok"}` when the backend server is alive and reachable. It doesn't do any transcription itself; the real work happens at `/transcribe`.

It's the first thing to check whenever something seems broken, because it instantly tells you *where* the problem is:

- **Loads and returns `{"status": "ok"}`** → the backend is fine; if the app still isn't working, the problem is on the frontend side (wrong `BACKEND_URL`, browser blocking the request, etc.).
- **Times out / connection refused** → the backend itself is down, or the EC2 Security Group / firewall is blocking the port — fix this before looking anywhere else.
- **Loads but the browser shows a "Not Secure" / certificate warning first** → this backend is using a self-signed HTTPS certificate (not one from a trusted authority). You need to open this exact URL once, click **Advanced → Proceed anyway**, before the frontend's requests to it will succeed. This is a one-time step per browser — until you do it, the S3 frontend will silently fail with "Failed to fetch," even though the backend is actually running fine.

So: it's not "required" in the sense that the code depends on it, but visiting it is a required *step* for you (or anyone testing this) to get the self-signed HTTPS backend working from the browser, and it's always the right first move when debugging.

---

## Project Structure

```
project/
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── wrapper.js           # BACKEND_URL here must point to the EC2 endpoint
├── backend/
│   ├── main.py               # FastAPI app — /health and /transcribe
│   ├── transcriber.py        # faster-whisper wrapper
│   ├── requirements.txt      # version-locked (pip freeze)
│   └── tests/
│       ├── common.py
│       ├── test_ecp.py
│       ├── test_bva.py
│       ├── audio_samples/
│       └── results/
└── README.md
```

---

## Architecture — Why It's Split This Way

- **Frontend on S3**: it's just static files (HTML/CSS/JS), so there's no server to manage — S3 serves them directly and cheaply. It stays up independently of the backend.
- **Backend on EC2**: needs a real Python process running continuously (loads an AI model into memory, runs inference) — that needs an actual server, so it lives on EC2, not S3.
- **They talk over the network**: the frontend's `wrapper.js` sends audio to the EC2 backend's public address, gets JSON back, and shows the transcript. This is why `BACKEND_URL` inside `wrapper.js` must always point to wherever the backend currently lives — if you ever redeploy the backend to a new IP, this is the one line you must update and re-upload.

---

## Part 1 — How to Use the Live App (for anyone, no setup)

1. Open the **frontend URL** (see Quick Links table) in a browser (Chrome/Edge/Firefox).
2. **To record:** click **Start Recording**, allow microphone access, speak, then click **Stop Recording**. It uploads automatically.
3. **To upload a file instead:** click the dropzone, or drag an audio file onto it.
4. Wait a few seconds — status shows "Transcribing…" — then the transcript appears on screen.
5. The console panel at the bottom logs everything happening (chunk capture, upload, response) — useful if something looks stuck.

That's it for a regular user — no backend knowledge needed.

---

## Part 2 — How to Redeploy / Restart Everything (for you, later, when you forget)

### A. Restarting the backend on EC2

If the backend ever goes down (server rebooted, etc.), SSH back in and bring it up again:

```bash
ssh -i your-key.pem ubuntu@<ec2-public-ip>
cd backend
source venv/bin/activate
```

**If running via systemd** (recommended, restarts automatically on reboot):
```bash
sudo systemctl status transcription    # check if it's already running
sudo systemctl restart transcription   # restart if needed
```

**If running via tmux** (manual/quick option):
```bash
tmux attach -t backend      # reattach to see if it's alive
# if not running, start it fresh:
tmux new -s backend
uvicorn main:app --host 0.0.0.0 --port 8000
# Ctrl+B then D to detach and leave it running
```

**Verify it's alive** (from your own machine, not the server):
```bash
curl http://<ec2-public-ip>:8000/health
```
Should return `{"status": "ok"}`.

### B. Redeploying the frontend to S3

If you change anything in `frontend/` (especially `BACKEND_URL` in `wrapper.js`):

1. Go to the S3 bucket in the AWS Console.
2. Upload the changed file(s) — this **overwrites** the old version (no separate "publish" step needed).
3. Refresh the frontend URL in your browser — changes are live immediately.

### C. If the backend's IP address changes (e.g. instance was stopped and restarted)

AWS assigns a new public IP by default every time you stop/start an EC2 instance (unless you attached an Elastic IP). If that happens:

1. Get the new public IP from the EC2 console.
2. Update `BACKEND_URL` in `frontend/wrapper.js` to the new IP.
3. Re-upload `wrapper.js` to S3 (step B above).
4. Re-open Security Group port 8000 (and 80/443 if using HTTPS) for the instance if it somehow reset.

> **Tip to avoid this entirely:** attach an **Elastic IP** to the EC2 instance — it's a fixed IP that doesn't change on stop/start, so you never have to touch `BACKEND_URL` again after the first setup.

---

## Part 3 — Full Setup From Scratch (if you ever need to rebuild this)

### Backend (EC2)

1. Launch an EC2 instance — Ubuntu 22.04, `t2.micro`/`t3.micro` (Free Tier).
2. Security Group: allow inbound TCP port `8000` (and `80`/`443` if using HTTPS) from `0.0.0.0/0`.
3. SSH in and install dependencies:
   ```bash
   sudo apt update && sudo apt install -y python3-pip python3-venv ffmpeg git
   ```
4. Get the code onto the instance (`git clone` or `scp`), then:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
5. Run it persistently — either `tmux` (quick) or `systemd` (recommended):
   ```ini
   # /etc/systemd/system/transcription.service
   [Unit]
   Description=Transcription Backend
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/backend
   ExecStart=/home/ubuntu/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable transcription
   sudo systemctl start transcription
   ```

### Frontend (S3)

1. Create an S3 bucket, uncheck "Block all public access."
2. Upload `index.html`, `style.css`, `wrapper.js`.
3. Enable **Static website hosting** on the bucket (set `index.html` as the index document).
4. Add a public-read bucket policy:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Sid": "PublicReadGetObject",
       "Effect": "Allow",
       "Principal": "*",
       "Action": "s3:GetObject",
       "Resource": "arn:aws:s3:::YOUR-BUCKET-NAME/*"
     }]
   }
   ```
5. Note the **website endpoint URL** (not the plain bucket URL) — use this one, it serves over `http://` matching the backend.
6. Update `wrapper.js`'s `BACKEND_URL` to the EC2 address, then upload it here too.

### Running the tests against the cloud backend

```bash
cd backend
python tests/test_ecp.py
python tests/test_bva.py
```
Make sure the test scripts point at the EC2 URL (not `localhost`) before running — check `common.py`'s base URL.

---

## HTTPS Note (only needed if the frontend is ever served over `https://`)

Browsers block a `https://` page from calling a plain `http://` backend ("mixed content"). This deployment currently keeps both frontend and backend on plain `http://`, which avoids the issue entirely and is fine for this deliverable.

If HTTPS is required later, the backend needs a real TLS certificate (e.g. via **nginx + Let's Encrypt**, with a domain name pointed at the EC2 IP) — this is more setup than the current version and only worth doing if explicitly asked for.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Frontend loads but "Transcribing…" never finishes | Backend down or wrong `BACKEND_URL` | Visit `https://54.95.19.33:8000/health` directly — confirms whether the backend is reachable at all; verify `wrapper.js` has the correct current EC2 address |
| Browser console: "Failed to fetch" / connection blocked | EC2 Security Group or `ufw` blocking the port | Confirm inbound rule for the port is open in AWS **and** `sudo ufw allow <port>` on the instance |
| Browser console: "Mixed Content" error | Frontend is `https://` but backend is `http://` | Use the S3 **website endpoint** (plain http), not a CloudFront/https URL, unless backend also has HTTPS set up |
| `curl` works but browser doesn't (self-signed HTTPS) | Browser doesn't trust the self-signed cert | Visit the backend URL directly once, click "Proceed anyway," then retry from the frontend |
| Backend was fine yesterday, dead today | EC2 instance was stopped/restarted, uvicorn wasn't set to auto-run | Use the `systemd` service (Part 3) so it restarts automatically; SSH in and check `sudo systemctl status transcription` |
| IP changed after a reboot | No Elastic IP attached | Attach an Elastic IP once so the address never changes again |
