{% include-markdown "it/dbzero/anagrafiche/manual/vw_indirizzi_resolved_base.md" %}
# 🔍 View `vw_indirizzi_resolved_base`

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_indirizzi_resolved_base AS
SELECT b.scope,
    b.scope AS source,
    b.indirizzo_id,
    b.soggetto_id,
    b.soggetto_ruolo_id,
    b.istanza_utility_id,
    b.tipo_indirizzo_id,
    (ti.codice)::character varying(10) AS tipo_indirizzo_codice,
    ti.descrizione AS tipo_indirizzo_descrizione,
    (b.indirizzo_dettaglio_id IS NOT NULL) AS is_normalizzato,
    b.indirizzo_dettaglio_id,
    COALESCE(vidd.indirizzo_normalizzato, NULLIF(btrim(b.indirizzo_libero), ''::text), NULLIF(btrim(concat_ws(', '::text, NULLIF(btrim((b.postal_box)::text), ''::text), NULLIF(btrim((b.sublocality)::text), ''::text), NULLIF(btrim((b.locality)::text), ''::text), NULLIF(btrim((b.administrative_area)::text), ''::text))), ''::text)) AS indirizzo_display,
    b.indirizzo_libero,
    b.administrative_area,
    b.locality,
    b.sublocality,
    b.postal_box AS postal_code,
    COALESCE(vidd.comune_id, b.comune_id) AS comune_id,
    COALESCE(vidd.descrizione_comune, co_ai.descrizione, co_s.descrizione, ic.comune) AS comune_descrizione,
    COALESCE(vidd.cap, ic.codice_postale) AS cap,
    COALESCE(vidd.provincia, ic.provincia) AS provincia,
    COALESCE(pr_ai.id, pr_s.id) AS provincia_id,
    COALESCE(pr_ai.sigla, pr_s.sigla) AS provincia_sigla,
    COALESCE(pr_ai.descrizione, pr_s.descrizione) AS provincia_descrizione,
    COALESCE(re_ai.id, re_s.id) AS regione_id,
    COALESCE(re_ai.descrizione, re_s.descrizione) AS regione_descrizione,
    COALESCE(b.stato_id, re_ai.stato_id, re_s.stato_id) AS stato_id,
    st.descrizione AS stato_descrizione,
    st.codice_iso2 AS stato_iso2,
    COALESCE(b.codice_postale_id, cp_s.id) AS codice_postale_id,
    COALESCE(cp_ai.codice, cp_s.codice) AS cap_codice,
    vidd.stradario_id,
    vidd.via_norm,
    vidd.civico,
    vidd.estensione_civico,
    vidd.palazzina,
    vidd.scala,
    vidd.piano,
    vidd.interno,
    vidd.altro,
    COALESCE(vidd.civic_geoloc, vidd.street_geoloc, b.geoloc) AS geoloc,
    b.storicizza,
    b.tx_id,
    b.data_insert,
    b.user_insert,
    b.data_update,
    b.user_update,
    ti.codice_interno AS tipo_indirizzo_codice_interno
   FROM (((((((((((((( SELECT 'RUOLO'::text AS scope,
            i.id AS indirizzo_id,
            sr.soggetto_id,
            i.soggetto_ruolo_id,
            i.istanza_utility_id,
            i.tipo_indirizzo_id,
            i.indirizzo_dettaglio_id,
            i.indirizzo_libero,
            i.stato_id,
            i.administrative_area,
            i.locality,
            i.sublocality,
            i.postal_code AS postal_box,
            i.comune_id,
            i.codice_postale_id,
            i.geoloc,
            i.storicizza,
            i.tx_id,
            i.data_insert,
            i.user_insert,
            i.data_update,
            i.user_update
           FROM (anagrafiche.indirizzi i
             JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = i.soggetto_ruolo_id)))
        UNION ALL
         SELECT 'SOGGETTO'::text AS scope,
            isg.id AS indirizzo_id,
            isg.soggetto_id,
            NULL::bigint AS soggetto_ruolo_id,
            NULL::bigint AS istanza_utility_id,
            isg.tipo_indirizzo_id,
            isg.indirizzo_dettaglio_id,
            isg.indirizzo_libero,
            isg.stato_id,
            isg.administrative_area,
            isg.locality,
            isg.sublocality,
            isg.postal_code AS postal_box,
            isg.comune_id,
            isg.codice_postale_id,
            isg.geoloc,
            isg.storicizza,
            isg.tx_id,
            isg.data_insert,
            isg.user_insert,
            isg.data_update,
            isg.user_update
           FROM anagrafiche.indirizzi_soggetti isg) b
     JOIN config.tipi_indirizzi ti ON ((ti.id = b.tipo_indirizzo_id)))
     LEFT JOIN anagrafiche.vw_indirizzi_dettaglio vidd ON ((vidd.indirizzo_dettaglio_id = b.indirizzo_dettaglio_id)))
     LEFT JOIN script.vw_indirizzo_completo ic ON ((ic.id_comune = b.comune_id)))
     LEFT JOIN config.stradario s ON ((s.id = vidd.stradario_id)))
     LEFT JOIN config.comuni co_s ON ((co_s.id = s.comune_id)))
     LEFT JOIN config.codici_postali cp_s ON ((cp_s.id = s.codice_postale_id)))
     LEFT JOIN config.comuni co_ai ON ((co_ai.id = b.comune_id)))
     LEFT JOIN config.codici_postali cp_ai ON ((cp_ai.id = b.codice_postale_id)))
     LEFT JOIN config.province pr_ai ON ((pr_ai.id = co_ai.provincia_id)))
     LEFT JOIN config.province pr_s ON ((pr_s.id = co_s.provincia_id)))
     LEFT JOIN config.regioni re_ai ON ((re_ai.id = pr_ai.regione_id)))
     LEFT JOIN config.regioni re_s ON ((re_s.id = pr_s.regione_id)))
     LEFT JOIN config.stati st ON ((st.id = COALESCE(b.stato_id, re_ai.stato_id, re_s.stato_id))));
```


---
{% include-markdown "signature-core.md" %}
