// app-report.js — 리포트 탭: AI 생성·검토·전송 (PC앱 계승 + 웹 통합)
// 기존 데이터 재사용: progressData·getTags·_readNote·dotClass·activeAsgns·config._classStudents
// 키·카톡은 강사 본인 PC 에이전트(로컬). 웹은 맥락 전달 + 검토 + 전송요청만.
//   웹 → campus/{campus}/genJobs/{강사}/{id} → 에이전트 생성 → draft 회신
//   웹 → campus/{campus}/sendJobs/{강사}/{id} → 에이전트 본인 카톡 발송 → 상태 회신

let reportDrafts = {};      // {nameKey: 검토중 문구} — 세션 보관
let _rpJobTimer = null;

// 과제수행도(assign_grade) 코드 → 수행도 라벨(이모지 제거). value 로 전달.
function _gradeLabel(code){
  if(!code) return '';
  const g = (typeof ASSIGN_GRADES !== 'undefined') ? ASSIGN_GRADES.find(x => x.key === code) : null;
  return g ? g.label.replace(/[^가-힣]/g, '').trim() : '';
}

// ── 학생 1명의 생성 맥락(genJob) — 실데이터로 build_single_prompt 입력 구성 ──
function _reportCtx(classId, subject, nk, name){
  const pd = progressData[`${classId}|${subject}`] || {};
  const tagsRaw = getTags(classId, nk, subject) || {};
  const tags = { ...tagsRaw }; delete tags.assign_grade;   // 과제수행도는 value로 따로(중복 방지)
  return {
    nameKey: nk, cls: classId, displayName: name, sheet: '',
    items: [{ subject, value: _gradeLabel(tagsRaw.assign_grade),
              progress: pd.progress || '', homework: pd.homework || '' }],
    tags: tags,
    note: _readNote(nk) || '',
    status: 'queued'
  };
}

function _rpStudents(){
  const a = activeAsgns()[curAI]; if(!a) return [];
  return sortStu((config._classStudents || {})[a.classId] || []);
}

// ── 메인 렌더 ─────────────────────────────────────────────────────────
function renderReport(mc){
  renderMhdr('리포트');
  if(!config){ mc.innerHTML = makeTb('리포트') + `<div class="empty">⚙️ 설정에서 연결 후 이용하세요.</div>`; return; }
  const asgns = instructor?.assignments || [];
  if(!asgns.length){ mc.innerHTML = makeTb('리포트') + `<div class="empty">설정 → 내 담당 수업에서<br>담당 수업을 추가해 주세요.</div>`; return; }
  if(curAI >= asgns.length) curAI = 0;
  const a = asgns[curAI]; const { classId, subject } = a;
  const pkey = `${classId}|${subject}`; const pd = progressData[pkey] || {};
  const students = _rpStudents();

  const ctxLine = [pd.progress ? `진도 ${esc(pd.progress)}` : '', pd.homework ? `과제 ${esc(pd.homework)}` : '']
    .filter(Boolean).join(' · ') || '진도·과제 미입력';

  const rows = students.map(s => {
    const nk = s.nameKey;
    const draft = (nk in reportDrafts) ? reportDrafts[nk] : (_readNote(nk) || '');
    const note = _readNote(nk) || '';
    const dot = dotClass(classId, nk, subject);
    const ready = !!draft.trim();
    return `<div class="rp-row">
      <div class="rp-who">
        <span class="dot ${dot}"></span><b>${esc(s.name)}</b>
        ${note ? `<span class="rp-badge ok">메모</span>` : ``}
        ${ready ? `<span class="rp-badge ok">검토중</span>` : `<span class="rp-badge no">미생성</span>`}
      </div>
      <textarea class="rp-ta" id="rp-${esc(nk)}" oninput="onRpEdit('${esc(nk)}',this)" placeholder="AI 생성 후 검토·수정 — 직접 메모는 반드시 반영됩니다">${esc(draft)}</textarea>
      <div class="rp-act">
        <button class="rp-gen" onclick="genReportOne('${esc(nk)}')">✨ ${ready ? '다시생성' : '생성'}</button>
        <div class="rp-tones">
          <button class="rp-tone" onclick="genReportOne('${esc(nk)}','warm')" title="더 따뜻하게">따뜻</button>
          <button class="rp-tone" onclick="genReportOne('${esc(nk)}','concise')" title="더 간결하게">간결</button>
          <button class="rp-tone" onclick="genReportOne('${esc(nk)}','detailed')" title="더 구체적으로">구체</button>
        </div>
      </div>
    </div>`;
  }).join('') || `<div class="empty">이 반에 학생이 없습니다.</div>`;

  mc.innerHTML = makeTb('리포트', `${classId} · ${subject}`) + `
    <div class="rp-wrap">
      <div class="rp-bar">
        <span class="rp-ctx">${ctxLine}</span>
        <button class="rp-btn ghost" onclick="genReportAll()">✨ 일괄 생성</button>
        <button class="rp-btn" onclick="openReportSend()">전송 대상 선택 →</button>
      </div>
      <div class="rp-list">${rows}</div>
      <div class="rp-jobs"><div class="rp-jobs-hd">전송 상태</div><div id="rp-jobs"><div class="rp-job">작업 없음</div></div></div>
    </div>`;
  loadReportJobs();
  clearInterval(_rpJobTimer); _rpJobTimer = setInterval(loadReportJobs, 2500);
}

function onRpEdit(nk, el){ reportDrafts[nk] = el.value; }

// ── 생성 (개별/톤/일괄) ──────────────────────────────────────────────
async function _pollDraft(jid, ms = 30000){
  const t0 = Date.now();
  while(Date.now() - t0 < ms){
    const j = await fbGet(`genJobs/${instructor.id}/${jid}`);
    if(j && j.status === 'done') return j.draft;
    if(j && j.status === 'error') throw new Error(j.error || '생성 실패');
    await new Promise(r => setTimeout(r, 800));
  }
  throw new Error('시간초과 — 에이전트 실행 확인');
}

async function genReportOne(nk, tone){
  const a = activeAsgns()[curAI]; if(!a) return;
  const { classId, subject } = a;
  const name = (_rpStudents().find(s => s.nameKey === nk) || {}).name || nk;
  const ta = document.getElementById('rp-' + nk);
  if(ta){ ta.value = tone ? '🎚 톤 조절 중…' : '✨ AI 생성 중…'; }
  const job = _reportCtx(classId, subject, nk, name);
  if(tone){ job.tone = tone; job.currentDraft = reportDrafts[nk] || ''; }
  const jid = Date.now() + '_' + Math.floor(Math.random() * 1000);
  try{
    await fbPut(`genJobs/${instructor.id}/${jid}`, job);
    const draft = await _pollDraft(jid);
    reportDrafts[nk] = draft;
    if(ta) ta.value = draft;
  }catch(e){
    if(ta) ta.value = '[' + (e.message || e) + ']';
    toast('생성 실패 — 에이전트 확인');
  }
}

async function genReportAll(){
  const a = activeAsgns()[curAI]; if(!a) return;
  toast('일괄 생성 시작 — 에이전트가 순차 처리합니다');
  for(const s of _rpStudents()){ await genReportOne(s.nameKey); }
}

// ── 전송 ──────────────────────────────────────────────────────────────
function openReportSend(){
  const a = activeAsgns()[curAI]; if(!a) return;
  const { classId } = a;
  const students = _rpStudents();
  const ready = students.filter(s => (reportDrafts[s.nameKey] || '').trim());
  const skipped = students.filter(s => !(reportDrafts[s.nameKey] || '').trim()).map(s => s.name);
  const cnt = {}; ready.forEach(s => cnt[s.name] = (cnt[s.name] || 0) + 1);
  const dups = [...new Set(ready.map(s => s.name).filter(n => cnt[n] > 1))];

  const body = `<div class="rp-modal">
    <h3>카카오톡 전송 대상</h3>
    <div class="rp-hint">전송 대상 ${ready.length}명 — 제외할 학생은 체크 해제</div>
    <div class="rp-cks">${ready.map(s => `<label class="rp-ck"><input type="checkbox" checked data-snk="${esc(s.nameKey)}"> ${esc(s.name)}${dups.includes(s.name) ? ` <span class="rp-warn-i">⚠동명이인</span>` : ``}</label>`).join('') || `<div class="rp-hint">생성·검토된 학생이 없습니다.</div>`}</div>
    ${dups.length ? `<div class="rp-warn">⚠ 동명이인 ${esc(dups.join(', '))} — 오발송 위험으로 자동 제외됩니다(수동 전송 권장).</div>` : ``}
    ${skipped.length ? `<div class="rp-warn">미생성 제외 ${skipped.length}명: ${esc(skipped.join(', '))}</div>` : ``}
    <div class="rp-mrow">
      <button class="rp-btn ghost" onclick="closeReportModal()">취소</button>
      <button class="rp-btn" ${ready.length ? '' : 'disabled'} onclick="doReportSend()">전송 시작</button>
    </div>
  </div>`;
  let ov = document.getElementById('rp-ov');
  if(!ov){ ov = document.createElement('div'); ov.id = 'rp-ov'; ov.className = 'rp-ov'; document.body.appendChild(ov); }
  ov.innerHTML = body; ov.classList.add('on');
}
function closeReportModal(){ const ov = document.getElementById('rp-ov'); if(ov) ov.classList.remove('on'); }

async function doReportSend(){
  const a = activeAsgns()[curAI]; if(!a) return;
  const { classId } = a;
  const picked = [...document.querySelectorAll('#rp-ov [data-snk]')].filter(c => c.checked).map(c => c.dataset.snk);
  const students = _rpStudents();
  const recipients = picked.map(nk => {
    const s = students.find(x => x.nameKey === nk) || {};
    return { nameKey: nk, name: s.name || nk, msg: (reportDrafts[nk] || '').trim(), status: '대기' };
  });
  closeReportModal();
  if(!recipients.length) return;
  const jid = Date.now() + '_' + Math.floor(Math.random() * 1000);
  try{
    await fbPut(`sendJobs/${instructor.id}/${jid}`, { cls: classId, recipients, status: 'queued', ts: Date.now() });
    toast(`전송 작업 생성 (${recipients.length}명) — 에이전트가 발송합니다`);
    loadReportJobs();
  }catch(e){ toast('전송 요청 실패 — ' + (e.message || e)); }
}

// ── 전송 상태 (sendJobs 라이브) ──────────────────────────────────────
async function loadReportJobs(){
  if(activeTab !== 'report'){ clearInterval(_rpJobTimer); return; }
  let jobs = {};
  try{ jobs = await fbGet(`sendJobs/${instructor.id}`) || {}; }catch(e){ return; }
  const arr = Object.entries(jobs).sort((x, y) => (y[1].ts || 0) - (x[1].ts || 0)).slice(0, 6);
  const el = document.getElementById('rp-jobs'); if(!el) return;
  el.innerHTML = arr.length ? arr.map(([id, j]) => {
    const recs = j.recipients || [], tot = recs.length;
    const done = recs.filter(r => r.status === '완료').length;
    const err = recs.filter(r => r.status === '실패').length;
    const exc = recs.filter(r => (r.status || '').indexOf('제외') === 0).length;
    let st = j.status === 'done' ? ['done', err ? `완료(실패 ${err})` : '완료']
      : (j.status === 'sending' || done + err > 0) ? ['send', `전송 중 ${done + err}/${tot}`]
      : ['q', '대기'];
    return `<div class="rp-job">${esc(j.cls || '')} (${tot}명)${exc ? ` <span class="rp-warn-i">제외 ${exc}</span>` : ''}<span class="rp-pill ${st[0]}">${st[1]}</span></div>`;
  }).join('') : `<div class="rp-job">작업 없음</div>`;
}
