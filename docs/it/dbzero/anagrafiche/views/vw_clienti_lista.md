# 🔍 View `vw_clienti_lista`

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_clienti_lista AS
SELECT cl.id,
    cl.soggetto_ruolo_id,
    cl.istanza_utility_id,
    cl.billing_account_id,
    s.id AS soggetto_id,
    s.codice AS soggetto_codice,
    ba.codice AS ba_codice,
    s.ragione_sociale_completa,
    s.codice_fiscale,
    s.partita_iva,
    s.id_fiscale_univoco_cf_piva,
    u.id AS utility_id,
    u.descrizione AS utility_descrizione,
    sc.id AS stato_cliente_id,
    sc.codice_interno AS stato_codice_interno,
    sc.codice AS stato_codice,
    sc.descrizione_breve AS stato_descrizione,
    cl.data_attivazione,
    cl.data_sospensione,
    cl.data_riattivazione,
    cl.data_chiusura
   FROM (((((anagrafiche.clienti cl
     JOIN anagrafiche.istanze_utilities iu ON ((iu.id = cl.istanza_utility_id)))
     JOIN anagrafiche.soggetti s ON ((s.id = iu.soggetto_id)))
     JOIN anagrafiche.billing_account ba ON ((ba.id = cl.billing_account_id)))
     JOIN config.utilities u ON ((u.id = cl.utility_id)))
     JOIN config.stati_cliente sc ON ((sc.id = cl.stato_cliente_id)));
```


---
{% include-markdown "signature-core.md" %}
