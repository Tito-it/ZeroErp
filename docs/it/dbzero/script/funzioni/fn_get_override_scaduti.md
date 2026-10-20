{% include-markdown "it/dbzero/script/manual/fn_get_override_scaduti.md" %}
# ⚙️ Funzione `fn_get_override_scaduti`

```sql
CREATE FUNCTION fn_get_override_scaduti(p_giorni_tolleranza integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_override_scaduti(p_giorni_tolleranza integer DEFAULT 0)
 RETURNS TABLE(tipo_override text, override_id bigint, auth_user_id integer, dettaglio text, valido_al date, giorni_scaduto integer)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituisce tutti gli override utente la cui data
  --   valido_al e' scaduta (passata). Unisce le 3 tabelle
  --   override: aree, oggetti, azioni.
  --
  -- Parametri:
  --   p_giorni_tolleranza: ignora override scaduti da meno
  --     di N giorni (default 0 = tutti gli scaduti).
  --
  -- Uso tipico:
  --   SELECT * FROM script.fn_get_override_scaduti(0);
  --   SELECT * FROM script.fn_get_override_scaduti(7);
  -- =========================================================

  RETURN QUERY

  -- Override aree scaduti
  SELECT
    'user_override_aree'::text      AS tipo_override,
    uoa.id                           AS override_id,
    uoa.auth_user_id,
    format('area: %s, livello: %s',
           af.codice, uoa.livello::text) AS dettaglio,
    uoa.valido_al,
    ((SELECT script.fn_data_operativa()) - uoa.valido_al)::integer AS giorni_scaduto
  FROM config.user_override_aree uoa
  JOIN config.aree_funzionali af ON af.id = uoa.area_id
  WHERE uoa.valido_al IS NOT NULL
    AND uoa.valido_al < (SELECT script.fn_data_operativa()) - p_giorni_tolleranza

  UNION ALL

  -- Override oggetti scaduti
  SELECT
    'user_override_oggetti'::text    AS tipo_override,
    uoo.id                            AS override_id,
    uoo.auth_user_id,
    format('model: %s.%s, livello: %s',
           uoo.app_label, uoo.model_name,
           uoo.livello::text)         AS dettaglio,
    uoo.valido_al,
    ((SELECT script.fn_data_operativa()) - uoo.valido_al)::integer AS giorni_scaduto
  FROM config.user_override_oggetti uoo
  WHERE uoo.valido_al IS NOT NULL
    AND uoo.valido_al < (SELECT script.fn_data_operativa()) - p_giorni_tolleranza

  UNION ALL

  -- Override azioni scaduti
  SELECT
    'user_override_azioni'::text     AS tipo_override,
    uoaz.id                           AS override_id,
    uoaz.auth_user_id,
    format('azione: %s, abilitata: %s',
           ap.permission_codename,
           uoaz.abilitata::text)      AS dettaglio,
    uoaz.valido_al,
    ((SELECT script.fn_data_operativa()) - uoaz.valido_al)::integer AS giorni_scaduto
  FROM config.user_override_azioni uoaz
  JOIN config.azioni_processo ap ON ap.id = uoaz.azione_id
  WHERE uoaz.valido_al IS NOT NULL
    AND uoaz.valido_al < (SELECT script.fn_data_operativa()) - p_giorni_tolleranza

  ORDER BY giorni_scaduto DESC, tipo_override, auth_user_id;
END
$function$

COMMENT ON FUNCTION script.fn_get_override_scaduti(p_giorni_tolleranza integer)
IS 'Restituisce override utente scaduti (valido_al < oggi) per segnalazione/pulizia.';
```

</div>

---
{% include-markdown "signature-core.md" %}
