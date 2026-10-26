{% include-markdown "it/dbzero/dbops/manual/fn_dati_di_sviluppo_ammessi_su_valori.md" %}
# ⚙️ Funzione `fn_dati_di_sviluppo_ammessi_su_valori`

```sql
CREATE FUNCTION fn_dati_di_sviluppo_ammessi_su_valori(p_ambiente text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_dati_di_sviluppo_ammessi_su_valori(p_ambiente text)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- I dati di sviluppo nascono solo in SVILUPPO; NULL resta NULL.
    SELECT p_ambiente = 'SVILUPPO'
$function$

COMMENT ON FUNCTION dbops.fn_dati_di_sviluppo_ammessi_su_valori(p_ambiente text)
IS 'La regola, pura sul valore (IMMUTABLE, sql): i dati di sviluppo (le etichette di prova, il verbo anagrafiche.fn_provisiona_dati_di_sviluppo) sono ammessi solo se l''ambiente e'' SVILUPPO. NULL resta NULL: l''ambiente mancante lo dice il lettore script.fn_ambiente_installazione (E_CONFIG_MANCANTE). La leggono il guard dbops.trgfn_etichette_di_prova_guard e il verbo, passando l''ambiente vero; i pgTAP la chiamano coi due valori (la CI e'' SVILUPPO e l''ambiente non cambia). Brief: brief-db-processi-accensione-per-ambiente (R-4, §5.5).';
```

</div>

---
{% include-markdown "signature-core.md" %}
