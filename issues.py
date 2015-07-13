from __future__ import print_function

from datetime import datetime
import getpass
import json
import sys
import time

import requests
try:
    import requests_cache
except ImportError:
    print("no cache")
else:
    requests_cache.install_cache("gh_api")

dfmt = '%Y/%m/%d %H:%M:%S'

# Keyring stores passwords by a 'username', but we're not storing a username and
# password
fake_username = 'ipython_tools'
token = None
def get_auth_token():
    global token

    if token is not None:
        return token

    import keyring
    token = keyring.get_password('github', fake_username)
    if token is not None:
        return token

    print("Please enter your github username and password. These are not "
           "stored, only used to get an oAuth token. You can revoke this at "
           "any time on Github.")
    user = input("Username: ")
    pw = getpass.getpass("Password: ")

    auth_request = {
      "scopes": [
        "public_repo",
        "gist"
      ],
      "note": "IPython tools",
      "note_url": "https://github.com/ipython/ipython/tree/master/tools",
    }
    response = requests.post('https://api.github.com/authorizations',
                            auth=(user, pw), data=json.dumps(auth_request))
    response.raise_for_status()
    token = json.loads(response.text)['token']
    keyring.set_password('github', fake_username, token)
    return token

def make_auth_header():
    return {'Authorization': 'token ' + get_auth_token()}

def get_paged_request(url, headers=None, **params):
    """get a full list, handling APIv3's paging"""
    results = []
    params.setdefault("per_page", 1000)
    while True:
        print("fetching %s with %s" % (url, params), file=sys.stderr)
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        results.extend(response.json())
        if 'next' in response.links:
            url = response.links['next']['url']
        else:
            break
    return results

def get_issues_list(project, auth=True, **params):
    """get issues list"""
    params.setdefault("state", "closed")
    url = "https://api.github.com/repos/{project}/issues".format(project=project)
    if auth:
        headers = make_auth_header()
    else:
        headers = None
    pages = get_paged_request(url, headers=headers, **params)
    return pages

def fetch_issues():
    # global issues
    issues = get_issues_list("ipython/ipython")
    map(squash_issue, issues)
    
    open_issues = [ i for i in issues if i['state'] == 'open' ]
    closed_issues = [ i for i in issues if i['state'] == 'closed' ]
    return issues, open_issues, closed_issues

def fetch_open(key='number'):
    # global issues
    _,issues,_ = fetch_issues()
    
    return sorted(issues, key=lambda x: x[key])

def fetch_closed():
    # closed issues
    return fetch_issues()[-1]

def asdict(issues):
    d = {}
    for i in issues:
        d[i['number']] = i
    return d

def squash_issue(issue):
    issue['labels'] = [label['name'] for label in issue['labels']]
    if issue['milestone']:
        issue['milestone'] = issue['milestone']['title']

def print_issue(issue):
    print("%i: %s"%(issue['number'], issue['title']))
    print("    ", issue['milestone'], issue['labels'])
    
def todo(issues=None):
    if issues is None:
        issues = globals()['issues']
    status_specified = [ i['number'] for i in issues if any([lab.startswith('status-') for lab in i['labels'] ]) ]
    # prio_specified = [ i['number'] for i in issues if any([lab.startswith('prio-') for lab in i['labels'] ]) ]
    type_specified = [ i['number'] for i in issues if ('bug' in i['labels'] or 'enhancement' in i['labels']) ]
    fully_specified = set(status_specified).intersection(set(type_specified))#intersection(set(prio_specified)).
    for issue in sorted(issues, key=lambda x: x['number']):
        # labels = issue['labels']
        # if not (any([ lab.startswith('status-') for lab in labels]) and \
        #     any([ lab.startswith('prio-') for lab in labels]) and \
            # ('bug' in labels or 'enhancement' in labels)):
        if issue['number'] not in fully_specified and not issue.get('pull_request_url',None):# and issue['number']%4==1:
            # tags incomplete!
            print_issue(issue)

def active(issues):
    c = 0
    for issue in issues:
        if 'status-active' in issue['labels']:
            c+=1
            print_issue(issue)
    return c

def dormant(issues):
    c = 0
    for issue in issues:
        if 'status-dormant' in issue['labels']:
            c+=1
            print_issue(issue)
    return c


def unlabeled(issues):
    statuses = set(['status-active', 'status-dormant'])
    types = set(['type-bug', 'type-enhancement', 'docs'])
    prios = set(['prio-low', 'prio-medium', 'prio-high', 'prio-critical'])
    c = 0
    for issue in issues:
        if issue['state'] == 'closed':
            continue
        elif issue['pull_request']['html_url']:
            continue
        labelset = set(issue['labels'])
        if issue['milestone'] or 'status-dormant' in labelset or 'type-enhancement' in labelset:
            # ignore any already marked for a milestone or dormant
            continue
        if not labelset.intersection(types) or \
                not labelset.intersection(prios) or \
                not labelset.intersection(statuses):
            print_issue(issue)
            c += 1
    print("%i issues without adequate labels" % c)

def closed_without_milestone(issues):
    c = 0
    print(len(issues))
    for issue in issues:
        if issue['state'] == 'open':
            continue
        elif issue['pull_request']['html_url']:
            continue
        if not issue['milestone']:
            print_issue(issue)
    if c:
        print("%i issues closed without milestone" % c)
        

if __name__ == '__main__':
    try:
        get_ipython
    except NameError:
        issues, opens, closed  = fetch_issues()
        unlabeled(opens)
        closed_without_milestone(closed)


