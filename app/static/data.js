const docsTableBody = document.querySelector('#docsTable tbody');
const chunksTableBody = document.querySelector('#chunksTable tbody');

const docLimit = document.getElementById('docLimit');
const chunkLimit = document.getElementById('chunkLimit');
const chunkDocId = document.getElementById('chunkDocId');
const loadDocsBtn = document.getElementById('loadDocs');
const loadChunksBtn = document.getElementById('loadChunks');

function renderDocs(rows) {
  docsTableBody.innerHTML = '';
  rows.forEach((d) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${d.id}</td>
      <td>${d.doc_id}</td>
      <td>${d.title}</td>
      <td>${d.doc_type || ''}</td>
      <td><small>${d.created_at || ''}</small></td>
    `;
    docsTableBody.appendChild(tr);
  });
}

function renderChunks(rows) {
  chunksTableBody.innerHTML = '';
  rows.forEach((c) => {
    const tr = document.createElement('tr');
    const text = (c.text || '').slice(0, 240).replace(/\n/g, ' ');
    tr.innerHTML = `
      <td>${c.id}</td>
      <td>${c.document_id}</td>
      <td>${c.section_label} <small>(${c.section_type})</small></td>
      <td>${c.page_start}-${c.page_end}</td>
      <td>${text}</td>
    `;
    chunksTableBody.appendChild(tr);
  });
}

async function loadDocs() {
  const limit = Number(docLimit.value) || 50;
  const res = await fetch(`/api/documents?limit=${limit}`);
  const data = await res.json();
  renderDocs(data);
}

async function loadChunks() {
  const limit = Number(chunkLimit.value) || 50;
  const docId = chunkDocId.value.trim();
  const query = new URLSearchParams({ limit: String(limit) });
  if (docId) query.set('document_id', docId);
  const res = await fetch(`/api/chunks?${query.toString()}`);
  const data = await res.json();
  renderChunks(data);
}

loadDocsBtn.addEventListener('click', loadDocs);
loadChunksBtn.addEventListener('click', loadChunks);

loadDocs();
