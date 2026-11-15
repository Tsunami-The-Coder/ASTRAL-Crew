(function(){
'use strict';var $=function(id){return document.getElementById(id);},blobURL=null;
document.addEventListener('astral-public-demo',function(){
  ['lab-voice','lab-wearable'].forEach(function(id){
    var select=$(id),option=select.querySelector('option[value="upload"]');
    if(option){if(select.value==='upload')select.value=select.options[0].value;option.remove();select.dispatchEvent(new Event('change'));}
  });
  $('lab-uploads').hidden=true;$('lab-wrist-upload').hidden=true;
});
$('lab-voice').onchange=function(){var upload=this.value==='upload';$('lab-uploads').hidden=!upload;if(!upload)$('lab-audio').src=this.value.startsWith('artemis-')?'/submission-assets/audio/'+this.value+'.wav':'/api/lab/audio/'+this.value;else{$('lab-audio').removeAttribute('src');$('lab-audio').load();}};
$('lab-wearable').onchange=function(){$('lab-wrist-upload').hidden=this.value!=='upload';};
$('lab-wav').onchange=function(){if(blobURL)URL.revokeObjectURL(blobURL);if(this.files[0]){$('lab-audio').src=blobURL=URL.createObjectURL(this.files[0]);}};
function encoded(file){return new Promise(function(resolve,reject){var r=new FileReader();r.onload=function(){resolve(r.result.split(',')[1]);};r.onerror=reject;r.readAsDataURL(file);});}
async function run(kind){
 var button=$('lab-run-'+kind),out=$('lab-'+kind+'-result');button.disabled=true;out.classList.add('processing');out.textContent='Sending sample → extracting features → running pipeline…';
 try{
  var sample=$('lab-'+kind).value,body={kind:kind,sample:sample};
  if(sample==='upload'&&kind==='voice'){
   var baselines=Array.from($('lab-baseline').files),test=$('lab-wav').files[0];
   if(!test||baselines.length<5||baselines.length>10)throw Error('Choose 5–10 calm WAVs and one test WAV from the same speaker.');
   if(baselines.concat([test]).reduce(function(n,f){return n+f.size;},0)>4*1024*1024)throw Error('Keep combined WAV files below 4 MB.');
   body.baseline_wavs=await Promise.all(baselines.map(encoded));body.test_wav=await encoded(test);
  }
  if(sample==='upload'&&kind==='wearable'){var f=$('lab-signals').files[0];if(!f||f.size>1024*1024)throw Error('Choose a signal JSON below 1 MB.');body.signals=JSON.parse(await f.text());}
  var response=await fetch('/api/lab/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),data=await response.json();if(!response.ok)throw Error(data.error);
  out.replaceChildren();var h=document.createElement('b');h.textContent='✓ Pipeline returned · '+data.origin;out.append(h);
  var result=data.result,record=result.record||result,details=result.details||result;
  var p=document.createElement('p');var score=record.stress_score;
  p.textContent=(details.status||'Complete')+' · '+(typeof score==='number'?'Indicator: '+score.toFixed(3):'No score: '+(details.reason||((details.quality||{}).issues||[]).join(', ')||'input unavailable'));out.append(p);
  if(details.features){var grid=document.createElement('div');grid.className='lab-feature-grid';[['Pitch','f0_mean_hz','Hz'],['Pitch spread','f0_std_hz','Hz'],['Teager energy','teo_log_mean','log scale'],['MFCC 1','mfcc_1_mean','coefficient']].forEach(function(item){var cell=document.createElement('div'),v=details.features[item[1]];cell.textContent=item[0]+': '+(typeof v==='number'?v.toFixed(2):'unavailable')+' '+item[2];grid.append(cell);});out.append(grid);}
  if(data.source){var credit=document.createElement('p');credit.textContent=data.source.title+' · Credit: NASA · first 15 seconds';out.append(credit);}
  var steps=document.createElement('ol');data.steps.forEach(function(step){var li=document.createElement('li');li.textContent=step;steps.append(li);});out.append(steps);
  if(data.features){var metrics=document.createElement('p');metrics.textContent=Object.entries(data.features).map(function(pair){return pair[0]+': '+(typeof pair[1]==='number'?pair[1].toFixed(2):'missing');}).join(' · ');out.append(metrics);}
  var scope=document.createElement('p');scope.textContent=data.scope;out.append(scope);
  var more=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent='Inspect actual backend output';pre.textContent=JSON.stringify(data,null,2);more.append(summary,pre);out.append(more);
 }catch(error){out.textContent='Test could not complete: '+error.message;}
 finally{button.disabled=false;out.classList.remove('processing');}
}
$('lab-run-voice').onclick=function(){run('voice');};$('lab-run-wearable').onclick=function(){run('wearable');};
$('lab-cross').onclick=function(){document.querySelector('.nav [data-page="overview"]').click();$('demo-scenario').value='co2_rise';$('demo-run').click();};
})();
