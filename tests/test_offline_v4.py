from pathlib import Path
import functools,http.server,threading,time,json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args): pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(ROOT)))
port=server.server_port
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  context=b.new_context(viewport={'width':390,'height':844},service_workers='allow')
  page=context.new_page();err=[];page.on('pageerror',lambda e:err.append(str(e)))
  page.goto(f'http://127.0.0.1:{port}/index.html',wait_until='networkidle');page.wait_for_function("navigator.serviceWorker.controller!==null",timeout=15000)
  page.wait_for_function("caches.keys().then(k=>k.includes('second-era-rundenplan-v5'))",timeout=15000)
  page.locator('[data-tab="tracker"]').click();page.locator('#ep-amount').fill('4');page.locator('[data-action="xp-normal"]').click()
  expect=page.evaluate('window.__appDebug.getState().groupXP');assert expect==6
  context.set_offline(True)
  page.reload(wait_until='load');assert 'Rundenassistent' in page.locator('#app').inner_text()
  state=page.evaluate('window.__appDebug.getState()');assert state['groupXP']==6
  report={'offline_start':'PASS','service_worker_controlled':True,'cache':'second-era-rundenplan-v5','state_preserved':True,'errors':err}
  (ROOT/'tests'/'v4_offline_results.json').write_text(json.dumps(report,indent=2))
  print('OFFLINE PASS',json.dumps(report))
  b.close()
finally:server.shutdown()
