import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from threading import RLock
import engine

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'data'/'state.json'
PUBLIC=ROOT/'site'/'catalog.json'
lock=RLock()
app=FastAPI(title='AI Catalog Studio')
app.mount('/shop',StaticFiles(directory=ROOT/'site',html=True),name='shop')

def state():
    return json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {'products':[], 'categories':[], 'cards':{}, 'approved':[]}

def call(fn,*args):
    try: return fn(*args)
    except ValueError as e: raise HTTPException(422,str(e)) from e
    except RuntimeError as e: raise HTTPException(502,str(e)) from e

@app.get('/')
def admin(): return FileResponse(ROOT/'admin.html')
@app.get('/api/state')
def get_state():
    with lock: return state()
@app.post('/api/import')
def import_products(items:list = Body(...)):
    with lock:
        s={'products':call(engine.validate_products,items),'categories':[],'cards':{},'approved':[]};engine.save_json(STATE,s);return s
@app.post('/api/categories')
def categories():
    with lock:
        s=state()
        if not s['products']: raise HTTPException(422,'Спочатку імпортуй товари.')
        s['categories']=call(engine.generate_categories,s['products']);s['cards']={};s['approved']=[];engine.save_json(STATE,s);return s
@app.post('/api/generate/{sku}')
def generate(sku:str):
    with lock:
        s=state();p=next((p for p in s['products'] if p['sku']==sku),None)
        if p is None or not s['categories']: raise HTTPException(422,'Потрібен товар і каталог.')
        s['cards'][sku]=call(engine.generate_card,p,s['categories']);s['approved']=[x for x in s['approved'] if x!=sku];engine.save_json(STATE,s);return s
@app.put('/api/cards/{sku}')
def edit(sku:str,card:dict = Body(...)):
    with lock:
        s=state()
        if sku not in s['cards']:raise HTTPException(404,'Картку не знайдено.')
        s['cards'][sku]=call(engine.validate_card,card,s['categories']);s['approved']=[x for x in s['approved'] if x!=sku];engine.save_json(STATE,s);return s
@app.post('/api/approve/{sku}')
def approve(sku:str):
    with lock:
        s=state()
        if sku not in s['cards']:raise HTTPException(422,'Спочатку згенеруй картку.')
        if sku not in s['approved']:s['approved'].append(sku)
        engine.save_json(STATE,s);return s
@app.post('/api/publish')
def publish():
    with lock:
        s=state()
        if not s['approved']:raise HTTPException(422,'Потрібна хоча б одна перевірена картка.')
        data=call(engine.export_catalog,s['products'],s['categories'],{k:s['cards'][k] for k in s['approved']});engine.save_json(PUBLIC,data);return {'count':len(data['products'])}
