{% include-markdown "it/dbzero/anagrafiche/manual/vw_fornitori_dettaglio.md" %}
# 🔍 View `vw_fornitori_dettaglio`

> 📝 **Descrizione**
>
> Dettaglio fornitore con soggetto, stato, valuta, modalita' e termine di pagamento, ritenuta e regime fiscale (regime_fiscale_rf, il codice RF; regime_fiscale_descrizione da config.regimi_fiscali). Sorgente della lista configurabile anagrafiche.fornitori (id_fiscale_univoco_cf_piva). stato_codice_interno = codice_interno (logica), stato_codice = codice (display). Split payment e instradamento FE non stanno qui: sono del soggetto (anagrafiche.soggetti, anagrafiche.dati_societari).

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_fornitori_dettaglio AS
SELECT f.id,
    f.uid,
    f.codice,
    f.attivo,
    f.soggetto_ruolo_id,
    f.stato_fornitore_id,
    sf.codice_interno AS stato_codice_interno,
    sf.codice AS stato_codice,
    sf.descrizione AS stato_descrizione,
    sf.descrizione_breve AS stato_descrizione_breve,
    sf.blocca_ordini,
    s.id AS soggetto_id,
    s.ragione_sociale_completa,
    s.codice_fiscale,
    s.partita_iva,
    f.valuta_id,
    v.iso_code AS valuta_iso,
    f.modalita_pagamento_id,
    mp.codice AS modalita_pagamento_codice,
    mp.descrizione AS modalita_pagamento_desc,
    f.termine_pagamento_id,
    tp.codice AS termine_pagamento_codice,
    f.ritenuta_acconto,
    f.ritenuta_aliquota,
    f.regime_fiscale_rf,
    rf.descrizione AS regime_fiscale_descrizione,
    f.rating,
    f.qualifica_scadenza,
    f.data_insert,
    f.data_update,
    s.id_fiscale_univoco_cf_piva
   FROM (((((((anagrafiche.fornitori f
     JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = f.soggetto_ruolo_id)))
     JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
     LEFT JOIN config.stati_fornitore sf ON ((sf.id = f.stato_fornitore_id)))
     LEFT JOIN config.valute v ON ((v.id = f.valuta_id)))
     LEFT JOIN config.modalita_pagamento mp ON ((mp.id = f.modalita_pagamento_id)))
     LEFT JOIN config.termini_pagamento tp ON ((tp.id = f.termine_pagamento_id)))
     LEFT JOIN config.regimi_fiscali rf ON (((rf.codice_interno)::text = (f.regime_fiscale_rf)::text)));
```

</div>


---
{% include-markdown "signature-core.md" %}
