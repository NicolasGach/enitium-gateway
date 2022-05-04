import getopt
import json
import logging
import os
from venv import create
import requests
import sys

TOKEN = '9WnOfoXlVQZe9885UqxJ81A7'
UNAME = 'nicolas@e-nitium.com'
ROOT = 'https://enitium.atlassian.net/'

logging.basicConfig(format = '%(asctime)s %(message)s', handlers=[logging.StreamHandler()])
log = logging.getLogger()
log.setLevel(logging.INFO)

def test_method():
    headers = {'Content-Type': 'application/json'}
    params = {'type': 'page', 'spaceKey': 'SEABLOCK', 'title': 'Minting', 'expand':'body.storage,version,ancestors'}
    get_confluence_content = requests.get(ROOT + 'wiki/rest/api/content', params=params, headers=headers, auth=requests.auth.HTTPBasicAuth(UNAME, TOKEN))
    log.debug('target content retrieved %s', get_confluence_content)
    data = json.loads(get_confluence_content.text)
    log.debug('data : %s', data)

def get_content(content_title):
    headers = {'Content-Type': 'application/json'}
    params = {'type': 'page', 'spaceKey': 'SEABLOCK', 'title': content_title, 'expand':'body.storage,version,ancestors'}
    return  requests.get(ROOT + 'wiki/rest/api/content', params=params, headers=headers, auth=requests.auth.HTTPBasicAuth(UNAME, TOKEN))

def create_content(content_title, content_ancestor, content_markdown):
    headers = {'Content-Type': 'application/json'}
    markdown_macro_prefix = '<ac:structured-macro ac:name="markdown" ac:schema-version="1" data-layout="default"><ac:parameter ac:name="attachmentSpaceKey" /><ac:parameter ac:name="sourceType">MacroBody</ac:parameter><ac:parameter ac:name="attachmentPageId" /><ac:parameter ac:name="syntax">Markdown</ac:parameter><ac:parameter ac:name="attachmentId" /><ac:parameter ac:name="url" /><ac:plain-text-body><![CDATA['
    markdown_macro_suffix = ']]></ac:plain-text-body></ac:structured-macro>'

    body = {
        'type': 'page',
        'title': content_title, 
        'space':{'key': 'SEABLOCK'}, 
        'ancestors': [{ 'id': content_ancestor }],
        'body': {
            'storage': {
                'value': markdown_macro_prefix + content_markdown + markdown_macro_suffix,
                'representation': 'storage'
            }
        }
    }

    create_result = requests.post(ROOT + 'wiki/rest/api/content', headers=headers, auth=requests.auth.HTTPBasicAuth(UNAME,TOKEN), data=json.dumps(body))
    
    if create_result.status_code == 200:
        log.info('Content created under ancestor {0}: {1}'.format(content_ancestor, content_title))
    else:
        log.info('Failed to create content {0}'.format(content_title))
        log.info('Creation failed with message: {0}'.format(create_result.text))

    log.debug('update result : %s', create_result)
    log.debug('update_result : %s', create_result.text)
    pass

def update_content(content_id, content_title, content_type, content_version, content_markdown):
    headers = {'Content-Type': 'application/json'}
    markdown_macro_prefix = '<ac:structured-macro ac:name="markdown" ac:schema-version="1" data-layout="default"><ac:parameter ac:name="attachmentSpaceKey" /><ac:parameter ac:name="sourceType">MacroBody</ac:parameter><ac:parameter ac:name="attachmentPageId" /><ac:parameter ac:name="syntax">Markdown</ac:parameter><ac:parameter ac:name="attachmentId" /><ac:parameter ac:name="url" /><ac:plain-text-body><![CDATA['
    markdown_macro_suffix = ']]></ac:plain-text-body></ac:structured-macro>'

    body = {
        'type': content_type, 
        'version': { 'number': int(content_version) + 1 },
        'title': content_title, 
        'space':{'key': 'SEABLOCK'}, 
        'body': {
            'storage': {
                'value': markdown_macro_prefix + content_markdown + markdown_macro_suffix,
                'representation': 'storage'
            }
        }
    }

    update_result = requests.put(ROOT + 'wiki/rest/api/content/' + content_id, headers=headers, auth=requests.auth.HTTPBasicAuth(UNAME,TOKEN), data=json.dumps(body))

    if update_result.status_code == 200:
        log.info('Content {0} updated, new version created'.format(content_title))
    
    log.debug('update result : %s', update_result)
    log.debug('update_result : %s', update_result.text)



def update_confluence_docs(argv):
        
    arg_folder_path = ''
    arg_ancestor_title = ''
    arg_excludes = []
    arg_help = '{0} -p <folder-path> -a <content-ancestor-title> -e <array-excluded-file-names>'.format(argv[0])

    try:
        opts, args = getopt.getopt(argv[1:], 'htp:a:e:', ["help", "test", "folder-path=", "ancestor=", "excludes="])
    except:
        print(arg_help)
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-t', '--test'):
            test_method()
            return
        if opt in ('-h', '--help'):
            print(arg_help)
            sys.exit(2)
        elif opt in ('-p', '--folder-path'):
            arg_folder_path = arg
        elif opt in ('-a', '--ancestor'):
            arg_ancestor_title = arg
        elif opt in ('-e', '--excludes'):
            arg_excludes = arg.split(',')

    os.chdir(arg_folder_path)

    file_dict = {}

    for file in os.listdir():
        if file.endswith('.md'):
            file_title = file.split('.')
            with open(f'{file}', 'r', encoding='utf-8') as md_file:
                file_content = md_file.read()
                file_dict.update({file_title[0]: file_content})
    
    for key in file_dict:

        if key in arg_excludes: continue

        content_title = key
        content_markdown = file_dict[key]

        get_confluence_content = get_content(content_title)
        get_ancestor_content = get_content(arg_ancestor_title)
        ancestor_data = json.loads(get_ancestor_content.text)

        if get_confluence_content.status_code == 200: 
            log.debug('target content retrieved %s', get_confluence_content)
            data = json.loads(get_confluence_content.text)
            log.debug('data : %s', data)
            if len(data['results']) == 0:
                log.info('Content {0} not found'.format(content_title))
                content_ancestor = ancestor_data['results'][0]['id']
                create_content(content_title, content_ancestor, content_markdown)
            else:
                log.info('Content {0} found'.format(content_title))
                content_id = data['results'][0]['id']
                content_body = data['results'][0]['body']['storage']['value']
                content_version = data['results'][0]['version']['number']
                content_title = data['results'][0]['title']
                content_type = data['results'][0]['type']
                ancestor_length = len(data['results'][0]['ancestors'])
                log.debug('id : %s', content_id)
                log.debug('body : %s', content_body)
                log.debug('version : %s', content_version)

                update_content(content_id, content_title, content_type, content_version, content_markdown)



if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    update_confluence_docs(sys.argv)

    #ac:local-id="014e8854-7d9a-4634-8660-8535d355366a" ac:macro-id="207b5a5e-3924-4659-b640-7df62a65dd75"