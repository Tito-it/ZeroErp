{% include-markdown "it/dbzero/maintenance/manual/vw_statistiche_mancanti.md" %}
# 🔍 View `vw_statistiche_mancanti`

> 📝 **Descrizione**
>
> Le tabelle che dopo un ANALYZE resterebbero senza statistiche per il ruolo CORRENTE. motivo: MAI_ANALIZZATA (pg_class.reltuples &lt; 0: mai un ANALYZE ne' un VACUUM; sta nel catalogo e sopravvive a un crash, i contatori di pg_stat_* no) oppure NON_ANALIZZABILE (niente MAINTAIN: ANALYZE la salterebbe con un WARNING, senza fallire). Perimetro per struttura: tabelle ordinarie e partizionate, esclusi gli schemi di sistema, le temporanee di altre sessioni e gli oggetti di un'estensione (pg_depend deptype e); esclusa anche la partizionata senza partizioni, che non ha dati da descrivere e resta a -1 dopo ANALYZE. ⚠️ Risponde per chi interroga: come zeroerp_app ogni tabella di progetto e' NON_ANALIZZABILE, ed e' giusto. La legge l'autoverifica di maintenance.fn_analyze_statistiche. Brief: brief-db-statistiche-tabelle-job-notturno (D15).

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW maintenance.vw_statistiche_mancanti AS
SELECT (c.oid)::regclass AS relid,
    (n.nspname)::text AS schema_nome,
    (c.relname)::text AS tabella_nome,
    (c.relkind)::text AS relkind,
        CASE
            WHEN (NOT has_table_privilege(c.oid, 'MAINTAIN'::text)) THEN 'NON_ANALIZZABILE'::text
            ELSE 'MAI_ANALIZZATA'::text
        END AS motivo
   FROM (pg_class c
     JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
  WHERE ((c.relkind = ANY (ARRAY['r'::"char", 'p'::"char"])) AND (n.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])) AND (n.nspname !~~ 'pg\_toast%'::text) AND ((c.relpersistence <> 't'::"char") OR (c.relnamespace = pg_my_temp_schema())) AND (NOT (EXISTS ( SELECT 1
           FROM pg_depend d
          WHERE ((d.classid = ('pg_class'::regclass)::oid) AND (d.objid = c.oid) AND (d.refclassid = ('pg_extension'::regclass)::oid) AND (d.deptype = 'e'::"char"))))) AND ((NOT has_table_privilege(c.oid, 'MAINTAIN'::text)) OR ((c.reltuples < (0)::double precision) AND (NOT ((c.relkind = 'p'::"char") AND (NOT (EXISTS ( SELECT 1
           FROM pg_inherits i
          WHERE (i.inhparent = c.oid)))))))));
```

</div>


---
{% include-markdown "signature-core.md" %}
