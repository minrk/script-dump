from __future__ import print_function

from datetime import datetime
import json
import sys
import time

import requests

import requests
import getpass
import json

try:
    from url.parse import urlparse, parse_qs # py3
except ImportError:
    from urlparse import urlparse, parse_qs # py2

try:
    import requests_cache
except ImportError:
    print("no cache")
else:
    requests_cache.install_cache("gh_api")

ISO8601 = "%Y-%m-%dT%H:%M:%SZ"
PER_PAGE = 100
project = "ipython/ipython"
api_url = "https://api.github.com"
repo_url = "%s/repos/%s" % (api_url, project)

try:
    from IPython.core.getipython import get_ipython
except ImportError:
    get_ipython = lambda : None

def round_hour(dt):
    return dt.replace(minute=0,second=0,microsecond=0)

def _parse_datetime(s):
    """Parse dates in the format returned by the Github API."""
    if s:
        return datetime.strptime(s, ISO8601)
    else:
        return datetime.fromtimestamp(0)

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
    token = response.json()['token']
    keyring.set_password('github', fake_username, token)
    return token

def make_auth_header():
    return {'Authorization': 'token ' + get_auth_token()}

def api_request(uri, headers=None, auth=True, method='get', json=True, data=None, **params):
    h = make_auth_header() if auth else {}
    if headers:
        h.update(headers)
    f = getattr(requests, method)
    if uri.startswith("http"):
        url = uri
    else:
        url = "%s/%s" % (repo_url, uri)
    if '?' in url:
        url, qs = url.split('?')
        q = parse_qs(qs)
        params.update(q)
    if params:
        param_s = " with %s" % params
    else:
        param_s = ""
    print("%s: %s%s" % (method, url, param_s), file=sys.stderr)
    r = f(url, headers=h, data=data, params=params)
    r.raise_for_status()
    if json:
        return r.json()
    else:
        return r
    

def get_paged_request(url, **params):
    """get a full list, handling APIv3's paging"""
    results = []
    params.setdefault("per_page", 100)
    # print("fetching %s with %s" % (url, params), file=sys.stderr)
    while True:
        # print("fetching page %s" % (url), file=sys.stderr)
        r = api_request(url, json=False, **params)
        results.extend(r.json())
        if 'next' in r.links:
            url = r.links['next']['url']
        else:
            break
    return results

def get_issues_list(**params):
    """get issues list"""
    params.setdefault("state", "closed")
    pages = get_paged_request("issues", **params)
    return pages

def get_pulls_list(auth=False, **params):
    """get pulls list"""
    params.setdefault("state", "closed")
    pages = get_paged_request("pulls", **params)
    return pages

def issue2pull(issue):
    return api_request(issue['pull_request']['url'])

def get_pulls_list(auth=False, **params):
    """get pulls list"""
    params.setdefault("state", "closed")
    pages = get_paged_request("pulls", **params)
    return pages

def is_pull_request(issue):
    """Return True if the given issue is a pull request."""
    return bool(issue.get('pull_request', {}).get('html_url', None))

def split_issues(both):
    issues = []
    pulls = []
    for i in both:
        if is_pull_request(i):
            pulls.append(issue2pull(i))
        else:
            issues.append(i)
    
    return issues, pulls

def get_milestones(**params):
    milestones = get_paged_request("milestones", **params)
    return milestones

def get_milestone_id(milestone, **params):
    milestones = get_milestones(**params)
    for mstone in milestones:
        if mstone['title'] == milestone:
            return mstone['number']
    else:
        raise KeyError("milestone %s not found" % milestone)

def closed_without_milestone():
    everything = get_issues_list(state='closed', milestone='none')
    issues = [ i for i in everything if not is_pull_request(i) ]
    pulls = [ i for i in everything if is_pull_request(i) ]
    # issues = sorted(issues, key=lambda i: i['closed_at'], reverse=True)
    print("%i issues closed without milestone" % len(issues))
    for issue in issues:
        print(issue['number'], issue['title'])
    print("%i pulls closed without milestone" % len(pulls))
    for issue in pulls:
        print(issue['number'], issue['title'])
    return issues, pulls

def mark_old_issues():
    """mark super old issues with the 'old' milestone"""
    old = get_milestone_id("old", state='closed')
    issues = get_issues_list(state='closed', milestone='none')
    issues = [ i for i in issues if not is_pull_request(i) ]
    issues = [ i for i in issues if i['number'] < 2000 ]
    issues = [ i for i in issues if i['milestone'] is None ]
    print(len(issues))
    base_url = "https://api.github.com/repos/ipython/ipython/issues"
    for issue in issues:
        # print(issue)
        url = "%s/%i" % (base_url, issue['number'])
        print(url)
        r = requests.patch(url, data=json.dumps(dict(milestone=old)), headers=make_auth_header())
        r.raise_for_status()

def mark_unmerged_noaction():
    pulls = get_pulls_list(state='closed')
    no_milestone = [p for p in pulls if p['milestone'] is None]
    
    noaction = get_milestone_id("no action", state='open')

    unmerged = [pull for pull in no_milestone if pull['merged_at'] is None]
    unmerged = sorted(unmerged, key=lambda p: p['number'])
    base_url = "https://api.github.com/repos/ipython/ipython/issues"
    for pull in unmerged:
        url = "%s/%i" % (base_url, pull['number'])
        print(url)
        r = requests.patch(url, data=json.dumps(dict(milestone=noaction)), headers=make_auth_header())
        r.raise_for_status()

def get_tag_date(tagname):
    tags = api_request("tags")
    for tag in tags:
        if tag['name'] == tagname:
            commit = api_request(tag['commit']['url'])
            return _parse_datetime(commit['commit']['author']['date'])
    raise KeyError("%s not found in %s" % (tagname, [ tag['name'] for tag in tags]))

def mark_branch_pr(base, milestone, apply=False):
    pulls = get_pulls_list(base=base, state='closed')
    pulls = [p for p in pulls if p['milestone'] is None]
    pulls = [p for p in pulls if p['merged_at'] is not None]
    ms = get_milestone_id(milestone, state='closed')
    for pull in pulls:
        print("%s: %s %s (%s)" % (pull['number'], pull['base']['ref'], pull['title'], pull['merged_at']))
        if apply:
            api_request("issues/%i" % pull['number'], method='patch', data=json.dumps(dict(milestone=ms)))
    return pulls
    
def mark_before_tag(tag, apply=False):
    # pulls = get_pulls_list(state='closed')
    everything = get_issues_list(state='closed', milestone='none')
    
    try:
        ms = get_milestone_id(tag.replace('rel-', ''), state='closed')
    except KeyError:
        ms = get_milestone_id(tag.replace('rel-', '').rsplit('.',1)[0], state='closed')
    tagday = get_tag_date(tag)
    
    everything = [ i for i in everything if _parse_datetime(i['closed_at']) < tagday ]

    issues, pulls = split_issues(everything)
    # pulls = [ get_pull_request(i['number']) for i in issues ]
    # filter out those actually with no milestone
    # pulls = [p for p in pulls if p['milestone'] is None]
    # filter out those not against master
    # pulls = [ p for p in pulls if p['base']['ref'] == 'master' ]
    # filter out unmerged PRs
    pulls = [p for p in pulls if p['merged_at'] is not None]
    # filter out those newer than the tag
    pulls = [ p for p in pulls if _parse_datetime(p['merged_at']) < tagday ]
    pulls = sorted(pulls, key=lambda p: p['number'])
    print("tag: %s (%s)" % (tag, tagday))
    for pull in pulls:
        print("%s: %s %s (%s)" % (pull['number'], pull['base']['ref'], pull['title'], pull['merged_at']))
        if apply:
            api_request("issues/%i" % pull['number'], method='patch', data=json.dumps(dict(milestone=ms)))
    return pulls
    
if __name__ == '__main__' and get_ipython() is None:
    # mark_old_issues()
    closed_without_milestone()
    # mark_unmerged_noaction()
