import argparse
from hashlib import md5
import requests

def get_signature(secret, params):
    sig = secret
    for (key, value) in dict(sorted(params.items())).items():
        sig += f'{key}{value}'

    return md5(sig.encode('utf-8')).hexdigest()

parser = argparse.ArgumentParser(prog='RTM Authenticator')
parser.add_argument('key', help='API Key')
parser.add_argument('secret', help='Shared Secret')

args = parser.parse_args()

print('Getting FROB...')
frob_request = 'https://api.rememberthemilk.com/services/rest/?'
frob_params = dict()
frob_params['method'] = 'rtm.auth.getFrob'
frob_params['api_key'] = args.key
frob_params['format'] = 'json'

for (key, value) in frob_params.items():
    frob_request += f'{key}={value}&'

frob_request += f'api_sig={get_signature(args.secret, frob_params)}'


frob_response = requests.get(frob_request).json()

frob = frob_response['rsp']['frob']


auth_request = 'https://www.rememberthemilk.com/services/auth/?'
auth_params = dict()
auth_params['frob'] = frob
auth_params['api_key'] = args.key
auth_params['perms'] = 'read'

for (key, value) in auth_params.items():
    auth_request += f'{key}={value}&'

auth_request += f'api_sig={get_signature(args.secret, auth_params)}'


print('Go to the URL below, follow the instructions, and come back.')
print(auth_request)

input('Press ENTER when done:')

token_request = 'https://api.rememberthemilk.com/services/rest/?'
token_params = dict()
token_params['method'] = 'rtm.auth.getToken'
token_params['api_key'] = args.key
token_params['frob'] = frob
frob_params['format'] = 'json'

for (key, value) in token_params.items():
    token_request += f'{key}={value}&'

token_request += f'api_sig={get_signature(args.secret, token_params)}'

token_response = requests.get(token_request)
print(token_response.text)
