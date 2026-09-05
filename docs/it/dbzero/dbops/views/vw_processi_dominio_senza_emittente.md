{% include-markdown "it/dbzero/dbops/manual/vw_processi_dominio_senza_emittente.md" %}
# 🔍 View `vw_processi_dominio_senza_emittente`

```sql
CREATE OR REPLACE VIEW dbops.vw_processi_dominio_senza_emittente AS
WITH dominio AS (
         SELECT p.id,
            p.codice,
            p.canale
           FROM dbops.processi p
          WHERE ((p.classe = 'DOMINIO'::text) AND p.attivo AND (p.obsoleto_dal IS NULL))
        )
 SELECT d.codice AS processo_codice,
    d.canale,
    NULL::text AS schema_tabella,
    NULL::text AS nome_tabella,
    NULL::text AS emittente_via,
    NULL::text AS emittente_colonna,
    'nessun bersaglio dichiarato'::text AS motivo,
    'NON_DICHIARATO'::text AS stato,
    NULL::text AS nota
   FROM dominio d
  WHERE (NOT (EXISTS ( SELECT 1
           FROM dbops.processi_bersagli b
          WHERE (b.processo_id = d.id))))
UNION ALL
 SELECT d.codice AS processo_codice,
    d.canale,
    b.schema_tabella,
    b.nome_tabella,
    b.emittente_via,
    b.emittente_colonna,
        CASE
            WHEN (NOT (EXISTS ( SELECT 1
               FROM (pg_class c
                 JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
              WHERE ((n.nspname = b.schema_tabella) AND (c.relname = b.nome_tabella) AND (c.relkind = ANY (ARRAY['r'::"char", 'p'::"char"])))))) THEN 'tabella inesistente'::text
            WHEN (b.emittente_via IS NULL) THEN 'percorso verso l''emittente non dichiarato'::text
            ELSE 'colonna del percorso inesistente'::text
        END AS motivo,
        CASE
            WHEN b.debito_dichiarato THEN 'DEBITO_DICHIARATO'::text
            ELSE 'NON_DICHIARATO'::text
        END AS stato,
    b.note AS nota
   FROM (dominio d
     JOIN dbops.processi_bersagli b ON ((b.processo_id = d.id)))
  WHERE ((NOT (EXISTS ( SELECT 1
           FROM (pg_class c
             JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
          WHERE ((n.nspname = b.schema_tabella) AND (c.relname = b.nome_tabella) AND (c.relkind = ANY (ARRAY['r'::"char", 'p'::"char"])))))) OR (b.emittente_via IS NULL) OR (NOT (EXISTS ( SELECT 1
           FROM ((pg_attribute a
             JOIN pg_class c ON ((c.oid = a.attrelid)))
             JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
          WHERE ((n.nspname = b.schema_tabella) AND (c.relname = b.nome_tabella) AND (a.attname = b.emittente_colonna) AND (a.attnum > 0) AND (NOT a.attisdropped))))));
```


---
{% include-markdown "signature-core.md" %}
