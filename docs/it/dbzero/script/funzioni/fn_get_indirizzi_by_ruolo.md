{% include-markdown "it/dbzero/script/manual/fn_get_indirizzi_by_ruolo.md" %}
# ⚙️ Funzione `fn_get_indirizzi_by_ruolo`

```sql
CREATE FUNCTION fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id bigint)
 RETURNS TABLE(tipo_indirizzo character varying, indirizzo_completo text, geoloc geometry, indirizzo_id bigint, soggetto_ruolo_id bigint, tipo_indirizzo_id integer, indirizzo_dettaglio_id bigint, indirizzo_libero text, is_normalizzato boolean, stato_id integer, stato_descrizione character varying, stato_iso2 character, regione_id integer, regione_descrizione character varying, provincia_id integer, provincia_sigla character varying, provincia_descrizione character varying, comune_id integer, comune_descrizione character varying, codice_postale_id integer, cap_codice character, locality character varying, administrative_area character varying, sublocality character varying, postal_box character varying)
 LANGUAGE sql
 STABLE
AS $function$
  SELECT
      -- tipo indirizzo
      ti.codice_interno AS tipo_indirizzo,

      -- composizione indirizzo human-readable con fallback
      CASE
          ------------------------------------------------------------------
          -- 1) Indirizzo normalizzato: dettaglio civico + Comune/CAP da STRADARIO/INDIRIZZI
          ------------------------------------------------------------------
          WHEN ai.indirizzo_dettaglio_id IS NOT NULL THEN
              trim(
                  concat_ws(
                      ', ',
                      NULLIF(ad.indirizzo_normalizzato, ''),
                      NULLIF(
                          concat_ws(
                              ' ',
                              NULLIF(COALESCE(co_ai.descrizione, co_s.descrizione), ''),
                              NULLIF(COALESCE(cp_ai.codice, cp_s.codice), '')
                          ),
                          ''
                      )
                  )
              )

          ------------------------------------------------------------------
          -- 2) Indirizzo libero nazionale:
          --    indirizzo_dettaglio_id NULL, indirizzo_libero NON NULL
          --    e almeno un comune/CAP disponibile (da indirizzi o da eventuale stradario)
          ------------------------------------------------------------------
          WHEN ai.indirizzo_dettaglio_id IS NULL
              AND ai.indirizzo_libero IS NOT NULL
              AND (
                  ai.comune_id IS NOT NULL
                  OR ai.codice_postale_id IS NOT NULL
                  OR co_s.id IS NOT NULL
              ) THEN
              trim(
                  concat_ws(
                      ', ',
                      NULLIF(ai.indirizzo_libero, ''),
                      NULLIF(
                          concat_ws(
                              ' ',
                              NULLIF(COALESCE(co_ai.descrizione, co_s.descrizione), ''),
                              NULLIF(COALESCE(cp_ai.codice, cp_s.codice), '')
                          ),
                          ''
                      )
                  )
              )

          ------------------------------------------------------------------
          -- 3) Indirizzo libero / estero:
          --    uso i campi "internazionali" come locality, administrative_area, postal_box
          ------------------------------------------------------------------
          WHEN ai.indirizzo_dettaglio_id IS NULL
              AND ai.indirizzo_libero IS NOT NULL THEN
              trim(
                  concat_ws(
                      ', ',
                      NULLIF(ai.indirizzo_libero, ''),
                      NULLIF(ai.locality, ''),
                      NULLIF(ai.administrative_area, ''),
                      NULLIF(ai.postal_box, '')
                  )
              )

          ------------------------------------------------------------------
          -- 4) Fallback: nessun dettaglio e nessun indirizzo_libero,
          --    ma ho locality/area/PO box
          ------------------------------------------------------------------
          ELSE
              trim(
                  concat_ws(
                      ', ',
                      NULLIF(ai.locality, ''),
                      NULLIF(ai.administrative_area, ''),
                      NULLIF(ai.postal_box, '')
                  )
              )
      END AS indirizzo_completo,

      -- geolocalizzazione prioritaria: dettaglio → indirizzo
      COALESCE(ad.civic_geoloc, ai.geoloc) AS geoloc,

      -- dati tecnici
      ai.id AS indirizzo_id,
      ai.soggetto_ruolo_id,
      ai.tipo_indirizzo_id,
      ai.indirizzo_dettaglio_id,
      ai.indirizzo_libero,
      (ai.indirizzo_dettaglio_id IS NOT NULL) AS is_normalizzato,

      -- geodata strutturata con COALESCE tra INDIRIZZI e STRADARIO
      COALESCE(ai.stato_id, re_ai.stato_id, re_s.stato_id) AS stato_id,
      st.descrizione AS stato_descrizione,
      st.codice_iso2 AS stato_iso2,

      COALESCE(re_ai.id, re_s.id) AS regione_id,
      COALESCE(re_ai.descrizione, re_s.descrizione) AS regione_descrizione,

      COALESCE(pr_ai.id, pr_s.id) AS provincia_id,
      COALESCE(pr_ai.sigla, pr_s.sigla) AS provincia_sigla,
      COALESCE(pr_ai.descrizione, pr_s.descrizione) AS provincia_descrizione,

      COALESCE(co_ai.id, co_s.id) AS comune_id,
      COALESCE(co_ai.descrizione, co_s.descrizione) AS comune_descrizione,

      COALESCE(cp_ai.id, cp_s.id) AS codice_postale_id,
      COALESCE(cp_ai.codice, cp_s.codice) AS cap_codice,

      -- dati raw (internazionali)
      ai.locality,
      ai.administrative_area,
      ai.sublocality,
      ai.postal_box
  FROM anagrafiche.indirizzi ai
  JOIN config.tipi_indirizzi ti
      ON ti.id = ai.tipo_indirizzo_id
  LEFT JOIN anagrafiche.indirizzi_dettaglio ad
      ON ad.id = ai.indirizzo_dettaglio_id
  LEFT JOIN config.stradario s
      ON s.id = ad.stradario_id
  -- lato STRADARIO
  LEFT JOIN config.comuni co_s
      ON co_s.id = s.comune_id
  LEFT JOIN config.codici_postali cp_s
      ON cp_s.id = s.codice_postale_id
  -- lato INDIRIZZI (per casi B/C e override)
  LEFT JOIN config.comuni co_ai
      ON co_ai.id = ai.comune_id
  LEFT JOIN config.codici_postali cp_ai
      ON cp_ai.id = ai.codice_postale_id
  LEFT JOIN config.province pr_ai
      ON pr_ai.id = co_ai.provincia_id
  LEFT JOIN config.province pr_s
      ON pr_s.id = co_s.provincia_id
  LEFT JOIN config.regioni re_ai
      ON re_ai.id = pr_ai.regione_id
  LEFT JOIN config.regioni re_s
      ON re_s.id = pr_s.regione_id
  LEFT JOIN config.stati st
      ON st.id = COALESCE(ai.stato_id, re_ai.stato_id, re_s.stato_id)
  WHERE ai.soggetto_ruolo_id = p_soggetto_ruolo_id
  ORDER BY ti.codice_interno;
  $function$
```

---
{% include-markdown "signature-core.md" %}
