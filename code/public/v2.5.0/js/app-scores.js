// ══════════════════════════════════════════════════════════════════════
//  성적 입력 (scores/)
// ══════════════════════════════════════════════════════════════════════

// ── Firebase 연동 ─────────────────────────────────────────────────────
async function _loadScoreDataIfNeeded(){
  if(!dbUrl||!dbPath)return;
  const a=curAsgn();
  if(!a)return;
  try{
    const {classId, subject} = a;
    // weekly: scores/weekly/{classId}/{subject} — null=빈 노드(스테일 캐시 클리어), undefined=fetch 실패(로컬 유지)
    const weeklyD=await fbGet(`scores/weekly/${classId}/${subject}`).catch(()=>undefined);
    if(!scoreData.weekly)scoreData.weekly={};
    if(!scoreData.weekly[classId])scoreData.weekly[classId]={};
    if(weeklyD!==undefined)scoreData.weekly[classId][subject]=(weeklyD&&typeof weeklyD==='object')?weeklyD:{};

    // achievement (담임만): curriculum 기반
    const curriculum=getCurriculumForSubject(classId,subject);
    if(curriculum){
      const curriculumKey=curriculumToKey(curriculum);
      const achD=await fbGet(`scores/achievement/${curriculumKey}`).catch(()=>undefined);
      if(!scoreData.achievement)scoreData.achievement={};
      if(achD!==undefined)scoreData.achievement[curriculumKey]=(achD&&typeof achD==='object')?achD:{};
    }
    if(activeTab==='scores')renderMain();
  }catch(e){}
}

// ── 경로/캐시 헬퍼 ────────────────────────────────────────────────────
// testKey 조각 소독: Firebase 키 금지문자(. # $ [ ] /)와 구분자(|) 치환 — 표시값은 meta에 원형 보존
function _scoreKeySafe(s){return String(s).replace(/[.#$\[\]\/|]/g,'-').trim();}
// 회차 정규화(키 식별용): "1회"·"1 회" → "1" — 표기 차이로 같은 시험이 갈라지지 않게. 표시값은 원형
function _normRound(r){const m=String(r).trim().match(/^(\d+)\s*회$/);return m?m[1]:String(r).trim();}
function _scoreBasePath(isAchievement,classId,subject){
  if(isAchievement){
    const curriculum=getCurriculumForSubject(classId,subject)||'';
    return `scores/achievement/${curriculumToKey(curriculum)}`;
  }
  return `scores/weekly/${classId}/${subject}`;
}
// 로컬 캐시 컨테이너 반환(없으면 생성)
function _scoreNodeRef(isAchievement,classId,subject){
  if(isAchievement){
    const curriculum=getCurriculumForSubject(classId,subject)||'';
    const ck=curriculumToKey(curriculum);
    if(!scoreData.achievement)scoreData.achievement={};
    if(!scoreData.achievement[ck])scoreData.achievement[ck]={};
    return scoreData.achievement[ck];
  }
  if(!scoreData.weekly)scoreData.weekly={};
  if(!scoreData.weekly[classId])scoreData.weekly[classId]={};
  if(!scoreData.weekly[classId][subject])scoreData.weekly[classId][subject]={};
  return scoreData.weekly[classId][subject];
}

// ── 반별 시험 권한: 해당 수업이 내 담당 배정(assignments)에 있으면 허용 ──
function _canInputWeekly(classId, subject){
  const course=config?.classes?.[classId]?.courses?.[subject];
  if(course?.archived)return false; // 보관 과목은 입력 차단 (관리자 포함)
  if(adminOn)return true; // 관리자 모드: 전체 수업 바운더리
  // v2.2.3: course.instructor 필드 → assignments 기준으로 교체.
  // 과목 등록이 instructor를 저장한 적이 없어(실DB 36개 과목 전부 미보유) 주간성적 저장이 전원 차단되던 버그.
  return (instructor?.assignments||[]).some(a=>a.classId===classId&&a.subject===subject);
}
// 학년단위 시험: 담임 여부 (assignments에 해당 classId+subject가 있고 role이 '담임')
function _canInputAchievement(classId){
  if(adminOn)return true; // 관리자 모드: 담임 제한 해제
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


// ── 메인 렌더 ─────────────────────────────────────────────────────────
function renderScores(mc){
  const a=curAsgn();
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

  // 합산: weekly + achievement (각각 타입 표기) — meta.date 기준 최신순(키는 보조)
  const weeklyEntries=Object.entries(weeklyTests).map(([tk,tv])=>([tk,tv,'weekly']));
  const achievementEntries=Object.entries(achievementTests).map(([tk,tv])=>([tk,tv,'achievement']));
  const list=[...weeklyEntries,...achievementEntries].sort(([ka,va],[kb,vb])=>{
    const da=(va?.meta||va||{}).date||'',db=(vb?.meta||vb||{}).date||'';
    return db.localeCompare(da)||kb.localeCompare(ka);
  });

  let rows='';
  if(list.length===0){
    rows=`<div style="padding:20px;text-align:center;color:var(--sub);font-size:12px">시험 기록이 없습니다.</div>`;
  }else{
    rows=list.map(([tk,tv,kind])=>{
      const isAchievement=kind==='achievement';
      const meta=tv.meta||tv; // 신규: meta 서브키 지원
      const students=tv.students||{}; // 학년 시험이면 과정 전체 코호트
      // 카드 통계(반 평균·입력 인원)는 현재 반 학생만 — 학년 공유 노드를 그대로 쓰면 반 평균=학년 평균이 됨
      const roster=new Set(((config?._classStudents||{})[classId]||[]).map(s=>s.nameKey));
      const classStu=isAchievement
        ?Object.fromEntries(Object.entries(students).filter(([nk])=>roster.has(nk)))
        :students;
      const avg=_scoreAvg(classStu);
      const cnt=Object.values(classStu).filter(v=>v!==''&&v!==null&&!isNaN(v)).length;
      const classStudentCount=(config?._classStudents||{})[classId]?.length||0;
      const maxScore=meta.max_score||100;

      // 학년 단위: 전체 집계 — 원점수 그대로, 과정 수강생 전체 코호트 기준
      let gradeLine='';
      if(isAchievement&&curriculumKey&&_scoreAvg(students)!==null){
        gradeLine=`<div style="margin-top:6px;padding:6px 8px;background:var(--indigo-l);border-radius:6px;font-size:11px">
          🎓 학년 집계 · ${_scoreStatLine(students,maxScore)}
        </div>`;
      }

      const scopeBadge=isAchievement
        ?`<span style="font-size:10px;background:#DCFCE7;color:#15803D;border-radius:4px;padding:1px 6px;font-weight:700;margin-left:4px">학년</span>`
        :`<span style="font-size:10px;background:#F1F5F9;color:#64748B;border-radius:4px;padding:1px 6px;font-weight:700;margin-left:4px">반</span>`;

      return`<div class="score-card">
  <div class="score-card-top">
    <div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px">
      <span class="score-type-badge">${esc(meta.type||'')}</span>
      ${meta.round?`<span class="score-round">${esc(String(meta.round).replace(/\s*회$/,''))}회</span>`:''}
      ${scopeBadge}
      <span class="score-date">${esc(meta.date||'')}</span>
    </div>
    <div style="display:flex;gap:6px;flex-shrink:0">
      <button class="btn bsm" onclick="_openScoreEdit('${esc(classId)}','${esc(subject)}','${esc(tk)}','${isAchievement?'1':'0'}')">수정</button>
      <button class="btn bsm" style="color:var(--red)" onclick="_confirmDeleteScore('${esc(classId)}','${esc(subject)}','${esc(tk)}','${isAchievement?'1':'0'}')">삭제</button>
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

  // 관리자 휴지통 — 삭제된 시험 스냅샷 복원/영구삭제
  let trashHtml='';
  if(adminOn){
    trashHtml=`<div style="margin-top:16px;border-top:1px dashed var(--line);padding-top:10px">
      <button class="btn bsm" onclick="_toggleScoreTrash()">🗑 휴지통 ${scoreTrashOpen?'접기':'열기'}</button>`;
    if(scoreTrashOpen){
      const entries=Object.entries(_trashCache||{}).sort(([a],[b])=>b.localeCompare(a));
      trashHtml+=entries.length?entries.map(([k,e])=>{
        const m=e?.test?.meta||e?.test||{};
        const n=Object.keys(e?.test?.students||{}).length;
        return`<div class="score-card" style="opacity:.85;margin-top:8px">
  <div class="score-card-top">
    <div style="font-size:12px;line-height:1.5">
      <strong>${esc(m.type||'')}</strong>${m.round?` ${esc(m.round)}회`:''} · ${esc(m.date||'')} · ${n}명
      <div style="font-size:10px;color:var(--sub)">${esc(e.reason||'')} · ${esc((e.deletedAt||'').slice(0,16).replace('T',' '))}${e.by?` · ${esc(e.by)}`:''}</div>
    </div>
    <div style="display:flex;gap:6px;flex-shrink:0">
      <button class="btn bsm" onclick="_restoreScoreTrash('${esc(k)}')">↩ 복원</button>
      <button class="btn bsm" style="color:var(--red)" onclick="_purgeScoreTrash('${esc(k)}')">영구 삭제</button>
    </div>
  </div>
</div>`;
      }).join(''):`<div style="padding:10px;color:var(--sub);font-size:12px">휴지통이 비어 있습니다.</div>`;
    }
    trashHtml+='</div>';
  }

  mc.innerHTML=makeTb('성적 입력',`${classId} · ${subject}${gs?' · '+gs:''}`)+`
<div style="padding:12px 14px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <span style="font-size:12px;color:var(--sub)">${list.length}개 시험 기록</span>
    <button class="btn bp bsm" onclick="_openScoreNew()">+ 새 시험 추가</button>
  </div>
  ${rows}
  ${trashHtml}
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
    <div id="scoreStats" class="score-stats">${_scoreStatLine(
      Object.fromEntries(Object.entries(existStudents).filter(([nk])=>students.some(s=>s.nameKey===nk))),
      maxScore)}</div>
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
  // 유형별 기본 만점 동적 세팅 (성취도평가·반배치고사 150, 그 외 100) — 직접입력은 사용자 지정 유지
  if(sel&&sel.value!=='직접입력'){
    const maxEl=document.getElementById('sc-max');
    if(maxEl){maxEl.value=SCORE_TYPE_MAX[sel.value]||100;_onMaxScoreChange(maxEl);}
  }
}
function _onMaxScoreChange(el){
  const max=Number(el.value)||100;
  // #scoreRows 한정 — 테이블 헤더의 "만점" 라벨(.score-slash)은 건드리지 않음
  document.querySelectorAll('#scoreRows .score-slash').forEach(e=>{e.textContent='/'+max;});
  document.querySelectorAll('.score-inp').forEach(i=>{i.max=max;_onScoreInput(i);});
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
// 저장 원칙:
// ① 화면에 렌더된(현재 반) 학생만 갱신/삭제 — 미렌더 키(학년 공유 노드의 타 반 학생, 전출생)는 보존
// ② 제자리 수정은 meta/·students/ 서브경로 PATCH — 타 담임 동시 입력과 충돌 없음
// ③ 날짜·유형·회차 변경 시 testKey 재계산 후 새 위치로 이동(구 위치 삭제) — weekly↔achievement 경계 포함
async function _saveScore(classId, subject){
  const typeEl=document.getElementById('sc-type');
  const customEl=document.getElementById('sc-type-custom');
  const typeVal=typeEl?.value==='직접입력'?(customEl?.value.trim()||'직접입력'):typeEl?.value||'주간Test';
  // 회차는 저장 시점에 정규화("1회"→"1") — 카드 "N회" 표기 중복("1회회") 방지, 키와 일치
  const round=_normRound((document.getElementById('sc-round')?.value.trim())||'');
  const date=document.getElementById('sc-date')?.value||todayKey();
  const maxScore=Number(document.getElementById('sc-max')?.value)||100;
  if(!(maxScore>=1)){toast('만점은 1 이상이어야 합니다.');return;}
  const memo=document.getElementById('sc-memo')?.value.trim()||'';

  // 점수 수집 + 범위 검증 (0~만점)
  const students={};        // 입력된 값 {nameKey: Number}
  const rendered=new Set(); // 화면에 렌더된 학생 — 이들만 갱신/삭제 대상
  const invalid=[];
  document.querySelectorAll('.score-inp').forEach(i=>{
    if(!i.dataset.namekey)return;
    rendered.add(i.dataset.namekey);
    if(i.value==='')return;
    const v=Number(i.value);
    if(isNaN(v)||v<0||v>maxScore){invalid.push(i.dataset.namekey);return;}
    students[i.dataset.namekey]=v;
  });
  if(invalid.length){toast(`0~${maxScore}점 범위를 벗어난 점수가 ${invalid.length}건 있습니다.`);return;}

  const isAchievement=ACHIEVEMENT_TYPES.includes(typeVal);

  // 권한 체크
  if(isAchievement&&!_canInputAchievement(classId)){toast('학년단위 시험은 담임만 입력할 수 있습니다.');return;}
  if(!isAchievement&&!_canInputWeekly(classId,subject)){toast('이 수업의 담당 강사만 입력할 수 있습니다.');return;}

  // testKey — 항상 현재 내용으로 재계산(수정 시 키-내용 불일치 방지), 조각은 소독
  //  반별: 날짜|유형[|회차] — 날짜 기반 식별
  //  학년: 유형[|회차] — 날짜 제외. 반·학생별 시행일이 달라도(또는 강사가 기본 오늘 날짜를 그대로 둬도)
  //        같은 시험으로 묶임. 날짜는 meta에만 보관(마지막 저장 기준 대표값)
  const kType=_scoreKeySafe(typeVal);
  const kRound=round?_scoreKeySafe(_normRound(round)):'';
  const testKey=isAchievement
    ?(kRound?`${kType}|${kRound}`:kType)
    :(kRound?`${date}|${kType}|${kRound}`:`${date}|${kType}`);

  const metaObj={type:typeVal,date,max_score:maxScore,memo:memo||null,round:round||null};

  const base=_scoreBasePath(isAchievement,classId,subject);
  const node=_scoreNodeRef(isAchievement,classId,subject);

  // 기존 위치(수정 모드) 및 이동 여부
  const oldIsAch=!!scoreEditing?.isAchievement;
  const oldKey=scoreEditing?.testKey;
  const moved=!!scoreEditing&&(oldIsAch!==isAchievement||oldKey!==testKey);
  const oldNode=scoreEditing?_scoreNodeRef(oldIsAch,classId,subject):null;

  // 무음 덮어쓰기 방지 (식별자 — 반별: 날짜·유형·회차 / 학년: 유형·회차)
  const idLabel=isAchievement?'유형·회차':'날짜·유형·회차';
  if(!scoreEditing&&node[testKey]
    &&!confirm(`같은 ${idLabel}의 기록이 이미 있습니다.\n기존 기록에 이어서(병합) 저장할까요?`))return;
  if(moved&&node[testKey]
    &&!confirm(`변경한 ${idLabel}에 이미 다른 기록이 있습니다.\n그 기록과 병합할까요?`))return;

  // students 머지: 보존 대상 = (이동 시)구 위치 + 대상 위치의 미렌더 키
  const prevStu={
    ...((node[testKey]?.students)||{}),
    ...(scoreEditing?((oldNode[oldKey]||{}).students||{}):{}),
  };
  rendered.forEach(nk=>{delete prevStu[nk];});
  const mergedStu={...prevStu,...students};

  const inPlace=scoreEditing?!moved:!!node[testKey];
  node[testKey]={meta:metaObj,students:mergedStu};

  if(inPlace){
    // 제자리 갱신: 서브경로 PATCH — 렌더된 키만 전송(값 또는 삭제 null)
    const stuPatch={};
    rendered.forEach(nk=>{stuPatch[nk]=(nk in students)?students[nk]:null;});
    if(dbUrl&&dbPath){
      await fbPatch(`${base}/${testKey}/meta`,metaObj).catch(fbFail('성적'));
      if(Object.keys(stuPatch).length)
        await fbPatch(`${base}/${testKey}/students`,stuPatch).catch(fbFail('성적'));
    }
  }else{
    // 신규 또는 위치 이동: 전체 노드 기록 (+이동 시 구 위치 삭제)
    if(moved)delete oldNode[oldKey];
    if(dbUrl&&dbPath){
      await fbPatch(base,{[testKey]:{meta:metaObj,students:mergedStu}}).catch(fbFail('성적'));
      if(moved)
        await fbPatch(_scoreBasePath(oldIsAch,classId,subject),{[oldKey]:null}).catch(fbFail('성적'));
    }
  }

  scoreEditing=null;scoreView='list';
  toast('저장됨 ✅');renderMain();
}
// ── 휴지통 (scores/trash/) — 삭제 전 스냅샷, 관리자 복원 ─────────────
// 백업 실패 시 false 반환 → 호출부에서 삭제 중단 (백업 없는 파괴 금지)
async function _trashScore(basePath,testKey,testObj,reason){
  if(!dbUrl||!dbPath)return true; // 오프라인(로컬 전용)은 통과
  const trashKey=`${Date.now()}_${_scoreKeySafe(testKey)}`.slice(0,120);
  const entry={path:basePath,testKey,reason,deletedAt:new Date().toISOString(),
    by:instructor?.name||instructor?.id||'',test:testObj};
  try{await fbPatch('scores/trash',{[trashKey]:entry});return true;}
  catch(e){fbFail('휴지통 백업')(e);return false;}
}

async function _confirmDeleteScore(classId,subject,testKey,isAchievementStr){
  // 소속 컬렉션(kind) 기준 — type 문자열 추정은 구형/커스텀 유형에서 오판
  const isAchievement=isAchievementStr==='1';
  const node=_scoreNodeRef(isAchievement,classId,subject);
  const tv=node[testKey];
  if(!tv)return;
  const base=_scoreBasePath(isAchievement,classId,subject);

  // 학년 공유 시험 + 비관리자: 내 반 점수만 비우기 — 한 명의 실수가 학년 전체를 날리지 못하게
  if(isAchievement&&!adminOn){
    const roster=new Set(((config?._classStudents||{})[classId]||[]).map(s=>s.nameKey));
    const mine=Object.keys(tv.students||{}).filter(nk=>roster.has(nk));
    if(!mine.length){toast('이 시험에 우리 반 점수가 없습니다. 시험 전체 삭제는 관리자 전용입니다.');return;}
    if(!confirm(`학년 공유 시험입니다. 우리 반 ${mine.length}명의 점수만 삭제됩니다.\n(시험 전체 삭제는 관리자 전용 · 삭제 전 휴지통 백업)`))return;
    if(!await _trashScore(base,testKey,tv,`반 점수 삭제(${classId})`))return;
    const remaining={...(tv.students||{})};
    mine.forEach(nk=>{delete remaining[nk];});
    if(Object.keys(remaining).length){
      tv.students=remaining;
      const patch={};mine.forEach(nk=>{patch[nk]=null;});
      if(dbUrl&&dbPath)await fbPatch(`${base}/${testKey}/students`,patch).catch(fbFail('성적 삭제'));
    }else{
      delete node[testKey]; // 마지막 반이었으면 빈 노드 정리
      if(dbUrl&&dbPath)await fbPatch(base,{[testKey]:null}).catch(fbFail('성적 삭제'));
    }
    toast('우리 반 점수 삭제됨 (휴지통 백업) 🗑');renderMain();return;
  }

  // 반별 시험, 또는 관리자의 학년 시험 전체 삭제
  if(!confirm(isAchievement
    ?'[관리자] 학년 공유 시험 전체를 삭제합니다.\n모든 반의 점수가 삭제됩니다. (삭제 전 휴지통 백업)'
    :'이 시험 기록을 삭제하시겠습니까? (삭제 전 휴지통 백업)'))return;
  if(!await _trashScore(base,testKey,tv,isAchievement?'학년 시험 전체 삭제':`반별 시험 삭제(${classId})`))return;
  delete node[testKey];
  if(dbUrl&&dbPath)await fbPatch(base,{[testKey]:null}).catch(fbFail('성적 삭제'));
  toast('삭제됨 (휴지통 백업) 🗑');renderMain();
}

// ── 휴지통 보기/복원/영구삭제 (관리자) ────────────────────────────────
let scoreTrashOpen=false,_trashCache=null;
async function _toggleScoreTrash(){
  if(scoreTrashOpen){scoreTrashOpen=false;renderMain();return;}
  _trashCache=(await fbGet('scores/trash').catch(()=>null))||{};
  scoreTrashOpen=true;renderMain();
}
async function _restoreScoreTrash(k){
  const e=_trashCache?.[k];
  if(!e||!e.path||!e.testKey||!e.test)return;
  if(!confirm('이 기록을 원래 위치로 복원할까요?\n(현재 같은 키에 기록이 있으면 덮어씁니다)'))return;
  await fbPatch(e.path,{[e.testKey]:e.test}).catch(fbFail('복원'));
  await fbPatch('scores/trash',{[k]:null}).catch(()=>{});
  delete _trashCache[k];
  _loadScoreDataIfNeeded(); // 현재 보기 경로 재로드
  toast('복원됨 ↩');renderMain();
}
async function _purgeScoreTrash(k){
  if(!confirm('휴지통에서 영구 삭제합니다. 복원할 수 없습니다.'))return;
  await fbPatch('scores/trash',{[k]:null}).catch(fbFail('영구 삭제'));
  delete _trashCache[k];
  toast('영구 삭제됨');renderMain();
}


// ══════════════════════════════════════════════════════════
//  초기화
// ══════════════════════════════════════════════════════════
function init(){
  loadLocal();
  loadCurriculum();
  if(_isTopAdmin())adminOn=true; // 운영자(admin/super)는 관리자 모드 고정 — 강사 모드 불요
  renderSb();
  if(!instructor){
    // v2.5.0: 온보딩 위저드 폐지 — 신원은 로그인 게이트(index.html)가 acl에서 주입.
    // 여기 도달 = 게이트 우회/세션 이상 → 게이트로 복귀.
    location.reload();
    return;
  }
  if(dbUrl&&dbPath){
    checkSchemaVersion(); // 스키마 게이트(#15) — 비차단 호출, 초과 시 화면 차단
    // classes는 최상위 classes/ 노드가 정본 (config/classes 아님)
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
          Object.values(classStudents).forEach(sortStu);
          config._classStudents=classStudents;
        }
        saveLocal();setSync(true);
      if(inpD)Object.assign(inputData,inpD);
      // 진도/과제(반 공통)는 Firebase 정본 우선 — 다기기(태블릿 입력→PC 발송) staleness 방지.
      // 메모·발송문·태그도 이미 Firebase 우선이라 일관. 오프라인 미반영 로컬값은 재입력 쉬움(반 공통).
      if(sessD?.class_data)Object.assign(progressData,sessD.class_data);
      if(obsD)Object.assign(tagData,obsD);
      if(scD&&typeof scD==='object')scoreData=scD;
      if(inpD||sessD||obsD)saveLocal();
      // 로그인 주입은 assignments=[] 이므로 config/instructors에서 하이드레이트
      // (없으면 _syncAssignments가 빈 채로 두어 리프레쉬 시 담당 수업 소실)
      const _rec=instructor&&config.instructors&&config.instructors[instructor.id];
      if(_rec){
        if((!instructor.assignments||!instructor.assignments.length)&&Array.isArray(_rec.assignments))instructor.assignments=_rec.assignments;
        if((!instructor.presets||!instructor.presets.length)&&Array.isArray(_rec.presets))instructor.presets=_rec.presets;
        if((!instructor.bulkTemplates||!instructor.bulkTemplates.length)&&Array.isArray(_rec.bulkTemplates))instructor.bulkTemplates=_rec.bulkTemplates;
        if(_rec.ai_style_mode&&!instructor.ai_style_mode)instructor.ai_style_mode=_rec.ai_style_mode;
        if(_rec.ai_custom_prompt!=null&&instructor.ai_custom_prompt==null)instructor.ai_custom_prompt=_rec.ai_custom_prompt;
        saveLocal();
      }
      _syncAssignments();
      renderMain();renderSb();
    }).catch(()=>{setSync(false);renderMain();});
  }
  renderMain();
}
init();
