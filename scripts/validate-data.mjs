import fs from 'node:fs';

const data=JSON.parse(fs.readFileSync(new URL('../data.json',import.meta.url),'utf8'));
const errors=[];
const warnings=[];
const allowedStatuses=new Set(['development','planned','not_submitted','review','changes_requested','approved','live','rejected']);
const allowedEventTypes=new Set(['submission','change_request','resubmission','acceptance','publication','rejection']);
const dateFields=['submitted','changeRequested','revisionSubmitted','accepted','published','rejected','playsAsOf'];
const datePattern=/^\d{4}-\d{2}-\d{2}$/;

function error(message){errors.push(message)}
function warn(message){warnings.push(message)}
function isValidDate(value){
  if(!datePattern.test(value))return false;
  const date=new Date(`${value}T12:00:00Z`);
  return !Number.isNaN(date.valueOf())&&date.toISOString().slice(0,10)===value;
}
function assertOrder(first,second,label){
  if(first&&second&&first>second)error(`${label}: ${first} liegt nach ${second}.`);
}

if(!isValidDate(data.meta?.updated||''))error('meta.updated fehlt oder ist ungültig.');

const portalIds=data.portals.map(portal=>portal.id);
if(new Set(portalIds).size!==portalIds.length)error('Portal-IDs sind nicht eindeutig.');
const gameIds=data.games.map(game=>game.id);
if(new Set(gameIds).size!==gameIds.length)error('Spiel-IDs sind nicht eindeutig.');

for(const portal of data.portals){
  for(const gameId of gameIds){
    if(!(gameId in portal.fits))error(`${portal.id}: Portal-Eignung für ${gameId} fehlt.`);
  }
}

for(const game of data.games){
  if(!allowedStatuses.has(game.status))error(`${game.id}: ungültiger Spielstatus ${game.status}.`);
  for(const portalId of portalIds){
    const placement=game.platforms[portalId];
    if(!placement){error(`${game.id}: Portal ${portalId} fehlt.`);continue}
    if(!allowedStatuses.has(placement.status))error(`${game.id}/${portalId}: ungültiger Status ${placement.status}.`);
    for(const field of dateFields){
      const value=placement[field];
      if(value&&!isValidDate(value))error(`${game.id}/${portalId}: ${field} ist kein gültiges ISO-Datum.`);
      if(value&&data.meta?.updated&&value>data.meta.updated)error(`${game.id}/${portalId}: ${field} liegt nach meta.updated.`);
    }
    assertOrder(placement.submitted,placement.accepted,`${game.id}/${portalId} Einreichung/Annahme`);
    assertOrder(placement.submitted,placement.changeRequested,`${game.id}/${portalId} Einreichung/Änderungsanforderung`);
    assertOrder(placement.submitted,placement.revisionSubmitted,`${game.id}/${portalId} Einreichung/Überarbeitung`);
    assertOrder(placement.submitted,placement.published,`${game.id}/${portalId} Einreichung/Veröffentlichung`);
    assertOrder(placement.submitted,placement.rejected,`${game.id}/${portalId} Einreichung/Ablehnung`);
    assertOrder(placement.accepted,placement.published,`${game.id}/${portalId} Annahme/Veröffentlichung`);
    if(placement.status==='live'&&!placement.published)warn(`${game.id}/${portalId}: Live-Status ohne Veröffentlichungsdatum.`);
    if(placement.acceptanceConfirmed!=null&&typeof placement.acceptanceConfirmed!=='boolean')error(`${game.id}/${portalId}: acceptanceConfirmed muss ein Boolean sein.`);
    if(placement.revisionSubmittedConfirmed!=null&&typeof placement.revisionSubmittedConfirmed!=='boolean')error(`${game.id}/${portalId}: revisionSubmittedConfirmed muss ein Boolean sein.`);
    if(placement.status==='live'&&!placement.accepted)warn(placement.acceptanceConfirmed?`${game.id}/${portalId}: Annahme bestätigt, genaues Datum fehlt.`:`${game.id}/${portalId}: Annahmedatum ist nicht bekannt.`);
    if(placement.status==='rejected'&&!placement.rejected)warn(`${game.id}/${portalId}: Ablehnungsdatum fehlt.`);
    if(placement.status==='approved'&&!placement.accepted)warn(`${game.id}/${portalId}: Freigabe bestätigt, genaues Datum fehlt.`);
    if(placement.status==='changes_requested'&&!placement.changeRequested)warn(`${game.id}/${portalId}: Änderungsanforderung bestätigt, genaues Datum fehlt.`);
    for(const event of placement.previousEvents||[]){
      if(!allowedEventTypes.has(event.type))error(`${game.id}/${portalId}: unbekannter historischer Ereignistyp ${event.type}.`);
      if(!isValidDate(event.date||''))error(`${game.id}/${portalId}: historisches Ereignis ohne gültiges ISO-Datum.`);
      if(event.date&&data.meta?.updated&&event.date>data.meta.updated)error(`${game.id}/${portalId}: historisches Ereignis ${event.date} liegt nach meta.updated.`);
    }
    for(const field of ['deployedCommit','submittedCommit','rejectedCommit']){
      if(placement[field]&&!/^[0-9a-f]{40}$/i.test(placement[field]))error(`${game.id}/${portalId}: ${field} ist keine vollständige Commit-SHA.`);
    }
  }

  const history=[...(game.metricsHistory||[])];
  for(const metric of history){
    if(!isValidDate(metric.date))error(`${game.id}: ungültiges Metrikdatum ${metric.date}.`);
    if(metric.date>data.meta.updated)error(`${game.id}: Metrik ${metric.date} liegt nach meta.updated.`);
    if(!portalIds.includes(metric.platform))error(`${game.id}: unbekanntes Metrikportal ${metric.platform}.`);
  }
  const sorted=[...history].sort((a,b)=>a.date.localeCompare(b.date));
  if(JSON.stringify(history)!==JSON.stringify(sorted))error(`${game.id}: metricsHistory ist nicht chronologisch sortiert.`);
  for(const portalId of portalIds){
    const latest=history.filter(metric=>metric.platform===portalId).at(-1);
    const placement=game.platforms[portalId];
    if(!latest||placement.latestPlays==null)continue;
    if(placement.playsAsOf!==latest.date)error(`${game.id}/${portalId}: playsAsOf stimmt nicht mit dem neuesten Snapshot überein.`);
    if(placement.latestPlays!==latest.plays)error(`${game.id}/${portalId}: latestPlays stimmt nicht mit dem neuesten Snapshot überein.`);
    if(placement.rating!=null&&latest.rating!=null&&placement.rating!==latest.rating)error(`${game.id}/${portalId}: rating stimmt nicht mit dem neuesten Snapshot überein.`);
  }
}

for(const message of warnings)console.warn(`WARNUNG: ${message}`);
for(const message of errors)console.error(`FEHLER: ${message}`);
if(errors.length)process.exit(1);
console.log(`Datenprüfung erfolgreich (${warnings.length} Warnung${warnings.length===1?'':'en'}).`);
