# -*- coding: utf-8 -*-
"""
Пере-резка ДЕФЕКТНЫХ каталожных фото из чистых исходников поставщика текущим
whitebg_cutout.cutout(). НИЧЕГО не перезаписывает в public до отдельного deploy.

Группы дефектов (см. исследование):
  - UNO grey/silver/dark_grey/matte_black — механизмы (заглушки в отверстиях, низкий контраст)
  - AURA все цвета, тыл/бок — отверстия рамки
  - точечно: A-002W, A-022W (выеденная клавиша / дуга на белом)

Алгоритм по группам:
  - рамки (имя «Рамка»)            -> cutout(remove_openings=True)
  - всё прочее (механизмы/лицо)    -> cutout() default  (проёмы закрывает заливка через зазоры)
QA-гейт: 12%<=cov<=98%. Прошедшие -> _pipeline/_recut_stage/<name>.webp + manifest.

Режимы:
  plan                 — что будет обработано (counts), без записи
  stage                — пере-резать в staging + QA + manifest
  sheet ART [ART...]   — контактный лист до(public)/после(staging) для артикулов
"""
import sys, os, re, glob, json
from pathlib import Path
import numpy as np, cv2
from PIL import Image
from scipy.ndimage import label, binary_fill_holes, binary_dilation

ROOT = Path("c:/Users/ikoko/Projects/aws-brand-site")
sys.path.insert(0, str(ROOT / "scripts"))
import verify_photos as vp
from whitebg_cutout import cutout


def punch_openings_safe(bgr, alpha, white_min=248, grad_tol=8):
    """Выбить ПРОЁМЫ монт. рамки (замочные прорези, круглые дырки), НЕ повредив товар.

    КЛЮЧЕВОЕ: проём = ЧИСТЫЙ студийный фон 255, видимый сквозь дырку. Измерено по
    исходникам: ВСЕ товары (белый/серебро/серый/чёрный) дают <=240 в центре, а фон =255.
    Поэтому порог white_min=248 изолирует ТОЛЬКО фон — металл/блики/белые клавиши не трогаются
    (это чинит крошку битых пикселей на серебре/сером). Доп. защита: проём enclosed,
    компактный (solidity), окружён материалом, площадь в диапазоне.
    Возвращает (alpha_out, n_punched)."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, 3); gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, 3)
    grad = cv2.GaussianBlur(np.sqrt(gx * gx + gy * gy), (0, 0), 1.0)
    bright = (gray >= white_min) & (grad <= grad_tol)    # чистый фон (внутри И снаружи)

    # внешний фон = яркие компоненты, КАСАЮЩИЕСЯ края кадра
    bl, bn = label(bright)
    border = set(np.concatenate([bl[0], bl[-1], bl[:, 0], bl[:, -1]]).tolist())
    border.discard(0)
    exterior = np.isin(bl, list(border)) if border else np.zeros_like(bright)
    enclosed = bright & (~exterior)                      # ЗАМКНУТЫЕ яркие = проёмы сквозь товар

    solid = binary_fill_holes(alpha > 128).astype(np.uint8)
    solid_area = max(int(solid.sum()), 1)
    enclosed = enclosed & (solid == 1)

    il, n = label(enclosed)
    out = alpha.copy()
    punched = 0
    for i in range(1, n + 1):
        comp = il == i
        a = int(comp.sum())
        if a < 60 or a > 0.35 * solid_area:           # мелочь / крупное светлое тело -> не проём
            continue
        # форма: проём компактный (solidity = площадь / площадь выпуклой оболочки)
        ys, xs = np.where(comp)
        pts = np.column_stack([xs, ys]).astype(np.int32)
        hull = cv2.convexHull(pts)
        harea = max(cv2.contourArea(hull), 1.0)
        if a / harea < 0.45:                           # тонкая дуга/полоса (блик) -> не проём
            continue
        out[comp] = 0
        punched += 1
    return out, punched

PUB = ROOT / "public/img/products"
STAGE = ROOT / "_pipeline/_recut_stage"
QADIR = ROOT / "_pipeline/_recut_qa"
DROP_VIEWS = {5, 6}

# ---- какие цвета/серии считаем дефектными группами ----
UNO_DEFECT_COLORS = {"grey", "silver", "dark grey", "matte black"}  # как в series colorwords
POINT_ARTICLES = {"A-002W", "A-022W"}

def deployed_names(items):
    """Воспроизводит наименование deploy(): drop 5/6, sort views, 0->'',1->_2..."""
    byview = {}
    for view, fp in items:
        if view in DROP_VIEWS:
            continue
        if view not in byview or fp.lower().endswith(".png"):
            byview[view] = fp
    ordered = [byview[v] for v in sorted(byview)]
    return [( ("" if i == 0 else f"_{i+1}"), src) for i, src in enumerate(ordered)]

def is_frame_article(key, by_series):
    for skey in by_series:
        for it in by_series[skey]:
            if it["article"] == key:
                return str(it.get("name","")).strip().lower().startswith("рамка")
    return False

def article_color(key, by_series):
    for skey in by_series:
        for it in by_series[skey]:
            if it["article"] == key:
                return skey, it.get("color","")
    return None, None

def select_targets(matched, by_series):
    """Список (skey,key) дефектных групп: ВСЯ новая УНО (все цвета) + ВСЯ Аура.
    Порог выбивания (white_min=248) безопасен для всех цветов, поэтому берём целиком."""
    tgt = []
    for (skey, key), rec in matched.items():
        if skey in ("uno", "aura"):
            tgt.append((skey, key))
    return sorted(tgt)

def to_bgr_path(src):
    return cv2.imdecode(np.fromfile(src, np.uint8), cv2.IMREAD_COLOR)

# Цвета УНО, где классический вырез ТЕЧЁТ по кромке (светлый металл сливается с
# белым фоном) -> берём силуэт нейросетью birefnet. У series.json эти цвета с
# подчёркиванием. Остальное (бел/чёрн УНО, вся аура, дизайн) -> classic (рамка тёмная, край чёткий).
NEURAL_COLORS = {"grey", "silver", "dark_grey", "matte_black"}

# Birefnet только для ВЫКЛЮЧАТЕЛЕЙ (плоская клавиша) нужных цветов.
# Розетки (круглое отверстие) birefnet ест — для них classic.
# Список switch-артикулов нужных цветов из series.json groups.switches.
def _build_neural_articles():
    import json
    d = json.load(open(str(ROOT / "src/data/series.json"), encoding="utf-8"))
    s = set()
    for p in d["uno"]["groups"].get("switches", []):
        if p["color"] in NEURAL_COLORS:
            s.add(p["article"])
    return s
NEURAL_ARTICLES = _build_neural_articles()

_BN = {}
def _birefnet_alpha(bgr):
    from rembg import remove, new_session
    if "s" not in _BN:
        _BN["s"] = new_session("birefnet-general")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    out = remove(Image.fromarray(rgb), session=_BN["s"], post_process_mask=True)
    return np.array(out)[..., 3]

def _largest_cc(mask):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if n <= 1:
        return mask
    idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return (lab == idx).astype(np.uint8)

def recut_one(src, frame, neural=False):
    bgr = to_bgr_path(src)
    if bgr is None:
        return None, None
    if max(bgr.shape[:2]) > 2000:
        s = 2000 / max(bgr.shape[:2])
        bgr = cv2.resize(bgr, (int(bgr.shape[1]*s), int(bgr.shape[0]*s)), interpolation=cv2.INTER_AREA)
    if neural:
        ab = _birefnet_alpha(bgr)
        m = _largest_cc(ab > 128)
        # НЕ делаем binary_fill_holes целиком — это заполняет монтажные отверстия.
        # Заполняем ТОЛЬКО маленькие внутренние дыры (структурные щели < 800px),
        # которые в исходнике ТЁМНЫЕ (= часть товара, не фон сквозь дырку).
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        inv = (m == 0).astype(np.uint8)
        hl, hn = label(inv)
        border = set(np.concatenate([hl[0], hl[-1], hl[:,0], hl[:,-1]]).tolist())
        border.discard(0)
        for i in range(1, hn + 1):
            if i in border:
                continue
            comp = (hl == i)
            if comp.sum() > 800:          # крупное = монтажное отверстие → не трогаем
                continue
            if gray[comp].mean() >= 240:  # светлое = фон сквозь дырку → не трогаем
                continue
            m[comp] = 1                   # маленькая тёмная щель → закрыть
        # лёгкий срез 1px загрязнённой кромки
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        m = cv2.erode(m, k, 1)
        alpha = (m * 255).astype(np.uint8)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        rgba = np.dstack([rgb, alpha])
        info = {"coverage": round(100 * (alpha > 128).mean(), 1), "mode": "birefnet"}
    else:
        rgba, info = cutout(bgr, remove_openings=frame)
    if not frame:
        # выбить проёмы монт. рамки на любых механизмах (тыл/бок/лицо) — безопасно
        a2, npn = punch_openings_safe(bgr, rgba[..., 3])
        rgba[..., 3] = a2
        info["punched"] = npn
    return rgba, info

def magenta(rgba):
    rgb = rgba[..., :3].astype(np.float32); a = (rgba[..., 3:4].astype(np.float32)/255)
    base = np.zeros_like(rgb); base[..., 0] = 255; base[..., 2] = 255
    return (rgb*a + base*(1-a)).astype(np.uint8)

def checker(rgba, cell=18):
    H, W = rgba.shape[:2]; yy, xx = np.mgrid[0:H, 0:W]; chk = (((xx//cell)+(yy//cell)) % 2)
    base = np.where(chk[..., None] == 0, 230, 195).astype(np.float32).repeat(3, 2)
    a = (rgba[..., 3:4].astype(np.float32)/255)
    return (rgba[..., :3].astype(np.float32)*a + base*(1-a)).astype(np.uint8)

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "plan"
    matched, by_series, *_ = vp.build_matches()
    targets = select_targets(matched, by_series)

    if mode == "plan":
        nfiles = 0; bygrp = {}
        for skey, key in targets:
            names = deployed_names(matched[(skey, key)]["items"])
            nfiles += len(names)
            bygrp[skey] = bygrp.get(skey, 0) + len(names)
        print(f"Дефектных артикулов: {len(targets)} | файлов(ракурсов): {nfiles}")
        for k, v in sorted(bygrp.items()):
            print(f"  {k}: {v} файлов")
        # показать пример маппинга
        for skey, key in targets[:4]:
            print(f"  пример [{key}] frame={is_frame_article(key,by_series)}:")
            for suf, src in deployed_names(matched[(skey,key)]["items"]):
                print(f"     {key}{suf}.webp  <-  {Path(src).name}")
        return

    if mode == "stage":
        STAGE.mkdir(parents=True, exist_ok=True)
        manifest = []; flagged = []; done = 0
        for skey, key in targets:
            frame = is_frame_article(key, by_series)
            sk, color = article_color(key, by_series)
            neural = (key in NEURAL_ARTICLES and not frame)
            for suf, src in deployed_names(matched[(skey, key)]["items"]):
                name = f"{key}{suf}.webp"
                rgba, info = recut_one(src, frame, neural=neural)
                if rgba is None:
                    flagged.append((name, "read-fail")); continue
                cov = info["coverage"]
                if not (12.0 <= cov <= 98.0):
                    flagged.append((name, f"cov={cov}")); continue
                Image.fromarray(rgba, "RGBA").save(STAGE / name, "WEBP", quality=90, method=6)
                manifest.append({"name": name, "src": str(src), "cov": cov, "frame": frame, "neural": neural})
                done += 1
        (STAGE / "_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        (STAGE / "_flagged.txt").write_text("\n".join(f"{n}\t{r}" for n, r in flagged), encoding="utf-8")
        print(f"Staged OK: {done} | flagged: {len(flagged)} -> {STAGE}")
        if flagged:
            for n, r in flagged[:40]: print("  FLAG", n, r)
        return

    if mode == "sheet":
        arts = sys.argv[2:]
        QADIR.mkdir(parents=True, exist_ok=True)
        for art in arts:
            # все staged файлы этого артикула
            files = sorted(glob.glob(str(STAGE / f"{art}*.webp")))
            rows = []
            for sf in files:
                name = Path(sf).name
                after = np.array(Image.open(sf).convert("RGBA"))
                pubf = PUB / name
                if pubf.exists():
                    before = np.array(Image.open(pubf).convert("RGBA"))
                else:
                    before = np.zeros_like(after)
                def fit(img, h=300):
                    s = h/img.shape[0]; return cv2.resize(img, (int(img.shape[1]*s), h))
                g = np.full((300, 6, 3), 255, np.uint8)
                row = np.hstack([fit(magenta(before)), g, fit(magenta(after)), g, fit(checker(after))])
                cv2.putText(row, name+"  [before-mag | after-mag | after-chk]", (4, 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 140, 0), 2, cv2.LINE_AA)
                rows.append(row)
            if not rows:
                print("нет staged для", art); continue
            w = max(r.shape[1] for r in rows)
            rows = [cv2.copyMakeBorder(r, 3, 3, 0, w-r.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in rows]
            out = QADIR / f"{art}.png"
            cv2.imencode(".png", cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR))[1].tofile(str(out))
            print("sheet:", out)
        return

if __name__ == "__main__":
    main()
