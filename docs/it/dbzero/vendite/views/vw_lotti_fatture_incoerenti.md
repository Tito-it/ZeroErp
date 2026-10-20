{% include-markdown "it/dbzero/vendite/manual/vw_lotti_fatture_incoerenti.md" %}
# 🔍 View `vw_lotti_fatture_incoerenti`

> 📝 **Descrizione**
>
> Elenco delle fatture il cui stato fiscale non coincide con quello del lotto che le contiene: e' la lista di lavoro dell'invariante presidiato da fn_guard_lotto_fatture_stato_coerente. rev 2026-08-04 (D-M): via il predicato su lf.esclusa, flag eliminato perche' dormiente; resta la sola eccezione critical. ⚠️ security_invoker=on: da ri-specificare in ogni CREATE OR REPLACE, non e' visibile in pg_get_viewdef.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

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
    f.data_update AS fattura_data_update
   FROM ((((vendite.fatturazione_lotti l
     JOIN vendite.fatturazione_lotti_fatture lf ON ((lf.lotto_id = l.id)))
     JOIN vendite.fatture f ON ((f.id = lf.fattura_id)))
     LEFT JOIN config.stati_doc_fiscale sl ON ((sl.id = l.stato_doc_fiscale_id)))
     LEFT JOIN config.stati_doc_fiscale sf ON ((sf.id = f.stato_doc_fiscale_id)))
  WHERE ((COALESCE(f.critical, false) IS FALSE) AND (f.stato_doc_fiscale_id IS DISTINCT FROM l.stato_doc_fiscale_id));
```

</div>


---
{% include-markdown "signature-core.md" %}
