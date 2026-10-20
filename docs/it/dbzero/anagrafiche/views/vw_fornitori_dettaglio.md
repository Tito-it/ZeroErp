{% include-markdown "it/dbzero/anagrafiche/manual/vw_fornitori_dettaglio.md" %}
# 🔍 View `vw_fornitori_dettaglio`

> 📝 **Descrizione**
>
> Dettaglio fornitore con soggetto, stato, valuta, modalita' e termine pagamento. Include id_fiscale_univoco_cf_piva per lista configurabile DEF-8. stato_codice_interno = codice_interno (logica), stato_codice = codice (display).

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
    f.giorni_pagamento,
    f.fine_mese,
    f.split_payment,
    f.ritenuta_acconto,
    f.ritenuta_aliquota,
    f.regime_fiscale,
    f.bollo_esente,
    f.canale_fe,
    f.pec_email,
    f.rating,
    f.qualifica_scadenza,
    f.data_insert,
    f.data_update,
    s.id_fiscale_univoco_cf_piva
   FROM ((((((anagrafiche.fornitori f
     JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = f.soggetto_ruolo_id)))
     JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
     LEFT JOIN config.stati_fornitore sf ON ((sf.id = f.stato_fornitore_id)))
     LEFT JOIN config.valute v ON ((v.id = f.valuta_id)))
     LEFT JOIN config.modalita_pagamento mp ON ((mp.id = f.modalita_pagamento_id)))
     LEFT JOIN config.termini_pagamento tp ON ((tp.id = f.termine_pagamento_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
