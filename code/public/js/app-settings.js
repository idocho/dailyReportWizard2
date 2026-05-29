
// ══════════════════════════════════════════════════════════
//  설정
// ══════════════════════════════════════════════════════════
function _saToggle(id){
  const hdr=document.querySelector(`#${id}>.sa-hdr`);
  const body=document.querySelector(`#${id}>.sa-body`);
  if(!hdr||!body)return;
  const open=body.classList.toggle('open');
  hdr.classList.toggle('open',open);
  if(open)openSaIds.add(id);else openSaIds.delete(id);
}
function _saOpen(id){
  const hdr=document.querySelector(`#${id}>.sa-hdr`);
  const body=document.querySelector(`#${id}>.sa-body`);
  if(!hdr||!body)return;
  hdr.classList.add('open');body.classList.add('open');
  openSaIds.add(id);
}

function renderSettings(mc){
  renderMhdr('설정');
  if(config)_ensureConfigShape();
  const instr=instructor||{};

  // ── 내 계정 상태 요약 ──
  const acctSub=instr.name?`<span class="sa-sub">${esc(instr.name)}</span>`:`<span class="sa-sub" style="color:var(--red)">미설정</span>`;

  // ── 담당 수업 rows ──
  const asgns=instr.assignments||[];
  const asgRows=!asgns.length
    ?`<div style="padding:10px 12px;font-size:12px;color:var(--gray)">담당 수업이 없습니다.</div>`
    :`<div class="ar" style="grid-template-columns:1fr 1fr 52px 30px;background:#F8FAFC;font-size:10px;font-weight:700;color:var(--sub)"><span>반</span><span>과목</span><span>역할</span><span></span></div>`
      +asgns.map((a,i)=>`<div class="ar" style="grid-template-columns:1fr 1fr 52px 30px"><span style="font-weight:700">${esc(a.classId)}</span><span style="color:var(--sub);font-size:11px">${esc(a.subject)}</span><span style="font-size:10px;color:var(--indigo)">${esc(a.role||'담임')}</span><button style="background:none;border:none;cursor:pointer;color:var(--red);font-size:14px;padding:0" onclick="removeA(${i})">✕</button></div>`).join('');
  let addAsgn='';
  if(config){
    // 신규: classes/ 에서 반 목록 구성
    let clsOpts='<option value="">-- 반 선택 --</option>';
    let firstCls='';
    for(const[classId,clsD] of Object.entries(config.classes||{})){
      if(!firstCls)firstCls=classId;
      clsOpts+=`<option value="${esc(classId)}">${esc(classId)}</option>`;
    }
    // subjects: 선택된 반의 courses 키 목록
    const subjectOpts=firstCls
      ?('<option value="">-- 과목 선택 --</option>'+Object.keys((config.classes?.[firstCls]?.courses)||{}).sort((a,b)=>a.localeCompare(b,'ko')).map(s=>`<option>${esc(s)}</option>`).join(''))
      :'';
    addAsgn=`<div style="padding:10px 12px;border-top:1px solid var(--border)"><div style="font-size:11px;font-weight:700;color:var(--sub);margin-bottom:8px">수업 추가</div><div style="display:grid;grid-template-columns:1fr 1fr 72px;gap:6px;margin-bottom:8px"><div><div class="sl">반</div><select class="inp sm" id="aCls" onchange="onCC()">${clsOpts}</select></div><div><div class="sl">과목</div><select class="inp sm" id="aTb">${subjectOpts}</select></div><div><div class="sl">역할</div><select class="inp sm" id="aRole"><option>담임</option><option>부담임</option></select></div></div><button class="btn bsm" onclick="addA()">+ 추가</button></div>`;
  }else{addAsgn=`<div style="padding:10px 12px;font-size:11px;color:var(--gray)">학생 명단을 먼저 불러오세요.</div>`;}

  // ── 자주 쓰는 문구 ──
  const myPresets=instr.presets||[];
  const presetChips=myPresets.map((p,i)=>`
    <div id="preset-row-${i}" style="display:flex;align-items:center;justify-content:space-between;padding:6px 10px;border-bottom:1px solid var(--border)">
      <span style="font-size:12px;flex:1;min-width:0;margin-right:6px" id="preset-txt-${i}">${esc(p)}</span>
      <div style="display:flex;gap:4px;flex-shrink:0" id="preset-btns-${i}">
        <button style="background:none;border:none;cursor:pointer;color:var(--indigo);font-size:12px;padding:2px 4px;border-radius:4px;line-height:1" onclick="editPreset(${i})" title="수정">✏️</button>
        <button style="background:none;border:none;cursor:pointer;color:var(--red);font-size:13px;padding:0 2px;line-height:1" onclick="rmPreset(${i})">✕</button>
      </div>
    </div>`).join('');

  // ── 초기화 UI (다중 선택형) ──
  const resetHtml=_renderResetHtml();

  // ── 관리자: 과목 목록 관리 ──
  const tbMgmtHtml = adminOn ? (()=>{
    // 신규: 모든 classes의 courses를 수집
    const subjectSet=new Set();
    for(const clsD of Object.values(config?.classes||{})){
      for(const s of Object.keys(clsD.courses||{}))subjectSet.add(s);
    }
    const subjectNames=[...subjectSet].sort((a,b)=>a.localeCompare(b,'ko'));
    const tbRows = subjectNames.map(name=>`<div style="display:flex;align-items:center;padding:6px 12px;border-bottom:1px solid var(--border);gap:8px">
        <span style="flex:1;font-size:12px;font-weight:600">${esc(name)}</span>
      </div>`).join('')||'<div style="padding:8px 12px;font-size:11px;color:var(--gray)">등록된 과목 없음</div>';
    return `<div class="sa admin-sec" id="sa-tbmgmt">
      <div class="sa-hdr${openSaIds.has('sa-tbmgmt')?' open':''}" onclick="_saToggle('sa-tbmgmt')">
        <span class="sa-ico">📖</span>
        <span class="sa-lbl">과목 목록</span>
        <span style="font-size:10px;background:#FEF3C7;color:#92400E;border-radius:8px;padding:1px 6px;font-weight:700;margin-right:4px">관리자</span>
        <span class="sa-chv">›</span>
      </div>
      <div class="sa-body${openSaIds.has('sa-tbmgmt')?' open':''}">
        ${tbRows}
      </div>
    </div>`;
  })() : '';

  // ── 강사 관리 (관리자 전용) ──
  const instrMgmt=adminOn?`
    <div class="sa admin-sec" id="sa-admin">
      <div class="sa-hdr${openSaIds.has('sa-admin')?' open':''}" onclick="_saToggle('sa-admin')">
        <span class="sa-ico">👑</span>
        <span class="sa-lbl">강사 관리</span>
        <span style="font-size:10px;background:#FEF3C7;color:#92400E;border-radius:8px;padding:1px 6px;font-weight:700;margin-right:4px">관리자</span>
        <span class="sa-chv">›</span>
      </div>
      <div class="sa-body${openSaIds.has('sa-admin')?' open':''}" id="instrMgmtCard"><div style="padding:10px 12px;font-size:12px;color:var(--gray)">불러오는 중...</div></div>
    </div>`:'';

  mc.innerHTML=makeTb('설정')+`<div style="padding:14px;display:flex;flex-direction:column;gap:10px">

    <div class="sa" id="sa-fb">
      <div class="sa-hdr${openSaIds.has('sa-fb')?' open':''}" onclick="_saToggle('sa-fb')">
        <span class="sa-ico">🔥</span>
        <span class="sa-lbl">Firebase 연결</span>
        <span class="sa-sub">${dbUrl?'연결됨 ✓':'미설정'}</span>
        <span class="sa-chv">›</span>
      </div>
      <div class="sa-body${openSaIds.has('sa-fb')?' open':''}">
        <div class="sr"><div class="sl">DB URL</div><input class="inp" id="sUrl" value="${esc(dbUrl)}" placeholder="https://your-project.firebaseio.com" type="url" onkeydown="if(event.key==='Enter')saveFb()"></div>
        <div class="sr"><div class="sl">경로 (Secret Path)</div><input class="inp" id="sPth" value="${esc(dbPath)}" placeholder="drw_a7f3k9x2" onkeydown="if(event.key==='Enter')saveFb()"></div>
        <div style="padding:10px 14px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn bp bsm" onclick="saveFb()">💾 저장</button><button class="btn bsm" onclick="loadCfg()">📥 학생 명단 불러오기</button></div>
        <div style="padding:0 14px 10px;font-size:10px;color:var(--sub)">💡 다른 기기에서 입력한 데이터는 위 버튼으로 수동 갱신하세요.</div>
      </div>
    </div>

    <div class="sa" id="sa-acct">
      <div class="sa-hdr${openSaIds.has('sa-acct')?' open':''}" onclick="_saToggle('sa-acct')">
        <span class="sa-ico">🔑</span>
        <span class="sa-lbl">내 계정</span>
        ${acctSub}
        <span class="sa-chv">›</span>
      </div>
      <div class="sa-body${openSaIds.has('sa-acct')?' open':''}">
        ${instr.name
          ? `<div style="display:flex;align-items:center;gap:8px;padding:10px 14px;border-bottom:1px solid var(--border)">
               <div class="avatar" style="width:32px;height:32px;font-size:11px">${esc(instr.name.slice(0,3))}</div>
               <div style="flex:1"><div style="font-size:13px;font-weight:700">${esc(instr.name)}</div><div style="font-size:11px;color:var(--sub)">${(instr.assignments||[]).length}개 수업</div></div>
               <span style="font-size:11px;color:var(--green);font-weight:700">✓ 로그인됨</span>
             </div>`
          : ''}
        <div class="sr"><div class="sl">${instr.name ? '다른 계정으로 전환' : '강사 이름으로 조회'}</div>
          <div style="display:flex;gap:8px">
            <input class="inp" id="acctName" value="" placeholder="이름을 입력하세요" style="flex:1" onkeydown="if(event.key==='Enter')lookupInstr()">
            <button class="btn bp bsm" onclick="lookupInstr()" style="flex-shrink:0">조회</button>
          </div>
        </div>
        <div style="padding:4px 14px 10px;font-size:11px;color:var(--sub)">이름 그대로 Firebase 키로 사용됩니다 (예: <code>config/instructors/홍길동</code>)</div>
      </div>
    </div>

    <div class="sa" id="sa-preset">
      <div class="sa-hdr${openSaIds.has('sa-preset')?' open':''}" onclick="_saToggle('sa-preset')">
        <span class="sa-ico">🎯</span>
        <span class="sa-lbl">자주 쓰는 문구</span>
        <span class="sa-sub">${myPresets.length}개</span>
        <span class="sa-chv">›</span>
      </div>
      <div class="sa-body${openSaIds.has('sa-preset')?' open':''}">
        ${presetChips||'<div style="padding:10px 12px;font-size:12px;color:var(--gray)">등록된 문구가 없습니다.</div>'}
        <div style="padding:8px 10px;border-top:1px solid var(--border);display:flex;gap:6px">
          <input class="inp sm" id="pInput" placeholder="새 문구 입력" style="flex:1" onkeydown="if(event.key==='Enter')addPreset()">
          <button class="btn bsm" onclick="addPreset()">+ 추가</button>
        </div>
      </div>
    </div>

    <div class="sa" id="sa-asgn">
      <div class="sa-hdr${openSaIds.has('sa-asgn')?' open':''}" onclick="_saToggle('sa-asgn')">
        <span class="sa-ico">📚</span>
        <span class="sa-lbl">내 담당 수업</span>
        <span class="sa-sub">${asgns.length}개</span>
        <span class="sa-chv">›</span>
      </div>
      <div class="sa-body${openSaIds.has('sa-asgn')?' open':''}">${asgRows}${addAsgn}</div>
    </div>

    <div class="sa" id="sa-cls">
      <div class="sa-hdr${openSaIds.has('sa-cls')?' open':''}" onclick="_saToggle('sa-cls')">
        <span class="sa-ico">🏫</span>
        <span class="sa-lbl">학급 &amp; 학생 관리</span>
        <span class="sa-sub">${config?Object.keys(config.classes||{}).length+'개 학급':'–'}</span>
        <span class="sa-chv">›</span>
      </div>
      <div class="sa-body${openSaIds.has('sa-cls')?' open':''}">${renderClsMgmt()}</div>
    </div>

    <div class="sa" id="sa-reset">
      <div class="sa-hdr${openSaIds.has('sa-reset')?' open':''}" onclick="_saToggle('sa-reset')">
        <span class="sa-ico">🗑</span>
        <span class="sa-lbl" style="color:var(--red)">초기화</span>
        <span class="sa-sub"></span>
        <span class="sa-chv">›</span>
      </div>
      <div class="sa-body${openSaIds.has('sa-reset')?' open':''}">${resetHtml}</div>
    </div>

    ${tbMgmtHtml}

    ${instrMgmt}

    <button class="adm-btn${adminOn?' on':''}" onclick="toggleAdmin()" id="admBtn">
      <span>${adminOn?'🔓':'🔒'}</span>
      <span id="admBtnLbl">${adminOn?'관리자 모드 해제':'관리자 모드'}</span>
    </button>

    <div style="font-size:10px;color:var(--gray);text-align:center">`+`DailyReportWizard ${APP_VERSION} · Crafted by IDO(idocho@kakao.com) · Powered by Claude AI`+`</div>
  </div>`;

  setSync(!!dbUrl&&!!dbPath);
  if(adminOn)loadInstrsSection();
  if(!instr.name)_saOpen('sa-acct');
}

// ══════════════════════════════════════════════════════════
//  학급 관리 — 신규: classes/ 구조
// ══════════════════════════════════════════════════════════
function renderClsMgmt(){
  if(clsDrillSh===null)return renderClsMgmtTop();
  return renderClsMgmtClass(clsDrillSh);
}

function renderClsMgmtTop(){
  if(!config)return `<div class="card"><div class="sh">🏫 학급 &amp; 학생 관리</div><div style="padding:10px 12px;font-size:12px;color:var(--gray)">학생 명단을 먼저 불러오세요.</div></div>`;
  _ensureConfigShape();

  // 내 담당 학급
  const myClsSet=new Set((instructor?.assignments||[]).map(a=>a.classId));
  let myRows='';
  for(const[classId,clsD] of Object.entries(config.classes||{})){
    if(myClsSet.has(classId)){
      const myRole=(instructor?.assignments||[]).find(a=>a.classId===classId)?.role||'담임';
      myRows+=buildClsAccordion(classId,clsD,myRole);
    }
  }

  // 전체 학급 드릴다운
  const classIds=Object.keys(config.classes||{});
  const drillBtns=classIds.map(classId=>{
    const clsD=config.classes[classId];
    const subjectCount=Object.keys(clsD.courses||{}).length;
    const studentCount=((config._classStudents||{})[classId]||[]).length;
    return `<div class="drill-btn" onclick="clsDrillSh='${esc(classId)}';openSaIds.add('sa-cls');renderMain()">
      <div style="width:32px;height:32px;border-radius:8px;background:var(--indigo-l);display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0">📂</div>
      <div style="flex:1"><div style="font-size:13px;font-weight:700">${esc(classId)}</div><div style="font-size:11px;color:var(--gray)">학생 ${studentCount}명 · 과목 ${subjectCount}개</div></div>
      <span style="color:var(--gray);font-size:14px;font-weight:300">›</span>
    </div>`;
  }).join('');

  return `<div class="card">
    <div class="sh">🏫 학급 &amp; 학생 관리</div>
    <div class="sh2">내 담당 학급</div>
    ${myRows||'<div style="padding:8px 12px;font-size:11px;color:var(--gray)">담당 수업을 추가하면 여기에 표시됩니다.</div>'}
    <div class="sh2">전체 학급 탐색</div>
    ${drillBtns||'<div style="padding:8px 12px;font-size:11px;color:var(--gray)">등록된 학급이 없습니다.</div>'}
  </div>`;
}

function renderClsMgmtClass(classId){
  if(!config)return '';
  _ensureConfigShape();
  const clsD=config.classes?.[classId]||{courses:{}};
  const myRole=(instructor?.assignments||[]).find(a=>a.classId===classId)?.role||null;
  return `<div class="card">
    <div class="sh" style="display:flex;align-items:center;gap:8px;padding:7px 10px 7px 14px">
      <button class="btn bsm" onclick="clsDrillSh=null;renderMain()" style="flex-shrink:0;font-size:11px">← 뒤로</button>
      <span style="flex:1">🏫 ${esc(classId)} 학급 관리</span>
    </div>
    ${buildClsAccordion(classId,clsD,myRole)}
  </div>`;
}

function buildClsAccordion(classId,clsD,myRole){
  const students=(config?._classStudents||{})[classId]||[];
  const courses=clsD.courses||{};
  const subjects=Object.keys(courses);
  const isSub=myRole==='부담임';
  const subBadge=isSub?`<span style="font-size:9px;background:#FEF3C7;color:#92400E;border-radius:8px;padding:1px 6px;font-weight:700;flex-shrink:0">부담임</span>`:'';
  const stuChips=students.map(s=>`<span class="chip" onclick="rmStu('${esc(classId)}','${esc(s.nameKey)}')">${esc(s.name||s.nameKey)} <span>×</span></span>`).join('');
  const courseChips=subjects.map(subj=>{
    const course=courses[subj]||{};
    const tb=course.textbook||'';
    // 교재명이 있으면 "교재명 (과목)", 없으면 "과목"만 표시
    const mainLabel=tb||subj;
    const subLabel=tb?`<span style="color:var(--indigo);font-size:9px;font-weight:700;margin-right:3px">${esc(subj)}</span>`:'';
    return`<span class="chip" onclick="rmCourse('${esc(classId)}','${esc(subj)}')">${subLabel}${esc(mainLabel)} <span style="display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px;margin-left:4px;border-radius:50%;background:#FEE2E2;color:#B91C1C;font-size:10px;font-weight:700;line-height:1">×</span></span>`;}).join('');
  return `<div style="border-bottom:1px solid var(--border)">
    <div class="acc-hdr" onclick="toggleAcc(this)">
      <span class="acc-arr" style="font-size:10px;color:var(--gray);width:14px;flex-shrink:0">▶</span>
      <span style="font-size:13px;font-weight:700;flex:1">${esc(classId)}</span>
      ${subBadge}
      <span style="font-size:10px;color:var(--gray);margin:0 6px;white-space:nowrap">학생 ${students.length} · 과목 ${subjects.length}</span>
      <button class="btn br bsm" onclick="rmCls('${esc(classId)}');event.stopPropagation()" style="padding:2px 7px;font-size:11px;flex-shrink:0">✕</button>
    </div>
    <div class="acc-body">
      <div class="sl">학생</div>
      <div class="chips" data-classid="${esc(classId)}" data-chip-type="stu">${stuChips}<span class="chip" style="background:var(--indigo-l);border-color:var(--indigo);color:var(--indigo);cursor:pointer" onclick="addStuInline('${esc(classId)}',this)">+ 추가</span></div>
      <div class="sl" style="margin-top:10px">과목</div>
      <div class="chips" data-classid="${esc(classId)}" data-chip-type="course">${courseChips}<span class="chip" style="background:var(--indigo-l);border-color:var(--indigo);color:var(--indigo);cursor:pointer" onclick="addCourseInline('${esc(classId)}',this)">+ 과목 추가</span></div>
    </div>
  </div>`;
}

// ── 학생 인라인 추가 ─────────────────────────────────────────────
function addStuInline(classId,btnEl){
  const chips=btnEl.parentElement;
  if(chips.querySelector('.stu-new-inp')){chips.querySelector('.stu-new-inp').focus();return;}

  const wrapper=document.createElement('span');
  wrapper.style.cssText='display:inline-flex;align-items:center;border:1px solid var(--indigo);border-radius:12px;padding:2px 6px;background:var(--indigo-l);gap:2px;vertical-align:middle;';
  const inp=document.createElement('input');
  inp.className='stu-new-inp';
  inp.style.cssText='border:none;background:transparent;font-size:11px;width:64px;color:var(--text);font-family:inherit;outline:none;';
  inp.placeholder='이름';
  const ok=document.createElement('span');
  ok.textContent='✓';ok.title='추가';
  ok.style.cssText='cursor:pointer;color:var(--indigo);font-weight:700;font-size:13px;line-height:1;padding:0 2px;';
  const cancel=document.createElement('span');
  cancel.textContent='×';
  cancel.style.cssText='cursor:pointer;color:var(--gray);font-size:13px;line-height:1;';
  cancel.onclick=()=>wrapper.remove();

  async function doAdd(){
    const n=inp.value.trim();
    if(!n){wrapper.remove();return;}
    // 신규: students/{nameKey} = {name, class: classId}
    // nameKey = 이름 (동명이인은 이름+숫자)
    let nameKey=n;
    // 중복 체크: config._classStudents 전체에서 nameKey 확인
    const allStudents=config._classStudents||{};
    const allKeys=Object.values(allStudents).flat().map(s=>s.nameKey);
    if(allKeys.includes(nameKey)){
      let i=0;
      while(allKeys.includes(nameKey+i))i++;
      nameKey=nameKey+i;
    }
    if(!config._classStudents)config._classStudents={};
    if(!config._classStudents[classId])config._classStudents[classId]=[];
    config._classStudents[classId].push({nameKey,name:n,class:classId});
    wrapper.remove();
    refreshStuChips(classId);
    // Firebase 저장: students/{nameKey}
    if(dbUrl&&dbPath){
      try{await fbPatch(`students/${nameKey}`,{name:n,class:classId});toast(`${n} 추가됨 ✅`);}catch(e){toast('저장 실패: '+e);}
    }
  }
  ok.onclick=doAdd;
  inp.addEventListener('keydown',e=>{
    if(e.key==='Enter'){e.preventDefault();doAdd();}
    if(e.key==='Escape')wrapper.remove();
  });
  wrapper.appendChild(inp);wrapper.appendChild(ok);wrapper.appendChild(cancel);
  chips.insertBefore(wrapper,btnEl);
  inp.focus();
}

function refreshStuChips(classId){
  const sCls=classId.replace(/\\/g,'\\\\').replace(/"/g,'\\"');
  const el=document.querySelector(`[data-chip-type="stu"][data-classid="${sCls}"]`);
  if(!el)return;
  const students=(config?._classStudents||{})[classId]||[];
  const stuChips=students.map(s=>`<span class="chip" onclick="rmStu('${esc(classId)}','${esc(s.nameKey)}')">${esc(s.name||s.nameKey)} <span>×</span></span>`).join('');
  el.innerHTML=stuChips+`<span class="chip" style="background:var(--indigo-l);border-color:var(--indigo);color:var(--indigo);cursor:pointer" onclick="addStuInline('${esc(classId)}',this)">+ 추가</span>`;
}

// ── 과목 인라인 추가 ─────────────────────────────────────────────
function addCourseInline(classId,btnEl){
  const chips=btnEl.parentElement;
  if(chips.querySelector('.course-inline-wrap')){return;}

  const wrapper=document.createElement('div');
  wrapper.className='course-inline-wrap';
  wrapper.style.cssText='display:flex;align-items:center;gap:4px;flex-wrap:wrap;margin-top:5px;padding:6px 8px;background:var(--indigo-l);border:1px solid var(--indigo);border-radius:8px;';

  // 커리큘럼 드롭다운
  const gsSel=document.createElement('select');
  gsSel.style.cssText='font-size:11px;padding:3px 5px;border:1px solid var(--indigo);border-radius:5px;font-family:inherit;background:#fff;';
  gsSel.innerHTML='<option value="">과정 선택</option>'+
    GRADE_SEM_LIST.map(g=>`<option value="${esc(g.val)}">${esc(g.label)}</option>`).join('');

  // 교재명 — 기존 교재 목록에서 선택하거나 직접 입력 (subject key로 사용)
  const tbDlId='tb-dl-'+classId.replace(/[^a-z0-9]/gi,'_');
  const tbDl=document.createElement('datalist');
  tbDl.id=tbDlId;
  const existingTbs=new Set();
  for(const clsD of Object.values(config?.classes||{}))
    for(const c of Object.values(clsD.courses||{}))
      if(c.textbook)existingTbs.add(c.textbook);
  existingTbs.forEach(t=>{const o=document.createElement('option');o.value=t;tbDl.appendChild(o);});
  wrapper.appendChild(tbDl);

  const tbInp=document.createElement('input');
  tbInp.placeholder=existingTbs.size?'교재 선택 또는 직접 입력':'교재명';
  tbInp.setAttribute('list',tbDlId);
  tbInp.style.cssText='font-size:11px;padding:3px 5px;border:1px solid var(--border);border-radius:5px;font-family:inherit;min-width:110px;';

  const ok=document.createElement('span');
  ok.textContent='✓';
  ok.style.cssText='cursor:pointer;color:var(--indigo);font-weight:700;font-size:14px;padding:0 2px;';
  const cancel=document.createElement('span');
  cancel.textContent='×';
  cancel.style.cssText='cursor:pointer;color:var(--gray);font-size:14px;padding:0 2px;';
  cancel.onclick=()=>wrapper.remove();

  async function doAdd(){
    const curriculum=gsSel.value;
    const textbook=tbInp.value.trim();
    if(!curriculum){toast('과정을 선택해 주세요.');return;}
    if(!textbook){toast('교재명을 입력해 주세요.');return;}
    // subject key = 교재명 (동일 과정도 교재가 다르면 별도 과목으로 추가 가능)
    const subject=textbook;
    const existingCourses=config?.classes?.[classId]?.courses||{};
    if(existingCourses[subject]){toast('이미 추가된 교재입니다.');return;}
    if(!config.classes)config.classes={};
    if(!config.classes[classId])config.classes[classId]={group:'',courses:{}};
    if(!config.classes[classId].courses)config.classes[classId].courses={};
    const courseData={textbook,curriculum};
    config.classes[classId].courses[subject]=courseData;
    wrapper.remove();
    try{refreshCourseChips(classId);}catch(e){renderMain();}
    if(dbUrl&&dbPath){
      try{
        await fbPatch(`classes/${classId}/courses/${subject}`,courseData);
        if(instructor?.id){
          const already=(instructor.assignments||[]).some(a=>a.classId===classId&&a.subject===subject);
          if(!already){
            instructor.assignments=[...(instructor.assignments||[]),{classId,subject,role:'담임'}];
            saveLocal();
            fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{assignments:instructor.assignments}).catch(()=>{});
          }
        }
        toast('과목 추가됨 ✅');
      }catch(e){toast('저장 실패: '+e);}
    }
  }
  ok.onclick=doAdd;
  [gsSel,tbInp].forEach(el=>{el.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();ok.click();}});});

  wrapper.appendChild(gsSel);wrapper.appendChild(tbInp);wrapper.appendChild(ok);wrapper.appendChild(cancel);
  chips.parentElement.appendChild(wrapper);
  gsSel.focus();
}

function refreshCourseChips(classId){
  const sCls=classId.replace(/\\/g,'\\\\').replace(/"/g,'\\"');
  const el=document.querySelector(`[data-chip-type="course"][data-classid="${sCls}"]`);
  if(!el)return;
  const courses=config?.classes?.[classId]?.courses||{};
  const courseChips=Object.keys(courses).map(subj=>{
    const course=courses[subj]||{};
    const tb=course.textbook||'';
    const mainLabel=tb||subj;
    const subLabel=tb?`<span style="color:var(--indigo);font-size:9px;font-weight:700;margin-right:3px">${esc(subj)}</span>`:'';
    return`<span class="chip" onclick="rmCourse('${esc(classId)}','${esc(subj)}')">${subLabel}${esc(mainLabel)} <span style="display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px;margin-left:4px;border-radius:50%;background:#FEE2E2;color:#B91C1C;font-size:10px;font-weight:700;line-height:1">×</span></span>`;
  }).join('');
  el.innerHTML=courseChips+`<span class="chip" style="background:var(--indigo-l);border-color:var(--indigo);color:var(--indigo);cursor:pointer" onclick="addCourseInline('${esc(classId)}',this)">+ 과목 추가</span>`;
}

// ── 프리셋 편집 (인플레이스) ──────────────────────────────────────
function editPreset(i){
  const txt=document.getElementById(`preset-txt-${i}`);
  const btns=document.getElementById(`preset-btns-${i}`);
  if(!txt||txt.querySelector('input'))return;
  const cur=instructor?.presets?.[i]||'';
  if(btns)btns.style.display='none';
  txt.innerHTML=`<div style="display:flex;gap:4px;width:100%;align-items:center">
    <input id="preset-edit-${i}" class="inp sm" value="${esc(cur)}" style="flex:1;min-width:0"
      onkeydown="if(event.key==='Enter'){event.preventDefault();savePreset(${i});}if(event.key==='Escape')renderMain();">
    <button class="btn bp bsm" style="flex-shrink:0" onclick="savePreset(${i})">✓</button>
    <button class="btn bsm" style="flex-shrink:0" onclick="renderMain()">✕</button>
  </div>`;
  document.getElementById(`preset-edit-${i}`)?.focus();
}
function savePreset(i){
  const val=document.getElementById(`preset-edit-${i}`)?.value.trim()||'';
  if(!val){renderMain();return;}
  if(!instructor?.presets)return;
  instructor.presets[i]=val;
  saveLocal();
  if(dbUrl&&dbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{presets:instructor.presets}).catch(()=>{});
  toast('문구 수정됨 ✅');
  renderMain();
}

// ══════════════════════════════════════════════════════════
//  설정 저장 / 강사 / 학급 관리
// ══════════════════════════════════════════════════════════
function saveFb(){
  dbUrl=document.getElementById('sUrl')?.value.trim()||'';
  dbPath=document.getElementById('sPth')?.value.trim()||'';
  SS('drw_db_url',dbUrl);SS('drw_db_path',dbPath);
  saveLocal();toast('Firebase 설정 저장됨 ✅');
}

async function lookupInstr(){
  const name=(document.getElementById('acctName')?.value||'').trim();
  if(!name){toast('이름을 입력해 주세요.');return;}
  if(!dbUrl||!dbPath){toast('Firebase 연결 정보를 먼저 저장하세요.');return;}
  try{
    const d=await fbGet(`config/instructors/${encodeURIComponent(name)}`);
    if(d&&d.name){
      instructor={id:name,...d};saveLocal();curAI=0;renderSb();renderMain();
      toast(`${name} 계정으로 로그인됨 ✅`);
    } else {
      if(confirm(`"${name}" 계정이 없습니다.\n신규 등록하시겠습니까?`)){
        await _registerInstr(name);
      }
    }
  }catch(e){toast('조회 실패: '+e);}
}
const _HARDCODED_PRESETS=[
  '채점 미실시','오답 풀이 안함',
  '교재 미지참','과제 이행 의지 없어 보임',
  '교재 검사 불가','교재 검사 거부','결석',
];
function _defaultPresets(){
  const saved=config?.presets?.['과제수행도'];
  return (saved&&saved.length>0)?saved:_HARDCODED_PRESETS;
}
async function _registerInstr(name){
  const defPresets=_defaultPresets();
  instructor={id:name,name,assignments:[],presets:defPresets};saveLocal();
  if(dbUrl&&dbPath)await fbPatch(`config/instructors/${encodeURIComponent(name)}`,{name,assignments:[],presets:defPresets}).catch(()=>{});
  renderSb();renderMain();toast(`${name} 등록됨 ✅ — 담당 수업·자주 쓰는 문구를 설정해 주세요`);
}

async function hashPw(pw){
  const buf=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(pw));
  return Array.from(new Uint8Array(buf)).map(b=>b.toString(16).padStart(2,'0')).join('');
}
async function toggleAdmin(){
  if(adminOn){adminOn=false;renderMain();return;}
  const pw=prompt('관리자 암호를 입력하세요');
  if(pw===null)return;
  const h=await hashPw(pw);
  if(h===ADMIN_HASH){adminOn=true;toast('관리자 모드 활성화 🔓');renderMain();}
  else toast('암호가 올바르지 않습니다.');
}

function onCC(){
  // 신규: 반 선택 시 해당 반의 courses 키 목록을 과목 셀렉트에 채움
  const s=document.getElementById('aCls');if(!s||!config)return;
  const classId=s.value;
  const subjects=Object.keys(config?.classes?.[classId]?.courses||{}).sort((a,b)=>a.localeCompare(b,'ko'));
  const t=document.getElementById('aTb');
  if(t)t.innerHTML='<option value="">-- 과목 선택 --</option>'+subjects.map(x=>`<option>${esc(x)}</option>`).join('');
}
function addA(){
  if(!instructor){toast('먼저 계정을 설정해 주세요.');return;}
  const cs=document.getElementById('aCls'),ts=document.getElementById('aTb'),rs=document.getElementById('aRole');
  if(!cs||!ts)return;
  const classId=cs.value;
  if(!classId){toast('반을 선택해 주세요.');return;}
  const subject=ts.value,role=rs?.value||'담임';
  if(!subject){toast('과목을 선택해 주세요.');return;}
  // group: classes/{classId}/group
  const group=config?.classes?.[classId]?.group||'';
  if(!instructor.assignments)instructor.assignments=[];
  if(instructor.assignments.some(a=>a.classId===classId&&a.subject===subject)){toast('이미 추가된 수업입니다.');return;}
  instructor.assignments.push({classId,subject,group,role});saveLocal();
  if(dbUrl&&dbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{assignments:instructor.assignments}).catch(()=>{});
  toast('담당 수업 추가됨 ✅');openSaIds.add('sa-asgn');renderMain();
}
function removeA(i){
  if(!instructor?.assignments)return;if(!confirm('이 담당 수업을 제거합니까?'))return;
  instructor.assignments.splice(i,1);if(curAI>=instructor.assignments.length)curAI=0;saveLocal();
  if(dbUrl&&dbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{assignments:instructor.assignments}).catch(()=>{});
  renderMain();renderSb();
}

function _ensureConfigShape(){
  if(!config)config={classes:{},instructors:{}};
  if(!config.classes)config.classes={};
  if(!config.instructors)config.instructors={};
  return config;
}

async function pushCfg(){
  _ensureConfigShape();
  saveLocal();
  if(!dbUrl||!dbPath)return;
  try{
    await fbPut('classes',config.classes||{});
    setSync(true);toast('저장됨 ✅');
  }catch(e){setSync(false);toast('저장 실패: '+e);}
}

function addCls(group){
  const c=prompt(`학급명 (예: 3MGM)`);
  if(!c?.trim())return;
  _ensureConfigShape();
  if(!config.classes[c.trim()])config.classes[c.trim()]={group:group||'',courses:{}};
  clsDrillSh=c.trim();
  openSaIds.add('sa-cls');
  pushCfg();
  renderMain();
}
function addCourse(classId){
  const subject=prompt(`${classId} 과목명 (예: 3-1):`);
  if(!subject?.trim())return;
  _ensureConfigShape();
  if(!config.classes[classId])config.classes[classId]={group:'',courses:{}};
  config.classes[classId].courses[subject.trim()]={textbook:'',curriculum:''};
  openSaIds.add('sa-cls');
  pushCfg();
  renderMain();
}

function _syncAssignments(){
  if(!instructor?.assignments?.length)return;
  const before=instructor.assignments.length;
  instructor.assignments=instructor.assignments.filter(a=>{
    const clsD=config?.classes?.[a.classId];
    if(!clsD)return false;
    return !a.subject||Object.prototype.hasOwnProperty.call(clsD.courses||{},a.subject);
  });
  if(instructor.assignments.length===before)return;
  if(curAI>=instructor.assignments.length)curAI=0;
  saveLocal();
  if(dbUrl&&dbPath&&instructor.id)
    fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{assignments:instructor.assignments}).catch(()=>{});
}

function rmCls(classId){
  if(!confirm(`${classId} 학급을 삭제합니까?`))return;
  delete config.classes[classId];
  if(config._classStudents)delete config._classStudents[classId];
  if(instructor?.assignments){
    const before=instructor.assignments.length;
    instructor.assignments=instructor.assignments.filter(a=>a.classId!==classId);
    if(instructor.assignments.length!==before){
      if(curAI>=instructor.assignments.length)curAI=0;
      saveLocal();
      if(dbUrl&&dbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{assignments:instructor.assignments}).catch(()=>{});
    }
  }
  pushCfg();renderMain();
}

async function rmStu(classId,nameKey){
  const stu=((config?._classStudents||{})[classId]||[]).find(s=>s.nameKey===nameKey);
  const displayName=stu?.name||nameKey;
  if(!confirm(`${displayName}을(를) 삭제합니까?`))return;
  if(config._classStudents?.[classId]){
    config._classStudents[classId]=config._classStudents[classId].filter(s=>s.nameKey!==nameKey);
  }
  refreshStuChips(classId);
  // Firebase: students/{nameKey} 삭제
  if(dbUrl&&dbPath){
    try{await fbPut(`students/${nameKey}`,null);}catch(e){}
  }
}

async function rmCourse(classId,subject){
  if(!confirm(`"${subject}" 과목을 삭제합니까?`))return;
  if(config?.classes?.[classId]?.courses)delete config.classes[classId].courses[subject];
  try{refreshCourseChips(classId);}catch(e){}
  if(dbUrl&&dbPath){
    try{await fbPut(`classes/${classId}/courses/${subject}`,null);}catch(e){}
  }
  _syncAssignments();
  renderMain();
}

async function loadCfg(){
  if(!dbUrl||!dbPath){toast('Firebase URL과 경로를 먼저 저장하세요.');return;}
  const mc=document.getElementById('mc');
  mc.innerHTML=`<div class="loading"><div class="spin"></div>불러오는 중...</div>`;
  try{
    // classes는 최상위 classes/ 노드가 정본 (config/classes 아님)
    const [cfgData,clsData,stuData]=await Promise.all([
      fbGet('config').catch(()=>null),
      fbGet('classes').catch(()=>null),
      fbGet('students').catch(()=>null),
    ]);
    config=cfgData||{classes:{},instructors:{}};
    if(clsData&&typeof clsData==='object')config.classes=clsData;
    _ensureConfigShape();
    // students를 classId별로 캐싱
    if(stuData&&typeof stuData==='object'){
      const classStudents={};
      for(const[nameKey,v] of Object.entries(stuData)){
        const cid=v?.class;
        if(cid){
          if(!classStudents[cid])classStudents[cid]=[];
          classStudents[cid].push({nameKey,...v});
        }
      }
      config._classStudents=classStudents;
    }
    saveLocal();setSync(true);
    try{let s=await fbGet('session').catch(()=>null);if(s?.class_data)for(const[k,v]of Object.entries(s.class_data))if(!progressData[k])progressData[k]=v;saveLocal();}catch(e){}
    try{const d=await fbGet('input');if(d)Object.assign(inputData,d);saveLocal();}catch(e){}
    try{const d=await fbGet('obs');if(d)Object.assign(tagData,d);saveLocal();}catch(e){}
    if(instructor?.id){const id=await fbGet(`config/instructors/${encodeURIComponent(instructor.id)}`).catch(()=>null);if(id){Object.assign(instructor,id);saveLocal();}}
    toast('학생 명단 불러옴 ✅');
    if(!instructor)toast('강사 선택이 필요합니다 — 좌측 상단 강사 뱃지를 클릭하세요',4000);
    renderMain();renderSb();
  }catch(e){setSync(false);toast('연결 실패: '+e);renderMain();}
}

// ── 초기화 scope 헬퍼 ───────────────────────────────────────────────
function _myResetKeys(){
  const asgns=instructor?.assignments||[];
  const inputKeys=[];
  const progressKeys=[];
  const noteKeySeen=new Set();
  for(const a of asgns){
    const students=(config?._classStudents||{})[a.classId]||[];
    for(const s of students){
      inputKeys.push(`${s.nameKey}|${a.subject}`);
      const nk=`${s.nameKey}|__note__`;
      if(!noteKeySeen.has(nk)){noteKeySeen.add(nk);inputKeys.push(nk);}
    }
    progressKeys.push(`${a.classId}|${a.subject}`);
  }
  return{inputKeys,progressKeys};
}

// ── 초기화 UI 렌더 ──────────────────────────────────────────────────
const _RESET_ITEMS=[
  {id:'tags',     icon:'🏷',  label:'수행도 & 관찰 태그',  desc:'오늘 수행도·이해도·컨디션 등 전체', admin:false},
  {id:'input',    icon:'📋', label:'특이사항 메모',        desc:'오늘 작성한 메모만 초기화',      admin:false},
  {id:'progress', icon:'📚', label:'진도 & 과제',          desc:'내 수업 진도·과제 데이터',      admin:false},
  {id:'presets',  icon:'⚙️', label:'자주 쓰는 문구 초기화', desc:'기본 문구 목록으로 복원',      admin:false},
  {id:'all-input',    icon:'🗂',  label:'전체 입력 삭제',   desc:'모든 강사 수행도·태그·노트',    admin:true},
  {id:'all-progress', icon:'📊', label:'전체 진도 삭제',   desc:'모든 강사 진도·과제',           admin:true},
  {id:'assignments',  icon:'👤', label:'강사 배정 초기화', desc:'모든 강사 수업 배정 삭제',      admin:true},
  {id:'config',       icon:'💥', label:'명단 & 설정 삭제', desc:'학생명단·강사·문구 전체',       admin:true},
];
function _renderResetHtml(){
  const hasAdmin=adminOn;
  const normalItems=_RESET_ITEMS.filter(it=>!it.admin);
  const adminItems=_RESET_ITEMS.filter(it=>it.admin);
  const _card=(it)=>{
    const sel=_resetSel.has(it.id);
    const adm=it.admin;
    const borderC=sel?(adm?'#EF4444':'#4338CA'):(adm?'#FCA5A5':'#E2E8F0');
    const bgC=sel?(adm?'#FEE2E2':'#EEF2FF'):(adm?'#FFF5F5':'#fff');
    const labelC=sel?(adm?'#EF4444':'#4338CA'):'#1E293B';
    const checkBg=sel?(adm?'#EF4444':'#4338CA'):'#fff';
    const checkBorder=sel?(adm?'#EF4444':'#4338CA'):'#CBD5E1';
    return `<div onclick="_resetToggle('${it.id}')" style="border:1.5px solid ${borderC};border-radius:12px;padding:11px 10px 9px;cursor:pointer;background:${bgC};position:relative;transition:border-color .15s,background .15s">
      <div style="position:absolute;top:7px;right:7px;width:15px;height:15px;border-radius:50%;border:1.5px solid ${checkBorder};background:${checkBg};display:flex;align-items:center;justify-content:center;font-size:9px;color:${sel?'#fff':'transparent'}">✓</div>
      <div style="font-size:17px;line-height:1;margin-bottom:4px">${it.icon}</div>
      <div style="font-size:12px;font-weight:700;color:${labelC};line-height:1.25;margin-bottom:3px">${it.label}</div>
      <div style="font-size:10px;color:#94A3B8;line-height:1.3">${it.desc}</div>
    </div>`;
  };
  const normalGrid=`<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:12px 12px 4px">${normalItems.map(_card).join('')}</div>`;
  const adminGrid=hasAdmin?`
    <div style="padding:8px 12px 2px;font-size:11px;font-weight:700;color:#EF4444;letter-spacing:.3px">👑 관리자 전용</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:0 12px 4px">${adminItems.map(_card).join('')}</div>`:'';
  const hasAdminSel=[..._resetSel].some(id=>_RESET_ITEMS.find(it=>it.id===id)?.admin);
  const empty=_resetSel.size===0;
  const btnBg=empty?'#E2E8F0':hasAdminSel?'#EF4444':'#4338CA';
  const btnC=empty?'#94A3B8':'#fff';
  const btnLabel=hasAdminSel?'⚠ 초기화 실행 (관리자)':'초기화 실행';
  return `${normalGrid}${adminGrid}
    <div style="padding:10px 12px 14px">
      <button class="btn bp" style="width:100%;background:${btnBg};color:${btnC};border-color:transparent;font-size:13px;font-weight:700;padding:10px;border-radius:10px" ${empty?'disabled':''} onclick="clrSelected()">${btnLabel}</button>
      ${_resetSel.size?`<div style="font-size:11px;color:#94A3B8;margin-top:6px;text-align:center">${_resetSel.size}개 항목 선택됨</div>`:''}
    </div>`;
}
function _resetToggle(id){
  if(_resetSel.has(id))_resetSel.delete(id);else _resetSel.add(id);
  const body=document.querySelector('#sa-reset .sa-body');
  if(body)body.innerHTML=_renderResetHtml();
}
async function _doResetPresets(){
  const def=_defaultPresets();
  if(instructor){instructor.presets=[...def];}
  if(dbUrl&&dbPath&&instructor?.id){
    await fbPatch(`config/instructors/${instructor.id}`,{presets:def}).catch(()=>{});
  }
  saveLocal();
}

async function clrSelected(){
  if(_resetSel.size===0)return;
  const sel=[..._resetSel];
  const hasAdminItem=sel.some(id=>_RESET_ITEMS.find(it=>it.id===id)?.admin);
  const labels=sel.map(id=>_RESET_ITEMS.find(it=>it.id===id)?.label||id).join(', ');

  if(hasAdminItem){
    if(!adminOn){toast('관리자 모드가 필요합니다.');return;}
    if(!confirm(`⚠ 관리자 초기화\n\n선택 항목: ${labels}\n\n진행합니까?`))return;
    if(!confirm('마지막 확인: 이 작업은 되돌릴 수 없습니다. 진행합니까?'))return;
  }else{
    if(!confirm(`다음 항목을 초기화합니까?\n\n${labels}`))return;
  }

  if(!dbUrl||!dbPath){
    if(sel.includes('input')){const{inputKeys}=_myResetKeys();for(const k of inputKeys)delete inputData[k];}
    if(sel.includes('tags')){
      const dk=todayKey();const asgns=instructor?.assignments||[];
      for(const a of asgns){
        const students=(config?._classStudents||{})[a.classId]||[];
        for(const s of students){
          if(tagData?.[s.nameKey]?.[a.subject]?.[dk])delete tagData[s.nameKey][a.subject][dk];
        }
      }
    }
    if(sel.includes('progress')){const{progressKeys}=_myResetKeys();for(const k of progressKeys)delete progressData[k];}
    if(sel.includes('presets'))await _doResetPresets();
    saveLocal();toast('초기화 완료 (로컬)');_resetSel.clear();renderMain();return;
  }

  try{
    const ops=[];
    if(sel.includes('input')){
      const{inputKeys}=_myResetKeys();
      for(const k of inputKeys)delete inputData[k];
      // 신규: input/{nameKey}/{subject} 구조
      const asgns=instructor?.assignments||[];
      for(const a of asgns){
        const students=(config?._classStudents||{})[a.classId]||[];
        for(const s of students){
          ops.push(fbPut(`input/${s.nameKey}/${a.subject}`,null).catch(()=>{}));
        }
      }
    }
    if(sel.includes('tags')){
      const dk=todayKey();const asgns=instructor?.assignments||[];
      for(const a of asgns){
        const students=(config?._classStudents||{})[a.classId]||[];
        for(const s of students){
          if(tagData?.[s.nameKey]?.[a.subject]?.[dk]){
            delete tagData[s.nameKey][a.subject][dk];
            ops.push(fbPatch(`obs/${s.nameKey}/${a.subject}`,{[dk]:null}));
          }
        }
      }
    }
    if(sel.includes('progress')){
      const{progressKeys}=_myResetKeys();
      for(const k of progressKeys)delete progressData[k];
      const p={};for(const k of progressKeys)p[k]=null;
      if(Object.keys(p).length)ops.push(fbPatch('session/class_data',p));
    }
    if(sel.includes('presets'))ops.push(_doResetPresets());
    if(sel.includes('all-input')){inputData={};tagData={};ops.push(fbPut('input',null));ops.push(fbPut('obs',null));}
    if(sel.includes('all-progress')){progressData={};ops.push(fbPut('session',null));}
    if(sel.includes('assignments')){
      const instrs=await fbGet('config/instructors').catch(()=>null);
      if(instrs)for(const id of Object.keys(instrs))ops.push(fbPatch(`config/instructors/${id}`,{assignments:[]}).catch(()=>{}));
    }
    if(sel.includes('config')){
      ops.push(fbPut('config',null));ops.push(fbPut('input',null));ops.push(fbPut('session',null));ops.push(fbPut('students',null));
      inputData={};progressData={};config=null;instructor=null;adminOn=false;
      SS('drw_input','{}');SS('drw_prog','{}');SS('drw_config','');SS('drw_instr','');
    }
    await Promise.all(ops);
    saveLocal();
    _resetSel.clear();
    toast('초기화 완료');
    if(sel.includes('config')){toast('페이지를 새로고침하세요',4000);}else{renderMain();}
  }catch(e){toast('초기화 실패: '+e);}
}

// ══════════════════════════════════════════════════════════
//  강사 모달 / 관리
// ══════════════════════════════════════════════════════════
async function showIM(){
  goNav('setting');
  setTimeout(()=>_saOpen('sa-acct'),50);
}
async function createI(ctx){
  const inputId=ctx==='modal'?'niNameModal':'niNameCard';
  const name=document.getElementById(inputId)?.value.trim()||'';
  if(!name){toast('이름을 입력해 주세요.');return;}
  await _registerInstr(name);
  if(ctx==='modal')closeIM();
}

async function loadInstrsSection(){
  const card=document.getElementById('instrMgmtCard');if(!card)return;
  if(!adminOn){card.innerHTML='<div style="padding:10px 12px;font-size:12px;color:var(--gray)">관리자 모드가 필요합니다.</div>';return;}
  if(!dbUrl||!dbPath){card.innerHTML='<div style="padding:10px 12px;font-size:12px;color:var(--gray)">Firebase 연결 후 사용 가능합니다.</div>';return;}
  let instrs=[];
  try{const d=await fbGet('config/instructors');if(d)instrs=Object.entries(d).map(([id,v])=>({id,...v})).sort((a,b)=>(a.name||'').localeCompare(b.name||'','ko'));}catch(e){}
  const list=instrs.map(ins=>{
    const isCur=instructor?.id===ins.id;
    return `<div style="display:flex;align-items:center;gap:10px;padding:9px 12px;border-bottom:1px solid var(--border)">
      <div class="avatar" style="width:32px;height:32px;font-size:10px;flex-shrink:0">${esc((ins.name||'?').slice(0,3))}</div>
      <div style="flex:1;min-width:0"><div style="font-size:13px;font-weight:700">${esc(ins.name||'?')}</div><div style="font-size:10px;color:var(--sub)">${(ins.assignments||[]).length}개 수업</div></div>
      <div style="display:flex;gap:4px;flex-shrink:0">
        ${isCur?'<span class="badge b-g">현재</span>':`<button class="btn bsm" onclick="switchInstr('${esc(ins.id)}')">전환</button>`}
        <button class="btn bsm" style="color:var(--red)" onclick="rmInstr('${esc(ins.id)}','${esc(ins.name||'')}')">삭제</button>
      </div>
    </div>`;
  }).join('');
  const newForm=`<div style="padding:10px 12px;border-top:1px solid var(--border)">
    <div style="font-size:11px;font-weight:700;color:var(--sub);margin-bottom:8px">신규 강사 등록</div>
    <div style="display:flex;gap:6px"><input class="inp sm" id="niNameCard" placeholder="이름" style="flex:1" onkeydown="if(event.key==='Enter')createI('card')"><button class="btn bp bsm" onclick="createI('card')">등록</button></div>
  </div>`;
  card.innerHTML=`${list||'<div style="padding:10px 12px;font-size:12px;color:var(--gray)">등록된 강사가 없습니다.</div>'}${newForm}`;
}
async function switchInstr(id){
  if(!dbUrl||!dbPath){toast('Firebase 연결이 필요합니다.');return;}
  try{const d=await fbGet(`config/instructors/${encodeURIComponent(id)}`);if(!d){toast('강사 데이터 없음');return;}
  instructor={id,...d};saveLocal();curAI=0;renderSb();renderMain();toast(`${instructor.name}으로 전환됨 ✅`);}
  catch(e){toast('전환 실패: '+e);}
}
async function rmInstr(id,name){
  if(!adminOn){toast('관리자 모드가 필요합니다.');return;}
  if(!confirm(`"${name}" 강사를 삭제합니까?\n이 작업은 되돌릴 수 없습니다.`))return;
  try{await fbPut(`config/instructors/${encodeURIComponent(id)}`,null);toast(`${name} 삭제됨`);loadInstrsSection();}
  catch(e){toast('삭제 실패: '+e);}
}

// ══════════════════════════════════════════════════════════
//  프리셋 추가 / 삭제
// ══════════════════════════════════════════════════════════
function addPreset(){
  const inp=document.getElementById('pInput');if(!inp)return;
  const val=inp.value.trim();if(!val){toast('문구를 입력하세요.');return;}
  if(!instructor){toast('먼저 계정을 설정해 주세요.');return;}
  if(!instructor.presets)instructor.presets=[];
  if(instructor.presets.includes(val)){toast('이미 있는 프리셋입니다.');return;}
  instructor.presets.push(val);inp.value='';saveLocal();
  if(dbUrl&&dbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{presets:instructor.presets}).catch(()=>{});
  renderMain();
}
function rmPreset(i){
  if(!instructor?.presets)return;
  if(!confirm(`"${instructor.presets[i]}" 프리셋을 삭제합니까?`))return;
  instructor.presets.splice(i,1);saveLocal();
  if(dbUrl&&dbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{presets:instructor.presets}).catch(()=>{});
  renderMain();
}

function closeIM(){document.getElementById('iModal').classList.remove('show');}
function toggleAcc(hdr){
  const body=hdr.nextElementSibling;
  const arrow=hdr.querySelector('.acc-arr');
  const open=body.classList.toggle('open');
  if(arrow)arrow.textContent=open?'▼':'▶';
}
