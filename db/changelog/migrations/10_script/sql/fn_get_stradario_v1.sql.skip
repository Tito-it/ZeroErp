CREATE OR REPLACE FUNCTION script.fn_get_stradario(p_comune_id integer DEFAULT NULL::integer, p_indirizzo text DEFAULT ''::text)
 RETURNS TABLE(stradario_id integer, via_id integer, toponomastica_id integer, descrizione_toponomastica character varying, sigla_stato character varying, descrizione_via character varying, descrizione_breve character varying, cod_postale character varying, comune character varying, provincia character varying, geoloc geometry, descrizione_completa text)
 LANGUAGE plpgsql
AS $function$
BEGIN
  IF p_comune_id IS NOT NULL THEN
    -- ricerca filtrata per comune
    RETURN QUERY
    SELECT
      s.id                      AS stradario_id,
      v.id                      AS via_id,
      t.id                      AS toponomastica_id,
      t.descrizione             AS descrizione_toponomastica,
      st.sigla_stato            AS sigla_stato,
      v.descrizione             AS descrizione_via,
      v.descrizione_breve       AS descrizione_breve,
      cp.codice_postale         AS cod_postale,
      c.descrizione             AS comune,
      pr.sigla                  AS provincia,
      s.geoloc                  AS geoloc,
      CONCAT_WS(' ', t.descrizione, v.descrizione) 
                               AS descrizione_completa
    FROM config.stradario s
      JOIN config.stradario_generale v  ON s.stradario_generale_id = v.id
      JOIN config.toponomastica t       ON v.toponomastica_id = t.id
      JOIN config.comuni c              ON s.comune_id = c.id
      JOIN config.province pr           ON c.provincia_id = pr.id
      JOIN config.codici_postali cp     ON s.codice_postale_id = cp.id
      LEFT JOIN config.stati st         ON t.stato_id = st.id
    WHERE s.comune_id = p_comune_id
      AND (t.descrizione || ' ' || v.descrizione)
          ILIKE '%' || p_indirizzo || '%'
    ORDER BY v.descrizione;

  ELSE
    -- ricerca libera su tutto lo stradario_generale
    RETURN QUERY
    SELECT
      NULL::integer             AS stradario_id,
      v.id                      AS via_id,
      t.id                      AS toponomastica_id,
      t.descrizione             AS descrizione_toponomastica,
      st.sigla_stato            AS sigla_stato,
      v.descrizione             AS descrizione_via,
      v.descrizione_breve       AS descrizione_breve,
      ''::character varying     AS cod_postale,
      ''::character varying     AS comune,
      ''::character varying     AS provincia,
      NULL::geometry            AS geoloc,
      CONCAT_WS(' ', t.descrizione, v.descrizione)
                               AS descrizione_completa
    FROM config.stradario_generale v
      JOIN config.toponomastica t   ON v.toponomastica_id = t.id
      LEFT JOIN config.stati st     ON t.stato_id = st.id
    WHERE (t.descrizione || ' ' || v.descrizione)
          ILIKE '%' || p_indirizzo || '%'
    ORDER BY v.descrizione;
  END IF;
END;
$function$
