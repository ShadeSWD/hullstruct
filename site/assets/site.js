/* Каркас страниц «Конструкция корпуса судов»: шапка с группированной
   навигацией, подвал, общие SVG-маркеры стрелок. */
'use strict';
(function () {
  const me = document.currentScript;
  const root = (me && me.dataset.root) || './';
  const page = (me && me.dataset.page) || '';
  const logoSvg = `
  <svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true">
    <rect x="1" y="1" width="28" height="28" rx="6" fill="#1f4e5f"/>
    <text x="15" y="22" text-anchor="middle" font-size="16">🚧</text>
  </svg>`;
  const nav = [
    { h: '', k: 'index', t: 'Обзор' },
    { t: 'Теория', h: 'theory', drop: [
      { h: 'theory', k: 'theory', t: 'Оглавление курса' },
      { h: 't-systems', k: 'theory', t: '1. Системы набора и шпация' },
      { h: 't-bottom', k: 'theory', t: '2. Днищевые перекрытия' },
      { h: 't-side', k: 'theory', t: '3. Бортовые перекрытия' },
      { h: 't-deck', k: 'theory', t: '4. Палубные перекрытия' },
      { h: 't-bulkheads', k: 'theory', t: '5. Переборки' },
      { h: 't-ends', k: 'theory', t: '6. Оконечности' },
      { h: 't-superstructure', k: 'theory', t: '7. Надстройки и рубки' },
      { h: 't-nodes', k: 'theory', t: '8. Типовые узлы и их работа' },
      { h: 't-rules', k: 'theory', t: '9. Нормирование по Правилам РМРС' },
    ] },
    { t: 'Задачи', h: 'tasks', drop: [
      { h: 'tasks', k: 'tasks', t: 'Оглавление разборов' },
      { h: 'p-spacing', k: 'tasks', t: '1. Шпация и система набора' },
      { h: 'p-plating', k: 'tasks', t: '2. Толщина наружной обшивки' },
      { h: 'p-deckplate', k: 'tasks', t: '3. Настил палубы и второго дна' },
      { h: 'p-stiffener', k: 'tasks', t: '4. Подбор профиля рёбер (живой расчёт)' },
      { h: 'p-frame', k: 'tasks', t: '5. Шпангоут и рамная связь' },
      { h: 'p-bracket', k: 'tasks', t: '6. Бракета и кница' },
      { h: 'p-opening', k: 'tasks', t: '7. Подкрепление выреза' },
      { h: 'p-node', k: 'tasks', t: '8. Узел «флор — шпангоут»' },
      { h: 'p-corrugated', k: 'tasks', t: '9. Гофрированная переборка' },
    ] },
    { h: 'sources', k: 'sources', t: 'Источники' },
  ];
  const navLink = (it) =>
    `<a href="${root}${it.h}" class="${page === it.k ? 'on' : ''}">${it.t}</a>`;
  const navHtml = nav.map((g) => {
    if (!g.drop) return navLink(g);
    const on = g.drop.some((it) => page === it.k) ? 'on' : '';
    return `<span class="nav-drop"><a href="${root}${g.h}" class="${on}">${g.t} ▾</a>`
      + `<span class="drop">${g.drop.map(navLink).join('')}</span></span>`;
  }).join('');
  const header = document.createElement('header');
  header.className = 'site';
  header.innerHTML = `<div class="wrap">
    <a class="logo" href="${root}">${logoSvg}<span>Конструкция корпуса судов</span></a>
    <nav class="top">${navHtml}</nav>
  </div>`;
  document.body.prepend(header);
  const onReady = (fn) => (document.readyState === 'loading'
    ? document.addEventListener('DOMContentLoaded', fn) : fn());
  const footer = document.createElement('footer');
  footer.className = 'site';
  footer.innerHTML = `<div class="wrap">
    <div>Учебный сайт по курсу «Конструкция корпуса судов» ·
      кафедра конструкции и технической эксплуатации судов СПбГМТУ ·
      размеры связей — по Правилам РМРС, часть II «Корпус»</div>
  </div>`;
  onReady(() => document.body.appendChild(footer));
  const defs = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  defs.setAttribute('width', '0'); defs.setAttribute('height', '0');
  defs.style.position = 'absolute';
  defs.innerHTML = `<defs>
    <marker id="arrE" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">
      <path d="M0,0 L10,4 L0,8 z" fill="#16161a"/></marker>
    <marker id="arrS" markerWidth="10" markerHeight="8" refX="1" refY="4" orient="auto">
      <path d="M10,0 L0,4 L10,8 z" fill="#16161a"/></marker>
    <marker id="arrR" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">
      <path d="M0,0 L10,4 L0,8 z" fill="#b3382e"/></marker>
  </defs>`;
  onReady(() => document.body.appendChild(defs));
})();
