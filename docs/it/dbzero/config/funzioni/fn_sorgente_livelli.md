# ⚙️ Funzione `fn_sorgente_livelli`

```sql
CREATE FUNCTION fn_sorgente_livelli(p_sorgente_tipo_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_sorgente_livelli(p_sorgente_tipo_id bigint)
 RETURNS TABLE(codice_interno character varying, attivo boolean, key_selector text, label_selector character varying, documento_relid oid, documento_schema name, documento_tabella name, documento_ha_uid boolean, documento_ha_label boolean, righe_relid oid, righe_schema name, righe_tabella name, righe_fk_column character varying, dettaglio_relid oid, dettaglio_schema name, dettaglio_tabella name, dettaglio_fk_column character varying)
 LANGUAGE sql
 STABLE ROWS 1
 SET search_path TO 'pg_catalog', 'pg_temp'
BEGIN ATOMIC
 SELECT s.codice_interno,
     s.attivo,
     s.key_selector,
     s.label_selector,
     dc.oid,
     dn.nspname,
     dc.relname,
     (EXISTS ( SELECT 1
            FROM pg_attribute a
           WHERE ((a.attrelid = dc.oid) AND (a.attname = 'uid'::name) AND (a.attnum > 0) AND (NOT a.attisdropped)))) AS "exists",
     (EXISTS ( SELECT 1
            FROM pg_attribute a
           WHERE ((a.attrelid = dc.oid) AND (a.attname = (s.label_selector)::name) AND (a.attnum > 0) AND (NOT a.attisdropped)))) AS "exists",
     rc.oid,
     rn.nspname,
     rc.relname,
     s.righe_fk_column,
     tc.oid,
     tn.nspname,
     tc.relname,
     s.dettaglio_fk_column
    FROM ((((((config.sorgenti s
      LEFT JOIN pg_class dc ON ((dc.oid = (s.target_table)::oid)))
      LEFT JOIN pg_namespace dn ON ((dn.oid = dc.relnamespace)))
      LEFT JOIN pg_class rc ON ((rc.oid = (s.righe_table)::oid)))
      LEFT JOIN pg_namespace rn ON ((rn.oid = rc.relnamespace)))
      LEFT JOIN pg_class tc ON ((tc.oid = (s.dettaglio_table)::oid)))
      LEFT JOIN pg_namespace tn ON ((tn.oid = tc.relnamespace)))
   WHERE (s.id = fn_sorgente_livelli.p_sorgente_tipo_id);
END

COMMENT ON FUNCTION config.fn_sorgente_livelli(p_sorgente_tipo_id bigint)
IS 'Dove vivono il documento di un tipo di sorgente, le sue righe e il loro dettaglio: schema, nome e oid delle tabelle che config.sorgenti dichiara (target_table, righe_table, dettaglio_table), letti da pg_class e pg_namespace, con le colonne FK di righe e dettaglio. Dice anche se la tabella del documento ha la colonna uid e se la colonna di label_selector esiste. Una riga per il tipo, con i livelli assenti a NULL; nessuna riga se il tipo non esiste. Non filtra su attivo: lo restituisce. La leggono il guard della provenienza, il BB che risolve, il presidio degli orfani e config.fn_sorgente_tabella. INVOKER, STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
