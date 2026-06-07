# -*- coding: utf-8 -*-
"""A-D025W _2: фон=чисто-255 (фон идеально ровный), панель почти везде <255 -> не трогаем."""
import numpy as np, cv2
from pathlib import Path
from PIL import Image
from whitebg_cutout import cutout

SRC = Path("c:/Users/ikoko/Projects/aws-brand-site/_pipeline/_recut025/src")
OUT = Path("c:/Users/ikoko/Projects/aws-brand-site/_pipeline/_recut025/out"); OUT.mkdir(parents=True, exist_ok=True)

def to_bgr(p): return cv2.cvtColor(np.array(Image.open(p).convert("RGB")), cv2.COLOR_RGB2BGR)
def smooth(a, ss=4, bf=0.9):
    fg = (a > 0).astype(np.uint8); h, w = fg.shape
    big = cv2.resize(fg * 255, (w * ss, h * ss), interpolation=cv2.INTER_NEAREST)
    sm = cv2.GaussianBlur(big.astype(np.float32), (0, 0), ss * bf)
    st = (sm >= 127.5).astype(np.float32) * 255
    st = cv2.GaussianBlur(st, (0, 0), ss * 0.5)
    return cv2.resize(st, (w, h), interpolation=cv2.INTER_AREA).clip(0, 255).astype(np.uint8)

bgr = to_bgr(SRC / "A-D025W_2.jpg")
for wt in (1, 2, 3):
    rgba, info = cutout(bgr, white_tol=wt, grad_tol=14, spill_erode=0, adaptive=False)
    rgba[..., 3] = smooth(rgba[..., 3])
    Image.fromarray(rgba, "RGBA").save(OUT / f"A-D025W_2_wt{wt}.webp", "WEBP", quality=90, method=6)
    print("wt", wt, "cov", info["coverage"])
