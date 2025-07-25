# ⚙️ Funzione `fn_get_indirizzi_by_ruolo`

```sql
CREATE FUNCTION fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id integer)
 RETURNS TABLE(tipo_indirizzo character varying, indirizzo_completo text, geoloc public.geometry)
 LANGUAGE sql
 STABLE
AS $function$
SELECT
  ti.cod_int_tipo_indirizzo  AS tipo_indirizzo,
  -- 1) dettaglio normalizzato: via/civico + Comune/CAP da config.stradario
  CASE
    WHEN ai.indirizzo_dettaglio_id IS NOT NULL THEN
      trim(
        ad.indirizzo_normalizzato || 
        ', ' || co.descrizione ||
        COALESCE(' ' || cp.codice_postale, '')
      )
	   -- 2) indirizzo libero (nazionale)
    WHEN ai.indirizzo_libero IS NOT NULL THEN
      trim(
        ai.indirizzo_libero ||
        COALESCE(', ' || co.descrizione, '') ||
        COALESCE(' ' || cp.codice_postale, '')
      )
	  -- 3) estero / internazionale
    ELSE
      trim(
	  	ai.indirizzo_libero ||
        COALESCE(ai.locality, '') ||
        COALESCE(', ' || ai.administrative_area, '') ||
        COALESCE(', ' || ai.postal_box, '')
      )
  END AS indirizzo_completo,
  -- Geolocalizzazione prioritaria: dettaglio → indirizzo
  COALESCE(ad.civic_geoloc, ai.geoloc) AS geoloc
FROM anagrafiche.indirizzi ai
JOIN config.tipi_indirizzi ti ON ti.id = ai.tipo_indirizzo_id
LEFT JOIN anagrafiche.indirizzi_dettaglio ad ON ad.id = ai.indirizzo_dettaglio_id
LEFT JOIN config.comuni co ON co.id = ai.comune_id
LEFT JOIN config.codici_postali cp ON cp.id = ai.codice_postale_id
WHERE ai.soggetto_ruolo_id = p_soggetto_ruolo_id
ORDER BY ti.cod_int_tipo_indirizzo;
$function$
```
---
{% include-markdown "signature-core.md" %}
