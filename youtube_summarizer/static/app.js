'use strict';

const form      = document.getElementById('analyze-form');
const urlInput  = document.getElementById('url-input');
const analyzeBtn = document.getElementById('analyze-btn');
const btnText   = document.getElementById('btn-text');
const btnSpinner = document.getElementById('btn-spinner');
const errorBox  = document.getElementById('error-box');
const loadingPanel = document.getElementById('loading-panel');

if (!form) {
  // Not on the index page — nothing to bind
} else {
  const steps = [
    document.getElementById('step-1'),
    document.getElementById('step-2'),
    document.getElementById('step-3'),
    document.getElementById('step-4'),
    document.getElementById('step-5'),
  ];

  let stepInterval = null;
  let currentStep = 0;

  function showError(msg) {
    errorBox.textContent = msg;
    errorBox.classList.remove('hidden');
    loadingPanel.classList.add('hidden');
    setLoading(false);
  }

  function setLoading(on) {
    analyzeBtn.disabled = on;
    btnText.textContent  = on ? 'Analyzing…' : 'Analyze';
    btnSpinner.classList.toggle('hidden', !on);
    errorBox.classList.add('hidden');
  }

  function startStepAnimation() {
    currentStep = 0;
    steps.forEach(s => {
      s.querySelector('.step-dot').classList.remove('active', 'done');
      s.classList.remove('active-step');
    });
    loadingPanel.classList.remove('hidden');
    activateStep(0);

    stepInterval = setInterval(() => {
      if (currentStep < steps.length - 1) {
        markDone(currentStep);
        currentStep++;
        activateStep(currentStep);
      }
    }, 5000);
  }

  function activateStep(i) {
    steps[i].querySelector('.step-dot').classList.add('active');
    steps[i].classList.add('active-step');
  }

  function markDone(i) {
    const dot = steps[i].querySelector('.step-dot');
    dot.classList.remove('active');
    dot.classList.add('done');
    steps[i].classList.remove('active-step');
  }

  function stopStepAnimation() {
    clearInterval(stepInterval);
    steps.forEach((s, i) => {
      markDone(i);
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = urlInput.value.trim();
    if (!url) return;

    setLoading(true);
    startStepAnimation();

    try {
      const resp = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });

      const data = await resp.json();

      if (!resp.ok) {
        showError(data.detail || 'Something went wrong. Please try again.');
        stopStepAnimation();
        return;
      }

      stopStepAnimation();
      // Redirect to the report page
      window.location.href = `/report/${data.id}`;

    } catch (err) {
      showError('Network error. Please check your connection and try again.');
      stopStepAnimation();
    }
  });
}
