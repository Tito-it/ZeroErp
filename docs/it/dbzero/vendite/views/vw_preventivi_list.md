{% include-markdown "it/dbzero/vendite/manual/vw_preventivi_list.md" %}
# 🔍 View `vw_preventivi_list`

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_list AS
SELECT p.id,
    p.uid,
    p.numero,
    p.rev,
    p.is_revision_attiva,
    p.data,
    p.stato_doc_preventivo_id,
    sdp.codice AS stato_codice,
    sdp.codice_interno AS stato_codice_interno,
    sdp.descrizione AS stato_descrizione,
    p.billing_account_id,
    ba.codice AS billing_account_codice,
    ba.utility_id AS ba_utility_id,
    s.id AS soggetto_id,
    s.ragione_sociale_completa AS cliente_denominazione,
    s.id_fiscale_univoco_cf_piva AS id_fiscale,
    p.emittente_fiscale_id,
    p.utility_id,
    u.codice AS utility_codice,
    u.descrizione AS utility_descrizione,
    p.istanza_utility_id,
    iu.codice AS istanza_utility_codice,
    p.totale_imponibile,
    p.totale_iva,
    p.totale_documento,
    p.valuta_id,
    v.codice AS valuta_codice,
    p.termine_pagamento_id,
    tp.descrizione AS termine_pagamento_descrizione,
    p.validita_dal,
    p.validita_al,
    p.competenza_mese,
    p.fatturazione_immediata,
    p.storicizza,
    p.data_insert
   FROM (((((((vendite.preventivi p
     JOIN config.stati_doc_preventivi sdp ON ((sdp.id = p.stato_doc_preventivo_id)))
     LEFT JOIN anagrafiche.istanze_utilities iu ON ((iu.id = p.istanza_utility_id)))
     LEFT JOIN anagrafiche.soggetti s ON ((s.id = iu.soggetto_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = p.billing_account_id)))
     LEFT JOIN config.utilities u ON ((u.id = p.utility_id)))
     LEFT JOIN config.valute v ON ((v.id = p.valuta_id)))
     LEFT JOIN config.termini_pagamento tp ON ((tp.id = p.termine_pagamento_id)))
  ORDER BY p.data DESC, p.numero DESC, p.id;
```


---
{% include-markdown "signature-core.md" %}
