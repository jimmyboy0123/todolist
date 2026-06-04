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

  formatFileSize(bytes) {
    if (!bytes) return '';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  },

  async fetchAttachments(itemId) {
    const res = await this.api('/api/items/' + itemId + '/attachments');
    return res.ok ? res.attachments : [];
  },

  async uploadAttachmentFiles(itemId, files) {
    let ok = true;
    for (const file of files) {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch('/api/items/' + itemId + '/attachments', { method: 'POST', body: fd });
      const data = await res.json();
      if (!data.ok) {
        alert((file.name || '文件') + ' 上传失败：' + (data.msg || '未知错误'));
        ok = false;
      }
    }
    return ok;
  },

  async deleteAttachment(attId) {
    const res = await fetch('/api/attachments/' + attId, { method: 'DELETE' });
    return res.json();
  },
};

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.app-nav a').forEach(a => {
    if (a.pathname === location.pathname) a.classList.add('active');
  });
});
