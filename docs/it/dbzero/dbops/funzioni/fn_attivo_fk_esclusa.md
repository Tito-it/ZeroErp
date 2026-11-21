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
             WHEN (lower(p_colonna_fk) ~~ '%_id'::text) THEN NULL::text
             WHEN (EXISTS ( SELECT 1
                FROM dbops.automazione_attivo_inclusioni i
               WHERE ((i.schema_figlia = fn_attivo_fk_esclusa.p_schema_figlia) AND (i.tabella_figlia = fn_attivo_fk_esclusa.p_tabella_figlia) AND (i.colonna_fk = fn_attivo_fk_esclusa.p_colonna_fk)))) THEN NULL::text
             ELSE 'FK_NO_ID_SUFFIX'::text
         END AS "case";
END

COMMENT ON FUNCTION dbops.fn_attivo_fk_esclusa(p_schema_figlia text, p_tabella_figlia text, p_colonna_fk text)
IS 'Se una FK resta fuori dall''automazione ATTIVO, e perche'': NULL se si lega, altrimenti il motivo. ECCEZIONE_DICHIARATA: la FK e'' in dbops.automazione_attivo_eccezioni, e l''eccezione prevale anche su un''inclusione. FK_NO_ID_SUFFIX: la colonna non finisce in _id (LIKE ''%_id'', col ''_'' jolly) e non e'' in dbops.automazione_attivo_inclusioni. La FK si nomina dalla FIGLIA: schema, tabella, colonna. Non guarda il padre: il padre senza la colonna attivo e le FK multicolonna li filtra dbops.fn_run_automations_attivo. La leggono il runner, che non genera le FK escluse, e dbops.fn_ritira_attivo_eccezioni, che ne toglie i trigger gia'' generati: una sede sola per la domanda «questa FK si lega?».';
```

</div>

---
{% include-markdown "signature-core.md" %}
