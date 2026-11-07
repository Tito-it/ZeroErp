# ⚙️ Funzione `fn_documento_uid_di_attivita`

```sql
CREATE FUNCTION fn_documento_uid_di_attivita(p_sorgente_tipo_id bigint, p_segment_key character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_documento_uid_di_attivita(p_sorgente_tipo_id bigint, p_segment_key character varying)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
AS $function$
-- =========================================================
-- Scopo: l'uid del documento da cui nasce una riga di commessa,
--   per qualunque tipo, dalla chiave del push (D-6). Senza tipo
--   NULL: una rettifica porta nella chiave l'uid del documento che
--   rettifica, ma non ne nasce.
-- Nessun SET: si espande in linea.
-- =========================================================
SELECT CASE WHEN p_sorgente_tipo_id IS NOT NULL
            THEN script.fn_segment_key_uid(p_segment_key) END;
$function$

COMMENT ON FUNCTION vendite.fn_documento_uid_di_attivita(p_sorgente_tipo_id bigint, p_segment_key character varying)
IS 'L''uid del documento da cui nasce una riga di commessa (vendite.commesse_attivita), in testo, per qualunque tipo: dalla chiave del push (script.fn_segment_key_uid), che lo porta anche per i tipi a chiave id, dove la riga tiene l''id in sorgente_id. NULL per una riga senza tipo (ONERE manuale, RETTIFICA: la rettifica porta nella chiave l''uid del documento che rettifica, ma non ne nasce). E'' l''uid della chiave del gruppo fatturabile (vendite.fn_gruppo_fatturabile_key_di_attivita) e della colonna sorgente_uid di vendite.vw_dash_competenza_attivita. Che la chiave nomini proprio il documento della provenienza lo verifica trg_commesse_attivita_a10_guard_sorgente_segment_ins_upd. LANGUAGE sql IMMUTABLE senza SET: si espande in linea.';
```

</div>

---
{% include-markdown "signature-core.md" %}
