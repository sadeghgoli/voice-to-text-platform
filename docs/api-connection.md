# اتصال سرویس‌ها به API تبدیل صوت به متن

هر نرم‌افزار فقط با HTTP به API وصل می‌شود. به PostgreSQL، Redis، Worker و GPU مستقیم وصل نشوید.

| مخاطب | آدرس | کار |
| --- | --- | --- |
| نرم‌افزارها | `http://SERVER:9002` | ارسال صوت، پیگیری Job، دریافت متن |
| پنل مدیریت | `http://SERVER:9001` | ساخت کلاینت و کلید، دیدن صف و GPU |
| Swagger | `http://SERVER:9002/docs` | همان API به‌صورت تعاملی |

`SERVER` همان IP سرور است، مثلاً `192.168.1.52`. داخل Docker، API همچنان روی پورت ۸۰۰۰ و پنل روی ۳۰۰۰ است. پورت ۹۰۰۲ و ۹۰۰۱ فقط روی میزبان منتشر می‌شوند. `API_INTERNAL_URL` را عوض نکنید؛ مقدار درست آن `http://api:8000` است.

## هر سرویس چه نقشی دارد

```
نرم‌افزار شما
    |  POST فایل + Bearer sk_stt_...
    v
API (پورت 9002)  --->  PostgreSQL  (Job و کلید)
    |                ->  Redis       (صف اولویت)
    v
Worker (GPU)     --->  متن، زیرنویس، وبهوک
```

1. در پنل برای هر نرم‌افزار یک کلاینت بسازید، مثلاً «کارتابل» یا «سامانه جلسات».
2. برای همان کلاینت یک کلید بسازید. مقدار `sk_stt_...` فقط همان لحظه نشان داده می‌شود. آن را در تنظیمات همان نرم‌افزار ذخیره کنید.
3. نرم‌افزار فایل را به API می‌فرستد و بلافاصله `job_id` می‌گیرد. تبدیل همان لحظه انجام نمی‌شود.
4. Worker فایل را به WAV مونو ۱۶ کیلوهرتز تبدیل می‌کند، با مدل Whisper (پیش‌فرض `large-v3`) روی GPU متن می‌سازد و Job را `completed` می‌کند.
5. نرم‌افزار یا وضعیت را می‌پرسد، یا اگر `webhook_url` داده باشد نتیجه را با POST دریافت می‌کند.

اولویت از ۱ تا ۱۰ است. عدد بزرگ‌تر زودتر پردازش می‌شود. در اولویت برابر، ترتیب ورود حفظ می‌شود. همزمانی پیش‌فرض GPU برابر ۱ است.

## احراز هویت

درخواست‌های تبدیل صوت این هدر را لازم دارند:

```http
Authorization: Bearer sk_stt_YOUR_KEY
```

به‌جای آن می‌توانید هدر `X-API-Key: sk_stt_YOUR_KEY` بفرستید. کلید پنل مدیریت (JWT) برای این مسیرها قبول نیست.

## ارسال فایل

`POST /api/v1/transcriptions`

بدنه از نوع `multipart/form-data` است.

| فیلد | الزام | توضیح |
| --- | --- | --- |
| `file` | بله | فایل صوت یا ویدیو |
| `language` | خیر | پیش‌فرض سیستم `fa` است. `auto` زبان را تشخیص می‌دهد |
| `model` | خیر | `large-v3`، `medium` یا `small`. خالی یعنی مدل پیش‌فرض |
| `priority` | خیر | ۱ تا ۱۰ |
| `webhook_url` | خیر | آدرس `http` یا `https` روی سرویس شما |
| `task` | خیر | `transcribe` یا `translate` |
| `initial_prompt` | خیر | برای فارسی، اگر خالی باشد «این یک گفتار فارسی است.» استفاده می‌شود |

پسوندهای مجاز: `wav`، `mp3`، `m4a`، `ogg`، `flac`، `aac`، `mp4`، `webm`، `mov`. ویدیو فقط صدایش استخراج می‌شود.

پاسخ `202`:

```json
{"success": true, "job_id": "UUID", "status": "queued"}
```

وضعیت‌های بعدی: `queued`، `processing`، `completed`، `failed`، `cancelled`.

### curl

```bash
curl -s -X POST http://192.168.1.52:9002/api/v1/transcriptions \
  -H "Authorization: Bearer sk_stt_YOUR_KEY" \
  -F "file=@meeting.mp3" \
  -F "language=fa" \
  -F "priority=5" \
  -F "webhook_url=https://app.example.com/hooks/stt"
```

### Python

```python
import time
import requests

base = "http://192.168.1.52:9002"
headers = {"Authorization": "Bearer sk_stt_YOUR_KEY"}

with open("meeting.mp3", "rb") as audio:
    created = requests.post(
        f"{base}/api/v1/transcriptions",
        headers=headers,
        files={"file": ("meeting.mp3", audio, "audio/mpeg")},
        data={"language": "fa", "priority": "5"},
        timeout=120,
    )
created.raise_for_status()
job_id = created.json()["job_id"]

while True:
    job = requests.get(f"{base}/api/v1/transcriptions/{job_id}", headers=headers, timeout=30)
    job.raise_for_status()
    body = job.json()
    if body["status"] in {"completed", "failed", "cancelled"}:
        print(body.get("text") or body.get("error_message"))
        break
    time.sleep(3)
```

### Node.js

```js
import fs from "node:fs";

const base = "http://192.168.1.52:9002";
const headers = { Authorization: "Bearer sk_stt_YOUR_KEY" };
const form = new FormData();
form.append("file", new Blob([fs.readFileSync("meeting.mp3")]), "meeting.mp3");
form.append("language", "fa");

const created = await fetch(`${base}/api/v1/transcriptions`, {
  method: "POST",
  headers,
  body: form,
}).then((response) => response.json());

const job = await fetch(`${base}/api/v1/transcriptions/${created.job_id}`, {
  headers,
}).then((response) => response.json());
```

## دریافت نتیجه

وضعیت و، بعد از اتمام، متن کامل:

```bash
curl -s http://192.168.1.52:9002/api/v1/transcriptions/JOB_ID \
  -H "Authorization: Bearer sk_stt_YOUR_KEY"
```

فایل خروجی وقتی `status` برابر `completed` است. `format` یکی از `txt`، `json`، `srt`، `vtt` است:

```bash
curl -s "http://192.168.1.52:9002/api/v1/transcriptions/JOB_ID/result?format=txt" \
  -H "Authorization: Bearer sk_stt_YOUR_KEY" \
  -o result.txt
```

`json` شامل `text` و `segments` با `start`، `end` و `text` است. `srt` و `vtt` زیرنویس زمانی هستند.

لغو Job در صف یا در حال پردازش:

```bash
curl -s -X DELETE http://192.168.1.52:9002/api/v1/transcriptions/JOB_ID \
  -H "Authorization: Bearer sk_stt_YOUR_KEY"
```

## وبهوک

اگر `webhook_url` بفرستید، Worker بعد از پایان یک `POST` با `Content-Type: application/json` به همان آدرس می‌زند. رویدادها: `transcription.completed`، `transcription.failed`، `transcription.cancelled`.

```json
{
  "event": "transcription.completed",
  "job_id": "UUID",
  "status": "completed",
  "text": "متن تشخیص‌داده‌شده",
  "duration": 12.4,
  "language": "fa",
  "error_message": null,
  "segments": [
    {"start": 0.0, "end": 2.5, "text": "سلام"}
  ]
}
```

سرویس شما باید با کد ۲xx جواب بدهد. در غیر این صورت تا سه بار دوباره تلاش می‌شود. آدرس وبهوک باید از خود سرور STT قابل دسترسی باشد.

## سلامت سرویس

این مسیرها کلید نمی‌خواهند:

- `GET /health`
- `GET /health/gpu`
- `GET /health/queue`
- `GET /health/database`

قبل از فرستادن ترافیک واقعی، `"worker": "online"` را در `/health` ببینید. اولین بار مدل `large-v3` دانلود می‌شود و تا تمام نشود Worker آنلاین نیست.
