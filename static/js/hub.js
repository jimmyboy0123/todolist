(function () {
  'use strict';

  let meta = { types: [] };
  let scope = 'my';
  let currentItemId = null;
  let pendingFiles = [];

  function formatFileSize(bytes) {
    if (!bytes) return '';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  function setAttachmentMode(itemId) {
    const hasId = !!itemId;
    document.getElementById('attachment-hint').textContent = hasId
      ? '可上传多个附件，单文件最大 20MB'
      : '可先选择文件，保存事项后自动上传（单文件最大 20MB）';
    document.getElementById('attachment-upload').style.display = '';
    if (!hasId) window._formAttachments = [];
  }

  function renderAttachmentList(attachments, editable) {
    const el = document.getElementById('attachment-list');
    if (!attachments?.length && !pendingFiles.length) {
      el.innerHTML = '';
      return;
    }
    const saved = (attachments || []).map(a => `
      <li class="attachment-item" data-att-id="${a.id}">
        <div class="attachment-item-name">
          <a href="${a.url}" target="_blank" rel="noopener" download>${TodoApp.esc(a.original_filename)}</a>
          <div class="attachment-item-meta">${formatFileSize(a.size_bytes)}</div>
        </div>
        ${editable ? `<div class="attachment-item-actions"><button type="button" class="btn btn-sm btn-danger att-del">删除</button></div>` : ''}
      </li>
    `).join('');
    const pending = pendingFiles.map((f, i) => `
      <li class="attachment-item" data-pending="${i}">
        <div class="attachment-item-name">
          <span>${TodoApp.esc(f.name)}</span>
          <div class="attachment-item-meta">${formatFileSize(f.size)} · 待上传</div>
        </div>
        <div class="attachment-item-actions"><button type="button" class="btn btn-sm btn-outline att-pending-del">移除</button></div>
      </li>
    `).join('');
    el.innerHTML = saved + pending;
    if (editable) {
      el.querySelectorAll('.att-del').forEach(btn => {
        btn.onclick = async e => {
          const li = e.target.closest('.attachment-item');
          const attId = +li.dataset.attId;
          if (!confirm('确定删除该附件？')) return;
          const res = await fetch('/api/attachments/' + attId, { method: 'DELETE' });
          const data = await res.json();
          if (data.ok) loadFormAttachments(+document.getElementById('f-id').value);
          else alert(data.msg || '删除失败');
        };
      });
      el.querySelectorAll('.att-pending-del').forEach(btn => {
        btn.onclick = e => {
          const i = +e.target.closest('.attachment-item').dataset.pending;
          pendingFiles.splice(i, 1);
          renderAttachmentList(window._formAttachments || [], true);
        };
      });
    }
  }

  async function loadFormAttachments(itemId) {
    if (!itemId) {
      window._formAttachments = [];
      renderAttachmentList([], true);
      return;
    }
    const res = await TodoApp.api('/api/items/' + itemId + '/attachments');
    window._formAttachments = res.ok ? res.attachments : [];
    renderAttachmentList(window._formAttachments, true);
  }

  async function uploadPendingFiles(itemId) {
    for (const file of pendingFiles) {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch('/api/items/' + itemId + '/attachments', { method: 'POST', body: fd });
      const data = await res.json();
      if (!data.ok) {
        alert((file.name || '文件') + ' 上传失败：' + (data.msg || '未知错误'));
        return false;
      }
    }
    pendingFiles = [];
    return true;
  }

  async function uploadFiles(itemId, files) {
    for (const file of files) {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch('/api/items/' + itemId + '/attachments', { method: 'POST', body: fd });
      const data = await res.json();
      if (!data.ok) alert((file.name || '文件') + ' 上传失败：' + (data.msg || '未知错误'));
    }
    await loadFormAttachments(itemId);
  }

  async function init() {
    const res = await TodoApp.api('/api/meta');
    if (res.ok) meta = res;
    const sel = document.getElementById('f-type');
    sel.innerHTML = meta.types.map(t =>
      `<option value="${t.type_key}">${t.icon} ${TodoApp.esc(t.type_name)}</option>`
    ).join('');
    bindEvents();
    loadItems();
  }

  function bindEvents() {
    document.getElementById('btn-create').onclick = () => openForm();
    document.getElementById('modal-close').onclick = closeModal;
    document.getElementById('modal-cancel').onclick = closeModal;
    document.getElementById('modal-save').onclick = saveItem;
    document.getElementById('detail-close').onclick = () => document.getElementById('detail-modal').classList.remove('open');
    document.getElementById('detail-edit').onclick = () => { closeDetail(); openForm(currentItemId); };
    document.getElementById('detail-delete').onclick = deleteItem;
    document.getElementById('f-recurring').onchange = e => {
      document.getElementById('freq-group').style.display = e.target.checked ? '' : 'none';
    };
    document.getElementById('btn-pick-attachment').onclick = () => document.getElementById('f-attachment-input').click();
    document.getElementById('f-attachment-input').onchange = async e => {
      const files = [...(e.target.files || [])];
      e.target.value = '';
      const id = document.getElementById('f-id').value;
      if (!files.length) return;
      if (id) {
        await uploadFiles(+id, files);
      } else {
        pendingFiles.push(...files);
        renderAttachmentList([], true);
      }
    };

    document.querySelectorAll('#scope-chips .chip').forEach(chip => {
      chip.onclick = () => {
        document.querySelectorAll('#scope-chips .chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        scope = chip.dataset.scope;
        loadItems();
      };
    });

    document.getElementById('filter-status').onchange = loadItems;
    let timer;
    document.getElementById('filter-search').oninput = () => {
      clearTimeout(timer);
      timer = setTimeout(loadItems, 300);
    };
  }

  async function loadItems() {
    const p = TodoApp.scopeParams(scope);
    const status = document.getElementById('filter-status').value;
    const q = document.getElementById('filter-search').value.trim();
    if (status) p.set('status', status);
    if (q) p.set('q', q);

    const res = await TodoApp.api('/api/items?' + p);
    const el = document.getElementById('item-list');
    if (!res.ok || !res.items.length) {
      el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📋</div><p>暂无事项</p><button class="btn btn-primary" onclick="document.getElementById(\'btn-create\').click()">创建第一个事项</button></div>';
      return;
    }
    el.innerHTML = res.items.map(it => `
      <div class="item-row" data-id="${it.id}">
        <div style="flex:1;">
          <div class="item-row-title">${TodoApp.esc(it.title)}</div>
          <div class="item-row-meta">
            ${TodoApp.statusBadge(it.status, it.status_info)}
            <span>${it.priority_info?.icon || ''} ${TodoApp.esc(it.priority_info?.name || '')}</span>
            <span>📅 ${TodoApp.formatDate(it.due_date || it.start_date)}</span>
            ${it.assignee_name ? `<span>👤 ${TodoApp.esc(it.assignee_name)}</span>` : ''}
            ${it.child_count ? `<span>📎 ${it.child_count} 子项</span>` : ''}
          </div>
        </div>
      </div>
    `).join('');
    el.querySelectorAll('.item-row').forEach(row => {
      row.onclick = () => showDetail(+row.dataset.id);
    });
  }

  function openForm(id) {
    document.getElementById('modal-title').textContent = id ? '编辑事项' : '新建事项';
    document.getElementById('f-id').value = id || '';
    pendingFiles = [];
    setAttachmentMode(id);
    if (id) {
      TodoApp.api('/api/items/' + id).then(res => {
        if (!res.ok) return;
        fillForm(res.item);
        loadFormAttachments(id);
      });
    } else {
      document.getElementById('f-title').value = '';
      document.getElementById('f-scope').value = scope;
      document.getElementById('f-status').value = 'open';
      document.getElementById('f-priority').value = 'normal';
      document.getElementById('f-start').value = new Date().toISOString().slice(0, 10);
      document.getElementById('f-due').value = '';
      document.getElementById('f-assignee').value = '';
      document.getElementById('f-content').value = '';
      document.getElementById('f-recurring').checked = false;
      document.getElementById('f-regular').checked = false;
      document.getElementById('freq-group').style.display = 'none';
      renderAttachmentList([], true);
    }
    document.getElementById('item-modal').classList.add('open');
  }

  function fillForm(it) {
    document.getElementById('f-title').value = it.title || '';
    document.getElementById('f-scope').value = it.scope || 'my';
    document.getElementById('f-type').value = it.item_type || 'todo';
    document.getElementById('f-status').value = it.status || 'open';
    document.getElementById('f-priority').value = it.priority || 'normal';
    document.getElementById('f-start').value = it.start_date || '';
    document.getElementById('f-due').value = it.due_date && it.due_date !== '2999-12-31' ? it.due_date : '';
    document.getElementById('f-assignee').value = it.assignee_name || '';
    document.getElementById('f-content').value = it.content || '';
    document.getElementById('f-recurring').checked = !!it.is_recurring;
    document.getElementById('f-regular').checked = !!it.is_regular;
    document.getElementById('f-frequency').value = it.frequency || 'weekly';
    document.getElementById('freq-group').style.display = it.is_recurring ? '' : 'none';
  }

  function closeModal() {
    document.getElementById('item-modal').classList.remove('open');
  }

  async function saveItem() {
    const id = document.getElementById('f-id').value;
    const data = {
      title: document.getElementById('f-title').value.trim(),
      scope: document.getElementById('f-scope').value,
      item_type: document.getElementById('f-type').value,
      status: document.getElementById('f-status').value,
      priority: document.getElementById('f-priority').value,
      start_date: document.getElementById('f-start').value || null,
      due_date: document.getElementById('f-due').value || null,
      assignee_name: document.getElementById('f-assignee').value.trim(),
      creator_name: '',
      team_name: '',
      department_name: '',
      content: document.getElementById('f-content').value.trim(),
      is_recurring: document.getElementById('f-recurring').checked,
      frequency: document.getElementById('f-recurring').checked ? document.getElementById('f-frequency').value : null,
      is_regular: document.getElementById('f-regular').checked,
    };
    if (!data.title) { alert('请填写标题'); return; }

    const res = id
      ? await TodoApp.api('/api/items/' + id, { method: 'PUT', body: JSON.stringify(data) })
      : await TodoApp.api('/api/items', { method: 'POST', body: JSON.stringify(data) });

    if (!res.ok) { alert(res.msg || '保存失败'); return; }

    const savedId = id ? +id : res.id;
    if (pendingFiles.length && savedId) {
      const ok = await uploadPendingFiles(savedId);
      if (!ok) return;
    }
    closeModal();
    loadItems();
  }

  async function showDetail(id) {
    currentItemId = id;
    const res = await TodoApp.api('/api/items/' + id);
    if (!res.ok) return;
    const it = res.item;
    document.getElementById('detail-title').textContent = it.title;
    document.getElementById('detail-body').innerHTML = `
      <div class="detail-section">
        ${TodoApp.statusBadge(it.status, it.status_info)}
        <span style="margin-left:8px;">${it.priority_info?.icon || ''} ${TodoApp.esc(it.priority_info?.name)}</span>
      </div>
      <div class="detail-section"><h4>日期</h4><p>开始 ${TodoApp.formatDate(it.start_date)} · 截止 ${TodoApp.formatDate(it.due_date)}</p></div>
      ${it.assignee_name ? `<div class="detail-section"><h4>负责人</h4><p>${TodoApp.esc(it.assignee_name)}</p></div>` : ''}
      ${it.content ? `<div class="detail-section"><h4>内容</h4><p style="white-space:pre-wrap;">${TodoApp.esc(it.content)}</p></div>` : ''}
      ${res.attachments?.length ? `<div class="detail-section"><h4>附件 (${res.attachments.length})</h4><ul class="attachment-list">${res.attachments.map(a => `
        <li class="attachment-item">
          <div class="attachment-item-name">
            <a href="${a.url}" target="_blank" rel="noopener" download>${TodoApp.esc(a.original_filename)}</a>
            <div class="attachment-item-meta">${formatFileSize(a.size_bytes)}</div>
          </div>
        </li>`).join('')}</ul></div>` : ''}
      ${res.children?.length ? `<div class="detail-section"><h4>子事项 (${res.children.length})</h4>${res.children.map(c => `<div class="item-row" style="margin-bottom:4px;cursor:default;"><span>${TodoApp.esc(c.title)}</span> ${TodoApp.statusBadge(c.status, c.status_info)}</div>`).join('')}</div>` : ''}
      <div class="detail-section">
        <h4>备注</h4>
        <textarea class="form-control" id="new-comment" rows="2" placeholder="添加备注..."></textarea>
        <button class="btn btn-sm btn-outline" style="margin-top:8px;" id="add-comment">添加</button>
        <div style="margin-top:12px;">${(res.activities || []).map(a => `<div class="activity-item"><strong>${TodoApp.esc(a.author_name || '匿名')}</strong> · ${a.created_at}<br>${TodoApp.esc(a.content)}</div>`).join('') || '<span style="color:var(--text-muted);font-size:13px;">暂无备注</span>'}</div>
      </div>
    `;
    document.getElementById('add-comment').onclick = async () => {
      const content = document.getElementById('new-comment').value.trim();
      if (!content) return;
      await TodoApp.api('/api/items/' + id + '/activities', {
        method: 'POST',
        body: JSON.stringify({ content, author_name: '' }),
      });
      showDetail(id);
    };
    document.getElementById('detail-modal').classList.add('open');
  }

  function closeDetail() {
    document.getElementById('detail-modal').classList.remove('open');
  }

  async function deleteItem() {
    if (!currentItemId || !confirm('确定删除此事项？')) return;
    const res = await TodoApp.api('/api/items/' + currentItemId, { method: 'DELETE' });
    if (res.ok) { closeDetail(); loadItems(); }
  }

  init();
})();
