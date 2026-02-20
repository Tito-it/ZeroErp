{% include-markdown "it/dbzero/anagrafiche/manual/fn_search_indirizzi_dettaglio.md" %}
# ⚙️ Funzione `fn_search_indirizzi_dettaglio`

```sql
CREATE FUNCTION fn_search_indirizzi_dettaglio(p_stradario_id integer, p_civico integer, p_estensione_civico text, p_palazzina text, p_scala text, p_piano text, p_interno text, p_indirizzo_norm text, p_limit integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_search_indirizzi_dettaglio(p_stradario_id integer DEFAULT NULL::integer, p_civico integer DEFAULT NULL::integer, p_estensione_civico text DEFAULT NULL::text, p_palazzina text DEFAULT NULL::text, p_scala text DEFAULT NULL::text, p_piano text DEFAULT NULL::text, p_interno text DEFAULT NULL::text, p_indirizzo_norm text DEFAULT NULL::text, p_limit integer DEFAULT 50)
 RETURNS SETOF anagrafiche.vw_indirizzi_dettaglio
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
DECLARE
  v_limit integer := COALESCE(p_limit, 50);
  v_pattern text;
BEGIN
  IF p_indirizzo_norm IS NOT NULL THEN
    v_pattern := NULLIF(btrim(p_indirizzo_norm), '');
  ELSE
    v_pattern := NULL;
  END IF;

  IF p_stradario_id IS NULL AND v_pattern IS NULL THEN
    RAISE EXCEPTION
      'fn_search_indirizzi_dettaglio: valorizzare almeno p_stradario_id o p_indirizzo_norm (non vuoto)'
      USING HINT = 'Per ricerche fuzzy usare p_indirizzo_norm, per ricerche esatte usare p_stradario_id + dettagli civico.';
  END IF;

  IF p_stradario_id IS NOT NULL THEN
    RETURN QUERY
    SELECT *
    FROM anagrafiche.vw_indirizzi_dettaglio v
    WHERE
      v.attivo = TRUE
      AND v.stradario_id = p_stradario_id
      AND (p_civico IS NULL OR v.civico = p_civico)
      AND (p_estensione_civico IS NULL OR COALESCE(v.estensione_civico, '') = COALESCE(p_estensione_civico, ''))
      AND (p_palazzina IS NULL         OR COALESCE(v.palazzina,        '') = COALESCE(p_palazzina,        ''))
      AND (p_scala IS NULL             OR COALESCE(v.scala,            '') = COALESCE(p_scala,            ''))
      AND (p_piano IS NULL             OR COALESCE(v.piano,            '') = COALESCE(p_piano,            ''))
      AND (p_interno IS NULL           OR COALESCE(v.interno,          '') = COALESCE(p_interno,          ''))
      AND (
        v_pattern IS NULL
        OR UPPER(v.indirizzo_normalizzato) LIKE UPPER('%' || v_pattern || '%')
      )
    ORDER BY
      v.indirizzo_normalizzato,
      v.indirizzo_dettaglio_id
    LIMIT v_limit;

    RETURN;
  END IF;

  RETURN QUERY
  SELECT *
  FROM anagrafiche.vw_indirizzi_dettaglio v
  WHERE
    v.attivo = TRUE
    AND UPPER(v.indirizzo_normalizzato) LIKE UPPER('%' || v_pattern || '%')
  ORDER BY
    v.indirizzo_normalizzato,
    v.indirizzo_dettaglio_id
  LIMIT v_limit;

  RETURN;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_search_indirizzi_dettaglio(p_stradario_id integer, p_civico integer, p_estensione_civico text, p_palazzina text, p_scala text, p_piano text, p_interno text, p_indirizzo_norm text, p_limit integer)
IS 'Funzione di ricerca indirizzi di dettaglio:
 - Se p_stradario_id è valorizzato → ricerca per stradario_id (+ eventuali dettagli civico e pattern).
 - Se p_stradario_id è NULL       → ricerca fuzzy su indirizzo_normalizzato (pattern case-insensitive).
 Ritorna righe da anagrafiche.vw_indirizzi_dettaglio, solo attive, limitate da p_limit.';
```

---
{% include-markdown "signature-core.md" %}
