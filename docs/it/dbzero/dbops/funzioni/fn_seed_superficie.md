{% include-markdown "it/dbzero/dbops/manual/fn_seed_superficie.md" %}
# ⚙️ Funzione `fn_seed_superficie`

```sql
CREATE FUNCTION fn_seed_superficie(p_tabella regclass, p_riga_id text, p_colonne_del_software text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_seed_superficie(p_tabella regclass, p_riga_id text, p_colonne_del_software text[])
 RETURNS TABLE(nata_dal_seed boolean, campi_del_software text[])
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT s.nata,
         CASE
             WHEN s.nata THEN COALESCE(fn_seed_superficie.p_colonne_del_software, ARRAY[]::text[])
             ELSE ARRAY[]::text[]
         END AS "array"
    FROM ( SELECT (EXISTS ( SELECT 1
                    FROM dbops.fn_seed_riga(fn_seed_superficie.p_tabella, fn_seed_superficie.p_riga_id) fn_seed_riga(seed_riga_id, schema_name, table_name, personalizzata_il))) AS nata) s;
END

COMMENT ON FUNCTION dbops.fn_seed_superficie(p_tabella regclass, p_riga_id text, p_colonne_del_software text[])
IS 'Il segno del seed di primo impianto su una riga, per le superfici che lo mostrano (liste e dettagli): nata_dal_seed dice se la riga p_riga_id (la chiave primaria id, come testo) della tabella p_tabella l''ha installata il software (dbops.fn_seed_riga); campi_del_software sono, su una riga nata dal seed, le colonne che l''installazione non modifica, quelle su cui il guard script.trgfn_seed_primo_impianto alza E_SEED_COLONNA_DEL_SOFTWARE; vuoto, mai NULL, su una riga dell''installazione o quando la forma della tabella non ne ha. Le colonne non dipendono dalla riga: il chiamante le legge una volta per tabella con dbops.fn_seed_colonne_del_software, in una sottoquery non correlata, e le passa in p_colonne_del_software (linee-guida-sql §13.2). Una riga sola. La leggono config.vw_email_account_seed, config.vw_email_template_seed e le liste admin di ui. SECURITY INVOKER, STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
