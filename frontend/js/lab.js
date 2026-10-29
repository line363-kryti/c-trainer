import {api} from '/js/api.js';
import {initShell} from '/js/shell.js';
import {loadMonaco,monacoTheme} from '/js/monaco-c.js';
import {currentTheme} from '/js/theme.js';
const $=id=>document.getElementById(id), slug=new URLSearchParams(location.search).get('lab');
const base='/api/labs/'+encodeURIComponent(slug||'');
let ed, lab, state={}, timer, saved='', chain=Promise.resolve(), busy=false;
const text=(tag,value)=>Object.assign(document.createElement(tag),{textContent:value});
const markdown=(el,value)=>{el.innerHTML=DOMPurify.sanitize(marked.parse(value));};
async function hash(code){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(code)))].map(x=>x.toString(16).padStart(2,'0')).join('');}
function save(){clearTimeout(timer);const code=ed.getValue();chain=chain.catch(()=>{}).then(async()=>{if(code===saved)return;$('save').textContent='Сохраняю…';await api(base+'/code',{method:'PUT',body:{code}});saved=code;$('save').textContent=ed.getValue()===saved?'Сохранено':'Есть изменения';});return chain;}
async function refresh(){const code=ed.getValue(), h=await hash(code);if(ed.getValue()!==code)return;
for(const s of lab.stages){const r=state.stages?.[s.id];document.getElementById('status-'+s.id).textContent=!r?'Не проверен':r.hash!==h?'Код изменён — проверь заново':r.passed?(r.manual?'Отмечен вручную':'Тесты пройдены'):'Нужны исправления';}
const f=state.final;$('verdict').textContent=!f?'':f.hash!==h?'Код изменён. Итоговую проверку нужно повторить.':f.passed?'Все итоговые тесты пройдены':'Итоговые тесты не пройдены';}
function report(e){$('notice').textContent=e.message||String(e);}
async function action(fn){if(busy)return;busy=true;document.querySelectorAll('#run,#check,[data-stage-action]').forEach(b=>b.disabled=true);$('notice').textContent='';try{await save();await fn();}catch(e){report(e);}finally{busy=false;document.querySelectorAll('#run,#check,[data-stage-action]').forEach(b=>b.disabled=b.id==='check'&&!lab.can_check);}}
async function check(stage=null){if(!stage && !lab.can_check)return;await action(async()=>{const code=ed.getValue();$('results').replaceChildren(text('p','Проверяю…'));const r=await api(base+'/check',{method:'POST',body:{code,stage}});if(stage)(state.stages??={})[stage]=r;else state.final=r;
$('results').replaceChildren(text('p',(stage?'Этап':'Вся работа')+': '+r.results.filter(t=>t.passed).length+' / '+r.total));
if(r.compile_error)$('results').append(text('pre',r.compile_error));
for(const t of r.results){const d=document.createElement('details');d.append(text('summary',`Тест ${t.index}: ${t.passed?'пройден':'не пройден'}`));d.append(text('pre',`Ввод:\n${t.input}\nОжидалось:\n${t.expected}\nПолучено:\n${t.got}\n${t.stderr||t.message||''}`));$('results').append(d);}await refresh();});}
try{if(!slug)throw Error('Выбери работу в разделе лабораторных.');
const [shell,m,data]=await Promise.all([initShell({active:'labs'}),loadMonaco(),api(base)]);lab=data;state=lab.state;saved=lab.code;
$('title').textContent=lab.title;document.title=lab.title+' — C-тренажёр';$('meta').textContent=[lab.variant,lab.max_points ? 'До '+lab.max_points+' баллов' : '',lab.source].filter(Boolean).join(' · ');markdown($('statement'),lab.statement);
for(const q of lab.defense)$('defense').append(text('li',q));if(!lab.defense.length)$('defense').append(text('li','Вопросы пока не добавлены.'));
$('check').disabled=!lab.can_check; if(!lab.can_check)$('check').title='Автоматические тесты пока не настроены';
if(lab.execution_note){const note=text('p',lab.execution_note);note.className='lab-note';$('statement').before(note);}
$('work').hidden=false;ed=m.editor.create($('editor'),{value:lab.code,language:'c',theme:monacoTheme(currentTheme()),automaticLayout:true,fontFamily:'JetBrains Mono',fontLigatures:false,minimap:{enabled:true}});
window.addEventListener('themechange',e=>m.editor.setTheme(monacoTheme(e.detail)));
ed.onDidChangeModelContent(()=>{$('save').textContent='Есть изменения';clearTimeout(timer);timer=setTimeout(()=>save().catch(report),700);refresh().catch(report);});
window.addEventListener('beforeunload',e=>{if(ed.getValue()!==saved){e.preventDefault();e.returnValue='';}});
for(const s of lab.stages){const box=document.createElement('section');box.className='lab-stage';box.append(text('h3',s.title));const desc=document.createElement('div');markdown(desc,s.description);box.append(desc);const status=text('p','');status.id='status-'+s.id;status.className='stage-state';box.append(status);
if(s.hint){const hint=document.createElement('details');hint.append(text('summary','Подсказка'),text('p',s.hint));box.append(hint);}
const btn=text('button',s.automatic?'Проверить этап':'Отметить выполненным');btn.className='btn btn-outline';btn.dataset.stageAction='';btn.onclick=()=>s.automatic?check(s.id):action(async()=>{state=await api(base+'/stages/'+encodeURIComponent(s.id),{method:'PUT',body:{code:ed.getValue(),done:true}});await refresh();});box.append(btn);$('stage-list').append(box);}
let guided=localStorage.getItem('lab-guided')!=='false';function mode(){ $('steps').hidden=!guided;document.querySelector('.lab-layout').classList.toggle('solo',!guided);$('mode').textContent=guided?'Самостоятельно':'По шагам';$('mode').setAttribute('aria-expanded',String(guided));ed.layout();}mode();$('mode').onclick=()=>{guided=!guided;localStorage.setItem('lab-guided',String(guided));mode();};
$('defended').checked=!!state.defended;$('defended').onchange=async()=>{const input=$('defended');input.disabled=true;try{state=await api(base+'/defended',{method:'PUT',body:{done:input.checked}});}catch(e){input.checked=!!state.defended;report(e);}finally{input.disabled=false;}};
$('save-btn').onclick=()=>save().catch(report);$('check').onclick=()=>check();$('run').onclick=()=>action(async()=>{const r=await api(base+'/run',{method:'POST',body:{code:ed.getValue(),stdin:$('stdin').value}});$('results').replaceChildren(text('p',r.status==='ok'?'Программа выполнена':r.status),text('pre',r.compile_output||r.stdout||r.message||'(нет вывода)'));if(r.stderr)$('results').append(text('pre',r.stderr));});
$('download').onclick=()=>{const url=URL.createObjectURL(new Blob([ed.getValue()],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='main.c';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
ed.addCommand(m.KeyMod.CtrlCmd|m.KeyCode.KeyS,()=>save().catch(report));
ed.addCommand(m.KeyMod.CtrlCmd|m.KeyCode.Enter,()=>$('run').click());ed.addCommand(m.KeyMod.CtrlCmd|m.KeyMod.Shift|m.KeyCode.Enter,()=>check());
$('notice').textContent='';$('save').textContent='Сохранено';await refresh();
}catch(e){report(e);}
