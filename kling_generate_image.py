"""
Kling AI — генерация стартового кадра для hero-слайда "Гостиная".
Цель: выключатель на правильной высоте (90см от пола), камера на уровне глаз.
"""
import os
import time
import base64
import jwt
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ACCESS_KEY = os.getenv("KLING_ACCESS_KEY")
SECRET_KEY = os.getenv("KLING_SECRET_KEY")

API_BASE = "https://api-singapore.klingai.com"
PROJECT_DIR = Path(__file__).parent
REFERENCE_SWITCH = PROJECT_DIR / "Белый настенный переключатель на белом фоне - использовать.png"


def generate_jwt_token() -> str:
    """Создаёт JWT-токен для авторизации в Kling API."""
    headers = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": ACCESS_KEY,
        "exp": int(time.time()) + 1800,  # 30 минут
        "nbf": int(time.time()) - 5,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256", headers=headers)


def image_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


PROMPT = """A cinematic interior photograph shot at eye level (camera at 150cm height). Left 35% of the frame: a light warm gray wall. A sleek modern white wall switch (exactly matching the reference image — thin flat square frame, flush square rocker button, tiny LED indicator) is mounted on the wall at standard human height — 90cm from the floor, at hand level for a standing adult. The switch is positioned in the VERTICAL CENTER of the frame, NOT near the bottom.

CRITICAL: Below the switch there is a large amount of visible wall before reaching the white baseboard. The switch is far from the floor. The camera is at eye level looking straight at the switch, which means the floor is visible BELOW in the frame with significant distance from the switch.

The switch and the wall around it are in razor-sharp focus. Everything else is dissolved into heavy creamy warm bokeh (85mm f/1.2 aperture).

Right 65% through dreamy blur: a large cream bouclé sectional sofa with soft throw pillows and a knit blanket, a golden retriever curled up cozily on the sofa. A round travertine coffee table in front with two ceramic coffee cups, a hardcover book, and a small potted plant. A sculptural brass floor lamp. A built-in linear fireplace at eye level glowing with warm flames. Floor-to-ceiling windows with sheer linen curtains, warm golden hour sunlight.

Below eye level: warm oak herringbone parquet floor with a large textured wool area rug. The floor area is clearly visible BELOW the switch, confirming proper switch mounting height.

Warm minimalism, timeless sophistication, cream and taupe palette. No people. Warm golden hour light throughout.

Professional cinematic photography, 85mm lens, f/1.2 aperture, extreme shallow depth of field, camera positioned at 150cm height."""


def create_image_task():
    """Создаёт задачу на генерацию изображения."""
    token = generate_jwt_token()

    payload = {
        "model_name": "kling-v1-5",
        "prompt": PROMPT,
        "negative_prompt": "switch near floor, switch at floor level, low switch, outlet near floor, modified switch design, vintage switch, bulky frame, rounded frame, visible screws",
        "aspect_ratio": "16:9",
        "n": 1,
        "image": image_to_base64(REFERENCE_SWITCH),
        "image_reference": "subject",
        "image_fidelity": 0.9,  # сила следования reference (0-1)
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    print("Отправляю запрос на генерацию...")
    r = requests.post(f"{API_BASE}/v1/images/generations", json=payload, headers=headers, timeout=60)
    print(f"Статус: {r.status_code}")
    print(f"Ответ: {r.text[:500]}")
    r.raise_for_status()
    data = r.json()
    return data["data"]["task_id"]


def poll_task(task_id: str, max_wait: int = 300):
    """Опрашивает статус задачи до готовности."""
    token = generate_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    start = time.time()
    while time.time() - start < max_wait:
        r = requests.get(f"{API_BASE}/v1/images/generations/{task_id}", headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()["data"]
        status = data.get("task_status")
        print(f"[{int(time.time()-start)}s] Статус: {status}")
        if status == "succeed":
            return data["task_result"]["images"]
        if status == "failed":
            raise RuntimeError(f"Task failed: {data}")
        time.sleep(5)
    raise TimeoutError(f"Task {task_id} не завершилась за {max_wait}s")


def download_image(url: str, path: Path):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    path.write_bytes(r.content)
    print(f"Сохранено: {path}")


def main():
    if not ACCESS_KEY or not SECRET_KEY or ACCESS_KEY.startswith("ВСТАВЬ"):
        raise SystemExit("Заполни KLING_ACCESS_KEY и KLING_SECRET_KEY в .env")
    if not REFERENCE_SWITCH.exists():
        raise SystemExit(f"Не найден reference: {REFERENCE_SWITCH}")

    task_id = create_image_task()
    print(f"task_id: {task_id}")

    images = poll_task(task_id)
    for i, img in enumerate(images):
        out = PROJECT_DIR / f"kling-living-room-v{i+1}.png"
        download_image(img["url"], out)


if __name__ == "__main__":
    main()
