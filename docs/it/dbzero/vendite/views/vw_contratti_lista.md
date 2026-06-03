# 🔍 View `vw_contratti_lista`

```sql
CREATE OR REPLACE VIEW vendite.vw_contratti_lista AS
SELECT c.id,
    c.uid,
    c.numero,
    c.billing_account_id,
    ba.codice AS ba_codice,
    s.id AS soggetto_id,
    s.ragione_sociale_completa,
    s.id_fiscale_univoco_cf_piva,
    c.emittente_fiscale_id,
    ef.codice AS emittente_fiscale_codice,
    c.utility_id,
    u.codice AS utility_codice,
    u.descrizione AS utility_descrizione,
    c.ambito,
    c.data,
    c.valido_dal,
    c.valido_al,
    c.stato_doc_contratto_id,
    sd.codice_interno AS stato_codice,
    sd.descrizione AS stato_descrizione,
    c.listino_id,
    l.codice AS listino_codice,
    l.descrizione AS listino_descrizione,
    c.listino_versione_id,
    lv.codice_versione AS listino_versione_codice,
    c.tipo_variazione_globale,
    c.valore_variazione_globale,
    c.categoria_cliente_id_snapshot,
    cc_snap.codice AS categoria_cliente_snapshot_codice,
    cc_snap.descrizione AS categoria_cliente_snapshot_descrizione,
    c.valuta_id,
    v_val.codice AS valuta_codice,
    v_val.descrizione AS valuta_descrizione,
    c.data_insert,
    c.user_insert,
    c.data_update,
    c.user_update
   FROM ((((((((((vendite.contratti c
     JOIN anagrafiche.billing_account ba ON ((ba.id = c.billing_account_id)))
     JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = ba.soggetto_ruolo_id)))
     JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
     JOIN config.utilities u ON ((u.id = c.utility_id)))
     JOIN config.stati_doc_contratti sd ON ((sd.id = c.stato_doc_contratto_id)))
     LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.id = c.emittente_fiscale_id)))
     LEFT JOIN vendite.listini l ON ((l.id = c.listino_id)))
     LEFT JOIN vendite.listini_versioni lv ON ((lv.id = c.listino_versione_id)))
     LEFT JOIN anagrafiche.categorie_clienti cc_snap ON ((cc_snap.id = c.categoria_cliente_id_snapshot)))
     LEFT JOIN config.valute v_val ON ((v_val.id = c.valuta_id)));
```


---
{% include-markdown "signature-core.md" %}
