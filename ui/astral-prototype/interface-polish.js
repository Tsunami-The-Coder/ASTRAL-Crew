/* Native dark select controls retain platform keyboard and screen-reader behavior. */
(function(){
 'use strict';
 document.querySelectorAll('select').forEach(function(select){
  if(select.hasAttribute('aria-label')||select.labels.length)return;
  var label=select.closest('label');
  if(label)select.setAttribute('aria-label',Array.from(label.childNodes).filter(function(n){return n.nodeType===3;}).map(function(n){return n.textContent.trim();}).join(' '));
 });
})();
