{% include-markdown "it/dbzero/dbops/manual/fn_seed_colonne_del_software.md" %}
# ⚙️ Funzione `fn_seed_colonne_del_software`

```sql
CREATE FUNCTION fn_seed_colonne_del_software(p_tabella regclass)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_seed_colonne_del_software(p_tabella regclass)
 RETURNS text[]
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT COALESCE(( SELECT a.colonne_software
            FROM (pg_trigger tg
              CROSS JOIN LATERAL dbops.fn_seed_primo_impianto_argomenti(dbops.fn_trigger_argomenti(tg.tgargs)) a(valido, dettaglio, forma, colonne_software, colonne_installazione, colonne_libere))
           WHERE ((tg.tgrelid = (fn_seed_colonne_del_software.p_tabella)::oid) AND (tg.tgfoid = ('script.trgfn_seed_primo_impianto()'::regprocedure)::oid) AND (NOT tg.tgisinternal) AND (tg.tgenabled <> 'D'::"char") AND a.valido)
           ORDER BY tg.tgname
          LIMIT 1), ARRAY[]::text[]) AS "coalesce";
END

COMMENT ON FUNCTION dbops.fn_seed_colonne_del_software(p_tabella regclass)
IS 'Le colonne del software della tabella p_tabella: quelle che su una riga nata dal seed l''installazione non modifica (il guard script.trgfn_seed_primo_impianto alza E_SEED_COLONNA_DEL_SOFTWARE). Si leggono dagli argomenti del trigger montato, con la stessa grammatica del guard (dbops.fn_seed_primo_impianto_argomenti): il campo spento e il rifiuto vengono dalla stessa sorgente. Vuoto, mai NULL, per una tabella senza il trigger o col trigger spento, per le forme RIGA e SOLO_INSERIMENTO e per un montaggio fuori grammatica. Vale per la tabella, non per la riga: su una riga dell''installazione nessuna colonna e'' del software (lo dice dbops.fn_seed_riga). La leggono le superfici config.vw_email_account_seed e config.vw_email_template_seed. SECURITY INVOKER, STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
