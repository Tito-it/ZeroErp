{% include-markdown "it/dbzero/script/manual/fn_get_soggetto_dati_by_ruolo.md" %}
# ⚙️ Funzione `fn_get_soggetto_dati_by_ruolo`

```sql
CREATE FUNCTION fn_get_soggetto_dati_by_ruolo(p_soggetto_ruolo_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_soggetto_dati_by_ruolo(p_soggetto_ruolo_id bigint)
 RETURNS TABLE(soggetto_ruolo_id bigint, soggetto_id uuid, tipo_ruolo_id integer, tipo_ruolo_codice character varying, tipo_ruolo_codice_interno character varying, tipo_ruolo_descrizione character varying, soggetto_codice text, ragione_sociale text, ragione_sociale_completa text, cognome text, nome text, codice_fiscale text, partita_iva text, id_fiscale_univoco_cf_piva text, sesso character, data_nascita date, soggetto_attivo boolean, stato_id integer, comune_id integer, titolo_cortesia_id integer, tipo_soggetto_dettaglio_id bigint, default_contatto_id bigint, tipo_soggetto_id character varying, tipo_soggetto_descrizione character varying, tipo_soggetto_codice_interno character varying, titolo_cortesia_descrizione text, titolo_cortesia_descrizione_breve text, has_dati_societari boolean, dati_societari_id bigint, forma_giuridica_id bigint, forma_giuridica_codice character varying, forma_giuridica_descrizione character varying, id_prov_iscri_rea integer, provincia_iscri_rea_sigla character varying, iscrizione_rea character varying, capitale_sociale numeric, socio_unico text, liquidazione text, destinatario_fe character varying, pec_fatturazione character varying, codice_sdi character varying, data_costituzione date)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Dato un soggetto_ruolo_id, restituisce un record con i
  --   dati anagrafici fondamentali del soggetto, il tipo ruolo
  --   risolto, il tipo soggetto, il titolo cortesia e, se
  --   presenti, i dati societari completi.
  --
  --   Tutti gli ID delle tabelle collegate sono inclusi per
  --   consentire navigazione e lookup dal frontend.
  --
  --   Modello: vw_soggetti_ruoli_dettaglio + vw_dati_societari.
  --
  -- Parametri:
  --   p_soggetto_ruolo_id: ID del record soggetti_ruoli
  --
  -- Restituisce:
  --   Un singolo record (o nessun record se ID inesistente).
  -- =========================================================

  -- Guard: parametro obbligatorio e valido
  IF p_soggetto_ruolo_id IS NULL OR p_soggetto_ruolo_id <= 0 THEN
    RAISE EXCEPTION 'p_soggetto_ruolo_id obbligatorio e > 0 (ricevuto: %)',
      COALESCE(p_soggetto_ruolo_id::text, 'NULL')
      USING ERRCODE = 'invalid_parameter_value';
  END IF;

  RETURN QUERY
  SELECT
    -- Identita' ruolo
    sr.id                        AS soggetto_ruolo_id,
    s.id                         AS soggetto_id,
    tr.id                        AS tipo_ruolo_id,
    tr.codice                    AS tipo_ruolo_codice,
    tr.codice_interno            AS tipo_ruolo_codice_interno,
    tr.descrizione               AS tipo_ruolo_descrizione,
    -- Dati anagrafici soggetto
    s.codice                     AS soggetto_codice,
    s.ragione_sociale,
    s.ragione_sociale_completa,
    s.cognome,
    s.nome,
    s.codice_fiscale,
    s.partita_iva,
    s.id_fiscale_univoco_cf_piva,
    s.sesso,
    s.data_nascita,
    s.attivo                     AS soggetto_attivo,
    -- FK e ID collegati
    s.stato_id,
    s.comune_id,
    s.titolo_cortesia_id,
    s.tipo_soggetto_dettaglio_id,
    s.default_contatto_id,
    -- Tipo soggetto (risolto)
    td.tipo_soggetto_id,
    ts.descrizione               AS tipo_soggetto_descrizione,
    td.codice_interno            AS tipo_soggetto_codice_interno,
    -- Titolo cortesia (risolto)
    tc.descrizione               AS titolo_cortesia_descrizione,
    tc.descrizione_breve         AS titolo_cortesia_descrizione_breve,
    -- Dati societari
    (ds.id IS NOT NULL)          AS has_dati_societari,
    ds.id                        AS dati_societari_id,
    ds.forma_giuridica_id,
    fg.codice                    AS forma_giuridica_codice,
    fg.descrizione               AS forma_giuridica_descrizione,
    ds.id_prov_iscri_rea,
    pr.sigla                     AS provincia_iscri_rea_sigla,
    ds.iscrizione_rea,
    ds.capitale_sociale,
    ds.socio_unico::text,
    ds.liquidazione::text,
    ds.destinatario_fe,
    ds.pec_fatturazione,
    ds.codice_sdi,
    ds.data_costituzione
  FROM anagrafiche.soggetti_ruoli sr
    INNER JOIN anagrafiche.soggetti s              ON s.id  = sr.soggetto_id
    INNER JOIN config.tipi_ruoli tr                ON tr.id = sr.tipo_ruolo_id
    LEFT  JOIN config.tipi_soggetto_dettaglio td   ON td.id = s.tipo_soggetto_dettaglio_id
    LEFT  JOIN config.tipi_soggetto ts             ON ts.id = td.tipo_soggetto_id
    LEFT  JOIN config.titoli_cortesia tc           ON tc.id = s.titolo_cortesia_id
    LEFT  JOIN anagrafiche.dati_societari ds       ON ds.soggetto_id = s.id
    LEFT  JOIN config.forme_giuridiche fg          ON fg.id = ds.forma_giuridica_id
    LEFT  JOIN config.province pr                  ON pr.id = ds.id_prov_iscri_rea
  WHERE sr.id = p_soggetto_ruolo_id;
END
$function$

COMMENT ON FUNCTION script.fn_get_soggetto_dati_by_ruolo(p_soggetto_ruolo_id bigint)
IS 'Dato un soggetto_ruolo_id, restituisce dati anagrafici soggetto + tipo ruolo + tipo soggetto + titolo cortesia + dati societari (se presenti). Tutti gli ID delle FK collegate sono inclusi.';
```

</div>

---
{% include-markdown "signature-core.md" %}
