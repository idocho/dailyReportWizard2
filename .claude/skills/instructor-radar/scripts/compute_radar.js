#!/usr/bin/env node
/*
 * compute_radar.js — 강사(또는 전체) 담당 학생들의 역량 레이더 5축을 실저장 데이터로 계산.
 *
 * 사용:
 *   node compute_radar.js "조이도"                 # 해당 강사 담당 학생
 *   node compute_radar.js --all                    # obs 있는 전체 학생
 *   node compute_radar.js "조이도" --config <path> # config.json 경로 지정
 *
 * 자격: code/dist/config.json 의 firebase_url·firebase_path (읽기 secret 불요).
 * 출력: stdout JSON 배열 [{nameKey,name,N,attitude,engage,autonomy,understand,achievement,tests}]
 *
 * ⚠️ 축 계산은 dailyReportAnalyzer/analyzer.html 의 computeWindowData 를 미러링한다.
 *    analyzer.html 공식이 바뀌면 이 파일도 같이 갱신할 것 (references/radar_formulas.md 참조).
 *    현재 기준: ANALYZER_REQUIREMENTS 문서 v2.9 (2026-06-14).
 */
const https=require('https'),fs=require('fs'),pathm=require('path');

function resolveConfig(){
  const i=process.argv.indexOf('--config');
  if(i>=0&&process.argv[i+1])return process.argv[i+1];
  const guesses=[
    pathm.join(process.cwd(),'code/dist/config.json'),
    pathm.join(__dirname,'../../../../code/dist/config.json'),
    pathm.join(__dirname,'../../../../../dailyReportWizard2/code/dist/config.json'),
  ];
  for(const g of guesses) if(fs.existsSync(g)) return g;
  throw new Error('config.json 못 찾음 — --config 로 경로 지정');
}
const cfg=JSON.parse(fs.readFileSync(resolveConfig(),'utf8'));
const base=(cfg.firebase_url||'').replace(/\/$/,''), fbpath=(cfg.firebase_path||'').replace(/^\/|\/$/g,'');
if(!base||!fbpath){console.error('firebase_url/path 없음');process.exit(1);}
const get=(node)=>new Promise((res)=>{
  const url=`${base}/${encodeURIComponent(fbpath)}/${encodeURIComponent(node)}.json`;
  https.get(url,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d))}catch(e){res(null)}});}).on('error',()=>res(null));
});

function tagArr(v){if(!v)return[];if(Array.isArray(v))return v.filter(Boolean);const vals=Object.values(v);if(vals.every(x=>typeof x==='string'))return vals;return Object.keys(v).filter(k=>v[k]);}
function scores(nameKey,allScores){
  const result=[];
  const collect=(t)=>{if(!t)return;const meta=t.meta||t;const myRaw=(t.students||{})[nameKey];if(myRaw==null||myRaw==='')return;
    const allVals=Object.values(t.students||{}).filter(v=>v!==''&&v!=null&&!isNaN(v)).map(Number);
    const myScore=Number(myRaw),maxScore=meta.max_score||100,cl=v=>Math.max(0,Math.min(100,Math.round(v)));
    const myPct=cl(myScore/maxScore*100);const rank=allVals.filter(s=>s>myScore).length+1;const cs=allVals.length;
    const percentile=cs>1?Math.round((cs-rank)/(cs-1)*100):50;result.push({date:meta.date,myPct,percentile});};
  for(const bs of Object.values(allScores.weekly||{}))for(const ts of Object.values(bs||{}))for(const t of Object.values(ts||{}))collect(t);
  for(const bs of Object.values(allScores.achievement||{}))for(const ts of Object.values(bs||{}))for(const t of Object.values(ts||{}))collect(t);
  return result.sort((a,b)=>String(a.date).localeCompare(String(b.date)));
}
const hwGrade={done:100,most:80,half:50,little:25,none:0};
function axes(obsForStudent,scoresList){
  const condOrder=['bad','low','normal','good','great'],undOrder=['hard','confused','normal_u','good','top'],hwOrder=['none','little','half','most','done'];
  const m={};
  for(const subject of Object.keys(obsForStudent||{})){
    for(const[date,data] of Object.entries(obsForStudent[subject]||{})){
      if(!m[date]){m[date]={...data};m[date].__hwAll=(data.assign_grade!=null&&data.assign_grade!=='')?[data.assign_grade]:[];}
      else{
        const idx=(arr,v,d)=>{const i=arr.indexOf(v);return i<0?arr.indexOf(d):i;};
        if(idx(condOrder,data.condition,'normal')<idx(condOrder,m[date].condition,'normal'))m[date].condition=data.condition;
        if(idx(undOrder,data.understand,'normal_u')<idx(undOrder,m[date].understand,'normal_u'))m[date].understand=data.understand;
        if(idx(hwOrder,data.assign_grade,'done')<idx(hwOrder,m[date].assign_grade,'done'))m[date].assign_grade=data.assign_grade;
        if(data.assign_grade!=null&&data.assign_grade!=='')(m[date].__hwAll||(m[date].__hwAll=[])).push(data.assign_grade);
        for(const f of['understand_sub','engage','caution','extra','highlight']){const a=tagArr(m[date][f]),b=tagArr(data[f]),u=[...new Set([...a,...b])];if(u.length)m[date][f]=u;}
      }
    }
  }
  const sess=Object.entries(m).sort((a,b)=>a[0].localeCompare(b[0]));const N=sess.length;
  const cond={great:0,good:0,normal:0,low:0,bad:0},und={top:0,good:0,normal_u:0,confused:0,hard:0};
  const undSub={self_solve:0,retry:0,confused:0},eng={present:0,question:0,help:0,preview:0,error_fix:0,deep_try:0};
  const caut={sleepy:0,chat:0,attitude:0,late:0,slow:0,calc_miss:0,writeup_weak:0},extra={self_study:0,weekly_test:0,retest:0};
  const hl={perfect:0,improved:0,mastered:0,effort:0,process_good:0};
  for(const[,d] of sess){
    if(d.condition&&cond[d.condition]!==undefined)cond[d.condition]++;
    if(d.understand&&und[d.understand]!==undefined)und[d.understand]++;
    for(const k of tagArr(d.understand_sub))if(undSub[k]!==undefined)undSub[k]++;
    for(const k of tagArr(d.engage))if(eng[k]!==undefined)eng[k]++;
    for(const k of tagArr(d.caution))if(caut[k]!==undefined)caut[k]++;
    for(const k of tagArr(d.extra))if(extra[k]!==undefined)extra[k]++;
    for(const k of tagArr(d.highlight))if(hl[k]!==undefined)hl[k]++;
  }
  const safe=N||1;
  const condScore={great:95,good:80,normal:65,low:45,bad:25};
  const cr=Object.values(cond).reduce((a,b)=>a+b,0);
  const condAvg=cr>0?['great','good','normal','low','bad'].reduce((s,k)=>s+condScore[k]*(cond[k]||0),0)/cr:65;
  const cautPenalty=(caut.late*8+caut.sleepy*5+caut.chat*6+caut.attitude*10)/safe;
  const attitude=Math.max(20,Math.min(100,Math.round(condAvg-cautPenalty)));
  const engRate=(eng.present*14+eng.deep_try*12+eng.question*10+eng.help*6)/safe;
  const engage=50+Math.min(50,Math.round(engRate*5));
  const hwScores=sess.flatMap(([,d])=>(d.__hwAll&&d.__hwAll.length?d.__hwAll:(d.assign_grade!=null?[d.assign_grade]:[])).map(g=>hwGrade[g]).filter(v=>v!==undefined));
  const hwAvg=hwScores.length?hwScores.reduce((a,b)=>a+b,0)/hwScores.length:50;
  const autoBehavior=Math.min(15,Math.round(eng.preview/safe*18+extra.self_study/safe*15+eng.error_fix/safe*12+undSub.retry/safe*10));
  const autonomy=Math.min(100,Math.round(hwAvg*0.85)+autoBehavior);
  const undScore={top:95,good:80,normal_u:65,confused:45,hard:28};
  const ur=['top','good','normal_u','confused','hard'].reduce((s,k)=>s+(und[k]||0),0);
  const undAvg=ur>0?['top','good','normal_u','confused','hard'].reduce((s,k)=>s+undScore[k]*(und[k]||0),0)/ur:65;
  const undBonus=Math.min(15,Math.round(undSub.self_solve/safe*10+undSub.retry/safe*7+hl.mastered/safe*8+hl.process_good/safe*8));
  const undPenalty=Math.min(8,Math.round(caut.writeup_weak/safe*8));
  const understand=Math.max(20,Math.min(100,Math.round(undAvg+undBonus-undPenalty)));
  const rN=Math.min(3,scoresList.length),recent=scoresList.slice(-rN);
  const pctAvg=rN>0?recent.reduce((a,s)=>a+s.percentile,0)/rN:0;
  const rawAvg=rN>0?recent.reduce((a,s)=>a+s.myPct,0)/rN:0;
  const hlBonus=Math.min(10,Math.round((hl.perfect+hl.improved+hl.effort)/safe*15));
  const achievement=scoresList.length>0?Math.min(100,Math.round(0.6*pctAvg+0.4*rawAvg+hlBonus)):50;
  return{N,attitude,engage,autonomy,understand,achievement};
}

(async()=>{
  const wantAll=process.argv.includes('--all');
  const instructor=process.argv.slice(2).find(a=>!a.startsWith('--')&&process.argv[process.argv.indexOf(a)-1]!=='--config');
  if(!wantAll&&!instructor){console.error('강사명 또는 --all 필요');process.exit(1);}
  const[history,students,obs,allScores]=await Promise.all([get('history'),get('students'),get('obs'),get('scores')]);
  let keys;
  if(wantAll){ keys=Object.keys(obs||{}); }
  else{
    const set=new Set();
    for(const[nk,days] of Object.entries(history||{})){if(typeof days!=='object')continue;for(const rec of Object.values(days)){if(rec&&rec.instructor===instructor){set.add(nk);break;}}}
    keys=[...set];
  }
  const out=[];
  for(const nk of keys){
    const sd=students&&students[nk];const name=(sd&&(sd.name||sd))||nk;
    const sl=scores(nk,allScores||{});
    const a=axes((obs||{})[nk]||{},sl);
    if(a.N===0&&sl.length===0)continue;
    out.push({nameKey:nk,name:typeof name==='string'?name:nk,...a,tests:sl.length});
  }
  out.sort((a,b)=>b.N-a.N);
  process.stdout.write(JSON.stringify(out,null,0)+'\n');
  console.error(`[radar] ${wantAll?'전체':instructor} · ${out.length}명 계산`);
})();
