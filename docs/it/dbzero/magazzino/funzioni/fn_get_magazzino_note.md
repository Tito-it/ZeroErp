{% include-markdown "it/dbzero/magazzino/manual/fn_get_magazzino_note.md" %}
# ⚙️ Funzione `fn_get_magazzino_note`

```sql
CREATE FUNCTION fn_get_magazzino_note(_target_tipo text, _target_id bigint, _target_riga_id bigint, _include_doc boolean, _include_righe boolean, _only_visible boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_get_magazzino_note(_target_tipo text, _target_id bigint, _target_riga_id bigint DEFAULT NULL::bigint, _include_doc boolean DEFAULT true, _include_righe boolean DEFAULT true, _only_visible boolean DEFAULT true)
 RETURNS TABLE(target_tipo text, target_id bigint, target_riga_id bigint, anchor_tipo text, posizione text, seq integer, testo text, testo_md text, stile character varying, lingua character varying, visibile boolean, solo_stampa boolean, meta jsonb, data_insert timestamp with time zone, user_insert text, data_update timestamp with time zone, user_update text)
 LANGUAGE sql
 STABLE
AS $function$
  SELECT * FROM script.fn_get_note('magazzino.note'::regclass,
                                   _target_tipo, _target_id, _target_riga_id,
                                   _include_doc, _include_righe, _only_visible);
$function$

COMMENT ON FUNCTION magazzino.fn_get_magazzino_note(_target_tipo text, _target_id bigint, _target_riga_id bigint, _include_doc boolean, _include_righe boolean, _only_visible boolean)
IS 'Wrapper su script.fn_get_note per la tabella magazzino.note.';
```

</div>

---
{% include-markdown "signature-core.md" %}
