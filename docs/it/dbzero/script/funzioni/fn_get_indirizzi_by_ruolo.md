{% include-markdown "it/dbzero/script/manual/fn_get_indirizzi_by_ruolo.md" %}
# ⚙️ Funzione `fn_get_indirizzi_by_ruolo`

```sql
CREATE FUNCTION fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(tipo_indirizzo character varying, indirizzo_completo text, geoloc geometry, indirizzo_id bigint, soggetto_ruolo_id bigint, istanza_utility_id bigint, tipo_indirizzo_id integer, indirizzo_dettaglio_id bigint, indirizzo_libero text, is_normalizzato boolean, stato_id integer, stato_descrizione character varying, stato_iso2 character, regione_id integer, regione_descrizione character varying, provincia_id integer, provincia_sigla character varying, provincia_descrizione character varying, comune_id integer, comune_descrizione character varying, codice_postale_id integer, cap_codice character varying, locality character varying, administrative_area character varying, sublocality character varying, postal_code character varying)
 LANGUAGE sql
 STABLE
AS $function$
  -- Proiezione dalla vista base, filtrata per scope RUOLO.
  -- Se p_istanza_utility_id valorizzato: istanza specifica + generici (NULL).
  -- Se p_istanza_utility_id NULL: tutti gli indirizzi del ruolo.
  SELECT
    r.tipo_indirizzo_codice, r.indirizzo_display, r.geoloc,
    r.indirizzo_id, r.soggetto_ruolo_id, r.istanza_utility_id,
    r.tipo_indirizzo_id, r.indirizzo_dettaglio_id, r.indirizzo_libero,
    r.is_normalizzato,
    r.stato_id, r.stato_descrizione, r.stato_iso2,
    r.regione_id, r.regione_descrizione,
    r.provincia_id, r.provincia_sigla, r.provincia_descrizione,
    r.comune_id, r.comune_descrizione,
    r.codice_postale_id, r.cap_codice,
    r.locality, r.administrative_area, r.sublocality, r.postal_code
  FROM anagrafiche.vw_indirizzi_resolved_base r
  WHERE r.scope = 'RUOLO'
    AND r.soggetto_ruolo_id = p_soggetto_ruolo_id
    AND (p_istanza_utility_id IS NULL
         OR r.istanza_utility_id = p_istanza_utility_id
         OR r.istanza_utility_id IS NULL)
  ORDER BY r.tipo_indirizzo_codice, r.istanza_utility_id NULLS LAST, r.indirizzo_id;
$function$

COMMENT ON FUNCTION script.fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint)
IS 'Indirizzi layer RUOLO. Se p_istanza_utility_id valorizzato filtra istanza specifica + generici (NULL).';
```

---
{% include-markdown "signature-core.md" %}
