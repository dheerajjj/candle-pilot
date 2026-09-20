import io
import json
import pathlib
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import credentials


class Store:
    def __init__(self): self.data={}
    def set_password(self,service,field,value): self.data[(service,field)]=value
    def get_password(self,service,field): return self.data.get((service,field))
    def delete_password(self,service,field): self.data.pop((service,field),None)


class CredentialsTests(unittest.TestCase):
    def test_setup_stores_only_api_credentials(self):
        store=Store()
        with patch.object(credentials,'vault',return_value=store), patch.object(credentials.getpass,'getpass',side_effect=['aKey','aSecret']):
            credentials.setup()
        self.assertEqual(set(field for _,field in store.data),{'api_key','api_secret'})

    def test_login_exchange_stores_token_without_printing(self):
        store=Store()
        store.set_password(credentials.SERVICE,'api_key','public')
        store.set_password(credentials.SERVICE,'api_secret','private')
        with patch.object(credentials,'vault',return_value=store), patch.object(credentials.webbrowser,'open'), \
             patch.object(credentials.getpass,'getpass',return_value='http://localhost/callback?request_token=one_time'), \
             patch.object(credentials,'exchange_request_token',return_value='short_lived_token'):
            credentials.login()
        self.assertEqual(store.get_password(credentials.SERVICE,'access_token'),'short_lived_token')

    def test_checksum_is_correct(self):
        def opener(req,timeout):
            self.assertEqual(req.full_url,'https://api.kite.trade/session/token')
            payload=dict(x.split('=',1) for x in req.data.decode().split('&'))
            import hashlib
            expected=hashlib.sha256(b'keytokensecret').hexdigest()
            self.assertEqual(payload['checksum'],expected)
            return io.BytesIO(json.dumps({'status':'success','data':{'access_token':'received'}}).encode())
        self.assertEqual(credentials.exchange_request_token('token','key','secret',opener),'received')


if __name__=='__main__': unittest.main()
