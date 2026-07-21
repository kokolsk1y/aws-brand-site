/* ============================================================
   Переключатель фона превью товара — единый компонент.
   Данные: /backgrounds.json · Стили: /bg-switch.css

   Разметка-контракт:
     [data-bg-stage]   — контейнер, который получает фон (можно много, синхронны).
     [data-bg-shadow]  — доп. флаг на сцене: адаптировать тень товара под тёмный фон.
     [data-bg-control] — точка монтирования ПУЛЬТА (панель свотчей).
                         data-bg-set="light,graphite" — ограничить набор фонов
                           (напр. несерийные товары: только белый+тёмный).
                           Без атрибута — все фоны из конфига.
                         data-bg-control="bar" — инлайн-вариант (в панели управления).
     Выбор единый на страницу, запоминается в localStorage; если сохранённый фон вне
     набора текущей страницы — откат к дефолтному из набора.
   ============================================================ */
(function () {
  if (window.__awsBgSwitch) return;
  window.__awsBgSwitch = true;

  var STORE_KEY = 'aws:bg';
  var CONFIG = null;
  var loading = null;

  function loadConfig() {
    if (CONFIG) return Promise.resolve(CONFIG);
    if (!loading) {
      loading = fetch('/backgrounds.json')
        .then(function (r) { return r.json(); })
        .then(function (c) { CONFIG = c; preloadImages(c); return c; })
        .catch(function () { CONFIG = { default: 'light', backgrounds: [] }; return CONFIG; });
    }
    return loading;
  }

  function preloadImages(cfg) {
    (cfg.backgrounds || []).forEach(function (b) {
      if (b.type === 'image' && b.src) { var im = new Image(); im.decoding = 'async'; im.src = b.src; }
    });
  }

  function allKeys(cfg) { return cfg.backgrounds.map(function (b) { return b.key; }); }

  // Разобрать data-bg-set в список ключей (в порядке конфига). Пусто → все.
  function parseSet(str, cfg) {
    if (!str) return allKeys(cfg);
    var want = str.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
    return allKeys(cfg).filter(function (k) { return want.indexOf(k) >= 0; });
  }

  // Набор фонов, допустимых на текущей странице = объединение наборов всех пультов.
  function pageSet(cfg) {
    var mounts = document.querySelectorAll('[data-bg-control]');
    if (!mounts.length) return allKeys(cfg);
    var seen = {};
    mounts.forEach(function (m) { parseSet(m.dataset.bgSet, cfg).forEach(function (k) { seen[k] = 1; }); });
    return allKeys(cfg).filter(function (k) { return seen[k]; });
  }

  function currentKey(cfg) {
    var ps = pageSet(cfg);
    var saved;
    try { saved = localStorage.getItem(STORE_KEY); } catch (e) {}
    if (saved && ps.indexOf(saved) >= 0) return saved;
    if (cfg.default && ps.indexOf(cfg.default) >= 0) return cfg.default;
    return ps[0];
  }

  function bgByKey(cfg, key) {
    return cfg.backgrounds.filter(function (b) { return b.key === key; })[0] || cfg.backgrounds[0];
  }

  function applyToStage(stage, bg) {
    if (bg.type === 'image') {
      stage.style.background = 'url("' + bg.src + '") center / cover no-repeat';
    } else {
      stage.style.background = bg.value;
    }
    stage.classList.toggle('is-dark-bg', !!bg.dark);
  }

  function updateControls(bg) {
    document.querySelectorAll('.bg-switch').forEach(function (p) {
      p.classList.toggle('is-dark', !!bg.dark);
    });
    document.querySelectorAll('.bg-switch__swatch').forEach(function (el) {
      var on = el.dataset.bgKey === bg.key;
      el.classList.toggle('is-active', on);
      el.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  function applyAll(cfg, key) {
    var bg = bgByKey(cfg, key);
    document.querySelectorAll('[data-bg-stage]').forEach(function (s) { applyToStage(s, bg); });
    updateControls(bg);
  }

  function select(cfg, key) {
    try { localStorage.setItem(STORE_KEY, key); } catch (e) {}
    applyAll(cfg, key);
  }

  function buildControl(cfg, mount) {
    if (mount.dataset.bgInit === '1') return;
    mount.dataset.bgInit = '1';
    var isBar = mount.dataset.bgControl === 'bar';
    var setKeys = parseSet(mount.dataset.bgSet, cfg);
    // Пульт из одного фона бессмыслен — не показываем.
    if (setKeys.length < 2) return;
    var panel = document.createElement('div');
    panel.className = 'bg-switch ' + (isBar ? 'bg-switch--bar' : 'bg-switch--float');
    panel.setAttribute('role', 'group');
    panel.setAttribute('aria-label', 'Фон превью');
    if (isBar) {
      var lab = document.createElement('span');
      lab.className = 'bg-switch__label';
      lab.textContent = 'Фон';
      panel.appendChild(lab);
    }
    cfg.backgrounds.filter(function (b) { return setKeys.indexOf(b.key) >= 0; }).forEach(function (b) {
      var s = document.createElement('button');
      s.type = 'button';
      s.className = 'bg-switch__swatch';
      s.dataset.bgKey = b.key;
      s.title = b.label;
      s.setAttribute('aria-label', 'Фон: ' + b.label);
      s.style.background = b.type === 'image'
        ? 'url("' + (b.thumb || b.src) + '") center / cover'
        : (b.swatch || b.value);
      s.addEventListener('click', function () { select(cfg, b.key); });
      panel.appendChild(s);
    });
    mount.appendChild(panel);
    requestAnimationFrame(function () { panel.classList.add('is-ready'); });
  }

  function init() {
    var stages = document.querySelectorAll('[data-bg-stage]');
    var mounts = document.querySelectorAll('[data-bg-control]');
    if (!stages.length && !mounts.length) return;
    loadConfig().then(function (cfg) {
      if (!cfg.backgrounds || !cfg.backgrounds.length) return;
      mounts.forEach(function (m) { buildControl(cfg, m); });
      applyAll(cfg, currentKey(cfg));
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  document.addEventListener('astro:page-load', init);
})();
