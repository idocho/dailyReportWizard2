/*
 * app.js — CampusManager 메인. 로그인 게이트(admin/super) + 계정/명단/전송 섹션.
 * 데이터: 명단/세션 = {DBPATH}/ 하위, acl·sendJobs = 루트. REST + idToken.
 * 선행: 콘솔 Auth 활성화 + firebase-config.js.  (위저드/수동설정 없음 — 로그인 기반)
 */
import * as A from './auth.js';
import * as P from './provision.js';
import { firebaseConfig } from './firebase-config.js';

const DB = firebaseConfig.databaseURL.replace(/\/$/, '');
const DBPATH = 'drw2_cbt';                 // TODO(F): 캠퍼스 경로 분리(campus/{id})
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const toast = t => { const e = $('toast'); e.textContent = t; e.classList.add('show'); setTimeout(() => e.classList.remove('show'), 1900); };
let session = null, booted = false, sec = 'accounts';

// ── REST 헬퍼 (idToken) ───────────────────────────────────────────────
async function tok(){ return (await A.getIdToken()) || ''; }
async function dbGet(node){ const r = await fetch(`${DB}/${DBPATH}/${node}.json?auth=${await tok()}`); return r.ok ? r.json() : null; }
async function dbPut(node, data){ const r = await fetch(`${DB}/${DBPATH}/${node}.json?auth=${await tok()}`, {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}); if(!r.ok) throw new Error('저장 실패 '+r.status); return r.json(); }
async function dbPatch(node, data){ const r = await fetch(`${DB}/${DBPATH}/${node}.json?auth=${await tok()}`, {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}); if(!r.ok) throw new Error('저장 실패 '+r.status); return r.json(); }
async function dbDel(node){ const r = await fetch(`${DB}/${DBPATH}/${node}.json?auth=${await tok()}`, {method:'DELETE'}); if(!r.ok) throw new Error('삭제 실패 '+r.status); return true; }
async function aclAll(){ const r = await fetch(`${DB}/acl.json?auth=${await tok()}`); return (r.ok ? await r.json() : null) || {}; }

// ── 로그인 게이트 ─────────────────────────────────────────────────────
let depsOk = true;
try { /* 모듈은 정적 import — 여기 도달 시 로드 성공 */ }
catch(e){ depsOk = false; }

function gMsg(t, x){ $('g-msg').className = 'msg ' + t; $('g-msg').textContent = x; }

A.onAuth(async (user) => {
  if (!user || booted) return;
  let acl;
  try { acl = await (await fetch(`${DB}/acl/${user.uid}.json?auth=${await A.getIdToken()}`)).json(); }
  catch(_) { acl = null; }
  if (!acl || acl.active !== true) { await A.logout(); gMsg('err', '비활성화된 계정입니다.'); return; }
  if (acl.role !== 'admin' && acl.role !== 'super') { await A.logout(); gMsg('err', '관리자 권한이 없습니다. 강사용 앱(DRW)을 이용하세요.'); return; }
  session = { uid: user.uid, ...acl };
  booted = true;
  renderShell();
});

$('g-btn').onclick = async () => {
  gMsg('', '');
  const name = $('g-name').value.trim(), pw = $('g-pw').value, c = $('g-campus').value;
  if (!name) return gMsg('err', '이름을 입력하세요.');
  $('g-btn').disabled = true; $('g-btn').textContent = '로그인 중…';
  try { await A.loginByName(c, name, pw, ['admin', 'super']); }   // 성공 → onAuth가 셸 렌더
  catch(e) { gMsg('err', e.message || String(e)); }
  finally { $('g-btn').disabled = false; $('g-btn').textContent = '로그인'; }
};

window.doLogout = async () => { try { await A.logout(); } catch(_){} location.reload(); };

// ── 셸 ────────────────────────────────────────────────────────────────
function renderShell(){
  $('gate').classList.add('hidden');
  $('app').classList.remove('hidden');
  $('whoName').textContent = session.instructorId || session.uid;
  $('whoCampus').textContent = session.campus;
  $('roleTag').textContent = session.role === 'super' ? '운영자(super)' : '관리자';
  $('logout').onclick = window.doLogout;
  document.querySelectorAll('.nav button').forEach(b => {
    b.onclick = () => { sec = b.dataset.sec; document.querySelectorAll('.nav button').forEach(x => x.classList.toggle('on', x === b)); renderSection(); };
  });
  renderSection();
}
function renderSection(){
  if (sec === 'accounts') renderAccounts();
  else if (sec === 'roster') renderRoster();
  else renderSend();
}

// ── 1) 강사 계정 ──────────────────────────────────────────────────────
async function renderAccounts(){
  $('content').innerHTML = `<div class="head"><h2>강사 계정</h2><span class="cnt" id="acnt"></span>
    <div class="sp"><button class="btn" id="addAcc">+ 강사 계정 발급</button></div></div>
    <div class="panel"><table><thead><tr><th>이름</th><th>상태</th><th>로그인 ID(자동)</th><th>작업</th></tr></thead><tbody id="arows"><tr><td colspan="4" class="empty">불러오는 중…</td></tr></tbody></table></div>
    <div class="note">발급=실제 Auth 계정+권한(acl) 생성, 첫 로그인 시 비번 변경. 비활성=즉시 차단(되돌림). 비번 리셋·삭제는 백엔드(Functions) 필요.</div>`;
  $('addAcc').onclick = openAccModal;
  const all = await aclAll();
  const mine = Object.entries(all).filter(([u,a]) => a && a.role === 'instructor' && (session.role === 'super' || a.campus === session.campus));
  $('acnt').textContent = `· ${mine.length}명 (활성 ${mine.filter(([u,a])=>a.active).length})`;
  $('arows').innerHTML = mine.length ? mine.map(([uid,a]) => `<tr>
      <td><b>${esc(a.instructorId||'(이름없음)')}</b>${session.role==='super'?` <span style="color:#94A3B8;font-size:11px">${esc(a.campus)}</span>`:''}</td>
      <td><span class="pill ${a.active?'on':'off'}">${a.active?'활성':'비활성'}</span></td>
      <td class="id">${esc(window.SynthEmail.synthEmail(a.instructorId||'',a.campus))}</td>
      <td><div class="act">
        <button data-act="toggle" data-uid="${uid}" data-active="${!a.active}">${a.active?'비활성':'활성화'}</button>
        <button class="del" disabled title="백엔드(Functions) 필요">비번 리셋</button>
        <button class="del" disabled title="백엔드(Functions) 필요">삭제</button>
      </div></td></tr>`).join('') : '<tr><td colspan="4" class="empty">강사 계정이 없습니다. + 발급으로 추가하세요.</td></tr>';
  $('arows').querySelectorAll('[data-act="toggle"]').forEach(b => b.onclick = async () => {
    try { await P.setActive(b.dataset.uid, b.dataset.active === 'true', await tok()); toast(b.dataset.active==='true'?'활성화':'비활성(즉시 차단)'); renderAccounts(); }
    catch(e){ toast(e.message||String(e)); }
  });
}
function genPw(){ const c='ABCDEFGHJKMNPQRSTUVWXYZ23456789'; let s=''; for(let i=0;i<8;i++) s+=c[Math.floor(Math.random()*c.length)]; return s; }
function openAccModal(){
  const pw = genPw();
  modal(`<h3>강사 계정 발급</h3>
    <label>이름</label><input id="mk-name" autocomplete="off">
    <label>임시 비밀번호</label><div style="display:flex;gap:8px"><input id="mk-pw" value="${pw}" readonly><button class="btn ghost" id="mk-gen">↻</button></div>
    <div id="mk-synth" style="margin-top:8px;font-size:10px;color:#94A3B8;font-family:ui-monospace,monospace;word-break:break-all;min-height:13px"></div>
    <div class="mrow"><button class="btn cancel" id="mk-cancel">취소</button><button class="btn" id="mk-ok">발급</button></div>`);
  $('mk-name').focus();
  $('mk-name').oninput = () => { const n=$('mk-name').value.trim(); $('mk-synth').textContent = n?'→ 로그인 ID: '+window.SynthEmail.synthEmail(n,session.campus):''; };
  $('mk-gen').onclick = () => $('mk-pw').value = genPw();
  $('mk-cancel').onclick = closeModal;
  $('mk-ok').onclick = async () => {
    const n = $('mk-name').value.trim(); if(!n) return $('mk-name').focus();
    $('mk-ok').disabled = true;
    try { await P.createInstructor(session.campus, n, $('mk-pw').value, await tok()); closeModal(); toast(`${n} 발급 — 임시비번 ${$('mk-pw').value} 전달`); renderAccounts(); }
    catch(e){ toast(e.message||String(e)); $('mk-ok').disabled = false; }
  };
}

// ── 2) 명단 (students/classes) ────────────────────────────────────────
let rState = { group:'M', sel:null, classes:{}, students:{} };
async function renderRoster(){
  $('content').innerHTML = `<div class="head"><h2>명단 관리</h2><span class="cnt" id="rcnt"></span>
    <div class="sp"><button class="btn ghost" id="addCls">+ 반 추가</button><button class="btn" id="addStu">+ 학생 추가</button></div></div>
    <div class="roster">
      <div class="panel"><div class="gtog"><button id="gM">M반</button><button id="gT">T반</button></div><div class="clist" id="clist" style="padding:4px 8px 10px"></div></div>
      <div class="panel" id="spanel"></div>
    </div>`;
  const [cls, stu] = await Promise.all([dbGet('classes'), dbGet('students')]);
  rState.classes = cls || {}; rState.students = stu || {};
  const cnt = Object.keys(rState.students).length;
  $('rcnt').textContent = `· 학생 ${cnt}명 · 반 ${Object.keys(rState.classes).length}개`;
  $('gM').onclick = () => { rState.group='M'; rState.sel=null; drawRoster(); };
  $('gT').onclick = () => { rState.group='T'; rState.sel=null; drawRoster(); };
  $('addCls').onclick = addClass;
  $('addStu').onclick = () => openStuModal(null);
  drawRoster();
}
function inClass(c){ return Object.values(rState.students).filter(s => s.class === c).length; }
function unassigned(){ return Object.entries(rState.students).filter(([k,s]) => !s.class || !rState.classes[s.class]); }
function drawRoster(){
  $('gM').className = rState.group==='M'?'on':''; $('gT').className = rState.group==='T'?'on':'';
  const cs = Object.entries(rState.classes).filter(([id,c]) => (c.group||'M') === rState.group);
  if (!rState.sel) rState.sel = cs.length ? cs[0][0] : '__un__';
  $('clist').innerHTML = cs.map(([id]) => `<div class="ci ${rState.sel===id?'on':''}" data-c="${esc(id)}">${esc(id)}<span class="n">${inClass(id)}</span></div>`).join('')
    + `<div class="ci ${rState.sel==='__un__'?'on':''}" data-c="__un__" style="color:var(--amber)">⚠ 무소속<span class="n">${unassigned().length}</span></div>`;
  $('clist').querySelectorAll('.ci').forEach(el => el.onclick = () => { rState.sel = el.dataset.c; drawRoster(); });
  const list = rState.sel==='__un__' ? unassigned() : Object.entries(rState.students).filter(([k,s]) => s.class === rState.sel);
  $('spanel').innerHTML = `<div style="padding:11px 14px;font-weight:800;font-size:13px;border-bottom:1px solid var(--line)">${rState.sel==='__un__'?'무소속':esc(rState.sel)} · ${list.length}명</div>`
    + (list.length ? `<table><thead><tr><th>출결번호</th><th>이름</th><th>반</th><th>작업</th></tr></thead><tbody>`
      + list.map(([k,s]) => `<tr><td class="num">${esc(k)}</td><td><b>${esc(s.name)}</b></td><td>${esc(s.class||'무소속')}</td>
        <td class="act"><button data-edit="${esc(k)}">편집</button><button class="del" data-del="${esc(k)}">삭제</button></td></tr>`).join('')
      + `</tbody></table>` : '<div class="empty">학생이 없습니다.</div>');
  $('spanel').querySelectorAll('[data-edit]').forEach(b => b.onclick = () => openStuModal(b.dataset.edit));
  $('spanel').querySelectorAll('[data-del]').forEach(b => b.onclick = () => delStudent(b.dataset.del));
}
function classOpts(cur){ return Object.keys(rState.classes).map(id => `<option value="${esc(id)}"${id===cur?' selected':''}>${esc(id)}</option>`).join('') + `<option value="">무소속</option>`; }
function openStuModal(key){
  const s = key ? rState.students[key] : null;
  modal(`<h3>${key?'학생 편집':'학생 추가'}</h3>
    <label>출결번호 (nameKey)</label><input id="ms-key" value="${key?esc(key):''}" ${key?'disabled':''}>
    <label>이름</label><input id="ms-name" value="${s?esc(s.name):''}">
    <label>반</label><select id="ms-cls">${classOpts(s?s.class:(rState.sel==='__un__'?'':rState.sel))}</select>
    <div class="mrow"><button class="btn cancel" id="ms-cancel">취소</button><button class="btn" id="ms-ok">저장</button></div>`);
  $('ms-cancel').onclick = closeModal;
  $('ms-ok').onclick = async () => {
    const k = $('ms-key').value.trim(), nm = $('ms-name').value.trim(), cl = $('ms-cls').value || null;
    if(!k||!nm) return toast('출결번호·이름을 입력하세요');
    if(!key && rState.students[k]) return toast('이미 있는 출결번호입니다');
    try { await dbPut('students/'+k, {name:nm, class:cl}); closeModal(); toast('저장됨'); renderRoster(); }
    catch(e){ toast(e.message||String(e)); }
  };
}
async function delStudent(k){
  if(!confirm(`'${rState.students[k]?.name}' 학생을 삭제할까요?`)) return;
  try { await dbDel('students/'+k); toast('삭제됨'); renderRoster(); } catch(e){ toast(e.message||String(e)); }
}
async function addClass(){
  const id = prompt('새 반 이름 (예: 중1A)'); if(!id) return;
  if(rState.classes[id]) return toast('이미 있는 반입니다');
  try { await dbPatch('classes', {[id]:{group:rState.group}}); toast(`${id} 추가 (${rState.group})`); renderRoster(); }
  catch(e){ toast(e.message||String(e)); }
}

// ── 3) 일괄 전송 (sendJobs 큐 작성) ───────────────────────────────────
const TPL = [
  {name:'일반 공지', body:'안녕하세요, {이름} 학부모님.\n{반} 반 안내드립니다.\n(내용을 입력하세요)\n감사합니다.'},
  {name:'시험 안내', body:'안녕하세요, {이름} 학부모님.\n{반} 반 시험 일정 안내드립니다.\n• 일시: ○월 ○일\n감사합니다.'},
];
let sState = { cls:null, sel:new Set(), classes:{}, students:{} };
async function renderSend(){
  $('content').innerHTML = `<div class="head"><h2>일괄 전송</h2></div>
    <div class="note" style="margin-top:0;margin-bottom:14px">작성 → <b>sendJobs 큐</b> → 캠퍼스 PC의 <b>전송 에이전트</b>가 KakaoTalk 발송(별도). 여기선 작업 생성·상태만.</div>
    <div class="send">
      <div class="panel" style="padding:16px">
        <label>템플릿</label><select id="s-tpl">${TPL.map((t,i)=>`<option value="${i}">${esc(t.name)}</option>`).join('')}</select>
        <label>대상 반</label><select id="s-cls"></select>
        <div style="display:flex;align-items:center;gap:10px;margin:8px 0"><span id="s-cnt" style="font-size:12px;color:var(--sub)"></span><a id="s-all" style="font-size:12px;color:var(--indigo);cursor:pointer;font-weight:700">전체선택</a><a id="s-none" style="font-size:12px;color:var(--indigo);cursor:pointer;font-weight:700">해제</a></div>
        <div class="stulist" id="s-stu"></div>
        <label>메시지 ({이름} {반} 치환)</label><textarea id="s-body"></textarea>
        <label>미리보기</label><div class="pv" id="s-pv"></div>
        <button class="btn full" id="s-send" style="margin-top:14px">전송 작업 생성 → 에이전트</button>
      </div>
      <div class="panel" style="padding:16px"><div style="font-weight:800;font-size:13px;margin-bottom:10px">전송 작업 (sendJobs)</div><div id="s-jobs"><div class="empty">작업 없음</div></div></div>
    </div>`;
  const [cls, stu] = await Promise.all([dbGet('classes'), dbGet('students')]);
  sState.classes = cls || {}; sState.students = stu || {};
  $('s-cls').innerHTML = Object.keys(sState.classes).map(id=>`<option>${esc(id)}</option>`).join('') || '<option value="">(반 없음)</option>';
  $('s-tpl').onchange = () => { $('s-body').value = TPL[+$('s-tpl').value].body; preview(); };
  $('s-cls').onchange = drawRecipients;
  $('s-all').onclick = () => { Object.keys(stuOf()).forEach(k=>sState.sel.add(k)); drawRecipients(); };
  $('s-none').onclick = () => { sState.sel.clear(); drawRecipients(); };
  $('s-body').oninput = preview;
  $('s-send').onclick = createJob;
  $('s-body').value = TPL[0].body;
  drawRecipients(); loadJobs();
}
function stuOf(){ const c = $('s-cls').value; const o={}; for(const [k,s] of Object.entries(sState.students)) if(s.class===c) o[k]=s; return o; }
function drawRecipients(){
  const list = stuOf();
  if (!sState.sel.size) Object.keys(list).forEach(k=>sState.sel.add(k));
  // 다른 반 선택 잔여 제거
  for (const k of [...sState.sel]) if (!list[k]) sState.sel.delete(k);
  $('s-stu').innerHTML = Object.entries(list).map(([k,s])=>`<label class="stu"><input type="checkbox" data-k="${esc(k)}" ${sState.sel.has(k)?'checked':''} style="width:auto"><b>${esc(s.name)}</b></label>`).join('') || '<div class="empty" style="padding:14px">학생 없음</div>';
  $('s-stu').querySelectorAll('input').forEach(i => i.onchange = () => { i.checked?sState.sel.add(i.dataset.k):sState.sel.delete(i.dataset.k); updCnt(); preview(); });
  updCnt(); preview();
}
function updCnt(){ $('s-cnt').textContent = `선택 ${sState.sel.size}명`; }
function preview(){ const first=[...sState.sel][0]; const nm=first?sState.students[first]?.name:'(수신자 없음)'; $('s-pv').textContent = render($('s-body').value, nm); }
function render(t, name){ return String(t||'').replace(/{이름}/g,name||'').replace(/{반}/g,$('s-cls').value||'').replace(/{날짜}/g,new Date().toLocaleDateString('ko-KR')); }
async function createJob(){
  const ids = [...sState.sel]; if(!ids.length) return toast('수신자를 선택하세요');
  const body = $('s-body').value.trim(); if(!body) return toast('메시지를 입력하세요');
  const cls = $('s-cls').value;
  const jobId = Date.now() + '_' + Math.floor(Math.random()*1000);
  const job = { createdBy: session.instructorId, campus: session.campus, cls, status:'queued', ts: Date.now(),
    recipients: ids.map(k => ({ nameKey:k, name: sState.students[k]?.name, status:'대기' })), body };
  try {
    const r = await fetch(`${DB}/sendJobs/${session.campus}/${jobId}.json?auth=${await tok()}`, {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(job)});
    if(!r.ok) throw new Error('작업 생성 실패 '+r.status);
    toast(`전송 작업 생성 (${ids.length}명) — 에이전트 대기`); loadJobs();
  } catch(e){ toast(e.message||String(e)); }
}
async function loadJobs(){
  const r = await fetch(`${DB}/sendJobs/${session.campus}.json?auth=${await tok()}`);
  const jobs = (r.ok ? await r.json() : null) || {};
  const arr = Object.entries(jobs).sort((a,b)=>(b[1].ts||0)-(a[1].ts||0)).slice(0,8);
  $('s-jobs').innerHTML = arr.length ? arr.map(([id,j])=>{
    const done = (j.recipients||[]).filter(x=>x.status==='완료').length, tot=(j.recipients||[]).length;
    const st = j.status==='done'?['done','완료']:['q', tot?`${done}/${tot}`:'대기'];
    return `<div class="job"><div class="jh">${esc(j.cls)} (${tot}명)<span class="st ${st[0]}">${st[1]}</span></div><div style="color:var(--sub)">${esc((j.body||'').slice(0,30))}…</div></div>`;
  }).join('') : '<div class="empty">작업 없음</div>';
}

// ── 모달 유틸 ─────────────────────────────────────────────────────────
function modal(html){ let ov=$('ov'); if(!ov){ ov=document.createElement('div'); ov.id='ov'; ov.className='ov'; document.body.appendChild(ov); } ov.innerHTML=`<div class="modal">${html}</div>`; ov.classList.add('on'); }
function closeModal(){ const ov=$('ov'); if(ov) ov.classList.remove('on'); }

// 설정 누락 시 안내
window.addEventListener('error', () => {});
