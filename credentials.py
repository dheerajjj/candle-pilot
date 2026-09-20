"""Private Kite Connect credentials in Windows Credential Manager.

Run `python credentials.py setup` once, then `python credentials.py login` each trading day.
No account password, TOTP seed or token is written to the project directory.
"""
import argparse
import getpass
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
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


def exchange_request_token(request_token, api_key, api_secret, opener=urllib.request.urlopen):
    checksum = hashlib.sha256((api_key + request_token + api_secret).encode('utf-8')).hexdigest()
    data = urllib.parse.urlencode(dict(api_key=api_key, request_token=request_token,
                                        checksum=checksum)).encode('ascii')
    req = urllib.request.Request('https://api.kite.trade/session/token', data=data,
                                 headers={'X-Kite-Version': '3'}, method='POST')
    with opener(req, timeout=15) as response:
        payload = json.load(response)
    token = payload.get('data', {}).get('access_token')
    if payload.get('status') != 'success' or not token:
        raise RuntimeError('Kite did not provide an access token')
    return token


def login():
    store = vault()
    key = store.get_password(SERVICE, 'api_key')
    secret = store.get_password(SERVICE, 'api_secret')
    if not key or not secret:
        raise RuntimeError('Run python credentials.py setup first')
    url = 'https://kite.zerodha.com/connect/login?v=3&' + urllib.parse.urlencode({'api_key':key})
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
