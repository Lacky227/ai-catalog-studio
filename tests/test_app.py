import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
import app, engine

P={'sku':'A','name':'Навушники','price':123,'attributes':{'Колір':'Чорний'}}
C=[{'l1':'Електроніка','l2':['Навушники']}]
CARD={'l1':'Електроніка','l2':'Навушники','title':'Навушники','short_description':'Короткий опис','description':'Опис','benefits':['Чорний колір'],'seo_title':'Навушники','seo_description':'Опис навушників','faq':[],'example_reviews':[]}

class TestApp(unittest.TestCase):
    def test_full_flow(self):
        with tempfile.TemporaryDirectory() as d, patch.object(app,'STATE',Path(d)/'state.json'), patch.object(app,'PUBLIC',Path(d)/'catalog.json'), patch.object(engine,'generate_categories',return_value=C), patch.object(engine,'generate_card',return_value=CARD):
            client=TestClient(app.app)
            self.assertEqual(client.get('/').status_code,200)
            self.assertEqual(client.post('/api/import',json=[P]).status_code,200)
            self.assertEqual(client.post('/api/categories').json()['categories'],C)
            self.assertEqual(client.post('/api/generate/A').json()['cards']['A'],CARD)
            self.assertEqual(client.post('/api/publish').status_code,422)
            self.assertEqual(client.post('/api/approve/A').status_code,200)
            self.assertEqual(client.post('/api/publish').json(),{'count':1})
            exported=json.loads(app.PUBLIC.read_text())['products'][0]
            self.assertEqual(exported['price'],123)
            self.assertEqual(exported['attributes'],P['attributes'])
            self.assertEqual(client.put('/api/cards/A',json=CARD).json()['approved'],[])
            self.assertEqual(client.get('/shop/').status_code,200)
    def test_validation(self):
        with self.assertRaises(ValueError):engine.validate_products([P,P])
        with self.assertRaises(ValueError):engine.validate_card(dict(CARD,l2='Unknown'),C)
        with self.assertRaises(ValueError):engine.validate_products([dict(P,price=-1)])
    def test_site_snapshot(self):
        root=Path(__file__).resolve().parents[1]
        data=json.loads((root/'site/catalog.json').read_text(encoding='utf-8'))
        categories=engine.validate_categories(data) if data['categories'] else []
        if data['products']:
            engine.validate_products(data['products'])
            for p in data['products']:engine.validate_card(p['content'],categories)
        self.assertTrue((root/'site/index.html').exists())

if __name__=='__main__':unittest.main()
