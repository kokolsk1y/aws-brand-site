/* ============================
   AWS Brand Site — script.js
   v6: По ТЗ Яны
   Lenis + Swiper + GSAP
   ============================ */

gsap.registerPlugin(ScrollTrigger);

// Refresh ScrollTrigger при resize (debounced)
let _stRefreshTimer;
window.addEventListener('resize', () => {
    clearTimeout(_stRefreshTimer);
    _stRefreshTimer = setTimeout(() => ScrollTrigger.refresh(), 250);
});

// ─── SPLASH SCREEN (первый заход) ───
(function () {
    // Создаём splash если его нет в HTML
    if (!document.getElementById('splash') && !sessionStorage.getItem('aws-splash-seen')) {
        const s = document.createElement('div');
        s.id = 'splash';
        s.className = 'splash';
        s.innerHTML = '<div class="splash__logo-wrap"><img src="logo/AWS.png" alt="AWS" class="splash__logo"><div class="splash__line"></div></div>';
        document.documentElement.appendChild(s);
    }
    const splash = document.getElementById('splash');
    if (!splash) return;
    const firstVisit = !sessionStorage.getItem('aws-splash-seen');
    if (!firstVisit) { splash.remove(); return; }
    sessionStorage.setItem('aws-splash-seen', '1');
    let hidden = false;
    const hide = () => {
        if (hidden) return;
        hidden = true;
        splash.classList.add('is-hiding');
        setTimeout(() => splash.remove(), 400);
    };
    // Прячем как только DOM готов (не ждём все картинки/видео)
    if (document.readyState !== 'loading') setTimeout(hide, 600);
    else document.addEventListener('DOMContentLoaded', () => setTimeout(hide, 600));
    // Hard fallback: через 2 секунды splash уйдёт в любом случае
    setTimeout(hide, 2000);
})();

// ─── HERO CURSOR SPOTLIGHT ───
(function () {
    const hero = document.querySelector('.hero');
    if (!hero) return;
    let rafId = null;
    hero.addEventListener('mousemove', e => {
        if (rafId) return;
        rafId = requestAnimationFrame(() => {
            const rect = hero.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            hero.style.setProperty('--mx', x + 'px');
            hero.style.setProperty('--my', y + 'px');
            rafId = null;
        });
    }, { passive: true });
})();

// ─── LENIS: Плавный скролл ───

const lenis = new Lenis({
    duration: 1.2,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    smoothWheel: true,
    touchMultiplier: 2
});

lenis.on('scroll', ScrollTrigger.update);
gsap.ticker.add((time) => lenis.raf(time * 1000));
gsap.ticker.lagSmoothing(0);

// Обработка hash-якорей при загрузке (напр. переход с /series/* на /#series)
function scrollToHashTarget() {
    const hash = window.location.hash;
    if (!hash || hash.length < 2) return;
    const target = document.querySelector(hash);
    if (!target) return;

    // Моментально прыгаем к якорю без анимации (hero большой, важно оказаться на нужной точке)
    const jump = () => {
        const rect = target.getBoundingClientRect();
        const y = rect.top + window.pageYOffset - 80;
        window.scrollTo(0, y);
        if (lenis && lenis.scrollTo) lenis.scrollTo(target, { duration: 0.1, immediate: true });
    };

    // 3 попытки: сразу, через 300мс, через 800мс — чтобы накрыть все сценарии (видео ещё грузится,
    // Swiper разворачивается, картинки resize)
    jump();
    setTimeout(jump, 300);
    setTimeout(jump, 800);
}
// Запускаем ДО события load, чтобы опередить браузерный нативный jump
if (window.location.hash) {
    // Первая попытка на DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', scrollToHashTarget);
    } else {
        scrollToHashTarget();
    }
    // Вторая серия попыток после полной загрузки
    window.addEventListener('load', scrollToHashTarget);
}

// Плавный скролл для внутренних якорей
document.querySelectorAll('a[href^="/#"], a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
        const href = a.getAttribute('href');
        const hash = href.startsWith('/#') ? href.slice(1) : href;
        if (hash === '#' || !hash) return;
        const target = document.querySelector(hash);
        if (!target) return;

        e.preventDefault();
        history.pushState(null, '', hash);

        // Если ссылка внутри side-menu — сначала закрыть меню, потом скроллить
        const isInSideMenu = a.closest('.side-menu');
        if (isInSideMenu) {
            // closeMenu триггерим вручную с микро-задержкой до scroll
            if (typeof closeMenu === 'function') closeMenu();
            // Ждём 320мс (CSS transition меню) чтобы lenis.start() успел отработать
            setTimeout(() => {
                lenis.scrollTo(target, { duration: 1.1 });
            }, 320);
        } else {
            lenis.scrollTo(target, { duration: 1.1 });
        }
    });
});

// ─── SIDE MENU ───

const menuToggle = document.getElementById('menuToggle');
const menuClose = document.getElementById('menuClose');
const menuOverlay = document.getElementById('menuOverlay');
const sideMenu = document.getElementById('sideMenu');

function openMenu() {
    if (!sideMenu) return;
    sideMenu.classList.add('open');
    if (menuToggle) menuToggle.setAttribute('aria-expanded', 'true');
    if (lenis) lenis.stop();
}

function closeMenu() {
    if (!sideMenu) return;
    sideMenu.classList.remove('open');
    if (menuToggle) menuToggle.setAttribute('aria-expanded', 'false');
    if (lenis) lenis.start();
}

if (menuToggle) menuToggle.addEventListener('click', openMenu);
if (menuClose) menuClose.addEventListener('click', closeMenu);
if (menuOverlay) menuOverlay.addEventListener('click', closeMenu);

// Закрытие при клике на ссылку (только для внешних ссылок — hash-якоря закрывают меню через anchor-handler ниже)
if (sideMenu) sideMenu.querySelectorAll('.side-menu__item, .side-menu__sub').forEach(link => {
    link.addEventListener('click', e => {
        const href = link.getAttribute('href') || '';
        // Hash-якоря закроют меню сами (с задержкой перед scroll)
        if (href.startsWith('#') || href.startsWith('/#')) return;
        closeMenu();
    });
});

// Dropdown категорий
document.querySelectorAll('.side-menu__toggle').forEach(btn => {
    btn.addEventListener('click', () => {
        btn.parentElement.classList.toggle('open');
    });
});

// ─── HERO SWIPER ───

const heroSwiper = new Swiper('.hero-swiper', {
    effect: 'fade',
    fadeEffect: { crossFade: true },
    speed: 1000,
    autoplay: {
        delay: 4200,
        disableOnInteraction: false
    },
    loop: true,
    pagination: {
        el: '.hero-pagination',
        clickable: true
    }
});

// Смена темы хедера
const header = document.getElementById('header');

// Темы хедера по realIndex слайдов (loop:true создаёт клоны —
// querySelector ненадёжен, используем массив напрямую)
const HERO_THEMES = ['dark', 'dark', 'dark', 'dark', 'light'];
function updateHeaderTheme() {
    const theme = HERO_THEMES[heroSwiper.realIndex] || 'dark';
    if (!header.classList.contains('scrolled')) {
        header.classList.remove('dark', 'light');
        header.classList.add(theme);
    }
}

updateHeaderTheme();
heroSwiper.on('slideChange', updateHeaderTheme);

// Анимация контента слайда при смене
function animateSlideContent() {
    const active = document.querySelector('.swiper-slide-active .hero-slide__content');
    if (!active) return;

    const label = active.querySelector('.hero-slide__label');
    const title = active.querySelector('.hero-slide__title');
    const subtitle = active.querySelector('.hero-slide__subtitle');
    const btn = active.querySelector('.hero-slide__btn');
    const tags = active.querySelector('.hero-slide__tags');

    if (label) gsap.fromTo(label, { opacity: 0, y: 15 }, { opacity: 0.5, y: 0, duration: 0.7, delay: 0.2, ease: 'power3.out' });
    if (title) gsap.fromTo(title, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.9, delay: 0.3, ease: 'power3.out' });
    if (subtitle) gsap.fromTo(subtitle, { opacity: 0, y: 20 }, { opacity: 0.6, y: 0, duration: 0.8, delay: 0.5, ease: 'power3.out' });
    if (btn) gsap.fromTo(btn, { opacity: 0, y: 15 }, { opacity: 1, y: 0, duration: 0.7, delay: 0.6, ease: 'power3.out' });
    if (tags) gsap.fromTo(tags, { opacity: 0, y: 15 }, { opacity: 1, y: 0, duration: 0.7, delay: 0.7, ease: 'power3.out' });
}

heroSwiper.on('slideChangeTransitionStart', animateSlideContent);

// Синхронизация видео и слайдера hero.
// Схема: crossfade (SWIPER_SPEED) стартует за 1с до конца видео → стоп-кадр не показывается.
// Особенность hero-1: перед play — freeze первого кадра на HOLD_START_MS (видео заморожено).
const SWIPER_SPEED = 1000;
const HOLD_START_MS = 2000;
const SLIDE_MODES = {
    0: { holdStart: HOLD_START_MS },
    1: {},
    2: {}
};
let currentTimeHandler = null;
let holdStartTimer = null;
let holdGuardInterval = null;  // watchdog — давит любые попытки play() во время freeze
let pendingHoldVideo = null;   // видео в состоянии freeze (для 'play' listener)

function clearSyncHandlers() {
    if (currentTimeHandler) {
        currentTimeHandler.video.removeEventListener('timeupdate', currentTimeHandler.fn);
        currentTimeHandler = null;
    }
    if (holdStartTimer) { clearTimeout(holdStartTimer); holdStartTimer = null; }
    if (holdGuardInterval) { clearInterval(holdGuardInterval); holdGuardInterval = null; }
    if (pendingHoldVideo) {
        pendingHoldVideo.removeEventListener('play', freezeGuard);
        pendingHoldVideo = null;
    }
}

function freezeGuard(e) {
    // любое play() во время freeze — откатываем обратно на паузу + кадр 0
    const v = e.target;
    v.pause();
    try { v.currentTime = 0; } catch (err) {}
}

function getActiveVideo() {
    const slide = heroSwiper.slides && heroSwiper.slides[heroSwiper.activeIndex];
    return slide ? slide.querySelector('.hero-slide__video') : null;
}

function freezeFirstFrame(video) {
    video.pause();
    try { video.currentTime = 0; } catch (e) {}
    video.addEventListener('play', freezeGuard);
    pendingHoldVideo = video;
    // на случай если браузер запустит воспроизведение позже (iOS, preload) —
    // watchdog каждые 100мс возвращает на кадр 0 и ставит паузу.
    holdGuardInterval = setInterval(() => {
        if (!video.paused) video.pause();
        if (video.currentTime > 0.05) { try { video.currentTime = 0; } catch (e) {} }
    }, 100);
}

function releaseFreeze(video) {
    if (holdGuardInterval) { clearInterval(holdGuardInterval); holdGuardInterval = null; }
    video.removeEventListener('play', freezeGuard);
    pendingHoldVideo = null;
}

// При старте crossfade: сбрасываем видео нового слайда на 0 кадр.
// Для слайдов с holdStart — freeze. Для остальных — play сразу.
heroSwiper.on('slideChangeTransitionStart', () => {
    clearSyncHandlers();
    const active = getActiveVideo();
    if (!active) return;
    const cfg = SLIDE_MODES[heroSwiper.realIndex];
    if (cfg && cfg.holdStart) {
        freezeFirstFrame(active);
    } else {
        try { active.currentTime = 0; } catch (e) {}
        active.play();
    }
});

function bindVideoEndSync() {
    clearSyncHandlers();
    const cfg = SLIDE_MODES[heroSwiper.realIndex];

    if (!cfg) { heroSwiper.autoplay && heroSwiper.autoplay.start(); return; }

    const activeVideo = getActiveVideo();
    if (!activeVideo) return;

    if (heroSwiper.autoplay) heroSwiper.autoplay.stop();

    let triggered = false;
    const attachCrossfadeSync = () => {
        const fn = () => {
            if (triggered) return;
            if (!activeVideo.duration || isNaN(activeVideo.duration)) return;
            const remaining = activeVideo.duration - activeVideo.currentTime;
            if (remaining <= SWIPER_SPEED / 1000) {
                triggered = true;
                heroSwiper.slideNext();
            }
        };
        activeVideo.addEventListener('timeupdate', fn);
        currentTimeHandler = { video: activeVideo, fn };
    };

    if (cfg.holdStart) {
        freezeFirstFrame(activeVideo);
        holdStartTimer = setTimeout(() => {
            releaseFreeze(activeVideo);
            activeVideo.play();
            attachCrossfadeSync();
        }, cfg.holdStart);
    } else {
        attachCrossfadeSync();
    }
}

heroSwiper.on('slideChangeTransitionEnd', bindVideoEndSync);

// На холодном заходе: сразу замораживаем ВСЕ hero-видео, запускаем логику.
(function initHeroVideos() {
    document.querySelectorAll('.hero-slide__video').forEach(v => {
        v.pause();
        try { v.currentTime = 0; } catch (e) {}
    });
    // дождёмся готовности метаданных первого видео чтобы currentTime=0 точно применился
    const firstVideo = getActiveVideo();
    const start = () => bindVideoEndSync();
    if (!firstVideo || firstVideo.readyState >= 1) {
        setTimeout(start, 100);
    } else {
        firstVideo.addEventListener('loadedmetadata', start, { once: true });
        setTimeout(start, 1500); // fallback
    }
})();

// Начальная анимация
setTimeout(animateSlideContent, 300);


// ─── HEADER: scrolled state ───

ScrollTrigger.create({
    trigger: '.hero',
    start: 'bottom top',
    onEnter: () => {
        header.classList.add('scrolled');
        header.classList.remove('dark', 'light');
    },
    onLeaveBack: () => {
        header.classList.remove('scrolled');
        updateHeaderTheme();
    }
});

// ─── SERIES: Карточки кликабельны → /series/[slug] ───

document.querySelectorAll('.series__card[data-series]').forEach(card => {
    card.style.cursor = 'pointer';
    card.addEventListener('click', e => {
        // Не переходить если кликнули на точку цвета (она своя логика)
        if (e.target.closest('.dot[data-color]')) return;
        const slug = card.dataset.series;
        if (slug) window.location.href = '/series/' + slug;
    });
});

// ─── SERIES: Появление карточек ───

const seriesCards = document.querySelectorAll('.series__card');
seriesCards.forEach((card, i) => {
    gsap.from(card, {
        opacity: 0,
        y: 50,
        duration: 0.8,
        delay: i * 0.12,
        ease: 'power3.out',
        scrollTrigger: {
            trigger: '.series__grid',
            start: 'top 80%',
            once: true
        }
    });
});

// Series header
gsap.from('.series__header', {
    opacity: 0, y: 40,
    duration: 0.9,
    ease: 'power3.out',
    scrollTrigger: {
        trigger: '.series',
        start: 'top 75%',
        once: true
    }
});

// ─── SERIES CARDS: Переключатель цвета (статичное фото) ───

document.querySelectorAll('.series__card').forEach(card => {
    const photo = card.querySelector('.series__photo');
    if (!photo) return;
    const img = photo.querySelector('.series__photo-img');
    const ph = photo.querySelector('.series__photo-placeholder');
    const sources = {
        white: photo.dataset.white || '',
        black: photo.dataset.black || ''
    };
    const dots = card.querySelectorAll('.dot[data-color]');

    function showPlaceholder() {
        if (img) img.style.display = 'none';
        if (ph) ph.style.display = '';
    }
    function showImage() {
        if (img) img.style.display = '';
        if (ph) ph.style.display = 'none';
    }

    if (img) {
        img.addEventListener('error', showPlaceholder);
        img.addEventListener('load', showImage);
    }

    function setColor(color) {
        const src = sources[color];
        if (src) {
            img.src = src;
        } else {
            showPlaceholder();
        }
    }

    // Инициализация по активной точке
    const activeDot = card.querySelector('.dot[data-color].active');
    if (activeDot) setColor(activeDot.dataset.color);

    dots.forEach(dot => {
        dot.addEventListener('click', () => {
            dots.forEach(d => d.classList.remove('active'));
            dot.classList.add('active');
            setColor(dot.dataset.color);
        });
    });
});

// ─── CONSTRUCTOR: Chip toggle + обновление превью ───

const constructorState = { series: 'UNO', color: 'Белый', frame: 'Пластик' };
const constructorPreview = document.getElementById('constructorPreview');
const constructorPlaceholder = document.getElementById('constructorPlaceholder');

const IMG_VERSION = 'v=20260414e';
const constructorMap = {
    'UNO|Белый|Пластик':   `img/series/uno-1kl-w.png?${IMG_VERSION}`,
    'UNO|Чёрный|Пластик':  `img/series/uno-1kl-b.png?${IMG_VERSION}`,
    'AURA|Белый|Пластик':  `img/series/aura-1kl-w.png?${IMG_VERSION}`,
    'AURA|Чёрный|Пластик': `img/series/aura-1kl-b.png?${IMG_VERSION}`
};

function showConstructorPlaceholder() {
    if (constructorPreview) constructorPreview.style.display = 'none';
    if (constructorPlaceholder) constructorPlaceholder.style.display = '';
}
function showConstructorImage() {
    if (constructorPreview) constructorPreview.style.display = '';
    if (constructorPlaceholder) constructorPlaceholder.style.display = 'none';
}
if (constructorPreview) {
    constructorPreview.addEventListener('error', showConstructorPlaceholder);
    constructorPreview.addEventListener('load', showConstructorImage);
}

function updateConstructorPreview() {
    const key = constructorState.series + '|' + constructorState.color + '|' + constructorState.frame;
    const src = constructorMap[key];
    if (!constructorPreview || !constructorPlaceholder) return;

    const apply = () => {
        if (src) {
            constructorPreview.src = src;
            showConstructorImage();
        } else {
            showConstructorPlaceholder();
        }
    };

    // View Transitions API — нативный морфинг между состояниями (Chrome 111+, Safari 18+)
    if (document.startViewTransition) {
        constructorPreview.style.viewTransitionName = 'constructor-product';
        document.startViewTransition(() => apply());
    } else {
        // Fallback — fade-out + src swap + fade-in
        constructorPreview.classList.add('fade-out');
        setTimeout(() => {
            apply();
            constructorPreview.classList.remove('fade-out');
        }, 250);
    }
}

document.querySelectorAll('.constructor__option').forEach(option => {
    const label = option.querySelector('.constructor__option-label')?.textContent.trim();
    const chips = option.querySelectorAll('.constructor__chip');
    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            chips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            const value = chip.textContent.trim();
            if (label === 'Серия') constructorState.series = value;
            else if (label === 'Цвет') constructorState.color = value;
            else if (label === 'Рамка') constructorState.frame = value;
            updateConstructorPreview();
        });
    });
});

// Constructor появление
gsap.from('.constructor', {
    opacity: 0, y: 40,
    duration: 0.9,
    ease: 'power3.out',
    scrollTrigger: {
        trigger: '.constructor',
        start: 'top 80%',
        once: true
    }
});

// ─── CATEGORIES: Появление карточек ───

document.querySelectorAll('.categories__card').forEach((card, i) => {
    gsap.from(card, {
        opacity: 0,
        y: 40,
        scale: 0.97,
        duration: 0.7,
        delay: i * 0.08,
        ease: 'power3.out',
        scrollTrigger: {
            trigger: '.categories__grid',
            start: 'top 80%',
            once: true
        }
    });
});

gsap.from('.categories__header', {
    opacity: 0, y: 30,
    duration: 0.8,
    ease: 'power3.out',
    scrollTrigger: {
        trigger: '.categories',
        start: 'top 75%',
        once: true
    }
});

// ─── ABOUT BRAND ───

const aboutSection = document.querySelector('.about');
if (aboutSection) {
    const aboutEls = ['.about .label', '.about__title', '.about__desc', '.about__link'];
    aboutEls.forEach((sel, i) => {
        gsap.from(sel, {
            opacity: 0, y: 30,
            duration: 0.8,
            delay: i * 0.12,
            ease: 'power3.out',
            scrollTrigger: { trigger: aboutSection, start: 'top 70%', once: true }
        });
    });

    gsap.from('.about__image', {
        opacity: 0, y: 50, scale: 0.97,
        duration: 1,
        delay: 0.2,
        ease: 'power3.out',
        scrollTrigger: { trigger: aboutSection, start: 'top 70%', once: true }
    });
}

// ─── ADVANTAGES SWIPER ───

const advantagesSwiper = new Swiper('.advantages-swiper', {
    effect: 'fade',
    fadeEffect: { crossFade: true },
    speed: 800,
    autoplay: {
        delay: 8000,
        disableOnInteraction: false
    },
    loop: true,
    pagination: {
        el: '.advantages-pagination',
        clickable: true
    }
});

// Анимация контента при смене слайда
advantagesSwiper.on('slideChangeTransitionStart', () => {
    const content = document.querySelector('.swiper-slide-active .advantages__content');
    if (!content) return;

    const num = content.querySelector('.advantages__num');
    const heading = content.querySelector('.advantages__heading');
    const text = content.querySelector('.advantages__text');

    if (num) gsap.fromTo(num, { opacity: 0, x: -20 }, { opacity: 1, x: 0, duration: 0.6, delay: 0.15, ease: 'power3.out' });
    if (heading) gsap.fromTo(heading, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.7, delay: 0.25, ease: 'power3.out' });
    if (text) gsap.fromTo(text, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.7, delay: 0.35, ease: 'power3.out' });
});

// ─── PRICE TICKERS: автоклонирование для seamless loop ───
// Cобирает уникальные карточки из HTML и клонирует столько раз, чтобы
// "половина трека" (50% — точка повтора в CSS keyframes) гарантированно
// покрывала контейнер. Иначе при translateY(-50%) снизу/сверху образуется
// пустое пространство ("пробка прерывается").

function setupPriceTicker(ticker) {
    const track = ticker.querySelector('.adv-ticker__track');
    if (!track) return;

    // Первый вызов: сохраним оригинал в data-атрибут, чтобы при resize пересобирать с нуля
    if (!track.dataset.sourceSaved) {
        track.dataset.sourceSaved = '1';
        // Берём первую половину карточек (в HTML они уже задублированы 2×)
        const all = Array.from(track.children);
        const half = Math.max(1, Math.floor(all.length / 2));
        const sourceHTML = all.slice(0, half).map(el => el.outerHTML).join('');
        track.dataset.source = sourceHTML;
    }

    const sourceHTML = track.dataset.source;
    if (!sourceHTML) return;

    // Ставим один экземпляр, чтобы измерить высоту одной копии
    track.innerHTML = sourceHTML;
    // Высоту измеряем после rAF, чтобы учесть лэйаут
    requestAnimationFrame(() => {
        const copyH = track.scrollHeight;
        const containerH = ticker.clientHeight;
        if (!copyH || !containerH) return;

        // "Половина трека" должна покрывать контейнер → копий в половине ≥ ceil(containerH / copyH) + 1 (запас)
        const copiesPerHalf = Math.max(1, Math.ceil(containerH / copyH) + 1);
        const totalCopies = copiesPerHalf * 2;

        // Собираем финальный трек
        track.innerHTML = sourceHTML.repeat(totalCopies);
    });
}

function initPriceTickers() {
    document.querySelectorAll('.adv-ticker').forEach(setupPriceTicker);
}

// Первая инициализация — после загрузки всех картинок (чтобы высоты карточек были корректными)
if (document.readyState === 'complete') {
    initPriceTickers();
} else {
    window.addEventListener('load', initPriceTickers);
}

// Пересобираем при resize (debounced)
let _tickerResizeTimer;
window.addEventListener('resize', () => {
    clearTimeout(_tickerResizeTimer);
    _tickerResizeTimer = setTimeout(initPriceTickers, 200);
});


// ─── HERO TAGS → ADVANTAGES SLIDE ───

document.querySelectorAll('.hero-slide__tag[data-adv-slide]').forEach(tag => {
    tag.addEventListener('click', e => {
        e.preventDefault();
        const idx = parseInt(tag.dataset.advSlide, 10) || 0;
        const section = document.getElementById('advantages');
        if (!section) return;

        // Переключаем swiper МГНОВЕННО до скролла — пользователь прибудет на готовый слайд
        if (advantagesSwiper && advantagesSwiper.slideToLoop) {
            advantagesSwiper.slideToLoop(idx, 0);
        }
        lenis.scrollTo(section, { duration: 1.1 });
    });
});

// ─── WHERE BUY ───

gsap.from('.where-buy__title', {
    opacity: 0, y: 40,
    duration: 0.9,
    ease: 'power3.out',
    scrollTrigger: {
        trigger: '.where-buy',
        start: 'top 75%',
        once: true
    }
});

document.querySelectorAll('.where-buy__card').forEach((card, i) => {
    gsap.from(card, {
        opacity: 0, y: 40,
        duration: 0.7,
        delay: i * 0.1,
        ease: 'power3.out',
        scrollTrigger: {
            trigger: '.where-buy__grid',
            start: 'top 80%',
            once: true
        }
    });
});

// ─── FOOTER ───

gsap.from('.footer__top', {
    opacity: 0, y: 30,
    duration: 0.8,
    ease: 'power3.out',
    scrollTrigger: {
        trigger: '.footer',
        start: 'top 85%',
        once: true
    }
});

// ─── PARALLAX: мягкий drift только на контейнерах (продукт не вылезает) ───

document.querySelectorAll('.series__card-visual, .categories__card-img, .about__image').forEach(el => {
    gsap.to(el, {
        yPercent: -4,
        ease: 'none',
        scrollTrigger: {
            trigger: el,
            start: 'top bottom',
            end: 'bottom top',
            scrub: true
        }
    });
});

// Лёгкий drift самого продукта — внутри безопасной амплитуды 4%, не выскочит за padding
document.querySelectorAll('.series__photo-img, .categories__card-img img').forEach(el => {
    gsap.to(el, {
        yPercent: -4,
        ease: 'none',
        scrollTrigger: {
            trigger: el.closest('.series__card, .categories__card'),
            start: 'top bottom',
            end: 'bottom top',
            scrub: 1.5
        }
    });
});

// ─── SPOTLIGHT HOVER: светлое пятно следует за курсором в карточках ───
(function initSpotlight() {
    if (window.matchMedia('(hover: none)').matches) return;
    document.querySelectorAll('.categories__card, .series__card').forEach(card => {
        const visual = card.querySelector('.categories__card-img, .series__card-visual');
        if (!visual) return;
        visual.addEventListener('mousemove', (e) => {
            const rect = visual.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;
            visual.style.setProperty('--spot-x', x + '%');
            visual.style.setProperty('--spot-y', y + '%');
        });
    });
})();

// ─── 3D TILT: лёгкий наклон карточек серий (1-2°) ───
(function initTilt() {
    if (window.matchMedia('(hover: none)').matches) return;
    const MAX = 2.5;
    document.querySelectorAll('.series__card').forEach(card => {
        card.style.transformStyle = 'preserve-3d';
        card.style.transition = 'transform 0.4s cubic-bezier(0.23, 1, 0.32, 1), box-shadow 0.5s';
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height / 2;
            const dx = (e.clientX - cx) / (rect.width / 2);
            const dy = (e.clientY - cy) / (rect.height / 2);
            card.style.transform = `perspective(1200px) translateY(-6px) rotateX(${-dy * MAX}deg) rotateY(${dx * MAX}deg)`;
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = '';
        });
    });
})();

// ─── MAGNETIC CTA: кнопки "притягиваются" к курсору ───
(function initMagneticButtons() {
    if (window.matchMedia('(hover: none)').matches) return; // пропускаем на тач-устройствах
    const STRENGTH = 0.35;
    const RADIUS = 90;
    document.querySelectorAll('.hero-slide__btn, .about__link').forEach(btn => {
        btn.style.transition = 'transform 0.25s cubic-bezier(0.23, 1, 0.32, 1)';
        btn.style.willChange = 'transform';
        btn.addEventListener('mousemove', (e) => {
            const rect = btn.getBoundingClientRect();
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height / 2;
            const dx = e.clientX - cx;
            const dy = e.clientY - cy;
            const dist = Math.sqrt(dx*dx + dy*dy);
            if (dist < RADIUS + Math.max(rect.width, rect.height) / 2) {
                btn.style.transform = `translate(${dx * STRENGTH}px, ${dy * STRENGTH}px)`;
            }
        });
        btn.addEventListener('mouseleave', () => {
            btn.style.transform = '';
        });
    });
})();

console.log('AWS Brand Site v6 — По ТЗ Яны loaded');

// ─── Reveal on scroll для новых секций главной (compare/reviews/docs/faq) ───
(function initReveal() {
    // На главной (index.html) помечаем заголовки и карточки новых секций
    const autoTargets = [
        '.compare .label', '.compare__title', '.compare__subtitle', '.compare__table-wrap',
        '.reviews .label', '.reviews__title', '.reviews__subtitle',
        '.reviews__marquee',
        '.docs .label', '.docs__title', '.docs__subtitle',
        '.docs .doc-card',
        '.faq .label', '.faq__title',
        '.faq .faq-item'
    ];
    const els = document.querySelectorAll(autoTargets.join(','));
    if (!els.length) return;
    els.forEach((el, i) => {
        el.classList.add('js-reveal');
        // staggered delay для списков карточек
        if (el.matches('.review-card, .doc-card, .faq-item')) {
            el.style.transitionDelay = (i % 8) * 50 + 'ms';
        }
    });
    if (!('IntersectionObserver' in window)) {
        els.forEach(el => el.classList.add('is-visible'));
        return;
    }
    const obs = new IntersectionObserver((entries) => {
        entries.forEach(e => {
            if (e.isIntersecting) {
                e.target.classList.add('is-visible');
                obs.unobserve(e.target);
            }
        });
    }, { threshold: 0.12, rootMargin: '0px 0px -5% 0px' });
    els.forEach(el => obs.observe(el));
})();

// ─── Анимированные счётчики в секции "О бренде" ───
(function initCounters() {
    const counters = document.querySelectorAll('[data-count]');
    if (!counters.length) return;
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            const el = entry.target;
            observer.unobserve(el);
            const target = parseInt(el.dataset.count, 10);
            const suffix = el.dataset.suffix || '';
            const duration = 1400;
            const start = performance.now();
            const step = (now) => {
                const p = Math.min((now - start) / duration, 1);
                const eased = 1 - Math.pow(1 - p, 3);
                const value = Math.floor(target * eased);
                el.textContent = value + (p === 1 ? suffix : '');
                if (p < 1) requestAnimationFrame(step);
            };
            requestAnimationFrame(step);
        });
    }, { threshold: 0.4 });
    counters.forEach(c => observer.observe(c));
})();


// ─── HERO 5 — showcase animation (stagger reveal + cycle items) ───
(function initShowcase() {
    const showcaseSlide = document.querySelector('.hero-slide--showcase');
    if (!showcaseSlide) return;
    const tiles = showcaseSlide.querySelectorAll('.hero-showcase__tile');
    if (!tiles.length) return;

    // Клик по плитке → переход на страницу категории
    tiles.forEach(tile => {
        const link = tile.dataset.catLink;
        if (!link) return;
        tile.addEventListener('click', () => { window.location.href = link; });
    });

    // Tonkij mouse parallax — товары слегка «следят» за курсором
    (function initParallax() {
        let rafId = null;
        showcaseSlide.addEventListener('mousemove', (e) => {
            if (rafId) return;
            rafId = requestAnimationFrame(() => {
                const rect = showcaseSlide.getBoundingClientRect();
                const cx = (e.clientX - rect.left) / rect.width - 0.5;  // -0.5..0.5
                const cy = (e.clientY - rect.top) / rect.height - 0.5;
                tiles.forEach(tile => {
                    const tr = tile.getBoundingClientRect();
                    // расстояние от центра курсора до центра плитки (-1..1)
                    const tdx = ((tr.left + tr.width / 2) - (rect.left + rect.width / 2)) / rect.width;
                    const tdy = ((tr.top + tr.height / 2) - (rect.top + rect.height / 2)) / rect.height;
                    // сдвиг: плитки на краях реагируют сильнее, центральные слабо
                    const px = (cx * 8 + tdx * 4) * -1;
                    const py = (cy * 8 + tdy * 4) * -1;
                    tile.style.setProperty('--parallax-x', px + 'px');
                    tile.style.setProperty('--parallax-y', py + 'px');
                });
                rafId = null;
            });
        }, { passive: true });
        showcaseSlide.addEventListener('mouseleave', () => {
            tiles.forEach(tile => {
                tile.style.setProperty('--parallax-x', '0px');
                tile.style.setProperty('--parallax-y', '0px');
            });
        });
    })();

    let triggered = false;
    let cycleTimers = [];

    // Состояние смены товара для каждой плитки (индекс текущего items[])
    const tileState = Array.from(tiles).map(tile => {
        const img = tile.querySelector('.hero-showcase__img');
        let items = [];
        try { items = JSON.parse(img.dataset.items || '[]'); } catch (e) {}
        let idx = items.indexOf(img.getAttribute('src'));
        if (idx < 0) idx = 0;
        return { img, items, idx };
    });

    // Меняем товар в одной конкретной плитке (с "дыханием")
    function changeOne(tIdx) {
        const st = tileState[tIdx];
        if (!st || !st.items.length || st.items.length < 2) return;
        st.idx = (st.idx + 1) % st.items.length;
        const nextSrc = st.items[st.idx];
        const pre = new Image();
        pre.src = nextSrc;
        pre.onload = () => {
            st.img.classList.add('is-changing');
            setTimeout(() => {
                st.img.src = nextSrc;
                st.img.classList.remove('is-changing');
            }, 600);
        };
    }

    // СИНХРОННАЯ пульсация: все плитки одновременно выдыхают и вдыхают
    function pulseAll() {
        showcaseSlide.classList.add('is-pulsing');
        // Фаза выдоха 700мс: все скрываются синхронно
        cycleTimers.push(setTimeout(() => {
            // Преzagruzim все изображения, затем swap синхронно
            const promises = tileState.map(st => new Promise(resolve => {
                if (!st.items.length || st.items.length < 2) return resolve();
                st.idx = (st.idx + 1) % st.items.length;
                const pre = new Image();
                pre.onload = pre.onerror = resolve;
                pre.src = st.items[st.idx];
            }));
            Promise.all(promises).then(() => {
                tileState.forEach(st => {
                    if (st.items.length >= 2) st.img.src = st.items[st.idx];
                });
                // Фаза вдоха: все возвращаются одновременно
                cycleTimers.push(setTimeout(() => {
                    showcaseSlide.classList.remove('is-pulsing');
                }, 50));
            });
        }, 700));
    }

    function startAnimation() {
        if (triggered) return;
        triggered = true;

        // Фаза 1 (0–0.9с): плитки слева→направо, stagger 110мс
        tiles.forEach((tile, i) => {
            cycleTimers.push(setTimeout(() => tile.classList.add('is-revealed'), 80 + i * 110));
        });

        // Фаза 2 (1.2с): появление центрального текста
        cycleTimers.push(setTimeout(() => {
            showcaseSlide.classList.add('is-active');
        }, 1200));

        // Фаза 3 (3.2с): синхронная пульсация, каждые 3.5с
        cycleTimers.push(setTimeout(function cyclePulse() {
            pulseAll();
            cycleTimers.push(setTimeout(cyclePulse, 3500));
        }, 3200));
    }

    function stopAnimation() {
        cycleTimers.forEach(t => clearTimeout(t));
        cycleTimers = [];
    }

    function resetState() {
        triggered = false;
        stopAnimation();
        showcaseSlide.classList.remove('is-active');
        tiles.forEach(t => t.classList.remove('is-revealed'));
        // Также сбросим is-changing на картинках (если осталось)
        tileState.forEach(st => st.img && st.img.classList.remove('is-changing'));
    }

    if (typeof heroSwiper !== 'undefined') {
        // slideChange — самый РАННИЙ event при смене realIndex.
        // Чистим состояние ДО начала transition, чтобы текст не успел мелькнуть.
        heroSwiper.on('slideChange', resetState);

        // После завершения transition — если активен hero-5, запускаем анимацию заново
        heroSwiper.on('slideChangeTransitionEnd', () => {
            const activeEl = heroSwiper.slides[heroSwiper.activeIndex];
            if (activeEl && activeEl.querySelector('.hero-slide--showcase')) {
                setTimeout(startAnimation, 50);
            }
        });
    }
    // Первый запуск — если слайд уже активен
    if (showcaseSlide.closest('.swiper-slide-active')) {
        setTimeout(startAnimation, 300);
    }
})();

// ─── DOC MODAL — просмотр сертификатов / документов ───
(function initDocModal() {
    const modal = document.getElementById('docModal');
    if (!modal) return;
    const titleEl = document.getElementById('docModalTitle');
    const descEl = document.getElementById('docModalDesc');
    const downloadBtn = document.getElementById('docModalDownload');
    const watermarkEl = document.getElementById('docSheetWatermark');
    let lastFocus = null;

    function open(card) {
        lastFocus = card;
        titleEl.textContent = card.dataset.docTitle || 'Документ';
        descEl.textContent = card.dataset.docDesc || '';
        // watermark = первое слово названия (напр. EAC / ГОСТ / AWS)
        const wmWord = (card.dataset.docTitle || 'AWS').split(' ').slice(-1)[0];
        watermarkEl.textContent = wmWord;
        // Если есть файл — включаем скачивание
        const file = card.dataset.docFile || '';
        if (file) {
            downloadBtn.disabled = false;
            downloadBtn.onclick = () => { window.open(file, '_blank'); };
        } else {
            downloadBtn.disabled = true;
            downloadBtn.onclick = null;
        }
        modal.hidden = false;
        document.body.style.overflow = 'hidden';
    }
    function close() {
        modal.hidden = true;
        document.body.style.overflow = '';
        if (lastFocus && lastFocus.focus) lastFocus.focus();
    }

    document.querySelectorAll('.doc-card[data-doc]').forEach(card => {
        card.addEventListener('click', () => open(card));
    });
    modal.querySelectorAll('[data-close]').forEach(el => el.addEventListener('click', close));
    document.addEventListener('keydown', e => {
        if (modal.hidden) return;
        if (e.key === 'Escape') close();
    });
})();
