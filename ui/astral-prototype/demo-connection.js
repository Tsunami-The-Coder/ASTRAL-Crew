/* Same-origin demo bridge for local HTTP or hosted HTTPS; file:// stays offline. */
(function () {
  'use strict';
  var connected = false, running = false;
  var $ = function (id) { return document.getElementById(id); };
  var view = window.AstralMissionView;
  async function request(path, body) {
    var response = await fetch(path, body === undefined ? { cache: 'no-store' } : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    var data = await response.json(); if (!response.ok) throw Error(data.error || 'Local backend request failed'); return data;
  }
  function refreshControls() {
    $('demo-run').disabled = !connected || running;
    var bundle = view.current();
    $('demo-review-save').disabled = !connected || running || !bundle.demo_server || !bundle.demo_server.connected || !bundle.overview.current_analysis;
  }
  function display(data) {
    var publicDemo = !!(data.demo_server && data.demo_server.public_demo);
    view.load(data, publicDemo ? 'Public synthetic model demo' : 'Local model backend');
    document.body.classList.add('backend-connected');
    if (publicDemo) {
      var mode = document.querySelector('.topbar .offline');
      if (mode) mode.textContent = '◉ PUBLIC SYNTHETIC DEMO';
    }
    $('mission-mode-badge').textContent = 'SYNTHETIC SIGNALS';
    var scenario = data.demo_server && data.demo_server.scenario;
    if (scenario) $('demo-scenario').value = scenario;
    $('demo-connection-status').textContent = publicDemo
      ? 'Voice + wearable pipelines connected · private temporary demo session (clears on restart)'
      : 'Voice + wearable pipelines connected · saved locally';
    $('mission-import-message').textContent = data.overview.current_analysis ? 'Generated test signals, actual pipeline code. No live sensor feed.' : 'Historical results — run a scenario for a fresh demo.';
    $('mission-import-message').className = 'import-message';
    refreshControls();
  }
  $('demo-run').addEventListener('click', async function () {
    if (!connected || running) return;
    running = true; document.body.classList.add('demo-busy'); refreshControls();
    $('demo-run').textContent = 'Running…'; $('demo-connection-status').textContent = 'Extracting wrist features and analyzing voice…';
    try { var generated = await request('/api/demo/run', { scenario: $('demo-scenario').value }); display(generated); document.dispatchEvent(new CustomEvent('astral-demo-generated', { detail: generated })); }
    catch (error) { $('demo-connection-status').textContent = error.message; }
    finally { running = false; document.body.classList.remove('demo-busy'); $('demo-run').textContent = 'Run preset demo'; refreshControls(); }
  });
  $('demo-review-form').addEventListener('submit', async function (event) {
    event.preventDefault(); if (!connected || running) return;
    var current = view.current(); var analysis = current.overview.current_analysis; if (!analysis || !current.demo_server) return;
    $('demo-review-save').disabled = true;
    try {
      var data = await request('/api/reviews', { analysis_id: analysis.id, snapshot_id: current.overview.snapshot.id, run_id: current.overview.snapshot.payload.run_id, reviewer: $('demo-reviewer').value, decision: $('demo-decision').value, note: $('demo-review-note').value });
      display(data); $('demo-review-status').textContent = data.demo_server && data.demo_server.public_demo
        ? 'Review saved temporarily in this browser session.' : 'Review saved locally. Original findings retained.';
      $('demo-review-note').value = '';
    } catch (error) { $('demo-review-status').textContent = error.message; }
    finally { refreshControls(); }
  });
  $('demo-export').addEventListener('click', function () {
    var blob = new Blob([JSON.stringify(view.current(), null, 2)], { type: 'application/json' });
    var url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = 'astral-mission-results.json'; link.click(); setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  });
  document.addEventListener('astral-data-changed', refreshControls);
  var apiMode = location.protocol === 'https:' || (location.protocol === 'http:' && ['127.0.0.1', 'localhost'].includes(location.hostname));
  if (apiMode) {
    $('demo-connection-status').textContent = 'Connecting to model backend…';
    request('/api/health').then(async function (health) {
      if (health.status !== 'ready') throw Error('Backend is not ready');
      if (health.public_demo) {
        document.dispatchEvent(new CustomEvent('astral-public-demo'));
        await request('/api/session', {});
      }
      connected = true;
      return request('/api/mission');
    }).then(display).catch(function () { connected = false; $('demo-connection-status').textContent = 'Backend unavailable · offline replay retained'; refreshControls(); });
  }
  if (apiMode) setInterval(async function () {
    if (running || document.hidden) return;
    var current = view.current();
    if (connected && !current.demo_server) return; // Preserve an explicitly loaded offline replay.
    try {
      var data;
      try { data = await request('/api/mission'); }
      catch (error) {
        if (!error.message.includes('Session expired')) throw error;
        await request('/api/session', {});
        data = await request('/api/mission');
      }
      var previous = current.overview;
      connected = true;
      if (!current.demo_server || previous.snapshot.id !== data.overview.snapshot.id || previous.freshness.status !== data.overview.freshness.status || JSON.stringify(current.mission_logs) !== JSON.stringify(data.mission_logs)) display(data);
      refreshControls();
    } catch (error) {
      connected = false; $('demo-connection-status').textContent = 'Backend unavailable · stored results retained'; refreshControls();
    }
  }, 15000);
})();
