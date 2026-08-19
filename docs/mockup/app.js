const PAGE_TITLES = {
  overview: 'Resumen del proyecto',
  flows: 'Flujos del bot',
  operations: 'Operaciones de cambio',
  conversations: 'Conversaciones WhatsApp',
  messages: 'Historial de mensajes',
  queue: 'Cola de envío',
  settings: 'Configuración',
};

function navigateTo(pageId) {
  if (!PAGE_TITLES[pageId]) return;

  document.querySelectorAll('.page').forEach((p) => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach((n) => n.classList.remove('active'));

  document.getElementById(`page-${pageId}`)?.classList.add('active');
  document.querySelector(`.nav-item[data-page="${pageId}"]`)?.classList.add('active');

  document.getElementById('pageTitle').textContent = PAGE_TITLES[pageId];
  document.getElementById('sidebar')?.classList.remove('open');
  window.scrollTo({ top: 0, behavior: 'smooth' });
  history.replaceState(null, '', `#${pageId}`);
}

document.querySelectorAll('.nav-item[data-page]').forEach((btn) => {
  btn.addEventListener('click', () => navigateTo(btn.dataset.page));
});

document.querySelectorAll('[data-goto]').forEach((el) => {
  el.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    navigateTo(el.dataset.goto);
  });
});

document.querySelectorAll('tr.row-clickable[data-goto]').forEach((row) => {
  row.addEventListener('click', () => navigateTo(row.dataset.goto));
});

document.getElementById('menuToggle')?.addEventListener('click', () => {
  document.getElementById('sidebar')?.classList.toggle('open');
});

document.querySelectorAll('.filter-chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    chip.closest('.header-filters')?.querySelectorAll('.filter-chip').forEach((c) => c.classList.remove('active'));
    chip.classList.add('active');
  });
});

document.querySelectorAll('.kanban-card').forEach((card) => {
  card.addEventListener('click', () => {
    document.querySelectorAll('.kanban-card').forEach((c) => c.classList.remove('kanban-card-active'));
    card.classList.add('kanban-card-active');
  });
});

const hash = window.location.hash.replace('#', '');
navigateTo(hash && PAGE_TITLES[hash] ? hash : 'overview');
