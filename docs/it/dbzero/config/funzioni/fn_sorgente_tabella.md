# ⚙️ Funzione `fn_sorgente_tabella`

```sql
CREATE FUNCTION fn_sorgente_tabella(p_codice_interno character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_sorgente_tabella(p_codice_interno character varying)
 RETURNS TABLE(schema_tabella name, nome_tabella name, relid oid)
 LANGUAGE sql
 STABLE
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
-- =========================================================
-- Scopo: dove vive il documento di una sorgente: schema, nome
--   e oid della sua target_table.
-- Parametri: p_codice_interno, il codice della sorgente.
-- Ritorna: una riga, oppure NESSUNA se la sorgente non c'e' o
--   non dichiara una tabella (target_table e' nullable). Il
--   chiamante decide che cosa vuol dire.
-- ⭐ La lettura del catalogo di PostgreSQL sta in
--   config.fn_sorgente_livelli (documento, righe, dettaglio):
--   qui se ne prende il solo documento.
-- =========================================================
SELECT l.documento_schema, l.documento_tabella, l.documento_relid
  FROM config.sorgenti s
  CROSS JOIN LATERAL config.fn_sorgente_livelli(s.id) l
 WHERE s.codice_interno = p_codice_interno
   AND l.documento_relid IS NOT NULL;
$function$

COMMENT ON FUNCTION config.fn_sorgente_tabella(p_codice_interno character varying)
IS 'Dove vive il documento di una sorgente: schema, nome e oid della sua target_table, letti da config.fn_sorgente_livelli (pg_class/pg_namespace, mai target_table::text, che dipende dal search_path di chi legge). Nessuna riga se la sorgente non c''e'' o non dichiara una tabella. La leggono il guard dei riferimenti e la check di spegnimento delle famiglie, la storia dell''emittente del BA e la lista delle famiglie. INVOKER, STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
