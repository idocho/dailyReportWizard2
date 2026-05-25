
// ══════════════════════════════════════════════════════════
//  설정
// ══════════════════════════════════════════════════════════
function _saToggle(id){
  const hdr=document.querySelector(`#${id}>.sa-hdr`);
  const body=document.querySelector(`#${id}>.sa-body`);
  if(!hdr||!body)return;
  const open=body.classList.toggle('open');
  hdr.classList.toggle('open',open);
  if(open)openSaIds.add(id);else openSaIds.delete(id); // 재렌더 후 복원용
}
function _saOpen(id){
  const hdr=document.querySelector(`#${id}>.sa-hdr`);
  const body=document.querySelector(`#${id}>.sa-body`);
  if(!hdr||!body)return;
  hdr.classList.add('open');body.classList.add('open');
  openSaIds.add(id); // 재렌더 후 복원용
}

function renderSettings(mc){
  renderMhdr('설정');
  if(cfg)_ensureConfigShape();
  const instr=instructor||{};

  // ── 내 계정 상태 요약 ──
  const acctSub=instr.name?`<span class="sa-sub">${esc(instr.name)}</span>`:`<span class="sa-sub" style="color:var(--red)">미설정</span>`;

  // ── 담당 수업 rows ──
  const asgns=instr.assignments||[];
  const asgRows=!asgns.length
    ?`<div style="padding:10px 12px;font-size:12px;color:var(--gray)">담당 수업이 없습니다.</div>`
    :`<div class="ar" style="grid-template-columns:1fr 1fr 52px 30px;background:#F8FAFC;font-size:10px;font-weight:700;color:var(--sub)"><span>반</span><span>교재</span><span>역할</span><span></span></div>`
      +asgns.map((a,i)=>`<div class="ar" style="grid-template-columns:1fr 1fr 52px 30px"><span style="font-weight:700">${esc(a.cls)}</span><span style="color:var(--sub);font-size:11px">${esc(a.tb)}</span><span style="font-size:10px;color:var(--indigo)">${esc(a.role||'담임')}</span><button style="background:none;border:none;cursor:pointer;color:var(--red);font-size:14px;padding:0" onclick="removeA(${i})">✕</button></div>`).join('');
  let addAsgn='';
  if(cfg){
    let clsOpts='<option value="">-- 반 선택 --</option>',firstSh='',firstCls='';
    for(const[sh,shD]of Object.entries(cfg.sheets||{})){for(const[cls]of Object.entries(shD.classes||{})){if(!firstSh){firstSh=sh;firstCls=cls;}clsOpts+=`<option value="${esc(sh)}|${esc(cls)}">${esc(cls)}</option>`;}}
    const tbOpts=firstSh?('<option value="">-- 교재 선택 --</option>'+[...(cfg?.sheets?.[firstSh]?.classes?.[firstCls]?.textbooks||[])].sort((a,b)=>a.localeCompare(b,'ko')).map(t=>`<option>${esc(t)}</option>`).join('')):''
    addAsgn=`<div style="padding:10px 12px;border-top:1px solid var(--border)"><div style="font-size:11px;font-weight:700;color:var(--sub);margin-bottom:8px">수업 추가</div><div style="display:grid;grid-template-columns:1fr 1fr 72px;gap:6px;margin-bottom:8px"><div><div class="sl">반</div><select class="inp sm" id="aCls" onchange="onCC()">${clsOpts}</select></div><div><div class="sl">교재</div><select class="inp sm" id="aTb">${tbOpts}</select></div><div><div class="sl">역할</div><select class="inp sm" id="aRole"><option>담임</option><option>부담임</option></select></div></div><button class="btn bsm" onclick="addA()">+ 추가</button></div>`;
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

  // ── 관리자: 교재 목록 관리 (교재명 레지스트리 — 학년학기 무관) ──
  const tbMgmtHtml = adminOn ? (()=>{
    const tbMap = cfg ? _ensureTextbookRegistry() : {};
    const tbNames = Object.keys(tbMap).sort((a,b)=>a.localeCompare(b,'ko'));
    const tbRows = tbNames.map(name=>`<div style="display:flex;align-items:center;padding:6px 12px;border-bottom:1px solid var(--border);gap:8px">
        <span style="flex:1;font-size:12px;font-weight:600">${esc(name)}</span>
        <span class="chip" style="flex-shrink:0" onclick="rmTextbook('${esc(name)}')">${'×'}</span>
      </div>`).join('')||'<div style="padding:8px 12px;font-size:11px;color:var(--gray)">등록된 교재 없음</div>';
    return `<div class="sa admin-sec" id="sa-tbmgmt">
      <div class="sa-hdr${openSaIds.has('sa-tbmgmt')?' open':''}" onclick="_saToggle('sa-tbmgmt')">
        <span class="sa-ico">📖</span>
        <span class="sa-lbl">교재 목록 관리</span>
        <span style="font-size:10px;background:#FEF3C7;color:#92400E;border-radius:8px;padding:1px 6px;font-weight:700;margin-right:4px">관리자</span>
        <span class="sa-chv">›</span>
      </div>
      <div class="sa-body${openSaIds.has('sa-tbmgmt')?' open':''}">
        ${tbRows}
        <div style="padding:8px 12px;display:flex;gap:6px;border-top:1px solid var(--border)">
          <input class="inp sm" id="tb-name-inp" placeholder="교재명" style="flex:1" onkeydown="if(event.key==='Enter')addTextbook()">
          <button class="btn bsm" onclick="addTextbook()">+ 등록</button>
        </div>
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
        <span class="sa-sub">${fbUrl?'연결됨 ✓':'미설정'}</span>
        <span class="sa-chv">›</span>
      </div>
      <div class="sa-body${openSaIds.has('sa-fb')?' open':''}">
        <div class="sr"><div class="sl">DB URL</div><input class="inp" id="sUrl" value="${esc(fbUrl)}" placeholder="https://your-project.firebaseio.com" type="url" onkeydown="if(event.key==='Enter')saveFb()"></div>
        <div class="sr"><div class="sl">경로 (Secret Path)</div><input class="inp" id="sPth" value="${esc(fbPath)}" placeholder="drw_a7f3k9x2" onkeydown="if(event.key==='Enter')saveFb()"></div>
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
        <div style="padding:4px 14px 10px;font-size:11px;color:var(--sub)">이름 그대로 Firebase 키로 사용됩니다 (예: <code>instructors/홍길동</code>)</div>
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
        <span class="sa-sub">${cfg?Object.values(cfg.sheets||{}).reduce((n,s)=>n+Object.keys(s.classes||{}).length,0)+'개 학급':'–'}</span>
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

  setSync(!!fbUrl&&!!fbPath);
  if(adminOn)loadInstrsSection();
  // 미로그인 시 내 계정 섹션 자동 열기
  if(!instr.name)_saOpen('sa-acct');
}

// ══════════════════════════════════════════════════════════
//  학급 관리 — 2단계 드릴다운
// ══════════════════════════════════════════════════════════
function renderClsMgmt(){
  if(clsDrillSh===null)return renderClsMgmtTop();
  return renderClsMgmtSheet(clsDrillSh);
}

function renderClsMgmtTop(){
  if(!cfg)return `<div class="card"><div class="sh">🏫 학급 &amp; 학생 관리</div><div style="padding:10px 12px;font-size:12px;color:var(--gray)">학생 명단을 먼저 불러오세요.</div></div>`;
  _ensureConfigShape();

  // 내 담당 학급 (assignments 기반)
  const myClsSet=new Set((instructor?.assignments||[]).map(a=>`${a.sheet}|${a.cls}`));
  let myRows='';
  for(const[sh,shD]of Object.entries(cfg.sheets||{})){
    for(const[cls,clsD]of Object.entries(shD.classes||{})){
      if(myClsSet.has(`${sh}|${cls}`)){
        const myRole=(instructor?.assignments||[]).find(a=>a.sheet===sh&&a.cls===cls)?.role||'담임';
        myRows+=buildClsAccordion(sh,cls,clsD,myRole);
      }
    }
  }

  // 전체 시트 드릴다운 버튼
  const sheets=['M','T',...Object.keys(cfg.sheets||{}).filter(sh=>!['M','T'].includes(sh))];
  const drillBtns=sheets.map(sh=>{
    const cnt=Object.keys(cfg.sheets[sh]?.classes||{}).length;
    return `<div class="drill-btn" onclick="clsDrillSh='${esc(sh)}';openSaIds.add('sa-cls');renderMain()">
      <div style="width:32px;height:32px;border-radius:8px;background:var(--indigo-l);display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0">📂</div>
      <div style="flex:1"><div style="font-size:13px;font-weight:700">${esc(sh)}반</div><div style="font-size:11px;color:var(--gray)">${cnt}개 학급</div></div>
      <span style="color:var(--gray);font-size:14px;font-weight:300">›</span>
    </div>`;
  }).join('');

  return `<div class="card">
    <div class="sh">🏫 학급 &amp; 학생 관리</div>
    <div class="sh2">내 담당 학급</div>
    ${myRows||'<div style="padding:8px 12px;font-size:11px;color:var(--gray)">담당 수업을 추가하면 여기에 표시됩니다.</div>'}
    <div class="sh2">전체 학급 탐색</div>
    ${drillBtns||'<div style="padding:8px 12px;font-size:11px;color:var(--gray)">등록된 시트가 없습니다.</div>'}
  </div>`;
}

function renderClsMgmtSheet(sh){
  if(!cfg)return '';
  _ensureConfigShape();
  const shD=cfg.sheets?.[sh]||{classes:{}};
  const shClasses=Object.entries(shD.classes||{});
  let rows='';
  for(const[cls,clsD]of shClasses){
    const myRole=(instructor?.assignments||[]).find(a=>a.sheet===sh&&a.cls===cls)?.role||null;
    rows+=buildClsAccordion(sh,cls,clsD,myRole);
  }
  return `<div class="card">
    <div class="sh" style="display:flex;align-items:center;gap:8px;padding:7px 10px 7px 14px">
      <button class="btn bsm" onclick="clsDrillSh=null;renderMain()" style="flex-shrink:0;font-size:11px">← 뒤로</button>
      <span style="flex:1">🏫 ${esc(sh)}반 학급 관리</span>
    </div>
    ${rows||'<div style="padding:8px 12px;font-size:11px;color:var(--gray)">학급이 없습니다.</div>'}
    <div style="padding:10px 12px;border-top:1px solid var(--border)">
      <button class="btn bsm" onclick="addCls('${esc(sh)}')">+ ${esc(sh)}반 학급 추가</button>
    </div>
  </div>`;
}

function buildClsAccordion(sh,cls,clsD,myRole){
  const sts=clsD.students||[],tbs=clsD.textbooks||[];
  const isSub=myRole==='부담임';
  const subBadge=isSub?`<span style="font-size:9px;background:#FEF3C7;color:#92400E;border-radius:8px;padding:1px 6px;font-weight:700;flex-shrink:0">부담임</span>`:'';
  // data-sh / data-cls 어트리뷰트로 식별 — 한글 등 특수문자 클래스명의 clsKey 충돌 방지
  const stuChips=sts.map(s=>`<span class="chip" onclick="rmStu('${esc(sh)}','${esc(cls)}','${esc(s.name)}')">${esc(s.name)} <span>×</span></span>`).join('');
  const tbChips=tbs.map(t=>{const gs=getTbGrade(sh,cls,t)||'';const gsLabel=gs?(GRADE_SEM_LIST.find(g=>g.val===gs)?.label||gs):'';return`<span class="chip" onclick="rmTb('${esc(sh)}','${esc(cls)}','${esc(t)}')">${gsLabel?`<span style="color:var(--indigo);font-size:9px;font-weight:700;margin-right:3px">${esc(gsLabel)}</span>`:`<span style="color:var(--red);font-size:9px;margin-right:3px">미설정</span>`}${esc(t)} <span style="display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px;margin-left:4px;border-radius:50%;background:#FEE2E2;color:#B91C1C;font-size:10px;font-weight:700;line-height:1">×</span></span>`;}).join('');
  return `<div style="border-bottom:1px solid var(--border)">
    <div class="acc-hdr" onclick="toggleAcc(this)">
      <span class="acc-arr" style="font-size:10px;color:var(--gray);width:14px;flex-shrink:0">▶</span>
      <span style="font-size:13px;font-weight:700;flex:1">${esc(cls)}</span>
      ${subBadge}
      <span style="font-size:10px;color:var(--gray);margin:0 6px;white-space:nowrap">학생 ${sts.length} · 교재 ${tbs.length}</span>
      <button class="btn br bsm" onclick="rmCls('${esc(sh)}','${esc(cls)}');event.stopPropagation()" style="padding:2px 7px;font-size:11px;flex-shrink:0">✕</button>
    </div>
    <div class="acc-body">
      <div class="sl">학생</div>
      <div class="chips" data-sh="${esc(sh)}" data-cls="${esc(cls)}" data-chip-type="stu">${stuChips}<span class="chip" style="background:var(--indigo-l);border-color:var(--indigo);color:var(--indigo);cursor:pointer" onclick="addStuInline('${esc(sh)}','${esc(cls)}',this)">+ 추가</span></div>
      <div class="sl" style="margin-top:10px">교재</div>
      <div class="chips" data-sh="${esc(sh)}" data-cls="${esc(cls)}" data-chip-type="tb">${tbChips}<span class="chip" style="background:var(--indigo-l);border-color:var(--indigo);color:var(--indigo);cursor:pointer" onclick="addTbInline('${esc(sh)}','${esc(cls)}',this)">+ 교재 추가</span></div>
    </div>
  </div>`;
}

// ── 학생 인라인 추가 (아코디언 열림 상태 유지) ───────────────────
function addStuInline(sh,cls,btnEl){
  const chips=btnEl.parentElement;
  // 이미 입력 중이면 포커스만
  if(chips.querySelector('.stu-new-inp')){chips.querySelector('.stu-new-inp').focus();return;}

  const wrapper=document.createElement('span');
  wrapper.style.cssText='display:inline-flex;align-items:center;border:1px solid var(--indigo);border-radius:12px;padding:2px 6px;background:var(--indigo-l);gap:2px;vertical-align:middle;';
  const inp=document.createElement('input');
  inp.className='stu-new-inp';
  inp.style.cssText='border:none;background:transparent;font-size:11px;width:64px;color:var(--text);font-family:inherit;outline:none;';
  inp.placeholder='이름';
  const ok=document.createElement('span');
  ok.textContent='✓';
  ok.title='추가';
  ok.style.cssText='cursor:pointer;color:var(--indigo);font-weight:700;font-size:13px;line-height:1;padding:0 2px;';
  const cancel=document.createElement('span');
  cancel.textContent='×';
  cancel.style.cssText='cursor:pointer;color:var(--gray);font-size:13px;line-height:1;';
  cancel.onclick=()=>wrapper.remove();

  function doAdd(){
    const n=inp.value.trim();
    if(!n){wrapper.remove();return;}
    ensPath(sh,cls);
    cfg.sheets[sh].classes[cls].students.push({name:n});
    wrapper.remove();
    refreshStuChips(sh,cls);  // chips만 갱신 → 아코디언 열림 유지
    pushCfg();
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

// chips 영역만 새로 그리기 (전체 재렌더 없음)
function refreshStuChips(sh,cls){
  // data-sh/data-cls 어트리뷰트로 탐색 — clsKey(한글→_) 충돌 방지
  const sSh=sh.replace(/\\/g,'\\\\').replace(/"/g,'\\"');
  const sCls=cls.replace(/\\/g,'\\\\').replace(/"/g,'\\"');
  const el=document.querySelector(`[data-chip-type="stu"][data-sh="${sSh}"][data-cls="${sCls}"]`);
  if(!el)return;
  const sts=cfg.sheets?.[sh]?.classes?.[cls]?.students||[];
  const stuChips=sts.map(s=>`<span class="chip" onclick="rmStu('${esc(sh)}','${esc(cls)}','${esc(s.name)}')">${esc(s.name)} <span>×</span></span>`).join('');
  el.innerHTML=stuChips+`<span class="chip" style="background:var(--indigo-l);border-color:var(--indigo);color:var(--indigo);cursor:pointer" onclick="addStuInline('${esc(sh)}','${esc(cls)}',this)">+ 추가</span>`;
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
  if(fbUrl&&fbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{presets:instructor.presets}).catch(()=>{});
  toast('문구 수정됨 ✅');
  renderMain();
}

// ══════════════════════════════════════════════════════════
//  설정 저장 / 강사 / 학급 관리
// ══════════════════════════════════════════════════════════
function saveFb(){
  fbUrl=document.getElementById('sUrl')?.value.trim()||'';
  fbPath=document.getElementById('sPth')?.value.trim()||'';
  saveLocal();toast('Firebase 설정 저장됨 ✅');
}
// 이름 직접 입력 → Firebase 단건 조회
async function lookupInstr(){
  const name=(document.getElementById('acctName')?.value||'').trim();
  if(!name){toast('이름을 입력해 주세요.');return;}
  if(!fbUrl||!fbPath){toast('Firebase 연결 정보를 먼저 저장하세요.');return;}
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
  const saved=cfg?.presets?.['과제수행도'];
  return (saved&&saved.length>0)?saved:_HARDCODED_PRESETS;
}
async function _registerInstr(name){
  const defPresets=_defaultPresets();
  instructor={id:name,name,assignments:[],presets:defPresets};saveLocal();
  if(fbUrl&&fbPath)await fbPatch(`config/instructors/${encodeURIComponent(name)}`,{name,assignments:[],presets:defPresets}).catch(()=>{});
  renderSb();renderMain();toast(`${name} 등록됨 ✅ — 담당 수업·자주 쓰는 문구를 설정해 주세요`);
}

// 관리자 인증 (SHA-256 비교)
async function hashPw(pw){
  const buf=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(pw));
  return Array.from(new Uint8Array(buf)).map(b=>b.toString(16).padStart(2,'0')).join('');
}
async function toggleAdmin(){
  if(adminOn){
    adminOn=false;renderMain();return;
  }
  const pw=prompt('관리자 암호를 입력하세요');
  if(pw===null)return;
  const h=await hashPw(pw);
  if(h===ADMIN_HASH){adminOn=true;toast('관리자 모드 활성화 🔓');renderMain();}
  else toast('암호가 올바르지 않습니다.');
}

function onCC(){
  const s=document.getElementById('aCls');if(!s||!cfg)return;
  const[sh,cls]=s.value.split('|');
  const tbs=[...(cfg?.sheets?.[sh]?.classes?.[cls]?.textbooks||[])].sort((a,b)=>a.localeCompare(b,'ko'));
  const t=document.getElementById('aTb');if(t)t.innerHTML='<option value="">-- 교재 선택 --</option>'+tbs.map(x=>`<option>${esc(x)}</option>`).join('');
}
function addA(){
  if(!instructor){toast('먼저 계정을 설정해 주세요.');return;}
  const cs=document.getElementById('aCls'),ts=document.getElementById('aTb'),rs=document.getElementById('aRole');
  if(!cs||!ts)return;
  const val=cs.value;
  if(!val){toast('반을 선택해 주세요.');return;}
  const[sheet,cls]=val.split('|'),tb=ts.value,role=rs?.value||'담임';
  if(!sheet||!cls){toast('반을 선택해 주세요.');return;}
  if(!tb){toast('교재를 선택해 주세요.');return;}
  if(!instructor.assignments)instructor.assignments=[];
  if(instructor.assignments.some(a=>a.sheet===sheet&&a.cls===cls&&a.tb===tb)){toast('이미 추가된 수업입니다.');return;}
  instructor.assignments.push({sheet,cls,tb,role});saveLocal();
  if(fbUrl&&fbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{assignments:instructor.assignments}).catch(()=>{});
  toast('담당 수업 추가됨 ✅');openSaIds.add('sa-asgn');renderMain();
}
function removeA(i){
  if(!instructor?.assignments)return;if(!confirm('이 담당 수업을 제거합니까?'))return;
  instructor.assignments.splice(i,1);if(curAI>=instructor.assignments.length)curAI=0;saveLocal();
  if(fbUrl&&fbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{assignments:instructor.assignments}).catch(()=>{});
  renderMain();renderSb();
}

function ensPath(sh,cls){
  if(!cfg.sheets)cfg.sheets={};
  if(!cfg.sheets[sh])cfg.sheets[sh]={classes:{}};
  if(!cfg.sheets[sh].classes)cfg.sheets[sh].classes={};
  if(!cfg.sheets[sh].classes[cls])cfg.sheets[sh].classes[cls]={students:[],textbooks:[]};
  // 이미 존재하는 클래스라도 배열 필드가 누락된 경우(구버전 데이터) 초기화
  if(!cfg.sheets[sh].classes[cls].students)cfg.sheets[sh].classes[cls].students=[];
  if(!cfg.sheets[sh].classes[cls].textbooks)cfg.sheets[sh].classes[cls].textbooks=[];
  if(!cfg.sheets[sh].classes[cls].tb_grade)cfg.sheets[sh].classes[cls].tb_grade={};
}

function _ensureConfigShape(){
  if(!cfg)cfg={sheets:{},presets:{'과제수행도':[]},textbooks:{}};
  if(!cfg.sheets)cfg.sheets={};
  for(const sh of ['M','T']){
    if(!cfg.sheets[sh])cfg.sheets[sh]={classes:{}};
    if(!cfg.sheets[sh].classes)cfg.sheets[sh].classes={};
  }
  if(!cfg.textbooks)cfg.textbooks={};
  return cfg;
}

async function pushCfg(){
  _ensureConfigShape();
  saveLocal();
  if(!fbUrl||!fbPath)return;
  try{
    const payload={sheets:cfg.sheets||{}};
    if(cfg.textbooks)payload.textbooks=cfg.textbooks;
    await fbPatch('config',payload);
    setSync(true);toast('저장됨 ✅');
  }
  catch(e){setSync(false);toast('저장 실패: '+e);}
}

function _ensureTextbookRegistry(){
  _ensureConfigShape();
  for(const shD of Object.values(cfg.sheets||{})){
    for(const clsD of Object.values(shD.classes||{})){
      for(const tb of clsD.textbooks||[]){
        if(tb)cfg.textbooks[tb]=true;
      }
    }
  }
  return cfg.textbooks;
}

function _assertAdminForTextbookDelete(){
  if(adminOn)return true;
  toast('교재 삭제는 관리자만 가능합니다.');
  return false;
}

async function addTextbook(){
  const name=document.getElementById('tb-name-inp')?.value.trim();
  if(!name){toast('교재명을 입력해 주세요.');return;}
  const registry=_ensureTextbookRegistry();
  if(registry[name]){toast('이미 등록된 교재명입니다.');return;}
  registry[name]=true;
  await pushCfg();
  openSaIds.add('sa-tbmgmt');renderMain();toast(`"${name}" 등록됨 ✅`);
}
async function rmTextbook(name){
  if(!_assertAdminForTextbookDelete())return;
  if(!confirm(`"${name}" 삭제합니까?\n모든 학급의 교재 목록에서도 제거됩니다.`))return;
  if(!cfg?.textbooks)return;
  delete cfg.textbooks[name];
  for(const shD of Object.values(cfg.sheets||{})){
    for(const clsD of Object.values(shD.classes||{})){
      if(clsD.textbooks)clsD.textbooks=clsD.textbooks.filter(t=>t!==name);
      if(clsD.tb_grade)delete clsD.tb_grade[name];
    }
  }
  _syncAssignments();
  await pushCfg();
  openSaIds.add('sa-tbmgmt');renderMain();
}
const addGradeSemTb=addTextbook;
const rmGradeSemTb=rmTextbook;
function addCls(sh){
  const c=prompt(`${sh}반 학급명 (예: 3MGM)`);
  if(!c?.trim())return;
  _ensureConfigShape();
  ensPath(sh,c.trim());
  clsDrillSh=sh;  // 추가 후 해당 시트로 유지
  openSaIds.add('sa-cls'); // 학급 관리 섹션 열린 상태 유지
  pushCfg();
  renderMain();
}
function _syncAssignments(){
  if(!instructor?.assignments?.length)return;
  const before=instructor.assignments.length;
  instructor.assignments=instructor.assignments.filter(a=>{
    const clsD=cfg.sheets?.[a.sheet]?.classes?.[a.cls];
    if(!clsD)return false;
    return !a.tb||(clsD.textbooks||[]).includes(a.tb);
  });
  if(instructor.assignments.length===before)return;
  if(curAI>=instructor.assignments.length)curAI=0;
  saveLocal();
  if(fbUrl&&fbPath&&instructor.id)
    fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{assignments:instructor.assignments}).catch(()=>{});
}
function rmCls(sh,cls){
  if(!confirm(`${cls} 학급을 삭제합니까?`))return;
  delete cfg.sheets[sh].classes[cls];
  if(instructor?.assignments){
    const before=instructor.assignments.length;
    instructor.assignments=instructor.assignments.filter(a=>!(a.sheet===sh&&a.cls===cls));
    if(instructor.assignments.length!==before){
      if(curAI>=instructor.assignments.length)curAI=0;
      saveLocal();
      if(fbUrl&&fbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{assignments:instructor.assignments}).catch(()=>{});
    }
  }
  pushCfg();renderMain();
}
function rmStu(sh,cls,name){
  if(!confirm(`${name}을(를) 삭제합니까?`))return;
  cfg.sheets[sh].classes[cls].students=cfg.sheets[sh].classes[cls].students.filter(s=>s.name!==name);
  refreshStuChips(sh,cls);  // chips만 갱신
  pushCfg();
}
// ── 교재 인라인 추가 — 학년학기 + 교재 선택/직접입력 ──────────────────────
function addTbInline(sh,cls,btnEl){
  const chips=btnEl.parentElement;
  if(chips.querySelector('.tb-inline-wrap')){return;}

  const wrapper=document.createElement('div');
  wrapper.className='tb-inline-wrap';
  wrapper.style.cssText='display:flex;align-items:center;gap:4px;flex-wrap:wrap;margin-top:5px;padding:6px 8px;background:var(--indigo-l);border:1px solid var(--indigo);border-radius:8px;';

  // 학년학기 select
  const gsSel=document.createElement('select');
  gsSel.style.cssText='font-size:11px;padding:3px 5px;border:1px solid var(--border);border-radius:5px;font-family:inherit;background:#fff;';
  gsSel.innerHTML='<option value="">학년학기</option>'+
    GRADE_SEM_LIST.map(g=>`<option value="${esc(g.val)}">${esc(g.label)}</option>`).join('');

  // 교재 select (전체 레지스트리)
  const tbSel=document.createElement('select');
  tbSel.style.cssText='font-size:11px;padding:3px 5px;border:1px solid var(--border);border-radius:5px;font-family:inherit;background:#fff;min-width:90px;';

  // 직접입력 텍스트 (교재가 없을 때 또는 "직접입력" 선택 시)
  const tbInp=document.createElement('input');
  tbInp.placeholder='교재명 직접 입력';
  tbInp.style.cssText='font-size:11px;padding:3px 5px;border:1px solid var(--indigo);border-radius:5px;font-family:inherit;display:none;min-width:100px;';

  function refreshTbOpts(){
    const allTbs=Object.keys(_ensureTextbookRegistry()).sort((a,b)=>a.localeCompare(b,'ko'));
    const existing=cfg?.sheets?.[sh]?.classes?.[cls]?.textbooks||[];
    const available=allTbs.filter(n=>!existing.includes(n));
    tbSel.innerHTML='<option value="">교재 선택</option>'+
      available.map(n=>`<option value="${esc(n)}">${esc(n)}</option>`).join('')+
      '<option value="__new__">✏️ 직접 입력...</option>';
    tbInp.style.display='none';
  }
  refreshTbOpts();

  tbSel.onchange=()=>{
    if(tbSel.value==='__new__'){
      tbInp.style.display='';tbInp.focus();
    } else {
      tbInp.style.display='none';tbInp.value='';
    }
  };

  const ok=document.createElement('span');
  ok.textContent='✓';
  ok.style.cssText='cursor:pointer;color:var(--indigo);font-weight:700;font-size:14px;padding:0 2px;';
  const cancel=document.createElement('span');
  cancel.textContent='×';
  cancel.style.cssText='cursor:pointer;color:var(--gray);font-size:14px;padding:0 2px;';
  cancel.onclick=()=>wrapper.remove();
  tbInp.onkeydown=e=>{if(e.key==='Enter')ok.click();};

  async function doAdd(){
    const gs=gsSel.value;
    if(!gs){toast('학년학기를 선택해 주세요.');return;}
    let t='';
    if(tbSel.value==='__new__'){
      t=tbInp.value.trim();
      if(!t){toast('교재명을 입력해 주세요.');return;}
      // 글로벌 레지스트리에도 등록
      _ensureTextbookRegistry()[t]=true;
    } else {
      t=tbSel.value;
      if(!t){toast('교재를 선택해 주세요.');return;}
    }
    const existingTbs=cfg?.sheets?.[sh]?.classes?.[cls]?.textbooks||[];
    if(existingTbs.includes(t)){toast('이미 추가된 교재입니다.');return;}
    ensPath(sh,cls);
    cfg.sheets[sh].classes[cls].textbooks.push(t);
    cfg.sheets[sh].classes[cls].tb_grade[t]=gs;
    wrapper.remove();
    try{refreshTbChips(sh,cls);}catch(e){renderMain();}
    try{await pushCfg();}catch(e){toast('교재 저장 실패: '+e);}
  }
  ok.onclick=doAdd;
  gsSel.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();ok.click();}};
  tbSel.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();ok.click();}};
  tbInp.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();ok.click();}};

  wrapper.appendChild(gsSel);wrapper.appendChild(tbSel);wrapper.appendChild(tbInp);wrapper.appendChild(ok);wrapper.appendChild(cancel);
  chips.parentElement.appendChild(wrapper);
  gsSel.focus();
}
function refreshTbChips(sh,cls){
  // data-sh/data-cls 어트리뷰트로 탐색 — clsKey(한글→_) 충돌 방지
  const sSh=sh.replace(/\\/g,'\\\\').replace(/"/g,'\\"');
  const sCls=cls.replace(/\\/g,'\\\\').replace(/"/g,'\\"');
  const el=document.querySelector(`[data-chip-type="tb"][data-sh="${sSh}"][data-cls="${sCls}"]`);
  if(!el)return;
  const tbs=cfg.sheets?.[sh]?.classes?.[cls]?.textbooks||[];
  const tbChips=tbs.map(t=>{const gs=getTbGrade(sh,cls,t)||'';const gsLabel=gs?(GRADE_SEM_LIST.find(g=>g.val===gs)?.label||gs):'';return`<span class="chip" onclick="rmTb('${esc(sh)}','${esc(cls)}','${esc(t)}')">${gsLabel?`<span style="color:var(--indigo);font-size:9px;font-weight:700;margin-right:3px">${esc(gsLabel)}</span>`:`<span style="color:var(--red);font-size:9px;margin-right:3px">미설정</span>`}${esc(t)} <span style="display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px;margin-left:4px;border-radius:50%;background:#FEE2E2;color:#B91C1C;font-size:10px;font-weight:700;line-height:1">×</span></span>`;}).join('');
  el.innerHTML=tbChips+`<span class="chip" style="background:var(--indigo-l);border-color:var(--indigo);color:var(--indigo);cursor:pointer" onclick="addTbInline('${esc(sh)}','${esc(cls)}',this)">+ 교재 추가</span>`;
}
function addTb(sh,cls){const t=prompt(`${cls} 교재명:`);if(!t?.trim())return;ensPath(sh,cls);cfg.sheets[sh].classes[cls].textbooks.push(t.trim());pushCfg();renderMain();}
async function rmTb(sh,cls,tb){
  if(!confirm(`"${tb}" 삭제합니까?`))return;
  ensPath(sh,cls);
  cfg.sheets[sh].classes[cls].textbooks=(cfg.sheets[sh].classes[cls].textbooks||[]).filter(t=>t!==tb);
  if(cfg?.sheets?.[sh]?.classes?.[cls]?.tb_grade){
    delete cfg.sheets[sh].classes[cls].tb_grade[tb];
  }
  try{refreshTbChips(sh,cls);}catch(e){}
  try{
    await pushCfg();
  }catch(e){
    toast('교재 삭제 저장 실패: '+e);
  }
}

async function loadCfg(){
  if(!fbUrl||!fbPath){toast('Firebase URL과 경로를 먼저 저장하세요.');return;}
  const mc=document.getElementById('mc');
  mc.innerHTML=`<div class="loading"><div class="spin"></div>불러오는 중...</div>`;
  try{
    const data=await fbGet('config');
    cfg=data||{sheets:{M:{classes:{}},T:{classes:{}}},presets:{'과제수행도':[]},textbooks:{}};
    _ensureConfigShape();
    _ensureTextbookRegistry();
    saveLocal();setSync(true);
    try{let s=await fbGet('session').catch(()=>null);if(!s?.class_data)s=await fbGet('lastSent').catch(()=>null);if(s?.class_data)for(const[k,v]of Object.entries(s.class_data))if(!progressData[k])progressData[k]=v;saveLocal();}catch(e){}
    try{const d=await fbGet('input');if(d)Object.assign(inputData,d);saveLocal();}catch(e){}
    try{const d=await fbGet('obs');if(d)Object.assign(tagData,d);saveLocal();}catch(e){}
    if(instructor?.id){const id=await fbGet(`config/instructors/${encodeURIComponent(instructor.id)}`).catch(()=>null);if(id){Object.assign(instructor,id);saveLocal();}}
    toast('학생 명단 불러옴 ✅');
    if(!instructor)toast('강사 선택이 필요합니다 — 좌측 상단 강사 뱃지를 클릭하세요',4000);
    renderMain();renderSb();
  }catch(e){setSync(false);toast('연결 실패: '+e);renderMain();}
}
// ── 초기화 scope 헬퍼 ───────────────────────────────────────────────
// assignments 기반으로 삭제 대상 키 목록 생성
// Returns: { inputKeys: string[], progressKeys: string[] }
function _myResetKeys(){
  const asgns=instructor?.assignments||[];
  const inputKeys=[];
  const progressKeys=[];
  const noteKeySeen=new Set();
  for(const a of asgns){
    const students=cfg?.sheets?.[a.sheet]?.classes?.[a.cls]?.students||[];
    for(const s of students){
      inputKeys.push(`${a.sheet}|${a.cls}|${s.name}|${a.tb}`);
      // __note__ 키는 tb와 무관하게 cls+name 기준으로 1개만 (중복 방지)
      const nk=`${a.sheet}|${a.cls}|${s.name}|__note__`;
      if(!noteKeySeen.has(nk)){noteKeySeen.add(nk);inputKeys.push(nk);}
    }
    progressKeys.push(`${a.sheet}|${a.cls}|${a.tb}`);
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
  // 설정 탭이 열려 있으면 해당 섹션만 부분 갱신
  const body=document.querySelector('#sa-reset .sa-body');
  if(body)body.innerHTML=_renderResetHtml();
}
async function _doResetPresets(){
  const def=_defaultPresets();
  if(instructor){instructor.presets=[...def];}
  if(fbUrl&&fbPath&&instructor?.id){
    await fbPatch(`config/instructors/${instructor.id}`,{presets:def}).catch(()=>{});
  }
  saveLocal();
}

// ── 초기화 실행 (다중 선택) ──────────────────────────────────────────
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

  if(!fbUrl||!fbPath){
    // 로컬 처리 (Firebase 없음)
    if(sel.includes('input')){const{inputKeys}=_myResetKeys();for(const k of inputKeys)delete inputData[k];}
    if(sel.includes('tags')){
      const dk=todayKey();const asgns=instructor?.assignments||[];
      for(const a of asgns){const sts=cfg?.sheets?.[a.sheet]?.classes?.[a.cls]?.students||[];
        for(const s of sts){const ok=`${a.sheet}|${a.cls}|${s.name}|${a.tb}`;if(tagData[ok]?.[dk])delete tagData[ok][dk];}
      }
    }
    if(sel.includes('progress')){const{progressKeys}=_myResetKeys();for(const k of progressKeys)delete progressData[k];}
    if(sel.includes('presets'))await _doResetPresets();
    saveLocal();toast('초기화 완료 (로컬)');_resetSel.clear();renderMain();return;
  }

  try{
    const ops=[];
    // ── 일반 항목 ──
    if(sel.includes('input')){
      // 특이사항 메모만 (inputData의 __note__ 항목)
      const{inputKeys}=_myResetKeys();
      const noteKeys=inputKeys.filter(k=>k.endsWith('|__note__'));
      for(const k of noteKeys)delete inputData[k];
      const p={};for(const k of noteKeys)p[k]=null;
      if(Object.keys(p).length)ops.push(fbPatch('input',p));
    }
    if(sel.includes('tags')){
      // 수행도(assign_grade/assign_tags) + 모든 obs 태그 — 키: sheet|cls|name|tb
      const dk=todayKey();const asgns=instructor?.assignments||[];
      for(const a of asgns){
        const sts=cfg?.sheets?.[a.sheet]?.classes?.[a.cls]?.students||[];
        for(const s of sts){
          const ok=`${a.sheet}|${a.cls}|${s.name}|${a.tb}`;
          if(tagData[ok]?.[dk]){delete tagData[ok][dk];ops.push(fbPatch(`obs/${encodeURIComponent(ok)}`,{[dk]:null}));}
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
    // ── 관리자 항목 ──
    if(sel.includes('all-input')){inputData={};tagData={};ops.push(fbPut('input',null));ops.push(fbPut('obs',null));}
    if(sel.includes('all-progress')){progressData={};ops.push(fbPut('session',null));}
    if(sel.includes('assignments')){
      const instrs=await fbGet('config/instructors').catch(()=>null);
      if(instrs)for(const id of Object.keys(instrs))ops.push(fbPatch(`config/instructors/${id}`,{assignments:[]}).catch(()=>{}));
    }
    if(sel.includes('config')){
      ops.push(fbPut('config',null));ops.push(fbPut('input',null));ops.push(fbPut('session',null));
      inputData={};progressData={};cfg=null;instructor=null;adminOn=false;
      SS('drw_input','{}');SS('drw_prog','{}');SS('drw_cfg','');SS('drw_instr','');
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
  // 사이드바 뱃지 클릭 → 설정 > 내 계정 섹션으로 이동
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
  if(!fbUrl||!fbPath){card.innerHTML='<div style="padding:10px 12px;font-size:12px;color:var(--gray)">Firebase 연결 후 사용 가능합니다.</div>';return;}
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
  if(!fbUrl||!fbPath){toast('Firebase 연결이 필요합니다.');return;}
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
  if(fbUrl&&fbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{presets:instructor.presets}).catch(()=>{});
  renderMain();
}
function rmPreset(i){
  if(!instructor?.presets)return;
  if(!confirm(`"${instructor.presets[i]}" 프리셋을 삭제합니까?`))return;
  instructor.presets.splice(i,1);saveLocal();
  if(fbUrl&&fbPath&&instructor.id)fbPatch(`config/instructors/${encodeURIComponent(instructor.id)}`,{presets:instructor.presets}).catch(()=>{});
  renderMain();
}

function closeIM(){document.getElementById('iModal').classList.remove('show');}
function toggleAcc(hdr){
  const body=hdr.nextElementSibling;
  const arrow=hdr.querySelector('.acc-arr');
  const open=body.classList.toggle('open');
  if(arrow)arrow.textContent=open?'▼':'▶';
}
