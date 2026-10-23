// Real Chromium rendering with deterministic API fixtures. This is not a live-provider test.
const { chromium } = require('playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const path = require('node:path');
const codes = ['E','KBL','JP_B1','JP_B2','PBA_GOV','ABA','ECW','FEC','UKR','TR_BSL'];
const entry = (code, i) => ({fixture:{event_id:code+'_1',league:code,home:'H',away:'A',home_name:code==='UKR'?'PRYKARPATTIA-GOVERLA-KFV (Iv-Frankivsk)':'Türk Telekom Basketbol',away_name:'Yukatel Denizli Basket',start_utc:'2099-10-25T15:00Z',captured_at:new Date().toISOString(),source_url:'https://example.org'},prediction:{ev_kazanir:.7,ev_skor:90,dep_skor:80,toplam:170,fark:10,toplam_80:[140,200],fark_80:[-5,25],model:'fixture model',data_quality:{issues:[]}},selected:i%2===0,threshold_passed:true,source_confirmation_fresh:true,record_status:'existing_immutable',total_estimates:[{line:170.5,over:.49,under:.51}]});
const basketball = {sample:false,job:{status:'idle',message:'Ready'},report_age_minutes:1,results:[],report:{checked_at_utc:'2026-10-23T12:00Z',upcoming:codes.map(entry),performance:{settled_games:1,pending_games:1,winner_accuracy:1,mean_score_mae:3.5},sources:{TR_BSL:{status:'failed',error:'Fixture source unavailable; prior snapshot retained'}},skipped:[]}};
basketball.results=[{fixture:entry('TR_BSL',0).fixture,prediction:entry('TR_BSL',0).prediction,game:{status:'final',actual_home:85,actual_away:82,winner_correct:true,home_absolute_error:5,away_absolute_error:2,total_absolute_error:3,margin_absolute_error:7,total_in_80:true,margin_in_80:false}},{fixture:entry('UKR',0).fixture,prediction:entry('UKR',0).prediction,game:{status:'pending'}}];
const football={sample:true,job:{status:'idle',message:'Ready'},leagues:{TR1:'Turkish Süper Lig',BE1:'Belgian Pro League',GR1:'Greek Super League',SC1:'Scottish Premiership'},report:{checked_at_utc:'2026-10-23T12:00Z',pending:1,publisher_performance:{games:1},source_errors:[],skipped:[],forecasts:['pending','publisher_final'].map((status,i)=>({status,fixture:{event_id:'football'+i,league:i?'BE1':'TR1',date:'2099-10-25',home_name:i?'Club Brugge':'Galatasaray',away_name:i?'Anderlecht':'Fenerbahçe',source_url:'https://github.com/openfootball/football.json'},prediction:{model:'fixture model',expected_home_goals:1.5,expected_away_goals:1,probabilities:{home:.45,draw:.3,away:.25},over:{'1.5':.7,'2.5':.4,'3.5':.2},both_teams_score:.5,total_goals_80:[0,5],issues:[]},result:i?{actual_home:2,actual_away:1,winner_correct:true,total_absolute_error:.5,margin_absolute_error:.5}:null}))}};
(async()=>{
 const directory=process.env.VISUAL_OUTPUT||'.runtime/visual';fs.mkdirSync(directory,{recursive:true});
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{})});
 const evidence={browser:browser.version(),api:'deterministic intercepted fixtures',live_server_verified:false,viewports:[],checks:[]};
 try{
  for(const viewport of [{width:1440,height:900},{width:390,height:844},{width:320,height:844}]){
   const page=await browser.newPage({viewport});const errors=[];let failFootballPoll=false;page.on('pageerror',e=>errors.push(e.message));
   await page.route('http://127.0.0.1:8765/**',async route=>{
    const url=new URL(route.request().url());let body,type='application/json';
    if(url.pathname==='/api/state')body=JSON.stringify(basketball);
    else if(url.pathname==='/api/football'){
      if(failFootballPoll)return route.fulfill({status:503,contentType:type,body:'{}'});
      body=JSON.stringify(football);
    }
    else if(url.pathname==='/api/football/run'){body=JSON.stringify({error:'Controlled request error'});return route.fulfill({status:409,contentType:type,body});}
    else {const name=url.pathname==='/'?'index.html':url.pathname==='/football'?'football.html':url.pathname.slice(1);const file=path.join('src/bbtahmin/ui',name);if(!fs.existsSync(file))return route.fulfill({status:404,body:'Not found'});body=fs.readFileSync(file,'utf8').replace('__CSRF_TOKEN__','test');type=name.endsWith('.css')?'text/css':name.endsWith('.js')?'text/javascript':'text/html';}
    return route.fulfill({status:200,contentType:type,body});
   });
   await page.goto('http://127.0.0.1:8765/');await page.waitForSelector('.match-card');
   assert.equal(await page.locator('#run-leagues input').count(),10);assert.equal(await page.locator('#league-filter option').count(),11);
   for(const code of codes){await page.selectOption('#league-filter',code);assert.equal(await page.locator('.match-card').count(),1);}
   await page.selectOption('#league-filter','UKR');await page.locator('.match-card summary').click();await page.waitForTimeout(2200);assert.equal(await page.locator('.match-card details').getAttribute('open'),'');
   await page.screenshot({path:path.join(directory,`basketball-${viewport.width}.png`),fullPage:true});
   await page.fill('#search','no matching team');assert.equal(await page.locator('#empty').isVisible(),true);await page.fill('#search','');
   await page.selectOption('#league-filter','');await page.check('#passed-only');assert.equal(await page.locator('.match-card').count(),5);
   assert.match(await page.locator('#results-body').innerText(),/85.*82/);assert.match(await page.locator('#results-body').innerText(),/Pending/);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   await page.goto('http://127.0.0.1:8765/football');await page.waitForSelector('.forecast-card');
   await page.selectOption('#result-status','pending');assert.equal(await page.locator('.forecast-card').count(),1);
   await page.selectOption('#result-status','publisher_final');assert.equal(await page.locator('.forecast-card').count(),1);
   await page.selectOption('#result-status','');await page.locator('.forecast-card details summary').first().click();
   failFootballPoll=true;await page.evaluate(()=>poll());assert.match(await page.locator('#status').innerText(),/Connection unavailable/);
   failFootballPoll=false;await page.evaluate(()=>poll());assert.equal(await page.locator('#status').innerText(),'Ready');
   await page.locator('#saved').click();await page.waitForTimeout(3200);assert.match(await page.locator('#status').innerText(),/Controlled request error/);
   assert.equal(await page.locator('#saved').isDisabled(),false);
   await page.screenshot({path:path.join(directory,`football-${viewport.width}.png`),fullPage:true});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);assert.deepEqual(errors,[]);
   evidence.viewports.push(viewport);await page.close();
  }
  evidence.checks=['10 basketball leagues and both domestic filters','selected and empty views','expanded details across polling','pending and final results','football status filters','persistent request errors','polling errors clear after recovery','no page overflow at 1440/390/320'];
  fs.writeFileSync(path.join(directory,'validation.json'),JSON.stringify(evidence,null,2));console.log(JSON.stringify(evidence));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
