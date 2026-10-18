-- Synthetic SQL-role tests only: not Auth HTTP sign-in or signed-JWT verification.
-- Entire fixture transaction rolls back; no passwords, messages, or real people.
BEGIN;
SET LOCAL statement_timeout = '5s';
CREATE TEMP TABLE lasoai_checks(name text);
GRANT INSERT, SELECT ON lasoai_checks TO authenticated, anon;
INSERT INTO auth.users(id,email,aud,role,created_at,updated_at) VALUES
 ('10000000-0000-4000-8000-000000000001','lasoai-a@example.invalid','authenticated','authenticated',now(),now()),
 ('10000000-0000-4000-8000-000000000002','lasoai-b@example.invalid','authenticated','authenticated',now(),now());
INSERT INTO auth.sessions(id,user_id,created_at,updated_at) VALUES
 ('20000000-0000-4000-8000-000000000001','10000000-0000-4000-8000-000000000001',now(),now()),
 ('20000000-0000-4000-8000-000000000002','10000000-0000-4000-8000-000000000002',now(),now());
INSERT INTO public.lasoai_connections(owner_id) SELECT id FROM auth.users WHERE email IN ('lasoai-a@example.invalid','lasoai-b@example.invalid');
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claims','{"sub":"10000000-0000-4000-8000-000000000001","session_id":"20000000-0000-4000-8000-000000000001"}',true);
INSERT INTO public.lasoai_dna VALUES ('10000000-0000-4000-8000-000000000001',
 '{"schema":"lasoai.business-dna","version":1,"savedAt":"2026-10-18T00:00:00Z","business":{"name":"Synthetic A"}}',ARRAY['name']);
DO $$ BEGIN
 IF (SELECT document->'business' FROM public.lasoai_dna) IS DISTINCT FROM '{"name":"Synthetic A"}'::jsonb THEN RAISE EXCEPTION 'selected save failed'; END IF;
 INSERT INTO lasoai_checks VALUES ('selected-only save and own read');
 BEGIN
   UPDATE public.lasoai_dna SET owner_id='10000000-0000-4000-8000-000000000002' WHERE owner_id='10000000-0000-4000-8000-000000000001';
   RAISE EXCEPTION 'owner reassignment accepted';
 EXCEPTION WHEN insufficient_privilege THEN INSERT INTO lasoai_checks VALUES ('owner reassignment denied'); END;
 BEGIN
   UPDATE public.lasoai_dna SET document=jsonb_set(document,'{business,rules}','"unselected"') WHERE owner_id='10000000-0000-4000-8000-000000000001';
   RAISE EXCEPTION 'unselected field accepted';
 EXCEPTION WHEN check_violation THEN INSERT INTO lasoai_checks VALUES ('unselected field rejected by DB'); END;
END $$;
SELECT set_config('request.jwt.claims','{"sub":"10000000-0000-4000-8000-000000000002","session_id":"20000000-0000-4000-8000-000000000002"}',true);
DO $$ BEGIN
 IF EXISTS(SELECT FROM public.lasoai_dna) THEN RAISE EXCEPTION 'cross-user read'; END IF;
 BEGIN
  INSERT INTO public.lasoai_dna VALUES ('10000000-0000-4000-8000-000000000001','{}',ARRAY['name']);
  RAISE EXCEPTION 'cross-user write';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 INSERT INTO lasoai_checks VALUES ('two-user read and write isolation');
END $$;
SET LOCAL ROLE anon;
SELECT set_config('request.jwt.claims','{}',true);
DO $$ BEGIN
 BEGIN
  PERFORM * FROM public.lasoai_dna;
  RAISE EXCEPTION 'signed-out read';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 BEGIN
  INSERT INTO public.lasoai_dna VALUES ('10000000-0000-4000-8000-000000000001','{}',ARRAY['name']);
  RAISE EXCEPTION 'signed-out write';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 INSERT INTO lasoai_checks VALUES ('signed-out read and write denied');
END $$;
RESET ROLE;
UPDATE auth.sessions SET not_after=now()-interval '1 minute' WHERE id='20000000-0000-4000-8000-000000000001';
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claims','{"sub":"10000000-0000-4000-8000-000000000001","session_id":"20000000-0000-4000-8000-000000000001"}',true);
DO $$ BEGIN
 IF EXISTS(SELECT FROM public.lasoai_dna) THEN RAISE EXCEPTION 'revoked session read'; END IF;
 INSERT INTO lasoai_checks VALUES ('existing claims denied after session expiry');
END $$;
RESET ROLE;
INSERT INTO auth.sessions(id,user_id,created_at,updated_at) VALUES
 ('20000000-0000-4000-8000-000000000003','10000000-0000-4000-8000-000000000001',now(),now());
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claims','{"sub":"10000000-0000-4000-8000-000000000001","session_id":"20000000-0000-4000-8000-000000000003"}',true);
DO $$ BEGIN
 IF (SELECT document->'business'->>'name' FROM public.lasoai_dna) IS DISTINCT FROM 'Synthetic A' THEN RAISE EXCEPTION 'restore in new session failed'; END IF;
 INSERT INTO lasoai_checks VALUES ('stored selection survives new session');
END $$;
UPDATE public.lasoai_connections SET enabled=false WHERE owner_id='10000000-0000-4000-8000-000000000001';
DO $$ BEGIN
 IF EXISTS(SELECT FROM public.lasoai_dna) THEN RAISE EXCEPTION 'revoked connection read'; END IF;
 BEGIN
  UPDATE public.lasoai_connections SET enabled=true WHERE owner_id='10000000-0000-4000-8000-000000000001';
  RAISE EXCEPTION 'self re-enable accepted';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 BEGIN
  INSERT INTO public.lasoai_dna VALUES ('10000000-0000-4000-8000-000000000001','{}',ARRAY['name']);
  RAISE EXCEPTION 'revoked write';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 INSERT INTO lasoai_checks VALUES ('connection revocation blocks existing session and cannot self re-enable');
END $$;
RESET ROLE;
SELECT name AS passed_check FROM lasoai_checks ORDER BY name;
ROLLBACK;
