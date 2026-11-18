"""UI tests of Second Era V4. Browser: Chromium; not native Safari."""
from pathlib import Path
import traceback,json,re
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="styles.css" />','')
JS=(ROOT/'app.js').read_text();CSS=(ROOT/'styles.css').read_text()
OK=[];BAD=[];errors=[]

def make(b,seed=None,viewport=390):
 p=b.new_page(viewport={'width':viewport,'height':844},device_scale_factor=2)
 p.on('dialog',lambda d:d.accept())
 p.on('pageerror',lambda e: errors.append(str(e)))
 p.set_content(HTML)
 p.evaluate("""store => {window._store=store;Object.defineProperty(window,'localStorage',{value:{getItem(k){return window._store[k]??null},setItem(k,v){window._store[k]=v},removeItem(k){delete window._store[k]},clear(){window._store={}}},configurable:true})}""", {'second-era-rundenplan-v1':json.dumps(seed)} if seed else {})
 p.add_style_tag(content=CSS);p.add_script_tag(content=JS)
 return p

def st(p):return p.evaluate('window.__appDebug.getState()')
def act(p,a):p.locator(f'[data-action="{a}"]').first.click()
def tab(p,t):p.locator(f'[data-tab="{t}"]').click()
def setv(p,key,val):p.locator(f'[data-setting="{key}"]').select_option(val) if isinstance(val,str) and p.locator(f'[data-setting="{key}"]').evaluate('e=>e.tagName')=='SELECT' else p.locator(f'[data-setting="{key}"]').fill(str(val));p.locator(f'[data-setting="{key}"]').dispatch_event('change')
def seed(**kwargs):
 d=dict(version=5,session=1,day=2,phase='morgen',groupXP=2,freeXP=0);d.update(kwargs);return d
def province(p):
 act(p,'next');assert st(p)['phase']=='provinz'
def encounter(p,v):
 p.locator(f'[data-encounter-choice="{v}"]').click();assert st(p)['encounter']==v

def decision(p,yn):
 act(p,'province-continue');assert st(p)['provinceScreen']=='combat';p.locator(f'[data-fight-choice="{yn}"]').click();act(p,'province-continue');assert st(p)['phase']=='begegnung'

def no_fight_day(p):
 province(p)
 if not st(p)['encounterSelectionMade']:encounter(p,'friedlich')
 decision(p,'nein');act(p,'next');assert st(p)['phase']=='belohnung';act(p,'next');assert st(p)['phase']=='abend';act(p,'next')

def test(name,fn,b):
 p=None
 try:
  p=fn(b)
  if errors:raise AssertionError('JS errors:'+str(errors))
  OK.append(name);print('PASS',name,flush=True)
 except Exception as e:
  BAD.append({'name':name,'error':repr(e),'traceback':traceback.format_exc()})
  print('FAIL',name,repr(e),flush=True)
 finally:
  if p:p.close()

with sync_playwright() as pw:
 b=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 def t1(b):
  p=make(b);assert st(p)['groupXP']==2;assert st(p)['freeXP']==0;assert 'Tag 1: Tageszähler steht' in p.locator('#phase-panel').inner_text();return p
 test('Startmodus: regulär 2 Gruppen-EP, keine gesparten EP',t1,b)
 def t2(b):
  p=make(b);tab(p,'regeln');setv(p,'startMode','intro');assert st(p)['groupXP']==1 and st(p)['startMode']=='intro';return p
 test('Intro: Gruppen-EP auf 1, ohne freie EP',t2,b)
 def t3(b):
  p=make(b);province(p);assert p.locator('[data-encounter-choice]').count()==1;assert st(p)['encounter']=='stadt';return p
 test('Tag 1: Stadt und kein Provinz-Bewegen',t3,b)
 def t4(b):
  p=make(b);no_fight_day(p);assert st(p)['day']==2 and st(p)['phase']=='morgen' and st(p)['dayChecks']=={};assert 'Tageszähler auf 2 einstellen' in p.locator('#phase-panel').inner_text();no_fight_day(p);assert st(p)['day']==3;return p
 test('Tage 1→2→3 mit offenen Häkchen und Tagesreset',t4,b)
 def t5(b):
  p=make(b,seed());province(p);opts=p.locator('[data-encounter-choice]');assert opts.count()==7
  assert [x for x in ['gildenquest','nebenquest','stadt','friedlich','konfliktreich','riskant','leer']]==[x.get_attribute('data-encounter-choice') for x in opts.all()];return p
 test('Hierarchie: Gildenquest vor Nebenquest vor Ort',t5,b)
 def t6(b):
  p=make(b,seed());province(p);encounter(p,'riskant');act(p,'province-continue');assert p.locator('[data-setting="riskOutcome"] option').count()==4;assert p.locator('[data-action="province-continue"]').is_disabled();setv(p,'riskOutcome','haendler');p.locator('[data-fight-choice="nein"]').click();act(p,'province-continue');assert 'Stadtaktionen' in p.locator('#phase-panel').inner_text();return p
 test('Riskant: Fahrende Händler als Stadtbegegnung',t6,b)
 def t7(b):
  p=make(b,seed());province(p);encounter(p,'riskant');act(p,'province-continue');setv(p,'riskOutcome','konfliktreich');p.locator('[data-fight-choice="nein"]').click();act(p,'province-continue');assert 'Konfliktreiche Begegnungskarte' in p.locator('#phase-panel').inner_text();assert st(p)['fightDecision']=='nein';return p
 test('Konfliktreicher Ort bedeutet nicht zwingend Schlacht',t7,b)
 def t8(b):
  p=make(b,seed());province(p);encounter(p,'friedlich');decision(p,'ja');assert p.locator('[data-tab="kampf"].active').count()==1
  setv(p,'dungeon','gewoelbe');assert st(p)['dungeon']=='gewoelbe';assert 'Gewölbe: zunächst nur' in p.locator('main').inner_text();return p
 test('Schlacht → Gewölbe als eigene Auswahl',t8,b)
 def t9(b):
  p=make(b,seed());province(p);encounter(p,'gildenquest');decision(p,'ja');setv(p,'battleGoal','aufklaerung');assert st(p)['battleGoal']=='aufklaerung';return p
 test('Schlachtziel Aufklärung auswählbar',t9,b)
 def t10(b):
  p=make(b,seed(phase='begegnung',encounter='konfliktreich',fightDecision='ja',dungeon='scharmuetzel'))
  tab(p,'kampf');act(p,'battle-to-round');assert st(p)['battleMode']=='round'
  for i in range(7):act(p,'battle-next-round')
  assert st(p)['battleRound']==6
  txt=p.locator('main').inner_text();assert 'Übermüdungsrunde' in txt and 'Daedrischen Schaden' in txt;return p
 test('Rundenzähler bleibt ab Übermüdungsrunde auf 6',t10,b)
 def t11(b):
  p=make(b,seed(phase='begegnung',fightDecision='ja',battleMode='round',battleRound=5));tab(p,'kampf');act(p,'battle-next-round');assert st(p)['battleRound']==6;act(p,'battle-next-round');assert st(p)['battleRound']==6;return p
 test('Übermüdungsrunde in jeder weiteren Runde wiederholt',t11,b)
 def t12(b):
  p=make(b,seed(phase='begegnung',fightDecision='ja',battleMode='round'));tab(p,'kampf');p.locator('[data-setting-bool="battleSkill"]').check();assert '1. Ermüdung' in p.locator('main').inner_text();
  for i in range(1,7):p.locator(f'[data-check="skill{i}"]').check()
  act(p,'skill-repeat');assert st(p)['skillUses']==1;assert not st(p)['battleChecks'].get('skill1');return p
 test('Wiederholbare Aktivieren-Checkliste',t12,b)
 def t13(b):
  p=make(b,seed(phase='begegnung',fightDecision='ja',battleMode='round',dungeon='gewoelbe'));tab(p,'kampf');p.locator('[data-setting-bool="exploring"]').check();txt=p.locator('main').inner_text();assert 'passende Matte' in txt and 'Himmelsscherben' in txt;return p
 test('Gewölbe-Erkunden: Matte, Platz, Kisten, Gegner, Scherben',t13,b)
 def t14(b):
  p=make(b,seed(phase='begegnung',fightDecision='ja',battleMode='round'));tab(p,'kampf');act(p,'battle-to-cleanup');assert 'Schlachtausgang' in p.locator('main').inner_text();assert 'Prüfreihenfolge' in p.locator('main').inner_text();return p
 test('Schlachtende mit Priorität Niederlage/Ziel/Rückzug',t14,b)
 def t15(b):
  p=make(b,seed(phase='begegnung',fightDecision='ja'));tab(p,'kampf');setv(p,'chestKind','legendaer');setv(p,'chestMaxAttempts','2');act(p,'chest-repeat');assert st(p)['chestAttempt']==2;assert p.locator('[data-action="chest-repeat"]').is_disabled();assert 'Schlüsselziffer' in p.locator('main').inner_text();return p
 test('Schlossknacken: Schlüsselziffer und begrenzte Versuche',t15,b)
 def t16(b):
  p=make(b,seed(phase='begegnung',encounter='stadt',fightDecision='nein'));tab(p,'ablauf');setv(p,'cityAction0','marktplatz');setv(p,'cityAction1','marktplatz');assert st(p)['cityActions']==['marktplatz',''];assert 'freie Stadtaktionen' in p.locator('#phase-panel').inner_text();return p
 test('Stadt: Marktplatz 1× und freie Stadtaktionen',t16,b)
 def t17(b):
  p=make(b,seed(phase='begegnung',encounter='friedlich',fightDecision='nein'));tab(p,'ablauf');p.locator('[data-setting-bool="social"]').check();assert 'Überzeugungsprobe' in p.locator('#phase-panel').inner_text() and 'Redekunst' in p.locator('#phase-panel').inner_text();return p
 test('Überzeugungsprobe: korrekter Würfel-/Fokus-Ablauf',t17,b)
 def t18(b):
  p=make(b);tab(p,'tracker');p.locator('#ep-amount').fill('5');act(p,'xp-normal');assert st(p)['groupXP']==7 and st(p)['freeXP']==5
  p.locator('#ep-amount').fill('2');act(p,'xp-bonus');assert st(p)['bonusXP']==2 and st(p)['freeXP']==7 and st(p)['groupXP']==7
  p.locator('#ep-amount').fill('3');act(p,'xp-spend');assert st(p)['freeXP']==4 and st(p)['groupXP']==7;return p
 test('EP: normale, Bonus und Ausgaben getrennt',t18,b)
 def t19(b):
  p=make(b,seed(phase='belohnung',encounter='gildenquest',fightDecision='ja',dungeon='gewoelbe',battleGoal='aufklaerung',groupXP=2,freeXP=0));
  setv(p,'shardCount','4');setv(p,'shardTarget','3');act(p,'shard-xp');assert st(p)['groupXP']==5 and st(p)['freeXP']==3 and st(p)['awardedShardXP']==3
  assert p.locator('[data-action="shard-xp"]').is_disabled();return p
 test('Aufklärung: max. 3 Himmelsscherben-EP ohne Doppelbuchung',t19,b)
 def t20(b):
  p=make(b,seed(phase='belohnung',encounter='gildenquest',fightDecision='ja',dungeon='gewoelbe',battleGoal='aufklaerung',shardAlive=False));
  setv(p,'shardCount','3');assert p.locator('[data-action="shard-xp"]').is_disabled();return p
 test('Aufklärung: keine EP bei vollständiger Niederlage',t20,b)
 def t21(b):
  p=make(b,seed(phase='abend'));tab(p,'tracker');act(p,'guild-assist');assert st(p)['guildAssistUsed'];assert p.locator('[data-action="guild-assist"]').is_disabled();return p
 test('Gildenunterstützung: einmal während Rasten',t21,b)
 def t22(b):
  p=make(b,seed(phase='morgen'));tab(p,'tracker');act(p,'guild-assist');assert st(p)['guildAssistUsed']==False;return p
 test('Gildenunterstützung: blockiert außerhalb erlaubter Phase',t22,b)
 def t23(b):
  p=make(b,seed(phase='begegnung',fightDecision='ja',battleMode='round'));tab(p,'tracker');act(p,'guild-assist');assert st(p)['guildAssistUsed']==True;return p
 test('Gildenunterstützung: während Schlachtrunde zulässig',t23,b)
 def t24(b):
  p=make(b,seed(phase='belohnung'));p.locator('[data-setting-bool="questFailed"]').check();act(p,'next');assert st(p)['phase']=='verloren';return p
 test('Gescheiterter Gildenquest-Abschnitt → Kampagne verloren',t24,b)
 def t25(b):
  p=make(b,seed(day=12,phase='abend'));act(p,'next');assert st(p)['phase']=='verloren' and st(p)['day']==12;return p
 test('Tag 12 ohne Erfolg → Kampagne verloren',t25,b)
 def t26(b):
  p=make(b,seed(phase='belohnung'));p.locator('[data-setting-bool="questCompleted"]').check();act(p,'next');assert st(p)['phase']=='sitzungsende';act(p,'next');assert st(p)['session']==2 and st(p)['day']==1;return p
 test('Erfolgreiche Gildenquest → ohne Abendphase in Partie 2',t26,b)
 def t27(b):
  p=make(b,seed(session=3,day=1,phase='morgen'));province(p);assert 'keine normale Provinzbewegung' in p.locator('#province-wizard').inner_text() or 'Gruppe nicht' in p.locator('#province-wizard').inner_text();return p
 test('Finale: keine normale Provinzbewegung',t27,b)
 def t28(b):
  p=make(b,seed(session=3,day=12,phase='abend'));act(p,'next');assert st(p)['day']==13 and st(p)['phase']=='morgen';return p
 test('Finale ohne gewöhnliches 12-Tage-Limit',t28,b)
 def t29(b):
  p=make(b,seed(phase='belohnung',freeXP=5,focusMax=7,focus=2));act(p,'next');assert st(p)['focus']==4 and st(p)['freeXP']==3;return p
 test('EP-Überhang 1:1 in Fokus, höchstens 3 gesparte EP',t29,b)
 def t30(b):
  p=make(b,seed(phase='belohnung',freeXP=5,focusMax=3,focus=2));act(p,'next');assert st(p)['focus']==3 and st(p)['freeXP']==3;return p
 test('EP-Überhang mit Fokusmaximum begrenzt',t30,b)
 def t31(b):
  p=make(b,seed(notes='Teststand',groupXP=16,freeXP=2,phase='abend'));act(p,'next');assert st(p)['groupXP']==16 and st(p)['notes']=='Teststand' and st(p)['freeXP']==2;return p
 test('Tagesreset erhält Notizen und EP',t31,b)
 def t32(b):
  legacy=dict(version=4,session=1,day=5,phase='begegnung',encounter='scharmuetzel',fightDecision='ja',groupXP=16,freeXP=2,notes='Alter Speicher',dungeon='explore',cityActions=['haendler','ausbilder'])
  p=make(b,legacy);r=st(p);assert r['version']==5 and r['encounter']=='konfliktreich' and r['dungeon']=='gewoelbe' and r['groupXP']==16 and r['notes']=='Alter Speicher';assert r['cityActions']==['laden','lehrer'];return p
 test('V3→V4-Spielstandmigration inkl. Begriffe und Werte',t32,b)
 def t33(b):
  p=make(b,seed(phase='abend',day=4));tab(p,'tracker');p.locator('#ep-amount').fill('2');act(p,'xp-normal');r1=st(p);stored=p.evaluate('window._store');p.close();p=make(b,json.loads(stored['second-era-rundenplan-v1']));r2=st(p);assert r1['groupXP']==r2['groupXP']==4 and r2['day']==4;return p
 test('Persistenz über simulierten App-Neustart',t33,b)
 def t34(b):
  p=make(b,seed(phase='abend',day=4));
  # check all phase checkboxes; automatic reset once
  for _ in range(8):
   remaining=p.locator('input[data-scope="day"]:not(:checked):not(:disabled)')
   if remaining.count()==0:break
   remaining.first.evaluate("e=>{e.checked=true;e.dispatchEvent(new Event('change',{bubbles:true}))}")
  p.wait_for_function('window.__appDebug.getState().day===5',timeout=4500)
  p.wait_for_timeout(1200);assert st(p)['day']==5 and st(p)['dayChecks']=={};return p
 test('Automatischer Abendabschluss nur einmal',t34,b)
 def t35(b):
  p=make(b);p.screenshot(path=str(ROOT/'V4_Vorschau_iPhone.png'),full_page=True)
  assert p.locator('body').evaluate('(e)=>e.scrollWidth<=window.innerWidth+2');return p
 test('iPhone-Bildschirm 390px ohne horizontales Überlaufen',t35,b)
 b.close()

report={'passed':len(OK),'failed':len(BAD),'passed_tests':OK,'failed_tests':BAD,'page_errors':errors}
(ROOT/'tests'/'v4_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('REPORT',len(OK),'passed',len(BAD),'failed')
if BAD:exit(1)
