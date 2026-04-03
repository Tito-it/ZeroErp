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
    sdp.descrizione AS stato_descrizione,
    p.billing_account_id,
    ba.utility_id AS ba_utility_id,
    s.id AS soggetto_id,
    s.ragione_sociale AS cliente_denominazione,
    anagrafiche.fn_get_emittente_fiscale_id(p.billing_account_id) AS emittente_fiscale_id,
    p.utility_id,
    p.istanza_utility_id,
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
   FROM ((((((vendite.preventivi p
     JOIN config.stati_doc_preventivi sdp ON ((sdp.id = p.stato_doc_preventivo_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = p.billing_account_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = ba.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
     LEFT JOIN config.valute v ON ((v.id = p.valuta_id)))
     LEFT JOIN config.termini_pagamento tp ON ((tp.id = p.termine_pagamento_id)))
  ORDER BY p.data DESC, p.numero DESC;
```


---
{% include-markdown "signature-core.md" %}
