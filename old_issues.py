from __future__ import print_function

from datetime import datetime
import json
import sys
import time

import requests

dfmt = '%Y/%m/%d %H:%M:%S'

sage_start = datetime(2011, 3, 20, 0, 0, 0)

def get_paged_request(url, headers=None, **params):
    """get a full list, handling APIv3's paging"""
    results = []
    params.setdefault("per_page", 100)
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

def get_issues_list(project, auth=False, **params):
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

def sage(opens=None, closed=None):
    fetched = None
    if opens is None:
        fetched = fetched if fetched else fetch_issues()
        opens = fetched[1]
    if closed is None:
        fetched = fetched if fetched else fetch_issues()
        closed = fetched[2]
    
    print("Issues Identified")
    c = 0
    for issue in filter(lambda i: 'pull_request_url' not in i, opens):
        ds = issue['created_at'].rsplit(' ',1)[0]
        opened = datetime.strptime(ds, dfmt)
        if opened > sage_start:
            print '    * [[%s|%i]] %s'%(issue['html_url'], issue['number'], issue['title'])
            c+=1
    print c
    print "Issues Closed and Pull Requests Merged"
    c=0
    for issue in closed:
        ds = issue['closed_at'].rsplit(' ',1)[0]
        ctime = datetime.strptime(ds, dfmt)
        if ctime > sage_start:
            if 'pull_request_url' in issue:
                print '    * Merged: [[%s|%i]] %s'%(issue['pull_request_url'], issue['number'], issue['title'])
                c+=1
            else:
                print '    * Closed: [[%s|%i]] %s'%(issue['html_url'], issue['number'], issue['title'])
                c+=1
    print c
    

def update_labels(issues):
    token = "3178363dd9e085f4f34e06194f52f4ff"
    login = "minrk"
    form = '?'+urllib.urlencode(dict(login=login, token=token))
    url="https://github.com/api/v2/json/issues/label/%s/ipython/ipython/%s/%i"
    for issue in issues:
        tic = time.time()
        if issue['state'] == 'closed':
            # don't edit closed issues
            continue
        labels = ordered_labels(issue['number'])
        # labels = list(issue['labels']) # copy
        # if 'minrk' not in labels:
        #     continue
        # 
        # print issue['number'], labels, issue['labels']
        tomove = []
        if not any([ lab.startswith('prio') for lab in labels]):
            continue
        while not labels[0].startswith('prio'):
            tomove.append(labels.pop(0))
        # prio = [ label for label in labels if label.startswith('prio')]
        # if prio:
        #     prio = prio[0]
        #     labels.remove(prio)
        # 
        # status = [ label for label in labels if label.startswith('status')]
        # if status:
        #     status = status[0]
        #     labels.remove(status)
        #     tomove.append(status)
        
        print issue['number'], issue['title'], issue['labels'], labels, tomove
        # continue
        for tag in tomove:
            print tag
            remove_url = url%('remove', tag, issue['number'])
            add_url = url%('add', tag, issue['number'])
            # print remove_url
            rep = fetch_json(remove_url+form)
            if 'error' in rep:
                print rep
                return
            time.sleep(max(1-(time.time()-tic),0))
            tic = time.time()
            rep = fetch_json(add_url+form)
            if 'error' in rep:
                print rep
                print "State may be inconsistent! Manually add tag %r to issue %i"%(tag, issue['number'])
                return
            time.sleep(max(1-(time.time()-tic),0))
            # print remove_url, add_url
        

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


        