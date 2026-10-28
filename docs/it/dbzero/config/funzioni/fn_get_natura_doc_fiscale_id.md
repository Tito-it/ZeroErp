{% include-markdown "it/dbzero/config/manual/fn_get_natura_doc_fiscale_id.md" %}
# ⚙️ Funzione `fn_get_natura_doc_fiscale_id`

```sql
CREATE FUNCTION fn_get_natura_doc_fiscale_id(p_codice_interno character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_get_natura_doc_fiscale_id(p_codice_interno character varying)
 RETURNS bigint
 LANGUAGE sql
 STABLE
AS $function$
-- Scopo: id della natura documento dalla sua chiave naturale
--   stabile. NULL se il codice non esiste o e' disattivato: e'
--   un fn_get_*, legge e risponde, non e' una sentinella.
SELECT n.id
  FROM config.nature_doc_fiscale n
 WHERE n.codice_interno = p_codice_interno
   AND n.attivo IS TRUE;
$function$

COMMENT ON FUNCTION config.fn_get_natura_doc_fiscale_id(p_codice_interno character varying)
IS 'Id della natura fiscale del documento dalla chiave naturale stabile (codice_interno, immutabile per lock). Nasce per il DEFAULT delle colonne natura_doc_id: un DEFAULT non ammette sottoquery e un id cablato violerebbe linee-guida-sql S6b (l''id e'' dettaglio implementativo, la chiave naturale e'' il contratto). STABLE e senza raise, deliberatamente: una VOLATILE dentro il DEFAULT di un ADD COLUMN toglierebbe a PostgreSQL il fast-default e riscriverebbe l''intera tabella; e il NULL diventa comunque un errore, sul NOT NULL della colonna, cioe'' esattamente sulla scrittura rimasta senza natura. brief-design-note-credito-resi N1. rev 2026-08-18.';
```

</div>

---
{% include-markdown "signature-core.md" %}
