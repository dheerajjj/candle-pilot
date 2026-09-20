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

class CallbackTests(unittest.TestCase):
    def test_browser_callback_uses_state_and_hides_token(self):
        import socket
        import threading
        import urllib.parse
        import urllib.request
        store=Store()
        store.set_password(credentials.SERVICE,'api_key','public')
        store.set_password(credentials.SERVICE,'api_secret','private')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port=sock.getsockname()[1]
        threads=[]
        def browser(url):
            params=urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            state=urllib.parse.parse_qs(params['redirect_params'][0])['cp_state'][0]
            def deliver():
                q=urllib.parse.urlencode({'cp_state':state,'request_token':'one_time'})
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/callback?{q}',timeout=2) as response:
                    assert b'one_time' not in response.read()
            thread=threading.Thread(target=deliver)
            threads.append(thread);thread.start()
            return True
        with patch.dict(sys.modules,{'kiteconnect':types.SimpleNamespace(KiteConnect=FakeKite)}), \
             patch.object(credentials,'vault',return_value=store), \
             patch.object(credentials.webbrowser,'open',side_effect=browser):
            self.assertTrue(credentials.login_browser(timeout=2,port=port))
        for thread in threads: thread.join(timeout=2)
        self.assertEqual(store.get_password(credentials.SERVICE,'access_token'),'short_lived_token')
