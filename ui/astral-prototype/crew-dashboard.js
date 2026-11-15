/* Internal backend-review bundle viewer. Offline, static replay; no live claims. */
(function () {
  'use strict';
  var IDS = ['AST-01', 'AST-02', 'AST-03', 'AST-04', 'AST-05'];
  var COLORS = ['#62e0cf', '#8daeff', '#f7c76d', '#e998bd', '#b6a1ed'];
  var defaultBundle = JSON.parse(document.getElementById('mission-demo-data').textContent);
  var bundle = defaultBundle, selected = 'AST-01', activeModule = 'cognitive', sourceLabel = 'Bundled backend replay';
  var $ = function (id) { return document.getElementById(id); };
  function node(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; }
  function finite(v) { return typeof v === 'number' && Number.isFinite(v); }
  function value(v, decimals) { return finite(v) ? v.toFixed(decimals === undefined ? 0 : decimals) : 'Unavailable'; }
  function date(v) { var d = new Date(v); return Number.isFinite(d.getTime()) ? d.toISOString().slice(0, 16).replace('T', ' ') + ' UTC' : 'Time unavailable'; }
  function clock(v) { var d = new Date(v); return Number.isFinite(d.getTime()) ? d.toISOString().slice(11, 16) : '—'; }
  function snapshot() { return bundle.overview.snapshot; }
  function payload() { return snapshot() ? snapshot().payload : { crew: [], environment: {} }; }
  function analysisEntry() { return bundle.overview.current_analysis || bundle.overview.historical_analysis; }
  function report() { var e = analysisEntry(); return e ? e.report : null; }
  function member(id, row) { var crew = (row || payload()).crew; return Array.isArray(crew) ? crew.find(function (c) { return c.crew_id === id; }) : undefined; }
  function multimodal(id) { var r = report(); return r && Array.isArray(r.multimodal) ? r.multimodal.find(function (c) { return c.crew_id === id; }) : undefined; }
  function empty(container, text) { container.appendChild(node('div', 'empty-state', text)); }
  function validate(input) {
    if (!input || input.export_version !== 'internal-review-v1' || !input.overview || !Array.isArray(input.snapshot_history) || !Array.isArray(input.mission_logs)) throw Error('Choose an internal-review-v1 backend export.');
    var s = input.overview.snapshot;
    function validSnapshot(row) {
      if (!row || typeof row.timestamp !== 'string' || !Number.isFinite(Date.parse(row.timestamp)) || !row.payload || !Array.isArray(row.payload.crew) || row.data_origin !== 'synthetic') throw Error('The viewer supports timestamped synthetic snapshots only.');
      var seen = new Set();
      row.payload.crew.forEach(function (c) { if (!c || !IDS.includes(c.crew_id) || seen.has(c.crew_id)) throw Error('Crew IDs must be unique AST-01 through AST-05.'); seen.add(c.crew_id); });
    }
    if (s) validSnapshot(s);
    if (input.snapshot_history.length > 10000) throw Error('History exceeds the viewer limit.');
    input.snapshot_history.forEach(validSnapshot);
    ['mission_logs', 'medical_incidents'].forEach(function (key) {
      if (input[key] !== undefined && !Array.isArray(input[key])) throw Error(key + ' must be a list.');
    });
    input.mission_logs.forEach(function (entry) {
      if (!entry || (entry.reviews !== undefined && !Array.isArray(entry.reviews))) throw Error('Malformed review history.');
      (entry.reviews || []).forEach(function (review) { if (!review || typeof review !== 'object') throw Error('Malformed review entry.'); });
    });
    ['current_analysis', 'historical_analysis'].forEach(function (key) {
      var entry = input.overview[key];
      if (entry && (!s || entry.snapshot_id !== s.id || !entry.report || !Array.isArray(entry.report.findings) || !Array.isArray(entry.report.input_issues))) throw Error('Analysis does not match the selected snapshot.');
      if (entry) {
        entry.report.findings.forEach(function (finding) {
          if (!finding || typeof finding.code !== 'string' || typeof finding.message !== 'string') throw Error('Malformed finding.');
          if (finding.evidence !== undefined && (!Array.isArray(finding.evidence) || finding.evidence.some(function (e) { return !e || typeof e !== 'object'; }))) throw Error('Malformed finding evidence.');
        });
        entry.report.input_issues.forEach(function (issue) { if (!issue || typeof issue !== 'object') throw Error('Malformed input issue.'); });
        if (entry.report.multimodal !== undefined && !Array.isArray(entry.report.multimodal)) throw Error('Malformed model evidence.');
        (entry.report.multimodal || []).forEach(function (model) {
          if (!model || !IDS.includes(model.crew_id) || (model.issues !== undefined && !Array.isArray(model.issues))) throw Error('Malformed model result.');
          if (model.signals !== undefined && (!model.signals || typeof model.signals !== 'object' || Array.isArray(model.signals))) throw Error('Malformed model signals.');
        });
      }
    });
    return input;
  }
  var RESULT_COPY = {
    BOTH_INDICATORS_ELEVATED: {title:'Voice and wearable indicators are high', what:'Both inputs are above their demo comparison bands.', next:'Check the readings and the member’s recent activity.'},
    MODALITY_DISAGREEMENT: {title:'Voice and wearable results disagree', what:'One indicator is high while the other is low.', next:'Check both samples before drawing a conclusion.'},
    SHARED_CREW_CHANGE: {title:'Several crew members changed', what:'At least two members have multiple readings above or below their references.', next:'Check shared activities and cabin conditions.'},
    POSSIBLE_ENVIRONMENTAL_ASSOCIATION: {title:'Crew changes happened alongside rising CO₂', what:'The crew pattern and CO₂ trend occurred together. This does not prove the cause.', next:'Check the cabin readings and ventilation context.'},
    MOVEMENT_CAUTION: {title:'Movement affects the wearable result', what:'Motion makes a stress interpretation less reliable.', next:'Use a resting sample or check the activity context.'},
    RADIATION_RATE_INCREASE: {title:'Radiation dose rate increased', what:'The simulated rate rose from the earlier reading.', next:'Check the dose-rate readings and scenario.'},
    CABIN_PRESSURE_DROP: {title:'Cabin pressure dropped', what:'Pressure fell from the earlier cabin reading.', next:'Check the cabin sensor and scenario.'},
    CABIN_OXYGEN_FRACTION_DROP: {title:'Cabin oxygen dropped', what:'The oxygen fraction fell from the earlier reading.', next:'Check oxygen and pressure readings together.'}
  };
  function resultCopy(f) { return RESULT_COPY[f.code] || {title:f.message || 'Reading needs checking', what:f.message || 'A reading changed.', next:'Check the source readings.'}; }
  function memberResult(r,id) {
    if(!r)return {title:'Analysis not ready', detail:'Finish playback or submit an entry.', flagged:false};
    var flags=r.findings.filter(function(f){return f.crew_id===id||(f.crew_ids||[]).includes(id);});
    var priority=['BOTH_INDICATORS_ELEVATED','MODALITY_DISAGREEMENT','MOVEMENT_CAUTION'];
    flags.sort(function(a,b){var ai=priority.indexOf(a.code),bi=priority.indexOf(b.code);return (ai<0?99:ai)-(bi<0?99:bi);});
    if(flags.length){var copy=resultCopy(flags[0]);return {title:copy.title,detail:copy.next,flagged:true};}
    var m=(r.multimodal||[]).find(function(item){return item.crew_id===id;});
    var voice=m&&m.signals&&m.signals.voice;
    if(voice&&voice.raw&&voice.raw.details&&voice.raw.details.nasa_demo)return {title:'Recorded audio features extracted',detail:'No crew stress score: this recording has no matching member baseline.',flagged:false};
    if(!m||m.status!=='compared')return {title:'Not enough usable inputs',detail:'Check the voice and wearable panels for the missing or uncertain input.',flagged:false};
    if(m.agreement==='inconclusive')return {title:'No clear combined result',detail:'The indicators do not meet a clear comparison pattern.',flagged:false};
    return {title:'No change flagged',detail:'No alert was triggered from the available inputs.',flagged:false};
  }
  function missionResult(r) {
    if(!r)return 'No analysis yet. Submit an entry or run the crew/cabin check.';
    if(!r.findings.length)return 'No changes flagged from the available inputs. Missing inputs are listed separately.';
    var ids=new Set();r.findings.forEach(function(f){if(f.crew_id)ids.add(f.crew_id);(f.crew_ids||[]).forEach(function(id){ids.add(id);});});
    var cabin=r.findings.some(function(f){return /CABIN|ENVIRONMENTAL|RADIATION/.test(f.code);});
    return r.findings.length+' flags · '+ids.size+' crew members affected'+(cabin?' · Cabin or exposure change detected.':'.')+' See Flagged findings for what changed and what to check.';
  }
  window.AstralResultText={member:memberResult,mission:missionResult,finding:resultCopy};
  function findings() {
    var r = report(); if (!r) return [];
    var all = r.findings.map(function (f, i) {
      var category = /CABIN|ENVIRONMENTAL/.test(f.code) ? 'cabin' : 'crew';
      var ids = Array.isArray(f.crew_ids) ? f.crew_ids.slice() : f.crew_id ? [f.crew_id] : [];
      if (Array.isArray(f.evidence)) f.evidence.forEach(function (e) { if (e.crew_id && !ids.includes(e.crew_id)) ids.push(e.crew_id); });
      return { code: f.code, source: f, key: 'finding-' + i, title: resultCopy(f).title, category: category, ids: ids, message: f.message || 'Review the source evidence.', type: 'finding' };
    });
    r.input_issues.forEach(function (issue, i) {
      var ids = IDS.filter(function (id) { return String(issue.scope).includes(id); });
      all.push({ key: 'issue-' + i, title: ({heart_rate_bpm:'Heart rate',hrv_rmssd_ms:'Pulse variability',eda_microsiemens:'Skin conductance',co2_percent:'Cabin CO₂',o2_percent:'Cabin oxygen',pressure_kpa:'Cabin pressure'}[issue.field] || 'Reading') + ' is ' + (issue.status==='invalid'?'invalid':'missing'), category: 'quality', ids: ids, type: 'quality', message: String(issue.scope || 'Input') + ' · ' + String(issue.field || 'reading') + ' · ' + String(issue.status || 'unavailable') + '. Verify input availability; no normal value was substituted.' });
    });
    (r.multimodal || []).forEach(function (m) {
      if (m.status !== 'compared') all.push({ key: 'model-' + m.crew_id, title: 'Voice and wearable cannot be compared', category: 'quality', ids: [m.crew_id], type: 'quality', message: 'One input is missing, uncertain, or unsuitable for a paired result. Check the member’s Cognitive panel.' });
    });
    return all;
  }
  function memberIndicator(r,id) {
    if(!r)return {tone:'neutral',icon:'…',label:'Not analyzed'};
    var flags=r.findings.filter(function(f){return f.crew_id===id||(f.crew_ids||[]).includes(id);});
    var has=function(code){return flags.some(function(f){return f.code===code;});};
    if(has('BOTH_INDICATORS_ELEVATED'))return {tone:'high',icon:'!',label:'High indicators'};
    if(has('MODALITY_DISAGREEMENT'))return {tone:'caution',icon:'⇄',label:'Conflicting signals'};
    if(has('MOVEMENT_CAUTION'))return {tone:'caution',icon:'≈',label:'Movement detected'};
    if(flags.length)return {tone:'caution',icon:'!',label:'Readings changed'};
    var m=(r.multimodal||[]).find(function(item){return item.crew_id===id;});
    var voice=m&&m.signals&&m.signals.voice;
    if(voice&&voice.raw&&voice.raw.details&&voice.raw.details.nasa_demo)return {tone:'info',icon:'i',label:'Audio features only'};
    if(!m||m.status!=='compared'){
      if(m&&(m.issues||[]).some(function(issue){return /confidence/.test(issue);}))return {tone:'caution',icon:'?',label:'Uncertain signal'};
      return {tone:'info',icon:'?',label:'Check inputs'};
    }
    if(m.agreement==='inconclusive')return {tone:'caution',icon:'?',label:'Inconclusive'};
    return {tone:'clear',icon:'✓',label:'No change flagged'};
  }
  function badge(indicator) {
    var e=node('span','result-indicator result-'+indicator.tone);
    e.dataset.result=indicator.tone;
    var icon=node('span','result-symbol',indicator.icon);icon.setAttribute('aria-hidden','true');
    e.append(icon,node('span','',indicator.label));e.setAttribute('aria-label','Result: '+indicator.label);return e;
  }
  function crewState(id) {
    var indicator=!member(id)?{tone:'info',icon:'?',label:'Reading missing'}:bundle.overview.historical_analysis?{tone:'neutral',icon:'◷',label:'Older reading'}:memberIndicator(report(),id);
    return {label:indicator.label,cls:indicator.tone,indicator:indicator};
  }
  function signalIndicator(signal,source,config) {
    if(!signal||signal.status!=='available')return {tone:'info',icon:'?',label:'Input unavailable'};
    if(source==='voice'&&(!finite(signal.confidence)||signal.confidence<(finite(config.minimum_voice_confidence)?config.minimum_voice_confidence:.5)))return {tone:'caution',icon:'?',label:'Uncertain signal'};
    if(source==='wearable'&&signal.quality&&signal.quality.status==='motion_caution')return {tone:'caution',icon:'≈',label:'Movement detected'};
    var low=finite(config[source+'_low_score'])?config[source+'_low_score']:.4,high=finite(config[source+'_elevated_score'])?config[source+'_elevated_score']:.6;
    if(signal.stress_score>=high)return {tone:'high',icon:'!',label:'High indicator'};
    if(signal.stress_score<=low)return {tone:'clear',icon:'✓',label:'Low indicator'};
    return {tone:'caution',icon:'•',label:'Between bands'};
  }
  window.AstralResultText.indicator=memberIndicator;
  window.AstralResultText.badge=badge;
  function kpi(title, reading, foot) {
    var card = node('article', 'card kpi'); card.append(node('div', 'kpi-top', title), node('div', 'kpi-value', reading), node('div', 'kpi-foot', foot)); return card;
  }
  function navigate(page) {
    document.querySelectorAll('.page').forEach(function (p) { p.classList.toggle('active', p.id === 'page-' + page); });
    document.querySelectorAll('.nav button').forEach(function (b) { b.classList.toggle('active', b.dataset.page === page); });
    requestAnimationFrame(drawCharts);
  }
  function selectCrew(id) { selected = id; renderCrew(); navigate('crew'); }
  function renderMission() {
    var p = payload(), r = report(), flags = findings(), crew = p.crew || [];
    var affected = new Set(); flags.filter(function (f) { return f.category !== 'quality'; }).forEach(function (f) { f.ids.forEach(function (id) { affected.add(id); }); });
    var missingPairs = IDS.filter(function (id) { var m = multimodal(id); return !m || m.status !== 'compared'; }).length;
    $('mission-kpis').replaceChildren(kpi('CREW IN VIEW', crew.length + ' / 5', 'Five explicit crew profiles'), kpi('CREW FLAGGED', r ? String(affected.size) : 'Not analyzed', 'Indicators for human review'), kpi('FLAGS', r ? String(r.findings.length) : 'Unavailable', 'Changes found in crew or cabin inputs'), kpi('INCOMPLETE MODEL PAIRS', String(missingPairs), 'Missing, withheld or unsupported'));
    $('mission-recheck-status').textContent = (bundle.overview.historical_analysis?'Older readings · run a new check. ':'') + missionResult(r);
    $('mission-day-label').textContent = finite(p.mission_day) ? 'MISSION DAY ' + p.mission_day : 'MISSION DAY UNAVAILABLE';
    $('mission-source-label').textContent = sourceLabel;
    $('mission-top-day').textContent = finite(p.mission_day) ? 'MISSION DAY ' + p.mission_day : 'MISSION REPLAY';
    $('mission-timestamp').textContent = snapshot() ? date(snapshot().timestamp) : 'No telemetry loaded';
    $('mission-crew-cards').replaceChildren();
    IDS.forEach(function (id, index) {
      var c = member(id), state = crewState(id), card = node('button', 'card mission-crew-card'); card.type = 'button'; card.dataset.crewId = id;
      card.setAttribute('aria-label', id + ', ' + state.label + ', view health details');
      var top = node('div', 'crew-card-top'), avatar = node('span', 'crew-avatar', String(index + 1).padStart(2, '0')); avatar.style.color = COLORS[index];
      top.append(node('span', 'crew-card-id', id), avatar); card.append(top, node('div', 'crew-card-role', c ? 'Synthetic crew telemetry' : 'Absent from loaded snapshot'));
      var reading = node('div', 'crew-reading', value(c && c.biometrics && c.biometrics.heart_rate_bpm)); if (c && finite(c.biometrics && c.biometrics.heart_rate_bpm)) reading.append(node('small', '', ' bpm'));
      card.append(reading, badge(state.indicator), node('span', 'crew-card-link', 'View health →'));
      card.addEventListener('click', function () { selectCrew(id); }); $('mission-crew-cards').append(card);
    });
    $('mission-cabin-values').replaceChildren(); var env = p.environment || {};
    [['Cabin CO₂', 'co2_percent', '%', 3], ['Oxygen', 'o2_percent', '%', 2], ['Pressure', 'pressure_kpa', 'kPa', 2]].forEach(function (item) {
      var cell = node('div', 'env-item'), reading = node('b', '', value(env[item[1]], item[3])); if (finite(env[item[1]])) reading.append(node('small', '', ' ' + item[2])); cell.append(node('span', '', item[0]), reading); $('mission-cabin-values').append(cell);
    });
    var f = bundle.overview.freshness || {};
    $('mission-freshness-label').textContent = 'Snapshot: ' + (f.status || 'unavailable') + ' · ' + date(snapshot() ? snapshot().timestamp : null) + '. Synthetic input.';
    $('crew-chart-caption').textContent = bundle.snapshot_history.length + ' stored snapshots · actual timestamps in UTC';
    $('mission-crew-legend').replaceChildren(); IDS.forEach(function (id, i) { var e = node('span'), swatch = node('i'); swatch.style.background = COLORS[i]; e.append(swatch, document.createTextNode(id)); $('mission-crew-legend').append(e); });
    var legend=$('result-indicator-key');if(!legend){legend=node('div','result-key');legend.id='result-indicator-key';$('mission-crew-cards').before(legend);}
    legend.replaceChildren();[{tone:'high',icon:'!',label:'High indicators'},{tone:'caution',icon:'⇄',label:'Check / disagreement'},{tone:'info',icon:'?',label:'Input issue'},{tone:'clear',icon:'✓',label:'No change flagged'}].forEach(function(item){legend.append(badge(item));});
    legend.append(node('small','','Demo results · colour is not a medical severity scale.'));
    renderFlagList($('mission-flag-preview'), flags.slice(0, 3));
  }
  function renderFlagList(container, items) {
    container.replaceChildren();
    if (!report()) { empty(container, 'Playback in progress. Cross-check findings appear on the final sample.'); return; }
    if (!items.length) { empty(container, 'No matching flags. Choose a crew member to add an entry, or change the cabin scenario in Mission control.'); return; }
    items.forEach(function (f) {
      var article = node('article', 'flag-item ' + (f.category === 'quality' ? 'quality' : '')), body = node('div'), top = node('div', 'flag-top');
      var title = f.title.charAt(0).toUpperCase() + f.title.slice(1),indicator=f.category==='quality'?{tone:'info',icon:'?',label:'Input issue'}:f.code==='BOTH_INDICATORS_ELEVATED'?{tone:'high',icon:'!',label:'High indicators'}:f.code==='MODALITY_DISAGREEMENT'?{tone:'caution',icon:'⇄',label:'Conflicting signals'}:{tone:'caution',icon:'!',label:'Check readings'}; article.dataset.result=indicator.tone;top.append(node('b','',title),badge(indicator));
      var copy=f.type==='finding'?resultCopy(f.source):{what:f.message,next:'Check the input source or submit a new sample.'};
      body.append(top,node('p','',copy.what),node('p','flag-next','Next: '+copy.next),node('div','flag-meta',f.ids.length?f.ids.join(' · '):'Shared cabin'));
      if (f.type === 'finding') { var detail = node('details', 'evidence-detail'); detail.append(node('summary', '', 'Evidence & limits'), node('p', '', f.message)); body.append(detail); }
      article.append(node('div', 'flag-mark', f.category === 'quality' ? 'i' : '!'), body); container.append(article);
    });
  }
  function renderFlags() {
    var filter = $('mission-flag-filter').value, flags = findings().filter(function (f) { return filter === 'all' || f.category === filter; });
    renderFlagList($('mission-flag-list'), flags);
    $('mission-report-state').textContent = (bundle.overview.historical_analysis?'Older readings · submit a fresh entry. ':'') + missionResult(report());
    $('mission-reviews').replaceChildren(); var entries = (bundle.mission_logs || []).flatMap(function (entry) { return (entry.reviews || []).map(function (review) { return { entry: entry, review: review }; }); });
    if (!entries.length) empty($('mission-reviews'), report()?'No team notes added yet. Analysis is already complete.':'No team notes added yet.');
    entries.forEach(function (item) { var e = node('div', 'review-item'); e.append(node('b', '', 'Analysis ' + item.entry.id + ' · ' + item.review.decision), node('p', '', item.review.note), node('small', 'flag-meta', item.review.reviewer + ' · ' + date(item.review.recorded_at))); $('mission-reviews').append(e); });
  }
  function renderCrew() {
    $('mission-crew-select').replaceChildren(); $('mission-crew-tabs').replaceChildren();
    IDS.forEach(function (id) {
      var option = node('option', '', id); option.value = id; $('mission-crew-select').append(option);
      var button = node('button', 'crew-tab', id); button.type = 'button'; button.setAttribute('aria-pressed', id === selected ? 'true' : 'false'); button.addEventListener('click', function () { selected = id; renderCrew(); requestAnimationFrame(drawCharts); }); $('mission-crew-tabs').append(button);
    }); $('mission-crew-select').value = selected;
    var c = member(selected), state = crewState(selected), vitals = c && c.biometrics || {};
    var summary = node('article', 'card crew-detail-banner'), info = node('div'); info.append(node('h2', '', selected), node('p', '', c ? 'Individual synthetic readings · ' + date(snapshot().timestamp) : 'No reading for this member in the loaded snapshot'));
    summary.append(node('div', 'crew-avatar', selected.slice(-2)), info, badge(state.indicator)); $('crew-detail-summary').replaceChildren(summary);
    $('crew-detail-vitals').replaceChildren(kpi('HEART RATE', value(vitals.heart_rate_bpm), 'bpm · synthetic'), kpi('RMSSD PROXY', value(vitals.hrv_rmssd_ms, 1), 'ms · extraction-dependent'), kpi('SKIN CONDUCTANCE', value(vitals.eda_microsiemens, 2), 'µS · synthetic'), kpi('MODEL COMPARISON', multimodal(selected) ? multimodal(selected).status : 'Unavailable', 'Not a health diagnosis'));
    $('crew-model-evidence').replaceChildren(); var m = multimodal(selected);
    [['voice', 'Voice arousal'], ['wearable', 'Wearable research indicator']].forEach(function (pair) {
      var signal = m && m.signals && m.signals[pair[0]], e = node('div', 'model-evidence'), title = node('div', 'model-title');
      var indicator=signalIndicator(signal,pair[0],m&&m.config||{});title.append(node('span','',pair[1]),badge(indicator));e.append(title);
      e.append(node('div', 'model-score', signal && signal.status === 'available' ? value(signal.stress_score,3)+' / 1' : 'Score unavailable'));
      e.append(node('p', 'model-meaning', signal && signal.score_semantics ? (pair[0] === 'voice' ? 'Voice change from the generated calm reference.' : 'Wearable indicator from pulse, skin conductance and movement.') : 'Check the sample or baseline. Missing data does not mean a normal result.'));
      if (signal) {
        e.append(node('p', '', (signal.model_version || 'Version unavailable') + ' · ' + (signal.input_origin || 'Input unavailable')));
        e.append(node('p', '', pair[0] === 'voice' ? 'Heuristic confidence: ' + value(signal.confidence, 2) : 'Confidence: not calibrated; kept null.'));
        if (signal.issues && signal.issues.length) e.append(node('p', '', signal.issues.join('; ')));
      }
      if(signal&&signal.status==='available'&&finite(signal.stress_score)){
        var meter=node('div','indicator-meter meter-'+indicator.tone);meter.setAttribute('role','meter');meter.setAttribute('aria-label',pair[1]+' demo score');meter.setAttribute('aria-valuemin','0');meter.setAttribute('aria-valuemax','1');meter.setAttribute('aria-valuenow',String(signal.stress_score));
        meter.setAttribute('aria-valuetext',value(signal.stress_score,3)+' out of 1; '+indicator.label+'. Scores have different meanings across models.');var fill=node('span');fill.style.width=(signal.stress_score*100)+'%';meter.append(fill);e.append(meter);
      }
      var technical=node('details','evidence-detail');technical.append(node('summary','','Model details'));Array.from(e.children).slice(3).filter(function(child){return !child.classList.contains('indicator-meter');}).forEach(function(child){technical.append(child);});if(technical.children.length>1)e.append(technical);
      var recorded=signal && signal.raw && signal.raw.details && signal.raw.details.nasa_demo;
      if(recorded && recorded.result && recorded.result.features){
        e.querySelector('.result-indicator').replaceWith(badge({tone:'info',icon:'i',label:'Features extracted'}));
        e.querySelector('.model-score').textContent='Features extracted';
        e.querySelector('.model-meaning').textContent='Audio processed; no matching crew baseline for stress scoring.';
        var features=recorded.result.features,box=node('div','recorded-features');
        box.append(node('p','',recorded.origin),node('b','','Pitch '+value(features.f0_mean_hz,1)+' Hz · TEO '+value(features.teo_log_mean,2)),node('p','','MFCC 1: '+value(features.mfcc_1_mean,2)+' · source label is not a model prediction.'));
        e.append(box);
      }
      $('crew-model-evidence').append(e);
    });
    var radiation = c && c.radiation || {}, gravity = c && c.gravity || {}, longTerm = $('crew-long-term'); longTerm.replaceChildren();
    var rad = node('article', 'card panel'); rad.append(node('h3', '', 'Radiation exposure'), node('div', 'detail-number', value(radiation.dose_equivalent_since_run_start_msv, 4) + (finite(radiation.dose_equivalent_since_run_start_msv) ? ' mSv' : '')), node('p', '', 'Since scenario start · rate ' + value(radiation.dose_equivalent_rate_msv_per_day, 2) + ' mSv/day. Career dose is unavailable. Synthetic exposure accounting, not personal risk.')); longTerm.append(rad);
    var grav = node('article', 'card panel'); grav.append(node('h3', '', 'Gravity-adaptation context'), node('div', 'detail-number', value(gravity.illustrative_bone_density_percent_of_start, 2) + (finite(gravity.illustrative_bone_density_percent_of_start) ? '% of start' : '')), node('p', '', 'Illustrative trend only · ' + value(gravity.microgravity_exposure_days) + ' exposure days. Measured bone density and cardiovascular assessment are unavailable.')); longTerm.append(grav);
    var medical = node('article', 'card panel'), incidents = (bundle.medical_incidents || []).filter(function (i) { return i.crew_id === selected; }); medical.append(node('h3', '', 'Medical-support records'), node('p', '', incidents.length + ' incident records in this export. ' + (bundle.medical_resources && bundle.medical_resources.availability === 'available' ? 'Reviewed resources are listed in the export.' : 'No reviewed medical checklist content is available.'))); longTerm.append(medical);
    renderFlagList($('crew-detail-flags'), findings().filter(function (f) { return f.ids.includes(selected) || f.category === 'cabin'; }));
    $('crew-detail-chart-caption').textContent = 'Stored readings · gaps preserved';
    var entryBadge=$('member-result-indicator');if(!entryBadge){entryBadge=node('div','entry-result-indicator');entryBadge.id='member-result-indicator';$('member-checkin-result').before(entryBadge);}entryBadge.replaceChildren(badge(state.indicator));
    renderTable();
    renderModules();
  }
  function renderModules() {
    var names = [['cognitive','Cognitive · voice & wearable'],['habitat','Habitat'],['radiation','Radiation'],['gravity','Gravity adaptation'],['medical','Medical support']];
    var tabs = $('crew-module-tabs'); tabs.replaceChildren();
    names.forEach(function(pair) { var b=node('button','crew-tab',pair[1]); b.type='button'; b.setAttribute('aria-pressed',String(activeModule===pair[0])); b.onclick=function(){activeModule=pair[0];renderModules();animateCharts();};tabs.append(b); });
    var grid=$('crew-detail-chart').closest('.main-grid'); grid.hidden=activeModule!=='cognitive';
    $('crew-detail-vitals').hidden=activeModule!=='cognitive';
    var cards=Array.from($('crew-long-term').children);
    cards.slice(0,3).forEach(function(card,i){card.hidden=activeModule!==['radiation','gravity','medical'][i];});
    var habitat=$('crew-habitat-module');
    if(!habitat){habitat=node('article','card panel');habitat.id='crew-habitat-module';$('crew-long-term').append(habitat);}
    habitat.hidden=activeModule!=='habitat';habitat.replaceChildren(node('h3','',selected+' · Shared habitat'));
    var env=payload().environment||{};
    [['CO₂','co2_percent','%'],['Oxygen','o2_percent','%'],['Pressure','pressure_kpa','kPa']].forEach(function(p){habitat.append(node('div','detail-number',p[0]+': '+value(env[p[1]],3)+' '+p[2]));});
    habitat.append(node('p','','Cabin measurements are shared by all five crew members. Individual exposure and symptoms require review.'));
    document.dispatchEvent(new CustomEvent('astral-crew-selected',{detail:selected}));
  }
  function metricValue(row, id, metric) { var c = member(id, row.payload); return c ? metric === 'radiation' ? c.radiation && c.radiation.dose_equivalent_since_run_start_msv : c.biometrics && c.biometrics[metric] : null; }
  function history() { return bundle.snapshot_history.slice().sort(function (a, b) { return Date.parse(a.timestamp) - Date.parse(b.timestamp) || a.id - b.id; }); }
  function renderTable() {
    var metric = $('crew-detail-metric').value, table = node('table'), head = node('thead'), tr = node('tr');
    ['Timestamp (UTC)', $('crew-detail-metric').selectedOptions[0].textContent].forEach(function (label) { tr.append(node('th', '', label)); }); head.append(tr); table.append(head); var body = node('tbody');
    history().forEach(function (row) { var tr = node('tr'), v = metricValue(row, selected, metric); tr.append(node('td', '', date(row.timestamp)), node('td', '', finite(v) ? String(v) : 'Unavailable')); body.append(tr); }); table.append(body); $('crew-detail-table').replaceChildren(table);
  }
  function plot(canvas, rows, series, unit, reveal) {
    var rect = canvas.getBoundingClientRect(); if (!rect.width || !rect.height) return;
    var dpr = window.devicePixelRatio || 1; canvas.width = Math.round(rect.width * dpr); canvas.height = Math.round(rect.height * dpr);
    var ctx = canvas.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); var w = rect.width, h = rect.height, pad = { l: 43, r: 24, t: 19, b: 28 };
    ctx.clearRect(0, 0, w, h); var values = series.flatMap(function (s) { return rows.map(s.read).filter(finite); });
    canvas.dataset.sampleCount = String(rows.length); canvas.dataset.numericValues = JSON.stringify(series.map(function (s) { return rows.map(s.read).map(function (v) { return finite(v) ? v : null; }); }));
    if (!values.length) { ctx.fillStyle = '#9aacc0'; ctx.font = '12px system-ui'; ctx.fillText('No available readings for this chart.', 12, 35); return; }
    var min = Math.min.apply(null, values), max = Math.max.apply(null, values), spread = max - min;
    var margin = spread ? spread * 0.16 : Math.max(Math.abs(max) * 0.05, unit === 'mSv' ? 0.001 : 0.01); min -= margin; max += margin;
    var times = rows.map(function (r) { return Date.parse(r.timestamp); }), first = Math.min.apply(null, times), last = Math.max.apply(null, times);
    var x = function (i) { return first === last ? (pad.l + w - pad.r) / 2 : pad.l + (times[i] - first) / (last - first) * (w - pad.l - pad.r); }, y = function (v) { return pad.t + (max - v) / (max - min) * (h - pad.t - pad.b); };
    ctx.font = '10px system-ui'; ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
    for (var t = 0; t <= 3; t++) { var v = min + (max - min) * t / 3, py = y(v); ctx.strokeStyle = 'rgba(152,176,201,.13)'; ctx.beginPath(); ctx.moveTo(pad.l, py); ctx.lineTo(w - pad.r, py); ctx.stroke(); ctx.fillStyle = '#8295a9'; ctx.fillText(v.toFixed(Math.abs(v) < 1 ? 3 : 1), pad.l - 7, py); }
    ctx.save(); ctx.beginPath(); ctx.rect(pad.l - 4, 0, (w - pad.l - pad.r + 8) * reveal, h - pad.b + 7); ctx.clip();
    series.forEach(function (s) { var connected = false; ctx.beginPath(); rows.forEach(function (row, i) { var v = s.read(row); if (!finite(v)) { connected = false; return; } if (connected) ctx.lineTo(x(i), y(v)); else ctx.moveTo(x(i), y(v)); connected = true; }); ctx.strokeStyle = s.color; ctx.lineWidth = 2; ctx.stroke(); rows.forEach(function (row, i) { var v = s.read(row); if (!finite(v)) return; ctx.beginPath(); ctx.arc(x(i), y(v), 3, 0, Math.PI * 2); ctx.fillStyle = s.color; ctx.fill(); }); });
    ctx.restore();
    ctx.fillStyle = '#8295a9'; ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left'; ctx.fillText(clock(rows[0].timestamp), pad.l, h - 7); ctx.textAlign = 'right'; ctx.fillText(clock(rows[rows.length - 1].timestamp) + ' UTC', w - pad.r, h - 7);
    canvas.setAttribute('aria-label', rows.length + ' stored snapshots. ' + series.map(function (s) { return s.name + ': ' + rows.map(s.read).map(function (v) { return finite(v) ? v + ' ' + unit : 'unavailable'; }).join(', '); }).join('. '));
  }
  function drawCharts(reveal) {
    reveal = typeof reveal === 'number' ? Math.max(0, Math.min(1, reveal)) : 1;
    var rows = history();
    plot($('mission-crew-chart'), rows, IDS.map(function (id, i) { return { name: id, color: COLORS[i], read: function (r) { return metricValue(r, id, 'heart_rate_bpm'); } }; }), 'bpm', reveal);
    var cabinMetric = $('cabin-chart-metric').value, unit = cabinMetric === 'pressure_kpa' ? 'kPa' : '%';
    plot($('mission-cabin-chart'), rows, [{ name: cabinMetric, color: '#8daeff', read: function (r) { return r.payload.environment && r.payload.environment[cabinMetric]; } }], unit, reveal);
    var metric = $('crew-detail-metric').value, units = { heart_rate_bpm: 'bpm', hrv_rmssd_ms: 'ms', eda_microsiemens: 'µS', radiation: 'mSv' };
    $('crew-detail-chart-title').textContent = selected + ' · ' + $('crew-detail-metric').selectedOptions[0].textContent;
    plot($('crew-detail-chart'), rows, [{ name: selected, color: COLORS[IDS.indexOf(selected)], read: function (r) { return metricValue(r, selected, metric); } }], units[metric], reveal);
  }
  var animationFrame = null;
  function animateCharts() {
    if (animationFrame) cancelAnimationFrame(animationFrame);
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { drawCharts(1); return; }
    var started = performance.now();
    function step(now) { var progress = Math.min(1, (now - started) / 650); drawCharts(1 - Math.pow(1 - progress, 3)); if (progress < 1) animationFrame = requestAnimationFrame(step); }
    animationFrame = requestAnimationFrame(step);
  }
  function render() { renderMission(); renderCrew(); renderFlags(); requestAnimationFrame(animateCharts); document.dispatchEvent(new Event('astral-data-changed')); }
  $('mission-crew-select').addEventListener('change', function () { selected = this.value; renderCrew(); requestAnimationFrame(drawCharts); });
  $('crew-detail-metric').addEventListener('change', function () { renderTable(); animateCharts(); });
  $('cabin-chart-metric').addEventListener('change', animateCharts);
  $('mission-flag-filter').addEventListener('change', renderFlags);
  document.querySelectorAll('.nav button,[data-go]').forEach(function (b) { b.addEventListener('click', function () { requestAnimationFrame(animateCharts); }); });
  document.querySelector('.local-preview').addEventListener('toggle', function () { window.dispatchEvent(new Event('resize')); });
  window.addEventListener('resize', function () { requestAnimationFrame(drawCharts); });
  $('mission-import').addEventListener('change', async function () {
    var file = this.files[0]; if (!file) return;
    try {
      if (file.size > 2 * 1024 * 1024) throw Error('Choose a JSON bundle smaller than 2 MB.');
      var next = validate(JSON.parse(await file.text()));
      var previousBundle = bundle, previousLabel = sourceLabel;
      bundle = next; sourceLabel = file.name;
      try { render(); } catch (renderError) { bundle = previousBundle; sourceLabel = previousLabel; render(); throw renderError; }
      $('mission-import-message').className = 'import-message'; $('mission-import-message').textContent = 'Loaded offline export. This does not start a live connection.';
    } catch (error) { $('mission-import-message').className = 'import-message error'; $('mission-import-message').textContent = 'Could not load file: ' + error.message + ' Previous replay retained.'; }
    this.value = '';
  });
  $('mission-reset').addEventListener('click', function () { bundle = defaultBundle; sourceLabel = 'Bundled backend replay'; selected = 'AST-01'; $('mission-import-message').className = 'import-message'; $('mission-import-message').textContent = 'Bundled synthetic replay restored.'; render(); });
  window.AstralMissionView = {
    load: function (input, label) { var next = validate(input); bundle = next; sourceLabel = label || 'Local backend'; render(); },
    current: function () { return JSON.parse(JSON.stringify(bundle)); }
  };
  $('page-flagged').querySelector('h1').textContent='What changed?';
  var reviewTitle=document.querySelector('.review-panel .panel-title');if(reviewTitle)reviewTitle.textContent='Add a team note and decision';
  validate(bundle); render();
})();
