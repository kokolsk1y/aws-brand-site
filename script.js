/* ============================
   AWS Brand Site — script.js
   v5: Werkel-inspired
   Lenis + Swiper + GSAP ScrollTrigger
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
sideMenu.querySelectorAll('.side-menu__item').forEach(link => {
    link.addEventListener('click', closeMenu);
});

// ─── HERO SWIPER ───

const heroSwiper = new Swiper('.hero-swiper', {
    effect: 'fade',
    fadeEffect: { crossFade: true },
    speed: 1000,
    autoplay: {
        delay: 5000,
        disableOnInteraction: false
    },
    loop: true,
    pagination: {
        el: '.hero-pagination',
        clickable: true
    }
});

// Смена темы хедера по слайду
const header = document.getElementById('header');

function updateHeaderTheme() {
    const activeSlide = document.querySelector('.swiper-slide-active .hero-slide');
    if (!activeSlide) return;
    const theme = activeSlide.dataset.theme || 'dark';
    header.classList.remove('dark', 'light');
    header.classList.add(theme);
}

updateHeaderTheme();
heroSwiper.on('slideChange', updateHeaderTheme);

// Анимация контента слайда
heroSwiper.on('slideChangeTransitionStart', () => {
    const activeContent = document.querySelector('.swiper-slide-active .hero-slide__content');
    if (!activeContent) return;

    gsap.fromTo(activeContent.querySelector('.hero-slide__label'),
        { opacity: 0, y: 20 },
        { opacity: 0.6, y: 0, duration: 0.8, delay: 0.3, ease: 'power3.out' }
    );
    gsap.fromTo(activeContent.querySelector('.hero-slide__title'),
        { opacity: 0, y: 40 },
        { opacity: 1, y: 0, duration: 1, delay: 0.4, ease: 'power3.out' }
    );
    gsap.fromTo(activeContent.querySelector('.hero-slide__btn'),
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.8, delay: 0.7, ease: 'power3.out' }
    );
});

// Начальная анимация первого слайда
gsap.fromTo('.swiper-slide-active .hero-slide__label',
    { opacity: 0, y: 20 },
    { opacity: 0.6, y: 0, duration: 0.8, delay: 0.5, ease: 'power3.out' }
);
gsap.fromTo('.swiper-slide-active .hero-slide__title',
    { opacity: 0, y: 40 },
    { opacity: 1, y: 0, duration: 1, delay: 0.6, ease: 'power3.out' }
);
gsap.fromTo('.swiper-slide-active .hero-slide__btn',
    { opacity: 0, y: 20 },
    { opacity: 1, y: 0, duration: 0.8, delay: 0.9, ease: 'power3.out' }
);

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

// ─── HIGHLIGHTS: Горизонтальный скролл с parallax ───

const highlightsSection = document.querySelector('.highlights');
const highlightsContainer = document.querySelector('.highlights__container');

if (highlightsSection && highlightsContainer) {
    const totalScroll = highlightsContainer.scrollWidth - window.innerWidth;

    gsap.to(highlightsContainer, {
        x: () => -totalScroll,
        ease: 'none',
        scrollTrigger: {
            trigger: highlightsSection,
            start: 'center center',
            end: () => '+=' + totalScroll,
            pin: '.highlights__pin',
            scrub: true,
            invalidateOnRefresh: true
        }
    });
}

// ─── CATEGORIES: Появление карточек ───

document.querySelectorAll('.categories__item').forEach((item, i) => {
    gsap.from(item, {
        opacity: 0,
        y: 40,
        duration: 0.8,
        delay: (i % 2) * 0.15,
        ease: 'power3.out',
        scrollTrigger: {
            trigger: item,
            start: 'top 85%',
            once: true
        }
    });
});

// ─── ABOUT BRAND: Появление текста ───

const aboutSection = document.querySelector('.about-brand');
if (aboutSection) {
    gsap.from('.about-brand__label', {
        opacity: 0, y: 30,
        duration: 0.8,
        ease: 'power3.out',
        scrollTrigger: { trigger: aboutSection, start: 'top 70%', once: true }
    });

    gsap.from('.about-brand__title', {
        opacity: 0, y: 40,
        duration: 1,
        delay: 0.15,
        ease: 'power3.out',
        scrollTrigger: { trigger: aboutSection, start: 'top 70%', once: true }
    });

    gsap.from('.about-brand__desc', {
        opacity: 0, y: 30,
        duration: 0.8,
        delay: 0.3,
        ease: 'power3.out',
        scrollTrigger: { trigger: aboutSection, start: 'top 70%', once: true }
    });

    gsap.from('.about-brand__link', {
        opacity: 0, y: 20,
        duration: 0.6,
        delay: 0.45,
        ease: 'power3.out',
        scrollTrigger: { trigger: aboutSection, start: 'top 70%', once: true }
    });

    gsap.from('.about-brand__image', {
        opacity: 0, y: 60,
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
    const content = document.querySelector('.swiper-slide-active .advantages__slide-content');
    if (!content) return;

    gsap.fromTo(content.querySelector('.advantages__num'),
        { opacity: 0, x: -20 },
        { opacity: 1, x: 0, duration: 0.6, delay: 0.2, ease: 'power3.out' }
    );
    gsap.fromTo(content.querySelector('.advantages__heading'),
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.8, delay: 0.3, ease: 'power3.out' }
    );
    gsap.fromTo(content.querySelector('.advantages__text'),
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.8, delay: 0.45, ease: 'power3.out' }
    );
});

// ─── WHERE BUY: Появление карточек ───

document.querySelectorAll('.where-buy__card').forEach((card, i) => {
    gsap.from(card, {
        opacity: 0,
        y: 40,
        duration: 0.8,
        delay: i * 0.12,
        ease: 'power3.out',
        scrollTrigger: {
            trigger: '.where-buy__grid',
            start: 'top 80%',
            once: true
        }
    });
});

// ─── WHERE BUY TITLE ───

gsap.from('.where-buy__title', {
    opacity: 0, y: 40,
    duration: 1,
    ease: 'power3.out',
    scrollTrigger: {
        trigger: '.where-buy',
        start: 'top 75%',
        once: true
    }
});

// ─── FOOTER: мягкое появление ───

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

console.log('AWS Brand Site v5 — Werkel-inspired loaded');
