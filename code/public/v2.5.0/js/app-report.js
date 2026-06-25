// app-report.js — 리포트 탭: AI 생성·검토·미리보기·전송 (PC앱 충실 이식 + 웹 통합)
// 기존 재사용: progressData·getTags·_readNote·dotClass·activeAsgns·activeCourses·getCurriculumForSubject
// 메시지 형식(build_message)·말투(ai_style)·미리보기를 PC앱과 동일하게 재현.
// 키·카톡·문체분석은 강사 PC 에이전트(로컬). 웹=맥락·검토·미리보기·전송요청.

let reportDrafts = {};      // {nameKey: 검토중 특이사항}
let _rpJobTimer = null;
let _rpActive = null;       // 우측 미리보기 대상 학생(nameKey)
let _excludeProg = new Set(); // {classId|subject} — 이번 발송 메시지서 진도/과제 제외 (세션 메모리, PC _toggle_exclude_prog 이식)
let _rpActiveCls = null;      // 트리서 선택한 활성 학생의 반(리포트 편집/전송 스코프)
let _treeOpen = {};           // {classId: bool} 트리 펼침 상태

// ── 디렉토리 트리 레일 (리포트·일괄 공통) ──────────────────────────────
function _myClassList(){   // 내 담당 반들(중복 제거, classId별 1개 + group)
  const seen = {}, out = [];
  (activeAsgns() || []).forEach(a => { if(!seen[a.classId]){ seen[a.classId] = 1; out.push({ classId: a.classId, group: a.group || '' }); } });
  return out;
}
function _clsStudents(classId){ return sortStu((config._classStudents || {})[classId] || []); }
function _allMyStudents(){ const m = {}; _myClassList().forEach(c => _clsStudents(c.classId).forEach(s => { m[s.nameKey] = { name: s.name, classId: c.classId }; })); return m; }
function _todayGroup(){ const dow = (typeof _devDate !== 'undefined' && _devDate ? new Date(_devDate) : new Date()).getDay(); return [1,3,5].includes(dow) ? 'M' : ([2,4,6].includes(dow) ? 'T' : ''); }
function _isTodayCls(c){ const tg = _todayGroup(); return !!c.group && !!tg && c.group.toUpperCase() === tg; }
function _clsOpen(c, mode){ return (c.classId in _treeOpen) ? _treeOpen[c.classId] : (mode === 'bulk' ? true : _isTodayCls(c)); }
function toggleTreeCls(cid, mode){ const c = _myClassList().find(x => x.classId === cid) || { classId: cid }; _treeOpen[cid] = !_clsOpen(c, mode); renderMain(); }
// mode: 'report'(학생 클릭 단일선택) | 'bulk'(체크박스 다중선택)
function _railTreeHtml(mode){
  const classes = _myClassList();
  if(!classes.length) return `<div class="rp-hint" style="padding:12px">담당 수업 없음</div>`;
  return classes.map(c => {
    const cid = c.classId, opened = _clsOpen(c, mode), studs = _clsStudents(cid);
    const today = _isTodayCls(c) ? '<span class="rp-today">오늘</span>' : '';
    const cb = mode === 'bulk'
      ? `<input type="checkbox" data-clsbox="${esc(cid)}" onclick="event.stopPropagation();bulkChkCls('${esc(cid)}',this.checked)" ${studs.length && studs.every(s => _bulkSel.has(s.nameKey)) ? 'checked' : ''}>` : '';
    const head = `<div class="rp-cls-h" onclick="toggleTreeCls('${esc(cid)}','${mode}')"><span class="rp-arw">${opened ? '▾' : '▸'}</span>${cb}<span class="rp-cls-nm">${esc(cid)}</span>${today}<span class="rp-cls-cnt">${studs.length}</span></div>`;
    let rows = '';
    if(opened) rows = studs.map(s => {
      if(mode === 'bulk') return `<label class="rp-stu"><input type="checkbox" onclick="bulkChk('${esc(s.nameKey)}',this.checked)" ${_bulkSel.has(s.nameKey) ? 'checked' : ''}><span class="rp-stu-nm">${esc(s.name)}</span></label>`;
      const has = !!_curDraft(s.nameKey).trim();
      const on = (s.nameKey === _rpActive && cid === _rpActiveCls) ? ' on' : '';
      return `<div class="rp-stu${on}" data-nk="${esc(s.nameKey)}" onclick="setRpActive('${esc(cid)}','${esc(s.nameKey)}')"><span class="rp-stu-nm">${esc(s.name)}</span><span class="rp-badge ${has ? 'ok' : 'no'}">${has ? '검토중' : '미생성'}</span></div>`;
    }).join('');
    return `<div class="rp-cls">${head}${rows}</div>`;
  }).join('');
}

// 문체 옵션 (ai_style.py STYLE_ORDER/LABELS 미러)
const RP_STYLES = [
  ['auto', '✍️ 내 말투 자동 (전송 노트 학습)'],
  ['warm_detail', '📖 따뜻·상세형'],
  ['balanced', '📋 정돈·균형형'],
  ['info_coach', '🎯 정보·코칭형'],
  ['concise', '⚡ 간결·요점형'],
];
// 문체별 설명·예시 (ai_style.py STYLE_PRESETS 미러) — 설정 화면 안내용
const RP_STYLE_INFO = {
  auto: { desc: '본인이 전송한 노트를 분석해 말투·분량·이모지·어조를 자동 반영합니다. 전송 노트가 쌓일수록 더 정교해집니다.', ex: [] },
  warm_detail: {
    desc: '4문장 이상 충분히 상세하게. 학생의 노력·태도 변화를 따뜻하게 공감하며 구체적으로 서술하고, 긍정적인 순간엔 😊 같은 부드러운 이모지를 한두 번. 격식체(~습니다)를 유지하되 다정·응원하는 어조.',
    ex: ['오늘은 피곤해하는 모습이 있었지만, 교재 오답도 성실하게 수정하고 설명도 집중해서 잘 들으며 수업에 참여했습니다. 어려운 부분은 스스로 질문하며 내용을 잘 이해했습니다.😊',
         '어려운 유형도 빠르게 이해하며 성실하게 수업에 참여하는 모습이 좋았습니다.😊'] },
  balanced: {
    desc: '3~4문장 적정 분량. 격식체로 명료하고 정돈되게, 담백하면서도 따뜻한 어조. 수업 내용과 공지·당부는 문단을 나누고, 이모지·과한 느낌표는 쓰지 않습니다.',
    ex: ['설명을 빠르게 이해하며 막힘 없이 수업을 진행하고, 궁금한 점은 스스로 질문하는 능동적인 모습이 돋보였습니다. 과제도 완벽히 완료하여 오늘도 알찬 수업이었습니다.'] },
  info_coach: {
    desc: '수업 활동·시험·일정을 구체적으로 명시. 학습 방향·코칭을 직설적이고 분명하게 전달하고, 보강·재검사·준비물·등원시간은 날짜·시간까지. 격식체로 사실·지도 중심.',
    ex: ['기출모의고사 3회 시행했습니다. 논술형 작성이 다소 미비합니다. 오답노트를 꼼꼼히 잘 작성해왔으며, 몰랐던 문제 복습이 철저합니다.',
         '실전모의고사 1회 진행. 논술형 12번 재검사 예정입니다. 6/16(화) 4:50 시험대비 보강 있습니다.'] },
  concise: {
    desc: '2~3문장 이내로 핵심만 간결하게. 점수·진도·핵심 사실 위주, 항목이 여럿이면 짧은 줄바꿈으로 구분. 불필요한 수식·감상은 넣지 않습니다.',
    ex: ['25년 동수원기출 시험 100점. 금일 학습도 집중력 있게 진행하며 완료했습니다.'] },
};
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
  if(tags.exam && TAGS.exam){ let _ex = tags.exam; if(typeof _ex === 'string') _ex = _ex ? [_ex] : []; (_ex || []).forEach(k => { const t = TAGS.exam.find(x => x.key === k); if(t) out.push({ label: '시험 ' + t.label, kind: (k === 'top' || k === 'good') ? 'pos' : 'warn' }); }); }
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
function _ini(name){ const n = String(name || ''); return n.length > 2 ? n.slice(-2) : n; }   // 아바타 이니셜(이름 끝 2자)

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
    const ex = _excludeProg.has(`${classId}|${sub}`);   // 발송 제외 → 그 교재의 진도·과제·수행도 전부 빈값(메시지·생성 동시 제외)
    classInfo[sub] = { progress: ex ? '' : (pd.progress || ''), homework: ex ? '' : (pd.homework || '') };
    assignMap[sub] = ex ? '' : _assignText((getTags(classId, nk, sub) || {}).assign_grade);
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

// ── 에이전트 실행 감지 + 미실행 시 설치 안내 ──────────────────────────
// 에이전트가 agents/{id}.ts(ms) 하트비트를 ~15s마다 기록 → 90s 이내면 살아있음
const AGENT_DL = 'https://github.com/idocho/dailyReportWizard2/releases/download/agent/DRW-AI-Agent-0.93.exe';
let _rpPending = null;
async function _agentAlive(){
  try{ const a = await fbGet(`agents/${instructor.id}`); return !!(a && a.ts && Date.now() - a.ts < 90000); }
  catch(_){ return false; }
}
function _agentGuide(proceed){
  _rpPending = proceed || null;
  _rpModal(`<h3>강사 에이전트가 필요합니다</h3>
    <div class="rp-hint">AI 생성·카톡 전송은 본인 PC의 <b>강사 에이전트</b>가 처리합니다. 지금 실행 중인 에이전트가 감지되지 않았습니다.</div>
    <ul style="font-size:12.5px;color:var(--sub);line-height:1.9;margin:10px 0 4px;padding-left:18px">
      <li>이미 설치돼 있으면 <b>DRW AI Agent</b>를 실행하세요(시작메뉴·트레이).</li>
      <li>처음이라면 아래에서 내려받아 1회 설치·설정 후 다시 시도.</li>
      <li style="color:var(--gray)">실행 시 Windows SmartScreen 경고가 뜨면 <b>추가 정보 → 실행</b>.</li></ul>
    <div class="rp-mrow">
      <a class="rp-btn" href="${AGENT_DL}" style="text-decoration:none;text-align:center">⬇ 에이전트 다운로드</a>
      <button class="rp-btn ghost" onclick="window.open('./guide.html','_blank')">설치 가이드</button>
    </div>
    <div class="rp-mrow" style="margin-top:8px">
      <button class="rp-btn ghost" onclick="closeRpModal()">닫기</button>
      ${proceed ? `<button class="rp-btn ghost" onclick="_rpProceed()">그래도 대기열 추가</button>` : ''}
    </div>`);
}
function _rpProceed(){ const f = _rpPending; _rpPending = null; closeRpModal(); if(f) f(); }

// ── 메인 렌더 ─────────────────────────────────────────────────────────
function renderReport(mc){
  renderMhdr('리포트');
  if(!config){ mc.innerHTML = makeTb('리포트') + `<div class="empty">⚙️ 설정 후 이용하세요.</div>`; return; }
  const asgns = instructor?.assignments || [];
  if(!asgns.length){ mc.innerHTML = makeTb('리포트') + `<div class="empty">설정 → 담당 수업을 추가해 주세요.</div>`; return; }
  if(curAI >= asgns.length) curAI = 0;
  const classes = _myClassList();
  // 활성 반 기본값: 기존 유효하면 유지, 아니면 오늘 수업(또는 첫 반)
  if(!_rpActiveCls || !classes.some(c => c.classId === _rpActiveCls)){
    _rpActiveCls = (classes.find(_isTodayCls) || classes[0] || {}).classId || null;
  }
  const actStu = _rpActiveCls ? _clsStudents(_rpActiveCls) : [];
  if(!_rpActive || !actStu.some(s => s.nameKey === _rpActive)) _rpActive = actStu[0]?.nameKey || null;
  const styleLbl = (RP_STYLES.find(s => s[0] === (instructor?.ai_style_mode || 'auto')) || RP_STYLES[0])[1];
  const todayN = classes.filter(_isTodayCls).length;
  const draftAll = Object.keys(_allMyStudents()).filter(nk => _curDraft(nk).trim()).length;

  // 발송 제외 토글 — 활성 반의 진도/과제 입력 과목만
  const cid0 = _rpActiveCls;
  const exSubs = cid0 ? [...new Set((activeAsgns() || []).filter(x => x.classId === cid0).map(x => x.subject))]
    .filter(sub => { const pd = progressData[`${cid0}|${sub}`] || {}; return pd.progress || pd.homework; }).sort() : [];
  const exBar = exSubs.length ? `<div class="rp-exbar">발송 진도/과제(${esc(cid0)}): ${exSubs.map(sub => {
    const off = _excludeProg.has(`${cid0}|${sub}`);
    return `<button class="rp-extag${off ? ' off' : ''}" onclick="toggleExProg('${esc(cid0)}','${esc(sub)}')" title="${off ? '발송 제외됨 — 누르면 포함' : '발송에 포함 — 누르면 제외'}">${off ? '✕' : '✓'} ${esc(sub)}</button>`;
  }).join('')}</div>` : '';

  mc.innerHTML = makeTb('리포트·전송', `활성 반 ${cid0 || '—'}`) + `
    <div class="rp-bar">
      <span class="rp-ctx">문체 <b>${esc(styleLbl)}</b> <a class="rp-ctx-link" onclick="goAiSettings()">AI설정에서 변경</a></span>
      <button class="rp-btn ghost" onclick="genReportAll()" style="margin-left:auto">✨ 일괄 생성(${esc(cid0 || '')})</button>
      <button class="rp-btn" onclick="openReportSend()">전송 →</button>
    </div>
    ${exBar}
    <div class="rp-grid">
      <div class="rp-rail">
        <div class="rp-rail-h">오늘 수업 <b>${todayN}</b>반 · 발송문 <b>${draftAll}</b></div>
        <div class="rp-rail-list">${_railTreeHtml('report')}</div>
      </div>
      <div class="rp-edit" id="rp-edit"></div>
      <div class="rp-right" id="rp-right"></div>
      <div class="rp-statcol">
        <div class="rp-rail-h">전송 모니터 <span class="rp-live"><i></i>실시간</span></div>
        <div id="rp-jobs" class="rp-statcol-list"><div class="rp-job">작업 없음</div></div>
      </div>
    </div>`;
  _renderRpEditor();
  _renderRpPreview();
  loadReportJobs();
  clearInterval(_rpJobTimer); _rpJobTimer = setInterval(loadReportJobs, 2500);
}

// 진도/과제 발송 제외 토글 (PC _toggle_exclude_prog) — 메시지·AI 생성서 동시 제외
function toggleExProg(cls, sub){
  const k = `${cls}|${sub}`;
  _excludeProg.has(k) ? _excludeProg.delete(k) : _excludeProg.add(k);
  renderReport(document.getElementById('mc'));
}

// 문체는 AI설정 단일 출처 — 리포트 탭에선 표시만, 변경은 설정으로 이동
function goAiSettings(){ goNav('setting'); if(typeof setStg === 'function') setStg('style'); }

// 가운데 편집 열 = 선택 학생 1명 (요약·메모·발송문·생성)
function _renderRpEditor(){
  const el = document.getElementById('rp-edit'); if(!el) return;
  const s = _rpActiveCls && _rpActive ? _clsStudents(_rpActiveCls).find(x => x.nameKey === _rpActive) : null;
  if(!s){ el.innerHTML = `<div class="rp-pv-empty">왼쪽 트리에서 학생을 선택하세요.</div>`; return; }
  const nk = s.nameKey, classId = _rpActiveCls;
  const note = _curDraft(nk), memo = _readNote(nk) || '';
  const d = _rpData(classId, nk);
  const exCnt = d.subjects.filter(sub => _excludeProg.has(`${classId}|${sub}`)).length;
  const multi = d.subjects.length > 1;
  const summary = d.subjects.map(sub => {
    if(_excludeProg.has(`${classId}|${sub}`)) return '';   // 발송 제외 교재 → 중앙 패널서도 숨김
    const ci = d.classInfo[sub], ag = d.assignMap[sub];
    const metrics = [ci.progress && ['진도', ci.progress], ci.homework && ['과제', ci.homework], ag && ['수행도', ag]]
      .filter(Boolean).map(([k, v]) => `<div class="rp-metric"><div class="k">${k}</div><div class="v">${esc(v)}</div></div>`).join('');
    const obs = _obsTagLabels(getTags(classId, nk, sub));
    const obsHtml = obs.length ? `<div class="rp-obs">${obs.map(o => `<span class="rp-tag k-${o.kind}">${esc(o.label)}</span>`).join('')}</div>` : '';
    if(!metrics && !obs.length) return '';
    return `${multi ? `<div class="rp-sub" style="margin-bottom:5px"><b>${esc(sub)}</b></div>` : ''}${metrics ? `<div class="rp-metrics">${metrics}</div>` : ''}${obsHtml}`;
  }).join('')
    || `<div class="rp-sub" style="color:var(--gray)">${exCnt ? '발송 제외된 교재만 있습니다 (상단에서 포함 가능)' : '진도·과제·수행도·관찰 미입력'}</div>`;
  el.innerHTML = `
    <div class="rp-ed-h">
      <div><h2>${esc(s.name)}</h2><div class="rp-ed-meta">${esc(classId)}${d.subjects[0] ? ' · ' + esc(multi ? (d.subjects.length + '과목') : d.subjects[0]) : ''} · ${note.trim() ? '검토중' : '미생성'}</div></div></div>
    <div class="rp-ed-sum">${summary}</div>
    ${memo ? `<div class="rp-memo">📝 강사 메모: <b>${esc(memo)}</b> <span>· 입력에서 수정</span></div>` : ''}
    <div class="rp-lbl">발송 특이사항 <span class="hint">AI 생성·검토 · 자동 저장</span></div>
    <textarea class="rp-ta" id="rp-${esc(nk)}" oninput="onRpEdit('${esc(nk)}',this)" onchange="_saveDraft('${esc(nk)}',this.value)" placeholder="✨ 생성을 누르면 강사 메모·데이터로 발송문을 만듭니다 — 검토·수정 후 전송">${esc(note)}</textarea>
    <div class="rp-act"><button class="rp-gen" onclick="genReportOne('${esc(nk)}')">✨ ${note.trim() ? '다시 생성' : '생성'}</button></div>`;
}

// 학생 편집 → 미리보기 즉시 갱신 (타이핑 무지연)
function onRpEdit(nk, el){ reportDrafts[nk] = el.value; if(nk === _rpActive) _renderRpPreview(); }
function setRpActive(cid, nk){
  const clsChanged = cid !== _rpActiveCls;
  _rpActiveCls = cid; _rpActive = nk;
  if(clsChanged){ renderMain(); return; }   // 반 바뀌면 발송제외 바 등 반-종속 갱신 위해 전체 재렌더
  document.querySelectorAll('.rp-stu').forEach(r => r.classList.toggle('on', r.dataset.nk === nk));
  _renderRpEditor(); _renderRpPreview();
}
function _renderRpPreview(){
  const el = document.getElementById('rp-right'); if(!el) return;
  const s = _rpActiveCls && _rpActive ? _clsStudents(_rpActiveCls).find(x => x.nameKey === _rpActive) : null;
  if(!s){ el.innerHTML = `<div class="rp-pv-empty">학생을 선택하면<br>실제 발송 미리보기가 표시됩니다.</div>`; return; }
  const msg = _buildMessage(_rpActiveCls, _rpActive, s.name, _curDraft(_rpActive));
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
function _genCtx(classId, nk, name){
  const d = _rpData(classId, nk);
  // 발송 제외 교재는 AI 프롬프트(items)에서 아예 배제 — 빈 item 미전송
  const items = d.subjects.filter(sub => !_excludeProg.has(`${classId}|${sub}`)).map(sub => ({
    subject: sub, value: d.assignMap[sub],
    progress: d.classInfo[sub].progress, homework: d.classInfo[sub].homework,
    gradeLabel: d.tbGrade[sub],
  }));
  // obs 태그 병합(과제수행도 제외 — value로 전달). 발송 제외 교재는 관찰 태그도 제외(교재 단위 일관)
  const tags = {};
  d.subjects.forEach(sub => { if(_excludeProg.has(`${classId}|${sub}`)) return; const t = { ...(getTags(classId, nk, sub) || {}) }; delete t.assign_grade; Object.assign(tags, t); });
  const job = {
    nameKey: nk, cls: classId, displayName: name, sheet: '',
    items, tags, note: _readNote(nk) || '',
    styleMode: instructor?.ai_style_mode || 'auto',
    customPrompt: instructor?.ai_custom_prompt || '',
    status: 'queued',
  };
  return job;
}
async function genReportOne(nk, force){
  if(!force && !await _agentAlive()){ _agentGuide(() => genReportOne(nk, true)); return; }
  const cid = _rpActiveCls; if(!cid) return;
  const name = (_clsStudents(cid).find(s => s.nameKey === nk) || {}).name || nk;
  const ta = document.getElementById('rp-' + nk);
  if(ta){ ta.value = '✨ AI 생성 중…'; }
  const jid = Date.now() + '_' + Math.floor(Math.random() * 1000);
  try{
    await fbPut(`genJobs/${instructor.id}/${jid}`, _genCtx(cid, nk, name));
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
async function genReportAll(force){
  if(!force && !await _agentAlive()){ _agentGuide(() => genReportAll(true)); return; }
  const classId = _rpActiveCls; if(!classId) return;
  const students = _clsStudents(classId).filter(s => _rpData(classId, s.nameKey).subjects.length);
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
// 여러 반의 '검토중'(발송문 작성) 학생을 한 번에 선택 → 반별 잡으로 큐 적재
async function openReportSend(force){
  if(!force && !await _agentAlive()){ _agentGuide(() => openReportSend(true)); return; }
  // 검토완료(발송문 있음) 학생이 있는 반들 — 활성반 우선
  const groups = _myClassList().map(c => ({ cls: c.classId, ready: _clsStudents(c.classId).filter(s => _curDraft(s.nameKey).trim()) }))
    .filter(g => g.ready.length)
    .sort((a, b) => (a.cls === _rpActiveCls ? -1 : b.cls === _rpActiveCls ? 1 : 0));
  if(!groups.length) return toast('발송문이 작성된(검토중) 학생이 없습니다');
  const totalReady = groups.reduce((n, g) => n + g.ready.length, 0);
  const body = groups.map(g => {
    const cnt = {}; g.ready.forEach(s => cnt[s.name] = (cnt[s.name] || 0) + 1);
    const dups = [...new Set(g.ready.map(s => s.name).filter(n => cnt[n] > 1))];
    const rows = g.ready.map(s => `<label class="rp-ck"><input type="checkbox" checked data-snk="${esc(s.nameKey)}" data-cls="${esc(g.cls)}"> ${esc(s.name)}${dups.includes(s.name) ? ` <span class="rp-warn-i">⚠동명이인</span>` : ''}</label>`).join('');
    return `<div class="rp-send-cls"><label class="rp-ck rp-send-clshd"><input type="checkbox" checked onchange="_sendClsToggle('${esc(g.cls)}',this.checked)"> <b>${esc(g.cls)}</b> <span class="rp-cls-cnt">${g.ready.length}</span></label>${rows}</div>`;
  }).join('');
  _rpModal(`<h3>카카오톡 전송 — ${groups.length}반 · ${totalReady}명</h3>
    <div class="rp-hint">검토중(발송문 작성)인 학생만 표시 — 제외할 반/학생 체크 해제. 반별로 큐에 쌓여 순차 발송됩니다.</div>
    <div class="rp-cks" style="max-height:320px">${body}</div>
    <div class="rp-mrow"><button class="rp-btn ghost" onclick="closeRpModal()">취소</button>
      <button class="rp-btn" onclick="doReportSend()">전송 시작</button></div>`);
}
function _sendClsToggle(cls, on){ document.querySelectorAll(`#rp-ov [data-snk][data-cls="${cls.replace(/"/g,'\\"')}"]`).forEach(c => { c.checked = on; }); }
async function doReportSend(){
  const picked = [...document.querySelectorAll('#rp-ov [data-snk]')].filter(c => c.checked).map(c => ({ nk: c.dataset.snk, cls: c.dataset.cls }));
  closeRpModal();
  if(!picked.length) return toast('선택된 학생이 없습니다');
  // 반별로 묶어 잡 생성(반별 history·취소·모니터 단위 유지)
  const byCls = {}; picked.forEach(p => { (byCls[p.cls] = byCls[p.cls] || []).push(p.nk); });
  let jobN = 0, stuN = 0;
  for(const [classId, nks] of Object.entries(byCls)){
    const students = _clsStudents(classId);
    const recipients = nks.map(nk => {
      const s = students.find(x => x.nameKey === nk) || {};
      const note = _curDraft(nk);
      return { nameKey: nk, name: s.name || nk, note, msg: _buildMessage(classId, nk, s.name || nk, note), status: '대기' };
    });
    if(!recipients.length) continue;
    const jid = Date.now() + '_' + Math.floor(Math.random() * 100000);
    try{
      await fbPut(`sendJobs/${instructor.id}/${jid}`, { cls: classId, recipients, status: 'queued', ts: Date.now(), date: todayKey(), instructor: instructor.id });
      jobN++; stuN += recipients.length;
    }catch(e){ toast(`${classId} 전송 요청 실패 — ${e.message || e}`); }
  }
  if(jobN) toast(`전송 큐 적재: ${jobN}반 · ${stuN}명 — 에이전트가 순차 발송`);
  loadReportJobs();
}

// ── 전송 상태 ─────────────────────────────────────────────────────────
async function loadReportJobs(){
  if(activeTab !== 'report' && activeTab !== 'bulk'){ clearInterval(_rpJobTimer); return; }
  let jobs = {};
  try{ jobs = await fbGet(`sendJobs/${instructor.id}`) || {}; }catch(e){ return; }
  const arr = Object.entries(jobs).sort((x, y) => (y[1].ts || 0) - (x[1].ts || 0)).slice(0, 6);
  const hasDone = Object.values(jobs).some(j => j && (j.status === 'done' || j.status === 'canceled' || j.status === 'error'));
  const el = document.getElementById('rp-jobs'); if(!el) return;
  el.innerHTML = (arr.length ? arr.map(([id, j]) => {
    const recs = j.recipients || [], tot = recs.length;
    const done = recs.filter(r => r.status === '완료').length, err = recs.filter(r => r.status === '실패').length;
    const exc = recs.filter(r => (r.status || '').indexOf('제외') === 0).length;
    const inflight = j.status === 'sending' || (done + err > 0 && j.status !== 'done' && j.status !== 'canceled' && j.status !== 'error');
    let st = j.status === 'canceled' ? ['cancel', '취소됨']
      : j.status === 'error' ? ['cancel', '오류']
      : j.status === 'done' ? ['done', err ? `완료·실패${err}` : '완료']
      : inflight ? ['send', '전송 중'] : ['q', '대기'];
    const live = j.status === 'queued' || j.status === 'sending';
    const cancelBtn = live && !j.cancel ? `<a class="rp-jx" onclick="cancelSendJob('${esc(id)}')">취소</a>`
      : (j.cancel && j.status === 'sending') ? `<span class="rp-jx-w">중단 중…</span>` : '';
    const pct = tot ? Math.round((done + err) / tot * 100) : 0;
    return `<div class="rp-job">
      <div class="rp-job-top"><span class="rp-job-cls">${esc(j.cls || '')} <span style="font-weight:400;opacity:.65">${tot}명</span></span><span class="rp-pill ${st[0]}">${st[1]}</span></div>
      ${inflight ? `<div class="rp-bar2"><i style="width:${pct}%"></i></div>` : ''}
      <div class="rp-job-sub"><span>${done + err}/${tot}${exc ? ` · 제외 ${exc}` : ''}${err ? ` · 실패 ${err}` : ''}</span>${cancelBtn}</div>
    </div>`;
  }).join('') : `<div class="rp-job">작업 없음</div>`)
    + (hasDone ? `<div class="rp-jobs-ft"><a onclick="clearDoneJobs()">완료·취소 건 정리</a></div>` : '');
}

// 전송 취소 (PC _cancel_send/_bulk_cancel) — 대기 건은 삭제(에이전트 미실행), 진행 건은 cancel 플래그(현재 학생까지만 발송 후 중단)
async function cancelSendJob(id){
  let j; try{ j = await fbGet(`sendJobs/${instructor.id}/${id}`); }catch(e){ return toast('취소 조회 실패'); }
  if(!j){ loadReportJobs(); return; }
  if(j.status === 'queued'){
    if(!confirm('대기 중인 전송 작업을 취소(삭제)할까요?')) return;
    try{ await fbPut(`sendJobs/${instructor.id}/${id}`, null); toast('대기 작업 취소됨'); }catch(e){ toast('취소 실패: ' + (e.message || e)); }
  }else if(j.status === 'sending'){
    if(!confirm('전송 진행 중입니다. 중단할까요?\n(진행 중인 학생까지는 발송 후 나머지를 멈춥니다)')) return;
    try{ await fbPatch(`sendJobs/${instructor.id}/${id}`, { cancel: true }); toast('중단 요청 — 진행 중 학생까지 발송 후 멈춤'); }catch(e){ toast('취소 실패: ' + (e.message || e)); }
  }else toast('이미 종료된 작업입니다');
  loadReportJobs();
}
// 완료·취소·오류 건 일괄 정리(수동)
async function clearDoneJobs(){
  if(!confirm('완료·취소·오류 건을 모두 삭제할까요?')) return;
  let jobs = {}; try{ jobs = await fbGet(`sendJobs/${instructor.id}`) || {}; }catch(e){ return toast('정리 조회 실패'); }
  const del = Object.entries(jobs).filter(([, j]) => j && ['done', 'canceled', 'error'].includes(j.status));
  if(!del.length) return toast('정리할 건 없음');
  try{ await Promise.all(del.map(([id]) => fbPut(`sendJobs/${instructor.id}/${id}`, null))); toast(`${del.length}건 정리됨`); }
  catch(e){ toast('정리 실패: ' + (e.message || e)); }
  loadReportJobs();
}

// ══════════════════════════════════════════════════════════════════════
//  일괄 공지 전송 (PC _build_bulk_tab 이식) — 템플릿 메시지를 담당 학생에게 일괄
// ══════════════════════════════════════════════════════════════════════
let _bulkSel = new Set(), _bulkImg = null, _bulkImgName = '';
function _bulkRender(tmpl, name, cls){
  const d = new Date();
  return String(tmpl || '').replace(/\{이름\}/g, name || '').replace(/\{반\}/g, cls || '')
    .replace(/\{날짜\}/g, `${d.getMonth() + 1}/${d.getDate()}`);
}
function renderBulk(mc){
  renderMhdr('일괄 공지');
  if(!config){ mc.innerHTML = makeTb('일괄 공지') + `<div class="empty">⚙️ 설정 후 이용하세요.</div>`; return; }
  if(!(instructor?.assignments || []).length){ mc.innerHTML = makeTb('일괄 공지') + `<div class="empty">설정 → 담당 수업을 추가해 주세요.</div>`; return; }
  // 진입 시 기본 전체선택 → 예외만 해제(CM 일괄전송과 조작감 통일)
  const valid = _allMyStudents();
  _bulkSel = new Set(Object.keys(valid));
  const tmpl = (typeof _bulkTmplCache === 'string') ? _bulkTmplCache : '';
  const tmplOpts = _bulkTemplates().map(t => `<option value="${esc(t.name)}">${esc(t.name)}</option>`).join('');
  const imgPv = _bulkImg ? `<div class="rp-imgpv"><img src="${_bulkImg}"><span>${esc(_bulkImgName)}</span><button class="rp-btn ghost" onclick="bulkClearImg()">제거</button><label class="rp-imgopt"><input type="checkbox" id="bulk-imgfirst">이미지 먼저</label></div>` : '';
  const composer = `<div style="padding:14px 16px">
      <div class="bulk-tmpls">저장 템플릿:
        <select id="bulk-tsel" onchange="bulkLoadTmpl(this.value)"><option value="">— 불러오기 —</option>${tmplOpts}</select>
        <button class="rp-btn ghost" onclick="bulkSaveTmpl()" title="현재 메시지를 이름 붙여 저장">💾 저장</button>
        <button class="rp-btn ghost" onclick="bulkDelTmpl()" title="선택한 템플릿 삭제">🗑</button>
      </div>
      <div class="rp-lblr">메시지
        <span style="margin-left:auto;display:flex;gap:4px">
          <button class="rp-btn ghost" style="padding:2px 8px;font-size:11px" onclick="bulkInsertVar('{이름}')">+이름</button>
          <button class="rp-btn ghost" style="padding:2px 8px;font-size:11px" onclick="bulkInsertVar('{반}')">+반</button>
          <button class="rp-btn ghost" style="padding:2px 8px;font-size:11px" onclick="bulkInsertVar('{날짜}')">+날짜</button>
        </span></div>
      <textarea class="rp-ta" id="bulk-tmpl" oninput="bulkOnInput(this)" placeholder="예: 안녕하세요 {이름} 학부모님. {날짜} {반} 공지드립니다.">${esc(tmpl)}</textarea>
      <div class="rp-lblr">이미지 첨부 (선택)</div>
      <div class="rp-bar"><input type="file" id="bulk-imgfile" accept="image/*" onchange="bulkPickImg(event)" style="font-size:12px;flex:1"></div>
      ${imgPv}
      <button class="rp-btn" onclick="bulkSend()" style="width:100%;margin-top:12px">📢 일괄 전송 →</button>
    </div>`;
  mc.innerHTML = makeTb('일괄 공지', '여러 반 가로질러 선택 — 같은 메시지 발송') + `
    <div class="rp-bar">
      <span class="rp-ctx">📢 기본 전체 선택 · 보낼 필요 없는 학생만 체크 해제하세요</span>
    </div>
    <div class="rp-grid">
      <div class="rp-rail">
        <div class="rp-rail-h">수신자 <b id="bulk-cnt2">${_bulkSel.size}</b>명
          <span style="display:flex;gap:4px;margin-left:auto">
            <button class="rp-btn ghost" style="padding:2px 7px;font-size:11px" onclick="bulkAll(true)">전체</button>
            <button class="rp-btn ghost" style="padding:2px 7px;font-size:11px" onclick="bulkAll(false)">해제</button>
          </span>
        </div>
        <div class="rp-rail-list">${_railTreeHtml('bulk')}</div>
      </div>
      <div class="rp-edit" id="rp-edit" style="padding:0">${composer}</div>
      <div class="rp-right" id="rp-right"></div>
      <div class="rp-statcol">
        <div class="rp-rail-h">전송 모니터 <span class="rp-live"><i></i>실시간</span></div>
        <div id="rp-jobs" class="rp-statcol-list"><div class="rp-job">작업 없음</div></div>
      </div>
    </div>`;
  _bulkSyncCls();
  bulkPreview();
  loadReportJobs();
  clearInterval(_rpJobTimer); _rpJobTimer = setInterval(loadReportJobs, 2500);
}
let _bulkTmplCache = '';
function bulkOnInput(el){ _bulkTmplCache = el.value; bulkPreview(); }
// 저장 템플릿 CRUD (PC _bulk_add/del/load_tmpl) — config/instructors/{id}/bulkTemplates 에 영속
function _bulkTemplates(){ return (instructor && Array.isArray(instructor.bulkTemplates)) ? instructor.bulkTemplates : []; }
function _saveBulkTemplates(arr){
  instructor.bulkTemplates = arr;
  try{ if(typeof saveLocal === 'function') saveLocal(); }catch(_){}
  try{ fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`, { bulkTemplates: arr }); }catch(_){}
}
function bulkLoadTmpl(name){
  if(!name) return;
  const t = _bulkTemplates().find(x => x.name === name); if(!t) return;
  _bulkTmplCache = t.body || ''; const ta = document.getElementById('bulk-tmpl'); if(ta) ta.value = _bulkTmplCache; bulkPreview();
}
function bulkSaveTmpl(){
  const body = (document.getElementById('bulk-tmpl')?.value || '').trim();
  if(!body) return toast('저장할 메시지를 먼저 입력하세요');
  const name = (prompt('템플릿 이름 (같은 이름이면 덮어쓰기)', '') || '').trim(); if(!name) return;
  const arr = _bulkTemplates().slice(); const i = arr.findIndex(x => x.name === name);
  if(i >= 0) arr[i] = { name, body }; else arr.push({ name, body });
  _saveBulkTemplates(arr); toast('템플릿 저장: ' + name); renderBulk(document.getElementById('mc'));
}
function bulkDelTmpl(){
  const name = document.getElementById('bulk-tsel')?.value; if(!name) return toast('삭제할 템플릿을 목록에서 고르세요');
  if(!confirm(`템플릿 "${name}" 삭제할까요?`)) return;
  _saveBulkTemplates(_bulkTemplates().filter(x => x.name !== name)); toast('삭제됨: ' + name); renderBulk(document.getElementById('mc'));
}
function _bulkCnt(){ ['bulk-cnt', 'bulk-cnt2'].forEach(id => { const c = document.getElementById(id); if(c) c.textContent = _bulkSel.size; }); }
// 반 체크박스 3-state 동기화 — 전체=checked, 일부=indeterminate, 없음=해제 (트리 재렌더 없이)
function _bulkSyncCls(){ document.querySelectorAll('.rp-rail-list [data-clsbox]').forEach(cb => { const studs = _clsStudents(cb.dataset.clsbox); const n = studs.filter(s => _bulkSel.has(s.nameKey)).length; cb.checked = studs.length > 0 && n === studs.length; cb.indeterminate = n > 0 && n < studs.length; }); }
function _bulkRefreshTree(){ const list = document.querySelector('.rp-grid .rp-rail-list'); if(list) list.innerHTML = _railTreeHtml('bulk'); _bulkSyncCls(); _bulkCnt(); bulkPreview(); }
function bulkChk(nk, on){ on ? _bulkSel.add(nk) : _bulkSel.delete(nk); _bulkSyncCls(); _bulkCnt(); bulkPreview(); }   // 개별 체크: 트리 미재렌더, 반 체크박스 3-state만 동기화
function bulkChkCls(cid, on){ _clsStudents(cid).forEach(s => on ? _bulkSel.add(s.nameKey) : _bulkSel.delete(s.nameKey)); _bulkRefreshTree(); }
function bulkAll(on){ if(on){ Object.keys(_allMyStudents()).forEach(nk => _bulkSel.add(nk)); } else { _bulkSel.clear(); } _bulkRefreshTree(); }
function bulkInsertVar(v){ const ta = document.getElementById('bulk-tmpl'); if(!ta) return; const s = ta.selectionStart, e = ta.selectionEnd; ta.value = ta.value.slice(0, s) + v + ta.value.slice(e); ta.selectionStart = ta.selectionEnd = s + v.length; ta.focus(); _bulkTmplCache = ta.value; bulkPreview(); }
function bulkPreview(){
  const ta = document.getElementById('bulk-tmpl'), el = document.getElementById('rp-right'); if(!el) return;
  const all = _allMyStudents(); const firstNk = [..._bulkSel][0]; const info = firstNk ? all[firstNk] : null;
  const msg = _bulkRender(ta ? ta.value : '', info ? info.name : '○○○', info ? info.classId : '');
  el.innerHTML = `<div class="rp-pv-hd">📨 ${info ? esc(info.name) : '예시'} · 미리보기 <span class="rp-len">${msg.length}자</span></div>`
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
async function bulkSend(force){
  const tmpl = (document.getElementById('bulk-tmpl')?.value || '').trim();
  if(!tmpl) return toast('메시지를 입력하세요');
  if(!force && !await _agentAlive()){ _agentGuide(() => bulkSend(true)); return; }
  const all = _allMyStudents();
  const sel = [..._bulkSel].filter(nk => all[nk]);   // 여러 반 가로질러 선택된 수신자
  if(!sel.length) return toast('수신자를 선택하세요(트리에서 체크)');
  const recipients = sel.map(nk => ({ nameKey: nk, name: all[nk].name, msg: _bulkRender(tmpl, all[nk].name, all[nk].classId), status: '대기' }));
  const clsSet = [...new Set(sel.map(nk => all[nk].classId))];
  // bulk = 공지(데일리리포트 아님) → date 없음(history 미기록). cls는 표시용.
  const job = { cls: clsSet.length > 1 ? `일괄 ${clsSet.length}반` : (clsSet[0] || '일괄'), recipients, status: 'queued', ts: Date.now() };
  if(_bulkImg){ job.image = _bulkImg; job.imageName = _bulkImgName; job.imageFirst = document.getElementById('bulk-imgfirst')?.checked || false; }
  try{
    await fbPut(`sendJobs/${instructor.id}/${Date.now()}_${Math.floor(Math.random() * 1000)}`, job);
    toast(`일괄 전송 작업 생성 (${recipients.length}명·${clsSet.length}반${_bulkImg ? ' · 이미지' : ''}) — 에이전트가 발송`);
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
