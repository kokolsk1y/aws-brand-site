/* ============================
   AWS Brand Site — script.js
   v6: По ТЗ Яны
   Lenis + Swiper + GSAP
   ============================ */

gsap.registerPlugin(ScrollTrigger);

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

// ─── SIDE MENU ───

const menuToggle = document.getElementById('menuToggle');
const menuClose = document.getElementById('menuClose');
const menuOverlay = document.getElementById('menuOverlay');
const sideMenu = document.getElementById('sideMenu');

function openMenu() {
    sideMenu.classList.add('open');
    lenis.stop();
}

function closeMenu() {
    sideMenu.classList.remove('open');
    lenis.start();
}

menuToggle.addEventListener('click', openMenu);
menuClose.addEventListener('click', closeMenu);
menuOverlay.addEventListener('click', closeMenu);

// Закрытие при клике на ссылку
sideMenu.querySelectorAll('.side-menu__item, .side-menu__sub').forEach(link => {
    link.addEventListener('click', closeMenu);
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

function updateHeaderTheme() {
    const activeSlide = document.querySelector('.swiper-slide-active .hero-slide');
    if (!activeSlide) return;
    const theme = activeSlide.dataset.theme || 'dark';
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

// Перезапуск видео при смене слайда
heroSwiper.on('slideChangeTransitionStart', () => {
    const activeSlide = document.querySelector('.swiper-slide-active .hero-slide__video');
    if (activeSlide) {
        activeSlide.currentTime = 0;
        activeSlide.play();
    }
});

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

// ─── CONSTRUCTOR: Chip toggle ───

document.querySelectorAll('.constructor__option').forEach(option => {
    const chips = option.querySelectorAll('.constructor__chip');
    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            chips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
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

// ─── PARALLAX: лёгкий эффект на секциях ───

document.querySelectorAll('.series__card-visual, .categories__card-img, .about__image').forEach(el => {
    gsap.to(el, {
        yPercent: -5,
        ease: 'none',
        scrollTrigger: {
            trigger: el,
            start: 'top bottom',
            end: 'bottom top',
            scrub: true
        }
    });
});

console.log('AWS Brand Site v6 — По ТЗ Яны loaded');
