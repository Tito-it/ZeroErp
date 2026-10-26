{% include-markdown "it/dbzero/script/manual/fn_get_stradario.md" %}
# ⚙️ Funzione `fn_get_stradario`

```sql
CREATE FUNCTION fn_get_stradario(p_comune_id integer, p_indirizzo text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_stradario(p_comune_id integer DEFAULT NULL::integer, p_indirizzo text DEFAULT ''::text)
 RETURNS TABLE(stradario_id integer, via_id integer, toponomastica_id integer, descrizione_toponomastica character varying, sigla_stato character varying, descrizione_via character varying, descrizione_breve character varying, cod_postale text, comune character varying, provincia text, geoloc geometry, descrizione_completa text)
 LANGUAGE plpgsql
AS $function$
  BEGIN
    -- Funzione per ottenere le informazioni dello stradario
    /* La funzione se indicato uno specifico comune restituisce le informazioni
        relative a tutte le vie di quel comune, altrimenti restituisce tutte le vie
        dello stradario_generale che contengono l'indirizzo indicato.

        p_comune_id: ID del comune (opzionale)
        p_indirizzo: stringa da cercare nell'indirizzo (opzionale)
       */

    IF p_comune_id IS NOT NULL THEN
      -- ricerca filtrata per comune
      -- ⚠️ cp.codice (era cp.codice_postale fino a 20250817-24)
      --    e i due ::text allineano la query ai tipi dichiarati.
      RETURN QUERY
      SELECT
        s.id                      AS stradario_id,
        v.id                      AS via_id,
        t.id                      AS toponomastica_id,
        t.descrizione             AS descrizione_toponomastica,
        st.sigla_stato            AS sigla_stato,
        v.descrizione             AS descrizione_via,
        v.descrizione_breve       AS descrizione_breve,
        cp.codice::text           AS cod_postale,
        c.descrizione             AS comune,
        pr.sigla::text            AS provincia,
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
      -- Qui comune/CAP/provincia non sono determinati: restano
      -- i segnaposto vuoti, ora ::text come la dichiarazione.
      RETURN QUERY
      SELECT
        NULL::integer             AS stradario_id,
        v.id                      AS via_id,
        t.id                      AS toponomastica_id,
        t.descrizione             AS descrizione_toponomastica,
        st.sigla_stato            AS sigla_stato,
        v.descrizione             AS descrizione_via,
        v.descrizione_breve       AS descrizione_breve,
        ''::text                  AS cod_postale,
        ''::character varying     AS comune,
        ''::text                  AS provincia,
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

COMMENT ON FUNCTION script.fn_get_stradario(p_comune_id integer, p_indirizzo text)
IS 'Stradario per comune (o ricerca libera su stradario_generale). cod_postale e provincia sono text esplicito: erano character = char(1) (brief-db-bonifica-riferimenti-morti F2).';
```

</div>

---
{% include-markdown "signature-core.md" %}
