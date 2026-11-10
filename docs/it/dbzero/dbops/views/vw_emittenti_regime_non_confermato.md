{% include-markdown "it/dbzero/dbops/manual/vw_emittenti_regime_non_confermato.md" %}
# 🔍 View `vw_emittenti_regime_non_confermato`

> 📝 **Descrizione**
>
> Gli emittenti fiscali attivi il cui regime fiscale nessuno ha mai dichiarato (regime_fiscale_confermato_il NULL): il regime e' quello scritto alla creazione, o il default RF01. Ogni UPDATE che nomina regime_fiscale_rf lo conferma (anagrafiche.trgfn_emittenti_fiscali_regime_conferma), quindi un cambio di regime non lascia mai la riga qui. DEVE restare VUOTA. Copre un guasto che non assomiglia a un errore: un emittente in IVA per cassa lasciato a RF01 emette tutte le fatture a esigibilita' immediata. Tutti i regimi e non solo RF01: un regime non confermato e' un regime che nessuno ha dichiarato, qualunque codice abbia. Si svuota confermando il regime dal form dell'emittente.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

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
