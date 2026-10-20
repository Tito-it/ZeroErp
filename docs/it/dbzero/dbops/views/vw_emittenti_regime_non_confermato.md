{% include-markdown "it/dbzero/dbops/manual/vw_emittenti_regime_non_confermato.md" %}
# 🔍 View `vw_emittenti_regime_non_confermato`

> 📝 **Descrizione**
>
> Gli emittenti fiscali attivi il cui regime fiscale nessuno ha confermato (regime_fiscale_confermato_il NULL): il regime e' quello del default RF01 (D-1) o di un cambio senza conferma. DEVE restare VUOTA. ⛔ Copre un guasto che non assomiglia a un errore: un emittente in IVA per cassa lasciato a RF01 emette tutte le fatture a esigibilita' immediata. Tutti i regimi e non solo RF01: un regime non confermato e' un regime che nessuno ha dichiarato, qualunque codice abbia. Si svuota confermando il regime dal form dell'emittente. Brief: brief-db-esigibilita-iva-per-cassa-emittente (D-1, D-11).

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_emittenti_regime_non_confermato AS
SELECT id AS emittente_fiscale_id,
    codice AS emittente_codice,
    regime_fiscale_rf
   FROM anagrafiche.emittenti_fiscali ef
  WHERE ((attivo IS TRUE) AND (regime_fiscale_confermato_il IS NULL));
```

</div>


---
{% include-markdown "signature-core.md" %}
