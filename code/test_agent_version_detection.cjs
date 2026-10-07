const fs=require('fs'),vm=require('vm'),assert=require('assert');
const ctx={instructor:{id:'tester'},dbPath:'campus/test',esc:s=>String(s),Date};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(__dirname+'/public/v2.6.1/js/app-report.js','utf8'),ctx);
const now=Date.now(), beat=version=>({ts:now,versionTs:now,version});
for(const [data,state] of [[beat('0.11.4'),'latest'],[beat('0.11.10'),'latest'],[beat('0.10.99'),'old'],
 [beat('bad'),'unknown'],[{ts:now},'unknown'],[{...beat('0.11.4'),versionTs:now-1},'unknown'],
 [{...beat('0.11.4'),ts:now-90000},'offline'],[null,'offline']]){
 assert.equal(ctx._classifyAgent(data,now).state,state);
}
(async()=>{
 let html='',guides=0,calls=0;
 ctx._rpModal=s=>{html=s};ctx.closeRpModal=()=>{};ctx._agentGuide=()=>{guides++};
 ctx.fbGet=async()=>beat('0.11.1');
 assert.equal(await ctx._agentCheck(()=>calls++),false);
 assert(html.includes('更新')===false && html.includes('업데이트 권장') && html.includes('v0.11.1'));
 assert.equal(calls,0);ctx._rpProceed();assert.equal(calls,1);
 assert.equal(await ctx._agentCheck(()=>calls++),true);assert.equal(calls,1);
 ctx.instructor.id='other';assert.equal(await ctx._agentCheck(()=>{}),false);
 ctx.fbGet=async()=>({ts:Date.now()});assert.equal(await ctx._agentCheck(()=>{}),false);
 assert(html.includes('버전을 확인할 수 없습니다'));
 ctx.fbGet=async()=>null;assert.equal(await ctx._agentCheck(()=>{}),false);assert.equal(guides,1);
 ctx.fbGet=async()=>{throw Error('network')};assert.equal(await ctx._agentCheck(()=>{}),true);
 assert.equal(await ctx._agentAlive(),null);
 ctx.fbGet=async()=>beat('0.12.0');assert.equal(await ctx._agentCheck(()=>{}),true);
 console.log('Version classification, modal continuation, reminder scope, offline and network failure passed');
})().catch(e=>{console.error(e);process.exitCode=1});
