const messages = document.getElementById('messages');
const composer = document.getElementById('composer');
const messageInput = document.getElementById('message');
const topKInput = document.getElementById('topK');
const docTypeSelect = document.getElementById('docType');
const searchBtn = document.getElementById('searchBtn');
const citationsEl = document.getElementById('citations');
const statusEl = document.getElementById('status');

function addMessage(text, role = 'assistant') {
  const wrapper = document.createElement('div');
  wrapper.className = `message ${role}`;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  wrapper.appendChild(bubble);
  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
  return bubble;
}

function setCitations(citations) {
  citationsEl.innerHTML = '';
  if (!citations || citations.length === 0) {
    citationsEl.classList.add('empty');
    citationsEl.textContent = 'Chưa có trích dẫn';
    return;
  }
  citationsEl.classList.remove('empty');
  citations.forEach((c) => {
    const div = document.createElement('div');
    div.className = 'cite';
    div.innerHTML = `
      <div><strong>${c.source_id}</strong> — ${c.doc_title || ''}</div>
      <div class="meta">${c.section_label || ''} • ${c.pages || ''}</div>
      ${c.url ? `<div class="meta"><a href="${c.url}" target="_blank" rel="noreferrer">${c.url}</a></div>` : ''}
      ${c.quote ? `<div class="quote">“${c.quote}”</div>` : ''}
    `;
    citationsEl.appendChild(div);
  });
}

async function checkHealth() {
  try {
    const res = await fetch('/healthz');
    if (res.ok) {
      statusEl.textContent = 'Đã kết nối';
      statusEl.style.color = 'var(--accent-2)';
    } else {
      statusEl.textContent = 'Kết nối lỗi';
      statusEl.style.color = 'var(--danger)';
    }
  } catch (_) {
    statusEl.textContent = 'Không kết nối';
    statusEl.style.color = 'var(--danger)';
  }
}

async function sendChat() {
  const message = messageInput.value.trim();
  if (!message) return;
  const top_k = Number(topKInput.value) || 8;
  const doc_type = docTypeSelect.value || null;

  addMessage(message, 'user');
  const pending = addMessage('Đang trả lời...', 'assistant');
  messageInput.value = '';

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, top_k, doc_type })
    });
    if (!res.ok) {
      const text = await res.text();
      pending.textContent = `Lỗi: ${res.status} ${text}`;
      return;
    }
    const data = await res.json();
    pending.textContent = data.answer || '(Không có trả lời)';
    setCitations(data.citations || []);
  } catch (err) {
    pending.textContent = `Lỗi kết nối: ${err}`;
  }
}

async function searchOnly() {
  const query = messageInput.value.trim();
  if (!query) return;
  const top_k = Number(topKInput.value) || 8;
  const doc_type = docTypeSelect.value || null;

  addMessage(`[Search] ${query}`, 'user');
  const pending = addMessage('Đang tìm nguồn...', 'assistant');

  try {
    const res = await fetch('/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k, doc_type })
    });
    if (!res.ok) {
      const text = await res.text();
      pending.textContent = `Lỗi: ${res.status} ${text}`;
      return;
    }
    const hits = await res.json();
    const summary = hits.map((h) => `${h.source_id}: ${h.section_label} (${h.pages})`).join('\n');
    pending.textContent = summary || 'Không có nguồn';
    setCitations(hits.map((h) => ({
      source_id: h.source_id,
      doc_title: h.doc_title,
      section_label: h.section_label,
      pages: h.pages,
      url: h.url,
      quote: h.text?.slice(0, 200)
    })));
  } catch (err) {
    pending.textContent = `Lỗi kết nối: ${err}`;
  }
}

composer.addEventListener('submit', (e) => {
  e.preventDefault();
  sendChat();
});

searchBtn.addEventListener('click', () => {
  searchOnly();
});

checkHealth();
