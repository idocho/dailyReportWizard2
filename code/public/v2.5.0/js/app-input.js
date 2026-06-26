// ══════════════════════════════════════════════════════════
//  수업 입력
// ══════════════════════════════════════════════════════════
function renderInput(mc){
  renderMhdr('수업 입력');
  if(!config){mc.innerHTML=makeTb('수업 입력',today())+`<div class="empty">⚙️ 설정에서 Firebase 연결 후<br>학생 명단을 불러오세요.</div>`;return;}
  const asgns=instructor?.assignments||[];
  if(!asgns.length){mc.innerHTML=makeTb('수업 입력',today())+`<div class="empty">설정 → 내 담당 수업에서<br>담당 수업을 추가해 주세요.</div>`;return;}
  if(curAI>=asgns.length)curAI=0;
  // activeGroup 초기화 (최초 진입 또는 유효하지 않을 때)
  const availGroups=[...new Set(asgns.map(a=>a.group||''))];
  if(!activeGroup||!availGroups.includes(activeGroup))activeGroup=asgns[curAI]?.group||availGroups[0]||'';
  // curAI가 activeGroup와 불일치하면 해당 그룹 첫 번째 assignment로 보정
  if((asgns[curAI]?.group||'')!==activeGroup){
    const idx=asgns.findIndex(a=>(a.group||'')===activeGroup);
    if(idx>=0)curAI=idx;
  }
  const a=asgns[curAI];
  const {classId, subject} = a;

  // 신규: students/ 에서 classId로 필터된 학생 목록 (이미 로드된 경우 config.classStudents 캐시 활용)
  const students = (config._classStudents||{})[classId] || [];

  // 프리셋 소스: instructor.presets 우선
  const presets=instructor?.presets||config?.presets?.['과제수행도']||DEFAULT_ASSIGN_PRESETS;
  const pkey=`${classId}|${subject}`;
  const pd=progressData[pkey]||{};

  let mTabs='';
  if(asgns.length>1){
    let groupTabHtml='';
    if(availGroups.length>1){
      const grBtns=availGroups.map(function(gr){
        const act=gr===activeGroup;
        const borderColor=act?'var(--indigo)':'transparent';
        const textColor=act?'var(--indigo)':'var(--sub)';
        return '<button onclick="selGroup(\'' +esc(gr)+ '\')" style="flex:1;padding:8px 0;border:none;border-bottom:2px solid '+borderColor+';background:transparent;color:'+textColor+';font-size:12px;font-weight:700;cursor:pointer;font-family:inherit">'+esc(gr||'기타')+'</button>';
      }).join('');
      groupTabHtml='<div style="display:flex;gap:0;background:var(--panel);border-bottom:1px solid var(--border)">'+grBtns+'</div>';
    }
    const grAsgns=_sortedAsgns(asgns).map(function(p){return p.a;}).filter(function(a){return (a.group||'')===activeGroup;});
    const tabs=grAsgns.map(function(x){
      const i=asgns.indexOf(x);
      const sel=i===curAI;
      const bg=sel?'var(--indigo)':'var(--bg)';
      const fg=sel?'#fff':'var(--sub)';
      const curriculum=getCurriculumForSubject(x.classId,x.subject)||'';
      const gsLabel=gsPrefix(curriculum, x.subject);
      return '<button onclick="selA('+i+')" style="padding:5px 12px;border-radius:16px;border:1px solid var(--border);background:'+bg+';color:'+fg+';font-size:11px;font-weight:700;white-space:nowrap;cursor:pointer;font-family:inherit">'+esc(x.classId)+(gsLabel?' <span style="opacity:.7;font-size:9px">'+esc(gsLabel)+'</span> ':' ')+esc(x.subject)+'</button>';
    }).join('');
    mTabs='<div class="m">'+groupTabHtml+'<div style="display:flex;gap:6px;padding:10px 12px;overflow-x:auto;background:var(--panel);border-bottom:1px solid var(--border)">'+tabs+'</div></div>';
  }

  // 진도 피커 초기값 파싱 — curriculum은 classes/{classId}/courses/{subject}/curriculum
  const curriculum=getCurriculumForSubject(classId,subject)||'';
  const gsLabel=gsPrefix(curriculum, subject);
  const curCurr=getCurriculumByGradeSem(curriculum);
  const pgVal=pd.progress||'';
  // pgVal 형식: "대단원 › 소단원" or "대단원" or 자유텍스트
  let pgMainIdx=-1,pgSubIdx=-1,pgFreeVal='',pgIsFree=false;
  if(pgVal&&curCurr.length){
    const sep=pgVal.indexOf(' › ');
    const mainStr=sep>=0?pgVal.slice(0,sep):pgVal;
    const subStr=sep>=0?pgVal.slice(sep+3):'';
    pgMainIdx=curCurr.findIndex(c=>stripIdx(c.main)===mainStr||c.main===mainStr);
    if(pgMainIdx>=0&&subStr){pgSubIdx=curCurr[pgMainIdx].subs.findIndex(s=>stripIdx(s)===subStr||s===subStr);}
    if(pgMainIdx<0){pgIsFree=true;pgFreeVal=pgVal;}
  } else if(pgVal){pgIsFree=true;pgFreeVal=pgVal;}
  if(!curCurr.length){
    pgIsFree=true;
    if(!pgFreeVal)pgFreeVal=pgVal||'';
  }
  const pgMainOpts=curCurr.length
    ? curCurr.map((c,i)=>'<option value="'+i+'"'+(i===pgMainIdx?' selected':'')+'>'+esc(stripIdx(c.main))+'</option>').join('')
    : '';
  const pgSubOpts=pgMainIdx>=0&&curCurr.length
    ? curCurr[pgMainIdx].subs.map((s,i)=>'<option value="'+i+'"'+(i===pgSubIdx?' selected':'')+'>'+esc(stripIdx(s))+'</option>').join('')
    : '';
  const pgPreviewVal=pgMainIdx>=0&&curCurr.length
    ? (pgSubIdx>=0?stripIdx(curCurr[pgMainIdx].main)+' › '+stripIdx(curCurr[pgMainIdx].subs[pgSubIdx]):stripIdx(curCurr[pgMainIdx].main))
    : '';
  const pgPicker=('<div class="pg-picker">'
    +'<select class="sel" id="pg-main" data-pkey="'+esc(pkey)+'" onchange="pgMainChange(this,\''+esc(pkey)+'\')">'
    +'<option value="">'+(curCurr.length?'대단원 선택...':'단원 데이터 없음 (직접 입력 사용)')+'</option>'
    +pgMainOpts
    +'<option value="sep" disabled>──────</option>'
    +'<option value="free"'+(pgIsFree?' selected':'')+'>✏️ 직접 입력</option>'
    +'</select>'
    +'<div class="pg-sub'+(pgMainIdx>=0&&!pgIsFree?' show':'')+'" id="pg-sub-wrap">'
    +'<select class="sel" id="pg-sub" data-pkey="'+esc(pkey)+'" onchange="pgBuild(\''+esc(pkey)+'\')">'
    +'<option value="">소단원 선택...</option>'
    +pgSubOpts
    +'<option value="all"'+(pgSubIdx<0&&pgMainIdx>=0?' selected':'')+'>단원 전체</option>'
    +'</select>'
    +'</div>'
    +'<input class="inp pg-free'+(pgIsFree?' show':'')+'" id="pg-free" placeholder="직접 입력" value="'+esc(pgFreeVal)+'" data-pkey="'+esc(pkey)+'" oninput="pgBuild(\''+esc(pkey)+'\')">'
    +'<div class="pg-preview'+(pgPreviewVal||pgIsFree?' show':'')+(pgIsFree?' free':'')+'" id="pg-preview">'
    +'<span>'+(pgIsFree?'📝':'📖')+'</span>'
    +'<span id="pg-pv">'+esc(pgIsFree?pgFreeVal:pgPreviewVal)+'</span>'
    +'</div>'
    +'</div>');

  const hw=_parseHwStr(pd.homework||'');
  const hwTypeBtns=['page','prob','free'].map(t=>{
    const sel=t===hw.type;
    const lbl={page:'p. 페이지',prob:'# 번호',free:'직접 입력'}[t];
    return `<button class="hw-tb${sel?' sel '+t:''}" data-t="${t}" onclick="hwSetType('${t}','${esc(pkey)}')">${lbl}</button>`;
  }).join('');
  const hwPrevVal=hw.type!=='free'&&hw.to?(hw.from?(hw.type==='page'?`p.${hw.from}~p.${hw.to}`:`#${hw.from}~#${hw.to}`):(hw.type==='page'?`~p.${hw.to}`:`~#${hw.to}`)):'';
  const hwPicker=`<div class="hw-picker">
    <div class="hw-types">${hwTypeBtns}</div>
    <div class="hw-num-row${hw.type!=='free'?' show':''}" id="hw-nums">
      <input class="hw-num" id="hw-from" type="number" min="1" placeholder="시작" value="${esc(hw.from)}" oninput="hwBuild('${esc(pkey)}')">
      <span class="hw-tilde">~</span>
      <input class="hw-num" id="hw-to" type="number" min="1" placeholder="끝" value="${esc(hw.to)}" oninput="hwBuild('${esc(pkey)}')">
    </div>
    <input class="inp hw-free${hw.type==='free'?' show':''}" id="hw-free" placeholder="직접 입력" value="${esc(hw.raw)}" oninput="hwBuild('${esc(pkey)}')">
    <div class="hw-preview ${hw.type==='free'?'empty':hwPrevVal?hw.type:'empty '+hw.type}" id="hw-preview" style="${hw.type==='free'?'display:none':''}">
      <span id="hw-pi">${hw.type==='page'?'📄':'🔢'}</span>
      <span id="hw-pv" style="font-family:monospace;font-size:10px">${esc(hwPrevVal)||'—'}</span>
    </div>
  </div>`;
  const pForm=`<div class="pf">
    <div style="font-size:12px;font-weight:700;color:var(--sub);margin-bottom:10px">📚 오늘 수업 — ${esc(classId)} · ${gsLabel?`<span style="color:var(--indigo);font-size:10px;font-weight:700;margin-right:3px">${esc(gsLabel)}</span>`:''}${esc(subject)}</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div><div class="fl">진도</div>${pgPicker}</div>
      <div><div class="fl">과제</div>${hwPicker}</div>
    </div>
  </div>`;

  const dk=todayKey();
  const done=students.filter(s=>tagData?.[s.nameKey]?.[subject]?.[dk]?.assign_grade).length;
  let dtRows='';

  for(const s of students){
    const nameKey=s.nameKey;
    const displayName=s.name||nameKey;
    // 특이사항: 학생별 단일 필드(v2.1.1) → __note__. 구 데이터(과목별) fallback.
    const note=_readNote(nameKey);
    const dc=dotClass(classId,nameKey,subject);
    const tags=tagData?.[nameKey]?.[subject]?.[dk]||{};

    // 과제 고정 등급 (택1)
    const agBtns=ASSIGN_GRADES.map(g=>{
      const sel=tags.assign_grade===g.key;
      return `<button class="tg-radio${sel?' sel-c ag-'+g.key:''}" data-k="${esc(g.key)}" onclick="onAssignGrade(this,'${esc(classId)}','${esc(nameKey)}','${esc(subject)}')">${esc(g.label)}</button>`;
    }).join('');
    // 추가 프리셋 (복수선택)
    const apBtns=presets.map(p=>{
      const sel=(tags.assign_tags||[]).includes(p);
      return `<button class="tg-check${sel?' sel-m':''}" data-p="${esc(p)}" onclick="onAssignTag(this,'${esc(classId)}','${esc(nameKey)}','${esc(subject)}')">${esc(p)}</button>`;
    }).join('');

    // condition 버튼 (PES 화살표)
    const condBtns=TAGS.condition.map(t=>{
      const sel=tags.condition===t.key;
      const rot=COND_ARROWS[t.key]??90;
      const svg=`<svg width="12" height="12" viewBox="0 0 24 24" style="transform:rotate(${rot}deg);flex-shrink:0"><polygon points="12,2 22,22 12,16 2,22" fill="currentColor"/></svg>`;
      return `<button class="tg-radio${sel?' sel-c':''}" data-k="${esc(t.key)}" data-g="condition" onclick="onTagCondition(this,'${esc(classId)}','${esc(nameKey)}','${esc(subject)}')">${svg}${esc(t.label)}</button>`;
    }).join('');

    // understand 버튼 (1택) + understand_sub (멀티)
    const undBtns=TAGS.understand.map(t=>{
      const sel=tags.understand===t.key;
      return `<button class="tg-radio${sel?' sel-c':''}" data-k="${esc(t.key)}" data-g="understand" onclick="onTagUnderstand(this,'${esc(classId)}','${esc(nameKey)}','${esc(subject)}')">${esc(t.label)}</button>`;
    }).join('');
    // 시험 결과 (복수 선택, 시험 본 날만 — 미선택이면 메시지 미반영)
    const examBtns=(TAGS.exam||[]).map(t=>{
      const sel=(tags.exam||[]).includes(t.key);
      return `<button class="tg-check${sel?' sel-m':''}" data-k="${esc(t.key)}" onclick="onTagMulti(this,'${esc(classId)}','${esc(nameKey)}','exam','${esc(subject)}')">${esc(t.label)}</button>`;
    }).join('');
    const undSubBtns=TAGS.understand_sub.map(t=>{
      const sel=(tags.understand_sub||[]).includes(t.key);
      return `<button class="tg-check${sel?' sel-m':''}" data-k="${esc(t.key)}" onclick="onTagMulti(this,'${esc(classId)}','${esc(nameKey)}','understand_sub','${esc(subject)}')">${esc(t.label)}</button>`;
    }).join('');

    // engage + caution 멀티
    const engBtns=TAGS.engage.map(t=>{
      const sel=(tags.engage||[]).includes(t.key);
      return `<button class="tg-check${sel?' sel-m':''}" data-k="${esc(t.key)}" onclick="onTagMulti(this,'${esc(classId)}','${esc(nameKey)}','engage','${esc(subject)}')">${esc(t.label)}</button>`;
    }).join('');
    const cauBtns=TAGS.caution.map(t=>{
      const sel=(tags.caution||[]).includes(t.key);
      return `<button class="tg-check${sel?' sel-m':''}" data-k="${esc(t.key)}" data-g="caution" onclick="onTagMulti(this,'${esc(classId)}','${esc(nameKey)}','caution','${esc(subject)}')">${esc(t.label)}</button>`;
    }).join('');
    const extraBtns = TAGS.extra.map(t => {
        const sel = (tags.extra || []).includes(t.key);
        return `<button class="tg-check${sel?' sel-m':''}" data-k="${esc(t.key)}" onclick="onTagMulti(this,'${esc(classId)}','${esc(nameKey)}','extra','${esc(subject)}')">${esc(t.label)}</button>`;
    }).join('');
    const hlBtns=TAGS.highlight.map(t=>{
      const hlArr=Array.isArray(tags.highlight)?tags.highlight:(tags.highlight?[tags.highlight]:[]);
      const sel=hlArr.includes(t.key);
      return `<button class="tg-check${sel?' sel-m':''}" data-k="${esc(t.key)}" data-g="highlight" onclick="onTagMulti(this,'${esc(classId)}','${esc(nameKey)}','highlight','${esc(subject)}')">${esc(t.label)}</button>`;
    }).join('');
    const isAbsent=(tags.assign_tags||[]).includes('결석');
    dtRows+=`<div class="si-card${isAbsent?' si-absent':''}">
      <div class="si-left">
        <span class="dot ${dc}" data-namekey="${esc(nameKey)}" data-subject="${esc(subject)}"></span>
        <span class="si-lname">${esc(displayName)}</span>
      </div>
      <div class="si-right">
        <div class="si-row">
          <span class="si-lbl">과제</span>
          <div class="si-btns tg-cell">${agBtns}${presets.length?`<div class="tg-sep"></div>${apBtns}`:''}</div>
        </div>
        <div class="si-div"></div>
        <div class="si-row">
          <span class="si-lbl">컨디션</span>
          <div class="si-btns tg-cell">${condBtns}</div>
        </div>
        <div class="si-row">
          <span class="si-lbl">이해도</span>
          <div class="si-btns tg-cell">${undBtns}<div class="tg-sep"></div>${hlBtns}</div>
        </div>
        <div class="si-row">
          <span class="si-lbl">참여·풀이</span>
          <div class="si-btns tg-cell">${engBtns}<div class="tg-sep"></div>${undSubBtns}<div class="tg-sep"></div>${extraBtns}</div>
        </div>
        <div class="si-row">
          <span class="si-lbl">주의</span>
          <div class="si-btns tg-cell">${cauBtns}</div>
        </div>
        <div class="si-row">
          <span class="si-lbl">시험</span>
          <div class="si-btns tg-cell">${examBtns}</div>
        </div>
        <div class="si-row">
          <span class="si-lbl">메모</span>
          <input class="inp sm" value="${esc(note)}" placeholder="특이사항" data-namekey="${esc(nameKey)}" data-subject="${esc(subject)}" oninput="onNI(this)" style="width:100%">
        </div>
      </div>
    </div>`;
  }

  const noStu=`<div class="empty" style="padding:20px;font-size:12px">이 반에 학생이 없습니다.</div>`;
  mc.innerHTML=makeTb(`${classId} · ${gsLabel?gsLabel+' ':''}${subject}`,today())+mTabs+
    `<div style="padding:14px 14px 10px"><div class="card">${pForm}</div></div>
     <div style="padding:0 14px 14px">
       <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
         <div style="font-size:12px;font-weight:700;color:var(--sub)">👥 학생별 입력</div>
         <div style="font-size:11px;color:var(--gray)" id="doneCount">${done}/${students.length}명 완료</div>
       </div>
       <div class="si-list">${dtRows||noStu}</div>
     </div>`;
}

// ── 과제 고정 등급 (택1) ──────────────────────────────────────────
function onAssignGrade(el,classId,nameKey,subject){
  const k=el.dataset.k;
  const tags=getTags(classId,nameKey,subject);
  tags.assign_grade=tags.assign_grade===k?null:k;
  el.closest('.tg-cell').querySelectorAll('[data-k]').forEach(b=>{
    const s=b.dataset.k===tags.assign_grade;
    b.className='tg-radio'+(s?' sel-c ag-'+b.dataset.k:'');
  });
  // 신호등 갱신: data-namekey + data-subject 어트리뷰트 사용
  const d=document.querySelector(`.dot[data-namekey="${CSS.escape(nameKey)}"][data-subject="${CSS.escape(subject)}"]`);
  if(d)d.className='dot '+dotClass(classId,nameKey,subject);
  const a=curAsgn();
  if(a){
    const students=(config?._classStudents||{})[a.classId]||[];
    const cnt=students.filter(s=>tagData?.[s.nameKey]?.[a.subject]?.[todayKey()]?.assign_grade).length;
    const dc=document.getElementById('doneCount');if(dc)dc.textContent=`${cnt}/${students.length}명 완료`;
  }
  pushObs(classId,nameKey,subject,'assign_grade');
}

// ── 과제 추가 프리셋 (복수선택) ───────────────────────────────────
function onAssignTag(el,classId,nameKey,subject){
  const p=el.dataset.p;
  const tags=getTags(classId,nameKey,subject);
  if(!tags.assign_tags)tags.assign_tags=[];
  const idx=tags.assign_tags.indexOf(p);
  if(idx>=0)tags.assign_tags.splice(idx,1); else tags.assign_tags.push(p);
  el.classList.toggle('sel-m',tags.assign_tags.includes(p));
  // 결석=하드 차단: 결석 선택 시 해당 학생의 나머지 입력 버튼 비활성(메모·결석 제외). CSS .si-absent 처리.
  if(p==='결석'){ const card=el.closest('.si-card'); if(card)card.classList.toggle('si-absent',tags.assign_tags.includes('결석')); }
  pushObs(classId,nameKey,subject,'assign_tags');
}

// ── 특이사항 읽기 (학생별 단일) ───────────────────────────────────
// v2.1.1: __note__ 우선. 없으면 구 과목별 note 중 첫 비어있지 않은 값(마이그레이션).
function _readNote(nameKey){
  const rec=inputData?.[nameKey];
  if(!rec)return '';
  const n=rec['__note__']?.note;
  if(n!=null&&n!=='')return n;
  for(const k in rec){
    if(k==='__note__')continue;
    const v=rec[k]?.note;
    if(v)return v;
  }
  return '';
}

// ── 특이사항 메모 저장 ────────────────────────────────────────────
// v2.1.1: 특이사항은 학생별 단일 필드. 과목 무관, input/{nameKey}/__note__ 에 저장.
function onNI(el){
  const nameKey=el.dataset.namekey;
  const subject=el.dataset.subject; // 권한 가드용 (현재 화면 과목)
  if(!inputData[nameKey])inputData[nameKey]={};
  const cur={...inputData[nameKey]['__note__']||{}};
  cur.note=el.value;
  inputData[nameKey]['__note__']=cur;
  saveLocal();
  if(!dbUrl||!dbPath)return;
  if(!_canWrite(curAsgn()?.classId||'',subject))return;
  fbPatch(`input/${nameKey}/__note__`,{note:el.value}).then(()=>setSync(true)).catch(()=>setSync(false));
}

// (v2.1.2: 레거시 onPB 제거 — input/{subject}.assign 죽은 경로 폐기. 과제수행도는 obs/assign_grade)

// ── 진도 cascade 피커 ─────────────────────────────────────────────
// 단원명에서 앞 번호 제거: "Ⅰ. 소인수분해" → "소인수분해", "1. 덧셈과 뺄셈" → "덧셈과 뺄셈"
function stripIdx(s){return s.replace(/^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+\.\s*/u,'').replace(/^\d+\.\s*/,'');}

function pgMainChange(sel, pkey) {
  const val = sel.value;
  const subWrap = document.getElementById('pg-sub-wrap');
  const freeInp = document.getElementById('pg-free');
  const preview = document.getElementById('pg-preview');
  const subSel = document.getElementById('pg-sub');
  if (!subWrap) return;
  if (val === 'free') {
    subWrap.classList.remove('show');
    freeInp.classList.add('show');
    if (preview) preview.classList.remove('show');
    freeInp.focus();
    pgBuild(pkey);
    return;
  }
  freeInp.classList.remove('show');
  if (!val || val === 'sep') {
    subWrap.classList.remove('show');
    if (preview) preview.classList.remove('show');
    return;
  }
  // 소단원 목록 채우기
  const parts = pkey.split('|');
  const pkeyClassId = parts[0]||'';
  const pkeySubject = parts.slice(1).join('|')||'';
  const curriculum2 = getCurriculumForSubject(pkeyClassId, pkeySubject)||'';
  const curr = getCurriculumByGradeSem(curriculum2);
  const idx = parseInt(val);
  if (!isNaN(idx) && curr[idx]) {
    subSel.innerHTML = '<option value="">소단원 선택...</option>' +
      curr[idx].subs.map(function(s, i) { return '<option value="' + i + '">' + esc(stripIdx(s)) + '</option>'; }).join('') +
      '<option value="all">단원 전체</option>';
  }
  subWrap.classList.add('show');
  pgBuild(pkey);
}
function pgBuild(pkey) {
  const mainSel = document.getElementById('pg-main');
  const subSel = document.getElementById('pg-sub');
  const freeInp = document.getElementById('pg-free');
  const preview = document.getElementById('pg-preview');
  const pvEl = document.getElementById('pg-pv');
  if (!mainSel) return;
  const mainVal = mainSel.value;
  const isFree = mainVal === 'free';
  let result = '';
  if (isFree) {
    result = freeInp ? freeInp.value || '' : '';
    if (preview) {
      if (result) { preview.className = 'pg-preview show free'; if (pvEl) pvEl.textContent = result; }
      else preview.className = 'pg-preview';
    }
  } else {
    const parts = pkey.split('|');
    const pkeyClassId = parts[0]||'';
    const pkeySubject = parts.slice(1).join('|')||'';
    const curriculum3 = getCurriculumForSubject(pkeyClassId, pkeySubject)||'';
    const curr = getCurriculumByGradeSem(curriculum3);
    const mainIdx = parseInt(mainVal);
    if (isNaN(mainIdx) || !curr[mainIdx]) { if (preview) preview.className = 'pg-preview'; return; }
    const mainText = stripIdx(curr[mainIdx].main);
    const subVal = subSel ? subSel.value || '' : '';
    let subText = '';
    if (subVal === 'all') subText = '';
    else if (subVal !== '' && subVal !== 'sep') subText = stripIdx(curr[mainIdx].subs[parseInt(subVal)] || '');
    result = subText || mainText;
    if (preview) {
      preview.className = 'pg-preview show';
      if (pvEl) pvEl.textContent = result;
    }
  }
  const cur = Object.assign({}, progressData[pkey] || {});
  cur.progress = result;
  pushProgress(pkey, cur);
  _updateDotsForPkey(pkey);
}

// ── 과제 피커 ─────────────────────────────────────────────────
function _parseHwStr(s){
  if(!s)return{type:'page',from:'',to:'',raw:''};
  let m;
  m=s.match(/^~p\.(\d+)$/i);if(m)return{type:'page',from:'',to:m[1],raw:s};
  m=s.match(/^~#(\d+)$/);if(m)return{type:'prob',from:'',to:m[1],raw:s};
  m=s.match(/^p\.(\d+)~p\.(\d+)$/i);if(m)return{type:'page',from:m[1],to:m[2],raw:s};
  m=s.match(/^#(\d+)~#(\d+)$/);if(m)return{type:'prob',from:m[1],to:m[2],raw:s};
  return{type:'free',from:'',to:'',raw:s};
}
function hwSetType(type,pkey){
  document.querySelectorAll('.hw-tb').forEach(b=>{b.className='hw-tb'+(b.dataset.t===type?' sel '+type:'');});
  const nr=document.getElementById('hw-nums');
  const fr=document.getElementById('hw-free');
  const pv=document.getElementById('hw-preview');
  if(nr)nr.className='hw-num-row'+(type!=='free'?' show':'');
  if(fr)fr.className='inp hw-free'+(type==='free'?' show':'');
  if(pv)pv.style.display=type==='free'?'none':'';
  hwBuild(pkey);
}
function hwBuild(pkey){
  const sel=document.querySelector('.hw-tb.sel');
  const type=sel?sel.dataset.t:'page';
  const from=(document.getElementById('hw-from')?.value||'').trim();
  const to=(document.getElementById('hw-to')?.value||'').trim();
  const raw=document.getElementById('hw-free')?.value||'';
  let result='';
  if(type==='free'){result=raw;}
  else if(to){result=from?(type==='page'?`p.${from}~p.${to}`:`#${from}~#${to}`):(type==='page'?`~p.${to}`:`~#${to}`);}
  const pv=document.getElementById('hw-preview');
  const pvv=document.getElementById('hw-pv');
  const pvi=document.getElementById('hw-pi');
  if(pv&&type!=='free'){
    pv.className='hw-preview '+(to?type:'empty '+type);
    if(pvv)pvv.textContent=result||'—';
    if(pvi)pvi.textContent=type==='page'?'📄':'🔢';
  }
  const cur={...progressData[pkey]||{}};cur.homework=result;
  pushProgress(pkey,cur);_updateDotsForPkey(pkey);
}
function onPI(el){
  const pkey=el.dataset.pkey,field=el.dataset.field;
  const cur={...progressData[pkey]||{}};cur[field]=el.value;pushProgress(pkey,cur);
  _updateDotsForPkey(pkey);
}

// ── 신호등 판정 헬퍼 ─────────────────────────────────────────
// g(초록): 수행도 입력 + 진도/과제 하나 이상 입력
// y(노랑): 수행도 입력 + 진도/과제 미입력
// e(회색): 수행도 미입력
function dotClass(classId,nameKey,subject){
  const grade=tagData?.[nameKey]?.[subject]?.[todayKey()]?.assign_grade;
  if(!grade)return'e';
  if(grade==='done')return'g';
  return'y'; // partial·none
}
// 진도/과제 입력 시 현재 화면에 보이는 해당 반 학생 도트 업데이트
function _updateDotsForPkey(pkey){
  const parts=pkey.split('|');
  if(parts.length<2) return;
  const classId=parts[0];
  const subject=parts.slice(1).join('|');
  document.querySelectorAll('.dot[data-namekey][data-subject]').forEach(d=>{
    if(d.dataset.subject===subject){
      const a=curAsgn();
      if(a&&a.classId===classId)
        d.className='dot '+dotClass(classId,d.dataset.namekey,subject);
    }
  });
}
