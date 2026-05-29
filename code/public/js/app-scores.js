// ══════════════════════════════════════════════════════════════════════
//  성적 입력 (scores/)
// ══════════════════════════════════════════════════════════════════════

// ── Firebase 연동 ─────────────────────────────────────────────────────
async function _loadScoreDataIfNeeded(){
  if(!dbUrl||!dbPath)return;
  const a=instructor?.assignments?.[curAI];
  if(!a)return;
  try{
    const {classId, subject} = a;
    // weekly: scores/weekly/{classId}/{subject}
    const weeklyD=await fbGet(`scores/weekly/${classId}/${subject}`).catch(()=>null);
    if(!scoreData.weekly)scoreData.weekly={};
    if(!scoreData.weekly[classId])scoreData.weekly[classId]={};
    if(weeklyD&&typeof weeklyD==='object')scoreData.weekly[classId][subject]=weeklyD;

    // achievement (담임만): curriculum 기반
    const curriculum=getCurriculumForSubject(classId,subject);
    if(curriculum){
      const curriculumKey=curriculumToKey(curriculum);
      const achD=await fbGet(`scores/achievement/${curriculumKey}`).catch(()=>null);
      if(!scoreData.achievement)scoreData.achievement={};
      if(achD&&typeof achD==='object')scoreData.achievement[curriculumKey]=achD;
    }
    if(activeTab==='scores')renderMain();
  }catch(e){}
}

// 저장 경로 결정
function getScorePath(classId, subject, testKey, type){
  if(ACHIEVEMENT_TYPES.includes(type)){
    const curriculum=getCurriculumForSubject(classId,subject);
    const curriculumKey=curriculumToKey(curriculum);
    return `scores/achievement/${curriculumKey}/${testKey}`;
  }
  return `scores/weekly/${classId}/${subject}/${testKey}`;
}

async function _pushScore(classId, subject, testKey, val, type){
  if(!dbUrl||!dbPath)return;
  const path=getScorePath(classId,subject,testKey,type||val.type||'');
  try{await fbPatch(path.slice(0,path.lastIndexOf('/')),{[testKey]:val});}catch(e){}
}
async function _deleteScore(classId, subject, testKey, type){
  if(!dbUrl||!dbPath)return;
  const path=getScorePath(classId,subject,testKey,type||'');
  try{await fbPatch(path.slice(0,path.lastIndexOf('/')),{[testKey]:null});}catch(e){}
}

// ── 반별 시험 권한: 해당 subject의 instructor만 ────────────────────
function _canInputWeekly(classId, subject){
  const course=config?.classes?.[classId]?.courses?.[subject];
  return course?.instructor===instructor?.id;
}
// 학년단위 시험: 담임 여부 (assignments에 해당 classId+subject가 있고 role이 '담임')
function _canInputAchievement(classId){
  return (instructor?.assignments||[]).some(a=>a.classId===classId&&(a.role||'담임')==='담임');
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
function _pctStatLine(pctStu){
  const vs=Object.values(pctStu||{}).filter(v=>!isNaN(v)).map(Number);
  if(!vs.length)return'<span style="color:var(--sub)">데이터 없음</span>';
  const avg=vs.reduce((a,b)=>a+b,0)/vs.length;
  const maxV=Math.max(...vs),minV=Math.min(...vs);
  return`평균: <strong>${avg.toFixed(1)}점</strong> · 최고: <strong>${maxV.toFixed(0)}점</strong> · 최저: <strong>${minV.toFixed(0)}점</strong> · ${vs.length}명`;
}

// ── 학년 단위 집계 (achievement) ─────────────────────────────────────
function _achievementAggregate(curriculumKey, testKey){
  const tests=scoreData?.achievement?.[curriculumKey]||{};
  const tv=tests[testKey];
  if(!tv)return null;
  const studs=tv.students||{};
  const vs=Object.values(studs).filter(v=>v!==''&&v!==null&&!isNaN(v));
  if(!vs.length)return null;
  return{rawStudents:studs,count:vs.length};
}

// ── 메인 렌더 ─────────────────────────────────────────────────────────
function renderScores(mc){
  const a=instructor?.assignments?.[curAI];
  if(!a){
    mc.innerHTML=makeTb('성적 입력')+`<div style="padding:20px;color:var(--sub)">좌측 사이드바에서 담당 수업을 선택하세요.</div>`;
    return;
  }
  const {classId, subject} = a;
  if(scoreView==='edit')_renderScoreEdit(mc,a,classId,subject);
  else _renderScoreList(mc,a,classId,subject);
}

// ── 목록 뷰 ──────────────────────────────────────────────────────────
function _renderScoreList(mc,a,classId,subject){
  const weeklyTests=scoreData?.weekly?.[classId]?.[subject]||{};
  const curriculum=getCurriculumForSubject(classId,subject)||'';
  const curriculumKey=curriculumToKey(curriculum);
  const achievementTests=curriculumKey?(scoreData?.achievement?.[curriculumKey]||{}):{};
  const gs=curriculum?(GRADE_SEM_LIST.find(g=>g.val===curriculum)?.label||curriculum):'';

  // 합산: weekly + achievement (각각 타입 표기)
  const weeklyEntries=Object.entries(weeklyTests).map(([tk,tv])=>([tk,tv,'weekly']));
  const achievementEntries=Object.entries(achievementTests).map(([tk,tv])=>([tk,tv,'achievement']));
  const list=[...weeklyEntries,...achievementEntries].sort(([ka],[kb])=>kb.localeCompare(ka));

  let rows='';
  if(list.length===0){
    rows=`<div style="padding:20px;text-align:center;color:var(--sub);font-size:12px">시험 기록이 없습니다.</div>`;
  }else{
    rows=list.map(([tk,tv,kind])=>{
      const isAchievement=kind==='achievement';
      const meta=tv.meta||tv; // 신규: meta 서브키 지원
      const students=tv.students||{};
      const avg=_scoreAvg(students);
      const cnt=Object.values(students).filter(v=>v!==''&&v!==null&&!isNaN(v)).length;
      const classStudentCount=(config?._classStudents||{})[classId]?.length||0;
      const maxScore=meta.max_score||100;

      // 학년 단위: 전체 집계
      let gradeLine='';
      if(isAchievement&&curriculumKey){
        const agg=_achievementAggregate(curriculumKey,tk);
        if(agg){
          gradeLine=`<div style="margin-top:6px;padding:6px 8px;background:var(--indigo-l);border-radius:6px;font-size:11px">
            🎓 학년 집계 · ${_pctStatLine(agg.rawStudents)}
          </div>`;
        }
      }

      const scopeBadge=isAchievement
        ?`<span style="font-size:10px;background:#DCFCE7;color:#15803D;border-radius:4px;padding:1px 6px;font-weight:700;margin-left:4px">학년</span>`
        :`<span style="font-size:10px;background:#F1F5F9;color:#64748B;border-radius:4px;padding:1px 6px;font-weight:700;margin-left:4px">반</span>`;

      return`<div class="score-card">
  <div class="score-card-top">
    <div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px">
      <span class="score-type-badge">${esc(meta.type||'')}</span>
      ${meta.round?`<span class="score-round">${esc(meta.round)}회</span>`:''}
      ${scopeBadge}
      <span class="score-date">${esc(meta.date||'')}</span>
    </div>
    <div style="display:flex;gap:6px;flex-shrink:0">
      <button class="btn bsm" onclick="_openScoreEdit('${esc(classId)}','${esc(subject)}','${esc(tk)}','${isAchievement?'1':'0'}')">수정</button>
      <button class="btn bsm" style="color:var(--red)" onclick="_confirmDeleteScore('${esc(classId)}','${esc(subject)}','${esc(tk)}','${esc(meta.type||'')}')">삭제</button>
    </div>
  </div>
  <div class="score-card-bottom">
    <span style="font-size:11px;color:var(--sub)">만점 ${maxScore}점</span>
    ${avg!==null?`<span style="font-size:11px;color:var(--sub)">· 반 평균 <strong>${avg.toFixed(1)}점</strong></span>`:''}
    <span style="font-size:11px;color:var(--sub)">· ${cnt}/${classStudentCount}명 입력</span>
    ${meta.memo?`<span style="font-size:11px;color:var(--sub);margin-left:4px">📝 ${esc(meta.memo)}</span>`:''}
  </div>
  ${gradeLine}
</div>`;
    }).join('');
  }

  mc.innerHTML=makeTb('성적 입력',`${classId} · ${subject}${gs?' · '+gs:''}`)+`
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
function _openScoreEdit(classId,subject,testKey,isAchievementStr){
  const isAchievement=isAchievementStr==='1';
  scoreEditing={classId,subject,testKey,isAchievement};
  scoreView='edit';renderMain();
}
function _cancelScoreEdit(){scoreEditing=null;scoreView='list';renderMain();}

function _renderScoreEdit(mc,a,classId,subject){
  const curriculum=getCurriculumForSubject(classId,subject)||'';
  const curriculumKey=curriculumToKey(curriculum);
  const gs=curriculum?(GRADE_SEM_LIST.find(g=>g.val===curriculum)?.label||curriculum):'';
  const today=todayKey();

  let existing={};
  if(scoreEditing){
    if(scoreEditing.isAchievement){
      const testObj=scoreData?.achievement?.[curriculumKey]?.[scoreEditing.testKey]||{};
      existing={...(testObj.meta||testObj),students:testObj.students||{}};
    } else {
      const testObj=scoreData?.weekly?.[classId]?.[subject]?.[scoreEditing.testKey]||{};
      existing={...(testObj.meta||testObj),students:testObj.students||{}};
    }
  }

  const students=(config?._classStudents||{})[classId]||[];
  const isNew=!scoreEditing;

  const type=existing.type||'주간Test';
  const isCustom=!SCORE_TYPES.slice(0,-1).includes(type);
  const round=existing.round??'';
  const date=existing.date||today;
  const maxScore=existing.max_score||100;
  const memo=existing.memo||'';
  const existStudents=existing.students||{};

  const typeOpts=SCORE_TYPES.map(t=>`<option${(isCustom&&t==='직접입력'||!isCustom&&t===type)?' selected':''}>${esc(t)}</option>`).join('');

  const studentRows=students.map(s=>{
    // 신규: students 키는 nameKey
    const sv=existStudents[s.nameKey]!==undefined?existStudents[s.nameKey]:'';
    return`<div class="score-row">
  <div class="score-sname">${esc(s.name||s.nameKey)}</div>
  <input class="inp score-inp" type="number" min="0" max="${maxScore}" value="${esc(String(sv))}"
    data-namekey="${esc(s.nameKey)}" oninput="_onScoreInput(this)" placeholder="-"
    style="width:80px;text-align:center;font-size:15px;touch-action:manipulation">
  <div class="score-slash">/${maxScore}</div>
</div>`;
  }).join('');

  mc.innerHTML=makeTb(isNew?'새 시험 추가':'시험 수정',`${classId} · ${subject}${gs?' · '+gs:''}`)+`
<div style="padding:12px 14px">

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

  ${gs?`<div style="font-size:10px;color:var(--sub);margin-bottom:8px">커리큘럼: ${esc(gs)}</div>`:''}

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
    <button class="btn bp bsm" onclick="_saveScore('${esc(classId)}','${esc(subject)}')" style="flex:2">저장</button>
  </div>
</div>`;
}

// ── 이벤트 핸들러 ─────────────────────────────────────────────────────
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
  const max=Number(document.getElementById('sc-max')?.value)||100;
  const statsEl=document.getElementById('scoreStats');
  if(statsEl){
    const studs={};
    document.querySelectorAll('.score-inp').forEach(i=>{if(i.dataset.namekey&&i.value!=='')studs[i.dataset.namekey]=Number(i.value);});
    statsEl.innerHTML=_scoreStatLine(studs,max);
  }
}

// ── 저장/삭제 ─────────────────────────────────────────────────────────
async function _saveScore(classId, subject){
  const typeEl=document.getElementById('sc-type');
  const customEl=document.getElementById('sc-type-custom');
  const typeVal=typeEl?.value==='직접입력'?(customEl?.value.trim()||'직접입력'):typeEl?.value||'주간Test';
  const round=(document.getElementById('sc-round')?.value.trim())||'';
  const date=document.getElementById('sc-date')?.value||todayKey();
  const maxScore=Number(document.getElementById('sc-max')?.value)||100;
  const memo=document.getElementById('sc-memo')?.value.trim()||'';

  // students 키: nameKey
  const students={};
  document.querySelectorAll('.score-inp').forEach(i=>{
    if(i.dataset.namekey&&i.value!=='')students[i.dataset.namekey]=Number(i.value);
  });

  // testKey: 회차 있으면 날짜|유형|회차, 없으면 날짜|유형
  const testKey=scoreEditing
    ?scoreEditing.testKey
    :(round?`${date}|${typeVal}|${round}`:`${date}|${typeVal}`);

  const isAchievement=ACHIEVEMENT_TYPES.includes(typeVal);

  // 신규 구조: meta + students 분리
  const metaObj={type:typeVal,date,max_score:maxScore,memo};
  if(round)metaObj.round=round;
  const testObj={meta:metaObj,students};

  // 권한 체크
  if(isAchievement&&!_canInputAchievement(classId)){toast('학년단위 시험은 담임만 입력할 수 있습니다.');return;}
  if(!isAchievement&&!_canInputWeekly(classId,subject)){toast('이 수업의 담당 강사만 입력할 수 있습니다.');return;}

  const curriculum=getCurriculumForSubject(classId,subject)||'';
  const curriculumKey=curriculumToKey(curriculum);

  if(isAchievement){
    if(!scoreData.achievement)scoreData.achievement={};
    if(!scoreData.achievement[curriculumKey])scoreData.achievement[curriculumKey]={};
    scoreData.achievement[curriculumKey][testKey]=testObj;
    if(dbUrl&&dbPath)await fbPatch(`scores/achievement/${curriculumKey}`,{[testKey]:testObj}).catch(()=>{});
  } else {
    if(!scoreData.weekly)scoreData.weekly={};
    if(!scoreData.weekly[classId])scoreData.weekly[classId]={};
    if(!scoreData.weekly[classId][subject])scoreData.weekly[classId][subject]={};
    scoreData.weekly[classId][subject][testKey]=testObj;
    if(dbUrl&&dbPath)await fbPatch(`scores/weekly/${classId}/${subject}`,{[testKey]:testObj}).catch(()=>{});
  }

  scoreEditing=null;scoreView='list';
  toast('저장됨 ✅');renderMain();
}
async function _confirmDeleteScore(classId,subject,testKey,type){
  if(!confirm('이 시험 기록을 삭제하시겠습니까?'))return;
  const isAchievement=ACHIEVEMENT_TYPES.includes(type);
  const curriculum=getCurriculumForSubject(classId,subject)||'';
  const curriculumKey=curriculumToKey(curriculum);
  if(isAchievement){
    if(scoreData.achievement?.[curriculumKey])delete scoreData.achievement[curriculumKey][testKey];
    if(dbUrl&&dbPath)await fbPatch(`scores/achievement/${curriculumKey}`,{[testKey]:null}).catch(()=>{});
  } else {
    if(scoreData.weekly?.[classId]?.[subject])delete scoreData.weekly[classId][subject][testKey];
    if(dbUrl&&dbPath)await fbPatch(`scores/weekly/${classId}/${subject}`,{[testKey]:null}).catch(()=>{});
  }
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
  if(dbUrl&&dbPath){
    // 신규: config(instructors), 최상위 classes/, students/ 전체, input, session, obs, scores 로드
    Promise.all([
      fbGet('config').catch(()=>null),
      fbGet('classes').catch(()=>null),
      fbGet('students').catch(()=>null),
      fbGet('input').catch(()=>null),
      fbGet('session').catch(()=>null),
      fbGet('obs').catch(()=>null),
      fbGet('scores').catch(()=>null),
    ])
    .then(([cfgD,clsD,stuD,inpD,sessD,obsD,scD])=>{
      // config 노드가 없어도(null) 최상위 classes/·students/만으로 명단 구성
      config=cfgD||config||{classes:{},instructors:{}};
      if(clsD&&typeof clsD==='object')config.classes=clsD;
      if(!config.classes)config.classes={};
      if(!config.instructors)config.instructors={};
      // students를 classId별로 캐싱
      if(stuD&&typeof stuD==='object'){
        const classStudents={};
        for(const[nameKey,v] of Object.entries(stuD)){
          const cid=v?.class;
          if(cid){
            if(!classStudents[cid])classStudents[cid]=[];
            classStudents[cid].push({nameKey,...v});
          }
        }
        config._classStudents=classStudents;
      }
      saveLocal();setSync(true);
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
