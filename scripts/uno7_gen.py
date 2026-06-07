# -*- coding: utf-8 -*-
"""Генерация всех 75 ¾-вырезов УНО хирургическим cut_uno -> _pipeline/_uno7/cuts/."""
import zipfile, os, json, io
import numpy as np, cv2
from PIL import Image
import sys; sys.path.insert(0, 'scripts')
from uno7_cut import cut_uno

ROOT = "c:/Users/ikoko/Projects/aws-brand-site"
CUTS = os.path.join(ROOT, "_pipeline/_uno7/cuts")
mapping = json.load(open(os.path.join(ROOT, "_pipeline/_uno7/mapping.json"), encoding="utf-8"))

cache = {}; done = 0; report = []
for full, info in sorted(mapping.items()):
    z = zipfile.ZipFile(os.path.join(ROOT, info['zip']))
    key = (info['zip'], info['name'])
    if key not in cache:
        bgr = cv2.cvtColor(np.array(Image.open(io.BytesIO(z.read(info['name']))).convert('RGB')), cv2.COLOR_BGR2RGB)
        # ^ намеренно читаем как RGB->BGR ниже
        bgr = cv2.cvtColor(np.array(Image.open(io.BytesIO(z.read(info['name']))).convert('RGB')), cv2.COLOR_RGB2BGR)
        rgba, ci = cut_uno(bgr)
        cache[key] = (rgba, ci['coverage'], ci['punched'])
    rgba, cov, pun = cache[key]
    Image.fromarray(rgba, 'RGBA').save(os.path.join(CUTS, full + '.webp'), 'WEBP', quality=90, method=6)
    report.append((full, cov, pun)); done += 1

print("sgenerirovano:", done)
print("\nartikuly s punch>0 (prorezan montazhnyy slot):")
for full, cov, pun in sorted(report, key=lambda x: -x[2]):
    if pun > 0:
        print(f"  {full:28} cov={cov} punch={pun}")
print("\nbez punch (sokety/bez slotov):", sum(1 for _,_,p in report if p == 0))
