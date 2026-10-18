import unittest
from lasoai_workspace.codespaces_callback import CodespacesCallbackRedirect


class CallbackTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, path, method="GET", query=b"", kind="http"):
        messages, calls = [], []
        async def upstream(scope, receive, send):
            calls.append(scope)
            await send({"type": "upstream-reached"})
        async def receive(): return {"type": "http.request", "body": b""}
        async def send(message): messages.append(message)
        scope={"type":kind,"method":method,"path":path,"query_string":query}
        await CodespacesCallbackRedirect(upstream)(scope,receive,send)
        return messages, calls

    async def test_callback_returns_home_without_browser_storage_or_scripts(self):
        for method in ["GET", "HEAD"]:
            for path in ["/auth-codespace", "/auth-codespace/"]:
                messages,calls=await self.request(path,method)
                self.assertFalse(calls)
                self.assertEqual(messages[0]['status'],303)
                headers=dict(messages[0]['headers'])
                self.assertEqual(headers[b'location'],b'/')
                self.assertEqual(headers[b'cache-control'],b'no-store')
                self.assertEqual(messages[1]['body'],b'')

    async def test_html_revalidates_but_asset_cache_policy_is_unchanged(self):
        for content_type, expected in [(b"text/html; charset=utf-8", b"no-store"),
                                       (b"application/javascript", b"public, max-age=31536000")]:
            messages = []
            async def upstream(scope, receive, send):
                await send({"type":"http.response.start","status":200,
                            "headers":[(b"content-type",content_type),
                                       (b"cache-control",b"public, max-age=31536000")]})
                await send({"type":"http.response.body","body":b"page"})
            async def send(message): messages.append(message)
            await CodespacesCallbackRedirect(upstream)({"type":"http","method":"GET","path":"/"},None,send)
            self.assertEqual(dict(messages[0]['headers'])[b'cache-control'],expected)
            self.assertEqual(messages[1]['body'],b'page')

    async def test_untrusted_redirect_parameters_cannot_leave_origin(self):
        for query in [b'redirect_to=https://evil.example',b'redirect_to=//evil.example',
                      b'redirect_to=%0d%0aX-Evil:yes',b'redirect_to=/auth-codespace']:
            messages,_=await self.request('/auth-codespace',query=query)
            self.assertEqual(dict(messages[0]['headers'])[b'location'],b'/')

    async def test_app_events_uploads_lifespan_and_other_methods_pass_through(self):
        for path,method,kind in [('/', 'GET','http'),('/ping','GET','http'),
                                 ('/_event/','GET','http'),('/_event/','GET','websocket'),
                                 ('/_upload','POST','http'),('/auth-codespace','POST','http'),
                                 ('','GET','lifespan')]:
            messages,calls=await self.request(path,method,kind=kind)
            self.assertEqual(len(calls),1)
            self.assertEqual(messages,[{'type':'upstream-reached'}])
