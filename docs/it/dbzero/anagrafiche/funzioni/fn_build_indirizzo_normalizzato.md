{% include-markdown "it/dbzero/anagrafiche/manual/fn_build_indirizzo_normalizzato.md" %}
# ⚙️ Funzione `fn_build_indirizzo_normalizzato`

```sql
CREATE FUNCTION fn_build_indirizzo_normalizzato(p_stradario_id integer, p_civico integer, p_estensione character varying, p_palazzina character varying, p_scala character varying, p_piano character varying, p_interno character varying, OUT o_estensione_civico character varying, OUT o_palazzina character varying, OUT o_scala character varying, OUT o_piano character varying, OUT o_interno character varying, OUT o_via_norm text, OUT o_civico_norm text, OUT o_indirizzo_normalizzato text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_build_indirizzo_normalizzato(p_stradario_id integer, p_civico integer DEFAULT NULL::integer, p_estensione character varying DEFAULT NULL::character varying, p_palazzina character varying DEFAULT NULL::character varying, p_scala character varying DEFAULT NULL::character varying, p_piano character varying DEFAULT NULL::character varying, p_interno character varying DEFAULT NULL::character varying, OUT o_estensione_civico character varying, OUT o_palazzina character varying, OUT o_scala character varying, OUT o_piano character varying, OUT o_interno character varying, OUT o_via_norm text, OUT o_civico_norm text, OUT o_indirizzo_normalizzato text)
 RETURNS record
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Centralizza TUTTA la logica di normalizzazione indirizzi.
  --   Riceve i campi raw, ritorna tutti i campi calcolati.
  --   Unica source of truth: il trigger e Python la chiamano.
  --
  -- OUT params:
  --   o_estensione_civico:      normalizzata (UPPER+BTRIM, prefisso '/')
  --   o_palazzina:              normalizzata (UPPER+BTRIM)
  --   o_scala:                  normalizzata (UPPER+BTRIM)
  --   o_piano:                  normalizzato (UPPER+BTRIM)
  --   o_interno:                normalizzato (UPPER+BTRIM)
  --   o_via_norm:               UPPER(tipo_toponimo + nome_strada)
  --   o_civico_norm:            civico + estensione oppure 'SNC'
  --   o_indirizzo_normalizzato: stringa completa
  -- =========================================================

  -- Guard
  IF p_stradario_id IS NULL OR p_stradario_id <= 0 THEN
    RETURN;
  END IF;

  -- 1. Lookup via_norm
  SELECT UPPER(TRIM(iv.tipo_toponimo || ' ' || iv.nome_strada))
    INTO o_via_norm
    FROM script.vw_indirizzo_completo iv
   WHERE iv.id_stradario = p_stradario_id
   LIMIT 1;

  IF o_via_norm IS NULL THEN
    RETURN;
  END IF;

  -- 2. Normalizza colonne strutturali
  o_estensione_civico := UPPER(BTRIM(p_estensione));
  o_palazzina         := UPPER(BTRIM(p_palazzina));
  o_scala             := UPPER(BTRIM(p_scala));
  o_piano             := UPPER(BTRIM(p_piano));
  o_interno           := UPPER(BTRIM(p_interno));

  -- 3. Prefisso '/' su estensione
  IF o_estensione_civico IS NOT NULL AND o_estensione_civico <> '' THEN
    IF LEFT(o_estensione_civico, 1) <> '/' THEN
      o_estensione_civico := '/' || o_estensione_civico;
    END IF;
  END IF;

  -- 4. Civico norm
  IF p_civico IS NOT NULL AND p_civico <> 0 THEN
    IF o_estensione_civico IS NOT NULL AND o_estensione_civico <> '' THEN
      o_civico_norm := p_civico::text || o_estensione_civico;
    ELSE
      o_civico_norm := p_civico::text;
    END IF;
  ELSE
    o_civico_norm := 'SNC';
  END IF;

  -- 5. Indirizzo normalizzato
  o_indirizzo_normalizzato := TRIM(BOTH ' ' FROM (
      o_via_norm
    || CASE WHEN o_civico_norm <> '' THEN ', ' || o_civico_norm ELSE '' END
    || CASE WHEN o_palazzina IS NOT NULL AND o_palazzina <> ''
            THEN ', Pal.' || o_palazzina ELSE '' END
    || CASE WHEN o_scala IS NOT NULL AND o_scala <> ''
            THEN ', Scala ' || o_scala ELSE '' END
    || CASE WHEN o_piano IS NOT NULL AND o_piano <> ''
            THEN ', Piano ' || o_piano ELSE '' END
    || CASE WHEN o_interno IS NOT NULL AND o_interno <> ''
            THEN ', Int.' || o_interno ELSE '' END
  ));
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_build_indirizzo_normalizzato(p_stradario_id integer, p_civico integer, p_estensione character varying, p_palazzina character varying, p_scala character varying, p_piano character varying, p_interno character varying, OUT o_estensione_civico character varying, OUT o_palazzina character varying, OUT o_scala character varying, OUT o_piano character varying, OUT o_interno character varying, OUT o_via_norm text, OUT o_civico_norm text, OUT o_indirizzo_normalizzato text)
IS 'Centralizza TUTTA la logica di normalizzazione indirizzi. Ritorna record con colonne strutturali normalizzate + via_norm + civico_norm + indirizzo_normalizzato. Usata dal trigger (zero logica) e dal backend Python (check duplicato via GIN index).';
```

</div>

---
{% include-markdown "signature-core.md" %}
