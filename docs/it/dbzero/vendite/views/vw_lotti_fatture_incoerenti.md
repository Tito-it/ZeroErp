{% include-markdown "it/dbzero/vendite/manual/vw_lotti_fatture_incoerenti.md" %}
# 🔍 View `vw_lotti_fatture_incoerenti`

> 📝 **Descrizione**
>
> Vista di lavoro e SEDE UNICA dell'invariante lotto &lt;-&gt; fatture: una riga per fattura il cui stato fiscale diverge da quello del lotto che la contiene. Eccezione: la fattura in errore (critical) rimasta indietro; ⛔ non quella gia' congelata e non abortita davanti a un lotto non congelato (R-1 di Tid, 2026-10-24: un documento definitivo non convive con uno in errore nello stesso lotto). La legge il guard vendite.fn_guard_lotto_fatture_stato_coerente. security_invoker: vede cio' che vede chi interroga. rev 2026-10-24 (20261024-34): predicato R-1 e colonna fattura_critical in coda.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_lotti_fatture_incoerenti
WITH (security_invoker=on) AS
SELECT l.id AS lotto_id,
    l.codice AS lotto_codice,
    l.tipo_lotto,
    l.stato_operativo,
    l.stato_doc_fiscale_id AS stato_lotto_id,
    sl.codice_interno AS stato_lotto_codice_interno,
    sl.codice AS stato_lotto_codice,
    f.id AS fattura_id,
    f.anno AS fattura_anno,
    f.serie AS fattura_serie,
    f.numero AS fattura_numero,
    f.stato_doc_fiscale_id AS stato_fattura_id,
    sf.codice_interno AS stato_fattura_codice_interno,
    sf.codice AS stato_fattura_codice,
    l.data_update AS lotto_data_update,
    f.data_update AS fattura_data_update,
    COALESCE(f.critical, false) AS fattura_critical
   FROM ((((vendite.fatturazione_lotti l
     JOIN vendite.fatturazione_lotti_fatture lf ON ((lf.lotto_id = l.id)))
     JOIN vendite.fatture f ON ((f.id = lf.fattura_id)))
     LEFT JOIN config.stati_doc_fiscale sl ON ((sl.id = l.stato_doc_fiscale_id)))
     LEFT JOIN config.stati_doc_fiscale sf ON ((sf.id = f.stato_doc_fiscale_id)))
  WHERE ((f.stato_doc_fiscale_id IS DISTINCT FROM l.stato_doc_fiscale_id) AND ((COALESCE(f.critical, false) IS FALSE) OR ((COALESCE(sf.congela_fiscale, false) IS TRUE) AND (COALESCE(sf.is_abortito, false) IS FALSE) AND (COALESCE(sl.congela_fiscale, false) IS FALSE))));
```

</div>


---
{% include-markdown "signature-core.md" %}
