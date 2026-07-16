;(function () {
  'use strict';

  var currentFileRecordId = null;

  function formatFileSize(bytes) {
    if (!bytes) return '';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  function showToast(message, type) {
    type = type || 'info';
    var toast = document.getElementById('toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'toast';
      toast.className = 'toast';
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.className = 'toast ' + type;
    requestAnimationFrame(function () { toast.classList.add('show'); });
    setTimeout(function () { toast.classList.remove('show'); }, 3500);
  }

  function showUploadError(msg) {
    var el = document.getElementById('upload-error');
    if (!el) {
      el = document.createElement('div');
      el.id = 'upload-error';
      el.style.cssText =
        'background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;' +
        'padding:12px 16px;margin-top:12px;color:#b91c1c;font-size:0.9rem;';
      var ref = document.getElementById('upload-area') || document.getElementById('dropzone');
      if (ref && ref.parentElement) ref.parentElement.appendChild(el);
    }
    el.textContent = msg;
    el.hidden = false;
  }

  function clearUploadError() {
    var el = document.getElementById('upload-error');
    if (el) el.hidden = true;
  }

  function switchToFileCard(file, result) {
    clearUploadError();

    var uploadArea = document.getElementById('upload-area');
    if (uploadArea) {
      uploadArea.style.display = 'none';
      uploadArea.hidden = true;
    }

    var fileInfo = document.getElementById('file-info');
    if (fileInfo) {
      var fileName = document.getElementById('file-name');
      var fileSize = document.getElementById('file-size');
      var fileStatus = document.getElementById('file-status') || fileInfo.querySelector('.file-status');
      if (fileName) fileName.textContent = file.name;
      if (fileSize) fileSize.textContent = formatFileSize(file.size || (result && result.fileSize));
      if (fileStatus) {
        fileStatus.textContent = 'Ready to generate';
        fileStatus.className = 'file-status success';
      }
      fileInfo.hidden = false;
      fileInfo.style.display = 'flex';
    }

    var controls = document.getElementById('feature-controls');
    if (controls) {
      controls.hidden = false;
      controls.style.display = '';
    }

    var genBtn = document.getElementById('generate-btn');
    if (genBtn) genBtn.disabled = false;

    showToast('Upload successful!', 'success');
  }

  function switchToUploadArea() {
    currentFileRecordId = null;

    var fileInfo = document.getElementById('file-info');
    if (fileInfo) {
      fileInfo.hidden = true;
      fileInfo.style.display = 'none';
    }

    var uploadArea = document.getElementById('upload-area');
    if (uploadArea) {
      uploadArea.hidden = false;
      uploadArea.style.display = '';
    }
    var fileInput = document.getElementById('file-input');
    if (fileInput) fileInput.value = '';

    var progressEl = document.getElementById('upload-progress');
    if (progressEl) {
      progressEl.hidden = true;
      var fill = progressEl.querySelector('.fill');
      if (fill) fill.style.width = '0%';
    }

    var controls = document.getElementById('feature-controls');
    if (controls) {
      controls.hidden = true;
      controls.style.display = 'none';
    }

    var output = document.getElementById('feature-output');
    if (output) {
      output.hidden = true;
      output.style.display = 'none';
    }

    var loading = document.getElementById('loading-screen');
    if (loading) {
      loading.hidden = true;
      loading.style.display = 'none';
    }

    var genBtn = document.getElementById('generate-btn');
    if (genBtn) genBtn.disabled = true;
  }

  function bindRemoveButton() {
    var removeBtn = document.getElementById('remove-file-btn');
    if (removeBtn) {
      removeBtn.onclick = function () {
        switchToUploadArea();
        showToast('File removed', 'info');
      };
    }
  }

  function uploadFile(file, feature) {
    clearUploadError();

    var uploadArea = document.getElementById('upload-area');
    if (uploadArea) {
      uploadArea.style.display = 'none';
      uploadArea.hidden = true;
    }

    var fileInfo = document.getElementById('file-info');
    if (fileInfo) {
      var fileName = document.getElementById('file-name');
      var fileSize = document.getElementById('file-size');
      var fileStatus = document.getElementById('file-status') || fileInfo.querySelector('.file-status');
      if (fileName) fileName.textContent = file.name;
      if (fileSize) fileSize.textContent = formatFileSize(file.size);
      if (fileStatus) {
        fileStatus.textContent = 'Uploading...';
        fileStatus.className = 'file-status info';
      }
      fileInfo.hidden = false;
      fileInfo.style.display = 'flex';
    }

    var controls = document.getElementById('feature-controls');
    if (controls) {
      controls.hidden = true;
      controls.style.display = 'none';
    }
    var genBtn = document.getElementById('generate-btn');
    if (genBtn) genBtn.disabled = true;

    var formData = new FormData();
    formData.append('file', file);
    formData.append('feature', feature);

    var token = localStorage.getItem('studymate-token');
    var xhr = new XMLHttpRequest();
    var progressEl = document.getElementById('upload-progress');

    xhr.upload.addEventListener('progress', function (e) {
      if (e.lengthComputable && progressEl) {
        var pct = Math.round((e.loaded / e.total) * 100);
        var fill = progressEl.querySelector('.fill');
        if (fill) fill.style.width = pct + '%';
        progressEl.hidden = false;
      }
      var fileStatus = document.getElementById('file-status') || (document.getElementById('file-info') && document.getElementById('file-info').querySelector('.file-status'));
      if (fileStatus && e.lengthComputable) {
        var pct = Math.round((e.loaded / e.total) * 100);
        if (pct < 100) {
          fileStatus.textContent = 'Uploading (' + pct + '%)...';
        } else {
          fileStatus.textContent = 'Processing...';
        }
      }
    });

    xhr.addEventListener('load', function () {
      if (progressEl) progressEl.hidden = true;
      if (xhr.status === 200) {
        var result = JSON.parse(xhr.responseText);
        currentFileRecordId = result.fileRecordId;
        switchToFileCard(file, result);
        document.dispatchEvent(new CustomEvent('upload-complete', { detail: result }));
      } else {
        var detail = 'Upload failed';
        try { var err = JSON.parse(xhr.responseText); detail = err.detail || detail; } catch (e) {}
        var fileStatus = document.getElementById('file-status') || (document.getElementById('file-info') && document.getElementById('file-info').querySelector('.file-status'));
        if (fileStatus) {
          fileStatus.textContent = 'Upload failed';
          fileStatus.className = 'file-status error';
        }
        showToast(detail, 'error');
        showUploadError(detail);
      }
    });

    xhr.addEventListener('error', function () {
      if (progressEl) progressEl.hidden = true;
      var fileStatus = document.getElementById('file-status') || (document.getElementById('file-info') && document.getElementById('file-info').querySelector('.file-status'));
      if (fileStatus) {
        fileStatus.textContent = 'Network error';
        fileStatus.className = 'file-status error';
      }
      showToast('Upload failed - network error', 'error');
      showUploadError('Network error. Please try again.');
    });

    xhr.open('POST', '/api/v1/upload');
    xhr.setRequestHeader('Accept', 'application/json');
    if (token) xhr.setRequestHeader('Authorization', 'Bearer ' + token);
    xhr.send(formData);
  }

  function initUpload() {
    if (initUpload._done) return;
    initUpload._done = true;

    var dropzone = document.getElementById('dropzone');
    var fileInput = document.getElementById('file-input');
    if (!dropzone || !fileInput) return;

    var fileInfo = document.getElementById('file-info');
    if (fileInfo && fileInfo.hidden) {
      fileInfo.style.display = 'none';
    }

    var feature = dropzone.dataset.feature || 'general';

    dropzone.addEventListener('click', function () { fileInput.click(); });
    dropzone.addEventListener('dragover', function (e) {
      e.preventDefault();
      dropzone.classList.add('drag-over');
    });
    dropzone.addEventListener('dragleave', function () {
      dropzone.classList.remove('drag-over');
    });
    dropzone.addEventListener('drop', function (e) {
      e.preventDefault();
      dropzone.classList.remove('drag-over');
      var file = e.dataTransfer.files[0];
      if (file) uploadFile(file, feature);
    });
    fileInput.addEventListener('change', function () {
      var file = fileInput.files[0];
      if (file) uploadFile(file, feature);
    });

    bindRemoveButton();
  }

  window.StudyMateUpload = {
    getCurrentFileId: function () { return currentFileRecordId; },
    reset: function () { currentFileRecordId = null; },
    setFromHistory: function (fileRecordId) {
      currentFileRecordId = fileRecordId;
      var uploadArea = document.getElementById('upload-area');
      if (uploadArea) { uploadArea.hidden = true; uploadArea.style.display = 'none'; }
      var fileInfo = document.getElementById('file-info');
      if (fileInfo) {
        var fileStatus = document.getElementById('file-status') || fileInfo.querySelector('.file-status');
        if (fileStatus) {
          fileStatus.textContent = 'Ready to generate';
          fileStatus.className = 'file-status success';
        }
        fileInfo.hidden = false;
        fileInfo.style.display = 'flex';
      }
      var controls = document.getElementById('feature-controls');
      if (controls) { controls.hidden = false; controls.style.display = ''; }
      var genBtn = document.getElementById('generate-btn');
      if (genBtn) genBtn.disabled = false;
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initUpload);
  } else {
    initUpload();
  }
})();
