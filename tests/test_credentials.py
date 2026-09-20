import pathlib
import sys
import types
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import credentials


class Store:
    def __init__(self): self.data={}
    def set_password(self,service,field,value): self.data[(service,field)]=value
    def get_password(self,service,field): return self.data.get((service,field))
    def delete_password(self,service,field): self.data.pop((service,field),None)


class FakeKite:
    def __init__(self,api_key): self.api_key=api_key
    def login_url(self): return f'https://kite.zerodha.com/connect/login?api_key={self.api_key}'
    def generate_session(self,request_token,api_secret):
        assert (self.api_key,request_token,api_secret)==('public','one_time','private')
        return {'access_token':'short_lived_token'}


class CredentialsTests(unittest.TestCase):
    def test_setup_stores_only_api_credentials(self):
        store=Store()
        with patch.object(credentials,'vault',return_value=store), patch.object(credentials.getpass,'getpass',side_effect=['aKey','aSecret']):
            credentials.setup()
        self.assertEqual(set(field for _,field in store.data),{'api_key','api_secret'})

    def test_official_sdk_login_stores_token(self):
        store=Store()
        store.set_password(credentials.SERVICE,'api_key','public')
        store.set_password(credentials.SERVICE,'api_secret','private')
        with patch.dict(sys.modules,{'kiteconnect':types.SimpleNamespace(KiteConnect=FakeKite)}), \
             patch.object(credentials,'vault',return_value=store), \
             patch.object(credentials.webbrowser,'open') as open_browser, \
             patch.object(credentials.getpass,'getpass',return_value='http://localhost/callback?request_token=one_time'):
            credentials.login()
        self.assertEqual(store.get_password(credentials.SERVICE,'access_token'),'short_lived_token')
        self.assertEqual(open_browser.call_args.args[0],FakeKite('public').login_url())


if __name__=='__main__': unittest.main()
