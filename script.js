/* ============================
   AWS Brand Site — script.js
   v3: Full dynamics + interactions
   ============================ */

gsap.registerPlugin(ScrollTrigger);

// ─── HERO: Строки появляются ───

gsap.set('.hero-badge', { opacity: 0, y: 20 });
gsap.to('.hero-badge', {
    opacity: 1, y: 0,
    duration: 1, delay: 0.3,
    ease: 'power3.out'
});

document.querySelectorAll('.hero-line').forEach((line, i) => {
    gsap.to(line, {
        opacity: 1, y: 0,
        duration: 1.1,
        delay: 0.6 + i * 0.18,
        ease: 'power3.out'
    });
});

gsap.set('.hero-sub', { opacity: 0, y: 20 });
gsap.to('.hero-sub', {
    opacity: 1, y: 0,
    duration: 0.9, delay: 1.3,
    ease: 'power3.out'
});

gsap.set('.hero-btn', { opacity: 0, y: 20 });
gsap.to('.hero-btn', {
    opacity: 1, y: 0,
    duration: 0.9, delay: 1.5,
    ease: 'power3.out'
});

// ─── HERO: Parallax-рассеивание при скролле ───

gsap.to('.hero-badge', {
    y: -80, opacity: 0,
    ease: 'none',
    scrollTrigger: {
        trigger: '.hero',
        start: 'top top',
        end: '60% top',
        scrub: true
    }
});

gsap.to('.hero-title', {
    y: -120, opacity: 0, scale: 0.95,
    ease: 'none',
    scrollTrigger: {
        trigger: '.hero',
        start: '10% top',
        end: '70% top',
        scrub: true
    }
});

gsap.to('.hero-sub', {
    y: -40, opacity: 0,
    ease: 'none',
    scrollTrigger: {
        trigger: '.hero',
        start: '15% top',
        end: '65% top',
        scrub: true
    }
});

gsap.to('.hero-btn', {
    y: 60, opacity: 0,
    ease: 'none',
    scrollTrigger: {
        trigger: '.hero',
        start: '10% top',
        end: '55% top',
        scrub: true
    }
});

gsap.to('.hero-bg-grid', {
    yPercent: 40, opacity: 0,
    ease: 'none',
    scrollTrigger: {
        trigger: '.hero',
        start: 'top top',
        end: 'bottom top',
        scrub: true
    }
});

gsap.to('.hero-scroll-hint', {
    opacity: 0, y: 20,
    ease: 'none',
    scrollTrigger: {
        trigger: '.hero',
        start: '5% top',
        end: '20% top',
        scrub: true
    }
});

// ─── NAVBAR ───

ScrollTrigger.create({
    trigger: '.hero',
    start: 'top top',
    end: '100px top',
    onLeave: () => document.getElementById('navbar').classList.add('scrolled'),
    onEnterBack: () => document.getElementById('navbar').classList.remove('scrolled')
});

// ─── FADE-UP: Универсальная ───

document.querySelectorAll('.fade-up').forEach(el => {
    const delay = parseFloat(el.dataset.delay) || 0;

    ScrollTrigger.create({
        trigger: el,
        start: 'top 88%',
        once: true,
        onEnter: () => {
            gsap.to(el, {
                opacity: 1, y: 0,
                duration: 0.9,
                delay: delay,
                ease: 'power3.out'
            });
        }
    });
});

// ─── О БРЕНДЕ: Номера считают + золотая линия ───

document.querySelectorAll('.about-number').forEach(el => {
    const text = el.textContent; // "01", "02", "03"
    const target = parseInt(text);

    ScrollTrigger.create({
        trigger: el,
        start: 'top 85%',
        once: true,
        onEnter: () => {
            const obj = { val: 0 };
            gsap.to(obj, {
                val: target,
                duration: 1.5,
                ease: 'power2.out',
                onUpdate: () => {
                    el.textContent = String(Math.round(obj.val)).padStart(2, '0');
                }
            });
        }
    });
});

// Золотая линия под карточками
document.querySelectorAll('.about-card').forEach(card => {
    ScrollTrigger.create({
        trigger: card,
        start: 'top 80%',
        once: true,
        onEnter: () => {
            gsap.to(card, {
                '--line-scale': 1,
                duration: 0.8,
                delay: 0.3,
                ease: 'power2.inOut'
            });
        }
    });
});

// ─── ЦИТАТА: Scale-up из точки ───

gsap.set('.big-quote', {
    scale: 0.4,
    opacity: 0
});

gsap.to('.big-quote', {
    scale: 1,
    opacity: 1,
    ease: 'power2.out',
    scrollTrigger: {
        trigger: '.quote-section',
        start: 'top 80%',
        end: 'top 20%',
        scrub: true
    }
});

gsap.set('.quote-author', { opacity: 0, y: 20 });
ScrollTrigger.create({
    trigger: '.quote-section',
    start: 'top 30%',
    once: true,
    onEnter: () => {
        gsap.to('.quote-author', {
            opacity: 1, y: 0,
            duration: 0.8,
            ease: 'power3.out'
        });
    }
});

// ─── СЕРИИ: Pinned + Glow пульсация ───

document.querySelectorAll('.series-section').forEach(section => {
    const steps = section.querySelectorAll('.series-step');
    const dots = section.querySelectorAll('.series-progress-dot');
    const frame = section.querySelector('.product-card-frame');
    let currentStep = 0;

    if (steps.length <= 1) return;

    // Glow пульсация на фрейме
    if (frame) {
        ScrollTrigger.create({
            trigger: section,
            start: 'top 50%',
            once: true,
            onEnter: () => {
                frame.classList.add('glow-active');
            }
        });
    }

    ScrollTrigger.create({
        trigger: section,
        start: 'top top',
        end: `+=${steps.length * 60}%`,
        pin: section.querySelector('.series-pin-wrapper'),
        scrub: 0.5,
        onUpdate: (self) => {
            const newStep = Math.min(
                Math.floor(self.progress * steps.length),
                steps.length - 1
            );

            if (newStep !== currentStep) {
                steps[currentStep].classList.remove('active');
                dots[currentStep].classList.remove('active');

                currentStep = newStep;

                steps[currentStep].classList.add('active');
                dots[currentStep].classList.add('active');

                // Анимация текста
                gsap.fromTo(steps[currentStep],
                    { opacity: 0, y: 24 },
                    { opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' }
                );

                // Рамка слегка поворачивается
                if (frame) {
                    gsap.to(frame, {
                        rotateY: currentStep * 2 - 2,
                        duration: 0.6,
                        ease: 'power2.out'
                    });
                }
            }
        }
    });
});

// ─── UNO: Ripple-эффект при входе ───

ScrollTrigger.create({
    trigger: '#uno',
    start: 'top 60%',
    once: true,
    onEnter: () => {
        const frame = document.querySelector('#uno .product-card-frame');
        if (frame) {
            const ripple = document.createElement('div');
            ripple.className = 'ripple-effect';
            frame.appendChild(ripple);

            gsap.fromTo(ripple,
                { scale: 0, opacity: 0.6 },
                {
                    scale: 3, opacity: 0,
                    duration: 1.2,
                    ease: 'power2.out',
                    onComplete: () => ripple.remove()
                }
            );
        }
    }
});

// ─── TEXT REVEAL: 3D-вращение слов ───

document.querySelectorAll('.reveal-word').forEach((word, i) => {
    gsap.to(word, {
        opacity: 1,
        y: 0,
        rotateX: 0,
        duration: 1,
        delay: i * 0.15,
        ease: 'power3.out',
        scrollTrigger: {
            trigger: '.text-reveal',
            start: 'top 75%',
            once: true
        }
    });
});

// ─── КАТАЛОГ: Карточки влетают веером ───

const catalogCards = document.querySelectorAll('.catalog-card');
catalogCards.forEach((card, i) => {
    gsap.set(card, {
        opacity: 0,
        x: -100 + (i * 15),
        y: 40,
        rotation: -8 + (i * 2),
        scale: 0.85
    });

    ScrollTrigger.create({
        trigger: '.catalog-track-wrapper',
        start: 'top 80%',
        once: true,
        onEnter: () => {
            gsap.to(card, {
                opacity: 1,
                x: 0,
                y: 0,
                rotation: 0,
                scale: 1,
                duration: 0.8,
                delay: i * 0.08,
                ease: 'back.out(1.2)'
            });
        }
    });
});

// Drag-скролл
const track = document.querySelector('.catalog-track');
let isDown = false;
let startX;
let scrollLeft;

if (track) {
    track.addEventListener('mousedown', (e) => {
        isDown = true;
        track.style.cursor = 'grabbing';
        startX = e.pageX - track.offsetLeft;
        scrollLeft = track.scrollLeft;
    });

    track.addEventListener('mouseleave', () => {
        isDown = false;
        track.style.cursor = 'grab';
    });

    track.addEventListener('mouseup', () => {
        isDown = false;
        track.style.cursor = 'grab';
    });

    track.addEventListener('mousemove', (e) => {
        if (!isDown) return;
        e.preventDefault();
        const x = e.pageX - track.offsetLeft;
        const walk = (x - startX) * 2;
        track.scrollLeft = scrollLeft - walk;
    });
}

// ─── ЦИФРЫ: Counter с bounce ───

document.querySelectorAll('.number-value').forEach(el => {
    const target = parseInt(el.dataset.target);

    ScrollTrigger.create({
        trigger: el,
        start: 'top 88%',
        once: true,
        onEnter: () => {
            const obj = { val: 0 };
            gsap.to(obj, {
                val: target,
                duration: 2,
                ease: 'power2.out',
                onUpdate: () => {
                    el.textContent = Math.round(obj.val).toLocaleString('ru-RU');
                },
                onComplete: () => {
                    // Bounce при достижении
                    gsap.fromTo(el,
                        { scale: 1 },
                        {
                            scale: 1.15,
                            duration: 0.2,
                            ease: 'power2.out',
                            yoyo: true,
                            repeat: 1
                        }
                    );
                    // Золотая вспышка на "+"
                    const plus = el.parentElement.querySelector('.number-plus');
                    if (plus) {
                        gsap.fromTo(plus,
                            { scale: 1, opacity: 0.5 },
                            {
                                scale: 1.5, opacity: 1,
                                duration: 0.3,
                                ease: 'power2.out',
                                yoyo: true,
                                repeat: 1
                            }
                        );
                    }
                }
            });
        }
    });
});

// ─── ГДЕ КУПИТЬ: 3D Flip при входе ───

document.querySelectorAll('.buy-card').forEach((card, i) => {
    gsap.set(card, {
        opacity: 0,
        rotateY: 90,
        transformPerspective: 800
    });

    ScrollTrigger.create({
        trigger: '.buy-grid',
        start: 'top 80%',
        once: true,
        onEnter: () => {
            gsap.to(card, {
                opacity: 1,
                rotateY: 0,
                duration: 0.8,
                delay: i * 0.15,
                ease: 'back.out(1.5)'
            });
        }
    });
});

// ─── PRODUCT CARD: 3D tilt ───

document.querySelectorAll('.product-card-frame').forEach(card => {
    card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        const rotateX = (y - centerY) / 25;
        const rotateY = (centerX - x) / 25;

        gsap.to(card, {
            rotateX: rotateX,
            rotateY: rotateY,
            scale: 1.02,
            duration: 0.4,
            ease: 'power2.out',
            transformPerspective: 800
        });
    });

    card.addEventListener('mouseleave', () => {
        gsap.to(card, {
            rotateX: 0,
            rotateY: 0,
            scale: 1,
            duration: 0.6,
            ease: 'power2.out'
        });
    });
});

// ─── КАТАЛОГ: Hover цветные точки ───

document.querySelectorAll('.catalog-card').forEach(card => {
    card.addEventListener('mouseenter', () => {
        const dots = card.querySelectorAll('.patch-dot');
        dots.forEach((dot, i) => {
            gsap.to(dot, {
                scale: 1.4,
                duration: 0.4,
                delay: i * 0.06,
                ease: 'back.out(3)'
            });
        });
    });

    card.addEventListener('mouseleave', () => {
        const dots = card.querySelectorAll('.patch-dot');
        dots.forEach(dot => {
            gsap.to(dot, { scale: 1, duration: 0.3 });
        });
    });
});

// ─── СЕКЦИИ: Плавное появление ───

gsap.utils.toArray('.about, .catalog, .buy').forEach(section => {
    gsap.fromTo(section,
        { opacity: 0.6 },
        {
            opacity: 1,
            duration: 0.5,
            scrollTrigger: {
                trigger: section,
                start: 'top 90%',
                end: 'top 40%',
                scrub: true
            }
        }
    );
});

console.log('AWS Brand Site v3 — full dynamics loaded');
