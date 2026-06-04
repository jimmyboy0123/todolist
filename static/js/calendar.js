(function () {
  'use strict';

  const state = {
    scope: 'my',
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    selectedDate: fmt(new Date()),
    monthItems: [],
    activeTab: 'today',
    todayItems: [],
    overdueItems: [],
    modalItemId: null,
    uploadTargetId: null,
  };

  function fmt(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  function monthStr() {
    return `${state.year}-${String(state.month).padStart(2, '0')}`;
  }

  function bindEvents() {
    document.querySelectorAll('.tc-scope-btn').forEach(btn => {
      btn.onclick = () => {
        document.querySelectorAll('.tc-scope-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.scope = btn.dataset.scope;
        loadMonth(); loadDay(); loadRegular();
      };
    });

    document.getElementById('prev-month').onclick = () => { changeMonth(-1); };
    document.getElementById('next-month').onclick = () => { changeMonth(1); };
    document.getElementById('today-btn').onclick = () => {
      const now = new Date();
      state.year = now.getFullYear();
      state.month = now.getMonth() + 1;
      state.selectedDate = fmt(now);
      loadMonth(); loadDay();
    };

    document.querySelectorAll('.tc-tab-btn').forEach(btn => {
      btn.onclick = () => {
        document.querySelectorAll('.tc-tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.activeTab = btn.dataset.tab;
        renderEvents();
      };
    });

    document.getElementById('search-btn').onclick = () => {
      document.getElementById('search-modal').classList.add('open');
      document.getElementById('search-input').focus();
    };
    document.getElementById('search-close').onclick = () => document.getElementById('search-modal').classList.remove('open');

    let st;
    document.getElementById('search-input').oninput = () => {
      clearTimeout(st);
      st = setTimeout(doSearch, 300);
    };

    const closeEventModal = () => document.getElementById('event-modal').classList.remove('open');
    document.getElementById('event-modal-close').onclick = closeEventModal;
    document.getElementById('event-modal-ok').onclick = closeEventModal;
    document.getElementById('event-modal').onclick = e => {
      if (e.target.id === 'event-modal') closeEventModal();
    };

    document.getElementById('tc-attachment-input').onchange = async e => {
      const itemId = state.uploadTargetId;
      const files = [...(e.target.files || [])];
      e.target.value = '';
      state.uploadTargetId = null;
      if (!itemId || !files.length) return;
      await TodoApp.uploadAttachmentFiles(itemId, files);
      const attachments = await refreshItemAttachmentCount(itemId);
      if (state.modalItemId === itemId) {
        const el = document.getElementById('event-modal-attachments');
        if (el) {
          el.innerHTML = renderAttachmentListHtml(attachments, true, itemId);
          bindModalAttachmentDeletes(itemId);
        }
      }
    };
  }

  async function refreshItemAttachmentCount(itemId) {
    const attachments = await TodoApp.fetchAttachments(itemId);
    setAttachmentCount(itemId, attachments.length);
    return attachments;
  }

  function setAttachmentCount(itemId, count) {
    const set = list => {
      list.forEach(it => {
        if (+it.id === itemId) it.attachment_count = count;
      });
    };
    set(state.todayItems);
    set(state.overdueItems);
    renderEvents();
  }

  function pickAttachments(itemId) {
    state.uploadTargetId = itemId;
    document.getElementById('tc-attachment-input').click();
  }

  function attachmentBadge(count) {
    const n = count || 0;
    return n ? `<span class="tc-att-badge">📎 ${n}</span>` : '';
  }

  function renderAttachmentListHtml(attachments, editable, itemId) {
    if (!attachments?.length) {
      return '<span style="color:var(--text-muted);font-size:13px;">暂无附件</span>';
    }
    return `<ul class="attachment-list">${attachments.map(a => `
      <li class="attachment-item" data-att-id="${a.id}">
        <div class="attachment-item-name">
          <a href="${a.url}" target="_blank" rel="noopener" download>${TodoApp.esc(a.original_filename)}</a>
          <div class="attachment-item-meta">${TodoApp.formatFileSize(a.size_bytes)}</div>
        </div>
        ${editable ? '<div class="attachment-item-actions"><button type="button" class="btn btn-sm btn-danger tc-att-del">删除</button></div>' : ''}
      </li>
    `).join('')}</ul>`;
  }

  function bindModalAttachmentDeletes(itemId) {
    const el = document.getElementById('event-modal-attachments');
    if (!el) return;
    el.querySelectorAll('.tc-att-del').forEach(btn => {
      btn.onclick = async e => {
        const attId = +e.target.closest('.attachment-item').dataset.attId;
        if (!confirm('确定删除该附件？')) return;
        const res = await TodoApp.deleteAttachment(attId);
        if (res.ok) await renderModalAttachments(itemId);
        else alert(res.msg || '删除失败');
      };
    });
  }

  async function renderModalAttachments(itemId) {
    const attachments = await refreshItemAttachmentCount(itemId);
    const el = document.getElementById('event-modal-attachments');
    if (!el) return;
    el.innerHTML = renderAttachmentListHtml(attachments, true, itemId);
    bindModalAttachmentDeletes(itemId);
  }

  async function openEventModal(itemId) {
    state.modalItemId = itemId;
    const res = await TodoApp.api('/api/items/' + itemId);
    if (!res.ok) {
      alert(res.msg || '加载失败');
      return;
    }
    const it = res.item;
    document.getElementById('event-modal-title').textContent = it.title;
    document.getElementById('event-modal-hub').href = '/hub';
    document.getElementById('event-modal-body').innerHTML = `
      <div class="detail-section">
        ${TodoApp.statusBadge(it.status, it.status_info)}
        <span style="margin-left:8px;">${it.priority_info?.icon || ''} ${TodoApp.esc(it.priority_info?.name || '')}</span>
      </div>
      <div class="detail-section">
        <h4>日期</h4>
        <p>开始 ${TodoApp.formatDate(it.start_date)} · 截止 ${TodoApp.formatDate(it.due_date)}</p>
      </div>
      ${it.content ? `<div class="detail-section"><h4>内容</h4><p style="white-space:pre-wrap;">${TodoApp.esc(it.content)}</p></div>` : ''}
      <div class="detail-section">
        <h4>附件</h4>
        <p class="attachment-hint">单文件最大 20MB，可上传多个附件</p>
        <div class="attachment-upload">
          <button type="button" class="btn btn-outline btn-sm" id="event-modal-upload">选择文件上传</button>
        </div>
        <div id="event-modal-attachments"></div>
      </div>
    `;
    document.getElementById('event-modal-upload').onclick = () => pickAttachments(itemId);
    document.getElementById('event-modal').classList.add('open');
    await renderModalAttachments(itemId);
  }

  function changeMonth(delta) {
    state.month += delta;
    if (state.month > 12) { state.month = 1; state.year++; }
    if (state.month < 1) { state.month = 12; state.year--; }
    loadMonth();
  }

  async function loadMonth() {
    const p = TodoApp.scopeParams(state.scope);
    p.set('action', 'month_events');
    p.set('month', monthStr());
    const res = await TodoApp.api('/api/calendar?' + p);
    state.monthItems = res.ok ? res.items : [];
    renderCalendar();
  }

  async function loadDay() {
    const p = TodoApp.scopeParams(state.scope);
    p.set('action', 'day_events');
    p.set('date', state.selectedDate);
    const res = await TodoApp.api('/api/calendar?' + p);
    if (res.ok) {
      state.todayItems = res.today || [];
      state.overdueItems = res.overdue || [];
    }
    document.getElementById('date-title').textContent = state.selectedDate;
    document.getElementById('today-count').textContent = state.todayItems.length;
    document.getElementById('overdue-count').textContent = state.overdueItems.length;
    document.getElementById('tabs').style.display = '';
    renderEvents();
  }

  async function loadRegular() {
    const p = TodoApp.scopeParams(state.scope);
    p.set('action', 'regular_items');
    const res = await TodoApp.api('/api/calendar?' + p);
    const el = document.getElementById('regular-list');
    if (!res.ok || !res.items.length) {
      el.innerHTML = '<div style="font-size:12px;color:var(--text-muted);">暂无常规事项</div>';
      return;
    }
    el.innerHTML = res.items.map(it =>
      `<div class="tc-regular-item" data-id="${it.id}">${TodoApp.esc(it.title)}</div>`
    ).join('');
  }

  function renderCalendar() {
    document.getElementById('month-title').textContent = `${state.year}年${state.month}月`;

    const first = new Date(state.year, state.month - 1, 1);
    const lastDay = new Date(state.year, state.month, 0).getDate();
    const startWd = first.getDay();
    const today = fmt(new Date());

    const eventDates = new Set();
    state.monthItems.forEach(it => {
      if (it.occurrences) it.occurrences.forEach(d => eventDates.add(d));
      else {
        if (it.start_date) eventDates.add(it.start_date);
        if (it.due_date && it.due_date !== '2999-12-31') eventDates.add(it.due_date);
        if (it.checkpoint_date) eventDates.add(it.checkpoint_date);
      }
    });

    const el = document.getElementById('cal-days');
    el.innerHTML = '';
    const prevLast = new Date(state.year, state.month - 1, 0).getDate();
    for (let i = startWd - 1; i >= 0; i--) {
      el.appendChild(makeDay(prevLast - i, true, eventDates, today));
    }
    for (let d = 1; d <= lastDay; d++) {
      el.appendChild(makeDay(d, false, eventDates, today));
    }
    const total = startWd + lastDay;
    const rem = total % 7 === 0 ? 0 : 7 - (total % 7);
    for (let d = 1; d <= rem; d++) {
      el.appendChild(makeDay(d, true, eventDates, today));
    }
  }

  function makeDay(num, other, eventDates, today) {
    const div = document.createElement('div');
    div.className = 'tc-day';
    div.textContent = num;
    if (other) div.classList.add('other-month');

    let dateStr;
    if (other && num > 20) {
      const pm = state.month === 1 ? 12 : state.month - 1;
      const py = state.month === 1 ? state.year - 1 : state.year;
      dateStr = `${py}-${String(pm).padStart(2,'0')}-${String(num).padStart(2,'0')}`;
    } else if (other) {
      const nm = state.month === 12 ? 1 : state.month + 1;
      const ny = state.month === 12 ? state.year + 1 : state.year;
      dateStr = `${ny}-${String(nm).padStart(2,'0')}-${String(num).padStart(2,'0')}`;
    } else {
      dateStr = `${state.year}-${String(state.month).padStart(2,'0')}-${String(num).padStart(2,'0')}`;
    }

    if (dateStr === today) div.classList.add('today');
    if (dateStr === state.selectedDate) div.classList.add('selected');
    if (eventDates.has(dateStr)) div.classList.add('has-events');

    div.onclick = () => {
      state.selectedDate = dateStr;
      if (other) {
        const [y, m] = dateStr.split('-').map(Number);
        state.year = y; state.month = m;
        loadMonth();
      } else {
        renderCalendar();
      }
      loadDay();
    };
    return div;
  }

  function renderEvents() {
    const items = state.activeTab === 'overdue' ? state.overdueItems : state.todayItems;
    const el = document.getElementById('event-list');
    if (!items.length) {
      el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">${state.activeTab === 'overdue' ? '⏰' : '📋'}</div><p>${state.activeTab === 'overdue' ? '暂无逾期事项' : '本日暂无事项'}</p></div>`;
      return;
    }
    const showAttach = state.activeTab === 'today';
    el.innerHTML = items.map(it => `
      <div class="tc-event" data-id="${it.id}">
        <div class="tc-event-main">
          <div class="tc-event-title">${TodoApp.esc(it.title)}</div>
          <div class="tc-event-meta">
            ${TodoApp.statusBadge(it.status, it.status_info)}
            <span>${it.priority_info?.icon || ''}</span>
            ${it.assignee_name ? `<span>👤 ${TodoApp.esc(it.assignee_name)}</span>` : ''}
            ${it.frequency_label ? `<span>🔄 ${TodoApp.esc(it.frequency_label)}</span>` : ''}
            ${it.due_date ? `<span>📅 ${it.due_date}</span>` : ''}
            ${showAttach ? attachmentBadge(it.attachment_count) : ''}
          </div>
        </div>
        ${showAttach ? `
        <div class="tc-event-actions">
          <button type="button" class="btn btn-outline btn-sm tc-event-upload">📎 上传附件</button>
          <button type="button" class="btn btn-outline btn-sm tc-event-detail">查看详情</button>
        </div>` : ''}
      </div>
    `).join('');

    el.querySelectorAll('.tc-event').forEach(ev => {
      const id = +ev.dataset.id;
      const main = ev.querySelector('.tc-event-main');
      if (main) main.onclick = () => showAttach && openEventModal(id);

      const uploadBtn = ev.querySelector('.tc-event-upload');
      if (uploadBtn) {
        uploadBtn.onclick = e => {
          e.stopPropagation();
          pickAttachments(id);
        };
      }
      const detailBtn = ev.querySelector('.tc-event-detail');
      if (detailBtn) {
        detailBtn.onclick = e => {
          e.stopPropagation();
          openEventModal(id);
        };
      }
    });
  }

  async function doSearch() {
    const q = document.getElementById('search-input').value.trim();
    const el = document.getElementById('search-results');
    if (!q) { el.innerHTML = ''; return; }
    const p = TodoApp.scopeParams(state.scope);
    p.set('action', 'search_items');
    p.set('q', q);
    const res = await TodoApp.api('/api/calendar?' + p);
    if (!res.ok || !res.items.length) {
      el.innerHTML = '<div style="color:var(--text-muted);font-size:13px;">无匹配结果</div>';
      return;
    }
    el.innerHTML = res.items.map(it => `
      <div class="item-row" style="cursor:default;">
        <div><div class="item-row-title">${TodoApp.esc(it.title)}</div>
        <div class="item-row-meta">${TodoApp.statusBadge(it.status, it.status_info)}</div></div>
      </div>
    `).join('');
  }

  bindEvents();
  loadMonth();
  loadDay();
  loadRegular();
})();
