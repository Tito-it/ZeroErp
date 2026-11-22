{% include-markdown "it/dbzero/dbops/manual/fn_attivo_fk_esclusa.md" %}
# ⚙️ Funzione `fn_attivo_fk_esclusa`

```sql
CREATE FUNCTION fn_attivo_fk_esclusa(p_schema_figlia text, p_tabella_figlia text, p_colonna_fk text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_attivo_fk_esclusa(p_schema_figlia text, p_tabella_figlia text, p_colonna_fk text)
 RETURNS text
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT
         CASE
             WHEN (EXISTS ( SELECT 1
                FROM dbops.automazione_attivo_eccezioni e
               WHERE ((e.schema_figlia = fn_attivo_fk_esclusa.p_schema_figlia) AND (e.tabella_figlia = fn_attivo_fk_esclusa.p_tabella_figlia) AND (e.colonna_fk = fn_attivo_fk_esclusa.p_colonna_fk)))) THEN 'ECCEZIONE_DICHIARATA'::text
             WHEN ((EXISTS ( SELECT 1
                FROM (((pg_constraint k
                  JOIN pg_class r ON ((r.oid = k.conrelid)))
                  JOIN pg_namespace n ON ((n.oid = r.relnamespace)))
                  JOIN pg_attribute a ON (((a.attrelid = k.conrelid) AND (a.attnum = k.conkey[1]))))
               WHERE ((k.contype = 'f'::"char") AND (cardinality(k.conkey) = 1) AND (k.conparentid <> (0)::oid) AND (n.nspname = fn_attivo_fk_esclusa.p_schema_figlia) AND (r.relname = fn_attivo_fk_esclusa.p_tabella_figlia) AND (a.attname = fn_attivo_fk_esclusa.p_colonna_fk)))) AND (NOT (EXISTS ( SELECT 1
                FROM (((pg_constraint k
                  JOIN pg_class r ON ((r.oid = k.conrelid)))
                  JOIN pg_namespace n ON ((n.oid = r.relnamespace)))
                  JOIN pg_attribute a ON (((a.attrelid = k.conrelid) AND (a.attnum = k.conkey[1]))))
               WHERE ((k.contype = 'f'::"char") AND (cardinality(k.conkey) = 1) AND (k.conparentid = (0)::oid) AND (n.nspname = fn_attivo_fk_esclusa.p_schema_figlia) AND (r.relname = fn_attivo_fk_esclusa.p_tabella_figlia) AND (a.attname = fn_attivo_fk_esclusa.p_colonna_fk)))))) THEN 'FK_EREDITATA'::text
             ELSE NULL::text
         END AS "case";
END

COMMENT ON FUNCTION dbops.fn_attivo_fk_esclusa(p_schema_figlia text, p_tabella_figlia text, p_colonna_fk text)
IS 'Se una FK resta fuori dall''automazione ATTIVO, e perche'': NULL se si lega, altrimenti il motivo. ECCEZIONE_DICHIARATA: la FK e'' in dbops.automazione_attivo_eccezioni. FK_EREDITATA: sulla figlia la colonna ha solo FK monocolonna ereditate da una radice partizionata (conparentid diverso da zero), e la FK si lega o si esclude sulla radice: il require della radice PostgreSQL lo clona sulle partizioni, e un''eccezione sulla radice vale per tutte. Il nome della colonna non decide niente: una FK con o senza il suffisso _id si lega allo stesso modo. La FK si nomina dalla FIGLIA: schema, tabella, colonna. Non guarda il padre: il padre senza la colonna attivo e le FK multicolonna li filtra dbops.fn_run_automations_attivo. La leggono il runner, che non genera le FK escluse, e dbops.fn_ritira_attivo_eccezioni, che ne toglie i trigger gia'' generati: una sede sola per la domanda «questa FK si lega?».';
```

</div>

---
{% include-markdown "signature-core.md" %}
