{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_contratto.md" %}
# 🔍 View `vw_stato_sorgente_contratto`

> 📝 **Descrizione**
>
> Resolver di dominio D2 (brief-db-proiezione-stato-dominio roll-out): descrittore normalizzato dello stato vivo di ogni contratto — stato nativo (alias fedeli) + fase/esito/terminale da config.stati_doc_contratti. Chiave (sorgente_tipo_id, sorgente_uid) con sorgente_uid=(id)::text (key_selector=id); al piu' una riga per chiave. Read-time. Consumata dal motore solo via script.vw_stato_sorgente.

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_contratto AS
SELECT s.id AS sorgente_tipo_id,
    (c.id)::text AS sorgente_uid,
    sdc.codice_interno AS stato_codice_interno,
    sdc.codice AS stato_codice,
    sdc.descrizione AS stato_descrizione,
    sdc.fase,
    sdc.esito,
    sdc.terminale
   FROM ((vendite.contratti c
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'CONTRATTO'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_contratti sdc ON ((sdc.id = c.stato_doc_contratto_id)));
```


---
{% include-markdown "signature-core.md" %}
