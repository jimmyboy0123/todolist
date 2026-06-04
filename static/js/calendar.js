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
    el.innerHTML = items.map(it => `
      <div class="tc-event" data-id="${it.id}">
        <div class="tc-event-title">${TodoApp.esc(it.title)}</div>
        <div class="tc-event-meta">
          ${TodoApp.statusBadge(it.status, it.status_info)}
          <span>${it.priority_info?.icon || ''}</span>
          ${it.assignee_name ? `<span>👤 ${TodoApp.esc(it.assignee_name)}</span>` : ''}
          ${it.frequency_label ? `<span>🔄 ${TodoApp.esc(it.frequency_label)}</span>` : ''}
          ${it.due_date ? `<span>📅 ${it.due_date}</span>` : ''}
        </div>
      </div>
    `).join('');
    el.querySelectorAll('.tc-event').forEach(ev => {
      ev.onclick = () => { window.location.href = '/hub'; };
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
