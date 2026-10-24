{% include-markdown "it/dbzero/anagrafiche/manual/vw_dati_societari.md" %}
# 🔍 View `vw_dati_societari`

> 📝 **Descrizione**
>
> Vista dati societari con decodifiche forma giuridica e provincia, include identificativi tecnici. destinatario_fe e' il canale FE (P = PEC, C = codice SDI), codice_sdi il codice (rev 20261010-38).

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_dati_societari AS
SELECT ds.id AS dati_societari_id,
    ds.soggetto_id,
    s.ragione_sociale_completa,
    s.id_fiscale_univoco_cf_piva,
    ds.forma_giuridica_id,
    fg.codice AS forma_giuridica_codice,
    fg.descrizione AS forma_giuridica_descrizione,
    ds.id_prov_iscri_rea AS provincia_iscrizione_rea_id,
    pr.sigla AS provincia_iscrizione_rea_sigla,
    pr.descrizione AS provincia_iscrizione_rea_descrizione,
    ds.iscrizione_rea,
    ds.capitale_sociale,
    ds.socio_unico,
    ds.liquidazione,
    ds.destinatario_fe,
    ds.pec_fatturazione,
    ds.codice_sdi,
    ds.data_costituzione,
    ds.storicizza,
    ds.tx_id,
    ds.data_insert,
    ds.user_insert,
    ds.data_update,
    ds.user_update
   FROM (((anagrafiche.dati_societari ds
     JOIN anagrafiche.soggetti s ON ((s.id = ds.soggetto_id)))
     LEFT JOIN config.forme_giuridiche fg ON ((fg.id = ds.forma_giuridica_id)))
     LEFT JOIN config.province pr ON ((pr.id = ds.id_prov_iscri_rea)));
```

</div>


---
{% include-markdown "signature-core.md" %}
