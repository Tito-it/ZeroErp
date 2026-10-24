# ⚙️ Funzione `fn_sorgente_tabella`

```sql
CREATE FUNCTION fn_sorgente_tabella(p_codice_interno character varying)
```

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
--   e oid della sua target_table, letti dal catalogo di
--   PostgreSQL (pg_class, pg_namespace).
-- Parametri: p_codice_interno, il codice della sorgente.
-- Ritorna: una riga, oppure NESSUNA se la sorgente non c'e' o
--   non dichiara una tabella (target_table e' nullable). Il
--   chiamante decide che cosa vuol dire.
-- ⭐ Perche' esiste (regola del 2): dal 2026-10-21 la famiglia
--   di numerazione e' una sorgente (G-5) e non porta piu'
--   schema_tabella/nome_tabella. Guard, check, la storia
--   dell'emittente del BA e la lista delle famiglie
--   compongono SQL dinamico su quella tabella: la risoluzione
--   sta qui, una volta.
-- ⛔ Mai target_table::text: un regclass si stampa SENZA
--   schema quando lo schema e' nel search_path di chi legge, e
--   un format('%I') su quel testo nomina la tabella sbagliata
--   o nessuna. Schema e nome si leggono da pg_class.
-- Brief: brief-db-grammatica-unica-documenti §10.4 (2c, G-5).
-- =========================================================
SELECT n.nspname, c.relname, c.oid
  FROM config.sorgenti s
  JOIN pg_catalog.pg_class c     ON c.oid = s.target_table
  JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
 WHERE s.codice_interno = p_codice_interno;
$function$

COMMENT ON FUNCTION config.fn_sorgente_tabella(p_codice_interno character varying)
IS 'Dove vive il documento di una sorgente: schema, nome e oid della sua target_table, letti da pg_class/pg_namespace (mai target_table::text, che dipende dal search_path di chi legge). Nessuna riga se la sorgente non c''e'' o non dichiara una tabella. BB della regola del 2 (2026-10-21): la famiglia di numerazione e'' una sorgente (G-5) e non porta piu'' schema_tabella/nome_tabella; la leggono il guard dei riferimenti e la check di spegnimento delle famiglie, la storia dell''emittente del BA e la lista delle famiglie. INVOKER, STABLE. Brief: brief-db-grammatica-unica-documenti §10.4.';
```

</div>

---
{% include-markdown "signature-core.md" %}
