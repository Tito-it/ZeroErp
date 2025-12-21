{% include-markdown "it/dbzero/anagrafiche/manual/vw_indirizzi_resolved_ruolo.md" %}
# 🔍 View `vw_indirizzi_resolved_ruolo`

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_indirizzi_resolved_ruolo AS
SELECT 'RUOLO'::text AS scope,
    i.id AS indirizzo_id,
    sr.soggetto_id,
    i.soggetto_ruolo_id,
    i.tipo_indirizzo_id,
    ti.codice_interno AS tipo_indirizzo_codice,
    ti.descrizione AS tipo_indirizzo_descrizione,
    (i.indirizzo_dettaglio_id IS NOT NULL) AS is_normalizzato,
    i.indirizzo_dettaglio_id,
    COALESCE(vidd.indirizzo_normalizzato, NULLIF(btrim(i.indirizzo_libero), ''::text), NULLIF(btrim(concat_ws(', '::text, NULLIF(btrim((i.postal_box)::text), ''::text), NULLIF(btrim((i.sublocality)::text), ''::text), NULLIF(btrim((i.locality)::text), ''::text), NULLIF(btrim((i.administrative_area)::text), ''::text))), ''::text)) AS indirizzo_display,
    i.indirizzo_libero,
    i.stato_id,
    i.administrative_area,
    i.locality,
    i.sublocality,
    i.postal_box,
    COALESCE(vidd.comune_id, i.comune_id) AS comune_id,
    COALESCE(vidd.descrizione_comune, ic.comune) AS comune_descrizione,
    COALESCE(vidd.cap, ic.codice_postale) AS cap,
    COALESCE(vidd.provincia, ic.provincia) AS provincia,
    vidd.stradario_id,
    vidd.via_norm,
    vidd.civico,
    vidd.estensione_civico,
    vidd.palazzina,
    vidd.scala,
    vidd.piano,
    vidd.interno,
    vidd.altro,
    COALESCE(vidd.civic_geoloc, vidd.street_geoloc, i.geoloc) AS geoloc,
    i.storicizza,
    i.tx_id,
    i.data_insert,
    i.user_insert,
    i.data_update,
    i.user_update
   FROM ((((anagrafiche.indirizzi i
     JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = i.soggetto_ruolo_id)))
     JOIN config.tipi_indirizzi ti ON ((ti.id = i.tipo_indirizzo_id)))
     LEFT JOIN anagrafiche.vw_indirizzi_dettaglio vidd ON ((vidd.indirizzo_dettaglio_id = i.indirizzo_dettaglio_id)))
     LEFT JOIN script.vw_indirizzo_completo ic ON ((ic.id_comune = i.comune_id)));
```


---
{% include-markdown "signature-core.md" %}
