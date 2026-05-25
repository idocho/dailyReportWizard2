// ══════════════════════════════════════════════════════════
//  수업 입력
// ══════════════════════════════════════════════════════════
function renderInput(mc){
  renderMhdr('수업 입력');
  if(!cfg){mc.innerHTML=makeTb('수업 입력',today())+`<div class="empty">⚙️ 설정에서 Firebase 연결 후<br>학생 명단을 불러오세요.</div>`;return;}
  const asgns=instructor?.assignments||[];
  if(!asgns.length){mc.innerHTML=makeTb('수업 입력',today())+`<div class="empty">설정 → 내 담당 수업에서<br>담당 수업을 추가해 주세요.</div>`;return;}
  if(curAI>=asgns.length)curAI=0;
  // curSheet 초기화 (최초 진입 또는 유효하지 않을 때)
  const availSheets=[...new Set(asgns.map(a=>a.sheet))];
  if(!curSheet||!availSheets.includes(curSheet))curSheet=asgns[curAI]?.sheet||availSheets[0]||'';
  // curAI가 curSheet와 불일치하면 해당 시트 첫 번째 assignment로 보정
  if(asgns[curAI]?.sheet!==curSheet){
    const idx=asgns.findIndex(a=>a.sheet===curSheet);
    if(idx>=0)curAI=idx;
  }
  const a=asgns[curAI];
  const clsD=cfg.sheets?.[a.sheet]?.classes?.[a.cls];
  const students=clsD?.students||[];
  // 프리셋 소스: instructor.presets 우선
  const presets=instructor?.presets||cfg?.presets?.['과제수행도']||[];
  const pkey=`${a.sheet}|${a.cls}|${a.tb}`;
  const pd=progressData[pkey]||{};

  let mTabs='';
  if(asgns.length>1){
    let sheetTabHtml='';
    if(availSheets.length>1){
      const shBtns=availSheets.map(function(sh){
        const act=sh===curSheet;
        const borderColor=act?'var(--indigo)':'transparent';
        const textColor=act?'var(--indigo)':'var(--sub)';
        return '<button onclick="selSheet(\'' +esc(sh)+ '\')" style="flex:1;padding:8px 0;border:none;border-bottom:2px solid '+borderColor+';background:transparent;color:'+textColor+';font-size:12px;font-weight:700;cursor:pointer;font-family:inherit">'+esc(sh)+'반</button>';
      }).join('');
      sheetTabHtml='<div style="display:flex;gap:0;background:var(--panel);border-bottom:1px solid var(--border)">'+shBtns+'</div>';
    }
    const shAsgns=asgns.filter(function(a){return a.sheet===curSheet;});
    const tabs=shAsgns.map(function(x){
      const i=asgns.indexOf(x);
      const sel=i===curAI;
      const bg=sel?'var(--indigo)':'var(--bg)';
      const fg=sel?'#fff':'var(--sub)';
      const xGs=getTbGrade(x.sheet,x.cls,x.tb)||'';const xGsL=xGs?(GRADE_SEM_LIST.find(g=>g.val===xGs)?.label||xGs):'';
      return '<button onclick="selA('+i+')" style="padding:5px 12px;border-radius:16px;border:1px solid var(--border);background:'+bg+';color:'+fg+';font-size:11px;font-weight:700;white-space:nowrap;cursor:pointer;font-family:inherit">'+esc(x.cls)+(xGsL?' <span style="opacity:.7;font-size:9px">'+esc(xGsL)+'</span> ':' ')+esc(x.tb)+'</button>';
    }).join('');
    mTabs='<div class="m">'+sheetTabHtml+'<div style="display:flex;gap:6px;padding:10px 12px;overflow-x:auto;background:var(--panel);border-bottom:1px solid var(--border)">'+tabs+'</div></div>';
  }

  // 진도 피커 초기값 파싱 — grade_sem은 학급-교재 조합에 종속 (tb_grade)
  const gradeSem=getTbGrade(a.sheet,a.cls,a.tb)||'';
  const gsLabel=gradeSem?(GRADE_SEM_LIST.find(g=>g.val===gradeSem)?.label||gradeSem):'';
  const curCurr=getCurriculumByGradeSem(gradeSem);
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
    <div style="font-size:12px;font-weight:700;color:var(--sub);margin-bottom:10px">📚 오늘 수업 — ${esc(a.cls)} · ${gsLabel?`<span style="color:var(--indigo);font-size:10px;font-weight:700;margin-right:3px">${esc(gsLabel)}</span>`:''}${esc(a.tb)}</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div><div class="fl">진도</div>${pgPicker}</div>
      <div><div class="fl">과제</div>${hwPicker}</div>
    </div>
  </div>`;

  const dk=todayKey();
  const done=students.filter(s=>tagData[`${a.sheet}|${a.cls}|${s.name}|${a.tb}`]?.[dk]?.assign_grade).length;
  let dtRows='';

  for(const s of students){
    const ikey=`${a.sheet}|${a.cls}|${s.name}|${a.tb}`;
    const nkey=`${a.sheet}|${a.cls}|${s.name}|__note__`;
    const note=inputData[nkey]?.note||'';
    const dc=dotClass(a.sheet,a.cls,s.name,a.tb);
    const tags=tagData[`${a.sheet}|${a.cls}|${s.name}|${a.tb}`]?.[dk]||{};

    // 과제 고정 등급 (택1)
    const agBtns=ASSIGN_GRADES.map(g=>{
      const sel=tags.assign_grade===g.key;
      return `<button class="tg-radio${sel?' sel-c ag-'+g.key:''}" data-k="${esc(g.key)}" onclick="onAssignGrade(this,'${esc(a.sheet)}','${esc(a.cls)}','${esc(s.name)}','${esc(a.tb)}')">${esc(g.label)}</button>`;
    }).join('');
    // 추가 프리셋 (복수선택)
    const apBtns=presets.map(p=>{
      const sel=(tags.assign_tags||[]).includes(p);
      return `<button class="tg-check${sel?' sel-m':''}" data-p="${esc(p)}" onclick="onAssignTag(this,'${esc(a.sheet)}','${esc(a.cls)}','${esc(s.name)}','${esc(a.tb)}')">${esc(p)}</button>`;
    }).join('');

    // condition 버튼 (PES 화살표)
    const condBtns=TAGS.condition.map(t=>{
      const sel=tags.condition===t.key;
      const rot=COND_ARROWS[t.key]??90;
      const svg=`<svg width="12" height="12" viewBox="0 0 24 24" style="transform:rotate(${rot}deg);flex-shrink:0"><polygon points="12,2 22,22 12,16 2,22" fill="currentColor"/></svg>`;
      return `<button class="tg-radio${sel?' sel-c':''}" data-k="${esc(t.key)}" data-g="condition" onclick="onTagCondition(this,'${esc(a.sheet)}','${esc(a.cls)}','${esc(s.name)}','${esc(a.tb)}')">${svg}${esc(t.label)}</button>`;
    }).join('');

    // understand 버튼 (1택) + understand_sub (멀티)
    const undBtns=TAGS.understand.map(t=>{
      const sel=tags.understand===t.key;
      return `<button class="tg-radio${sel?' sel-c':''}" data-k="${esc(t.key)}" data-g="understand" onclick="onTagUnderstand(this,'${esc(a.sheet)}','${esc(a.cls)}','${esc(s.name)}','${esc(a.tb)}')">${esc(t.label)}</button>`;
    }).join('');
    const undSubBtns=TAGS.understand_sub.map(t=>{
      const sel=(tags.understand_sub||[]).includes(t.key);
      return `<button class="tg-check${sel?' sel-m':''}" data-k="${esc(t.key)}" onclick="onTagMulti(this,'${esc(a.sheet)}','${esc(a.cls)}','${esc(s.name)}','understand_sub','${esc(a.tb)}')">${esc(t.label)}</button>`;
    }).join('');

    // engage + caution 멀티
    const engBtns=TAGS.engage.map(t=>{
      const sel=(tags.engage||[]).includes(t.key);
      return `<button class="tg-check${sel?' sel-m':''}" data-k="${esc(t.key)}" onclick="onTagMulti(this,'${esc(a.sheet)}','${esc(a.cls)}','${esc(s.name)}','engage','${esc(a.tb)}')">${esc(t.label)}</button>`;
    }).join('');
    const cauBtns=TAGS.caution.map(t=>{
      const sel=(tags.caution||[]).includes(t.key);
      return `<button class="tg-check${sel?' sel-m':''}" data-k="${esc(t.key)}" data-g="caution" onclick="onTagMulti(this,'${esc(a.sheet)}','${esc(a.cls)}','${esc(s.name)}','caution','${esc(a.tb)}')">${esc(t.label)}</button>`;
    }).join('');
    const extraBtns = TAGS.extra.map(t => {
        const sel = (tags.extra || []).includes(t.key);
        return `<button class="tg-check${sel?' sel-m':''}" data-k="${esc(t.key)}" onclick="onTagMulti(this,'${esc(a.sheet)}','${esc(a.cls)}','${esc(s.name)}','extra','${esc(a.tb)}')">${esc(t.label)}</button>`;
    }).join('');
    const hlBtns=TAGS.highlight.map(t=>{
      const hlArr=Array.isArray(tags.highlight)?tags.highlight:(tags.highlight?[tags.highlight]:[]);
      const sel=hlArr.includes(t.key);
      return `<button class="tg-check${sel?' sel-m':''}" data-k="${esc(t.key)}" data-g="highlight" onclick="onTagMulti(this,'${esc(a.sheet)}','${esc(a.cls)}','${esc(s.name)}','highlight','${esc(a.tb)}')">${esc(t.label)}</button>`;
    }).join('');
    dtRows+=`<div class="si-card">
      <div class="si-left">
        <span class="dot ${dc}" data-ikey="${esc(ikey)}"></span>
        <span class="si-lname">${esc(s.name)}</span>
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
          <div class="si-btns tg-cell">${undBtns}<div class="tg-sep"></div>${undSubBtns}<div class="tg-sep"></div>${hlBtns}</div>
        </div>
        <div class="si-row">
          <span class="si-lbl">참여</span>
          <div class="si-btns tg-cell">${engBtns}</div>
        </div>
        <div class="si-row">
          <span class="si-lbl">기타</span>
          <div class="si-btns tg-cell">${extraBtns}${cauBtns}</div>
        </div>
        <div class="si-row">
          <span class="si-lbl">메모</span>
          <input class="inp sm" value="${esc(note)}" placeholder="특이사항" data-key="${esc(nkey)}" oninput="onNI(this)" style="width:100%">
        </div>
      </div>
    </div>`;
  }

  const noStu=`<div class="empty" style="padding:20px;font-size:12px">이 반에 학생이 없습니다.</div>`;
  mc.innerHTML=makeTb(`${a.cls} · ${gsLabel?gsLabel+' ':''}${a.tb}`,today())+mTabs+
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
function onAssignGrade(el,sheet,cls,name,tb){
  const k=el.dataset.k;
  const tags=getTags(sheet,cls,name,tb);
  tags.assign_grade=tags.assign_grade===k?null:k;
  el.closest('.tg-cell').querySelectorAll('[data-k]').forEach(b=>{
    const s=b.dataset.k===tags.assign_grade;
    b.className='tg-radio'+(s?' sel-c ag-'+b.dataset.k:'');
  });
  const d=document.querySelector(`.dot[data-ikey="${CSS.escape(sheet+'|'+cls+'|'+name+'|'+tb)}"]`);
  if(d)d.className='dot '+dotClass(sheet,cls,name,tb);
  const a=instructor?.assignments?.[curAI];
  if(a){const sts=cfg?.sheets?.[a.sheet]?.classes?.[a.cls]?.students||[];
    const cnt=sts.filter(s=>tagData[`${a.sheet}|${a.cls}|${s.name}|${a.tb}`]?.[todayKey()]?.assign_grade).length;
    const dc=document.getElementById('doneCount');if(dc)dc.textContent=`${cnt}/${sts.length}명 완료`;}
  pushObs(sheet,cls,name,tb);
}

// ── 과제 추가 프리셋 (복수선택) ───────────────────────────────────
function onAssignTag(el,sheet,cls,name,tb){
  const p=el.dataset.p;
  const tags=getTags(sheet,cls,name,tb);
  if(!tags.assign_tags)tags.assign_tags=[];
  const idx=tags.assign_tags.indexOf(p);
  if(idx>=0)tags.assign_tags.splice(idx,1); else tags.assign_tags.push(p);
  el.classList.toggle('sel-m',tags.assign_tags.includes(p));
  pushObs(sheet,cls,name,tb);
}

// ── 수행도 버튼 (레거시, 미사용) ─────────────────────────────────
function onPB(btn){
  const key=btn.dataset.key,pi=parseInt(btn.dataset.pi);
  const presets=instructor?.presets||cfg?.presets?.['과제수행도']||[];
  const val=presets[pi]||'';
  pushInput(key,{assign:val});
  document.querySelectorAll('.px,.pb').forEach(b=>{
    if(b.dataset.key!==key||b.dataset.pi===undefined)return;
    const bpi=parseInt(b.dataset.pi),s=bpi===pi;
    b.classList.toggle('sel',s);b.style.background=s?BC[bpi%BC.length]:'';b.style.borderColor=s?'transparent':'';b.style.color=s?'#fff':'';
    if(s){
      const d=document.querySelector(`.dot[data-ikey="${key}"]`);
      if(d){const p=key.split('|');if(p.length===4)d.className='dot '+dotClass(p[0],p[1],p[2],p[3]);}
    }
  });
  const a=instructor?.assignments?.[curAI];
  if(a){const sts=cfg?.sheets?.[a.sheet]?.classes?.[a.cls]?.students||[];const done=sts.filter(s=>inputData[`${a.sheet}|${a.cls}|${s.name}|${a.tb}`]?.assign?.trim()).length;const dc=document.getElementById('doneCount');if(dc)dc.textContent=`${done}/${sts.length}명 완료`;}
}
function onNI(el){pushInput(el.dataset.key,{note:el.value});}
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
  const mainSel = document.getElementById('pg-main');
  const gradeSem2 = (function() {
    const pkey2 = mainSel ? mainSel.dataset.pkey || '' : '';
    const parts = pkey2.split('|');
    const tbKey = parts.length >= 3 ? parts.slice(2).join('|') : '';
    return getTbGrade(parts[0],parts[1],tbKey)||'';
  })();
  const curr = getCurriculumByGradeSem(gradeSem2);
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
    const tbKey = parts.length >= 3 ? parts.slice(2).join('|') : '';
    const gradeSem3 = getTbGrade(parts[0],parts[1],tbKey)||'';
    const curr = getCurriculumByGradeSem(gradeSem3);
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
  // 진도/과제 변경 시 해당 반 학생 도트 일괄 갱신
  _updateDotsForPkey(pkey);
}

// ── 신호등 판정 헬퍼 ─────────────────────────────────────────
// g(초록): 수행도 입력 + 진도/과제 하나 이상 입력
// y(노랑): 수행도 입력 + 진도/과제 미입력
// e(회색): 수행도 미입력
function dotClass(sheet,cls,name,tb){
  const grade=tagData[`${sheet}|${cls}|${name}|${tb}`]?.[todayKey()]?.assign_grade;
  if(!grade)return'e';
  if(grade==='done')return'g';
  return'y'; // partial·none
}
// 진도/과제 입력 시 현재 화면에 보이는 해당 반 학생 도트 업데이트
function _updateDotsForPkey(pkey){
  const parts=pkey.split('|');
  if(parts.length!==3) return;
  const [sh,cl,tb]=parts;
  document.querySelectorAll('.dot[data-ikey]').forEach(d=>{
    const k=d.dataset.ikey.split('|');
    if(k.length===4&&k[0]===sh&&k[1]===cl&&k[3]===tb)
      d.className='dot '+dotClass(sh,cl,k[2],tb);
  });
}
