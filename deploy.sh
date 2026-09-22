#!/usr/bin/env bash
# استقرار سکوی تبدیل صوت به متن روی سرور خام لینوکس.
# AlmaLinux / Rocky / RHEL / CentOS و Ubuntu / Debian.
#
#   sudo bash deploy.sh
#
# اگر درایور NVIDIA تازه نصب شود، اسکریپت درخواست ری‌استارت می‌دهد.
# بعد از بالا آمدن سرور همان دستور را دوباره اجرا کنید.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

log() { printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }
die() { printf '\nخطا: %s\n' "$*" >&2; exit 1; }

if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo bash "$ROOT/deploy.sh" "$@"
fi

[[ -f "$ROOT/docker-compose.yml" ]] || die "docker-compose.yml کنار این اسکریپت پیدا نشد."

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
else
  die "نسخه سیستم‌عامل قابل تشخیص نیست."
fi

OS_ID="${ID:-unknown}"
OS_LIKE="${ID_LIKE:-}"
VERSION_MAJOR="${VERSION_ID%%.*}"

is_dnf() { [[ "$OS_ID" =~ (almalinux|rocky|rhel|centos|fedora) || "$OS_LIKE" =~ (rhel|fedora) ]]; }
is_apt() { [[ "$OS_ID" =~ (ubuntu|debian) || "$OS_LIKE" =~ debian ]]; }

install_base() {
  log "نصب ابزارهای پایه"
  if is_dnf; then
    dnf install -y curl ca-certificates tar gzip openssl dnf-plugins-core
  elif is_apt; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y curl ca-certificates tar gzip openssl gnupg
  else
    die "این توزیع پشتیبانی نمی‌شود: $OS_ID. AlmaLinux، Rocky، RHEL یا Ubuntu استفاده کنید."
  fi
}

add_dnf_repo() {
  local url="$1"
  if [[ -f /etc/yum.repos.d/docker-ce.repo ]]; then
    return
  fi
  dnf config-manager --add-repo "$url" \
    || dnf config-manager addrepo --from-repofile="$url"
}

install_docker_rhel() {
  # get.docker.com توزیع almalinux و rocky را قبول نمی‌کند.
  # AlmaLinux باینری‌سازگار با RHEL است و مخزن docker-ce همان نسخه را دارد.
  log "نصب Docker از مخزن RHEL"
  add_dnf_repo "https://download.docker.com/linux/rhel/docker-ce.repo"
  rpm --import https://download.docker.com/linux/rhel/gpg || true
  local packages=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin)
  if ! dnf install -y "${packages[@]}"; then
    log "Docker با podman تداخل دارد؛ podman حذف و نصب دوباره انجام می‌شود"
    dnf remove -y podman buildah podman-docker || true
    dnf install -y "${packages[@]}"
  fi
}

install_docker() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    log "Docker و Compose از قبل نصب هستند"
    systemctl enable --now docker
    return
  fi
  if is_dnf && [[ "$OS_ID" != "fedora" ]]; then
    install_docker_rhel
  else
    log "نصب Docker"
    curl -fsSL https://get.docker.com | sh
  fi
  systemctl enable --now docker
  docker compose version >/dev/null 2>&1 || die "افزونه docker compose نصب نشد."
}

nvidia_ok() { command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; }

install_nvidia_driver() {
  if nvidia_ok; then
    log "درایور NVIDIA آماده است"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    return
  fi
  log "درایور NVIDIA پیدا نشد؛ در حال نصب"
  if [[ "$OS_ID" == "almalinux" ]]; then
    # روی AlmaLinux 9 و 10 درایور امضاشده از مخزن خود توزیع نصب می‌شود و به dkms نیاز ندارد.
    dnf install -y almalinux-release-nvidia-driver
    dnf install -y nvidia-open-kmod nvidia-driver nvidia-driver-cuda
  elif is_dnf; then
    dnf install -y gcc make elfutils-libelf-devel "kernel-devel-$(uname -r)" "kernel-headers-$(uname -r)" \
      || dnf install -y gcc make elfutils-libelf-devel kernel-devel kernel-headers
    dnf config-manager --add-repo "https://developer.download.nvidia.com/compute/cuda/repos/rhel${VERSION_MAJOR}/x86_64/cuda-rhel${VERSION_MAJOR}.repo" \
      || dnf config-manager addrepo --from-repofile="https://developer.download.nvidia.com/compute/cuda/repos/rhel${VERSION_MAJOR}/x86_64/cuda-rhel${VERSION_MAJOR}.repo"
    dnf clean all
    dnf module install -y nvidia-driver:latest-dkms
    dnf install -y nvidia-driver-cuda || true
  elif is_apt; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get install -y "linux-headers-$(uname -r)" ubuntu-drivers-common || apt-get install -y "linux-headers-$(uname -r)"
    if command -v ubuntu-drivers >/dev/null 2>&1; then
      ubuntu-drivers install || ubuntu-drivers autoinstall
    else
      apt-get install -y nvidia-driver
    fi
  fi
  modprobe nvidia || modprobe nvidia_drm || true
  if ! nvidia_ok; then
    cat <<EOF

درایور NVIDIA نصب شد ولی هنوز به کارت گرافیک وصل نیست.
سرور را یک‌بار ری‌استارت کنید و سپس همین اسکریپت را دوباره اجرا کنید:

  sudo reboot
  cd "$ROOT" && sudo bash deploy.sh

EOF
    exit 20
  fi
}

install_nvidia_toolkit() {
  if command -v nvidia-ctk >/dev/null 2>&1; then
    log "NVIDIA Container Toolkit از قبل نصب است"
  else
    log "نصب NVIDIA Container Toolkit"
    if is_dnf; then
      curl -fsSL https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo \
        -o /etc/yum.repos.d/nvidia-container-toolkit.repo
      dnf install -y nvidia-container-toolkit
    else
      install -d -m 0755 /usr/share/keyrings
      curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
        | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
      curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
        | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
        > /etc/apt/sources.list.d/nvidia-container-toolkit.list
      apt-get update
      apt-get install -y nvidia-container-toolkit
    fi
  fi
  nvidia-ctk runtime configure --runtime=docker
  systemctl restart docker
  if command -v getenforce >/dev/null 2>&1 && [[ "$(getenforce)" == "Enforcing" ]]; then
    setsebool -P container_use_devices on 2>/dev/null || true
  fi
}

verify_gpu_in_docker() {
  log "بررسی دیده شدن GPU داخل Docker"
  docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi \
    || die "کارت گرافیک داخل کانتینر در دسترس نیست. nvidia-ctk و ری‌استارت Docker را بررسی کنید."
}

rand_hex() { openssl rand -hex 24; }

prepare_env() {
  if [[ -f .env ]]; then
    if grep -Eq 'replace-with|change-this-password' .env; then
      die "فایل .env هنوز رمز نمونه دارد. آن را ویرایش کنید یا پاک کنید تا اسکریپت رمز تازه بسازد."
    fi
    log "از فایل .env موجود استفاده می‌شود"
    return
  fi
  log "ساخت .env با رمزهای تصادفی"
  local secret db_pass admin_pass admin_email host
  secret="$(rand_hex)"
  db_pass="$(rand_hex)"
  admin_pass="${ADMIN_PASSWORD:-$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-20)}"
  admin_email="${ADMIN_EMAIL:-admin@example.com}"
  host="${PUBLIC_HOST:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
  host="${host:-localhost}"
  cat > .env <<EOF
APP_NAME=STT Platform
ENVIRONMENT=production
LOG_LEVEL=INFO
SECRET_KEY=${secret}
ACCESS_TOKEN_EXPIRE_MINUTES=720

POSTGRES_USER=stt
POSTGRES_PASSWORD=${db_pass}
POSTGRES_DB=stt
DATABASE_URL=postgresql+psycopg://stt:${db_pass}@postgres:5432/stt

REDIS_URL=redis://redis:6379/0
CORS_ORIGINS=http://localhost:3000,http://${host}:3000

STORAGE_PATH=/data/storage
TEMP_PATH=/data/temp
WHISPER_MODEL_DIR=/data/models

DEVICE=cuda
COMPUTE_TYPE=float16
GPU_INDEX=0

ADMIN_EMAIL=${admin_email}
ADMIN_PASSWORD=${admin_pass}
ADMIN_NAME=مدیر سیستم

API_INTERNAL_URL=http://api:8000
EOF
  chmod 600 .env
  CREATED_ENV=1
}

open_firewall() {
  if systemctl is-active --quiet firewalld; then
    log "باز کردن پورت‌های ۸۰۰۰ و ۳۰۰۰ در firewalld"
    firewall-cmd --permanent --add-port=8000/tcp
    firewall-cmd --permanent --add-port=3000/tcp
    firewall-cmd --reload
  elif command -v ufw >/dev/null 2>&1 && ufw status | grep -q 'Status: active'; then
    log "باز کردن پورت‌های ۸۰۰۰ و ۳۰۰۰ در ufw"
    ufw allow 8000/tcp
    ufw allow 3000/tcp
  fi
}

wait_http() {
  local url="$1" tries="$2" i
  for ((i = 1; i <= tries; i++)); do
    if curl -fsS "$url" >/dev/null; then
      return 0
    fi
    sleep 5
  done
  return 1
}

worker_running() {
  local id
  id="$(docker compose ps -q worker || true)"
  [[ -n "$id" ]] || return 1
  [[ "$(docker inspect -f '{{.State.Running}}' "$id")" == "true" ]]
}

verify_stack() {
  log "ساخت و اجرای سرویس‌ها. اولین بار دانلود مدل ممکن است طول بکشد"
  docker compose up -d --build

  log "منتظر سالم شدن API"
  wait_http "http://127.0.0.1:8000/health" 60 || {
    docker compose ps
    docker compose logs --tail 80 api
    die "API سالم نشد."
  }

  log "منتظر پنل مدیریت"
  wait_http "http://127.0.0.1:3000/login" 40 || {
    docker compose logs --tail 80 frontend
    die "پنل مدیریت بالا نیامد."
  }

  worker_running || {
    docker compose logs --tail 100 worker
    die "کانتینر Worker در حال اجرا نیست."
  }

  log "بررسی CUDA داخل Worker"
  local i
  for ((i = 1; i <= 12; i++)); do
    if docker compose exec -T worker python -c "import ctranslate2; raise SystemExit(0 if ctranslate2.get_cuda_device_count() > 0 else 1)"; then
      break
    fi
    sleep 5
    if ((i == 12)); then
      docker compose logs --tail 80 worker
      die "Worker کارت CUDA را نمی‌بیند."
    fi
  done

  log "منتظر آنلاین شدن Worker بعد از بارگذاری مدل"
  local online=0
  for ((i = 1; i <= 80; i++)); do
    worker_running || {
      docker compose logs --tail 100 worker
      die "Worker در حین بارگذاری مدل متوقف شد."
    }
    if curl -fsS "http://127.0.0.1:8000/health" | grep -q '"worker": "online"'; then
      online=1
      break
    fi
    sleep 15
  done

  echo
  curl -fsS "http://127.0.0.1:8000/health" || true
  echo
  docker compose ps

  local host admin_email admin_pass
  host="${PUBLIC_HOST:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
  host="${host:-localhost}"
  admin_email="$(grep -E '^ADMIN_EMAIL=' .env | cut -d= -f2-)"
  admin_pass="$(grep -E '^ADMIN_PASSWORD=' .env | cut -d= -f2-)"

  cat <<EOF

استقرار انجام شد.
  مستندات API:  http://${host}:8000/docs
  سلامت سرویس: http://${host}:8000/health
  پنل مدیریت:   http://${host}:3000
  ایمیل ادمین:  ${admin_email}
EOF
  if [[ "${CREATED_ENV:-0}" == "1" ]]; then
    printf '  رمز ادمین:    %s\n  این رمز در فایل .env هم ذخیره شده است.\n' "$admin_pass"
  else
    printf '  رمز ادمین در فایل .env موجود است.\n'
  fi
  if [[ "$online" -ne 1 ]]; then
    cat <<EOF

Worker هنوز مدل را تمام نکرده است. این خطا نیست؛ دانلود large-v3 ممکن است چند دقیقه طول بکشد.
وضعیت را با این دستور ببینید:

  cd "$ROOT" && docker compose logs -f worker

EOF
  else
    echo "Worker آنلاین است و GPU را می‌بیند."
  fi
}

CREATED_ENV=0
install_base
install_docker
install_nvidia_driver
install_nvidia_toolkit
verify_gpu_in_docker
prepare_env
open_firewall
verify_stack
