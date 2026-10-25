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
  --   Unica source of truth: il trigger, il BB
  --   fn_get_or_create_indirizzo_dettaglio e
  --   fn_check_indirizzo_duplicato la chiamano.
  --
  -- OUT params:
  --   o_estensione_civico:      normalizzata (UPPER+BTRIM, vuoto -> NULL, prefisso '/')
  --   o_palazzina:              normalizzata (UPPER+BTRIM, vuoto -> NULL)
  --   o_scala:                  normalizzata (UPPER+BTRIM, vuoto -> NULL)
  --   o_piano:                  normalizzato (UPPER+BTRIM, vuoto -> NULL)
  --   o_interno:                normalizzato (UPPER+BTRIM, vuoto -> NULL)
  --   o_via_norm:               UPPER(tipo_toponimo + nome_strada)
  --   o_civico_norm:            civico + estensione oppure 'SNC' (civico NULL)
  --   o_indirizzo_normalizzato: stringa completa
  --
  -- ⚠️ Via non risolta in vw_indirizzo_completo: TUTTI gli OUT
  --   restano NULL, anche le colonne strutturali. Chi cerca con
  --   questi valori deve fermarsi su o_via_norm NULL (D4).
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

  -- 2. Normalizza colonne strutturali: il vuoto e' NULL, una forma
  --    sola per «non c'e'» (l'indice e' NULLS NOT DISTINCT)
  o_estensione_civico := NULLIF(UPPER(BTRIM(p_estensione)), '');
  o_palazzina         := NULLIF(UPPER(BTRIM(p_palazzina)), '');
  o_scala             := NULLIF(UPPER(BTRIM(p_scala)), '');
  o_piano             := NULLIF(UPPER(BTRIM(p_piano)), '');
  o_interno           := NULLIF(UPPER(BTRIM(p_interno)), '');

  -- 3. Prefisso '/' su estensione
  IF o_estensione_civico IS NOT NULL
     AND LEFT(o_estensione_civico, 1) <> '/' THEN
    o_estensione_civico := '/' || o_estensione_civico;
  END IF;

  -- 4. Civico norm: SNC = civico NULL (il civico <= 0 lo rifiuta
  --    il guard trgfn_indirizzi_dettaglio_guard_chiave)
  IF p_civico IS NOT NULL THEN
    o_civico_norm := p_civico::text || COALESCE(o_estensione_civico, '');
  ELSE
    o_civico_norm := 'SNC';
  END IF;

  -- 5. Indirizzo normalizzato
  o_indirizzo_normalizzato := TRIM(BOTH ' ' FROM (
      o_via_norm
    || ', ' || o_civico_norm
    || CASE WHEN o_palazzina IS NOT NULL THEN ', Pal.'   || o_palazzina ELSE '' END
    || CASE WHEN o_scala     IS NOT NULL THEN ', Scala ' || o_scala     ELSE '' END
    || CASE WHEN o_piano     IS NOT NULL THEN ', Piano ' || o_piano     ELSE '' END
    || CASE WHEN o_interno   IS NOT NULL THEN ', Int.'   || o_interno   ELSE '' END
  ));
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_build_indirizzo_normalizzato(p_stradario_id integer, p_civico integer, p_estensione character varying, p_palazzina character varying, p_scala character varying, p_piano character varying, p_interno character varying, OUT o_estensione_civico character varying, OUT o_palazzina character varying, OUT o_scala character varying, OUT o_piano character varying, OUT o_interno character varying, OUT o_via_norm text, OUT o_civico_norm text, OUT o_indirizzo_normalizzato text)
IS 'Centralizza TUTTA la logica di normalizzazione indirizzi. Ritorna record con colonne strutturali normalizzate (UPPER+BTRIM, vuoto -> NULL, prefisso / sull''estensione) + via_norm + civico_norm (SNC = civico NULL) + indirizzo_normalizzato. Via non risolta in script.vw_indirizzo_completo: tutti gli OUT NULL. Usata dal trigger trgfn_indirizzi_dettaglio_normalize, dal BB fn_get_or_create_indirizzo_dettaglio (lookup coi valori come li salva il trigger) e da script.fn_check_indirizzo_duplicato. Rev 2026-10-25 (20261025-23, brief-db-unicita-civico-indirizzi-dettaglio D2-a e D3-a): vuoto -> NULL, ritirato il ramo civico = 0 vale SNC.';
```

</div>

---
{% include-markdown "signature-core.md" %}
