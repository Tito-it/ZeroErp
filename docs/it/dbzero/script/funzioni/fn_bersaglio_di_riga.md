{% include-markdown "it/dbzero/script/manual/fn_bersaglio_di_riga.md" %}
# ⚙️ Funzione `fn_bersaglio_di_riga`

```sql
CREATE FUNCTION fn_bersaglio_di_riga(p_schema name, p_tabella name, p_colonna name, p_valore text)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_bersaglio_di_riga(p_schema name, p_tabella name, p_colonna name, p_valore text)
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
BEGIN ATOMIC
 SELECT
         CASE
             WHEN ((fn_bersaglio_di_riga.p_valore IS NOT NULL) AND (count(*) = 1)) THEN jsonb_build_array(jsonb_build_object('tipo', min(te.codice), 'id', fn_bersaglio_di_riga.p_valore))
             ELSE NULL::jsonb
         END AS "case"
    FROM (config.tipi_entita te
      LEFT JOIN config.sorgenti s ON (((s.codice_interno)::text = te.sorgente_codice_interno)))
   WHERE (
         CASE
             WHEN te.is_sorgente THEN (s.apribile AND ((s.target_table)::oid = (to_regclass(format('%I.%I'::text, fn_bersaglio_di_riga.p_schema, fn_bersaglio_di_riga.p_tabella)))::oid))
             ELSE ((to_regclass(te.tabella))::oid = (to_regclass(format('%I.%I'::text, fn_bersaglio_di_riga.p_schema, fn_bersaglio_di_riga.p_tabella)))::oid)
         END AND (te.key_selector = fn_bersaglio_di_riga.p_colonna) AND (NOT script.fn_e_obsoleto(te.obsoleto_dal)));
END

COMMENT ON FUNCTION script.fn_bersaglio_di_riga(p_schema name, p_tabella name, p_colonna name, p_valore text)
IS 'Building block: il bersaglio di un errore che riguarda una riga, nella forma del canale (un array con un oggetto tipo + id), o NULL. Il tipo lo dichiara il catalogo: config.tipi_entita.tabella per un tipo non sorgente; config.sorgenti.target_table, se la sorgente ha una pagina (apribile), per un tipo sorgente. Vale solo se la colonna e'' la chiave del tipo (key_selector) e il tipo non e'' ritirato; con nessun tipo, o con piu'' di uno, restituisce NULL. Lo chiamano i guard ATTIVO sul ramo del rifiuto (dbops.trgfn_child_requires_active_parent, dbops.trgfn_child_requires_non_obsolete_parent). SECURITY DEFINER, eseguibile da tutti come gli altri helper dei guard: il bersaglio non deve mai togliere il rifiuto a chi scrive. STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
