/* Optional UI composes existing views; all analysis remains in the local backend. */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const view = window.AstralMissionView;
  const names = {about:'method',hazards:'mission-hazards',overview:'mission-control',flagged:'flagged-findings',sources:'sources'};
  const ids = ['AST-01','AST-02','AST-03','AST-04','AST-05'];
  const el = (tag, className, text) => {const n=document.createElement(tag);if(className)n.className=className;if(text!==undefined)n.textContent=text;return n;};
  const icon = name => {const n=el('i','ph ph-'+name);n.setAttribute('aria-hidden','true');return n;};
  let currentPage='about', selectedFinding=null;

  function closeMenu(){
    const side=document.querySelector('.side');side.classList.remove('nav-open');
    const mobile=matchMedia('(max-width:700px)').matches;side.inert=mobile;
    side.setAttribute('aria-hidden',String(mobile));
    $('menu-toggle').setAttribute('aria-expanded','false');
    $('menu-toggle').setAttribute('aria-label','Open navigation');
    $('main-content').inert=false;
  }
  function pageState(page){
    currentPage=page;
    document.querySelectorAll('.nav button').forEach(button=>{
      if(button.dataset.page===page)button.setAttribute('aria-current','page');
      else button.removeAttribute('aria-current');
    });
    closeMenu();
    window.dispatchEvent(new Event('resize'));
  }
  function navigate(page, focus){
    if(page==='crew'||page==='biology')page='overview';
    if(!Object.hasOwn(names,page))page='overview';
    document.querySelectorAll('.page').forEach(p=>p.classList.toggle('active',p.id==='page-'+page));
    document.querySelectorAll('.nav button').forEach(b=>b.classList.toggle('active',b.dataset.page===page));
    history.replaceState(null,'','#'+names[page]);
    pageState(page);
    document.dispatchEvent(new CustomEvent('astral-page-changed',{detail:page}));
    if(focus){const heading=$('page-'+page).querySelector('h1');heading.setAttribute('tabindex','-1');heading.focus({preventScroll:true});window.scrollTo({top:0,behavior:'instant'});}
  }
  window.AstralNavigate=navigate;
  document.addEventListener('astral-page-changed',event=>pageState(event.detail));
  document.querySelectorAll('[data-page],[data-go]').forEach(button=>button.addEventListener('click',()=>navigate(button.dataset.page||button.dataset.go,true)));
  $('menu-toggle').addEventListener('click',()=>{
    const open=!document.querySelector('.side').classList.contains('nav-open');
    if(!open){closeMenu();return;}
    document.querySelector('.side').classList.add('nav-open');
    document.querySelector('.side').inert=false;document.querySelector('.side').setAttribute('aria-hidden','false');
    $('menu-toggle').setAttribute('aria-expanded','true');$('menu-toggle').setAttribute('aria-label','Close navigation');
    $('main-content').inert=true;document.querySelector('.nav button.active').focus();
  });
  document.addEventListener('keydown',event=>{
    if(!document.querySelector('.side').classList.contains('nav-open'))return;
    if(event.key==='Escape'){closeMenu();$('menu-toggle').focus();}
    if(event.key==='Tab'){
      const buttons=[$('menu-toggle'),...document.querySelectorAll('.nav button')];
      const first=buttons[0],last=buttons[buttons.length-1];
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
    }
  });
  window.matchMedia('(min-width:701px)').addEventListener('change',closeMenu);
  window.addEventListener('hashchange',()=>navigate(Object.keys(names).find(k=>names[k]===location.hash.slice(1))||'about'));

  function updateCrew(){
    const id=$('mission-crew-select').value||'AST-01';
    $('evidence-selected-title').textContent=id+' · Last saved analysis';
    $('crew-previous').disabled=$('member-voice').disabled;
    $('crew-next').disabled=$('member-voice').disabled;
    document.querySelectorAll('#mission-crew-tabs button').forEach(button=>{
      if(button.getAttribute('aria-pressed')==='true')button.setAttribute('aria-current','true');else button.removeAttribute('aria-current');
    });
  }
  function switchCrew(delta){const current=ids.indexOf($('mission-crew-select').value);view.selectCrew(ids[(current+delta+ids.length)%ids.length]);}
  $('crew-previous').addEventListener('click',()=>switchCrew(-1));
  $('crew-next').addEventListener('click',()=>switchCrew(1));
  $('open-mission-tools').addEventListener('click',()=>{$('mission-overview').open=true;$('mission-overview').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});window.dispatchEvent(new Event('resize'));});
  $('mission-overview').addEventListener('toggle',()=>window.dispatchEvent(new Event('resize')));
  $('research-expand').addEventListener('click',()=>{
    const expanded=!$('research-details').open;$('research-details').open=expanded;
    $('page-biology').classList.toggle('expanded',expanded);$('research-expand').setAttribute('aria-expanded',String(expanded));
    $('research-expand').replaceChildren(document.createTextNode(expanded?'Collapse research ':'Expand research '),icon(expanded?'arrows-in':'arrow-up-right'));
    window.dispatchEvent(new Event('resize'));
  });
  $('research-details').addEventListener('toggle',()=>{$('research-expand').setAttribute('aria-expanded',String($('research-details').open));});

  const stages=[
    {title:'Choose inputs, then review a draft',copy:'Select a voice sample and a 60-second wearable window. Generate synthetic readings, inspect the draft, and submit only when ready.',tags:'VOICE + WRIST · DRAFT READINGS'},
    {title:'Extract features, preserve uncertainty',copy:'Voice processing extracts speech quality, pitch, MFCCs and Teager energy. Wrist processing extracts pulse, RMSSD proxy, skin conductance and motion. Missing signals remain explicit.',tags:'ACTUAL PYTHON PIPELINES · QUALITY CHECKS'},
    {title:'Compare evidence in context',copy:'Review each member against their reference, then inspect voice and wearable agreement alongside shared cabin changes. The scores retain their separate meanings.',tags:'PERSONAL REFERENCE · CREW + CABIN'},
    {title:'Save results and record a human review',copy:'Timestamped entries and snapshot-linked findings are saved locally. A person reviews the evidence and records what should be verified next.',tags:'SQLITE HISTORY · HUMAN REVIEW'}
  ];
  let stageIndex=1;
  function stage(index){stageIndex=index;const data=stages[index];$('method-title').textContent=data.title;$('method-copy').textContent=data.copy;$('method-tags').textContent=data.tags;document.querySelectorAll('#method-stages button').forEach((b,i)=>{b.classList.toggle('active',i===index);b.setAttribute('aria-pressed',String(i===index));});$('method-visual').dataset.stage=String(index);}
  document.querySelectorAll('#method-stages button').forEach((b,i)=>b.addEventListener('click',()=>stage(i)));
  $('method-next').addEventListener('click',()=>stage((stageIndex+1)%stages.length));stage(1);

  const hazards=[
    {title:'Understand simulated exposure.',description:'Dose accumulation and rate changes provide mission context for review.',shows:'Illustrative dose accounting and radiation-rate trends.',limit:'Personal exposure, health risk, or real dosimetry.',module:'radiation',label:'Radiation'},
    {title:'Review indicators in context.',description:'Voice and wearable observations can prompt a closer look at recent activity.',shows:'Separate voice and wearable research indicators.',limit:'A psychological condition, its cause, or fitness for duty.',module:'cognitive',label:'Cognitive'},
    {title:'Keep the next step reviewable.',description:'Communication delays make accessible local records and human review useful.',shows:'Saved entries, source-linked analyses and team notes.',limit:'Autonomous treatment or an emergency procedure.',module:'medical',label:'Medical support'},
    {title:'Explore an illustrative adaptation trend.',description:'The gravity module provides context for a simulated long-duration mission.',shows:'Illustrative bone trend and exposure duration.',limit:'Measured bone density or individual physiological adaptation.',module:'gravity',label:'Gravity adaptation'},
    {title:'The cabin is a shared input.',description:'CO₂, oxygen and pressure provide context for crew changes.',shows:'Synthetic cabin readings and trends.',limit:'Cause, diagnosis, or spacecraft safety.',module:'habitat',label:'Habitat'}
  ];
  let hazardIndex=4;
  function hazard(index){hazardIndex=index;const h=hazards[index];$('hazard-title').textContent=h.title;$('hazard-description').textContent=h.description;$('hazard-shows').textContent=h.shows;$('hazard-limit').textContent=h.limit;$('hazard-open-module').replaceChildren(document.createTextNode('Open '+h.label+' in Mission Control '),icon('arrow-right'));document.querySelectorAll('#hazard-menu button').forEach((b,i)=>b.setAttribute('aria-pressed',String(index===i)));}
  document.querySelectorAll('#hazard-menu button').forEach((b,i)=>b.addEventListener('click',()=>hazard(i)));
  $('hazard-open-module').addEventListener('click',()=>{navigate('overview',true);view.setModule(hazards[hazardIndex].module);$('page-crew').scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});});hazard(4);

  function tone(f){return f.category==='quality'?'info':f.code==='BOTH_INDICATORS_ELEVATED'?'high':'caution';}
  function copy(f){return f.type==='finding'?view.findingCopy(f.source):{what:f.message,next:'Check the input source or submit a new sample.'};}
  function findingDetail(f){
    const container=$('finding-detail-content');container.replaceChildren();
    if(!f){container.append(el('h2','','No matching findings'),el('p','finding-what','Review a different filter, or open Mission Control to generate and analyze an entry.'));return;}
    container.append(el('h2','',f.title),el('p','finding-status',(f.ids.length?f.ids.join(' · '):'Shared cabin')+' · '+(f.category==='quality'?'Input issue':f.code==='BOTH_INDICATORS_ELEVATED'?'High indicators':'Check readings')));
    const c=copy(f);container.append(el('p','finding-what',c.what));
    const data=view.current(),analysis=data.overview.current_analysis||data.overview.historical_analysis;
    if(f.ids.length===1){
      const member=analysis&&(analysis.report.multimodal||[]).find(m=>m.crew_id===f.ids[0]);
      if(member){const pair=el('div','evidence-pair');for(const [key,label] of [['voice','Voice input'],['wearable','Wearable input']]){const signal=member.signals&&member.signals[key],cell=el('div');let text='Unavailable';if(signal&&signal.status==='available'&&Number.isFinite(signal.stress_score))text=signal.stress_score.toFixed(3)+' / 1';else if(signal)text=signal.status==='missing'?'Missing input':signal.status.replaceAll('_',' ');cell.append(el('small','',label),el('strong','',text));pair.append(cell);}container.append(pair);}
    }
    const next=el('div','next-check');next.append(icon('info'),el('b','',c.next));container.append(next);
    if(f.ids.length){const button=el('button','text-button finding-crew-link','Open '+f.ids[0]+' in Mission Control ');button.append(icon('arrow-right'));button.addEventListener('click',()=>{view.selectCrew(f.ids[0]);view.setModule('cognitive');navigate('overview',true);});container.append(button);}
    const details=el('details','evidence-detail');details.open=true;details.append(el('summary','','Evidence & limitations'),el('p','',f.message),el('p','','These demo comparison bands do not establish a diagnosis. Missing input is not a normal result.'));container.append(details);
  }
  function renderFindings(){
    const filter=$('mission-flag-filter').value,all=view.findings(),items=all.filter(f=>filter==='all'||f.category===filter),list=$('mission-flag-list');list.replaceChildren();
    if(!items.some(f=>f.key===selectedFinding))selectedFinding=(items.find(f=>f.category==='quality')||items[0]||{}).key;
    if(!items.length)list.append(el('p','empty-state','No matching findings from the available inputs.'));
    for(const f of items){const button=el('button','finding-choice');button.type='button';button.dataset.tone=tone(f);button.setAttribute('aria-pressed',String(f.key===selectedFinding));const body=el('span');body.append(el('b','',f.title),el('small','',copy(f).what),el('small','choice-ids',f.ids.join(' · ')||'Shared cabin'));button.append(icon(f.category==='quality'?'info':'warning'),body,icon('caret-right'));button.addEventListener('click',()=>{selectedFinding=f.key;renderFindings();});list.append(button);}
    findingDetail(items.find(f=>f.key===selectedFinding));
  }
  $('mission-flag-filter').addEventListener('change',renderFindings);
  function connection(){
    if($('demo-review-status').textContent.startsWith('Complete a demo run')&&view.current().overview.current_analysis)$('demo-review-status').textContent='Your review will be linked to this snapshot and analysis.';
    $('sidebar-connection').textContent=window.AstralBackendConnected?'Local pipelines connected':'Backend unavailable · replay';
    $('sidebar-connection').parentElement.dataset.connected=String(!!window.AstralBackendConnected);
  }
  document.addEventListener('astral-crew-selected',updateCrew);
  document.addEventListener('astral-data-changed',()=>{updateCrew();renderFindings();connection();});
  document.addEventListener('astral-connection-changed',connection);
  updateCrew();renderFindings();connection();
  document.fonts.ready.then(()=>window.dispatchEvent(new Event('resize')));
  navigate(Object.keys(names).find(k=>names[k]===location.hash.slice(1))||'about');
})();
