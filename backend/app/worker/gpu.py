from __future__ import annotations

import json
import shutil
import subprocess

import psutil
import structlog

from app.core.config import get_settings
from app.core.time import utcnow

log = structlog.get_logger()


def cuda_device_count() -> int:
    try:
        import ctranslate2

        return int(ctranslate2.get_cuda_device_count())
    except Exception as exc:
        log.warning("gpu.cuda_check_failed", error=str(exc))
        return 0


def resolve_device(requested: str) -> str:
    choice = (requested or "auto").strip().lower()
    available = cuda_device_count() > 0
    if choice == "cpu":
        log.info("gpu.device", device="cpu", cuda_devices=cuda_device_count())
        return "cpu"
    if choice == "cuda":
        if not available:
            log.error("gpu.cuda_missing")
            raise RuntimeError("CUDA درخواست شده اما GPU در دسترس نیست.")
        log.info("gpu.device", device="cuda")
        return "cuda"
    device = "cuda" if available else "cpu"
    log.info("gpu.device", device=device, requested="auto", cuda=available)
    return device


def collect_host_stats(device: str) -> dict:
    cpu = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    gpu = _gpu_stats(device)
    return {
        "updated_at": utcnow().isoformat(),
        "device": device,
        "cpu": {"percent": cpu},
        "memory": {
            "percent": memory.percent,
            "used_mb": int(memory.used / (1024 * 1024)),
            "total_mb": int(memory.total / (1024 * 1024)),
        },
        "gpu": gpu,
    }


def _gpu_stats(device: str) -> dict:
    if device != "cuda":
        return {"available": False, "device": "cpu", "name": "CPU"}
    nvml = _nvml_stats()
    if nvml is not None:
        return nvml
    smi = _nvidia_smi_stats()
    if smi is not None:
        return smi
    log.error("gpu.stats_unavailable")
    return {"available": False, "device": "cuda", "name": None}


def _nvml_stats() -> dict | None:
    try:
        import pynvml

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(get_settings().gpu_index)
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode()
        memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
        temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000
        limit = pynvml.nvmlDeviceGetEnforcedPowerLimit(handle) / 1000
        return {
            "available": True,
            "device": "cuda",
            "name": name,
            "temperature_c": int(temperature),
            "utilization_percent": int(utilization.gpu),
            "vram_used_mb": int(memory.used / (1024 * 1024)),
            "vram_total_mb": int(memory.total / (1024 * 1024)),
            "power_w": round(power, 1),
            "power_limit_w": round(limit, 1),
        }
    except Exception as exc:
        log.warning("gpu.nvml_failed", error=str(exc))
        return None


def _nvidia_smi_stats() -> dict | None:
    binary = shutil.which("nvidia-smi")
    if not binary:
        return None
    try:
        result = subprocess.run(
            [
                binary,
                f"--id={get_settings().gpu_index}",
                "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw,power.limit",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )
    except Exception as exc:
        log.warning("gpu.nvidia_smi_failed", error=str(exc))
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    parts = [item.strip() for item in result.stdout.strip().split(",")]
    if len(parts) < 7:
        return None

    def num(value: str, cast=float):
        try:
            return cast(value)
        except ValueError:
            return None

    return {
        "available": True,
        "device": "cuda",
        "name": parts[0],
        "temperature_c": num(parts[1], int),
        "utilization_percent": num(parts[2], int),
        "vram_used_mb": num(parts[3], int),
        "vram_total_mb": num(parts[4], int),
        "power_w": num(parts[5], float),
        "power_limit_w": num(parts[6], float),
    }


def log_gpu_banner(stats: dict) -> None:
    gpu = stats.get("gpu") or {}
    log.info(
        "gpu.ready",
        name=gpu.get("name"),
        device=stats.get("device"),
        vram_total_mb=gpu.get("vram_total_mb"),
        vram_used_mb=gpu.get("vram_used_mb"),
        temperature_c=gpu.get("temperature_c"),
    )
    if stats.get("device") == "cuda" and not gpu.get("available"):
        log.error("gpu.unhealthy", stats=json.dumps(gpu, ensure_ascii=False))
