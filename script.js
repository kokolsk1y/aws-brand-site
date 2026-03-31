/* ============================
   AWS Brand Site — script.js
   GSAP ScrollTrigger animations
   ============================ */

gsap.registerPlugin(ScrollTrigger);

// ─── HERO: Строки появляются одна за другой ───

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

// ─── NAVBAR: Сжимается при скролле ───

ScrollTrigger.create({
    trigger: '.hero',
    start: 'top top',
    end: '100px top',
    onLeave: () => document.getElementById('navbar').classList.add('scrolled'),
    onEnterBack: () => document.getElementById('navbar').classList.remove('scrolled')
});

// ─── FADE-UP: Универсальная анимация ───

document.querySelectorAll('.fade-up').forEach(el => {
    const delay = parseFloat(el.dataset.delay) || 0;

    ScrollTrigger.create({
        trigger: el,
        start: 'top 85%',
        once: true,
        onEnter: () => {
            gsap.to(el, {
                opacity: 1,
                y: 0,
                duration: 0.9,
                delay: delay,
                ease: 'power3.out'
            });
        }
    });
});

// ─── БОЛЬШАЯ ЦИТАТА: Строки появляются с parallax ───

document.querySelectorAll('.quote-line').forEach((line, i) => {
    gsap.to(line, {
        opacity: 1,
        y: 0,
        duration: 1,
        ease: 'power3.out',
        scrollTrigger: {
            trigger: '.quote-section',
            start: `top ${75 - i * 8}%`,
            once: true
        }
    });
});

// ─── TEXT REVEAL: Слова появляются с 3D-вращением ───

document.querySelectorAll('.reveal-word').forEach((word, i) => {
    gsap.to(word, {
        opacity: 1,
        y: 0,
        rotateX: 0,
        duration: 1,
        delay: i * 0.12,
        ease: 'power3.out',
        scrollTrigger: {
            trigger: '.text-reveal',
            start: 'top 75%',
            once: true
        }
    });
});

// ─── СЕРИИ: Pinned с переключением шагов ───

document.querySelectorAll('.series-section').forEach(section => {
    const steps = section.querySelectorAll('.series-step');
    const dots = section.querySelectorAll('.series-progress-dot');
    let currentStep = 0;

    if (steps.length <= 1) return;

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

                gsap.fromTo(steps[currentStep],
                    { opacity: 0, y: 24 },
                    { opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' }
                );
            }
        }
    });
});

// ─── КАТАЛОГ: Drag-скролл ───

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

// ─── ЦИФРЫ: Counter ───

document.querySelectorAll('.number-value').forEach(el => {
    const target = parseInt(el.dataset.target);

    ScrollTrigger.create({
        trigger: el,
        start: 'top 85%',
        once: true,
        onEnter: () => {
            const obj = { val: 0 };
            gsap.to(obj, {
                val: target,
                duration: 2.2,
                ease: 'power2.out',
                onUpdate: () => {
                    el.textContent = Math.round(obj.val).toLocaleString('ru-RU');
                }
            });
        }
    });
});

// ─── PARALLAX: Секции с лёгким движением ───

gsap.utils.toArray('.about, .catalog, .buy').forEach(section => {
    gsap.fromTo(section,
        { opacity: 0.7 },
        {
            opacity: 1,
            duration: 0.6,
            scrollTrigger: {
                trigger: section,
                start: 'top 85%',
                end: 'top 30%',
                scrub: true
            }
        }
    );
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

        card.style.transform = `perspective(800px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
    });

    card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(800px) rotateX(0) rotateY(0) scale(1)';
    });
});

// ─── КАТАЛОГ: Hover-анимация цветных точек ───

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

// ─── PARALLAX: Сетка hero двигается при скролле ───

gsap.to('.hero-bg-grid', {
    yPercent: 30,
    ease: 'none',
    scrollTrigger: {
        trigger: '.hero',
        start: 'top top',
        end: 'bottom top',
        scrub: true
    }
});

console.log('AWS Brand Site v2 loaded');
