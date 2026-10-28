/* Gemeinsame Messwertdiagramme. Keine Glättung und keine erfundenen Tageswerte. */
(function(root){
  'use strict';
  const DAY=86400000, registry=new Map();
  let sequence=0;
  const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const date=value=>new Date(value+'T12:00:00Z').toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit',year:'2-digit',timeZone:'UTC'});
  const number=(value,digits=2)=>value.toLocaleString('de-DE',{maximumFractionDigits:digits});
  function samples(history,key){
    return history.filter(p=>Number.isFinite(p[key])&&Number.isFinite(Date.parse(p.date+'T12:00:00Z')))
      .map(p=>({...p,value:p[key],time:Date.parse(p.date+'T12:00:00Z')})).sort((a,b)=>a.time-b.time);
  }
  function scale(values,{ratingMax=null,full=false,zero=false}={}){
    const low=Math.min(...values),high=Math.max(...values);
    if(ratingMax&&full)return {min:0,max:ratingMax,step:ratingMax/4};
    const minimum=ratingMax?ratingMax*.02:1;
    const span=Math.max(high-low,minimum);
    let min=zero?Math.min(0,low):Math.max(0,low-span*.15),max=(zero?Math.max(0,high):high)+span*.15;
    if(max-min<minimum){min=Math.max(0,(low+high-minimum)/2);max=min+minimum;}
    const rough=(max-min)/4,power=10**Math.floor(Math.log10(rough));
    const rawStep=[1,2,2.5,5,10].map(n=>n*power).find(n=>n>=rough);
    const step=!ratingMax&&!zero?Math.max(1,Math.ceil(rawStep)):rawStep;
    min=Math.floor(min/step)*step;max=Math.ceil(max/step)*step;
    if(ratingMax){
      min=Math.max(0,min);max=Math.min(ratingMax,max);
      if(max-min<minimum){min=Math.max(0,Math.floor((max-minimum)/step)*step);max=Math.min(ratingMax,Math.max(max,min+minimum));}
    }
    if(max===min)max=min+step;
    return {min,max,step};
  }
  function daily(points){
    return points.slice(1).map((p,i)=>{
      const previous=points[i],days=(p.time-previous.time)/DAY;
      return {...p,value:(p.value-previous.value)/days,days,previous:previous.date};
    }).filter(p=>p.days>0);
  }
  function model(history,options,state){
    const all=samples(history,options.key),end=all.at(-1)?.time;
    const calculated=state.mode==='daily'?daily(all):all;
    const points=calculated.filter(p=>state.period==='all'||p.time>=end-(Number(state.period)-1)*DAY);
    return {points,scale:points.length?scale(points.map(p=>p.value),{ratingMax:options.ratingMax,full:state.scale==='full',zero:state.mode==='daily'}):null};
  }
  function render(history,options){
    const id='measurement-'+(++sequence);
    const entry={history,options,state:{period:'30',scale:'detail',mode:'total'},selected:null};
    registry.set(id,entry);
    return '<section class="measurement" id="'+id+'" aria-label="'+escape(options.title)+'">'+body(entry)+'</section>';
  }
  function body(entry){
    const {options,state}=entry,{points,scale:axis}=model(entry.history,options,state);
    const select=(field,label,items)=>'<label>'+label+' <select data-chart-control="'+field+'">'+items.map(([value,text])=>'<option value="'+value+'"'+(state[field]===value?' selected':'')+'>'+text+'</option>').join('')+'</select></label>';
    const controls='<div class="measurement-head"><strong>'+escape(options.title)+'</strong><div class="measurement-controls">'+
      select('period','Zeitraum',[['14','14 Tage'],['30','30 Tage'],['90','90 Tage'],['all','Gesamt']])+
      (options.key==='plays'?select('mode','Ansicht',[['total','Gesamtaufrufe'],['daily','Zuwachs / Tag']]):'')+
      (options.ratingMax?select('scale','Skala',[['detail','Detail'],['full','0–'+options.ratingMax]]):'')+'</div></div>';
    if(!points.length)return controls+'<p class="measurement-note">'+(state.mode==='daily'?'Für den Zuwachs sind mindestens zwei Messpunkte nötig.':'Noch keine Messwerte in diesem Zeitraum.')+'</p>';
    const first=points[0],last=points.at(-1),digits=options.ratingMax?2:state.mode==='daily'?1:0;
    const format=v=>number(v,digits),unit=options.ratingMax?' / '+options.ratingMax:state.mode==='daily'?' Plays/Tag':options.key==='plays'?' Plays':' Likes';
    const difference=last.value-first.value;
    const signed=v=>(v>0?'+':'')+format(v);
    const stat=points.length===1?'Erster Messpunkt':state.mode==='daily'?'Spitze: '+format(Math.max(...points.map(p=>p.value)))+' Plays/Tag':difference===0?'Unverändert seit '+date(first.date):signed(difference)+(options.ratingMax?' Punkte':'')+' seit '+date(first.date);
    const summary='<div class="measurement-summary"><span class="measurement-value">'+format(last.value)+'<small>'+unit+'</small></span><span class="'+(difference>0?'positive':difference<0?'negative':'')+'">'+stat+'</span></div>';
    const x=p=>first.time===last.time?300:8+(p.time-first.time)/(last.time-first.time)*584;
    const y=p=>232-(p.value-axis.min)/(axis.max-axis.min)*224;
    const ticks=[];for(let value=axis.min;value<=axis.max+axis.step/100;value+=axis.step)ticks.push(Number(value.toFixed(8)));
    if(Math.abs(ticks.at(-1)-axis.max)>1e-8)ticks.push(axis.max);
    const grid=ticks.map(value=>'<line x1="8" x2="592" y1="'+y({value})+'" y2="'+y({value})+'" class="measurement-grid"/>').join('');
    const axes=ticks.map(value=>'<span style="top:'+((y({value})/240)*100)+'%">'+number(value,options.ratingMax?2:2)+'</span>').join('');
    const lines=points.slice(1).map((p,i)=>'<line class="measurement-line'+((p.time-points[i].time)>DAY*1.5?' gap':'')+'" x1="'+x(points[i])+'" y1="'+y(points[i])+'" x2="'+x(p)+'" y2="'+y(p)+'"/>').join('');
    const zeroY=y({value:0});
    const bars=points.map(p=>'<line class="measurement-bar" x1="'+x(p)+'" x2="'+x(p)+'" y1="'+zeroY+'" y2="'+y(p)+'"/>').join('');
    const dots=points.map((p,i)=>'<circle class="measurement-dot" data-point="'+i+'" cx="'+x(p)+'" cy="'+y(p)+'" r="3"><title>'+date(p.date)+': '+format(p.value)+unit+'</title></circle>').join('');
    entry.points=points;
    entry.selected=Math.min(entry.selected??points.length-1,points.length-1);
    const middleDate=new Date((first.time+last.time)/2).toISOString().slice(0,10);
    const plot='<div class="measurement-plot"><div class="measurement-axis" aria-hidden="true">'+axes+'</div><div class="measurement-canvas"><svg viewBox="0 0 600 240" preserveAspectRatio="none" role="img" aria-label="'+escape(options.title+': '+date(first.date)+' bis '+date(last.date)+', Skala '+number(axis.min)+' bis '+number(axis.max))+'">'+grid+(state.mode==='daily'?bars:lines)+dots+'</svg><div class="measurement-dates"><span>'+date(first.date)+'</span><span>'+(points.length>2?date(middleDate):'')+'</span><span>'+(points.length>1?date(last.date):'')+'</span></div></div></div>';
    const selector='<label class="measurement-scrubber">Messpunkt auswählen <input type="range" min="0" max="'+(points.length-1)+'" value="'+entry.selected+'" step="1" aria-label="Messpunkt für '+escape(options.title)+' auswählen"></label><output class="measurement-readout" aria-live="polite">'+readout(entry)+'</output>';
    const note=(options.ratingMax?'Skalenausschnitt '+number(axis.min)+'–'+number(axis.max)+' von '+options.ratingMax+' · ':state.mode==='total'?'Skalenausschnitt '+number(axis.min)+'–'+number(axis.max)+' · ':'')+points.length+' Messpunkte. '+(state.mode==='daily'?'Bei Lücken: durchschnittlicher Zuwachs pro Tag im Messintervall; negative Werte sind Zählerkorrekturen.':'Gestrichelte Abschnitte überbrücken fehlende Tage; dazwischen liegen keine Messwerte.');
    const table='<details class="measurement-table"><summary>Messwerte anzeigen</summary><div><table><thead><tr><th>Datum</th><th>Wert'+(options.ratingMax?' / '+options.ratingMax:'')+'</th><th>Änderung zum Vorwert</th></tr></thead><tbody>'+points.map((p,i)=>'<tr><td>'+date(p.date)+'</td><td>'+format(p.value)+'</td><td>'+(i?signed(p.value-points[i-1].value):'—')+'</td></tr>').join('')+'</tbody></table></div></details>';
    return controls+summary+plot+selector+'<p class="measurement-note">'+note+'</p>'+table;
  }
  function readout(entry){
    const p=entry.points[entry.selected],previous=entry.points[entry.selected-1];
    const suffix=entry.options.ratingMax?' / '+entry.options.ratingMax:entry.state.mode==='daily'?' Plays/Tag':entry.options.key==='plays'?' Plays':' Likes';
    return '<strong>'+date(p.date)+' · '+number(p.value)+suffix+'</strong>'+(previous?' · Δ '+(p.value-previous.value>0?'+':'')+number(p.value-previous.value)+' zum Vorwert':' · erster Wert im Zeitraum')+(p.days>1?' · Ø über '+p.days+' Tage':'')+(p.source==='manual'?' · manuell erfasst':'');
  }
  if(typeof document!=='undefined'){
    document.addEventListener('change',event=>{
      const control=event.target.closest('[data-chart-control]'),chart=control?.closest('.measurement');
      if(!chart)return;const entry=registry.get(chart.id);if(!entry)return;
      entry.state[control.dataset.chartControl]=control.value;entry.selected=null;
      const field=control.dataset.chartControl;chart.innerHTML=body(entry);chart.querySelector('[data-chart-control="'+field+'"]').focus();
    });
    document.addEventListener('input',event=>{
      if(!event.target.matches('.measurement input[type=range]'))return;
      const chart=event.target.closest('.measurement'),entry=registry.get(chart.id);entry.selected=Number(event.target.value);
      chart.querySelector('output').innerHTML=readout(entry);
      chart.querySelectorAll('[data-point]').forEach(dot=>dot.classList.toggle('selected',Number(dot.dataset.point)===entry.selected));
    });
    document.addEventListener('pointermove',event=>{
      if(event.pointerType==='touch'&&event.buttons===0)return;
      const svg=event.target.closest('.measurement svg');if(!svg)return;
      const chart=svg.closest('.measurement'),entry=registry.get(chart.id),rect=svg.getBoundingClientRect();
      const ratio=Math.max(0,Math.min(1,((event.clientX-rect.left)/rect.width*600-8)/584));
      const time=entry.points[0].time+ratio*(entry.points.at(-1).time-entry.points[0].time);
      entry.selected=entry.points.reduce((best,p,i)=>Math.abs(p.time-time)<Math.abs(entry.points[best].time-time)?i:best,0);
      const input=chart.querySelector('input');input.value=entry.selected;input.dispatchEvent(new Event('input',{bubbles:true}));
    });
  }
  root.GameCharts={render,scale,samples,daily,model};
  if(typeof module!=='undefined')module.exports=root.GameCharts;
})(globalThis);
