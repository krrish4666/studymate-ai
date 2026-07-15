import { getAuthHeaders } from './api.js';

export function initUpload(dropzoneEl, inputEl, progressEl, feature) {
  if (!dropzoneEl || !inputEl) return;

  dropzoneEl.addEventListener('click', () => inputEl.click());

  dropzoneEl.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzoneEl.classList.add('drag-over');
  });

  dropzoneEl.addEventListener('dragleave', () => {
    dropzoneEl.classList.remove('drag-over');
  });

  dropzoneEl.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzoneEl.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file, progressEl, feature);
  });

  inputEl.addEventListener('change', () => {
    const file = inputEl.files[0];
    if (file) uploadFile(file, progressEl, feature);
  });
}

async function uploadFile(file, progressEl, feature) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('feature', feature);

  const token = localStorage.getItem('studymate-token');
  const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && progressEl) {
        const pct = Math.round((e.loaded / e.total) * 100);
        progressEl.querySelector('.fill').style.width = `${pct}%`;
        progressEl.hidden = false;
      }
    });

    xhr.addEventListener('load', () => {
      progressEl.hidden = true;
      if (xhr.status === 200) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          reject(JSON.parse(xhr.responseText));
        } catch {
          reject({ detail: 'Upload failed' });
        }
      }
    });

    xhr.addEventListener('error', () => {
      progressEl.hidden = true;
      reject({ detail: 'Upload failed' });
    });

    xhr.open('POST', '/api/v1/upload');
    headers['Accept'] = 'application/json';
    for (const [k, v] of Object.entries(headers)) {
      xhr.setRequestHeader(k, v);
    }
    xhr.send(formData);
  });
}
