#!/usr/bin/env python3

import argparse
import getpass
import json

import keyring
import requests
try:
    import requests_cache
except ImportError:
    print("no cache")

class Issue(object):
    def __init__(self, data, repo, session):
        self._data = data
        self.repo = repo
        self._session = session
    
    def __dir__(self):
        return super().__dir__() + list(self._data)
    
    def _repr_pretty_(self, p, cycle):
        p.text()
        p.text("Issue: " + json.dumps(self._data, indent=1))
    
    def __getattr__(self, key):
        return self._data[key]
    
    def __getitem__(self, key):
        return self._data[key]
    
    def close(self):
        return self._session.patch(self.url, data={
            'state': 'closed'
        })
    
    def comment(self, body):
        return self._session.post(self.comments_url, data={
            'body': body,
        })


def migrate_comment(comment):
    lines = [
        '@{user} commented at {date}'.format(
            user=comment['user']['login'],
            date=comment['created_at'],
        )
    ]
    lines.append(comment['body'])
    
    return '\n\n'.join(lines)

def migrated_issue_body(issue):
    lines = [
        '@{user} opened {repo}#{number} at {date}'.format(
            repo=issue.repo,
            number=issue.number,
            user=issue['user']['login'],
            date=issue['created_at'],
        )
    ]
    lines.append(issue['body'])
    
    return '\n\n'.join(lines)
    

class GitHubSession(requests.Session):
    github = 'https://api.github.com/'
    
    def authorize(self):
        token = keyring.get_password('github-issue-migration', 'ignored')
        if token is not None:
            self.set_auth_header(token)
            return
        print("Please enter your github username and password. These are not "
               "stored, only used to get an OAuth token. You can revoke this at "
               "any time on GitHub.")
        user = input("Username: ")
        pw = getpass.getpass("Password: ")
        body = {
          "scopes": [
            "public_repo",
          ],
          "note": "Jupyter Issue Migration",
          "note_url": "https://github.com/minrk",
        }
        r = self.post('authorizations', auth=(user, pw),
            data=json.dumps(body)
        )
        token = r['token']
        keyring.set_password('github-issue-migration', 'ignored', token)
        self.set_auth_header(token)
    
    def set_auth_header(self, token):
        self.headers.update({'Authorization': 'token %s' % token})
    
    def request(self, method, url, *args, **kwargs):
        """Make request to GitHub API, and parse JSON reply
        
        So instead of:
        
            r = s.get('http://.../path/')
            r.raise_for_status()
            reply = r.json()
        
        Do:
        
            reply = s.get('path')
        """
        if '://' not in url:
            url = self.github + url
        if 'data' in kwargs and isinstance(kwargs['data'], dict):
            kwargs['data'] = json.dumps(kwargs['data'])
        r = super().request(method, url, *args, **kwargs)
        r.raise_for_status()
        return r.json()
    
    def get_issue(self, repo, number):
        """Get an Issue for a given repo"""
        issue = self.get('repos/%s/issues/%i' % (repo, number))
        issue = Issue(issue, repo, self)
        return issue
    
    def create_issue(self, repo, issue):
        issue = self.post('repos/%s/issues' % repo, data=issue)
        issue['repo'] = repo
        return Issue(issue, repo, self)
    
    def milestone_number(self, repo, title):
        milestones = self.get('repos/%s/milestones' % repo)
        for m in milestones:
            if m['title'] == title:
                return m['number']
        
    
    def migrate_issue(self, number, from_repo, to_repo):
        issue = self.get_issue(from_repo, number)
        
        new_issue = {
            'title': issue.title,
            'body': migrated_issue_body(issue),
            'labels': [ label['name'] for label in issue.labels],
        }
        if issue['assignee']:
            new_issue['assignee'] = issue['assignee']['login']
        if issue['milestone']:
            milestone_number = self.milestone_number(to_repo, issue['milestone']['title'])
            if milestone_number is not None:
                new_issue['milestone'] = milestone_number
        # create the new issue
        new_issue = self.create_issue(to_repo, new_issue)
        # migrate comments
        if issue.comments:
            # if any comments, migrate them as well
            comments = self.get(issue.comments_url)
            for comment in comments:
                new_comment = migrate_comment(comment)
                new_issue.comment(new_comment)
        # comment on original:
        issue.comment("Migrated to {repo}#{number}".format(
            repo=to_repo,
            number=new_issue.number,
        ))
        issue.close()

def main():
    """docstring for main"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--from', type=str, default='minrk/comment-test-A')
    parser.add_argument('--to', type=str, default='minrk/comment-test-B')
    parser.add_argument('issues', nargs='*', type=int,
                    help="The issue numbers to migrate")
    s = GitHubSession()
    s.authorize()

if __name__ == '__main__':
    s = GitHubSession()
    s.authorize()
    
