// ══════════════════════════════════════════════════════════════════════
//  성적 입력 (scores/)
// ══════════════════════════════════════════════════════════════════════

// ── Firebase 연동 ─────────────────────────────────────────────────────
async function _loadScoreDataIfNeeded(){
  if(!fbUrl||!fbPath)return;
  try{
    const d=await fbGet('scores');
    if(d&&typeof d==='object')scoreData=d;
    if(curNav==='scores')renderMain();
  }catch(e){}
}
async function _pushScore(clsKey,testKey,val){
  if(!fbUrl||!fbPath)return;
  try{await fbPatch(`scores/${encodeURIComponent(clsKey)}`,{[testKey]:val});}catch(e){}
}
async function _deleteScore(clsKey,testKey){
  if(!fbUrl||!fbPath)return;
  try{await fbPatch(`scores/${encodeURIComponent(clsKey)}`,{[testKey]:null});}catch(e){}
}

// ── 통계 계산 ─────────────────────────────────────────────────────────
function _scoreAvg(students){
  const vs=Object.values(students||{}).filter(v=>v!==''&&v!==null&&!isNaN(v)).map(Number);
  return vs.length?vs.reduce((a,b)=>a+b,0)/vs.length:null;
}
function _scoreStatLine(students,maxScore,label){
  const vs=Object.values(students||{}).filter(v=>v!==''&&v!==null&&!isNaN(v)).map(Number);
  if(!vs.length)return'<span style="color:var(--sub)">점수를 입력하면 통계가 표시됩니다.</span>';
  const avg=vs.reduce((a,b)=>a+b,0)/vs.length;
  const maxV=Math.max(...vs),minV=Math.min(...vs);
  const m=Number(maxScore)||100;
  const prefix=label?`<strong style="color:var(--indigo)">${label}</strong> · `:'';
  return`${prefix}평균: <strong>${avg.toFixed(1)}점</strong> · 최고: <strong>${maxV}</strong>점 · 최저: <strong>${minV}</strong>점 · ${vs.length}명`;
}

// ── 백분율 기준 통계 (학년 집계용) ────────────────────────────────────
// pctStu: {uid: pct(0~100)} — 각 반의 만점으로 정규화된 값
function _pctStatLine(pctStu){
  const vs=Object.values(pctStu||{}).filter(v=>!isNaN(v)).map(Number);
  if(!vs.length)return'<span style="color:var(--sub)">데이터 없음</span>';
  const avg=vs.reduce((a,b)=>a+b,0)/vs.length;
  const maxV=Math.max(...vs),minV=Math.min(...vs);
  return`평균: <strong>${avg.toFixed(1)}점</strong> · 최고: <strong>${maxV.toFixed(0)}점</strong> · 최저: <strong>${minV.toFixed(0)}점</strong> · ${vs.length}명`;
}

// ── 학년 단위 집계 ───────────────────────────────────────────────────
function _gradeAggregate(testKey,gradeSem){
  if(!cfg||!gradeSem)return null;
  const rawStu={};
  let clsCount=0;
  for(const[ck,tests] of Object.entries(scoreData||{})){
    const tv=tests?.[testKey];
    if(!tv||tv.scope!=='grade')continue;
    const parts=ck.split('|');
    if(parts.length<2)continue;
    const[sh,cls]=parts;
    const tbGrade=cfg?.sheets?.[sh]?.classes?.[cls]?.tb_grade||{};
    if(!Object.values(tbGrade).includes(gradeSem))continue;
    const studs=tv.students||{};
    const hasSc=Object.values(studs).some(v=>v!==''&&v!==null&&!isNaN(v));
    if(!hasSc)continue;
    clsCount++;
    for(const[name,score] of Object.entries(studs)){
      if(score===''||score===null||isNaN(score))continue;
      rawStu[ck+'::'+name]=Number(score);
    }
  }
  return clsCount>0?{rawStudents:rawStu,clsCount}:null;
}

// ── 메인 렌더 ─────────────────────────────────────────────────────────
function renderScores(mc){
  const a=instructor?.assignments?.[curAI];
  if(!a){
    mc.innerHTML=makeTb('성적 입력')+`<div style="padding:20px;color:var(--sub)">좌측 사이드바에서 담당 수업을 선택하세요.</div>`;
    return;
  }
  const clsKey=`${a.sheet}|${a.cls}`;
  if(scoreView==='edit')_renderScoreEdit(mc,a,clsKey);
  else _renderScoreList(mc,a,clsKey);
}

// ── 목록 뷰 ──────────────────────────────────────────────────────────
function _renderScoreList(mc,a,clsKey){
  const tests=scoreData[clsKey]||{};
  const list=Object.entries(tests).sort(([ka],[kb])=>kb.localeCompare(ka));
  const gs=getTbGrade(a.sheet,a.cls,a.tb)||'';

  let rows='';
  if(list.length===0){
    rows=`<div style="padding:20px;text-align:center;color:var(--sub);font-size:12px">시험 기록이 없습니다.</div>`;
  }else{
    rows=list.map(([tk,tv])=>{
      const isGrade=tv.scope==='grade';
      const avg=_scoreAvg(tv.students);
      const cnt=Object.values(tv.students||{}).filter(v=>v!==''&&v!==null&&!isNaN(v)).length;
      const totalStu=cfg?.sheets?.[a.sheet]?.classes?.[a.cls]?.students?.length||0;
      const maxScore=tv.max_score||100;

      // 학년 단위: 전체 집계
      let gradeLine='';
      if(isGrade&&gs){
        const agg=_gradeAggregate(tk,gs);
        if(agg){
          const clsLabel=agg.clsCount===1?'1개 반 입력됨':`${agg.clsCount}개 반 합산`;
          gradeLine=`<div style="margin-top:6px;padding:6px 8px;background:var(--indigo-l);border-radius:6px;font-size:11px">
            🎓 학년 전체 (${clsLabel}) · ${_pctStatLine(agg.rawStudents)}
          </div>`;
        }
      }

      const scopeBadge=isGrade
        ?`<span style="font-size:10px;background:#DCFCE7;color:#15803D;border-radius:4px;padding:1px 6px;font-weight:700;margin-left:4px">학년</span>`
        :`<span style="font-size:10px;background:#F1F5F9;color:#64748B;border-radius:4px;padding:1px 6px;font-weight:700;margin-left:4px">반</span>`;

      return`<div class="score-card">
  <div class="score-card-top">
    <div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px">
      <span class="score-type-badge">${esc(tv.type||'')}</span>
      ${tv.round?`<span class="score-round">${esc(tv.round)}회</span>`:''}
      ${scopeBadge}
      <span class="score-date">${esc(tv.date||'')}</span>
    </div>
    <div style="display:flex;gap:6px;flex-shrink:0">
      <button class="btn bsm" onclick="_openScoreEdit('${esc(clsKey)}','${esc(tk)}')">수정</button>
      <button class="btn bsm" style="color:var(--red)" onclick="_confirmDeleteScore('${esc(clsKey)}','${esc(tk)}')">삭제</button>
    </div>
  </div>
  <div class="score-card-bottom">
    <span style="font-size:11px;color:var(--sub)">만점 ${maxScore}점</span>
    ${avg!==null?`<span style="font-size:11px;color:var(--sub)">· 반 평균 <strong>${avg.toFixed(1)}점</strong></span>`:''}
    <span style="font-size:11px;color:var(--sub)">· ${cnt}/${totalStu}명 입력</span>
    ${tv.memo?`<span style="font-size:11px;color:var(--sub);margin-left:4px">📝 ${esc(tv.memo)}</span>`:''}
  </div>
  ${gradeLine}
</div>`;
    }).join('');
  }

  mc.innerHTML=makeTb('성적 입력',`${a.cls} · ${a.tb}${gs?' · '+gs:''}`)+`
<div style="padding:12px 14px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <span style="font-size:12px;color:var(--sub)">${list.length}개 시험 기록</span>
    <button class="btn bp bsm" onclick="_openScoreNew()">+ 새 시험 추가</button>
  </div>
  ${rows}
</div>`;
}

// ── 입력/수정 뷰 ──────────────────────────────────────────────────────
function _openScoreNew(){scoreEditing=null;scoreView='edit';renderMain();}
function _openScoreEdit(clsKey,testKey){scoreEditing={clsKey,testKey};scoreView='edit';renderMain();}
function _cancelScoreEdit(){scoreEditing=null;scoreView='list';renderMain();}

function _renderScoreEdit(mc,a,clsKey){
  const existing=scoreEditing?(scoreData[clsKey]?.[scoreEditing.testKey]||{}):{};
  const students=cfg?.sheets?.[a.sheet]?.classes?.[a.cls]?.students||[];
  const isNew=!scoreEditing;
  const gs=getTbGrade(a.sheet,a.cls,a.tb)||'';
  const today=todayKey();

  const type=existing.type||'주간Test';
  const isCustom=!SCORE_TYPES.slice(0,-1).includes(type);
  const round=existing.round??'';          // 기본값 빈 문자열 → 선택사항
  const date=existing.date||today;
  const maxScore=existing.max_score||100;
  const memo=existing.memo||'';
  const scope=existing.scope||'class';     // 'class' | 'grade'
  const existStudents=existing.students||{};

  const typeOpts=SCORE_TYPES.map(t=>`<option${(isCustom&&t==='직접입력'||!isCustom&&t===type)?' selected':''}>${esc(t)}</option>`).join('');

  // scope 버튼 스타일
  const clsActive=scope!=='grade';
  const grdActive=scope==='grade';
  const clsBtnSt=clsActive?'background:var(--indigo);color:#fff;border-color:var(--indigo)':'';
  const grdBtnSt=grdActive?'background:var(--indigo);color:#fff;border-color:var(--indigo)':'';

  const studentRows=students.map(s=>{
    const sv=existStudents[s.name]!==undefined?existStudents[s.name]:'';
    return`<div class="score-row">
  <div class="score-sname">${esc(s.name)}</div>
  <input class="inp score-inp" type="number" min="0" max="${maxScore}" value="${esc(String(sv))}"
    data-name="${esc(s.name)}" oninput="_onScoreInput(this)" placeholder="-"
    style="width:80px;text-align:center;font-size:15px;touch-action:manipulation">
  <div class="score-slash">/${maxScore}</div>
</div>`;
  }).join('');

  mc.innerHTML=makeTb(isNew?'새 시험 추가':'시험 수정',`${a.cls} · ${a.tb}${gs?' · '+gs:''}`)+`
<div style="padding:12px 14px">

  <!-- 시험 범위 (scope) -->
  <div style="margin-bottom:10px">
    <div class="field-lbl">시험 범위</div>
    <div style="display:flex;gap:6px">
      <button class="btn bsm" id="sc-scope-class" style="flex:1;${clsBtnSt}" onclick="_onScopeChange('class')">🏫 반 단위</button>
      <button class="btn bsm" id="sc-scope-grade" style="flex:1;${grdBtnSt}" onclick="_onScopeChange('grade')">🎓 학년 단위</button>
    </div>
    <input type="hidden" id="sc-scope-val" value="${scope}">
    ${gs?`<div style="font-size:10px;color:var(--sub);margin-top:4px">학년학기: ${esc(gs)}</div>`:''}
  </div>

  <!-- 시험 유형 / 회차(선택) / 날짜 / 만점 -->
  <div class="score-form-grid">
    <div>
      <div class="field-lbl">시험 유형</div>
      <select class="sel" id="sc-type" onchange="_onScoreTypeChange()">${typeOpts}</select>
      <input class="inp" id="sc-type-custom" placeholder="시험명 직접 입력"
        style="margin-top:4px;display:${isCustom?'block':'none'}"
        value="${isCustom?esc(type):''}">
    </div>
    <div>
      <div class="field-lbl">회차 <span style="font-weight:400;color:var(--gray)">(선택)</span></div>
      <input class="inp" id="sc-round" type="text" value="${esc(String(round))}" placeholder="없음"
        style="text-align:center">
    </div>
    <div>
      <div class="field-lbl">날짜</div>
      <input class="inp" id="sc-date" type="date" value="${esc(date)}">
    </div>
    <div>
      <div class="field-lbl">만점</div>
      <input class="inp" id="sc-max" type="number" min="1" value="${esc(String(maxScore))}"
        oninput="_onMaxScoreChange(this)" style="text-align:center">
    </div>
  </div>

  <div style="margin-bottom:10px">
    <div class="field-lbl">메모 (선택)</div>
    <input class="inp" id="sc-memo" value="${esc(memo)}" placeholder="시험 범위, 특이사항 등">
  </div>

  <!-- 학생 점수 테이블 -->
  <div class="score-table">
    <div class="score-table-header">
      <div class="score-sname" style="font-size:11px;color:var(--sub);font-weight:700">학생</div>
      <div style="width:80px;text-align:center;font-size:11px;color:var(--sub);font-weight:700">점수</div>
      <div class="score-slash" style="font-size:11px;color:var(--sub)">만점</div>
    </div>
    <div id="scoreRows">${studentRows}</div>
    <div id="scoreStats" class="score-stats">${_scoreStatLine(existStudents,maxScore)}</div>
  </div>

  <div style="display:flex;gap:8px;margin-top:10px">
    <button class="btn bsm" onclick="_cancelScoreEdit()" style="flex:1">취소</button>
    <button class="btn bp bsm" onclick="_saveScore('${esc(clsKey)}')" style="flex:2">저장</button>
  </div>
</div>`;
}

// ── 이벤트 핸들러 ─────────────────────────────────────────────────────
function _onScopeChange(val){
  const hid=document.getElementById('sc-scope-val');
  if(hid)hid.value=val;
  const cb=document.getElementById('sc-scope-class');
  const gb=document.getElementById('sc-scope-grade');
  const act='background:var(--indigo);color:#fff;border-color:var(--indigo)';
  const idle='';
  if(cb)cb.style.cssText=`flex:1;${val==='class'?act:idle}`;
  if(gb)gb.style.cssText=`flex:1;${val==='grade'?act:idle}`;
}
function _onScoreTypeChange(){
  const sel=document.getElementById('sc-type');
  const inp=document.getElementById('sc-type-custom');
  if(inp)inp.style.display=sel?.value==='직접입력'?'block':'none';
}
function _onMaxScoreChange(el){
  const max=Number(el.value)||100;
  document.querySelectorAll('.score-slash').forEach(e=>{if(!e.style.fontWeight)e.textContent='/'+max;});
  document.querySelectorAll('.score-inp').forEach(i=>_onScoreInput(i));
}
function _onScoreInput(inp){
  const name=inp.dataset.name;
  const score=inp.value;
  const max=Number(document.getElementById('sc-max')?.value)||100;
  const statsEl=document.getElementById('scoreStats');
  if(statsEl){
    const studs={};
    document.querySelectorAll('.score-inp').forEach(i=>{if(i.dataset.name&&i.value!=='')studs[i.dataset.name]=Number(i.value);});
    statsEl.innerHTML=_scoreStatLine(studs,max);
  }
}

// ── 저장/삭제 ─────────────────────────────────────────────────────────
async function _saveScore(clsKey){
  const typeEl=document.getElementById('sc-type');
  const customEl=document.getElementById('sc-type-custom');
  const typeVal=typeEl?.value==='직접입력'?(customEl?.value.trim()||'직접입력'):typeEl?.value||'주간Test';
  const round=(document.getElementById('sc-round')?.value.trim())||''; // 빈 문자열 = 회차 없음
  const date=document.getElementById('sc-date')?.value||todayKey();
  const maxScore=Number(document.getElementById('sc-max')?.value)||100;
  const memo=document.getElementById('sc-memo')?.value.trim()||'';
  const scope=document.getElementById('sc-scope-val')?.value||'class';

  const students={};
  document.querySelectorAll('.score-inp').forEach(i=>{
    if(i.dataset.name&&i.value!=='')students[i.dataset.name]=Number(i.value);
  });

  // testKey: 회차 있으면 날짜|유형|회차, 없으면 날짜|유형
  const testKey=scoreEditing
    ?scoreEditing.testKey
    :(round?`${date}|${typeVal}|${round}`:`${date}|${typeVal}`);

  const testObj={type:typeVal,date,max_score:maxScore,scope,memo,students};
  if(round)testObj.round=round;

  // 학년 단위 시험이면 grade_sem 저장 (집계에 사용)
  const a=instructor?.assignments?.[curAI];
  if(scope==='grade'&&a){
    const gs=getTbGrade(a.sheet,a.cls,a.tb)||'';
    if(gs)testObj.grade_sem=gs;
  }

  if(!scoreData[clsKey])scoreData[clsKey]={};
  scoreData[clsKey][testKey]=testObj;
  await _pushScore(clsKey,testKey,testObj);

  scoreEditing=null;scoreView='list';
  toast('저장됨 ✅');renderMain();
}
async function _confirmDeleteScore(clsKey,testKey){
  if(!confirm('이 시험 기록을 삭제하시겠습니까?'))return;
  if(scoreData[clsKey])delete scoreData[clsKey][testKey];
  await _deleteScore(clsKey,testKey);
  toast('삭제됨');renderMain();
}


// ══════════════════════════════════════════════════════════
//  초기화
// ══════════════════════════════════════════════════════════
function init(){
  loadLocal();
  loadCurriculum();
  renderSb();
  if(!instructor){
    renderMhdr('DailyReportWizard');
    document.getElementById('mc').innerHTML=`<div class="empty">👋 안녕하세요!<br>먼저 강사 정보를 등록해 주세요.<br><br><button class="btn bp" onclick="goNav('setting')">⚙️ 설정으로 이동</button></div>`;
    return;
  }
  if(fbUrl&&fbPath){
    Promise.all([fbGet('config').catch(()=>null),fbGet('input').catch(()=>null),fbGet('session').catch(()=>null),fbGet('obs').catch(()=>null),fbGet('scores').catch(()=>null)])
    .then(([cfgD,inpD,sessD,obsD,scD])=>{
      if(cfgD){cfg=cfgD;saveLocal();setSync(true);}
      if(inpD)Object.assign(inputData,inpD);
      if(sessD?.class_data)for(const[k,v]of Object.entries(sessD.class_data))if(!progressData[k])progressData[k]=v;
      if(obsD)Object.assign(tagData,obsD);
      if(scD&&typeof scD==='object')scoreData=scD;
      if(inpD||sessD||obsD)saveLocal();
      _syncAssignments();
      renderMain();renderSb();
    }).catch(()=>{setSync(false);renderMain();});
  }
  renderMain();
}
init();
