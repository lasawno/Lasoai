#!/usr/bin/env python3
"""Synthetic Auth/Data API test runner for the EXISTING Codespace.

No SDK or package installation. Fixed isolated project; secrets prompted without echo.
Admin key is used ONLY to provision/clean up synthetic test accounts and grant access.
Actual save/restore tests use each user's real signed JWT and publishable key.
"""
import getpass
import json
import os
from pathlib import Path
import secrets
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps/reflex'))
from lasoai_workspace.connector import ConnectorError, ProviderConfig, SupabaseDNAConnector
from lasoai_workspace.dna import export_business, import_business

ORIGIN='https://eqcrmpeoosxnjbtxijgh.supabase.co'

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def api(method,path,key,token=None,body=None,prefer=None):
    headers={'apikey':key,'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    if prefer: headers['Prefer']=prefer
    req=Request(ORIGIN+path,headers=headers,method=method,
                data=json.dumps(body).encode() if body is not None else None)
    try:
        with build_opener(NoRedirect()).open(req,timeout=8) as response:
            raw=response.read(262145)
            if len(raw)>262144: raise RuntimeError('Response too large')
            return response.status,json.loads(raw) if raw else None
    except HTTPError as error:
        # Do not print response bodies: auth errors can contain sensitive input.
        return error.code,None
    except (URLError,OSError,ValueError):
        raise RuntimeError('Network or provider response failed; no sensitive response logged') from None

def require(condition,message):
    if not condition: raise RuntimeError(message)

def denied(call):
    try: call()
    except ConnectorError: return
    raise RuntimeError('Expected access denial')

def main():
    status,_=api('GET','/auth/v1/health','')
    require(status in (200,401),'Isolated provider endpoint is not reachable')
    print(f'PASS bounded provider reachability: HTTP {status}',flush=True)
    publishable=os.environ.get('LASOAI_TEST_PUBLISHABLE_KEY') or getpass.getpass('Test project publishable key (hidden): ')
    ProviderConfig(ORIGIN,publishable)
    admin=os.environ.get('LASOAI_TEST_ADMIN_KEY') or getpass.getpass('Isolated test project secret/service-role key (hidden, used only for fixture setup/cleanup): ')
    require(admin.startswith('sb_secret_') or admin.startswith('eyJ'),'Expected isolated project admin API key')
    users=[]
    passed=[]
    try:
        credentials=[]
        for suffix in ['a','b']:
            email=f'lasoai-system-{secrets.token_hex(10)}-{suffix}@example.invalid'
            password=secrets.token_urlsafe(32)
            status,user=api('POST','/auth/v1/admin/users',admin,admin,
                            {'email':email,'password':password,'email_confirm':True})
            require(status in (200,201) and isinstance(user,dict) and user.get('id'),'Synthetic Auth provisioning failed')
            uid=user['id']; users.append(uid)
            status,_=api('POST','/rest/v1/lasoai_connections',admin,admin,{'owner_id':uid,'enabled':True})
            require(status in (200,201,204),'Founder-admin connection grant failed')
            status,session=api('POST','/auth/v1/token?grant_type=password',publishable,body={'email':email,'password':password})
            require(status==200 and session.get('access_token'),'Real synthetic password sign-in failed')
            credentials.append((email,password,session['access_token']))
        passed.append('two real synthetic Auth identities signed in (no emails sent)')
        a,b=credentials[0][2],credentials[1][2]
        connector=SupabaseDNAConnector(ProviderConfig(ORIGIN,publishable))
        draft={'name':'Synthetic portable test','goals':'keep local only','rules':'unselected private draft'}
        before=dict(draft)
        denied(lambda:connector.save(a,draft,['name'],False))
        connector.save(a,draft,['name'],True)
        require(connector.restore(a)=={'name':draft['name']},'Selected field save/restore mismatch')
        passed.append('explicit consent, partial selected save and restore')
        denied(lambda:connector.restore(b))
        denied(lambda:connector.restore(''))
        status,rows=api('GET','/rest/v1/lasoai_dna?select=owner_id',publishable)
        require(status in (401,403),'Signed-out Data API read was not denied')
        status,_=api('POST','/rest/v1/lasoai_dna',publishable,body={'owner_id':users[0],'document':export_business({}),'selected_fields':['name']})
        require(status in (401,403),'Signed-out Data API write was not denied')
        status,rows=api('GET',f'/rest/v1/lasoai_dna?owner_id=eq.{users[0]}&select=document',publishable,b)
        require(status==200 and rows==[],'Cross-user direct read exposed a record')
        status,_=api('PATCH',f'/rest/v1/lasoai_dna?owner_id=eq.{users[0]}',publishable,a,{'owner_id':users[1]})
        require(status in (401,403),'Owner reassignment accepted')
        passed.append('two-user direct Data API isolation and signed-out denial')
        status,_=api('POST','/auth/v1/logout?scope=local',publishable,a)
        require(status in (200,204),'Session sign-out failed')
        status,rows=api('GET','/rest/v1/lasoai_dna?select=document',publishable,a)
        require(status in (401,403) or status==200 and rows==[],'Old access token still read DNA after sign-out')
        email,password,_=credentials[0]
        status,new=api('POST','/auth/v1/token?grant_type=password',publishable,body={'email':email,'password':password})
        require(status==200,'New session sign-in failed')
        a=new['access_token']
        fresh=SupabaseDNAConnector(ProviderConfig(ORIGIN,publishable))
        require(fresh.restore(a)=={'name':draft['name']},'Durable restore after end-session failed')
        passed.append('old JWT denied after sign-out; durable restore in a new Auth session')
        require(import_business(json.dumps(export_business(draft)))=={**{k:'' for k in ['name','purpose','goals','responsibilities','tools','rules']},**draft},'Portable roundtrip failed')
        require(draft==before,'Local draft mutated')
        def outage(*args): raise ConnectorError('Synthetic outage')
        denied(lambda:SupabaseDNAConnector(ProviderConfig(ORIGIN,publishable),outage).save(a,draft,['name'],True))
        require(draft==before,'Outage lost local draft')
        passed.append('portable export/import and simulated outage without local edit loss')
        fresh.revoke(a)
        denied(lambda:fresh.restore(a))
        denied(lambda:fresh.save(a,draft,['name'],True))
        status,_=api('PATCH',f'/rest/v1/lasoai_connections?owner_id=eq.{users[0]}',publishable,a,{'enabled':True})
        require(status in (401,403),'Revoked user self re-enabled connection')
        passed.append('connection revocation denies existing-session reads/writes and re-enable')
        for name in passed: print('PASS '+name,flush=True)
        print('HTTP TESTS PASSED. Browser/Reflex UI testing is a separate stage.',flush=True)
    finally:
        failures=0
        for uid in users:
            status,_=api('DELETE','/auth/v1/admin/users/'+uid,admin,admin)
            if status not in (200,204): failures+=1
        print('Synthetic account cleanup: '+('complete' if not failures else f'{failures} failed; inspect ONLY lasoai-system- accounts'),flush=True)

if __name__=='__main__':
    try: main()
    except (RuntimeError,ConnectorError,KeyboardInterrupt):
        # No traceback/exception body containing credentials or raw provider payloads.
        print('TEST RUN DID NOT COMPLETE. No end-to-end success claim. Check test-project keys/access; secrets were not logged.',file=sys.stderr)
        sys.exit(1)
