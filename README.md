# سکوی مرکزی تبدیل صوت به متن

سرویس داخلی برای چند نرم‌افزار که با یک کارت گرافیک مشترک، فایل صوتی را به متن تبدیل می‌کنند. تمرکز پیش‌فرض روی فارسی است. API فقط Job می‌سازد؛ Worker مدل Whisper را یک‌بار روی GPU نگه می‌دارد و صف اولویت‌دار را پردازش می‌کند.

## معماری

```
کلاینت‌ها  --Bearer API Key-->  FastAPI
پنل ادمین  --JWT-->             FastAPI
FastAPI --> PostgreSQL
FastAPI --> Redis Sorted Set
Worker  --> Redis + GPU (faster-whisper) + فایل‌ها
Worker  --> Webhook کلاینت
```

مدل پشت اینترفیس `STTEngine` است. پیاده‌سازی فعلی `faster-whisper` است و مدل‌های `large-v3`، `medium`، `small` و یک ردیف غیرفعال برای مدل اختصاصی فارسی از قبل ثبت شده‌اند.

## پیش‌نیاز سرور

- AlmaLinux با NVIDIA Driver و CUDA
- NVIDIA RTX 4060 یا کارت سازگار
- Docker Engine و افزونه Compose
- NVIDIA Container Toolkit
- دسترسی خروجی اینترنت برای دانلود یک‌باره مدل Whisper

## نصب درایور و CUDA روی AlmaLinux

مخزن CUDA مخصوص RHEL 9 با AlmaLinux 9 سازگار است:

```bash
sudo dnf update -y
sudo dnf install -y kernel-devel kernel-headers gcc make dkms
sudo dnf config-manager --add-repo https://developer.download.nvidia.com/compute/cuda/repos/rhel9/x86_64/cuda-rhel9.repo
sudo dnf clean all
sudo dnf module install -y nvidia-driver:latest-dkms
sudo dnf install -y cuda-toolkit
sudo reboot
nvidia-smi
```

`nvidia-smi` باید نام RTX 4060، درایور و نسخه CUDA را نشان دهد.

## Docker

```bash
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
```

## NVIDIA Container Toolkit

```bash
curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo
sudo dnf install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

## استقرار روی سرور خام

روی AlmaLinux، Rocky، RHEL یا Ubuntu، داخل همین پوشه:

```bash
sudo bash deploy.sh
```

اسکریپت Docker، درایور NVIDIA، NVIDIA Container Toolkit و سرویس‌ها را نصب می‌کند و سلامت API، پنل و GPU را بررسی می‌کند. اگر درایور تازه نصب شود، بعد از `sudo reboot` همان دستور را دوباره اجرا کنید. رمز ادمین را فقط همان بار چاپ می‌کند و در `.env` هم می‌نویسد.

اجرای دستی، اگر نخواهید از اسکریپت استفاده کنید:

```bash
cp .env.example .env
```

در `.env` این مقدارها را عوض کنید و در `DATABASE_URL` همان رمز Postgres را بگذارید:

- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- `ADMIN_PASSWORD`
- `DEVICE=cuda`

سپس:

```bash
docker compose up -d --build
```

سرویس API بعد از بالا آمدن Postgres و Redis، مهاجرت Alembic را اجرا می‌کند، مدل‌ها و تنظیمات پیش‌فرض را seed می‌کند و اگر ایمیل ادمین وجود نداشته باشد آن را می‌سازد. اولین اجرای Worker مدل `large-v3` را دانلود می‌کند و ممکن است چند دقیقه طول بکشد.

- API و Swagger: `http://SERVER:9002/docs`
- ReDoc: `http://SERVER:9002/redoc`
- پنل: `http://SERVER:9001`

اگر سرویس از قبل بالا باشد و فقط بخواهید همین پورت‌ها را اعمال کنید:

```bash
sudo bash set-ports.sh
```

نحوه اتصال نرم‌افزارها، ارسال فایل و دریافت متن در [docs/api-connection.md](docs/api-connection.md) است.

دستورهای معادل داخل کانتینر API:

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m app.scripts.seed
docker compose exec api python -m app.scripts.create_admin --email admin@example.com --password 'a-strong-password' --name 'مدیر سیستم'
```

اگر ادمین از قبل وجود داشته باشد، دستور چیزی را عوض نمی‌کند.

## ساخت کلید و تست API

1. وارد پنل شوید.
2. یک کلاینت بسازید، مثلاً «کارتابل شهرداری».
3. برای همان کلاینت کلید بسازید. مقدار `sk_stt_...` فقط همان لحظه نشان داده می‌شود.
4. فایل را بفرستید:

```bash
curl -s -X POST http://localhost:9002/api/v1/transcriptions \
  -H "Authorization: Bearer sk_stt_YOUR_KEY" \
  -F "file=@sample.mp3" \
  -F "language=fa" \
  -F "priority=5"
```

پاسخ:

```json
{"success": true, "job_id": "...", "status": "queued"}
```

سپس وضعیت و نتیجه:

```bash
curl -s http://localhost:9002/api/v1/transcriptions/JOB_ID \
  -H "Authorization: Bearer sk_stt_YOUR_KEY"

curl -s "http://localhost:9002/api/v1/transcriptions/JOB_ID/result?format=srt" \
  -H "Authorization: Bearer sk_stt_YOUR_KEY"
```

کالکشن Postman در `postman/STT-Platform.postman_collection.json` است. متغیر `apiKey` را تنظیم کنید، فایل را در درخواست Create transcription انتخاب کنید، و بعد Get transcription را تکرار کنید تا `completed` شود.

### نمونه Node.js

```js
import fs from "node:fs";

const base = "http://localhost:9002";
const key = process.env.STT_API_KEY;
const body = new FormData();
body.append("file", new Blob([fs.readFileSync("sample.mp3")]), "sample.mp3");
body.append("language", "fa");

const created = await fetch(`${base}/api/v1/transcriptions`, {
  method: "POST",
  headers: { Authorization: `Bearer ${key}` },
  body,
}).then((response) => response.json());

const job = await fetch(`${base}/api/v1/transcriptions/${created.job_id}`, {
  headers: { Authorization: `Bearer ${key}` },
}).then((response) => response.json());

console.log(job.status, job.text);
```

اگر `webhook_url` بفرستید، بعد از پایان یا شکست، یک POST با رویداد `transcription.completed` یا `transcription.failed` ارسال می‌شود.

## رفتار صف و فارسی

- اولویت از ۱ تا ۱۰ است و عدد بزرگ‌تر زودتر پردازش می‌شود. در اولویت برابر، ترتیب ورود حفظ می‌شود.
- `MAX` همزمانی از تنظیمات پنل خوانده می‌شود و پیش‌فرض آن ۱ است. استنتاج Whisper همیشه پشت یک قفل GPU می‌ماند.
- اگر `language` خالی باشد، زبان پیش‌فرض سیستم (`fa`) استفاده می‌شود. مقدار `auto` تشخیص زبان را روشن می‌کند.
- برای فارسی، اگر پرامپت اولیه نفرستید، جمله «این یک گفتار فارسی است.» فرستاده می‌شود.
- فایل ویدیویی فقط به صوت مونو ۱۶ کیلوهرتز WAV تبدیل می‌شود. FFmpeg بدون shell و فقط با آرگومان لیستی اجرا می‌شود.
- فایل صوتی پیش‌فرض بعد از ۲۴ ساعت حذف می‌شود و متن تا ۹۰ روز می‌ماند. هر دو از صفحه تنظیمات قابل تغییرند.
- خطای موقت تا ۳ بار با فاصله ۵، ۱۵ و ۴۵ ثانیه به صف برمی‌گردد.

آمار GPU را خود Worker در Redis می‌نویسد، چون فقط همان کانتینر به کارت گرافیک دسترسی دارد.

## توسعه بدون GPU

روی ماشینی که CUDA ندارد `DEVICE=cpu` بگذارید و در `docker-compose.yml` خط `gpus: all` را بردارید. Worker در حالت `auto` اگر CUDA نبیند روی CPU با `int8` ادامه می‌دهد. `DEVICE=cuda` در صورت نبودن GPU، Worker را متوقف می‌کند تا خطا پنهان نماند.

تست‌های واحد، بدون پایگاه داده و GPU:

```bash
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

روی Linux به‌جای مسیر ویندوز از `.venv/bin/python` استفاده کنید.

## امنیت

- کلید API با SHA-256 ذخیره می‌شود.
- رمز ادمین با Argon2 ذخیره می‌شود.
- محدودیت درخواست در دقیقه و سقف صوت روزانه و ماهانه برای هر کلید وجود دارد.
- پسوند، MIME، حجم، نام فایل و مسیر UUID بررسی می‌شود.
- آدرس وبهوک باید `http` یا `https` باشد و میزبان metadata ابری رد می‌شود.

## نقاط سلامت

- `GET /health`
- `GET /health/gpu`
- `GET /health/queue`
- `GET /health/database`

همان مسیرها زیر `/api/v1` هم هستند. مستندات تعاملی در `/docs` و `/redoc` است.

استریم زنده در این نسخه پیاده نشده است. ماژول `backend/app/stt/realtime.py` برای WebSocket بعدی کنار همان رجیستری مدل رزرو شده است.
