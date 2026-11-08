# ⚙️ Funzione `fn_segment_key_uid`

```sql
CREATE FUNCTION fn_segment_key_uid(p_segment_key character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_segment_key_uid(p_segment_key character varying)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
AS $function$
-- =========================================================
-- Scopo: l'uid del documento da cui viene una riga di commessa,
--   letto dalla chiave (<sorgente>:<uid>...); NULL se la chiave
--   non ne ha uno in forma canonica (righe a mano MAN:...).
-- Nessun SET: si espande in linea.
-- =========================================================
SELECT substring(p_segment_key
       FROM '^[^:#]+:([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:[:#]|$)');
$function$

COMMENT ON FUNCTION script.fn_segment_key_uid(p_segment_key character varying)
IS 'L''uid del documento da cui viene una riga di commessa, letto dalla chiave del push (<sorgente>:<uid>[:R:<riga>][:A:<articolo>][:M:<mese>][#...]): il secondo campo, se e'' un uuid in forma canonica; NULL altrimenti (le righe a mano MAN:<commessa>:<n>, una chiave fuori grammatica). La chiave la costruisce solo script.fn_segment_key, con l''uid del documento anche per i tipi a chiave id; le sorelle script.fn_segment_key_sorgente e script.fn_segment_key_riga ne leggono il codice e la riga. La usa vendite.fn_documento_uid_di_attivita, da cui la chiave del gruppo fatturabile. LANGUAGE sql IMMUTABLE senza SET: si espande in linea.';
```

</div>

---
{% include-markdown "signature-core.md" %}
