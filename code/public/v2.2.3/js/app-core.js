// ── 수학 커리큘럼 (2022 개정) — data/curriculum.js 에서 CURRICULUM_RAW 로드
let CURRICULUM = {};

function _normalizeCurriculum(raw){
  const root = raw?.curriculum || raw?.['2022_revised_math_curriculum'] || raw;
  const out = {};
  const add = (key, arr) => {
    if(!Array.isArray(arr))return;
    out[key] = arr.map(ch => ({
      main: ch.main || ch.main_chapter || "",
      subs: ch.subs || ch.sub_chapters || []
    })).filter(ch => ch.main);
  };

  const elem = root?.elementary_school || {};
  for(let g=3; g<=6; g++){
    add(`초${g}-1`, elem[`grade_${g}`]?.semester_1);
    add(`초${g}-2`, elem[`grade_${g}`]?.semester_2);
  }

  const middle = root?.middle_school || {};
  for(let g=1; g<=3; g++){
    add(`중${g}-1`, middle[`grade_${g}`]?.semester_1);
    add(`중${g}-2`, middle[`grade_${g}`]?.semester_2);
  }

  const highCredit = root?.high_school_credit_system || {};
  const common = highCredit.level_1_common_courses || {};
  const elective = highCredit.level_2_general_elective_courses || {};
  add("공통수학1", common.common_math_1);
  add("공통수학2", common.common_math_2);
  add("대수", elective.algebra);
  add("미적분I", elective.calculus_1);
  add("확통", elective.probability_and_statistics);

  return out;
}

function loadCurriculum(){
  CURRICULUM = _normalizeCurriculum(typeof CURRICULUM_RAW !== 'undefined' ? CURRICULUM_RAW : {});
}

const GRADE_SEM_LIST = [
  {val:'초3-1',label:'초3-1'},{val:'초3-2',label:'초3-2'},
  {val:'초4-1',label:'초4-1'},{val:'초4-2',label:'초4-2'},
  {val:'초5-1',label:'초5-1'},{val:'초5-2',label:'초5-2'},
  {val:'초6-1',label:'초6-1'},{val:'초6-2',label:'초6-2'},
  {val:'중1-1',label:'중1-1'},{val:'중1-2',label:'중1-2'},
  {val:'중2-1',label:'중2-1'},{val:'중2-2',label:'중2-2'},
  {val:'중3-1',label:'중3-1'},{val:'중3-2',label:'중3-2'},
  {val:'공통수학1',label:'공통수학1'},{val:'공통수학2',label:'공통수학2'},
  {val:'대수',label:'대수'},{val:'미적분I',label:'미적분I'},
  {val:'확통',label:'확통'},
];

const BC=['#22C55E','#3B82F6','#F59E0B','#EF4444','#94A3B8','#4338CA','#8B5CF6','#F97316','#14B8A6','#EC4899'];

// ── 과제 고정 평가지표 (수정 불가, obs/assign_grade 저장) ─────────
const ASSIGN_GRADES = [
  {key:'done',   label:'✅ 완료'},
  {key:'most',   label:'🔵 대부분'},
  {key:'half',   label:'🟡 절반'},
  {key:'little', label:'🟠 일부'},
  {key:'none',   label:'❌ 미완'},
];

// ── 컨디션 화살표 회전각 (PES 스타일) ─────────────────────────────
const COND_ARROWS={great:0,good:45,normal:90,low:135,bad:180};

// ── 관찰 태그 정의 (key=Firebase 저장값, label=표시) ──────────────
const TAGS = {
  condition: [
    {key:'great',  label:'최상'},
    {key:'good',   label:'좋음'},
    {key:'normal', label:'보통'},
    {key:'low',    label:'낮음'},
    {key:'bad',    label:'힘듦'},
  ],
  understand: [
    {key:'top',      label:'완벽'},
    {key:'good',     label:'잘함'},
    {key:'normal_u', label:'이해함'},
    {key:'confused', label:'헷갈림'},
    {key:'hard',     label:'어려워함'},
  ],
  understand_sub: [
    {key:'self_solve', label:'💪 혼자해결'},
    {key:'retry',      label:'🔁 오답재풀이'},
    {key:'confused',   label:'😵 개념혼동'},
  ],
  engage: [
    {key:'present',   label:'📣 발표'},
    {key:'question',  label:'🙋 질문'},
    {key:'help',      label:'🤝 도움'},
    {key:'preview',   label:'📖 예습'},
    {key:'error_fix', label:'💡 오류정정'},
  ],
  caution: [
    {key:'sleepy',   label:'💤 졸음'},
    {key:'chat',     label:'🗣 잡담'},
    {key:'attitude', label:'😤 태도불량'},
    {key:'late',     label:'⏰ 지각'},
  ],
  extra: [
    {key:'self_study',  label:'📚 자율학습'},
    {key:'weekly_test', label:'📝 주간Test'},
    {key:'retest',      label:'🔄 재시험'},
  ],
  highlight: [
    {key:'perfect',  label:'🏆 만점·완벽'},
    {key:'improved', label:'📈 큰 향상'},
    {key:'mastered', label:'✅ 개념완전습득'},
    {key:'effort',   label:'💎 끝까지도전'},
  ],
};

// config: { classes: {classId: {group, courses: {subject: {textbook, curriculum, instructor}}}}, instructors: {...} }
let config=null,inputData={},progressData={},tagData={},instructor=null;
let activeTab='input',curAI=0,dbUrl='',dbPath='',dbSecret='',activeGroup='';
let _devDate=null; // 🔧 테스트용 날짜 오버라이드 (null=오늘)
let clsDrillSh=null; // 학급 관리 드릴다운 상태 (null=최상위, classId)
let adminOn=false;   // 관리자 세션 상태 (새로고침 시 해제)
let sbFolded={};     // 사이드바 그룹 섹션 접힘 상태 {그룹명: true/false}
let archOpen={};     // 학급 관리 보관 과목 행 펼침 상태 {classId: true} — 재렌더에도 유지(세션)
let _resetSel=new Set(); // 초기화 다중 선택 상태
let openSaIds=new Set(['sa-fb']); // 설정 아코디언 열림 상태 — renderMain() 재렌더 후 복원용
// 초기 설정 위저드 (온보딩) — 강사 미설정 신규 사용자에게 4단계 가이드
let wizardActive=false; // true면 renderMain()이 탭 대신 위저드 렌더
let wzStep=0;           // 0:Firebase 1:계정 2:명단 3:수업 4:완료
let wzCls=null;         // 위저드 수업 단계: 선택된 반(classId)
// 점수 입력 상태
let scoreData={};        // {weekly: {subject: {testKey: testObj}}, achievement: {curriculumKey: {testKey: testObj}}}
let scoreEditing=null;   // {classId,subject,testKey,isAchievement} | null(=신규)
let scoreView='list';    // 'list' | 'edit'
const SCORE_TYPES=['주간Test','기출모의고사','실전모의고사','성취도평가','반배치고사','직접입력'];
const ACHIEVEMENT_TYPES=['성취도평가','기출모의고사','실전모의고사','반배치고사'];
// SHA-256("idocho")
const ADMIN_HASH='f3fd1456b2db60728b102561496c156e4c4adf0e537d4c45fa0add381fdd9a1e';

const LS=k=>localStorage.getItem(k);
const SS=(k,v)=>localStorage.setItem(k,v);
function loadLocal(){
  dbUrl=LS('drw_db_url')||'';dbPath=LS('drw_db_path')||'';dbSecret=LS('drw_db_secret')||'';
  try{inputData=JSON.parse(LS('drw_input')||'{}');}catch(e){inputData={};}
  try{progressData=JSON.parse(LS('drw_prog')||'{}');}catch(e){progressData={};}
  try{tagData=JSON.parse(LS('drw_tags')||LS('drw_obs')||'{}');}catch(e){tagData={};}
  try{instructor=JSON.parse(LS('drw_instr')||'null');}catch(e){instructor=null;}
  try{config=JSON.parse(LS('drw_config')||'null');}catch(e){config=null;}
}
function saveLocal(){
  SS('drw_db_url',dbUrl);SS('drw_db_path',dbPath);SS('drw_db_secret',dbSecret);
  SS('drw_input',JSON.stringify(inputData));
  SS('drw_prog',JSON.stringify(progressData));
  SS('drw_tags',JSON.stringify(tagData));
  if(instructor)SS('drw_instr',JSON.stringify(instructor));
  if(config)SS('drw_config',JSON.stringify(config));
}

// Security Rules 전환 대비(#15): dbSecret 설정 시 ?auth= 전달. 미설정이면 종전과 동일(no-op).
function fbE(n){const u=`${dbUrl.replace(/\/$/,'')}/${dbPath.replace(/^\/|\/$/g,'')}/${n}.json`;return dbSecret?`${u}?auth=${encodeURIComponent(dbSecret)}`:u;}
// 스키마 버전 게이트: DB의 schema_version(정수)이 이 클라 지원 최대치보다 크면 차단.
// 노드 부재·읽기 실패 = 통과(전환 전 DB·일시 네트워크 오류에 가용성 우선).
const SCHEMA_MAX=14; // DB_SCHEMA v1.4
async function checkSchemaVersion(){
  try{
    const v=await fbGet('schema_version');
    if(typeof v==='number'&&v>SCHEMA_MAX){
      document.body.innerHTML=`<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;gap:14px;padding:24px;text-align:center;font-family:inherit">
        <div style="font-size:42px">⛔</div>
        <div style="font-size:18px;font-weight:700">앱 버전이 낮아 사용할 수 없습니다</div>
        <div style="color:#888">DB 스키마 v${v} &gt; 지원 v${SCHEMA_MAX} — 데이터 보호를 위해 차단되었습니다.<br>최신 버전으로 접속해 주세요.</div>
        <button class="btn bp" onclick="location.reload(true)" style="padding:10px 22px">새로고침</button></div>`;
    }
  }catch(e){}
}
async function fbGet(n){const r=await fetch(fbE(n));if(!r.ok)throw n+':'+r.status;return r.json();}
async function fbPut(n,d){const r=await fetch(fbE(n),{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});if(!r.ok)throw n+':'+r.status;return r.json();}
async function fbPatch(n,d){const r=await fetch(fbE(n),{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});if(!r.ok)throw n+':'+r.status;return r.json();}

const DAYS=['일','월','화','수','목','금','토'];
function today(){
  if(_devDate){const p=_devDate.split('-');const d=new Date(_devDate);return`🔧 ${Number(p[1])}/${Number(p[2])} (${DAYS[d.getDay()]})`;}
  const d=new Date();return `${d.getMonth()+1}/${d.getDate()} (${DAYS[d.getDay()]})`;
}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
function toast(m,ms=2500){const e=document.getElementById('toast');e.textContent=m;e.classList.add('show');clearTimeout(e._t);e._t=setTimeout(()=>e.classList.remove('show'),ms);}
// 학생 배열 이름 가나다 오름차순 정렬(제자리). None-safe + 동명이인 nameKey tiebreak. 키 불변, 표시 순서만.
function sortStu(arr){return (arr||[]).sort((a,b)=>(a.name||'').localeCompare(b.name||'','ko')||String(a.nameKey).localeCompare(String(b.nameKey)));}
function setSync(ok){/* syncBadge 제거됨 (v0.9.4) */}
// v2.2.3: Firebase write 실패 표면화 — 무음 catch 일괄 대체용. 로컬엔 저장돼 있으니 재시도 안내.
function fbFail(label){return e=>toast(`⚠️ ${label} 서버 저장 실패 — 네트워크 확인 후 다시 시도하세요`,4000);}
// 담당 수업 표시 정렬: 학급→과정→교재명 오름차순 (subject="{과정} {교재}" 복합 키라 subject ko 정렬로 충분).
// 원본 배열 인덱스(i)를 보존해 반환 — removeA(i)/selA(i) 등 인덱스 기반 핸들러와 호환 (저장 순서는 불변, 표시만 정렬)
function _sortedAsgns(asgns){
  return (asgns||[]).map((a,i)=>({a,i})).sort((x,y)=>
    (x.a.classId||'').localeCompare(y.a.classId||'','ko')||
    (x.a.subject||'').localeCompare(y.a.subject||'','ko'));
}
// 소프트 삭제: archived 과목 제외. 과목 "삭제"는 archived:true 마킹 — obs/scores/history/session 데이터는 DB에 보존되고 노출만 차단. 같은 키로 재추가 시 복원.
function activeCourses(clsD){const out={};for(const[s,c]of Object.entries((clsD||{}).courses||{})){if(!(c&&c.archived))out[s]=c;}return out;}
function _normWs(s){return String(s||'').replace(/\s+/g,' ').trim();}
function _normTbName(s){return _normWs(s);}
function _normGradeSem(s){
  let v=_normWs(s)
    .replace(/[－–—]/g,'-')
    .replace(/\s*-\s*/g,'-')
    .replace(/학기/g,'')
    .replace(/([0-9])\s*학년\s*([12])/g,'$1-$2')
    .replace(/(초|중|고)\s*([0-9])\s*-\s*([12])/g,'$1$2-$3');
  v=v.replace(/미적분\s*1/i,'미적분I').replace(/미적분\s*I/i,'미적분I');
  return v;
}
function getCurriculumByGradeSem(gradeSem){
  const g=_normGradeSem(gradeSem);
  if(!g)return [];
  const direct=CURRICULUM[g];
  if(Array.isArray(direct))return direct;
  for(const [k,v] of Object.entries(CURRICULUM||{})){
    if(_normGradeSem(k)===g&&Array.isArray(v))return v;
  }
  return [];
}

/**
 * 신규: classes/{classId}/courses/{subject}/curriculum → GRADE_SEM 형식으로 반환
 * curriculum 키 형식: "middle_school.grade_3.semester_1" → "중3-1"
 */
function getCurriculumForSubject(classId, subject){
  const course = config?.classes?.[classId]?.courses?.[subject];
  if(!course)return '';
  return course.curriculum || '';
}

/**
 * 과정명 표시 prefix — subject 키가 이미 과정명으로 시작하면 '' 반환(중복 방지).
 * 신규 교재 키는 "{curriculum} {textbook}" 복합이라 gsLabel 을 또 붙이면 과정명이 두 번 나옴.
 * (PC grade_label 의 "이미 과정명으로 시작하면 prepend 안 함" 규칙을 웹에 대응)
 */
function gsPrefix(curriculum, subject){
  if(!curriculum) return '';
  const label = (GRADE_SEM_LIST.find(g=>g.val===curriculum)?.label) || curriculum;
  const s = String(subject||'');
  if(s.startsWith(curriculum + ' ') || s.startsWith(label + ' ')) return '';
  return label;
}

/**
 * curriculum 키(점 표기) → curriculumKey(언더스코어)
 */
function curriculumToKey(curriculum){
  return (curriculum||'').replaceAll('.','_');
}

async function pushInput(key,val){
  inputData[key]=val;saveLocal();
  if(!dbUrl||!dbPath)return;
  // 쓰기 권한 가드: 내 assignments 범위 내 키만 Firebase PATCH
  const p=key.split('|');
  if(p.length===4){
    const [,classId,,subject]=p;
    const realSubject=subject==='__note__'?null:subject;
    if(!_canWrite(classId,realSubject))return;
  }
  try{await fbPatch('input',{[key]:val});}catch(e){fbFail('과제수행도/메모')(e);}
}
async function pushProgress(pkey,val){
  progressData[pkey]=val;saveLocal();
  if(!dbUrl||!dbPath)return;
  const p=pkey.split('|');
  if(p.length===2){
    const [classId,subject]=p;
    if(!_canWrite(classId,subject))return;
  }
  try{await fbPatch('session/class_data',{[pkey]:val});}catch(e){fbFail('진도/과제')(e);}
}

// ── 오늘 날짜 키 (YYYY-MM-DD) ────────────────────────────────────
function todayKey(){
  if(_devDate)return _devDate;
  const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}
function setDevDate(val){_devDate=val||null;renderMain();}

// ── 🔧 더미 세션 생성 (현재 반 전체 학생 → _devDate로 obs 푸시) ─────
async function devPushDummy(){
  if(!_devDate){toast('날짜를 먼저 선택하세요.');return;}
  if(!dbUrl||!dbPath){toast('Firebase 연결 필요.');return;}
  const asgns=instructor?.assignments||[];
  if(!asgns.length){toast('담당 수업 없음.');return;}
  const a=asgns[curAI];
  // 신규: students/ 전체 로드 후 classId 필터
  let classStudents=[];
  try{
    const allStudents=await fbGet('students')||{};
    classStudents=Object.entries(allStudents)
      .filter(([,v])=>v?.class===a.classId)
      .map(([nameKey,v])=>({nameKey,...v}));
  }catch(e){toast('학생 로드 실패: '+e);return;}
  if(!classStudents.length){toast('학생 없음.');return;}
  const _r=arr=>arr[Math.floor(Math.random()*arr.length)];
  const _pick=(arr,n)=>{const s=[...arr];const r=[];for(let i=0;i<n&&s.length;i++){const idx=Math.floor(Math.random()*s.length);r.push(s.splice(idx,1)[0]);}return r;};
  let ok=0,skip=0;
  for(const stu of classStudents){
    const nameKey=stu.nameKey;
    // 이미 해당 날짜 데이터 있으면 스킵
    const existing=tagData?.[nameKey]?.[a.subject]?.[_devDate];
    if(existing&&Object.keys(existing).length>0){skip++;continue;}
    const dummy={
      condition: _r(['great','good','good','normal','normal','normal','low','bad']),
      understand: _r(['top','good','good','normal_u','normal_u','normal_u','confused','hard']),
      assign_grade: _r(['done','done','done','most','most','half','little','none']),
      understand_sub: _pick(['self_solve','retry','confused'],Math.random()<0.5?1:0),
      engage: _pick(['present','question','help','preview','error_fix'],Math.random()<0.4?1:0),
      caution: _pick(['sleepy','chat','attitude','late'],Math.random()<0.15?1:0),
      highlight: _pick(['perfect','improved','mastered','effort'],Math.random()<0.1?1:0),
    };
    if(!tagData[nameKey])tagData[nameKey]={};
    if(!tagData[nameKey][a.subject])tagData[nameKey][a.subject]={};
    tagData[nameKey][a.subject][_devDate]=dummy;
    try{await fbPatch(`obs/${nameKey}/${a.subject}`,{[_devDate]:dummy});ok++;}catch(e){}
  }
  saveLocal();
  const skipMsg=skip?` (${skip}명 기존 데이터 유지)`:'';
  toast(`✅ ${_devDate} 더미 ${ok}명 생성${skipMsg}`);
  renderMain();
}

// ── tags 저장 키: tagData[nameKey][subject][YYYY-MM-DD] ─
function getTags(classId,nameKey,subject){
  if(!tagData[nameKey])tagData[nameKey]={};
  if(!tagData[nameKey][subject])tagData[nameKey][subject]={};
  if(!tagData[nameKey][subject][todayKey()])tagData[nameKey][subject][todayKey()]={};
  return tagData[nameKey][subject][todayKey()];
}
async function pushObs(classId,nameKey,subject,field){
  saveLocal();
  if(!dbUrl||!dbPath)return;
  if(!_canWrite(classId,subject))return;
  const dateKey=todayKey();
  const val=tagData?.[nameKey]?.[subject]?.[dateKey]||{};
  try{
    if(field!==undefined){
      // v2.2.3: 동시쓰기 race 완화 — 날짜 객체 통째가 아니라 변경된 필드만 PATCH.
      // 두 강사가 같은 학생을 동시에 입력해도 서로 다른 필드는 충돌하지 않음 (검수 C3).
      const fv=val[field];
      await fbPatch(`obs/${nameKey}/${subject}/${dateKey}`,{[field]:fv===undefined?null:fv});
    }else{
      // 필드 미지정(레거시/일괄) — 날짜 객체 통째 (devPushDummy 등)
      await fbPatch(`obs/${nameKey}/${subject}`,{[dateKey]:val});
    }
  }catch(e){fbFail('관찰 태그')(e);}
}

// ── 태그 토글 핸들러 ─────────────────────────────────────────────
function onTagCondition(el,classId,nameKey,subject){
  const k=el.dataset.k;
  const tags=getTags(classId,nameKey,subject);
  tags.condition = tags.condition===k ? null : k;
  const cell=el.closest('.tg-cell');
  if(cell)cell.querySelectorAll('.tg-radio[data-g="condition"]').forEach(b=>{
    b.classList.toggle('sel-c', b.dataset.k===tags.condition);
  });
  pushObs(classId,nameKey,subject,'condition');
}
function onTagUnderstand(el,classId,nameKey,subject){
  const k=el.dataset.k;
  const tags=getTags(classId,nameKey,subject);
  tags.understand = tags.understand===k ? null : k;
  const cell=el.closest('.tg-cell');
  if(cell)cell.querySelectorAll('.tg-radio[data-g="understand"]').forEach(b=>{
    b.classList.toggle('sel-c', b.dataset.k===tags.understand);
  });
  pushObs(classId,nameKey,subject,'understand');
}
function onTagMulti(el,classId,nameKey,field,subject){
  const k=el.dataset.k;
  const tags=getTags(classId,nameKey,subject);
  if(!tags[field])tags[field]=[];
  const idx=tags[field].indexOf(k);
  if(idx>=0)tags[field].splice(idx,1); else tags[field].push(k);
  el.classList.toggle('sel-m', tags[field].includes(k));
  pushObs(classId,nameKey,subject,field);
}

/**
 * 쓰기 권한 가드 — instructor.assignments 기반
 * subject=null 이면 classId 레벨 검사
 * instructor 미설정 시 항상 false
 */
function _canWrite(classId,subject){
  if(!instructor)return false;
  const asgns=instructor.assignments||[];
  if(!asgns.length)return true; // assignments 없으면 전체 허용
  return asgns.some(a=>
    a.classId===classId && (subject===null||a.subject===subject)
  );
}

function goNav(n){
  activeTab=n;
  if(n==='scores'){scoreView='list';scoreEditing=null;_loadScoreDataIfNeeded();}
  ['input','scores','setting'].forEach(x=>{const e=document.getElementById('nav_'+x);if(e)e.classList.toggle('on',x===n);});
  renderSb();renderMain();
}
function selA(i){
  const a=instructor?.assignments?.[i];
  const newGroup=a?.group||activeGroup;
  sbFolded[newGroup]=false;
  curAI=i;activeGroup=newGroup;if(activeTab!=='scores')activeTab='input';renderSb();renderMain();
}
function selGroup(gr){
  sbFolded[gr]=false;
  activeGroup=gr;
  const asgns=instructor?.assignments||[];
  const idx=asgns.findIndex(a=>a.group===gr);
  if(idx>=0)curAI=idx;
  renderSb();renderMain();
}
function sbToggle(gr){
  sbFolded[gr]=sbFolded[gr]!==true;
  renderSb();
}

function renderSb(){
  const sb=document.getElementById('sb');if(!sb)return;
  const asgns=instructor?.assignments||[];
  let aHtml='';
  if(activeTab==='input'||activeTab==='scores'){
    aHtml='<div class="sb-lbl">내 담당 수업</div>';
    if(!asgns.length){
      aHtml+=`<div style="padding:8px 13px;font-size:11px;color:rgba(255,255,255,.3)">설정에서 추가하세요</div>`;
    } else {
      const groups=[...new Set(asgns.map(a=>a.group||''))];
      groups.forEach(gr=>{
        const grAsgns=asgns.filter(a=>(a.group||'')===gr);
        const folded=sbFolded[gr]===true;
        const arrow=folded?'▸':'▾';
        aHtml+=`<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 13px 2px;font-size:9px;font-weight:700;color:rgba(255,255,255,.4);letter-spacing:.08em;cursor:pointer;user-select:none" onclick="sbToggle('${esc(gr)}')">${esc(gr||'기타')} <span style="font-size:11px;opacity:.7">${arrow}</span></div>`;
        if(!folded){
          grAsgns.forEach(a=>{
            const i=asgns.indexOf(a);
            aHtml+=`<div class="sb-a${i===curAI?' on':''}" onclick="selA(${i})"><div style="font-size:11px;font-weight:700">${esc(a.classId)}</div><div style="font-size:10px;color:rgba(255,255,255,.45);margin-top:1px">${esc(a.subject)}</div></div>`;
          });
        }
      });
    }
  }
  sb.innerHTML=`
    <div class="sb-me" onclick="showIM()">
      <div style="display:flex;align-items:center;gap:8px">
        <div class="avatar">${esc((instructor?.name||'?').slice(0,3))}</div>
        <div style="flex:1;min-width:0">
          <div style="font-size:12px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(instructor?.name||'강사 미선택')}</div>
          <div style="font-size:10px;color:var(--gray)">${(instructor?.assignments||[]).length}개 수업</div>
        </div>
        <span style="font-size:10px;color:rgba(255,255,255,.4)">▾</span>
      </div>
    </div>
    <div class="sb-nav">
      <div class="sni${activeTab==='input'?' on':''}" onclick="goNav('input')">✏️ 수업 입력</div>
      <div class="sni${activeTab==='scores'?' on':''}" onclick="goNav('scores')">📊 성적 입력</div>
      <div class="sni${activeTab==='setting'?' on':''}" onclick="goNav('setting')">⚙️ 설정</div>
    </div>
    ${aHtml}
    <div style="flex:1"></div>
    <a href="./guide.html" target="_blank" style="display:flex;align-items:center;gap:8px;padding:10px 13px;font-size:11px;color:rgba(255,255,255,.4);text-decoration:none;border-top:1px solid rgba(255,255,255,.08);transition:background .12s,color .12s" onmouseover="this.style.background='rgba(255,255,255,.07)';this.style.color='rgba(255,255,255,.8)'" onmouseout="this.style.background='';this.style.color='rgba(255,255,255,.4)'">📖 <span>설치 · 운용 가이드</span></a>
    <div style="padding:5px 8px 8px;font-size:9px;color:rgba(255,255,255,.18);text-align:center">`+`DRW ${APP_VERSION} · IDO`+`</div>`;
}

function renderMhdr(title){/* PC 전용 — 모바일 헤더 미사용 */}
function makeTb(title,sub=''){
  // 🔧 dev 도구(날짜 변경·더미 생성)는 관리자 전용 — 일반 강사 오조작으로
  // 운영 obs 누적이 오염되던 경로 차단 (액션아이템 A4)
  if(!adminOn)return `<div class="topbar"><div><div style="font-size:14px;font-weight:700">${esc(title)}</div>${sub?`<div style="font-size:11px;color:var(--sub);margin-top:1px">${esc(sub)}</div>`:''}</div></div>`;
  const devBadge=_devDate
    ?`<div style="display:flex;align-items:center;gap:6px;background:#7c3a00;border:1px solid #f97316;border-radius:8px;padding:4px 8px">
        <span style="font-size:10px;color:#fb923c;font-weight:700;white-space:nowrap">🔧 테스트</span>
        <input type="date" value="${_devDate}" onchange="setDevDate(this.value)"
          style="font-size:11px;background:transparent;border:none;color:#fed7aa;outline:none;cursor:pointer;width:110px">
        <button onclick="devPushDummy()" title="현재 반 전체 학생에게 이 날짜로 랜덤 더미 데이터 생성"
          style="font-size:10px;background:#92400e;border:1px solid #fb923c;border-radius:4px;color:#fed7aa;cursor:pointer;padding:2px 6px;white-space:nowrap">🎲 더미</button>
        <button onclick="setDevDate('')" style="font-size:10px;background:none;border:none;color:#fb923c;cursor:pointer;padding:0;line-height:1">✕</button>
      </div>`
    :`<button onclick="setDevDate('${(()=>{const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');})()}')"
        style="font-size:10px;background:var(--panel2,#2a2a3a);border:1px solid var(--border);border-radius:6px;color:var(--sub);padding:3px 8px;cursor:pointer">
        🔧 날짜 변경
      </button>`;
  return `<div class="topbar"><div><div style="font-size:14px;font-weight:700">${esc(title)}</div>${sub?`<div style="font-size:11px;color:${_devDate?'#fb923c':'var(--sub)'};margin-top:1px">${esc(sub)}</div>`:''}</div>${devBadge}</div>`;
}

function render(){renderSb();renderMain();}
function renderMain(){
  const mc=document.getElementById('mc');if(!mc)return;
  if(wizardActive){renderWizard(mc);return;}
  if(activeTab==='input')renderInput(mc);
  else if(activeTab==='scores')renderScores(mc);
  else renderSettings(mc);
}
