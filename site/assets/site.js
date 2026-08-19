/* Данные каркаса страниц. Машинерия — assets/shell.js. */
'use strict';
(function () {
  const me = document.currentScript;
  const root = (me && me.dataset.root) || './';
  buildSiteShell({
    root,
    page: (me && me.dataset.page) || '',
    brand: 'Конструкция корпуса судов',
    logo: `
  <svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true">
    <rect x="1" y="1" width="28" height="28" rx="6" fill="#1f4e5f"/>
    <text x="15" y="22" text-anchor="middle" font-size="16">🚧</text>
  </svg>`,
    nav: [
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
    ],
    footer: `<div>Учебный сайт по курсу «Конструкция корпуса судов» ·
      кафедра конструкции и технической эксплуатации судов СПбГМТУ ·
      размеры связей — по Правилам РМРС, часть II «Корпус»</div>`,
    markers: `<marker id="arrE" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">
      <path d="M0,0 L10,4 L0,8 z" fill="#16161a"/></marker>
    <marker id="arrS" markerWidth="10" markerHeight="8" refX="1" refY="4" orient="auto">
      <path d="M10,0 L0,4 L10,8 z" fill="#16161a"/></marker>
    <marker id="arrR" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">
      <path d="M0,0 L10,4 L0,8 z" fill="#b3382e"/></marker>`,
  });
})();
