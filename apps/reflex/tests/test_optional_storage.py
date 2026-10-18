import copy
import json
import unittest
from unittest.mock import patch
from lasoai_workspace.dna import LIMITS, export_business, import_business, merge_business
from lasoai_workspace.connector import ConnectorError, ProviderConfig, SupabaseDNAConnector, NoRedirect

A='10000000-0000-4000-8000-000000000001'
B='10000000-0000-4000-8000-000000000002'

class FakeProvider:
    """Contract fixture, NOT evidence of live provider isolation."""
    def __init__(self):
        self.calls=[]; self.rows={}; self.revoked=set(); self.outage=False
    def __call__(self, method, url, headers, body):
        self.calls.append((method,url,copy.deepcopy(body)))
        token=headers['Authorization'].removeprefix('Bearer ')
        if self.outage or token not in [A,B] or token in self.revoked:
            raise ConnectorError('Denied or unavailable')
        if url.endswith('/auth/v1/user'): return {'id':token}
        if method=='POST':
            self.rows[token]=copy.deepcopy(body)
            return [copy.deepcopy(body)]
        if method=='GET': return [copy.deepcopy(self.rows[token])] if token in self.rows else []
        if method=='PATCH':
            self.revoked.add(token)
            return [{'enabled':False}]
        raise AssertionError(method)

class PortableTests(unittest.TestCase):
    def test_lossless_portable_export_import(self):
        business={k:f'{k}: Café\n  literal <script>' for k in LIMITS}
        self.assertEqual(import_business(json.dumps(export_business(business))),business)
    def test_partial_import_keeps_unselected_local_fields(self):
        doc=export_business({}); doc['business']={'goals':''}
        result=merge_business({'name':'local','goals':'old'},import_business(json.dumps(doc)))
        self.assertEqual(result['name'],'local'); self.assertEqual(result['goals'],'')
    def test_invalid_imports(self):
        good=export_business({'name':'valid'})
        cases=[[],None,{**good,'owner_id':A},{**good,'version':True},{**good,'schema':'other'},
               {**good,'savedAt':'2020-01-01'},{**good,'business':{'api_key':'no'}},
               {**good,'business':{'name':'a'*161}},{**good,'business':{'tools':[]}}]
        for data in cases:
            with self.subTest(data=data), self.assertRaises(ValueError): import_business(json.dumps(data))
        for raw in ['{"schema":1,"schema":2}','x'*262145,'['*10000]:
            with self.assertRaises(ValueError): import_business(raw)

class ConnectorTests(unittest.TestCase):
    def setUp(self):
        self.provider=FakeProvider()
        self.config=ProviderConfig('https://example.supabase.co','sb_publishable_test')
        self.connector=SupabaseDNAConnector(self.config,self.provider)
    def test_selected_save_and_new_session_restore(self):
        draft={'name':'test','rules':'never upload this'}
        self.connector.save(A,draft,['name'],True)
        self.assertEqual(self.provider.rows[A]['document']['business'],{'name':'test'})
        self.assertNotIn('never upload this',json.dumps(self.provider.calls))
        fresh=SupabaseDNAConnector(self.config,self.provider)
        self.assertEqual(fresh.restore(A),{'name':'test'})
        self.assertEqual(draft['rules'],'never upload this')
    def test_consent_selection_before_any_network(self):
        for fields,consent in [(['name'],False),([],True),(['name','name'],True),(['owner_id'],True)]:
            with self.assertRaises(ConnectorError): self.connector.save(A,{},fields,consent)
        self.assertEqual(self.provider.calls,[])
    def test_contract_isolation_signedout_and_revocation(self):
        self.connector.save(A,{'name':'A'},['name'],True)
        with self.assertRaises(ConnectorError): self.connector.restore(B)
        with self.assertRaises(ConnectorError): self.connector.restore('')
        self.connector.save(B,{'name':'B'},['name'],True)
        self.assertEqual(self.connector.restore(B),{'name':'B'})
        self.connector.revoke(A)
        with self.assertRaises(ConnectorError): self.connector.restore(A)
        with self.assertRaises(ConnectorError): self.connector.save(A,{},['name'],True)
    def test_outage_no_loss_retry_or_implicit_upload(self):
        draft={'name':'local unsaved','goals':'keep'}; before=copy.deepcopy(draft)
        self.provider.outage=True
        with self.assertRaises(ConnectorError): self.connector.save(A,draft,['name'],True)
        self.assertEqual(draft,before); self.assertEqual(len(self.provider.calls),1)
        self.assertEqual(self.provider.rows,{})
        self.assertEqual(import_business(json.dumps(export_business(draft)))['name'],draft['name'])
    def test_disabled_no_network_or_token_retention(self):
        with patch.dict('os.environ',{},clear=True): self.assertIsNone(ProviderConfig.from_environment())
        with self.assertRaises(ConnectorError): SupabaseDNAConnector(None,self.provider)
        self.assertEqual(self.provider.calls,[])
        self.connector.save(A,{},['name'],True)
        self.assertNotIn(A,repr(self.connector.__dict__))
    def test_config_and_no_redirect_token_leak(self):
        for url,key in [('http://example.com','sb_publishable_test'),('https://u:p@example.com','sb_publishable_test'),
                        ('https://example.com/path','sb_publishable_test'),('https://example.com','sb_secret_no'),
                        ('https://example.com','eyJservice_role')]:
            with self.assertRaises(ConnectorError): ProviderConfig(url,key)
        self.assertIsNone(NoRedirect().redirect_request(None,None,302,'',{},'https://attacker.test'))
    def test_no_false_save_success(self):
        def request(method,url,headers,body): return {'id':A} if url.endswith('/user') else []
        with self.assertRaises(ConnectorError): SupabaseDNAConnector(self.config,request).save(A,{},['name'],True)

if __name__=='__main__': unittest.main()
