/* ============================
   AWS Brand Site — script.js
   GSAP ScrollTrigger animations
   ============================ */

gsap.registerPlugin(ScrollTrigger);

// ─── HERO: Анимация появления строк ───

gsap.to('.hero-badge', {
    opacity: 1,
    y: 0,
    duration: 0.8,
    delay: 0.3,
    ease: 'power3.out',
    onStart: function() {
        gsap.set('.hero-badge', { opacity: 0, y: 20 });
    }
});

gsap.set('.hero-badge', { opacity: 0, y: 20 });

document.querySelectorAll('.hero-line').forEach((line, i) => {
    gsap.to(line, {
        opacity: 1,
        y: 0,
        duration: 0.9,
        delay: 0.5 + i * 0.15,
        ease: 'power3.out'
    });
});

gsap.set('.hero-sub', { opacity: 0, y: 20 });
gsap.to('.hero-sub', {
    opacity: 1, y: 0,
    duration: 0.8, delay: 1.1,
    ease: 'power3.out'
});

gsap.set('.hero-btn', { opacity: 0, y: 20 });
gsap.to('.hero-btn', {
    opacity: 1, y: 0,
    duration: 0.8, delay: 1.3,
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

// ─── FADE-UP: Универсальная анимация появления ───

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
                duration: 0.8,
                delay: delay,
                ease: 'power3.out'
            });
        }
    });
});

// ─── СЕРИИ: Автоматическая смена шагов при скролле ───

document.querySelectorAll('.series-section').forEach(section => {
    const steps = section.querySelectorAll('.series-step');
    const dots = section.querySelectorAll('.series-progress-dot');
    let currentStep = 0;

    if (steps.length <= 1) return;

    // Pinned эффект
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
                    { opacity: 0, y: 20 },
                    { opacity: 1, y: 0, duration: 0.4 }
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

// ─── ЦИФРЫ: Counter анимация ───

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
                duration: 2,
                ease: 'power2.out',
                onUpdate: () => {
                    el.textContent = Math.round(obj.val).toLocaleString('ru-RU');
                }
            });
        }
    });
});

// ─── SMOOTH: Плавное появление секций при смене dark/light ───

document.querySelectorAll('.about, .catalog, .buy').forEach(section => {
    gsap.fromTo(section,
        { opacity: 0.8 },
        {
            opacity: 1,
            duration: 0.5,
            scrollTrigger: {
                trigger: section,
                start: 'top 80%',
                end: 'top 20%',
                scrub: true
            }
        }
    );
});

// ─── PRODUCT CARD: Лёгкий 3D tilt при наведении ───

document.querySelectorAll('.product-card-frame').forEach(card => {
    card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        const rotateX = (y - centerY) / 20;
        const rotateY = (centerX - x) / 20;

        card.style.transform = `perspective(600px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
    });

    card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(600px) rotateX(0) rotateY(0) scale(1)';
    });
});

// ─── КАТАЛОГ КАРТОЧКИ: hover-анимация цветных точек ───

document.querySelectorAll('.catalog-card').forEach(card => {
    card.addEventListener('mouseenter', () => {
        const dots = card.querySelectorAll('.patch-dot');
        dots.forEach((dot, i) => {
            gsap.to(dot, {
                scale: 1.3,
                duration: 0.3,
                delay: i * 0.05,
                ease: 'back.out(2)'
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

console.log('AWS Brand Site loaded');
