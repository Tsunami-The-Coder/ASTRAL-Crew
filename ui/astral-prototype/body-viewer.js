/* Three.js viewer of MakeHuman's CC0 body surface. Illustrative, never medical data. */
import * as THREE from 'three';
const container=document.getElementById('body-viewport'),toggle=document.getElementById('body-rotation'),message=document.getElementById('body-load-status');
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
let rotating=!reduced.matches,dragging=false,lastX=0,lastTime=0,visible=false,renderer;
const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(34,1,.01,100),pivot=new THREE.Group();
camera.position.set(0,1.04,3.8);camera.lookAt(0,.98,0);scene.add(pivot);
function control(){const icon=document.createElement('i');icon.className='ph ph-'+(rotating?'pause':'play');icon.setAttribute('aria-hidden','true');toggle.replaceChildren(icon,document.createTextNode(rotating?' Pause rotation':' Resume rotation'));toggle.setAttribute('aria-pressed',String(rotating));}
function resize(){if(!renderer)return;const {width,height}=container.getBoundingClientRect();if(width<1||height<1)return;camera.aspect=width/height;camera.updateProjectionMatrix();renderer.setSize(width,height,false);renderer.render(scene,camera);}
try{
 renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'low-power'});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.domElement.setAttribute('aria-hidden','true');container.append(renderer.domElement);
 scene.add(new THREE.AmbientLight(0x9cc9da,.7));const light=new THREE.DirectionalLight(0x7af0e1,1.8);light.position.set(-2,3,3);scene.add(light);
 fetch('./vendor/human-wireframe.json',{cache:'force-cache'}).then(response=>{if(!response.ok)throw Error('Model unavailable');return response.json();}).then(data=>{
  const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(data.positions,3));geometry.setIndex(data.triangles);geometry.computeVertexNormals();geometry.computeBoundingSphere();
  const surface=new THREE.Mesh(geometry,new THREE.MeshPhongMaterial({color:0x061b24,specular:0x163f43,shininess:12,polygonOffset:true,polygonOffsetFactor:1,polygonOffsetUnits:1}));
  // Original quadrilateral loops wrap the mesh, without diagonal triangle lines.
  const edges=new THREE.BufferGeometry();edges.setAttribute('position',geometry.getAttribute('position'));edges.setIndex(data.edges);const grid=new THREE.LineSegments(edges,new THREE.LineBasicMaterial({color:0x62e0cf,transparent:true,opacity:.62}));grid.renderOrder=1;
  pivot.add(surface,grid);pivot.rotation.y=-.28;message.hidden=true;container.dataset.model='ready';resize();
 }).catch(()=>{message.textContent='The body model could not load. Entry and evidence controls remain available.';container.dataset.model='unavailable';toggle.disabled=true;});
 const ring=new THREE.Mesh(new THREE.RingGeometry(.51,.514,96),new THREE.MeshBasicMaterial({color:0x276b70,side:THREE.DoubleSide,transparent:true,opacity:.65}));ring.rotation.x=-Math.PI/2;ring.position.y=-.012;scene.add(ring);
 const ground=new THREE.GridHelper(1,10,0x1d4b55,0x14343e);ground.position.y=-.015;ground.material.transparent=true;ground.material.opacity=.35;scene.add(ground);
 renderer.setAnimationLoop(time=>{const delta=Math.min((time-lastTime)/1000,.05);lastTime=time;if(visible&&!document.hidden&&rotating&&!dragging){pivot.rotation.y+=delta*.18;renderer.render(scene,camera);}});
 new ResizeObserver(resize).observe(container);new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;resize();}).observe(container);
 container.addEventListener('pointerdown',event=>{if(event.button!==0)return;dragging=true;lastX=event.clientX;container.setPointerCapture(event.pointerId);});
 container.addEventListener('pointermove',event=>{if(dragging){pivot.rotation.y+=(event.clientX-lastX)*.009;lastX=event.clientX;renderer.render(scene,camera);}});
 for(const event of ['pointerup','pointercancel','lostpointercapture'])container.addEventListener(event,()=>{dragging=false;});
 container.addEventListener('keydown',event=>{if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();pivot.rotation.y+=(event.key==='ArrowRight'?1:-1)*.14;renderer.render(scene,camera);}});
 renderer.domElement.addEventListener('webglcontextlost',event=>{event.preventDefault();message.hidden=false;message.textContent='3D display paused. Reload to restore it; entry controls remain available.';});
 toggle.addEventListener('click',()=>{rotating=!rotating;control();});reduced.addEventListener('change',()=>{rotating=!reduced.matches;control();});window.addEventListener('resize',resize);document.addEventListener('astral-page-changed',resize);control();resize();
}catch(error){message.textContent='3D display is unavailable on this device. Entry and evidence controls remain available.';container.dataset.model='unavailable';toggle.disabled=true;}
