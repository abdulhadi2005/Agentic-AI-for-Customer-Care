(function (global) {
  'use strict';

  function nowStamp() {
    const d = new Date();
    return d.toTimeString().split(' ')[0];
  }

  function buildMarkup() {
    return `
      <div class="tw-root">
        <div class="tw-header">
          <span class="tw-title">Voice Input Wrapper</span>
          <span class="tw-status-pill" data-tw-status-pill>
            <span class="tw-status-dot"></span>
            <span data-tw-status-text>Idle</span>
          </span>
        </div>

        <div class="tw-visual">
          <canvas data-tw-canvas></canvas>
          <div class="tw-visual-idle" data-tw-idle-label>Awaiting audio input&hellip;</div>
        </div>

        <div class="tw-controls">
          <button type="button" class="tw-btn tw-btn-primary" data-tw-record-btn>
            <svg class="tw-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="7"></circle>
            </svg>
            <span data-tw-record-label>Start Recording</span>
          </button>
        </div>

        <label class="tw-dropzone" data-tw-dropzone>
          <span data-tw-dropzone-label><strong>Click to upload</strong> or drag an audio file here</span>
          <input type="file" accept="audio/*" data-tw-file-input />
        </label>

        <div class="tw-transcript" data-tw-transcript-panel hidden>
          <div class="tw-transcript-label">Transcript</div>
          <div class="tw-transcript-text" data-tw-transcript-text></div>
        </div>

        <div class="tw-console" data-tw-console>
          <div class="tw-console-line tw-console-muted">Ready.</div>
        </div>
      </div>
    `;
  }

  var BACKEND_URL = 'http://localhost:8000/transcribe';

  function TranscriptionWrapper(container) {
    this.container = container;
    this.container.innerHTML = buildMarkup();

    this.els = {
      statusPill: container.querySelector('[data-tw-status-pill]'),
      statusText: container.querySelector('[data-tw-status-text]'),
      canvas: container.querySelector('[data-tw-canvas]'),
      idleLabel: container.querySelector('[data-tw-idle-label]'),
      recordBtn: container.querySelector('[data-tw-record-btn]'),
      recordLabel: container.querySelector('[data-tw-record-label]'),
      dropzone: container.querySelector('[data-tw-dropzone]'),
      dropzoneLabel: container.querySelector('[data-tw-dropzone-label]'),
      fileInput: container.querySelector('[data-tw-file-input]'),
      consoleBox: container.querySelector('[data-tw-console]'),
      transcriptPanel: container.querySelector('[data-tw-transcript-panel]'),
      transcriptText: container.querySelector('[data-tw-transcript-text]')
    };

    this.audioCtx = null;
    this.analyser = null;
    this.mediaStream = null;
    this.mediaRecorder = null;
    this.recordedChunks = [];
    this.isRecording = false;
    this.rafId = null;

    this._bindEvents();
    this.log('Wrapper initialized. Ready to accept mic or file input.', 'ok');
  }

  TranscriptionWrapper.prototype._bindEvents = function () {
    const self = this;

    this.els.recordBtn.addEventListener('click', function () {
      if (self.isRecording) {
        self.stopRecording();
      } else {
        self.startRecording();
      }
    });

    this.els.fileInput.addEventListener('change', function (e) {
      const file = e.target.files && e.target.files[0];
      if (file) self.handleFileUpload(file);
    });

    ['dragover', 'dragenter'].forEach(function (evt) {
      self.els.dropzone.addEventListener(evt, function (e) {
        e.preventDefault();
        self.els.dropzone.classList.add('tw-drag');
      });
    });

    ['dragleave', 'drop'].forEach(function (evt) {
      self.els.dropzone.addEventListener(evt, function (e) {
        e.preventDefault();
        self.els.dropzone.classList.remove('tw-drag');
      });
    });

    this.els.dropzone.addEventListener('drop', function (e) {
      const file = e.dataTransfer.files && e.dataTransfer.files[0];
      if (file) self.handleFileUpload(file);
    });
  };

  TranscriptionWrapper.prototype.log = function (message, level) {
    level = level || 'info';
    const line = document.createElement('div');
    line.className = 'tw-console-line tw-console-' + level;
    line.innerHTML = '<span class="tw-console-time">' + nowStamp() + '</span>' + message;
    this.els.consoleBox.appendChild(line);
    this.els.consoleBox.scrollTop = this.els.consoleBox.scrollHeight;
    console.log('[TranscriptionWrapper]', message);
  };

  TranscriptionWrapper.prototype._setStatus = function (text, live) {
    this.els.statusText.textContent = text;
    this.els.statusPill.classList.toggle('tw-live', !!live);
  };

  TranscriptionWrapper.prototype._showTranscript = function (text) {
    this.els.transcriptPanel.hidden = false;
    this.els.transcriptText.textContent = text;
  };

  // Shared bridge: sends any audio Blob/File to the FastAPI backend and
  // renders the returned transcript. Used by both the mic-recording path
  // and the file-upload path.
  TranscriptionWrapper.prototype.sendToBackend = async function (audioBlob, filename) {
    const self = this;
    this._setStatus('Transcribing…', true);
    this.log('Sending audio to backend (' + BACKEND_URL + ')…', 'info');

    const formData = new FormData();
    formData.append('file', audioBlob, filename || 'audio.webm');

    try {
      const response = await fetch(BACKEND_URL, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errText = await response.text().catch(function () { return response.statusText; });
        throw new Error('Server responded with ' + response.status + ': ' + errText);
      }

      const data = await response.json();
      const text = (data && data.text) ? data.text : '';

      if (text) {
        this.log('Transcription received (' + text.length + ' characters).', 'ok');
        this._showTranscript(text);
      } else {
        this.log('Backend responded but returned no transcript text.', 'err');
      }
    } catch (err) {
      this.log('Transcription request failed: ' + err.message, 'err');
    } finally {
      this._setStatus('Idle', false);
    }
  };

  TranscriptionWrapper.prototype.startRecording = async function () {
    const self = this;

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      this.log('getUserMedia is not supported in this browser.', 'err');
      return;
    }

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      this.log('Microphone permission denied or unavailable: ' + err.message, 'err');
      return;
    }

    this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const source = this.audioCtx.createMediaStreamSource(this.mediaStream);
    this.analyser = this.audioCtx.createAnalyser();
    this.analyser.fftSize = 256;
    source.connect(this.analyser);

    this.recordedChunks = [];
    this.mediaRecorder = new MediaRecorder(this.mediaStream);

    this.mediaRecorder.ondataavailable = function (e) {
      if (e.data && e.data.size > 0) {
        self.recordedChunks.push(e.data);
        self.log('Captured audio chunk (' + e.data.size + ' bytes).', 'info');
      }
    };

    this.mediaRecorder.onstop = function () {
      const blob = new Blob(self.recordedChunks, { type: 'audio/webm' });
      self.log('Recording stopped. Final blob ready: ' + blob.size + ' bytes, type ' + blob.type + '.', 'ok');
      self.mediaStream.getTracks().forEach(function (t) { t.stop(); });
      self.sendToBackend(blob, 'recording.webm');
    };

    this.mediaRecorder.start(500);
    this.isRecording = true;
    this.els.idleLabel.style.display = 'none';
    this._setStatus('Recording', true);
    this.els.recordLabel.textContent = 'Stop Recording';
    this.els.recordBtn.classList.add('tw-recording');
    this.log('Microphone stream acquired. Recording started.', 'ok');

    this._drawWaveform();
  };

  TranscriptionWrapper.prototype.stopRecording = function () {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }
    this.isRecording = false;
    this._setStatus('Idle', false);
    this.els.recordLabel.textContent = 'Start Recording';
    this.els.recordBtn.classList.remove('tw-recording');
    this.els.idleLabel.style.display = 'flex';

    const canvas = this.els.canvas;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (this.rafId) cancelAnimationFrame(this.rafId);
    if (this.audioCtx) {
      this.audioCtx.close();
      this.audioCtx = null;
    }
  };

  TranscriptionWrapper.prototype._drawWaveform = function () {
    const self = this;
    const canvas = this.els.canvas;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;

    function resize() {
      canvas.width = canvas.clientWidth * dpr;
      canvas.height = canvas.clientHeight * dpr;
    }
    resize();

    const bufferLength = this.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function draw() {
      if (!self.isRecording) return;
      self.rafId = requestAnimationFrame(draw);
      self.analyser.getByteTimeDomainData(dataArray);

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.lineWidth = 2 * dpr;
      ctx.strokeStyle = '#b7bec9';
      ctx.beginPath();

      const sliceWidth = canvas.width / bufferLength;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128.0;
        const y = (v * canvas.height) / 2;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
        x += sliceWidth;
      }
      ctx.lineTo(canvas.width, canvas.height / 2);
      ctx.stroke();
    }
    draw();
  };

  TranscriptionWrapper.prototype.handleFileUpload = function (file) {
    if (!file.type.startsWith('audio/')) {
      this.log('Rejected file "' + file.name + '" — not a recognized audio type.', 'err');
      return;
    }

    this.els.dropzoneLabel.innerHTML = '<strong>' + file.name + '</strong> selected';
    this.log(
      'Audio file selected: ' + file.name + ' (' + Math.round(file.size / 1024) + ' KB, ' + file.type + ').',
      'ok'
    );

    // Reset the input value so re-selecting the same file re-triggers 'change'.
    this.els.fileInput.value = '';

    this.sendToBackend(file, file.name);
  };

  global.TranscriptionWrapper = {
    init: function (selector) {
      const nodes = document.querySelectorAll(selector || '[data-tw-widget]');
      const instances = [];
      nodes.forEach(function (node) {
        instances.push(new TranscriptionWrapper(node));
      });
      return instances;
    }
  };
})(window);