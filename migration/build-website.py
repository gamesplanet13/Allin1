#!/usr/bin/env python3
"""Reproduce the all-in-one website from pinned, backed-up public source commits."""
import argparse,concurrent.futures,hashlib,json,os,pathlib,re,shutil,subprocess,tempfile,zipfile
HERE=pathlib.Path(__file__).resolve().parent
TEXT={'.html','.htm','.js','.mjs','.cjs','.css','.json','.txt','.md','.webmanifest','.svg','.php','.ts','.tsx','.yml','.yaml','.sql','.sh'}
PRIVATE={'invoice-db-backup.json','orders-backup.json','customers.json','accounts.json','sessions.json'}
def source_tree(entry,root):
 path=root/entry['name']
 if path.exists():
  actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=path,text=True).strip()
  if actual!=entry['head']:raise RuntimeError('Source changed: '+entry['name'])
  return path
 path.mkdir(parents=True)
 for command in [['git','init','-q'],['git','remote','add','origin','https://github.com/gamesplanet13/'+entry['name']+'.git'],['git','fetch','--quiet','--depth=1','origin',entry['head']],['git','checkout','--quiet','--detach','FETCH_HEAD']]:
  subprocess.run(command,cwd=path,check=True,stdout=subprocess.DEVNULL,timeout=300)
 return path
def rewrite(s,base,names):
 for name in sorted(names,key=len,reverse=True):
  s=re.sub(r'https://raw\.githubusercontent\.com/gamesplanet13/'+re.escape(name)+r'/(?:main|master)/',base+name+'/',s,flags=re.I)
  s=s.replace('https://api.github.com/repos/gamesplanet13/'+name+'/contents/', 'https://api.github.com/repos/gamesplanet13/'+base.rstrip('/').split('/')[-1]+'/contents/'+name+'/')
 s=s.replace('https://gamesplanet13.github.io/',base).replace('http://gamesplanet13.github.io/',base)
 s=s.replace('//gamesplanet13.github.io/','//'+base.split('://',1)[-1])
 for q in ["'",'"']:
  s=s.replace('location.pathname.split('+q+'/'+q+')[1]','location.pathname.split('+q+'/'+q+')[2]')
  s=s.replace('path.split('+q+'/'+q+')[1]','path.split('+q+'/'+q+')[2]')
  s=s.replace('location.pathname.split('+q+'/'+q+').filter(Boolean)[0]','location.pathname.split('+q+'/'+q+').filter(Boolean)[1]')
 return s
def patch_products(path):
 if not path.exists():return
 s=path.read_text()
 helper='''
const GP_PRODUCT_QTY={};
function productQuantity(p){return `<div class="gp-product-quantity"><button type="button" data-product-step="-1" data-product-id="${p.id}" aria-label="Decrease quantity">−</button><output>${GP_PRODUCT_QTY[p.id]||1}</output><button type="button" data-product-step="1" data-product-id="${p.id}" aria-label="Increase quantity">+</button></div>`}
function bindProductQuantity(){document.querySelectorAll('[data-product-step]').forEach(b=>b.onclick=()=>{const id=b.dataset.productId;GP_PRODUCT_QTY[id]=Math.max(1,(GP_PRODUCT_QTY[id]||1)+Number(b.dataset.productStep));b.closest('.gp-product-quantity').querySelector('output').textContent=GP_PRODUCT_QTY[id]})}
'''
 s=helper+s
 s=s.replace('c[id]=(c[id]||0)+1','c[id]=GP_PRODUCT_QTY[id]||1')
 if path.name=='store.js':
  s=s.replace('<div class="actions"><button class="btn add"','${productQuantity(p)}<div class="actions"><button class="btn add"')
  needle='document.querySelectorAll("[data-buy]").forEach(b=>b.onclick=()=>addToCart(b.dataset.buy,true))'
  if needle not in s:raise RuntimeError('Product store action binding changed')
  s=s.replace(needle,needle+';bindProductQuantity()')
 else:
  s=s.replace('<button class="detail-add"','${productQuantity(p)}<button class="detail-add"')
  # Details page classes vary; insert immediately before the actual Add button.
  if '${productQuantity(p)}' not in s:s=s.replace('<button class="detail-btn add"','${productQuantity(p)}<button class="detail-btn add"')
  if '${productQuantity(p)}' not in s:
   s=re.sub(r'(<button[^>]*id="detailAdd")',r'${productQuantity(p)}\1',s,count=1)
  if '${productQuantity(p)}' not in s:raise RuntimeError('Product details Add button changed')
  s=s.replace('document.getElementById("detailBuy").onclick=()=>addToCart(p.id,true);','document.getElementById("detailBuy").onclick=()=>addToCart(p.id,true);bindProductQuantity();')
 path.write_text(s)
def build(args):
 plan=json.loads((HERE/'plan.json').read_text());names=[e['name']for e in plan];base='https://gamesplanet13.github.io/'+args.repository.strip('/')+'/'
 out=pathlib.Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
 snapshots=pathlib.Path(args.snapshots).resolve() if args.snapshots else pathlib.Path(tempfile.mkdtemp(prefix='gp-snapshots-'))
 with concurrent.futures.ThreadPoolExecutor(max_workers=5)as pool:trees=list(pool.map(lambda e:source_tree(e,snapshots),plan))
 count=0;size=0
 for entry,tree in zip(plan,trees):
  dest=out/entry['name'];dest.mkdir(exist_ok=True)
  for p in tree.rglob('*'):
   rel=p.relative_to(tree)
   if not p.is_file() or any(x in {'.git','.github','node_modules','.wrangler','.next','outputs'} for x in rel.parts) or p.name.lower() in PRIVATE or p.name.startswith(('.env','.dev.vars')) or p.suffix in {'.sqlite','.sqlite3','.db'}:continue
   target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True)
   if p.suffix.lower() in TEXT and p.stat().st_size<25*1024*1024:
    try:s=rewrite(p.read_text(),base,names)
    except UnicodeDecodeError:shutil.copyfile(p,target)
    else:
     if p.suffix.lower()=='.html':
      script='<script src="'+base+'arcade-accessories-/buy-cart.js?v=20261025"></script>'
      s=s.replace('</body>',script+'</body>')
      if entry['name']=='Products' and 'shared-store.js' not in s:s=s.replace('</body>','<script src="'+base+'arcade-accessories-/shared-store.js?v=20261025"></script></body>')
     target.write_text(s)
   else:shutil.copyfile(p,target)
   count+=1;size+=target.stat().st_size
 main=out/'arcade-accessories-'
 for name in ['buy-cart.js','buy-cart.test.cjs']:shutil.copyfile(HERE/'patches'/name,main/name)
 shared=main/'shared-store.js';s=shared.read_text();s=s.replace("function capture(){const repo=", "function capture(){if(window.GP_EXPLICIT_PRODUCT_ACTIONS)return;const repo=")
 s=s.replace("window.goDetails=()=>checkout('catalog',window.buildOrderSummary().items)","window.goDetails=()=>location.href=base+'cart.html'")
 shared.write_text(s)
 patch_products(out/'Products'/'store.js');patch_products(out/'Products'/'product.js')
 # Current backend source is retained separately; runtime secrets / customer records are never copied.
 services=HERE/'patches'/'services'
 if services.exists():shutil.copytree(services,out/'services',dirs_exist_ok=True)
 archive=HERE/'services-source.zip'
 if archive.exists():
  with zipfile.ZipFile(archive) as z:
   for item in z.infolist():
    name=pathlib.PurePosixPath(item.filename)
    if name.is_absolute() or '..' in name.parts:raise RuntimeError('Unsafe backend source path')
    target=out/'services'/item.filename
    if item.is_dir():target.mkdir(parents=True,exist_ok=True)
    else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(item))
 (out/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GAMES PLANET</title><meta http-equiv="refresh" content="0;url=arcade-accessories-/index.html"><script>location.replace("arcade-accessories-/index.html"+location.search+location.hash)</script><a href="arcade-accessories-/index.html">Open GAMES PLANET website</a></html>')
 (out/'.nojekyll').touch()
 report={'repository':args.repository,'base':base,'files':count,'bytes':size,'sources':[{k:e[k]for k in ['name','head','baseline']}for e in plan]}
 (out/'migration-report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'files':count,'megabytes':round(size/1024**2,1),'output':str(out),'base':base}),flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--repository',default='games-planet-website');parser.add_argument('--output',default='site');parser.add_argument('--snapshots');build(parser.parse_args())
