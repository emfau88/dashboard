const {test}=require('node:test');
const assert=require('node:assert/strict');
const {scale,samples,daily,model}=require('../assets/charts.js');
test('Bewertungsskalen umfassen alle Werte und bleiben innerhalb der Portalskala',()=>{
  for(const maximum of [5,10])for(const values of [[0],[maximum],[maximum-.01,maximum],[0,.01],[2.77,2.78],[1.2,3.7]]){
    const axis=scale(values,{ratingMax:maximum});
    assert.ok(axis.min<=Math.min(...values));assert.ok(axis.max>=Math.max(...values));
    assert.ok(axis.min>=0&&axis.max<=maximum&&axis.max>axis.min);
    assert.ok(axis.max-axis.min>=maximum*.02-1e-8);
  }
  assert.deepEqual(scale([2.77,2.78],{ratingMax:5,full:true}),{min:0,max:5,step:1.25});
  assert.ok(scale([2.77,2.78],{ratingMax:5}).max-scale([2.77,2.78],{ratingMax:5}).min<.25);
});
test('Fehlende Messwerte erzeugen weder Nullen noch erfundene Tageswerte',()=>{
  const points=samples([{date:'2026-10-01',plays:100},{date:'2026-10-02',plays:null},{date:'2026-10-04',plays:160},{date:'2026-10-05',plays:155}],'plays');
  const growth=daily(points);assert.equal(growth.length,2);
  assert.equal(growth[0].value,20);assert.equal(growth[0].days,3);
  assert.equal(growth[1].value,-5);
  const axis=scale(growth.map(p=>p.value),{zero:true});assert.ok(axis.min<=-5&&axis.max>=20);
  const correction=scale([-5],{zero:true});assert.ok(correction.min<=-5&&correction.max>=0);
});
test('Zeitraum ist datumsbasiert und nutzt den vorherigen Messpunkt für Tageszuwachs',()=>{
  const history=[{date:'2026-09-01',plays:10},{date:'2026-10-14',plays:53},{date:'2026-10-28',plays:81}];
  const result=model(history,{key:'plays'},{period:'14',mode:'daily'});
  assert.equal(result.points.length,1);assert.equal(result.points[0].value,2);assert.equal(result.points[0].days,14);
  assert.equal(model(history,{key:'plays'},{period:'all',mode:'total'}).points.length,3);
});
test('Leere, konstante und einzelne Messreihen bleiben endlich',()=>{
  assert.equal(model([],{key:'rating'},{period:'30'}).scale,null);
  for(const value of [0,100,2.77]){const axis=scale([value]);assert.ok(Number.isFinite(axis.min)&&axis.max>axis.min);}
});
