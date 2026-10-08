(() => {
  const root = document.querySelector('[data-ic-series]');
  if (!root) return;

  const order = ['uno', 'aura', 'design'];
  const descriptions = {
    uno: 'Тактильная классика — мягкое покрытие, чёткое нажатие',
    aura: 'Строгая классика — чистые линии и выверенные пропорции',
    design: 'Дизайнерская серия для выразительных интерьеров'
  };
  const buttons = [...root.querySelectorAll('[data-ic-series-go]')];
  const product = root.querySelector('.ic-product');
  const productName = root.querySelector('.ic-product-name');
  const description = root.querySelector('.ic-series-desc');
  const colors = root.querySelector('.ic-series-colors');
  const seriesLink = root.querySelector('.ic-series-actions a');
  const scrollScene = root.querySelector('.ic-series-scroll');
  const constructorPreview = root.querySelector('#cstPrevA');
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const shortScene = matchMedia('(max-width: 1000px)');
  let data = null;
  let activeIndex = -1;
  let activeColor = 0;
  let frame = 0;
  let coverToken = 0;
  let handoffComplete = false;
  const handoffProduct = document.createElement('img');
  handoffProduct.className = 'ic-handoff-product';
  handoffProduct.alt = '';
  handoffProduct.setAttribute('aria-hidden', 'true');
  handoffProduct.hidden = true;
  document.body.append(handoffProduct);

  const clamp = value => Math.max(0, Math.min(1, value));

  function showCover(src, label) {
    if (!src || product.getAttribute('src') === src) return;
    const token = ++coverToken;
    const preload = new Image();
    preload.onload = () => {
      if (token !== coverToken) return;
      product.animate([{opacity:.35,transform:'translateY(5px) scale(.985)'},{opacity:1,transform:'none'}], {duration:320,easing:'cubic-bezier(.22,1,.36,1)'});
      product.src = src;
      product.alt = `Выключатель ${label}`;
    };
    preload.src = src;
  }

  function renderColors(series, selected = 0) {
    activeColor = selected;
    colors.replaceChildren();
    const availableColors = series.colors.filter(color => color.cover);
    availableColors.forEach((color, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'ic-series-swatch';
      button.style.setProperty('--ic-swatch', color.swatch);
      button.setAttribute('aria-label', color.label);
      button.setAttribute('aria-pressed', String(index === selected));
      button.addEventListener('click', () => {
        activeColor = index;
        [...colors.children].forEach((item, itemIndex) => item.setAttribute('aria-pressed', String(itemIndex === index)));
        showCover(availableColors[index].cover, `${series.label}, ${availableColors[index].label}`);
      });
      colors.append(button);
    });
  }

  function selectSeries(index) {
    if (!data || index === activeIndex) return;
    activeIndex = index;
    const key = order[index];
    const series = data.series[key];
    buttons.forEach((button, buttonIndex) => button.setAttribute('aria-pressed', String(buttonIndex === index)));
    productName.textContent = series.label;
    description.textContent = descriptions[key];
    seriesLink.href = `https://awsproducts.ru/series/${key}`;
    renderColors(series, 0);
    showCover(series.colors[0].cover, series.label);
  }

  function sceneProgress() {
    if (shortScene.matches || reducedMotion.matches) return 0;
    const start = scrollScene.getBoundingClientRect().top + scrollY;
    const range = Math.max(1, scrollScene.offsetHeight - innerHeight);
    return clamp((scrollY - start) / range);
  }

  function resetHandoff() {
    handoffComplete = false;
    root.classList.remove('is-handoff', 'is-handoff-complete');
    handoffProduct.hidden = true;
  }

  function updateHandoff(progress) {
    if (!constructorPreview) return;
    const handoff = clamp((progress - .82) / .18);

    if (handoff <= 0) {
      resetHandoff();
      return;
    }

    const target = constructorPreview.getBoundingClientRect();
    if (progress < .96) handoffComplete = false;
    if (progress >= .995 && target.top <= innerHeight * .68) handoffComplete = true;

    if (handoffComplete) {
      root.classList.remove('is-handoff');
      root.classList.add('is-handoff-complete');
      handoffProduct.hidden = true;
      return;
    }

    const source = product.getBoundingClientRect();
    const eased = handoff * handoff * (3 - 2 * handoff);
    const lerp = (from, to) => from + (to - from) * eased;
    handoffProduct.src = product.currentSrc || product.src;
    handoffProduct.style.left = `${lerp(source.left, target.left)}px`;
    handoffProduct.style.top = `${lerp(source.top, target.top)}px`;
    handoffProduct.style.width = `${lerp(source.width, target.width)}px`;
    handoffProduct.style.height = `${lerp(source.height, target.height)}px`;
    handoffProduct.hidden = false;
    root.classList.remove('is-handoff-complete');
    root.classList.add('is-handoff');
  }

  function updateScroll() {
    frame = 0;
    if (shortScene.matches || reducedMotion.matches) {
      root.style.setProperty('--ic-product-y', '0px');
      root.style.setProperty('--ic-product-scale', '1');
      root.style.setProperty('--ic-product-opacity', '1');
      resetHandoff();
      return;
    }
    const progress = sceneProgress();
    const index = progress < .3 ? 0 : progress < .6 ? 1 : 2;
    selectSeries(index);
    root.style.setProperty('--ic-product-y', '0px');
    root.style.setProperty('--ic-product-scale', '1');
    root.style.setProperty('--ic-product-opacity', '1');
    updateHandoff(progress);
  }

  function queueScroll() {
    if (!frame) frame = requestAnimationFrame(updateScroll);
  }

  buttons.forEach((button, index) => button.addEventListener('click', () => {
    selectSeries(index);
    if (shortScene.matches || reducedMotion.matches) return;
    const start = scrollScene.getBoundingClientRect().top + scrollY;
    const range = scrollScene.offsetHeight - innerHeight;
    const points = [.12, .44, .7];
    scrollTo({top:start + range * points[index],behavior:'smooth'});
  }));

  fetch('/constructor-data.json')
    .then(response => response.json())
    .then(payload => {
      data = payload;
      selectSeries(shortScene.matches ? 2 : 0);
      updateScroll();
    })
    .catch(() => {});

  addEventListener('scroll', queueScroll, {passive:true});
  addEventListener('resize', queueScroll, {passive:true});
  shortScene.addEventListener('change', () => { if (shortScene.matches) selectSeries(2); queueScroll(); });
  reducedMotion.addEventListener('change', queueScroll);
})();
