-- Reviewed setup, NOT run by app startup. Apply only to a founder-selected test project.
-- Founder/admin explicitly grants a connection per real Auth user after provisioning.
BEGIN;
CREATE SCHEMA IF NOT EXISTS lasoai_private;
REVOKE ALL ON SCHEMA lasoai_private FROM PUBLIC, anon;
GRANT USAGE ON SCHEMA lasoai_private TO authenticated;

CREATE FUNCTION lasoai_private.live_session() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
  SELECT auth.uid() IS NOT NULL AND EXISTS (
    SELECT 1 FROM auth.sessions s JOIN auth.users u ON u.id = s.user_id
    WHERE s.user_id = auth.uid() AND s.id::text = auth.jwt()->>'session_id'
      AND (s.not_after IS NULL OR s.not_after > now())
      AND u.deleted_at IS NULL AND NOT u.is_anonymous
      AND (u.banned_until IS NULL OR u.banned_until <= now())
  );
$$;
REVOKE ALL ON FUNCTION lasoai_private.live_session() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION lasoai_private.live_session() TO authenticated;

CREATE FUNCTION lasoai_private.valid_document(doc jsonb, fields text[]) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY INVOKER SET search_path = '' AS $$
DECLARE k text; v jsonb; lim integer;
BEGIN
  IF doc IS NULL OR fields IS NULL OR jsonb_typeof(doc) <> 'object'
     OR NOT doc ?& ARRAY['schema','version','savedAt','business']
     OR (SELECT count(*) FROM jsonb_object_keys(doc)) <> 4
     OR doc->>'schema' <> 'lasoai.business-dna' OR doc->'version' <> '1'::jsonb
     OR jsonb_typeof(doc->'savedAt') <> 'string'
     OR jsonb_typeof(doc->'business') <> 'object'
     OR cardinality(fields) < 1 OR cardinality(fields) > 6
     OR array_position(fields, NULL) IS NOT NULL
     OR cardinality(fields) <> (SELECT count(DISTINCT f) FROM unnest(fields) f)
     OR NOT fields <@ ARRAY['name','purpose','goals','responsibilities','tools','rules']::text[]
     OR (SELECT count(*) FROM jsonb_object_keys(doc->'business')) <> cardinality(fields)
     OR NOT (doc->'business') ?& fields THEN RETURN false; END IF;
  IF NOT doc->>'savedAt' ~ '(Z|[+-][0-9]{2}:[0-9]{2})$' THEN RETURN false; END IF;
  PERFORM (doc->>'savedAt')::timestamptz;
  FOR k,v IN SELECT * FROM jsonb_each(doc->'business') LOOP
    lim := CASE k WHEN 'name' THEN 160 WHEN 'purpose' THEN 2000 ELSE 10000 END;
    IF jsonb_typeof(v) <> 'string' OR char_length(v #>> '{}') > lim THEN RETURN false; END IF;
  END LOOP;
  RETURN true;
EXCEPTION WHEN OTHERS THEN RETURN false;
END;
$$;
REVOKE ALL ON FUNCTION lasoai_private.valid_document(jsonb,text[]) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION lasoai_private.valid_document(jsonb,text[]) TO authenticated;

CREATE TABLE public.lasoai_connections (
  owner_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  enabled boolean NOT NULL DEFAULT true
);
CREATE TABLE public.lasoai_dna (
  owner_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  document jsonb NOT NULL,
  selected_fields text[] NOT NULL,
  CONSTRAINT portable_selected_document CHECK (lasoai_private.valid_document(document,selected_fields))
);
ALTER TABLE public.lasoai_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lasoai_dna ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.lasoai_connections, public.lasoai_dna FROM PUBLIC, anon, authenticated;
GRANT SELECT, UPDATE(enabled) ON public.lasoai_connections TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.lasoai_dna TO authenticated;
CREATE POLICY own_connection_read ON public.lasoai_connections FOR SELECT TO authenticated
  USING ((SELECT auth.uid()) = owner_id AND (SELECT lasoai_private.live_session()));
CREATE POLICY own_connection_revoke ON public.lasoai_connections FOR UPDATE TO authenticated
  USING ((SELECT auth.uid()) = owner_id AND (SELECT lasoai_private.live_session()))
  WITH CHECK ((SELECT auth.uid()) = owner_id AND NOT enabled AND (SELECT lasoai_private.live_session()));
CREATE POLICY own_live_dna ON public.lasoai_dna FOR ALL TO authenticated
  USING ((SELECT auth.uid()) = owner_id AND (SELECT lasoai_private.live_session()) AND EXISTS
    (SELECT 1 FROM public.lasoai_connections c WHERE c.owner_id = (SELECT auth.uid()) AND c.enabled))
  WITH CHECK ((SELECT auth.uid()) = owner_id AND (SELECT lasoai_private.live_session()) AND EXISTS
    (SELECT 1 FROM public.lasoai_connections c WHERE c.owner_id = (SELECT auth.uid()) AND c.enabled));
COMMIT;
