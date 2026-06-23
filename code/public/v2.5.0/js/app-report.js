// app-report.js — 리포트 탭: AI 생성·검토·미리보기·전송 (PC앱 충실 이식 + 웹 통합)
// 기존 재사용: progressData·getTags·_readNote·dotClass·activeAsgns·activeCourses·getCurriculumForSubject
// 메시지 형식(build_message)·말투(ai_style)·미리보기를 PC앱과 동일하게 재현.
// 키·카톡·문체분석은 강사 PC 에이전트(로컬). 웹=맥락·검토·미리보기·전송요청.

let reportDrafts = {};      // {nameKey: 검토중 특이사항}
let _rpJobTimer = null;
let _rpActive = null;       // 우측 미리보기 대상 학생(nameKey)

// 문체 옵션 (ai_style.py STYLE_ORDER/LABELS 미러)
const RP_STYLES = [
  ['auto', '✍️ 내 말투 자동 (전송 노트 학습)'],
  ['warm_detail', '📖 따뜻·상세형'],
  ['balanced', '📋 정돈·균형형'],
  ['info_coach', '🎯 정보·코칭형'],
  ['concise', '⚡ 간결·요점형'],
];
// 과제수행도 코드 → 라벨(이모지 제거)
function _assignText(code){
  if(!code) return '';
  const g = (typeof ASSIGN_GRADES !== 'undefined') ? ASSIGN_GRADES.find(x => x.key === code) : null;
  return g ? g.label.replace(/[^가-힣]/g, '').trim() : '';
}
// 입력된 관찰 태그(obs) → {label, kind} 목록. kind=의미별 색상(pos/warn/neutral/assign)
function _obsTagLabels(tags){
  if(!tags || typeof TAGS === 'undefined') return [];
  const out = [];
  if(tags.condition){ const t = TAGS.condition.find(x => x.key === tags.condition); if(t) out.push({ label: '컨디션 ' + t.label, kind: 'neutral' }); }
  if(tags.understand){ const t = TAGS.understand.find(x => x.key === tags.understand); if(t) out.push({ label: '이해 ' + t.label, kind: 'neutral' }); }
  const KIND = { understand_sub: 'pos', engage: 'pos', highlight: 'pos', caution: 'warn', extra: 'neutral' };
  ['understand_sub', 'engage', 'caution', 'extra', 'highlight'].forEach(g => {
    (tags[g] || []).forEach(k => { const t = (TAGS[g] || []).find(x => x.key === k); if(t) out.push({ label: t.label, kind: KIND[g] || 'neutral' }); });
  });
  (tags.assign_tags || []).forEach(p => out.push({ label: p, kind: 'assign' }));
  return out;
}
// 과정+교재 라벨 (constants.grade_label 미러) — 다과목일 때만
function _subjLabel(gs, subject){
  gs = (gs || '').trim();
  return (gs && !subject.startsWith(gs + ' ')) ? `${gs} ${subject}` : subject;
}
function _nickSuffix(full){
  const nick = full.length > 1 ? full.slice(1) : full;
  const c = nick.charCodeAt(nick.length - 1);
  return (c >= 0xAC00 && c <= 0xD7A3 && (c - 0xAC00) % 28 !== 0) ? nick + '이는' : nick + '는';
}
function _todayStr(){ const d = new Date(); return `${d.getMonth() + 1}/${d.getDate()} (${'일월화수목금토'[d.getDay()]})`; }

// 학생 1명의 메시지 데이터 집계 — 내가 담당하는 과목만(옛/타 교재 노출 방지)
function _rpData(classId, nk){
  const courses = (typeof activeCourses === 'function') ? (activeCourses(config.classes[classId] || {}) || {}) : {};
  // 담당 과목(assignments, admin이면 activeAsgns 확장 포함) ∩ 현재 활성 과목
  const mine = (typeof activeAsgns === 'function' ? activeAsgns() : (instructor?.assignments || []))
    .filter(a => a.classId === classId).map(a => a.subject);
  const subjects = [...new Set(mine)].filter(s => courses[s]).sort();
  const classInfo = {}, assignMap = {}, tbGrade = {};
  subjects.forEach(sub => {
    const pd = progressData[`${classId}|${sub}`] || {};
    classInfo[sub] = { progress: pd.progress || '', homework: pd.homework || '' };
    assignMap[sub] = _assignText((getTags(classId, nk, sub) || {}).assign_grade);
    tbGrade[sub] = courses[sub].curriculum || '';
  });
  return { subjects, classInfo, assignMap, tbGrade };
}
// 실제 발송 메시지 조립 (message.build_message 미러)
function _buildMessage(classId, nk, name, note){
  const { subjects, classInfo, assignMap, tbGrade } = _rpData(classId, nk);
  const multi = subjects.length > 1;
  const lbl = tb => multi ? _subjLabel(tbGrade[tb] || '', tb) : null;
  const section = field => subjects.map(tb => {
    const v = (classInfo[tb][field] || '').trim(); if(!v) return '';
    const l = lbl(tb); return l ? `[${l}] ${v}` : v;
  }).filter(Boolean).join('\n');
  const assignLines = subjects.map(tb => {
    const a = (assignMap[tb] || '').trim(); if(!a) return '';
    const l = lbl(tb); return l ? `[${l}] ${a}` : a;
  }).filter(Boolean).join('\n');
  return `[데일리 리포트] ${_todayStr()}\n-------------------------\n`
    + `▶ 오늘의 진도\n${section('progress')}\n\n`
    + `▶ 오늘의 과제\n${section('homework')}\n\n`
    + `▶ 과제 수행도\n${assignLines}\n\n`
    + `▶ 오늘의 ${_nickSuffix(name)}?\n${note || ''}`;
}

function _rpStudents(){
  const a = activeAsgns()[curAI]; if(!a) return [];
  return sortStu((config._classStudents || {})[a.classId] || []);
}
// 발송 특이사항(발송문) — 세션 편집 > 저장된 오늘 draft > 빈값. (강사 원천 메모와 별개)
function _curDraft(nk){
  if(nk in reportDrafts) return reportDrafts[nk];
  const d = (inputData[nk] || {}).__draft__;
  return (d && d.date === todayKey()) ? (d.value || '') : '';
}
function _saveDraft(nk, val){
  reportDrafts[nk] = val;
  if(!inputData[nk]) inputData[nk] = {};
  inputData[nk].__draft__ = { value: val, date: todayKey() };
  try{ fbPatch(`input/${nk}/__draft__`, { value: val, date: todayKey() }); }catch(_){}
}

// ── 메인 렌더 ─────────────────────────────────────────────────────────
function renderReport(mc){
  renderMhdr('리포트');
  if(!config){ mc.innerHTML = makeTb('리포트') + `<div class="empty">⚙️ 설정 후 이용하세요.</div>`; return; }
  const asgns = instructor?.assignments || [];
  if(!asgns.length){ mc.innerHTML = makeTb('리포트') + `<div class="empty">설정 → 담당 수업을 추가해 주세요.</div>`; return; }
  if(curAI >= asgns.length) curAI = 0;
  const a = asgns[curAI]; const { classId, subject } = a;
  const students = _rpStudents();
  if(!_rpActive || !students.some(s => s.nameKey === _rpActive)) _rpActive = students[0]?.nameKey || null;
  const styleLbl = (RP_STYLES.find(s => s[0] === (instructor?.ai_style_mode || 'auto')) || RP_STYLES[0])[1];

  const rows = students.map(s => {
    const nk = s.nameKey, name = s.name;
    const note = _curDraft(nk);
    const memo = _readNote(nk) || '';
    const d = _rpData(classId, nk);
    const dot = dotClass(classId, nk, subject);
    const summary = d.subjects.map(sub => {
      const ci = d.classInfo[sub], ag = d.assignMap[sub];
      const bits = [ci.progress && `진도 ${esc(ci.progress)}`, ci.homework && `과제 ${esc(ci.homework)}`, ag && `수행도 ${esc(ag)}`].filter(Boolean).join(' · ');
      const obs = _obsTagLabels(getTags(classId, nk, sub));
      const obsHtml = obs.length ? `<div class="rp-obs">${obs.map(o => `<span class="rp-tag k-${o.kind}">${esc(o.label)}</span>`).join('')}</div>` : '';
      return (bits || obs.length) ? `<div class="rp-sub"><b>${esc(d.subjects.length > 1 ? sub : '')}</b> ${bits}</div>${obsHtml}` : '';
    }).join('') || `<div class="rp-sub" style="color:var(--gray)">진도·과제·수행도·관찰 미입력</div>`;
    return `<div class="rp-row${nk === _rpActive ? ' active' : ''}" data-nk="${esc(nk)}" onclick="setRpActive('${esc(nk)}')">
      <div class="rp-head"><span class="dot ${dot}"></span><b>${esc(name)}</b>
        ${note.trim() ? `<span class="rp-badge ok">검토중</span>` : `<span class="rp-badge no">미생성</span>`}</div>
      ${summary}
      ${memo ? `<div class="rp-memo">📝 강사 메모: <b>${esc(memo)}</b> <span>· 입력에서 수정</span></div>` : ''}
      <div class="rp-lbl">발송 특이사항 <span class="hint">AI 생성·검토 · 자동 저장</span></div>
      <textarea class="rp-ta" id="rp-${esc(nk)}" onfocus="setRpActive('${esc(nk)}')" oninput="onRpEdit('${esc(nk)}',this)" onchange="_saveDraft('${esc(nk)}',this.value)" placeholder="✨ 생성을 누르면 강사 메모·데이터로 발송문을 만듭니다 — 검토·수정 후 전송">${esc(note)}</textarea>
      <div class="rp-act">
        <button class="rp-gen" onclick="event.stopPropagation();genReportOne('${esc(nk)}')">✨ ${note.trim() ? '다시생성' : '생성'}</button>
        <div class="rp-tones">
          <button class="rp-tone" onclick="event.stopPropagation();genReportOne('${esc(nk)}','warm')">따뜻</button>
          <button class="rp-tone" onclick="event.stopPropagation();genReportOne('${esc(nk)}','concise')">간결</button>
          <button class="rp-tone" onclick="event.stopPropagation();genReportOne('${esc(nk)}','detailed')">구체</button>
        </div>
      </div>
    </div>`;
  }).join('') || `<div class="empty">이 반에 학생이 없습니다.</div>`;

  mc.innerHTML = makeTb('리포트', `${classId} · ${subject}`) + _stageBar('report') + `
    <div class="rp-2col">
      <div class="rp-left">
        <div class="rp-bar">
          <span class="rp-ctx">문체: ${esc(styleLbl)}</span>
          <button class="rp-btn ghost" onclick="genReportAll()">✨ 일괄 생성</button>
          <button class="rp-btn" onclick="openReportSend()">전송 →</button>
        </div>
        <div class="rp-list">${rows}</div>
        <div class="rp-jobs"><div class="rp-jobs-hd">전송 상태</div><div id="rp-jobs"><div class="rp-job">작업 없음</div></div></div>
      </div>
      <div class="rp-right" id="rp-right"></div>
    </div>`;
  _renderRpPreview();
  loadReportJobs();
  clearInterval(_rpJobTimer); _rpJobTimer = setInterval(loadReportJobs, 2500);
}

// 좌측 학생 편집 → 우측 미리보기 (전체 재렌더 없이 우측만 갱신 = 타이핑 무지연)
function onRpEdit(nk, el){ reportDrafts[nk] = el.value; if(nk === _rpActive) _renderRpPreview(); }
function setRpActive(nk){
  _rpActive = nk;
  document.querySelectorAll('.rp-row').forEach(r => r.classList.toggle('active', r.dataset.nk === nk));
  _renderRpPreview();
}
function _renderRpPreview(){
  const el = document.getElementById('rp-right'); if(!el) return;
  const a = activeAsgns()[curAI];
  const s = a && _rpActive ? _rpStudents().find(x => x.nameKey === _rpActive) : null;
  if(!s){ el.innerHTML = `<div class="rp-pv-empty">학생을 선택하면<br>실제 발송 미리보기가 표시됩니다.</div>`; return; }
  const msg = _buildMessage(a.classId, _rpActive, s.name, _curDraft(_rpActive));
  el.innerHTML = `<div class="rp-pv-hd">📨 ${esc(s.name)} · 발송 미리보기 <span class="rp-len">${msg.length}자</span></div>`
    + `<pre class="rp-pv-body">${esc(msg)}</pre>`;
}

// ── 생성 ──────────────────────────────────────────────────────────────
async function _pollDraft(jid, ms = 120000){
  const t0 = Date.now();
  while(Date.now() - t0 < ms){
    const j = await fbGet(`genJobs/${instructor.id}/${jid}`);
    if(j && j.status === 'done') return j.draft;
    if(j && j.status === 'error') throw new Error(j.error || '생성 실패');
    await new Promise(r => setTimeout(r, 1000));
  }
  throw new Error('생성 지연 — 잠시 후 다시 생성하거나 에이전트 상태를 확인하세요');
}
function _genCtx(classId, nk, name, tone){
  const d = _rpData(classId, nk);
  const items = d.subjects.map(sub => ({
    subject: sub, value: d.assignMap[sub],
    progress: d.classInfo[sub].progress, homework: d.classInfo[sub].homework,
    gradeLabel: d.tbGrade[sub],
  }));
  // obs 태그 병합(과제수행도 제외 — value로 전달)
  const tags = {};
  d.subjects.forEach(sub => { const t = { ...(getTags(classId, nk, sub) || {}) }; delete t.assign_grade; Object.assign(tags, t); });
  const job = {
    nameKey: nk, cls: classId, displayName: name, sheet: '',
    items, tags, note: _readNote(nk) || '',
    styleMode: instructor?.ai_style_mode || 'auto',
    customPrompt: instructor?.ai_custom_prompt || '',
    status: 'queued',
  };
  if(tone){ job.tone = tone; job.currentDraft = reportDrafts[nk] || ''; }
  return job;
}
async function genReportOne(nk, tone){
  const a = activeAsgns()[curAI]; if(!a) return;
  const name = (_rpStudents().find(s => s.nameKey === nk) || {}).name || nk;
  const ta = document.getElementById('rp-' + nk);
  if(ta){ ta.value = tone ? '🎚 톤 조절 중…' : '✨ AI 생성 중…'; }
  const jid = Date.now() + '_' + Math.floor(Math.random() * 1000);
  try{
    await fbPut(`genJobs/${instructor.id}/${jid}`, _genCtx(a.classId, nk, name, tone));
    const draft = await _pollDraft(jid);
    _saveDraft(nk, draft); _rpActive = nk;
    renderMain();
  }catch(e){ if(ta) ta.value = '[' + (e.message || e) + ']'; toast('생성 실패 — 에이전트 확인'); }
}
async function _pollDrafts(jid, ms = 180000){   // 배치 — 더 긴 여유
  const t0 = Date.now();
  while(Date.now() - t0 < ms){
    const j = await fbGet(`genJobs/${instructor.id}/${jid}`);
    if(j && j.status === 'done') return j.drafts || {};
    if(j && j.status === 'error') throw new Error(j.error || '생성 실패');
    await new Promise(r => setTimeout(r, 1200));
  }
  throw new Error('생성 지연 — 에이전트 상태를 확인하세요');
}
async function genReportAll(){
  const a = activeAsgns()[curAI]; if(!a) return;
  const classId = a.classId;
  const students = _rpStudents().filter(s => _rpData(classId, s.nameKey).subjects.length);
  if(!students.length) return toast('생성 대상이 없습니다');
  const list = students.map(s => {
    const c = _genCtx(classId, s.nameKey, s.name);   // 단건 맥락 재사용
    return { nameKey: s.nameKey, displayName: s.name, items: c.items, tags: c.tags, note: c.note };
  });
  const job = { batch: true, cls: classId, students: list,
    styleMode: instructor?.ai_style_mode || 'auto', customPrompt: instructor?.ai_custom_prompt || '', status: 'queued' };
  toast(`일괄 생성 ${list.length}명 — 한 번에 처리합니다`);
  students.forEach(s => { const t = document.getElementById('rp-' + s.nameKey); if(t) t.value = '✨ 생성 중…'; });
  const jid = Date.now() + '_' + Math.floor(Math.random() * 1000);
  try{
    await fbPut(`genJobs/${instructor.id}/${jid}`, job);
    const drafts = await _pollDrafts(jid);
    Object.entries(drafts).forEach(([nk, note]) => _saveDraft(nk, note));
    const got = Object.keys(drafts).length;
    toast(got ? `${got}명 생성 완료` : '생성 결과 없음 — 입력/에이전트 확인');
    renderMain();
  }catch(e){ toast('일괄 생성 실패: ' + (e.message || e)); renderMain(); }
}

// ── 전송 (실제 메시지 = build_message 전체) ──────────────────────────
function openReportSend(){
  const a = activeAsgns()[curAI]; if(!a) return;
  const students = _rpStudents();
  const ready = students.filter(s => _curDraft(s.nameKey).trim());
  const skipped = students.filter(s => !_curDraft(s.nameKey).trim()).map(s => s.name);
  const cnt = {}; ready.forEach(s => cnt[s.name] = (cnt[s.name] || 0) + 1);
  const dups = [...new Set(ready.map(s => s.name).filter(n => cnt[n] > 1))];
  _rpModal(`<h3>카카오톡 전송 대상</h3>
    <div class="rp-hint">전송 대상 ${ready.length}명 — 제외할 학생 체크 해제. 실제 발송 형식으로 전송됩니다.</div>
    <div class="rp-cks">${ready.map(s => `<label class="rp-ck"><input type="checkbox" checked data-snk="${esc(s.nameKey)}"> ${esc(s.name)}${dups.includes(s.name) ? ` <span class="rp-warn-i">⚠동명이인</span>` : ``}</label>`).join('') || `<div class="rp-hint">생성·검토된 학생이 없습니다.</div>`}</div>
    ${dups.length ? `<div class="rp-warn">⚠ 동명이인 ${esc(dups.join(', '))} — 자동 제외(수동 전송 권장)</div>` : ``}
    ${skipped.length ? `<div class="rp-warn">미생성 제외 ${skipped.length}명: ${esc(skipped.join(', '))}</div>` : ``}
    <div class="rp-mrow"><button class="rp-btn ghost" onclick="closeRpModal()">취소</button>
      <button class="rp-btn" ${ready.length ? '' : 'disabled'} onclick="doReportSend()">전송 시작</button></div>`);
}
async function doReportSend(){
  const a = activeAsgns()[curAI]; if(!a) return;
  const classId = a.classId;
  const picked = [...document.querySelectorAll('#rp-ov [data-snk]')].filter(c => c.checked).map(c => c.dataset.snk);
  const students = _rpStudents();
  const recipients = picked.map(nk => {
    const s = students.find(x => x.nameKey === nk) || {};
    return { nameKey: nk, name: s.name || nk, msg: _buildMessage(classId, nk, s.name || nk, _curDraft(nk)), status: '대기' };
  });
  closeRpModal();
  if(!recipients.length) return;
  const jid = Date.now() + '_' + Math.floor(Math.random() * 1000);
  try{
    await fbPut(`sendJobs/${instructor.id}/${jid}`, { cls: classId, recipients, status: 'queued', ts: Date.now() });
    toast(`전송 작업 생성 (${recipients.length}명) — 에이전트가 발송`); loadReportJobs();
  }catch(e){ toast('전송 요청 실패 — ' + (e.message || e)); }
}

// ── 전송 상태 ─────────────────────────────────────────────────────────
async function loadReportJobs(){
  if(activeTab !== 'report'){ clearInterval(_rpJobTimer); return; }
  let jobs = {};
  try{ jobs = await fbGet(`sendJobs/${instructor.id}`) || {}; }catch(e){ return; }
  const arr = Object.entries(jobs).sort((x, y) => (y[1].ts || 0) - (x[1].ts || 0)).slice(0, 6);
  const el = document.getElementById('rp-jobs'); if(!el) return;
  el.innerHTML = arr.length ? arr.map(([id, j]) => {
    const recs = j.recipients || [], tot = recs.length;
    const done = recs.filter(r => r.status === '완료').length, err = recs.filter(r => r.status === '실패').length;
    const exc = recs.filter(r => (r.status || '').indexOf('제외') === 0).length;
    let st = j.status === 'done' ? ['done', err ? `완료(실패 ${err})` : '완료']
      : (j.status === 'sending' || done + err > 0) ? ['send', `전송 중 ${done + err}/${tot}`] : ['q', '대기'];
    return `<div class="rp-job">${esc(j.cls || '')} (${tot}명)${exc ? ` <span class="rp-warn-i">제외 ${exc}</span>` : ''}<span class="rp-pill ${st[0]}">${st[1]}</span></div>`;
  }).join('') : `<div class="rp-job">작업 없음</div>`;
}

// ══════════════════════════════════════════════════════════════════════
//  일괄 공지 전송 (PC _build_bulk_tab 이식) — 템플릿 메시지를 담당 학생에게 일괄
// ══════════════════════════════════════════════════════════════════════
let _bulkSel = new Set(), _bulkImg = null, _bulkImgName = '';
function _bulkStudents(){
  const a = activeAsgns()[curAI]; if(!a) return [];
  return sortStu((config._classStudents || {})[a.classId] || []);
}
function _bulkRender(tmpl, name, cls){
  const d = new Date();
  return String(tmpl || '').replace(/\{이름\}/g, name || '').replace(/\{반\}/g, cls || '')
    .replace(/\{날짜\}/g, `${d.getMonth() + 1}/${d.getDate()}`);
}
function renderBulk(mc){
  renderMhdr('일괄 공지');
  if(!config){ mc.innerHTML = makeTb('일괄 공지') + `<div class="empty">⚙️ 설정 후 이용하세요.</div>`; return; }
  const asgns = instructor?.assignments || [];
  if(!asgns.length){ mc.innerHTML = makeTb('일괄 공지') + `<div class="empty">설정 → 담당 수업을 추가해 주세요.</div>`; return; }
  if(curAI >= asgns.length) curAI = 0;
  const classId = asgns[curAI].classId;
  const students = _bulkStudents();
  if(!_bulkSel.size) students.forEach(s => _bulkSel.add(s.nameKey));
  for(const k of [..._bulkSel]) if(!students.some(s => s.nameKey === k)) _bulkSel.delete(k);
  const tmpl = (typeof _bulkTmplCache === 'string') ? _bulkTmplCache : '';
  const imgPv = _bulkImg ? `<div class="rp-imgpv"><img src="${_bulkImg}"><span>${esc(_bulkImgName)}</span><button class="rp-btn ghost" onclick="bulkClearImg()">제거</button><label class="rp-imgopt"><input type="checkbox" id="bulk-imgfirst">이미지 먼저</label></div>` : '';
  const chips = students.map(s => `<label class="rp-ck"><input type="checkbox" ${_bulkSel.has(s.nameKey) ? 'checked' : ''} onchange="bulkToggle('${esc(s.nameKey)}',this.checked)"> ${esc(s.name)}</label>`).join('') || '<div class="rp-hint">학생 없음</div>';

  mc.innerHTML = makeTb('일괄 공지', `${classId} · 담당 학생에게 같은 메시지 일괄 발송`) + `
    <div class="rp-2col">
      <div class="rp-left">
        <div class="bulk-vars">변수:
          <button class="rp-tag k-neutral" onclick="bulkInsertVar('{이름}')">{이름}</button>
          <button class="rp-tag k-neutral" onclick="bulkInsertVar('{반}')">{반}</button>
          <button class="rp-tag k-neutral" onclick="bulkInsertVar('{날짜}')">{날짜}</button>
        </div>
        <textarea class="rp-ta" id="bulk-tmpl" oninput="bulkOnInput(this)" placeholder="예: 안녕하세요 {이름} 학부모님. {날짜} {반} 공지드립니다.">${esc(tmpl)}</textarea>
        <div class="rp-bar" style="margin-top:8px">
          <input type="file" id="bulk-imgfile" accept="image/*" onchange="bulkPickImg(event)" style="font-size:12px;flex:1">
        </div>
        ${imgPv}
        <div class="rp-bar" style="margin-top:10px">
          <span class="rp-ctx">수신자 <b id="bulk-cnt">${[..._bulkSel].length}</b>/${students.length}명</span>
          <a class="rp-pv-toggle" onclick="bulkAll(true)">전체</a>
          <a class="rp-pv-toggle" onclick="bulkAll(false)">해제</a>
          <button class="rp-btn" onclick="bulkSend()" style="margin-left:auto">📢 일괄 전송 →</button>
        </div>
        <div class="rp-cks" style="max-height:200px">${chips}</div>
        <div class="rp-jobs"><div class="rp-jobs-hd">전송 상태</div><div id="rp-jobs"><div class="rp-job">작업 없음</div></div></div>
      </div>
      <div class="rp-right" id="rp-right"></div>
    </div>`;
  bulkPreview();
  loadReportJobs();
  clearInterval(_rpJobTimer); _rpJobTimer = setInterval(loadReportJobs, 2500);
}
let _bulkTmplCache = '';
function bulkOnInput(el){ _bulkTmplCache = el.value; bulkPreview(); }
function bulkToggle(nk, on){ on ? _bulkSel.add(nk) : _bulkSel.delete(nk); const c = document.getElementById('bulk-cnt'); if(c) c.textContent = [..._bulkSel].length; bulkPreview(); }
function bulkAll(on){ const st = _bulkStudents(); _bulkSel = new Set(on ? st.map(s => s.nameKey) : []); renderBulk(document.getElementById('mc')); }
function bulkInsertVar(v){ const ta = document.getElementById('bulk-tmpl'); if(!ta) return; const s = ta.selectionStart, e = ta.selectionEnd; ta.value = ta.value.slice(0, s) + v + ta.value.slice(e); ta.selectionStart = ta.selectionEnd = s + v.length; ta.focus(); _bulkTmplCache = ta.value; bulkPreview(); }
function bulkPreview(){
  const ta = document.getElementById('bulk-tmpl'), el = document.getElementById('rp-right'); if(!el) return;
  const a = activeAsgns()[curAI]; const first = _bulkStudents().find(s => _bulkSel.has(s.nameKey));
  const msg = _bulkRender(ta ? ta.value : '', first ? first.name : '○○○', a ? a.classId : '');
  el.innerHTML = `<div class="rp-pv-hd">📨 ${first ? esc(first.name) : '예시'} · 미리보기 <span class="rp-len">${msg.length}자</span></div>`
    + (_bulkImg ? `<img src="${_bulkImg}" style="max-width:100%;border-radius:8px;margin:8px">` : '')
    + `<pre class="rp-pv-body">${esc(msg) || '<span style="color:var(--gray)">메시지를 입력하세요</span>'}</pre>`;
}
function bulkPickImg(e){
  const f = e.target.files && e.target.files[0]; if(!f){ bulkClearImg(); return; }
  const rd = new FileReader();
  rd.onload = () => { const img = new Image(); img.onload = () => {
    const max = 1280; let { width: w, height: h } = img;
    if(w > max || h > max){ const r = Math.min(max / w, max / h); w = Math.round(w * r); h = Math.round(h * r); }
    const cv = document.createElement('canvas'); cv.width = w; cv.height = h; cv.getContext('2d').drawImage(img, 0, 0, w, h);
    _bulkImg = cv.toDataURL('image/jpeg', 0.82); _bulkImgName = f.name; renderBulk(document.getElementById('mc'));
  }; img.src = rd.result; };
  rd.readAsDataURL(f);
}
function bulkClearImg(){ _bulkImg = null; _bulkImgName = ''; renderBulk(document.getElementById('mc')); }
async function bulkSend(){
  const a = activeAsgns()[curAI]; if(!a) return;
  const classId = a.classId;
  const tmpl = (document.getElementById('bulk-tmpl')?.value || '').trim();
  if(!tmpl) return toast('메시지를 입력하세요');
  const students = _bulkStudents().filter(s => _bulkSel.has(s.nameKey));
  if(!students.length) return toast('수신자를 선택하세요');
  const recipients = students.map(s => ({ nameKey: s.nameKey, name: s.name, msg: _bulkRender(tmpl, s.name, classId), status: '대기' }));
  const job = { cls: classId, recipients, status: 'queued', ts: Date.now() };
  if(_bulkImg){ job.image = _bulkImg; job.imageName = _bulkImgName; job.imageFirst = document.getElementById('bulk-imgfirst')?.checked || false; }
  try{
    await fbPut(`sendJobs/${instructor.id}/${Date.now()}_${Math.floor(Math.random() * 1000)}`, job);
    toast(`일괄 전송 작업 생성 (${recipients.length}명${_bulkImg ? ' · 이미지' : ''}) — 에이전트가 발송`);
    _bulkImg = null; _bulkImgName = ''; loadReportJobs();
  }catch(e){ toast('전송 요청 실패: ' + (e.message || e)); }
}

// ── 모달 유틸 ─────────────────────────────────────────────────────────
function _rpModal(html){
  let ov = document.getElementById('rp-ov');
  if(!ov){ ov = document.createElement('div'); ov.id = 'rp-ov'; ov.className = 'rp-ov'; document.body.appendChild(ov); }
  ov.innerHTML = `<div class="rp-modal">${html}</div>`; ov.classList.add('on');
}
function closeRpModal(){ const ov = document.getElementById('rp-ov'); if(ov) ov.classList.remove('on'); }
