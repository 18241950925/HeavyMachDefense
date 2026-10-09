"""Export a clean source snapshot, push it, and publish existing game packages.

Uses the user's cached Git credential without writing or printing the token.
The original workspace, game packages, signing key and saves stay in place.
"""
import argparse
import configparser
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / '.publish/HeavyMachDefense'
OWNER = '18241950925'
NAME = 'HeavyMachDefense'
TAG = 'v1.0.3-zh4'
ASSETS = [ROOT / 'HeavyMachDefense-Windows.zip',
          ROOT / 'HeavyMachDefense-Windows.zip.sha256',
          ROOT / 'android/HeavyMachDefense-arm64.apk',
          ROOT / 'android/HeavyMachDefense-arm64.apk.sha256']
ENV = dict(os.environ, GCM_INTERACTIVE='Never', GIT_TERMINAL_PROMPT='0')


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd, env=ENV)


def copy(relative):
    src, dest = ROOT / relative, SNAPSHOT / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as src:
        for block in iter(lambda: src.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def prepare():
    if (SNAPSHOT / '.git').exists():
        raise RuntimeError('Snapshot repository already exists; inspect it before publishing again.')
    SNAPSHOT.mkdir(parents=True, exist_ok=True)
    for name in ['.gitignore', 'README.md', 'BUILD.md', 'THIRD_PARTY_NOTICES.md',
                 'RELEASE_NOTES.md', 'requirements.txt']:
        copy(name)
    for path in (ROOT / 'tools').iterdir():
        if path.is_file() and (path.suffix in {'.py', '.ps1', '.cpp', '.cmd', '.rc'}
                              or path.name == 'game.ico'):
            copy(path.relative_to(ROOT))
    for relative in ['android/project/src', 'android/chinese-fonts', 'android/source-support',
                     'windows/runtime/source-support']:
        for path in (ROOT / relative).rglob('*'):
            if path.is_file():
                copy(path.relative_to(ROOT))
    copy('android/project/AndroidManifest.xml')
    for path in (ROOT / 'windows').iterdir():
        if path.is_file() and path.suffix in {'.md', '.json', '.ini', '.cmd'}:
            copy(path.relative_to(ROOT))
    for relative in ['windows/runtime/SOURCE.md', 'windows/runtime/compatibility.patch',
                     'android/HeavyMachDefense-arm64.apk.sha256', 'HeavyMachDefense-Windows.zip.sha256']:
        copy(relative)
    for path in (ROOT / 'android').iterdir():
        if path.is_file() and path.suffix in {'.md', '.json'}:
            copy(path.relative_to(ROOT))
    copy('android/apk-info.txt')
    # Export screenshots actually referenced by the verification documents.
    documents = [ROOT / 'android/汉化验证.md', ROOT / 'windows/verification.md']
    for document in documents:
        for target in re.findall(r'\]\(([^)]+\.png)\)', document.read_text(encoding='utf-8')):
            path = document.parent / target
            if path.is_file():
                copy(path.relative_to(ROOT))
    copy('android/zh-verified-base.png')  # Performance probe reference.
    runtime = ROOT / 'reference/touchHLE'
    modules = configparser.ConfigParser()
    modules.read(runtime / '.gitmodules')
    links = []
    entries = git('ls-files', '--stage', '-z', cwd=runtime).decode().split('\0')
    for entry in entries:
        if not entry:
            continue
        mode, oid, stage_and_path = entry.split(' ', 2)
        path = stage_and_path.split('\t', 1)[1]
        relative = Path('reference/touchHLE') / path
        if mode == '160000':
            section = next(s for s in modules.sections() if modules[s]['path'] == path)
            links.append({'path': relative.as_posix(), 'commit': oid, 'url': modules[section]['url']})
        elif path not in {'.gitmodules', 'AGENTS.md', 'CLAUDE.md'}:
            copy(relative)
    files = {}
    for path in sorted((SNAPSHOT / 'reference/touchHLE').rglob('*')):
        if path.is_file():
            files[path.relative_to(SNAPSHOT).as_posix()] = sha256(path)
    text = ''.join('[submodule "{0}"]\n\tpath = {0}\n\turl = {1}\n'.format(item['path'], item['url'])
                   for item in links)
    (SNAPSHOT / '.gitmodules').write_text(text, encoding='utf-8')
    manifest = {'upstream': 'https://github.com/touchHLE/touchHLE',
                'upstream_base': 'd34530b52174e8a4f1fe43178cc4fb0c99506f9f',
                'local_checkpoint': git('rev-parse', 'HEAD', cwd=runtime).decode().strip(),
                'snapshot_includes_uncommitted_runtime_fixes': True,
                'runtime_file_sha256': files, 'submodules': links,
                'release_assets': {p.name: {'size': p.stat().st_size, 'sha256': sha256(p)} for p in ASSETS}}
    (SNAPSHOT / 'source-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    git('init', '-b', 'main', cwd=SNAPSHOT)
    git('add', '--force', '.', cwd=SNAPSHOT)
    for item in links:
        git('update-index', '--add', '--cacheinfo', '160000,' + item['commit'] + ',' + item['path'], cwd=SNAPSHOT)
    staged = git('ls-files', '-z', cwd=SNAPSHOT).decode().split('\0')
    denied = ('.keystore', '.jks', '.sav', '.apk', '.zip', '.pdb', '.log')
    for name in staged:
        if name and (name.endswith(denied) or any(part in {'touchHLE_sandbox', '.git', 'target'} for part in Path(name).parts)):
            raise RuntimeError('Private or generated file was staged: ' + name)
    git('diff', '--cached', '--check', '--', 'README.md', 'BUILD.md',
        'THIRD_PARTY_NOTICES.md', 'RELEASE_NOTES.md', 'tools/publish_github.py',
        'tools/prepare_dependencies.py', cwd=SNAPSHOT)
    git('commit', '-m', 'Publish Windows port and Android Chinese fixes with build sources', cwd=SNAPSHOT)
    (ROOT / '.publish/manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Prepared source snapshot:', len([x for x in staged if x]), 'tracked entries', flush=True)


def credential():
    result = subprocess.run(['git', 'credential', 'fill'], cwd=ROOT, env=ENV,
                            input='protocol=https\nhost=github.com\n\n', text=True,
                            capture_output=True, check=True)
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if not values.get('password'):
        raise RuntimeError('No cached GitHub credential. Sign in with Git Credential Manager or GitHub CLI first.')
    return values['password']


def api(token, method, path, payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8') if payload is not None else None
    request = urllib.request.Request('https://api.github.com' + path, method=method, data=body,
        headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': NAME + '-publisher',
                 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def upload(token, release, path):
    assets = api(token, 'GET', '/repos/' + OWNER + '/' + NAME + '/releases/' + str(release['id']) + '/assets')
    digest = 'sha256:' + sha256(path)
    existing = next((item for item in assets if item['name'] == path.name), None)
    if existing:
        if existing['size'] != path.stat().st_size or existing.get('digest') != digest:
            raise RuntimeError('Existing asset differs; refusing to overwrite: ' + path.name)
        print('Asset already verified:', path.name, flush=True)
        return existing
    url = urllib.parse.urlsplit(release['upload_url'].split('{', 1)[0])
    connection = http.client.HTTPSConnection(url.hostname, timeout=180)
    request_path = url.path + '?' + urllib.parse.urlencode({'name': path.name})
    connection.putrequest('POST', request_path)
    for name, value in {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                        'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': NAME + '-publisher',
                        'Content-Type': 'application/octet-stream', 'Content-Length': str(path.stat().st_size)}.items():
        connection.putheader(name, value)
    connection.endheaders()
    print('Uploading:', path.name, path.stat().st_size, 'bytes', flush=True)
    with path.open('rb') as source:
        while block := source.read(1024 * 1024):
            connection.send(block)
    response = connection.getresponse()
    data = json.loads(response.read())
    connection.close()
    if response.status != 201:
        raise RuntimeError('Asset upload failed: HTTP ' + str(response.status) + ' ' + data.get('message', ''))
    if data['size'] != path.stat().st_size or data.get('digest') != digest:
        raise RuntimeError('GitHub asset checksum mismatch: ' + path.name)
    print('Uploaded and SHA-256 verified:', path.name, flush=True)
    return data


def publish(private):
    if not (SNAPSHOT / '.git').exists():
        raise RuntimeError('Prepare the source snapshot first.')
    token = credential()
    profile = api(token, 'GET', '/user')
    if profile['login'] != OWNER:
        raise RuntimeError('The cached credential belongs to a different account.')
    repo_path = '/repos/' + OWNER + '/' + NAME
    try:
        repo = api(token, 'GET', repo_path)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        repo = api(token, 'POST', '/user/repos', {
            'name': NAME, 'private': private, 'auto_init': False,
            'description': 'Heavy MACH: Defense Windows port and Android Chinese edition, with build sources and releases',
            'has_wiki': False, 'has_projects': False})
    if repo['private'] != private:
        raise RuntimeError('Existing repository visibility differs from the requested choice.')
    print('Repository:', repo['html_url'], flush=True)
    remotes = git('remote', cwd=SNAPSHOT).decode().splitlines()
    if 'origin' not in remotes:
        git('remote', 'add', 'origin', repo['clone_url'], cwd=SNAPSHOT)
    subprocess.run(['git', 'push', '-u', 'origin', 'main'], cwd=SNAPSHOT, env=ENV, check=True)
    commit = git('rev-parse', 'HEAD', cwd=SNAPSHOT).decode().strip()
    if api(token, 'GET', repo_path + '/git/ref/heads/main')['object']['sha'] != commit:
        raise RuntimeError('GitHub branch does not match the published source commit.')
    try:
        release = api(token, 'GET', repo_path + '/releases/tags/' + TAG)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        release = api(token, 'POST', repo_path + '/releases', {
            'tag_name': TAG, 'target_commitish': commit, 'draft': True, 'prerelease': False,
            'name': 'Heavy MACH: Defense — Windows + Android 1.0.3-zh4',
            'body': (ROOT / 'RELEASE_NOTES.md').read_text(encoding='utf-8')})
    outputs = [upload(token, release, path) for path in ASSETS]
    if release['draft']:
        release = api(token, 'PATCH', repo_path + '/releases/' + str(release['id']), {'draft': False, 'make_latest': 'true'})
    record = {'repository': repo['html_url'], 'private': repo['private'], 'commit': commit,
              'release': release['html_url'], 'tag': TAG,
              'assets': [{'name': item['name'], 'size': item['size'], 'digest': item['digest'],
                          'url': item['browser_download_url']} for item in outputs]}
    (ROOT / '.publish/publication.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps(record, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--private', action='store_true')
    args = parser.parse_args()
    if args.prepare:
        prepare()
    if args.publish:
        publish(args.private)


if __name__ == '__main__':
    main()
