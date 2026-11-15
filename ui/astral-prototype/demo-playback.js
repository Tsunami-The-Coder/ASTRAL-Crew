/* Playback of stored synthetic samples; final analysis is never applied to earlier frames. */
(function(){
'use strict';
var view=window.AstralMissionView, full=view.current(), timer=null, frame=11, painting=false;
var $=function(id){return document.getElementById(id);};
function stop(){clearTimeout(timer);timer=null;$('demo-play').textContent='▶ Replay readings';}
function show(index){
  var rows=full.snapshot_history.slice().sort(function(a,b){return Date.parse(a.timestamp)-Date.parse(b.timestamp);});
  if(!rows.length)return;
  frame=Math.max(0,Math.min(index,rows.length-1));
  $('demo-timeline').max=rows.length-1;$('demo-timeline').value=frame;
  $('demo-frame').textContent=(frame+1)+' / '+rows.length+' samples';
  var next=JSON.parse(JSON.stringify(full));
  if(frame<rows.length-1){next.overview.snapshot=rows[frame];next.snapshot_history=rows.slice(0,frame+1);next.overview.current_analysis=null;next.overview.historical_analysis=null;next.mission_logs=[];delete next.demo_server;}
  painting=true;view.load(next,'Synthetic scenario playback');painting=false;
  $('demo-play-state').textContent=frame===rows.length-1?'Complete · backend cross-check results ready':'Playing stored samples · analysis shown at completion';
  // Playback is a viewer: generating another scenario remains available.
  $('demo-run').disabled=false;
}
function advance(){show(frame+1);if(frame<full.snapshot_history.length-1)timer=setTimeout(advance,850);else stop();}
$('demo-play').onclick=function(){if(timer){stop();return;}show(0);$('demo-play').textContent='Ⅱ Pause replay';timer=setTimeout(advance,850);};
$('demo-timeline').oninput=function(){stop();show(Number(this.value));};
document.addEventListener('astral-data-changed',function(){if(painting)return;stop();full=view.current();frame=full.snapshot_history.length-1;$('demo-timeline').max=frame;$('demo-timeline').value=frame;$('demo-frame').textContent=(frame+1)+' / '+(frame+1)+' samples';});
document.addEventListener('astral-demo-generated',function(event){stop();full=event.detail;show(0);$('demo-play').textContent='Ⅱ Pause replay';timer=setTimeout(advance,850);});
})();
