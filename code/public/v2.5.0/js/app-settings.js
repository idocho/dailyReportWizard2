
// ══════════════════════════════════════════════════════════
//  설정
// ══════════════════════════════════════════════════════════
// 설정 좌측 탭 (account|conn|data|admin) — 재렌더 없이 CSS show/hide 전환
let stgTab='account';
function setStg(t){
  stgTab=t;
  document.querySelectorAll('.stg-tab').forEach(b=>b.classList.toggle('on',b.dataset.stg===t));
  document.querySelectorAll('.stg-pane').forEach(p=>p.classList.toggle('on',p.dataset.stg===t));
}
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

// (v2.5.0) 온보딩 위저드 제거됨 — 로그인 게이트가 대체(index.html). 신원=acl.

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
      +_sortedAsgns(asgns).map(({a,i})=>`<div class="ar" style="grid-template-columns:1fr 1fr 52px 30px"><span style="font-weight:700">${esc(a.classId)}</span><span style="color:var(--sub);font-size:11px">${esc(a.subject)}</span><span style="font-size:10px;color:var(--indigo)">${esc(a.role||'담임')}</span><button style="background:none;border:none;cursor:pointer;color:var(--red);font-size:14px;padding:0" onclick="removeA(${i})">✕</button></div>`).join('');
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
      ?('<option value="">-- 과목 선택 --</option>'+Object.keys(activeCourses(config.classes?.[firstCls])).sort((a,b)=>a.localeCompare(b,'ko')).map(s=>`<option>${esc(s)}</option>`).join(''))
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
    // 신규: 모든 classes의 courses를 수집 (관리자 뷰는 보관 과목도 표시 — 배지로 구분)
    const subjectMap=new Map(); // name → archived(전 학급에서 모두 보관일 때만 true)
    for(const clsD of Object.values(config?.classes||{})){
      for(const[s,c] of Object.entries(clsD.courses||{})){
        const arch=!!(c&&c.archived);
        subjectMap.set(s,subjectMap.has(s)?(subjectMap.get(s)&&arch):arch);
      }
    }
    const subjectNames=[...subjectMap.keys()].sort((a,b)=>a.localeCompare(b,'ko'));
    const tbRows = subjectNames.map(name=>`<div style="display:flex;align-items:center;padding:6px 12px;border-bottom:1px solid var(--border);gap:8px">
        <span style="flex:1;font-size:12px;font-weight:600${subjectMap.get(name)?';color:var(--gray)':''}">${esc(name)}</span>
        ${subjectMap.get(name)?'<span style="font-size:9px;background:#F1F5F9;color:#64748B;border-radius:8px;padding:1px 6px;font-weight:700">보관</span>':''}
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

  // ── 관리자: 교재 명단 (전역 레지스트리 config/textbooks — 반 삭제와 무관하게 보존) ──
  const tbListHtml = adminOn ? (()=>{
    const names=Object.keys(config?.textbooks||{}).sort((a,b)=>a.localeCompare(b,'ko'));
    const rows=names.map(n=>`<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 12px;border-bottom:1px solid var(--border)">
        <span style="font-size:12px;font-weight:600">${esc(n)}</span>
        <button style="background:none;border:none;cursor:pointer;color:var(--red);font-size:13px;padding:0 2px;line-height:1" onclick="rmTbName('${esc(n)}')">✕</button>
      </div>`).join('')||'<div style="padding:8px 12px;font-size:11px;color:var(--gray)">등록된 교재명 없음 — 과목 등록 시 자동 추가됩니다</div>';
    return `<div class="sa admin-sec" id="sa-tblist">
      <div class="sa-hdr${openSaIds.has('sa-tblist')?' open':''}" onclick="_saToggle('sa-tblist')">
        <span class="sa-ico">📚</span>
        <span class="sa-lbl">교재 명단</span>
        <span style="font-size:10px;background:#FEF3C7;color:#92400E;border-radius:8px;padding:1px 6px;font-weight:700;margin-right:4px">관리자</span>
        <span class="sa-chv">›</span>
      </div>
      <div class="sa-body${openSaIds.has('sa-tblist')?' open':''}">
        <div style="padding:6px 12px;font-size:11px;color:var(--gray)">반을 삭제해도 보존되는 전역 교재 목록 — 과목 등록 자동완성에 사용. 과목 등록 시 새 교재명은 자동 추가됩니다.</div>
        ${rows}
        <div style="display:flex;gap:6px;padding:10px 12px 4px">
          <input class="inp sm" id="newTbName" placeholder="교재명 직접 추가" style="flex:1"
            onkeydown="if(event.key==='Enter'){event.preventDefault();addTbName();}">
          <button class="btn bp bsm" onclick="addTbName()">+ 추가</button>
        </div>
        <div style="padding:4px 12px 8px;font-size:10px;color:var(--gray)">✕ 제거는 자동완성 후보에서만 제외 — 등록된 과목·기록에는 영향 없음</div>
      </div>
    </div>`;
  })() : '';

  // 강사 관리(생성·전환·삭제)는 CampusManager 전담 — DRW에서 제거(이중 관리 방지).

  // v2.5.0 슬림화: Firebase 연결(SA_FB)·자가등록 계정(SA_ACCT) 제거 — 로그인이 대체.
  //   연결정보는 로그인 게이트가 자동 주입(index.html), 신원은 acl(instructorId)에서 옴.
  //   내 이름은 사이드바 아바타에 표시됨(app-core).

  const SA_PRESET=`
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
    </div>`;

  const SA_ASGN=`
    <div class="sa" id="sa-asgn">
      <div class="sa-hdr${openSaIds.has('sa-asgn')?' open':''}" onclick="_saToggle('sa-asgn')">
        <span class="sa-ico">📚</span>
        <span class="sa-lbl">내 담당 수업</span>
        <span class="sa-sub">${asgns.length}개</span>
        <span class="sa-chv">›</span>
      </div>
      <div class="sa-body${openSaIds.has('sa-asgn')?' open':''}">${asgRows}${addAsgn}</div>
    </div>`;

  const SA_CLS=`
    <div class="sa" id="sa-cls">
      <div class="sa-hdr${openSaIds.has('sa-cls')?' open':''}" onclick="_saToggle('sa-cls')">
        <span class="sa-ico">🏫</span>
        <span class="sa-lbl">학급 &amp; 학생 관리</span>
        <span class="sa-sub">${config?Object.keys(config.classes||{}).length+'개 학급':'–'}</span>
        <span class="sa-chv">›</span>
      </div>
      <div class="sa-body${openSaIds.has('sa-cls')?' open':''}">${renderClsMgmt()}</div>
    </div>`;

  const SA_RESET=`
    <div class="sa" id="sa-reset">
      <div class="sa-hdr${openSaIds.has('sa-reset')?' open':''}" onclick="_saToggle('sa-reset')">
        <span class="sa-ico">🗑</span>
        <span class="sa-lbl" style="color:var(--red)">초기화</span>
        <span class="sa-sub"></span>
        <span class="sa-chv">›</span>
      </div>
      <div class="sa-body${openSaIds.has('sa-reset')?' open':''}">${resetHtml}</div>
    </div>`;

  // ── AI 문체·지침 (리포트 생성) ──
  const _AISTYLES=(typeof RP_STYLES!=='undefined')?RP_STYLES:[['auto','✍️ 내 말투 자동']];
  const aiMode=instr.ai_style_mode||'auto', aiCustom=instr.ai_custom_prompt||'';
  const SA_AISTYLE=`
    <div class="sa" id="sa-aistyle">
      <div class="sa-hdr${openSaIds.has('sa-aistyle')?' open':''}" onclick="_saToggle('sa-aistyle')">
        <span class="sa-ico">✍️</span>
        <span class="sa-lbl">AI 문체 · 지침</span>
        <span class="sa-sub">리포트 생성</span>
        <span class="sa-chv">›</span>
      </div>
      <div class="sa-body${openSaIds.has('sa-aistyle')?' open':''}">
        <div style="padding:10px 12px">
          <div class="sl">문체(말투)</div>
          <select class="inp sm" id="aiStyleMode" onchange="renderAiStyleInfo()">${_AISTYLES.map(([k,l])=>`<option value="${esc(k)}"${k===aiMode?' selected':''}>${esc(l)}</option>`).join('')}</select>
          <div id="aiStyleInfo" class="ai-style-info">${_aiStyleInfoHtml(aiMode)}</div>
          <div class="sl" style="margin-top:10px">개별 지침 (선택)</div>
          <textarea class="inp sm" id="aiCustom" style="min-height:62px;resize:vertical" placeholder="예: 마지막에 다음 수업 준비물을 안내해 주세요">${esc(aiCustom)}</textarea>
          <div style="font-size:10px;color:var(--gray);margin:6px 0 8px">AI 엔진·API 키는 본인 PC 에이전트에서 설정합니다.</div>
          <button class="btn bsm" onclick="saveAiStyle()">💾 저장</button>
        </div>
      </div>
    </div>`;

  // 활성 탭 (관리자 탭은 adminOn일 때만) — 잡다한 단일 스크롤 → 4탭 좌측 레일
  // ── 평탄화: 탭 = 기능 1개, 아코디언(이중구조) 제거 → 카드 직접 표시 ──
  const _card=(ic,title,sub,body)=>`<div class="stg-card"><div class="stg-card-h"><span>${ic}</span><b>${esc(title)}</b>${sub?`<span class="stg-csub">${esc(sub)}</span>`:''}</div><div class="stg-card-b">${body}</div></div>`;
  const _aiBody=`<div style="padding:12px"><div class="sl">문체(말투)</div><select class="inp sm" id="aiStyleMode" onchange="renderAiStyleInfo()">${_AISTYLES.map(([k,l])=>`<option value="${esc(k)}"${k===aiMode?' selected':''}>${esc(l)}</option>`).join('')}</select><div id="aiStyleInfo" class="ai-style-info">${_aiStyleInfoHtml(aiMode)}</div><div class="sl" style="margin-top:12px">개별 지침 (선택) <span class="fld-tag">추가 프롬프트</span></div><div class="fld-help">리포트를 생성할 때마다 AI에게 <b>항상 함께 전달되는 추가 지시문</b>입니다. 선택한 문체에 더해 <b>내가 맡은 전 학생 메시지에 공통 적용</b>돼요.</div><textarea class="inp sm" id="aiCustom" style="min-height:64px;resize:vertical" placeholder="예: 항상 마지막에 다음 수업 준비물과 날짜를 안내해 주세요">${esc(aiCustom)}</textarea><div style="font-size:10px;color:var(--gray);margin:6px 0 10px">AI 엔진·API 키는 본인 PC 에이전트에서 설정합니다.</div><button class="btn bsm" onclick="saveAiStyle()">💾 저장</button></div>`;
  const _presetBody=`${presetChips||'<div style="padding:10px 12px;font-size:12px;color:var(--gray)">등록된 문구가 없습니다.</div>'}<div style="padding:8px 12px;border-top:1px solid var(--border);display:flex;gap:6px"><input class="inp sm" id="pInput" placeholder="새 문구 입력" style="flex:1" onkeydown="if(event.key==='Enter')addPreset()"><button class="btn bsm" onclick="addPreset()">+ 추가</button></div>`;
  const _sysBody=`<div style="padding:12px;display:flex;flex-direction:column;gap:8px"><button class="btn bsm" style="width:100%;justify-content:center;display:flex;gap:6px" onclick="doLogout()">🚪 로그아웃</button>${(_isMgr()&&!_isTopAdmin())?`<div style="font-size:11px;color:var(--sub);background:var(--bg);border-radius:8px;padding:8px 10px;line-height:1.5">관리자 모드는 좌측 사이드바의 <b>강사 ⇄ 관리자</b> 스위치로 전환합니다.</div>`:''}${_isTopAdmin()?`<div style="font-size:11px;color:var(--sub);background:var(--bg);border-radius:8px;padding:8px 10px;line-height:1.5">운영자 계정은 항상 <b>관리자 모드</b>입니다.</div>`:''}<div style="font-size:10px;color:var(--gray);text-align:center">DailyReportWizard ${APP_VERSION} · Crafted by IDO · Powered by Claude AI</div></div>`;
  let _subjBody='',_bookBody='';
  if(adminOn){
    const sm=new Map();
    for(const clsD of Object.values(config?.classes||{}))for(const[s,c]of Object.entries(clsD.courses||{})){const ar=!!(c&&c.archived);sm.set(s,sm.has(s)?(sm.get(s)&&ar):ar);}
    _subjBody=[...sm.keys()].sort((a,b)=>a.localeCompare(b,'ko')).map(n=>`<div style="display:flex;align-items:center;padding:6px 12px;border-bottom:1px solid var(--border);gap:8px"><span style="flex:1;font-size:12px;font-weight:600${sm.get(n)?';color:var(--gray)':''}">${esc(n)}</span>${sm.get(n)?'<span style="font-size:9px;background:#F1F5F9;color:#64748B;border-radius:8px;padding:1px 6px;font-weight:700">보관</span>':''}</div>`).join('')||'<div style="padding:8px 12px;font-size:11px;color:var(--gray)">등록된 과목 없음</div>';
    const bn=Object.keys(config?.textbooks||{}).sort((a,b)=>a.localeCompare(b,'ko'));
    _bookBody=`<div style="padding:6px 12px;font-size:11px;color:var(--gray)">반 삭제와 무관하게 보존되는 전역 교재 목록(자동완성).</div>`+(bn.map(n=>`<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 12px;border-bottom:1px solid var(--border)"><span style="font-size:12px;font-weight:600">${esc(n)}</span><button style="background:none;border:none;cursor:pointer;color:var(--red);font-size:13px;padding:0 2px" onclick="rmTbName('${esc(n)}')">✕</button></div>`).join('')||'<div style="padding:8px 12px;font-size:11px;color:var(--gray)">등록된 교재명 없음</div>')+`<div style="display:flex;gap:6px;padding:10px 12px"><input class="inp sm" id="newTbName" placeholder="교재명 직접 추가" style="flex:1" onkeydown="if(event.key==='Enter'){event.preventDefault();addTbName();}"><button class="btn bp bsm" onclick="addTbName()">+ 추가</button></div>`;
  }
  const _valid=['asgn','style','preset','roster','subj','book','reset','system'];
  let T=_valid.includes(stgTab)?stgTab:'asgn';
  if(['subj','book'].includes(T)&&!adminOn)T='asgn';
  const _tab=(k,ic,lb,adm)=> (adm&&!adminOn)?'' : `<button class="stg-tab${T===k?' on':''}" data-stg="${k}" onclick="setStg('${k}')">${ic} ${lb}</button>`;
  const _pane=(k,html,adm)=> (adm&&!adminOn)?'' : `<div class="stg-pane${T===k?' on':''}" data-stg="${k}">${html}</div>`;
  mc.innerHTML=makeTb('설정')+`<div class="stg">
    <div class="stg-rail">
      ${_tab('asgn','👤','수업')}
      ${_tab('style','✍️','AI설정')}
      ${_tab('preset','💬','문구')}
      ${_tab('roster','🏫','명단')}
      ${_tab('subj','📖','과목',true)}
      ${_tab('book','📚','교재',true)}
      ${_tab('reset','🗑','초기화')}
      ${_tab('system','⚙️','시스템')}
    </div>
    <div class="stg-panes">
      ${_pane('asgn',_card('👤','담당 수업',asgns.length+'개',asgRows+addAsgn))}
      ${_pane('style',_card('✍️','AI 문체·지침','',_aiBody))}
      ${_pane('preset',_card('💬','자주 쓰는 문구',myPresets.length+'개',_presetBody))}
      ${_pane('roster',_card('🏫','학급 · 학생','',renderClsMgmt()))}
      ${_pane('subj',_card('📖','과목 목록','관리자',_subjBody),true)}
      ${_pane('book',_card('📚','교재 명단','관리자',_bookBody),true)}
      ${_pane('reset',_card('🗑','초기화','',resetHtml))}
      ${_pane('system',_card('⚙️','시스템','',_sysBody))}
    </div>
  </div>`;

  setSync(!!dbUrl&&!!dbPath);
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
    const subjectCount=Object.keys(activeCourses(clsD)).length;
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
    <div class="sh2" style="display:flex;align-items:center;justify-content:space-between">전체 학급 탐색${_rosterAdmin()?`<button class="btn bsm" onclick="addClsModal()" style="font-size:11px;padding:3px 9px">+ 학급 추가</button>`:''}</div>
    ${drillBtns||'<div style="padding:8px 12px;font-size:11px;color:var(--gray)">등록된 학급이 없습니다.</div>'}
  </div>`;
}

function renderClsMgmtClass(classId){
  if(!config)return '';
  _ensureConfigShape();
  const clsD=config.classes?.[classId]||{courses:{}};
  // 드릴인 상세 화면: 아코디언 없이 본문을 바로 펼쳐 보여줌 (이중 클릭 제거)
  return `<div class="card">
    <div class="sh" style="display:flex;align-items:center;gap:8px;padding:7px 10px 7px 14px">
      <button class="btn bsm" onclick="clsDrillSh=null;renderMain()" style="flex-shrink:0;font-size:11px">← 뒤로</button>
      <span style="flex:1">🏫 ${esc(classId)} 학급 관리</span>
      ${_rosterAdmin()?`<button class="btn br bsm" onclick="rmCls('${esc(classId)}')" style="padding:2px 7px;font-size:11px;flex-shrink:0">학급 삭제</button>`:''}
    </div>
    <div style="padding:12px 14px">${_clsSectionsHtml(classId,clsD)}</div>
  </div>`;
}

// 표시 동일 과목(과정·교재 필드 일치, 키 상이) 탐색 — 구형 키(교재명만)와 신형 복합 키의
// 중복 등록 방지. 칩 표시가 필드 기반이라 키가 달라도 똑같이 보이는 중복이 생길 수 있음(3MSM 사례)
function _findCourseTwin(courses,curriculum,textbook,excludeKey){
  const nc=_normGradeSem(curriculum),nt=_normTbName(textbook);
  for(const[k,c]of Object.entries(courses||{})){
    if(k===excludeKey||!c)continue;
    if(_normGradeSem(c.curriculum||'')===nc&&_normTbName(c.textbook||'')===nt)return k;
  }
  return null;
}

// 과목 칩 1개 (활성) — 과정 라벨 + 교재명 + 보관(×)
function _courseChipHtml(classId,subj,course){
  const curriculum=course.curriculum||'';
  const tbLabel=course.textbook||subj;
  const subLabel=curriculum?`<span style="color:var(--indigo);font-size:9px;font-weight:700;margin-right:3px">${esc(curriculum)}</span>`:'';
  return`<span class="chip" onclick="rmCourse('${esc(classId)}','${esc(subj)}')">${subLabel}${esc(tbLabel)} <span style="display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px;margin-left:4px;border-radius:50%;background:#FEE2E2;color:#B91C1C;font-size:10px;font-weight:700;line-height:1">×</span></span>`;
}
// 과목 칩 블록 — 활성 행(과정→교재명 오름차순) + 보관 행(기본 접힘, ↩ 원클릭 복원).
// subject 키 = "{과정} {교재}" 복합이라 키 ko 정렬이 곧 과정→교재명 순.
// 아코디언 본문·드릴인 상세·refreshCourseChips 3곳 공용 (마크업 발산 방지)
function _courseChipsBlockHtml(classId,clsD){
  const all=(clsD||{}).courses||{};
  const ko=(a,b)=>a.localeCompare(b,'ko');
  const act=Object.keys(all).filter(s=>!(all[s]&&all[s].archived)).sort(ko);
  const arch=Object.keys(all).filter(s=>all[s]&&all[s].archived).sort(ko);
  const actChips=act.map(s=>_courseChipHtml(classId,s,all[s]||{})).join('');
  const archChips=arch.map(s=>{
    const c=all[s]||{};
    const subLabel=c.curriculum?`<span style="color:var(--indigo);font-size:9px;font-weight:700;margin-right:3px">${esc(c.curriculum)}</span>`:'';
    return`<span class="chip arch"><span class="arch-badge">보관</span>${subLabel}${esc(c.textbook||s)} <span class="restore" onclick="restoreCourse('${esc(classId)}','${esc(s)}')">↩ 복원</span></span>`;
  }).join('');
  const open=!!archOpen[classId]; // 펼침 상태 세션 보존 — 보관/복원 재렌더마다 접히는 불편 방지
  return`<div class="chips" data-classid="${esc(classId)}" data-chip-type="course">${actChips}<span class="chip" style="background:var(--indigo-l);border-color:var(--indigo);color:var(--indigo);cursor:pointer" onclick="addCourseInline('${esc(classId)}',this)">+ 과목 추가</span></div>`
    +(arch.length?`<button class="arch-tg" onclick="toggleArchRow(this,'${esc(classId)}')">${open?'▾':'▸'} 보관 ${arch.length}</button><div class="chips" style="display:${open?'flex':'none'}">${archChips}</div>`:'');
}
function toggleArchRow(btn,classId){
  const row=btn.nextElementSibling;if(!row)return;
  const open=row.style.display!=='none';
  archOpen[classId]=!open;
  row.style.display=open?'none':'flex';
  btn.textContent=(open?'▸':'▾')+btn.textContent.slice(1);
}

// 학급의 학생/과목 칩 섹션 (아코디언 본문과 드릴인 상세에서 공용)
function _clsSectionsHtml(classId,clsD){
  const students=(config?._classStudents||{})[classId]||[];
  // 설정 명단은 조회 전용 — 학생 추가·편집은 사이드바 '🏫 학생 명단' 탭으로 일원화
  const stuChips=students.map(s=>`<span class="chip" style="cursor:default">${esc(s.name||s.nameKey)}</span>`).join('');
  return `<div class="sl">학생${_isMgr()?` <span style="font-weight:500;font-size:10px;color:var(--gray)">· 추가/편집은 ‘학생 명단’ 탭</span>`:''}</div>
      <div class="chips" data-classid="${esc(classId)}" data-chip-type="stu">${stuChips||`<span style="font-size:11px;color:var(--gray)">학생 없음</span>`}</div>
      <div class="sl" style="margin-top:10px">과목</div>
      <div data-course-block="${esc(classId)}">${_courseChipsBlockHtml(classId,clsD)}</div>`;
}

function buildClsAccordion(classId,clsD,myRole){
  const students=(config?._classStudents||{})[classId]||[];
  const subjects=Object.keys(activeCourses(clsD));
  const isSub=myRole==='부담임';
  const subBadge=isSub?`<span style="font-size:9px;background:#FEF3C7;color:#92400E;border-radius:8px;padding:1px 6px;font-weight:700;flex-shrink:0">부담임</span>`:'';
  const open=!!clsAccOpen[classId]; // 펼침 상태 세션 보존 — 보관/복원 등 renderMain 후에도 유지
  return `<div style="border-bottom:1px solid var(--border)">
    <div class="acc-hdr" onclick="toggleAcc(this,'${esc(classId)}')">
      <span class="acc-arr" style="font-size:10px;color:var(--gray);width:14px;flex-shrink:0">${open?'▼':'▶'}</span>
      <span style="font-size:13px;font-weight:700;flex:1">${esc(classId)}</span>
      ${subBadge}
      <span style="font-size:10px;color:var(--gray);margin:0 6px;white-space:nowrap">학생 ${students.length} · 과목 ${subjects.length}</span>
      ${_rosterAdmin()?`<button class="btn br bsm" onclick="rmCls('${esc(classId)}');event.stopPropagation()" style="padding:2px 7px;font-size:11px;flex-shrink:0">✕</button>`:''}
    </div>
    <div class="acc-body${open?' open':''}">${_clsSectionsHtml(classId,clsD)}</div>
  </div>`;
}

// ── 학급 CRUD (설정 명단 탭) — 학생 추가·편집은 '🏫 학생 명단' 탭으로 일원화 ──────
function addClsModal(){
  if(!_rosterAdmin())return toast('학급·학생 편집 권한이 없습니다.');
  _rpModal(`<h3>학급 추가</h3>
    <label class="rp-flbl">반 이름</label><input class="rp-fin" id="cl-id" placeholder="예: 중1A">
    <label class="rp-flbl">그룹</label><select class="rp-fin" id="cl-grp"><option value="M">M반 (월수금)</option><option value="T">T반 (화목토)</option></select>
    <div class="rp-mrow"><button class="rp-btn ghost" onclick="closeRpModal()">취소</button><button class="rp-btn" onclick="saveCls()">추가</button></div>`);
  setTimeout(()=>document.getElementById('cl-id')?.focus(),0);
}
async function saveCls(){
  const id=(document.getElementById('cl-id').value||'').trim();
  const grp=document.getElementById('cl-grp').value;
  if(!id)return toast('반 이름을 입력하세요');
  if(config?.classes?.[id])return toast('이미 있는 반입니다');
  try{
    await fbPut('classes/'+encodeURIComponent(id),{group:grp,courses:{}});
    config.classes=config.classes||{}; config.classes[id]={group:grp,courses:{}};
    closeRpModal(); toast(`${id} 추가됨 ✅`); clsDrillSh=id; renderMain();
  }catch(e){ toast('학급 추가 실패: '+e,4000); }
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
  const existingTbs=new Set(Object.keys(config?.textbooks||{}));  // 전역 레지스트리 (반 삭제와 무관)
  for(const clsD of Object.values(config?.classes||{}))
    for(const c of Object.values(clsD.courses||{}))
      if(c.textbook)existingTbs.add(c.textbook);
  [...existingTbs].sort((a,b)=>a.localeCompare(b,'ko')).forEach(t=>{const o=document.createElement('option');o.value=t;tbDl.appendChild(o);});
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
    // subject key = "과정 교재" 조합 (과정·교재 둘 다 같을 때만 중복으로 간주)
    const subject=`${curriculum} ${textbook}`;
    const existingCourses=config?.classes?.[classId]?.courses||{};
    const prev=existingCourses[subject];
    if(prev&&!prev.archived){toast('이미 추가된 과목입니다 (같은 과정·교재).');return;}
    const twin=_findCourseTwin(existingCourses,curriculum,textbook,subject);
    if(twin){
      if(!existingCourses[twin].archived){toast('이미 추가된 과목입니다 (같은 과정·교재).');return;}
      wrapper.remove();
      restoreCourse(classId,twin); // 보관된 구형 키 → 새 키 생성 대신 그 키 그대로 복원 (중복 방지)
      return;
    }
    const restoring=!!(prev&&prev.archived); // 보관 과목 재추가 = 복원 (기존 기록 그대로 연결)
    if(!config.classes)config.classes={};
    if(!config.classes[classId])config.classes[classId]={group:'',courses:{}};
    if(!config.classes[classId].courses)config.classes[classId].courses={};
    const courseData={textbook,curriculum};
    config.classes[classId].courses[subject]=courseData;
    wrapper.remove();
    try{refreshCourseChips(classId);}catch(e){renderMain();}
    if(dbUrl&&dbPath){
      try{
        await fbPatch(`classes/${classId}/courses/${subject}`,{...courseData,archived:null});
        _registerTbName(textbook);
        toast(restoring?'보관 과목 복원됨 ✅ (기존 기록 연결)':'과목 추가됨 ✅');
      }catch(e){toast('저장 실패: '+e,4000);}
    }
    saveLocal();
  }
  ok.onclick=doAdd;
  [gsSel,tbInp].forEach(el=>{el.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();ok.click();}});});

  wrapper.appendChild(gsSel);wrapper.appendChild(tbInp);wrapper.appendChild(ok);wrapper.appendChild(cancel);
  chips.parentElement.appendChild(wrapper);
  gsSel.focus();
}

function refreshCourseChips(classId){
  const sCls=classId.replace(/\\/g,'\\\\').replace(/"/g,'\\"');
  const el=document.querySelector(`[data-course-block="${sCls}"]`);
  if(!el)return;
  el.innerHTML=_courseChipsBlockHtml(classId,config?.classes?.[classId]);
}

// ── 교재 명단(전역 레지스트리) 관리 — 관리자 전용 ─────────────────
function addTbName(){
  if(!adminOn){toast('관리자만 가능합니다.');return;}
  const name=_normTbName(document.getElementById('newTbName')?.value||'');
  if(!name){toast('교재명을 입력해 주세요.');return;}
  if(!config.textbooks)config.textbooks={};
  if(config.textbooks[name]){toast('이미 있는 교재명입니다.');return;}
  config.textbooks[name]=true;saveLocal();
  if(dbUrl&&dbPath)fbPatch('config/textbooks',{[name]:true}).then(()=>toast('교재명 추가됨 ✅')).catch(fbFail('교재 명단'));
  renderMain();
}
function rmTbName(name){
  if(!adminOn){toast('관리자만 가능합니다.');return;}
  if(!confirm(`"${name}" 을(를) 교재 명단에서 제거합니까?
(등록된 과목·기록에는 영향 없음 — 자동완성 후보에서만 제외)`))return;
  if(config?.textbooks)delete config.textbooks[name];
  saveLocal();
  if(dbUrl&&dbPath)fbPatch('config/textbooks',{[name]:null}).then(()=>toast('제거됨')).catch(fbFail('교재 명단'));
  renderMain();
}
function _registerTbName(textbook){
  // 과목 등록 시 전역 레지스트리에 자동 등록 (idempotent) — 반 삭제 후에도 교재명 보존
  const name=_normTbName(textbook||'');
  if(!name)return;
  if(!config.textbooks)config.textbooks={};
  if(config.textbooks[name])return;
  config.textbooks[name]=true;
  if(dbUrl&&dbPath)fbPatch('config/textbooks',{[name]:true}).catch(fbFail('교재 명단'));
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
  if(dbUrl&&dbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{presets:instructor.presets}).catch(fbFail('문구'));
  toast('문구 수정됨 ✅');
  renderMain();
}

// ══════════════════════════════════════════════════════════
//  설정 저장 / 강사 / 학급 관리
// ══════════════════════════════════════════════════════════
function saveFb(){
  dbUrl=document.getElementById('sUrl')?.value.trim()||'';
  dbPath=document.getElementById('sPth')?.value.trim()||'';
  dbSecret=document.getElementById('sSec')?.value.trim()||'';
  SS('drw_db_url',dbUrl);SS('drw_db_path',dbPath);SS('drw_db_secret',dbSecret);
  saveLocal();toast('Firebase 설정 저장됨 ✅');
}

// 문체 설명·예시 안내 (RP_STYLE_INFO = ai_style.py STYLE_PRESETS 미러)
function _aiStyleInfoHtml(mode){
  const info=(typeof RP_STYLE_INFO!=='undefined')?RP_STYLE_INFO[mode]:null;
  if(!info) return '';
  const ex=(info.ex||[]).map(e=>`<div class="asi-ex">“${esc(e)}”</div>`).join('');
  return `<div class="asi-desc">${esc(info.desc)}</div>`
    + (ex ? `<div class="asi-exh">예시 문구</div>${ex}`
          : `<div class="asi-exh">전송한 노트가 쌓이면 본인 문장이 예시로 학습됩니다.</div>`);
}
function renderAiStyleInfo(){
  const el=document.getElementById('aiStyleInfo'); if(!el) return;
  el.innerHTML=_aiStyleInfoHtml(document.getElementById('aiStyleMode')?.value||'auto');
}
async function saveAiStyle(){
  if(!instructor){toast('강사 미선택');return;}
  const mode=document.getElementById('aiStyleMode')?.value||'auto';
  const custom=(document.getElementById('aiCustom')?.value||'').trim();
  instructor.ai_style_mode=mode; instructor.ai_custom_prompt=custom; saveLocal();
  try{
    if(dbUrl&&dbPath&&instructor.id) await fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{ai_style_mode:mode,ai_custom_prompt:custom});
    toast('AI 문체·지침 저장 ✅');
  }catch(e){toast('저장 실패: '+(e.message||e));}
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

function onCC(){
  // 신규: 반 선택 시 해당 반의 courses 키 목록을 과목 셀렉트에 채움
  const s=document.getElementById('aCls');if(!s||!config)return;
  const classId=s.value;
  const subjects=Object.keys(activeCourses(config?.classes?.[classId])).sort((a,b)=>a.localeCompare(b,'ko'));
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
  if(dbUrl&&dbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{assignments:instructor.assignments}).catch(fbFail('담당 수업'));
  toast('담당 수업 추가됨 ✅');openSaIds.add('sa-asgn');renderMain();
}
function removeA(i){
  if(!instructor?.assignments)return;if(!confirm('이 담당 수업을 제거합니까?'))return;
  instructor.assignments.splice(i,1);if(curAI>=instructor.assignments.length)curAI=0;saveLocal();
  if(dbUrl&&dbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{assignments:instructor.assignments}).catch(fbFail('담당 수업'));
  renderMain();renderSb();
}

function _ensureConfigShape(){
  if(!config)config={classes:{},instructors:{}};
  if(!config.classes)config.classes={};
  if(!config.instructors)config.instructors={};
  return config;
}

// pushCfg(classes 전체 PUT) 제거(v2.2.2) — 다른 기기의 stale 로컬 config가 삭제/보관된 과목을
// 통째로 되살리는 부활 버그 원인. 모든 쓰기는 변경 노드만 타겟 PATCH/PUT.
// addCls/addCourse(prompt 방식)는 호출처 없는 죽은 코드라 함께 제거 — 추가는 addCourseInline/wzAddCourse 경로만 사용.

function _syncAssignments(){
  if(!instructor?.assignments?.length)return;
  const before=instructor.assignments.length;
  instructor.assignments=instructor.assignments.filter(a=>{
    const clsD=config?.classes?.[a.classId];
    if(!clsD)return false;
    // 보관(archived) 과목 배정도 제거 — 복원 시 수업 추가에서 재배정
    return !a.subject||Object.prototype.hasOwnProperty.call(activeCourses(clsD),a.subject);
  });
  if(instructor.assignments.length===before)return;
  if(curAI>=instructor.assignments.length)curAI=0;
  saveLocal();
  if(dbUrl&&dbPath&&instructor.id)
    fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{assignments:instructor.assignments}).catch(fbFail('담당 수업'));
}

function rmCls(classId){
  if(!_rosterAdmin()){toast('학급 삭제 권한이 없습니다.');return;}
  if(!confirm(`${classId} 학급을 삭제합니까?`))return;
  delete config.classes[classId];
  if(config._classStudents)delete config._classStudents[classId];
  if(instructor?.assignments){
    const before=instructor.assignments.length;
    instructor.assignments=instructor.assignments.filter(a=>a.classId!==classId);
    if(instructor.assignments.length!==before){
      if(curAI>=instructor.assignments.length)curAI=0;
      if(dbUrl&&dbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{assignments:instructor.assignments}).catch(fbFail('담당 수업'));
    }
  }
  saveLocal();
  // 해당 학급 노드만 타겟 삭제 (classes 전체 PUT 금지 — 부활 버그 방지)
  if(dbUrl&&dbPath)fbPut(`classes/${classId}`,null).then(()=>toast('학급 삭제됨 ✅')).catch(e=>toast('학급 삭제 실패: '+e,4000));
  renderMain();
}

async function restoreCourse(classId,subject){
  // 보관 해제(v2.2.3): 같은 과정·교재 재입력 없이 원클릭 복원 — 기존 obs/scores/history 그대로 연결.
  // 담당 배정은 보관 시 _syncAssignments로 제거됐으므로 복원 후 「수업 추가」에서 재배정.
  const c=config?.classes?.[classId]?.courses?.[subject];
  if(!c||!c.archived){toast('이미 활성 과목입니다.');return;}
  if(!confirm(`"${subject}" 과목을 복원합니까?\n기존 수업 기록이 그대로 연결됩니다.`))return;
  delete c.archived;
  try{refreshCourseChips(classId);}catch(e){}
  if(dbUrl&&dbPath){
    try{
      await fbPatch(`classes/${classId}/courses/${subject}`,{archived:null});
      if(c.textbook)_registerTbName(c.textbook);
      toast('과목 복원됨 ✅ (기존 기록 연결)');
    }catch(e){
      c.archived=true; // DB 반영 실패 → 로컬 롤백 + 사용자에게 표면화
      toast('과목 복원 실패: '+e,4000);
      try{refreshCourseChips(classId);}catch(_){}
      renderMain();
      return;
    }
  }
  saveLocal();
  renderMain();
}

async function rmCourse(classId,subject){
  // 소프트 삭제(v2.2.2): 하드 삭제 대신 archived:true 마킹 — obs/session/scores 기록은 DB에 보존.
  // 같은 과정·교재로 재추가하면 archived 해제로 복원(기존 기록 그대로 연결). Analyzer는 보관 과목 기록도 조인 가능.
  if(!confirm(`"${subject}" 과목을 보관(숨김) 처리합니까?\n수업 기록은 유지되며, 같은 과정·교재를 다시 추가하면 복원됩니다.`))return;
  const c=config?.classes?.[classId]?.courses?.[subject];
  if(c)c.archived=true;
  archOpen[classId]=true; // 방금 보관한 과목이 어디로 갔는지 보이게 보관 행 자동 펼침
  try{refreshCourseChips(classId);}catch(e){}
  if(dbUrl&&dbPath){
    try{
      await fbPatch(`classes/${classId}/courses/${subject}`,{archived:true});
      toast('과목 보관됨 ✅ (기록은 유지)');
    }catch(e){
      if(c)delete c.archived; // DB 반영 실패 → 로컬 롤백 + 사용자에게 표면화
      toast('과목 보관 실패: '+e,4000);
      try{refreshCourseChips(classId);}catch(_){}
      renderMain();
      return;
    }
  }
  saveLocal();
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
      Object.values(classStudents).forEach(sortStu);
      config._classStudents=classStudents;
    }
    saveLocal();setSync(true);
    try{let s=await fbGet('session').catch(()=>null);if(s?.class_data)Object.assign(progressData,s.class_data);saveLocal();}catch(e){}
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
  {id:'all-input',    icon:'🗂',  label:'전체 오늘 입력 삭제', desc:'모든 강사의 오늘 수행도·태그·노트 (누적 이력은 보존)', admin:true},
  {id:'all-progress', icon:'📊', label:'전체 진도 삭제',   desc:'모든 강사 진도·과제',           admin:true},
  {id:'assignments',  icon:'👤', label:'강사 배정 초기화', desc:'모든 강사 수업 배정 삭제',      admin:true},
  {id:'config',       icon:'💥', label:'강사 & 설정 삭제', desc:'강사·문구·설정 (학생 명단·관찰 이력·성적은 보존 — Analyzer 원료 불가침)', admin:true},
];
function _renderResetHtml(){
  const hasAdmin=adminOn;
  // 일반(강사 단위) 초기화는 담당수업(assignments) 기준 — 담당 없는 계정(운영자)은 no-op이므로 미노출
  const normalItems=(instructor?.assignments||[]).length?_RESET_ITEMS.filter(it=>!it.admin):[];
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
  // 실제 렌더는 설정 탭(stg-pane) — 구 아코디언(#sa-reset)은 사문. 탭 컨테이너 우선 갱신.
  const body=document.querySelector('.stg-pane[data-stg="reset"] .stg-card-b')||document.querySelector('#sa-reset .sa-body');
  if(body)body.innerHTML=_renderResetHtml();
}
async function _doResetPresets(){
  const def=_defaultPresets();
  if(instructor){instructor.presets=[...def];}
  if(dbUrl&&dbPath&&instructor?.id){
    await fbPatch(`config/instructors/${instructor.id}`,{presets:def}).catch(fbFail('문구'));
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
    if(sel.includes('input')){
      const asgns=instructor?.assignments||[];
      for(const a of asgns){
        const students=(config?._classStudents||{})[a.classId]||[];
        for(const s of students){ if(inputData[s.nameKey]){delete inputData[s.nameKey][a.subject];delete inputData[s.nameKey]['__note__'];} }
      }
    }
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
      // 로컬 inputData는 중첩 구조(input[nameKey][subject] / input[nameKey].__note__) — 평면키 삭제 금지
      const asgns=instructor?.assignments||[];
      const noteDone=new Set();
      for(const a of asgns){
        const students=(config?._classStudents||{})[a.classId]||[];
        for(const s of students){
          if(inputData[s.nameKey])delete inputData[s.nameKey][a.subject];
          ops.push(fbPut(`input/${s.nameKey}/${a.subject}`,null).catch(fbFail('초기화')));
          if(!noteDone.has(s.nameKey)){noteDone.add(s.nameKey);
            if(inputData[s.nameKey])delete inputData[s.nameKey]['__note__'];   // 특이사항 메모(학생별 단일)
            ops.push(fbPut(`input/${s.nameKey}/__note__`,null).catch(fbFail('초기화')));}
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
    if(sel.includes('all-input')){
      // Analyzer 스탯 원료 불가침: obs 누적은 절대 통삭제하지 않는다 — 오늘 날짜키만 전 학생 정리.
      // (기존 fbPut('obs',null)은 전체 관찰 이력을 파괴해 월간 리포트 원료를 소멸시키던 위험 동작)
      inputData={};
      ops.push(fbPut('input',null));
      const dk=todayKey();
      const obsAll=await fbGet('obs').catch(()=>null);
      if(obsAll&&typeof obsAll==='object'){
        for(const[nk,subjMap] of Object.entries(obsAll)){
          if(!subjMap||typeof subjMap!=='object')continue;
          for(const subj of Object.keys(subjMap)){
            if(subjMap[subj]&&subjMap[subj][dk]!==undefined){
              ops.push(fbPatch(`obs/${nk}/${subj}`,{[dk]:null}).catch(fbFail('초기화')));
              if(tagData?.[nk]?.[subj]?.[dk])delete tagData[nk][subj][dk];
            }
          }
        }
      }
    }
    if(sel.includes('all-progress')){progressData={};ops.push(fbPut('session',null));}
    if(sel.includes('assignments')){
      const instrs=await fbGet('config/instructors').catch(()=>null);
      if(instrs)for(const id of Object.keys(instrs))ops.push(fbPatch(`config/instructors/${id}`,{assignments:[]}).catch(fbFail('초기화')));
    }
    if(sel.includes('config')){
      // 학생 명단(students/)은 삭제하지 않는다 — 이력(obs/history)의 이름 해석 원료.
      // 명단 관리는 ClassManager 소관. (기존 fbPut('students',null) 제거)
      ops.push(fbPut('config',null));ops.push(fbPut('input',null));ops.push(fbPut('session',null));
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
// 강사 생성·전환·삭제(createI·switchInstr·rmInstr·loadInstrsSection)는 CampusManager 전담으로 이관 — DRW서 제거(이중 관리 방지).

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
  if(dbUrl&&dbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{presets:instructor.presets}).catch(fbFail('문구'));
  renderMain();
}
function rmPreset(i){
  if(!instructor?.presets)return;
  if(!confirm(`"${instructor.presets[i]}" 프리셋을 삭제합니까?`))return;
  instructor.presets.splice(i,1);saveLocal();
  if(dbUrl&&dbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{presets:instructor.presets}).catch(fbFail('문구'));
  renderMain();
}

function toggleAcc(hdr,classId){
  const body=hdr.nextElementSibling;
  const arrow=hdr.querySelector('.acc-arr');
  const open=body.classList.toggle('open');
  if(arrow)arrow.textContent=open?'▼':'▶';
  if(classId!==undefined)clsAccOpen[classId]=open; // 세션 보존 — renderMain 재빌드 시 복원
}

// ══════════════════════════════════════════════════════════
//  강사 계정 관리 (CM 통폐합 — 매니저/운영자 전용, Cloud Functions)
// ══════════════════════════════════════════════════════════
function _accGenPw(){ const c='ABCDEFGHJKMNPQRSTUVWXYZ23456789'; let s=''; for(let i=0;i<8;i++)s+=c[Math.floor(Math.random()*c.length)]; return s; }
function _accIsAdmin(){ return ['admin','super'].includes(instructor?.role); }
async function _aclAll(){
  try{ const r=await fetch(dbUrl.replace(/\/$/,'')+'/acl.json?auth='+encodeURIComponent(window.__AUTH_TOKEN__||'')); return r.ok?((await r.json())||{}):{}; }
  catch(_){ return {}; }
}
async function _aclPut(uid,field,val){
  const r=await fetch(`${dbUrl.replace(/\/$/,'')}/acl/${encodeURIComponent(uid)}/${field}.json?auth=${encodeURIComponent(window.__AUTH_TOKEN__||'')}`,
    {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(val)});
  if(!r.ok) throw new Error('변경 실패 '+r.status);
}
// ── 학생 명단 탭 (CampusManager 포팅: 2-pane M/T 그룹 토글 + 학생 테이블) ──────
//   스키마: students/{nameKey}={name,class} · classes/{id}={group:'M'|'T',courses}
let _rs={group:'M',sel:null,classes:{},students:{}};
async function renderStudents(mc){
  if(!_isMgr()){ activeTab='input'; renderMain(); return; }
  mc.innerHTML=makeTb('학생 명단','반·학생 추가·편집 (관리자)')+`
    <div class="rs-wrap">
      <div class="rs-head"><span class="rs-cnt" id="rsCnt">불러오는 중…</span>
        <span class="rs-sp"><button class="btn bsm" id="rsAddCls">+ 반 추가</button><button class="btn bsm bp" id="rsAddStu">+ 학생 추가</button></span></div>
      <div class="rs-grid">
        <div class="rs-panel"><div class="rs-gtog"><button id="rsGM">M반</button><button id="rsGT">T반</button></div><div class="rs-clist" id="rsClist"></div></div>
        <div class="rs-panel" id="rsSpanel"></div>
      </div>
    </div>`;
  try{ const [cls,stu]=await Promise.all([fbGet('classes').catch(()=>null),fbGet('students').catch(()=>null)]);
       _rs.classes=cls||{}; _rs.students=stu||{}; }
  catch(_){ _rs.classes=config?.classes||{}; _rs.students={}; }
  document.getElementById('rsAddCls').onclick=rsAddCls;
  document.getElementById('rsAddStu').onclick=()=>rsEditStu(null);
  document.getElementById('rsGM').onclick=()=>{_rs.group='M';_rs.sel=null;_rsDraw();};
  document.getElementById('rsGT').onclick=()=>{_rs.group='T';_rs.sel=null;_rsDraw();};
  _rsDraw();
}
function _rsInClass(c){ return Object.values(_rs.students).filter(s=>s&&s.class===c).length; }
function _rsUnassigned(){ return Object.entries(_rs.students).filter(([k,s])=>!s||!s.class||!_rs.classes[s.class]); }
function _rsDraw(){
  document.getElementById('rsCnt').textContent=`학생 ${Object.keys(_rs.students).length}명 · 반 ${Object.keys(_rs.classes).length}개`;
  document.getElementById('rsGM').className=_rs.group==='M'?'on':'';
  document.getElementById('rsGT').className=_rs.group==='T'?'on':'';
  const cs=Object.entries(_rs.classes).filter(([id,c])=>((c&&c.group)||'M')===_rs.group);
  if(!_rs.sel||(_rs.sel!=='__un__'&&!_rs.classes[_rs.sel]))_rs.sel=cs.length?cs[0][0]:'__un__';
  const clist=document.getElementById('rsClist');
  clist.innerHTML=cs.map(([id])=>`<div class="rs-ci${_rs.sel===id?' on':''}" data-c="${esc(id)}">${esc(id)}<span class="rs-n">${_rsInClass(id)}</span></div>`).join('')
    +`<div class="rs-ci rs-un${_rs.sel==='__un__'?' on':''}" data-c="__un__">⚠ 무소속<span class="rs-n">${_rsUnassigned().length}</span></div>`;
  clist.querySelectorAll('.rs-ci').forEach(el=>el.onclick=()=>{_rs.sel=el.dataset.c;_rsDraw();});
  const list=(_rs.sel==='__un__'?_rsUnassigned():Object.entries(_rs.students).filter(([k,s])=>s&&s.class===_rs.sel))
    .sort((a,b)=>String(a[1]?.name||'').localeCompare(String(b[1]?.name||''),'ko'));
  const isCls=_rs.sel!=='__un__';
  const sp=document.getElementById('rsSpanel');
  sp.innerHTML=`<div class="rs-sphd"><span class="rs-spttl">${isCls?esc(_rs.sel):'무소속'} · ${list.length}명</span>${isCls?`<span class="rs-spact"><button class="rs-abtn" id="rsRen">반 이름 변경</button><button class="rs-abtn del" id="rsDelC">반 삭제</button></span>`:''}</div>`
    +(list.length?`<table class="rs-tbl"><thead><tr><th>출결번호</th><th>이름</th><th>반</th><th>작업</th></tr></thead><tbody>`
      +list.map(([k,s])=>{const assigned=s.class&&_rs.classes[s.class];return `<tr><td class="rs-num">${esc(k)}</td><td><b>${esc(s.name||'')}</b></td><td>${esc(s.class||'무소속')}</td><td class="rs-act"><button data-edit="${esc(k)}">편집</button>${assigned?`<button class="del x" data-del="${esc(k)}" title="반에서 빼기(무소속)">✕</button>`:`<button class="del" data-del="${esc(k)}">영구삭제</button>`}</td></tr>`;}).join('')
      +`</tbody></table>`:`<div class="rs-empty">학생이 없습니다.</div>`);
  sp.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>rsEditStu(b.dataset.edit));
  sp.querySelectorAll('[data-del]').forEach(b=>b.onclick=()=>rsDelStu(b.dataset.del));
  if(isCls){ document.getElementById('rsRen').onclick=()=>rsRenameCls(_rs.sel); document.getElementById('rsDelC').onclick=()=>rsDelCls(_rs.sel); }
}
function _rsClsOpts(cur){ return Object.keys(_rs.classes).map(id=>`<option value="${esc(id)}"${id===cur?' selected':''}>${esc(id)}</option>`).join('')+`<option value=""${!cur?' selected':''}>무소속</option>`; }
function rsEditStu(key){
  const s=key?_rs.students[key]:null;
  _rpModal(`<h3>${key?'학생 편집':'학생 추가'}</h3>
    <label class="rp-flbl">출결번호 (nameKey)</label><input class="rp-fin" id="rs-key" value="${key?esc(key):''}" ${key?'disabled':''} inputmode="numeric" placeholder="예: 1024">
    <label class="rp-flbl">이름</label><input class="rp-fin" id="rs-name" value="${s?esc(s.name||''):''}">
    <label class="rp-flbl">반</label><select class="rp-fin" id="rs-cls">${_rsClsOpts(s?s.class:(_rs.sel==='__un__'?'':_rs.sel))}</select>
    <div class="rp-mrow"><button class="rp-btn ghost" onclick="closeRpModal()">취소</button><button class="rp-btn" id="rs-ok">저장</button></div>`);
  setTimeout(()=>document.getElementById(key?'rs-name':'rs-key')?.focus(),0);
  document.getElementById('rs-ok').onclick=async()=>{
    const k=(document.getElementById('rs-key').value||'').trim(),nm=(document.getElementById('rs-name').value||'').trim(),cl=document.getElementById('rs-cls').value||null;
    if(!k||!nm)return toast('출결번호·이름을 입력하세요');
    if(!key&&_rs.students[k])return toast('이미 있는 출결번호입니다');
    try{ await fbPut('students/'+encodeURIComponent(k),{name:nm,class:cl}); _rs.students[k]={name:nm,class:cl}; if(cl)_rs.sel=cl; closeRpModal(); toast('저장됨 ✅'); _rsSyncConfig(); _rsDraw(); }
    catch(e){ toast('저장 실패: '+e,4000); }
  };
}
async function rsDelStu(k){
  const s=_rs.students[k]; if(!s)return;
  const assigned=s.class&&_rs.classes[s.class];
  if(assigned){
    if(!confirm(`'${s.name}' 학생을 '${s.class}'에서 빼서 무소속으로 옮길까요?`))return;
    try{ await fbPut('students/'+encodeURIComponent(k),{name:s.name,class:null}); _rs.students[k]={name:s.name,class:null}; toast('무소속으로 이동'); _rsSyncConfig(); _rsDraw(); }catch(e){ toast(e.message||String(e)); }
  }else{
    if(!confirm(`'${s.name}' 학생을 완전히 삭제할까요? (되돌릴 수 없음)`))return;
    try{ await fbPut('students/'+encodeURIComponent(k),null); delete _rs.students[k]; toast('삭제됨'); _rsSyncConfig(); _rsDraw(); }catch(e){ toast(e.message||String(e)); }
  }
}
function rsAddCls(){
  _rpModal(`<h3>반 추가</h3>
    <label class="rp-flbl">반 이름</label><input class="rp-fin" id="rs-cid" placeholder="예: 중1A">
    <label class="rp-flbl">그룹</label><select class="rp-fin" id="rs-cgrp"><option value="M"${_rs.group==='M'?' selected':''}>M반 (월수금)</option><option value="T"${_rs.group==='T'?' selected':''}>T반 (화목토)</option></select>
    <div class="rp-mrow"><button class="rp-btn ghost" onclick="closeRpModal()">취소</button><button class="rp-btn" id="rs-cok">추가</button></div>`);
  setTimeout(()=>document.getElementById('rs-cid')?.focus(),0);
  document.getElementById('rs-cok').onclick=async()=>{
    const id=(document.getElementById('rs-cid').value||'').trim(); if(!id)return toast('반 이름을 입력하세요');
    if(_rs.classes[id])return toast('이미 있는 반입니다');
    const grp=document.getElementById('rs-cgrp').value;
    try{ await fbPut('classes/'+encodeURIComponent(id),{group:grp,courses:{}}); _rs.classes[id]={group:grp,courses:{}}; _rs.group=grp;_rs.sel=id; closeRpModal(); toast(`${id} 추가됨 ✅`); _rsSyncConfig(); _rsDraw(); }
    catch(e){ toast('추가 실패: '+e,4000); }
  };
}
async function rsDelCls(id){
  const n=_rsInClass(id);
  if(!confirm(`'${id}' 반을 삭제할까요?${n?`\n소속 학생 ${n}명은 무소속으로 이동됩니다(데이터 보존).`:''}`))return;
  try{
    for(const [k,s] of Object.entries(_rs.students))if(s&&s.class===id){ await fbPut('students/'+encodeURIComponent(k),{name:s.name,class:null}); _rs.students[k]={name:s.name,class:null}; }
    await fbPut('classes/'+encodeURIComponent(id),null); delete _rs.classes[id];
    _rs.sel=null; toast(`${id} 반 삭제 (학생 ${n}명 무소속 이동)`); _rsSyncConfig(); _rsDraw();
  }catch(e){ toast(e.message||String(e)); }
}
function rsRenameCls(oldId){
  _rpModal(`<h3>반 이름 변경</h3>
    <label class="rp-flbl">새 반 이름</label><input class="rp-fin" id="rs-rid" value="${esc(oldId)}">
    <div class="rp-hint">소속 학생·진도/과제·성적·강사 담당배정이 함께 이동합니다. 주기적 개편용 — 실행 전 백업 권장.</div>
    <div class="rp-mrow"><button class="rp-btn ghost" onclick="closeRpModal()">취소</button><button class="rp-btn" id="rs-rok">변경</button></div>`);
  setTimeout(()=>{const i=document.getElementById('rs-rid');if(i){i.focus();i.select();}},0);
  document.getElementById('rs-rok').onclick=async()=>{
    const nv=(document.getElementById('rs-rid').value||'').trim();
    if(!nv||nv===oldId)return closeRpModal();
    if(_rs.classes[nv])return toast('이미 있는 반 이름입니다');
    const btn=document.getElementById('rs-rok'); btn.disabled=true; btn.textContent='이동 중…';
    try{ await _rsMigrate(oldId,nv); closeRpModal(); _rs.sel=nv; toast(`'${oldId}' → '${nv}' 변경 완료`); await renderStudents(document.getElementById('mc')); }
    catch(e){ toast('변경 실패: '+(e.message||e)); btn.disabled=false; btn.textContent='변경'; }
  };
}
// 반 키 마이그레이션 — classes·students·session/class_data·scores·강사 담당배정 일괄 이동
async function _rsMigrate(oldId,newId){
  const enc=encodeURIComponent;
  await fbPut('classes/'+enc(newId), _rs.classes[oldId]||{group:_rs.group,courses:{}});
  const stu=await fbGet('students').catch(()=>null)||{};
  for(const [k,s] of Object.entries(stu))if(s&&s.class===oldId)await fbPatch('students/'+enc(k),{class:newId});
  const sess=await fbGet('session/class_data').catch(()=>null)||{};
  for(const [key,val] of Object.entries(sess)){ const parts=key.split('|'); if(parts[0]===oldId){ const nk=newId+'|'+parts.slice(1).join('|'); await fbPut('session/class_data/'+enc(nk),val); await fbPut('session/class_data/'+enc(key),null); } }
  const sc=await fbGet('scores/weekly/'+enc(oldId)).catch(()=>null);
  if(sc){ await fbPut('scores/weekly/'+enc(newId),sc); await fbPut('scores/weekly/'+enc(oldId),null); }
  const instrs=await fbGet('config/instructors').catch(()=>null)||{};
  for(const [nm,info] of Object.entries(instrs)){ const as=info&&info.assignments; if(Array.isArray(as)){ let ch=false; as.forEach(a=>{if(a&&a.classId===oldId){a.classId=newId;ch=true;}}); if(ch)await fbPatch('config/instructors/'+enc(nm),{assignments:as}); } }
  await fbPut('classes/'+enc(oldId),null);
}
// _rs 변경분을 DRW 인메모리(config)로 반영 — 입력·성적·사이드바 일관성
function _rsSyncConfig(){
  config=config||{classes:{},instructors:{}};
  config.classes=JSON.parse(JSON.stringify(_rs.classes));
  const cs={}; for(const [k,v] of Object.entries(_rs.students)){ const cid=v&&v.class; if(cid){ (cs[cid]=cs[cid]||[]).push({nameKey:k,...v}); } }
  config._classStudents=cs;
  try{ saveLocal(); }catch(_){}
  try{ if(typeof renderSb==='function')renderSb(); }catch(_){}
}

function renderAccounts(mc){
  if(!_isMgr()){ activeTab='input'; renderMain(); return; }
  mc.innerHTML=makeTb('강사 계정','발급·비활성·비번 리셋·삭제 (관리자 전용)')+`
    <div style="padding:16px 18px;max-width:760px">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
        <b style="font-size:13px">계정 발급</b>
        <input class="rp-ta" id="ac-name" placeholder="강사 이름" style="min-height:0;height:34px;flex:1;max-width:160px">
        ${_accIsAdmin()?`<select class="bulk-tsel-like" id="ac-role" style="height:34px;border:1px solid var(--border);border-radius:8px;padding:0 8px"><option value="instructor">강사</option><option value="manager">관리자</option></select>`:''}
        <input class="rp-ta" id="ac-pw" value="${_accGenPw()}" readonly style="min-height:0;height:34px;width:96px;font-family:monospace">
        <button class="rp-btn ghost" onclick="document.getElementById('ac-pw').value=_accGenPw()" title="임시비번 재생성">↻</button>
        <button class="rp-btn" onclick="accCreate()">발급</button>
      </div>
      <div id="ac-list"><div class="rp-hint" style="padding:12px">불러오는 중…</div></div>
    </div>`;
  loadAccounts();
}
async function loadAccounts(){
  const el=document.getElementById('ac-list'); if(!el)return;
  const isAdmin=_accIsAdmin(), myCampus=instructor?.campus||'';
  const all=await _aclAll();
  const mine=Object.entries(all).filter(([u,a])=> a && a.role!=='admin' && a.role!=='super'
    && (isAdmin ? (a.role==='instructor'||a.role==='manager') : (a.role==='instructor' && a.campus===myCampus)));
  if(!mine.length){ el.innerHTML='<div class="rp-hint" style="padding:12px">계정이 없습니다. 위에서 발급하세요.</div>'; return; }
  el.innerHTML=`<table style="width:100%;border-collapse:collapse;font-size:12.5px">
    <thead><tr style="text-align:left;color:var(--sub);font-size:11px">
      <th style="padding:7px 8px">이름</th><th>역할</th><th>상태</th>${isAdmin?'<th>캠퍼스</th>':''}<th style="text-align:right;padding-right:8px">작업</th></tr></thead>
    <tbody>${mine.map(([uid,a])=>`<tr style="border-top:1px solid var(--line-soft)">
      <td style="padding:7px 8px;font-weight:700">${esc(a.instructorId||'?')}</td>
      <td><span class="rp-badge ${a.role==='manager'?'ok':'no'}">${a.role==='manager'?'관리자':'강사'}</span></td>
      <td><span class="rp-badge ${a.active?'ok':'no'}">${a.active?'활성':'비활성'}</span></td>
      ${isAdmin?`<td style="color:var(--sub)">${esc(a.campus||'')}</td>`:''}
      <td style="text-align:right;padding-right:8px;white-space:nowrap">
        ${isAdmin?`<button class="rp-btn ghost" style="padding:3px 8px;font-size:11px" onclick="accRole('${esc(uid)}','${a.role==='manager'?'instructor':'manager'}')">${a.role==='manager'?'강사로':'관리자로'}</button>`:''}
        <button class="rp-btn ghost" style="padding:3px 8px;font-size:11px" onclick="accToggle('${esc(uid)}',${!a.active})">${a.active?'비활성':'활성화'}</button>
        <button class="rp-btn ghost" style="padding:3px 8px;font-size:11px" onclick="accReset('${esc(uid)}','${esc(a.instructorId||'')}')">비번 리셋</button>
        <button class="rp-btn ghost" style="padding:3px 8px;font-size:11px;color:var(--red)" onclick="accDel('${esc(uid)}','${esc(a.instructorId||'')}')">삭제</button>
      </td></tr>`).join('')}</tbody></table>`;
}
async function accCreate(){
  const name=(document.getElementById('ac-name').value||'').trim(); if(!name){toast('이름을 입력하세요');return;}
  const pw=document.getElementById('ac-pw').value;
  const role=document.getElementById('ac-role')?document.getElementById('ac-role').value:'instructor';
  try{ await window.__drwCallFn('createInstructor',{campus:instructor?.campus,name,password:pw,role}); toast(`${name} 발급 — 임시비번 ${pw}`); loadAccounts(); document.getElementById('ac-name').value=''; document.getElementById('ac-pw').value=_accGenPw(); }
  catch(e){ toast(e.message||String(e)); }
}
async function accToggle(uid,active){ try{ await _aclPut(uid,'active',active===true); toast(active?'활성화':'비활성(즉시 차단)'); loadAccounts(); }catch(e){ toast(e.message||String(e)); } }
async function accRole(uid,role){ try{ await _aclPut(uid,'role',role); toast(role==='manager'?'관리자로 지정':'강사로 변경'); loadAccounts(); }catch(e){ toast(e.message||String(e)); } }
async function accReset(uid,name){ const np=_accGenPw(); if(!confirm(`${name} 비번을 임시비번으로 초기화할까요?\n새 임시비번: ${np}\n(첫 로그인 시 변경 강제)`))return; try{ await window.__drwCallFn('resetInstructorPassword',{uid,newPassword:np}); toast(`${name} 임시비번: ${np}`); }catch(e){ toast(e.message||String(e)); } }
async function accDel(uid,name){ if(!confirm(`${name} 계정을 영구 삭제할까요?\nAuth+권한 제거 — 되돌릴 수 없습니다.`))return; try{ await window.__drwCallFn('deleteInstructor',{uid}); toast(`${name} 삭제됨`); loadAccounts(); }catch(e){ toast(e.message||String(e)); } }
