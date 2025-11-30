{% include-markdown "it/dbzero/anagrafiche/manual/vw_indirizzi_dettaglio.md" %}
# 🔍 View `vw_indirizzi_dettaglio`

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_indirizzi_dettaglio AS
SELECT idd.id AS indirizzo_dettaglio_id,
    idd.stradario_id,
    s.comune_id,
    idd.indirizzo_normalizzato,
    idd.via_norm,
    idd.civico,
    idd.estensione_civico,
    idd.palazzina,
    idd.scala,
    idd.piano,
    idd.interno,
    idd.altro,
    idd.civic_geoloc,
    idd.street_geoloc,
    idd.attivo,
    idd.storicizza,
    idd.tx_id,
    idd.data_insert,
    idd.user_insert,
    idd.data_update,
    idd.user_update
   FROM (anagrafiche.indirizzi_dettaglio idd
     JOIN config.stradario s ON ((s.id = idd.stradario_id)));
```


---
{% include-markdown "signature-core.md" %}
