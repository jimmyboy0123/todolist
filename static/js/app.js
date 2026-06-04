/** 公共工具 */
const TodoApp = {
  esc(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  },

  async api(url, opts = {}) {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
      ...opts,
    });
    return res.json();
  },

  statusBadge(status, info) {
    const color = info?.color || '#999';
    const name = info?.name || status;
    return `<span class="badge" style="background:${color}20;color:${color}">${this.esc(name)}</span>`;
  },

  formatDate(d) {
    if (!d || d === '2999-12-31') return '未设定';
    return d;
  },

  scopeParams(scope) {
    return new URLSearchParams({ scope });
  },
};

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.app-nav a').forEach(a => {
    if (a.pathname === location.pathname) a.classList.add('active');
  });
});
