{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_offerta.md" %}
# 🔍 View `vw_stato_sorgente_offerta`

> 📝 **Descrizione**
>
> Resolver di dominio D2 (brief-db-proiezione-stato-dominio roll-out): descrittore normalizzato dello stato vivo di ogni offerta commerciale — stato nativo (alias fedeli) + fase/esito/terminale dichiarati su config.stati_doc_offerte. Chiave (sorgente_tipo_id, sorgente_uid) coerente con pratiche_sorgenti (key_selector=uid); al piu' una riga per chiave. Read-time (nessun mirror). Consumata dal motore solo via script.vw_stato_sorgente.

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_offerta AS
SELECT s.id AS sorgente_tipo_id,
    (oc.uid)::text AS sorgente_uid,
    sdo.codice_interno AS stato_codice_interno,
    sdo.codice AS stato_codice,
    sdo.descrizione AS stato_descrizione,
    sdo.fase,
    sdo.esito,
    sdo.terminale
   FROM ((vendite.offerte_commerciali oc
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_offerte sdo ON ((sdo.id = oc.stato_doc_offerta_id)));
```


---
{% include-markdown "signature-core.md" %}
