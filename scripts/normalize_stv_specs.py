"""
normalize_stv_specs.py — приводит грязные характеристики STV к канону AWS.

Вход:  scripts/audit/stv_specs.json  (поле specs — сырьё)
Выход: то же, добавляет поле specs_norm (упорядоченный канон) + stv_specs_norm_report.md

Канон (см. memory feedback_specs_style):
  • Серия ЗАГЛАВНЫМИ: УНО / АУРА / ДИЗАЙН
  • единицы с неразрывным пробелом: 16 А, 250 В, 1,5 м
  • булевы: Есть / Нет
  • IP без скобок, монтаж/материал единообразно
"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "scripts" / "audit" / "stv_specs.json"
REPORT = ROOT / "scripts" / "audit" / "stv_specs_norm_report.md"
NBSP = " "

# --- 1. канон названий ключей (дубли → один) -------------------------------
KEY_CANON = {
    "Цвет": "Цвет",
    "Серия": "Серия",
    "Материал": "Материал",
    "Тип поверхности": "Покрытие",
    "Количество клавиш": "Клавиш",
    "Количество постов": "Постов",
    "Подсветка": "Подсветка",
    "Шторки": "Шторки",
    "Откидная крышка": "Крышка",
    "Количество USB-портов": "USB-портов",
    "Количество портов TYPE-C": "Портов Type-C",
    "Напряжение USB-портов": "Напряжение USB",
    "USB": "USB",
    "Type-C": "Type-C",
    "Выход": "Выход USB",
    "Номинальный ток": "Номинальный ток",
    "Номинальное напряжение": "Напряжение",
    "Напряжение": "Напряжение",
    "Степень защиты (IP)": "Защита",
    "Тип монтажа": "Монтаж",
    "Ориентация монтажа": "Ориентация",
    "Способ крепления": "Крепление",
    "Способ или тип крепления": "Крепление",
    "Способ подключения": "Подключение",
    "Заземление": "Заземление",
    "Встроенный выключатель": "Выключатель",
    # кабель
    "Тип кабеля": "Тип кабеля",
    "Категория": "Категория",
    "Количество пар": "Пар",
    "Материал проводников": "Проводник",
    "Тип проводников": "Жила",
    "Диаметр проводников, мм": "Диаметр жилы",
    "Применение": "Применение",
    "Материал изоляции проводников": "Изоляция",
    "Материал внешней оболочки": "Оболочка",
    "Разрывная нить": "Разрывная нить",
    "Устойчив к воздействию UV": "UV-стойкость",
    "Цвет оболочки": "Цвет оболочки",
    "Тип соединителя или разъема": "Разъём",
    "Тип разъёма": "Разъём",
    "Количество разъемов": "Разъёмов",
    "Защитная пленка": "Защитная плёнка",
    # клеммы / коннекторы
    "Рабочее сечение проводов": "Сечение проводов",
    "Сечение провода": "Сечение",
    "Сечение кабеля": "Сечение",
    "Количество точек подключения": "Точек подключения",
    "Количество отверстий": "Отверстий",
    "В упаковке": "В упаковке",
    # удлинители
    "Количество розеток": "Розеток",
    "Длина кабеля": "Длина кабеля",
    "Макс. нагрузка": "Макс. нагрузка",
    "Назначение": "Назначение",
}

# порядок вывода (всё, что не в списке — в конец, в исходном порядке)
ORDER = [
    "Серия", "Цвет", "Цвет оболочки", "Материал", "Покрытие",
    "Клавиш", "Постов", "Подсветка", "Шторки", "Крышка",
    "USB", "USB-портов", "Type-C", "Портов Type-C", "Напряжение USB", "Выход USB",
    "Номинальный ток", "Напряжение", "Макс. нагрузка", "Защита",
    "Заземление", "Выключатель", "Розеток", "Длина кабеля",
    "Монтаж", "Ориентация", "Крепление", "Подключение",
    # кабель
    "Тип кабеля", "Категория", "Пар", "Проводник", "Жила", "Диаметр жилы",
    "Изоляция", "Оболочка", "Защитная плёнка", "Разрывная нить", "UV-стойкость",
    "Применение", "Разъём", "Разъёмов",
    # клеммы
    "Сечение", "Сечение проводов", "Точек подключения", "Отверстий", "В упаковке",
    "Назначение",
]
ORDER_IDX = {k: i for i, k in enumerate(ORDER)}

BOOL_KEYS = {"Подсветка", "Шторки", "Крышка", "USB", "Type-C", "Заземление",
             "Выключатель", "Разрывная нить", "UV-стойкость"}

SERIES_MAP = {
    "uno": "УНО", "уно": "УНО", "ауна": "АУРА", "aura": "АУРА", "аура": "АУРА",
    "design": "ДИЗАЙН", "дизайн": "ДИЗАЙН", "u1a": "УНО", "u2b": "УНО",
}

UNIT_RE = re.compile(r"(\d)\s*([АВ]|Вт|мм²|мм|м|кВт)\b")
SOFTTOUCH_RE = re.compile(r"soft[\s\-]?touch", re.I)


def fix_units(v: str) -> str:
    # "16А"/"16 А" → "16 А" (неразрывный)
    return UNIT_RE.sub(lambda m: f"{m.group(1)}{NBSP}{m.group(2)}", v)


def tr_softtouch(v: str) -> str:
    # Soft Touch / SoftTouch / Soft-Touch → Софт-тач (везде, обязательно по-русски)
    return SOFTTOUCH_RE.sub("Софт-тач", v)


def norm_value(key: str, v: str) -> str:
    v = v.strip()
    if key == "Серия":
        return SERIES_MAP.get(v.lower().strip(), v.upper())
    if key == "Покрытие":
        low = v.lower()
        surface = "Матовое" if "матов" in low else ("Глянцевое" if "глянц" in low else "")
        soft = bool(SOFTTOUCH_RE.search(v)) or "софт-тач" in low or "софт тач" in low
        parts = [p for p in (surface, "Софт-тач" if soft else "") if p]
        return ", ".join(parts) if parts else tr_softtouch(v)
    if key in BOOL_KEYS:
        low = v.lower()
        if low in ("да", "есть", "yes", "+", "true"):
            return "Есть"
        if low in ("нет", "no", "-", "false", "—"):
            return "Нет"
        return v
    if key == "Защита":
        m = re.search(r"ip\s*\d+", v, re.I)
        return m.group(0).upper().replace(" ", "") if m else v
    if key == "Монтаж":
        low = v.lower()
        if "скрыт" in low or "внутр" in low:
            return "Скрытый"
        if "наружн" in low or "открыт" in low or "наклад" in low:
            return "Накладной"
        return v.capitalize()
    if key == "Материал":
        low = v.lower()
        if "стекло" in low and "abs" in low:
            return "Стекло + ABS"
        if "стекло" in low:
            return "Стекло"
        if "поликарбонат" in low and "abs" in low:
            return "Поликарбонат + ABS"
        if "поликарбонат" in low:
            return "Поликарбонат"
        return v
    return fix_units(v)


def normalize(specs: dict) -> dict:
    out: dict[str, str] = {}
    for k, v in specs.items():
        ck = KEY_CANON.get(k.strip(), k.strip())
        nv = tr_softtouch(norm_value(ck, v))   # Soft Touch → Софт-тач везде
        if ck not in out:               # первый выигрывает при слиянии дублей
            out[ck] = nv
    # сортировка по канону
    return dict(sorted(out.items(),
                       key=lambda kv: ORDER_IDX.get(kv[0], 999)))


def main() -> None:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    unknown: dict[str, int] = {}
    changed = 0
    for art, v in d.items():
        before = dict(v.get("specs", {}))
        v["specs_norm"] = normalize(before)
        for k in before:
            if k.strip() not in KEY_CANON:
                unknown[k] = unknown.get(k, 0) + 1
        if list(v["specs_norm"].keys()) != list(before.keys()) or \
           list(v["specs_norm"].values()) != list(before.values()):
            changed += 1
    SRC.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# Нормализация характеристик — отчёт", "",
             f"- товаров обработано: {len(d)}",
             f"- карточек изменено: {changed}", ""]
    if unknown:
        lines += ["## ⚠ Ключи без канона (попали как есть)", ""]
        lines += [f"- `{k}` × {n}" for k, n in sorted(unknown.items(), key=lambda x: -x[1])]
    else:
        lines.append("Все ключи покрыты каноном ✓")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"обработано {len(d)}, изменено {changed}, неизвестных ключей {len(unknown)}")
    print(f"saved -> {SRC}\nreport -> {REPORT}")


if __name__ == "__main__":
    main()
