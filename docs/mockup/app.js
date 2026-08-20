/* Interactive mock simulator — mirrors Odoo WhatsApp bot flows (mock mode). */

const PAGE_TITLES = {
  overview: 'Resumen del proyecto',
  flows: 'Flujos del bot',
  operations: 'Operaciones de cambio',
  conversations: 'Conversaciones WhatsApp',
  messages: 'Historial de mensajes',
  queue: 'Cola de envío',
  settings: 'Configuración',
};

const OPEN_TEMPLATE =
  'Generaste una operación en nuestra web. Ya estamos trabajando en ella.';
const CLOSE_TEMPLATE =
  'Tu operación ha sido completada. Revisa tu correo para obtener el voucher.';

const state = {
  seq: 2,
  jobSeq: 1050,
  mockMode: true,
  operations: [
    {
      id: 'OP/2026/00001',
      client: 'Test Client',
      initials: 'TC',
      phone: '+51947736930',
      pair: 'BOB → PEN',
      amountFrom: 1000,
      amountTo: 550,
      state: 'done',
      whatsapp: 'complete',
      when: 'Prueba Odoo · 20/08',
      verified: true,
    },
  ],
  messages: [
    {
      time: '04:29',
      client: 'Test Client',
      direction: 'out',
      origin: 'Cierre',
      text: CLOSE_TEMPLATE,
      status: 'sent',
      verified: true,
    },
    {
      time: '04:23',
      client: 'Test Client',
      direction: 'out',
      origin: 'Apertura',
      text: OPEN_TEMPLATE,
      status: 'sent',
      verified: true,
    },
  ],
  queue: [],
  activeChatId: 'OP/2026/00001',
};

function nowTime() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

function initials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('');
}

function formatAmount(n) {
  return Number(n).toLocaleString('es-BO', { maximumFractionDigits: 2 });
}

function toast(msg, type = 'ok') {
  let el = document.getElementById('toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'toast';
    el.className = 'toast';
    document.body.appendChild(el);
  }
  el.className = `toast toast--${type} toast--show`;
  el.textContent = msg;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.remove('toast--show'), 3200);
}

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
  renderAll();
}

function statusLabel(s) {
  return (
    {
      draft: 'Borrador',
      confirmed: 'Confirmada',
      processing: 'En proceso',
      done: 'Concluida',
    }[s] || s
  );
}

function statusClass(s) {
  return (
    {
      draft: 'status-confirmed',
      confirmed: 'status-confirmed',
      processing: 'status-processing',
      done: 'status-done',
    }[s] || 'status-confirmed'
  );
}

function waLabel(w) {
  if (w === 'complete') return 'Completo ✓';
  if (w === 'open') return 'Apertura ✓';
  return 'Pendiente';
}

function enqueue(client, type, onDone) {
  const job = {
    id: `#${state.jobSeq++}`,
    client,
    type,
    status: 'pending',
    retries: 0,
    onDone,
  };
  state.queue.unshift(job);
  renderQueue();
  if (state.mockMode) {
    job.status = 'processing';
    renderQueue();
    setTimeout(() => {
      job.status = 'done';
      if (typeof job.onDone === 'function') job.onDone();
      renderAll();
      toast(`[MOCK] ${type} → Enviado`);
    }, 700);
  }
  return job;
}

function createOperation({ client, phone, pair, amountFrom, amountTo }) {
  const id = `OP/2026/${String(state.seq++).padStart(5, '0')}`;
  const op = {
    id,
    client,
    initials: initials(client),
    phone: phone || '+59170000000',
    pair,
    amountFrom: Number(amountFrom),
    amountTo: Number(amountTo),
    state: 'confirmed',
    whatsapp: 'none',
    when: `Ahora · ${nowTime()}`,
    verified: false,
  };
  state.operations.unshift(op);
  state.activeChatId = id;

  enqueue(client, 'Plantilla apertura', () => {
    op.whatsapp = 'open';
    state.messages.unshift({
      time: nowTime(),
      client,
      direction: 'out',
      origin: 'Apertura',
      text: OPEN_TEMPLATE,
      status: 'sent',
      opId: id,
    });
  });

  toast(`Operación ${id} creada · mensaje de apertura en cola`);
  navigateTo('operations');
  return op;
}

function advanceOperation(opId) {
  const op = state.operations.find((o) => o.id === opId);
  if (!op) return;

  if (op.state === 'confirmed') {
    op.state = 'processing';
    toast(`${opId} → En proceso`);
    renderAll();
    return;
  }

  if (op.state === 'processing') {
    op.state = 'done';
    enqueue(op.client, 'Plantilla cierre', () => {
      op.whatsapp = 'complete';
      state.messages.unshift({
        time: nowTime(),
        client: op.client,
        direction: 'out',
        origin: 'Cierre',
        text: CLOSE_TEMPLATE,
        status: 'sent',
        opId: op.id,
      });
    });
    toast(`${opId} → Concluida · cierre en cola`);
    renderAll();
    return;
  }

  toast('Esta operación ya está concluida', 'info');
}

function simulateClientReply(opId) {
  const op = state.operations.find((o) => o.id === opId);
  if (!op) return;

  const question = '¿Cuándo llega el depósito a la cuenta destino?';
  state.messages.unshift({
    time: nowTime(),
    client: op.client,
    direction: 'in',
    origin: 'Cliente',
    text: question,
    status: 'delivered',
    opId: op.id,
  });
  state.activeChatId = op.id;

  enqueue(op.client, 'Respuesta Claude', () => {
    const reply = `Hola ${op.client.split(' ')[0]}, tu operación ${op.id} por ${formatAmount(op.amountFrom)} ${op.pair.split(' → ')[0]} → ${formatAmount(op.amountTo)} ${op.pair.split(' → ')[1]} está ${op.state === 'done' ? 'concluida' : 'en proceso'}. Te avisamos en cuanto se confirme.`;
    state.messages.unshift({
      time: nowTime(),
      client: op.client,
      direction: 'out',
      origin: 'Claude',
      text: reply,
      status: 'sent',
      opId: op.id,
    });
  });

  toast('Mensaje entrante simulado · Claude responde');
  navigateTo('conversations');
}

function processQueueNow() {
  const pending = state.queue.filter((j) => j.status === 'pending' || j.status === 'processing');
  if (!pending.length) {
    toast('Cola vacía', 'info');
    return;
  }
  pending.forEach((job, i) => {
    job.status = 'processing';
    setTimeout(() => {
      job.status = 'done';
      if (typeof job.onDone === 'function') job.onDone();
      renderAll();
    }, 400 + i * 350);
  });
  toast(`Procesando ${pending.length} job(s)…`);
  renderQueue();
}

function renderOperations() {
  const tbody = document.getElementById('ops-tbody');
  if (!tbody) return;

  const q = (document.getElementById('ops-search')?.value || '').toLowerCase().trim();
  const stateFilter = document.getElementById('ops-state')?.value || '';
  const pairFilter = document.getElementById('ops-pair')?.value || '';

  const rows = state.operations.filter((op) => {
    if (q && !(`${op.id} ${op.client}`.toLowerCase().includes(q))) return false;
    if (stateFilter && op.state !== stateFilter) return false;
    if (pairFilter && op.pair !== pairFilter) return false;
    return true;
  });

  tbody.innerHTML = rows
    .map(
      (op) => `
    <tr class="${op.verified ? 'row-verified' : ''}" data-op="${op.id}">
      <td><strong>${op.id}</strong><br><small>${op.when}</small></td>
      <td><div class="cell-user"><div class="avatar-xs">${op.initials}</div>${op.client}</div></td>
      <td><span class="pair-badge">${op.pair}</span></td>
      <td>${formatAmount(op.amountFrom)} → ${formatAmount(op.amountTo)}</td>
      <td><span class="status ${statusClass(op.state)}">${statusLabel(op.state)}</span></td>
      <td><span class="status status-sent">${waLabel(op.whatsapp)}</span></td>
      <td class="ops-actions">
        ${
          op.state !== 'done'
            ? `<button class="btn btn-sm" data-action="advance" data-op="${op.id}">Avanzar</button>`
            : ''
        }
        <button class="btn btn-sm btn-secondary" data-action="reply" data-op="${op.id}">Simular reply</button>
      </td>
    </tr>`
    )
    .join('');

  tbody.querySelectorAll('[data-action="advance"]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      advanceOperation(btn.dataset.op);
    });
  });
  tbody.querySelectorAll('[data-action="reply"]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      simulateClientReply(btn.dataset.op);
    });
  });
}

function renderMessages() {
  const tbody = document.getElementById('msg-tbody');
  if (!tbody) return;
  tbody.innerHTML = state.messages
    .map((m) => {
      const dir = m.direction === 'in' ? 'dir-in">Entrante' : 'dir-out">Saliente';
      const originClass =
        m.origin === 'Claude'
          ? 'origin-claude'
          : m.origin === 'Cliente'
            ? 'origin-system'
            : 'origin-template';
      const st = m.status === 'delivered' ? 'status-delivered">Entregado' : 'status-sent">Enviado';
      return `<tr class="${m.verified ? 'row-verified' : ''}">
        <td>${m.time}</td>
        <td>${m.client}</td>
        <td><span class="dir ${dir}</span></td>
        <td><span class="origin ${originClass}">${m.origin}</span></td>
        <td class="msg-cell">${m.text}</td>
        <td><span class="status ${st}</span></td>
      </tr>`;
    })
    .join('');
}

function renderQueue() {
  const tbody = document.getElementById('queue-tbody');
  const stats = document.getElementById('queue-stats');
  if (!tbody) return;

  const done = state.queue.filter((j) => j.status === 'done').length;
  const pending = state.queue.filter((j) => j.status === 'pending').length;
  const processing = state.queue.filter((j) => j.status === 'processing').length;

  if (stats) {
    stats.innerHTML = `
      <div class="metric-card"><span>Completados</span><strong>${done}</strong></div>
      <div class="metric-card"><span>Pendientes</span><strong>${pending}</strong></div>
      <div class="metric-card"><span>Procesando</span><strong>${processing}</strong></div>
      <div class="metric-card"><span>Fallidos</span><strong>0</strong></div>`;
  }

  if (!state.queue.length) {
    tbody.innerHTML =
      '<tr><td colspan="5"><em>Sin jobs. Crea una operación para encolar mensajes.</em></td></tr>';
    return;
  }

  tbody.innerHTML = state.queue
    .map((j) => {
      const cls =
        j.status === 'done'
          ? 'status-done">Completado'
          : j.status === 'processing'
            ? 'status-processing">Procesando'
            : 'status-confirmed">Pendiente';
      return `<tr>
        <td><strong>${j.id}</strong></td>
        <td>${j.client}</td>
        <td>${j.type}</td>
        <td><span class="status ${cls}</span></td>
        <td>${j.retries}</td>
      </tr>`;
    })
    .join('');
}

function renderConversations() {
  const board = document.getElementById('kanban-board');
  const chat = document.getElementById('chat-preview');
  if (!board || !chat) return;

  const columns = {
    new: [],
    progress: [],
    waiting: [],
    done: [],
  };

  state.operations.forEach((op) => {
    const hasIn = state.messages.some((m) => m.opId === op.id && m.direction === 'in');
    const last = state.messages.find((m) => m.client === op.client);
    const preview = last?.text || OPEN_TEMPLATE;
    const card = { op, preview, hasIn };
    if (op.state === 'done' && op.whatsapp === 'complete' && !hasIn) columns.done.push(card);
    else if (hasIn && op.state !== 'done') columns.progress.push(card);
    else if (hasIn) columns.waiting.push(card);
    else columns.new.push(card);
  });

  const colHtml = (title, key, items) => `
    <div class="kanban-col">
      <div class="kanban-head"><span>${title}</span><span class="count">${items.length}</span></div>
      ${items
        .map(
          ({ op, preview }) => `
        <article class="kanban-card ${state.activeChatId === op.id ? 'kanban-card-active' : ''}" data-chat="${op.id}">
          <div class="kanban-card-top">
            <div class="avatar-xs">${op.initials}</div>
            <div><strong>${op.client}</strong><small>${op.id}</small></div>
          </div>
          <p>${preview.slice(0, 90)}${preview.length > 90 ? '…' : ''}</p>
          <div class="kanban-tags"><span class="tag">${op.pair.replace(/\s/g, '')}</span></div>
        </article>`
        )
        .join('') || '<p class="kanban-empty">Vacío</p>'}
    </div>`;

  board.innerHTML =
    colHtml('Nuevos contactos', 'new', columns.new) +
    colHtml('Chats en progreso', 'progress', columns.progress) +
    colHtml('Pendiente respuesta', 'waiting', columns.waiting) +
    colHtml('Finalizados', 'done', columns.done);

  board.querySelectorAll('[data-chat]').forEach((card) => {
    card.addEventListener('click', () => {
      state.activeChatId = card.dataset.chat;
      renderConversations();
    });
  });

  const op = state.operations.find((o) => o.id === state.activeChatId) || state.operations[0];
  if (!op) {
    chat.innerHTML = '<p>Sin conversaciones.</p>';
    return;
  }

  const bubbles = state.messages
    .filter((m) => m.client === op.client)
    .slice()
    .reverse()
    .map((m) => {
      const cls =
        m.direction === 'in' ? 'in' : m.origin === 'Claude' ? 'out bubble-ai' : 'out';
      const who = m.direction === 'in' ? 'Cliente' : m.origin;
      return `<div class="bubble ${cls}">${m.text}<time>${m.time} · ${who}</time></div>`;
    })
    .join('');

  chat.innerHTML = `
    <div class="chat-preview-head">
      <div class="cell-user">
        <div class="avatar-xs">${op.initials}</div>
        <div><strong>${op.client}</strong><small>${op.phone} · ${op.id}</small></div>
      </div>
      <div class="chat-actions">
        <button class="btn btn-sm btn-secondary" id="btn-sim-reply">Simular mensaje cliente</button>
        ${
          op.state !== 'done'
            ? `<button class="btn btn-sm" id="btn-advance-chat">Avanzar estado</button>`
            : ''
        }
      </div>
    </div>
    <div class="chat-window">${bubbles || '<em>Sin mensajes aún.</em>'}</div>`;

  document.getElementById('btn-sim-reply')?.addEventListener('click', () =>
    simulateClientReply(op.id)
  );
  document.getElementById('btn-advance-chat')?.addEventListener('click', () =>
    advanceOperation(op.id)
  );
}

function renderAll() {
  renderOperations();
  renderMessages();
  renderQueue();
  renderConversations();
  const pill = document.getElementById('mock-pill');
  if (pill) pill.textContent = state.mockMode ? 'Modo mock ON' : 'Modo mock OFF';
}

function openModal() {
  document.getElementById('op-modal')?.classList.add('open');
  document.getElementById('f-client')?.focus();
}

function closeModal() {
  document.getElementById('op-modal')?.classList.remove('open');
}

function bindUi() {
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

  document.getElementById('menuToggle')?.addEventListener('click', () => {
    document.getElementById('sidebar')?.classList.toggle('open');
  });

  document.getElementById('btn-new-op')?.addEventListener('click', openModal);
  document.getElementById('btn-try-demo')?.addEventListener('click', openModal);
  document.getElementById('modal-close')?.addEventListener('click', closeModal);
  document.getElementById('modal-cancel')?.addEventListener('click', closeModal);
  document.getElementById('op-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'op-modal') closeModal();
  });

  document.getElementById('op-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const client = document.getElementById('f-client').value.trim();
    const phone = document.getElementById('f-phone').value.trim();
    const pair = document.getElementById('f-pair').value;
    const amountFrom = document.getElementById('f-from').value;
    const amountTo = document.getElementById('f-to').value;
    if (!client || !amountFrom || !amountTo) {
      toast('Completa cliente y montos', 'info');
      return;
    }
    createOperation({ client, phone, pair, amountFrom, amountTo });
    closeModal();
    e.target.reset();
  });

  document.getElementById('btn-process-queue')?.addEventListener('click', processQueueNow);

  ['ops-search', 'ops-state', 'ops-pair'].forEach((id) => {
    document.getElementById(id)?.addEventListener('input', renderOperations);
    document.getElementById(id)?.addEventListener('change', renderOperations);
  });

  document.getElementById('mock-toggle')?.addEventListener('click', () => {
    state.mockMode = !state.mockMode;
    document.getElementById('mock-toggle')?.classList.toggle('on', state.mockMode);
    renderAll();
    toast(state.mockMode ? 'Modo mock activado' : 'Modo mock desactivado (cola manual)');
  });
}

const hash = window.location.hash.replace('#', '');
bindUi();
navigateTo(hash && PAGE_TITLES[hash] ? hash : 'overview');
