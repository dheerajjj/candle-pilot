"""Private Kite Connect credentials in Windows Credential Manager.

Run `python credentials.py setup` once, then `python credentials.py login` each trading day.
No account password, TOTP seed or token is written to the project directory.
"""
import argparse
import getpass
import os
import urllib.parse
import webbrowser

SERVICE = 'CandlePilot.Kite'
FIELDS = ('api_key', 'api_secret', 'access_token')


def vault():
    if os.name != 'nt':
        raise RuntimeError('Credential Manager storage requires native Windows Python (not WSL).')
    try:
        import keyring
    except ImportError as exc:
        raise RuntimeError('Install the Windows keyring package: python -m pip install keyring') from exc
    backend = keyring.get_keyring()
    if not type(backend).__module__.startswith('keyring.backends.Windows'):
        raise RuntimeError('Windows Credential Manager backend is unavailable; no credentials stored.')
    return keyring


def get_value(field):
    if field not in FIELDS:
        raise ValueError('Invalid credential field')
    # Session-scoped environment variables can override for CI or temporary use.
    return os.environ.get('KITE_' + field.upper()) or vault().get_password(SERVICE, field)


def setup():
    store = vault()
    key = getpass.getpass('Kite Connect API key (hidden): ').strip()
    secret = getpass.getpass('Kite Connect API secret (hidden): ').strip()
    if not key or not secret or any(x.isspace() for x in key+secret):
        raise ValueError('API key and secret must be nonempty and contain no spaces')
    store.set_password(SERVICE, 'api_key', key)
    store.set_password(SERVICE, 'api_secret', secret)
    print('API key and secret stored in Windows Credential Manager. Kite login password/TOTP not stored.')


def exchange_request_token(request_token, api_key, api_secret):
    from kiteconnect import KiteConnect
    kite = KiteConnect(api_key=api_key)
    data = kite.generate_session(request_token, api_secret=api_secret)
    token = data.get('access_token')
    if not token:
        raise RuntimeError('Kite did not provide an access token')
    return token



def login():
    store = vault()
    key = store.get_password(SERVICE, 'api_key')
    secret = store.get_password(SERVICE, 'api_secret')
    if not key or not secret:
        raise RuntimeError('Run python credentials.py setup first')
    from kiteconnect import KiteConnect
    url = KiteConnect(api_key=key).login_url()
    print('Opening the official Kite login page in your browser.')
    webbrowser.open(url)
    print('After official Kite login, copy the FULL redirect URL from your browser address bar.')
    redirect = getpass.getpass('Paste redirect URL (hidden): ').strip()
    parsed = urllib.parse.urlparse(redirect)
    token = urllib.parse.parse_qs(parsed.query).get('request_token', [None])[0]
    if not token:
        raise ValueError('No request_token found in redirect URL; check your app redirect URL')
    access_token = exchange_request_token(token, key, secret)
    store.set_password(SERVICE, 'access_token', access_token)
    print('Kite access token stored in Windows Credential Manager; expires next day at 6 a.m.')


def status():
    store = vault()
    for field in FIELDS:
        print(f'{field}: {"stored" if store.get_password(SERVICE,field) else "missing"}')
    print('Stored does not mean the session token is still valid.')


def delete():
    store = vault()
    for field in FIELDS:
        if store.get_password(SERVICE, field):
            store.delete_password(SERVICE, field)
    print('Candle Pilot credentials removed from Windows Credential Manager.')


def main():
    parser=argparse.ArgumentParser(description='Candle Pilot Windows credential setup')
    parser.add_argument('command', choices=('setup','login','status','delete'))
    cmd=parser.parse_args().command
    try:
        {'setup':setup,'login':login,'status':status,'delete':delete}[cmd]()
    except (RuntimeError, ValueError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__=='__main__':
    main()

# Desktop login: registered callback must be http://127.0.0.1:8787/callback .
REDIRECT_URL = 'http://127.0.0.1:8787/callback'


def login_browser(timeout=180, port=8787):
    """Open official Kite login and collect its one-use token on localhost."""
    import http.server
    import secrets
    store = vault()
    key = store.get_password(SERVICE, 'api_key')
    secret = store.get_password(SERVICE, 'api_secret')
    if not key or not secret:
        raise RuntimeError('API key and secret are missing from Windows Credential Manager')
    from kiteconnect import KiteConnect
    nonce = secrets.token_urlsafe(20)
    result = {}

    class Callback(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(query.query)
            if query.path != '/callback' or params.get('cp_state') != [nonce]:
                self.send_error(403, 'Invalid callback')
                return
            result['token'] = params.get('request_token', [None])[0]
            result['error'] = params.get('error', [None])[0]
            body = b'<h2>Candle Pilot received your login. You can close this tab.</h2>'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass  # Never log request tokens in callback URLs.

    try:
        server = http.server.HTTPServer(('127.0.0.1', port), Callback)
    except OSError as exc:
        raise RuntimeError('Local login port 8787 is busy. Close other Candle Pilot windows.') from exc
    try:
        server.timeout = timeout
        url = KiteConnect(api_key=key).login_url()
        url += '&redirect_params=' + urllib.parse.quote('cp_state=' + nonce, safe='')
        if not webbrowser.open(url):
            raise RuntimeError('Could not open browser for Kite login')
        server.handle_request()
    finally:
        server.server_close()
    if not result.get('token'):
        raise RuntimeError('Kite login timed out or callback failed. Check the registered redirect URL: ' + REDIRECT_URL)
    store.set_password(SERVICE, 'access_token', exchange_request_token(result['token'], key, secret))
    return True
