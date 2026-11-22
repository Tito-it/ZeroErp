{% include-markdown "it/dbzero/anagrafiche/manual/fn_check_tipo_indirizzo_soggetto.md" %}
# ⚙️ Funzione `fn_check_tipo_indirizzo_soggetto`

```sql
CREATE FUNCTION fn_check_tipo_indirizzo_soggetto(p_soggetto_id uuid, p_tipo_indirizzo_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_check_tipo_indirizzo_soggetto(p_soggetto_id uuid, p_tipo_indirizzo_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    c_chi    CONSTANT text := 'anagrafiche.fn_check_tipo_indirizzo_soggetto';
    v_natura anagrafiche.soggetti.tipo_soggetto_dettaglio_id%TYPE;
    v_motivi jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   I motivi per cui il tipo di indirizzo non si puo'
    --   scrivere sul soggetto salvato. Legge il contesto (la
    --   natura, i tipi presenti) e lo passa alla meta' sui
    --   motivi; il giorno e' script.fn_data_operativa(), quello
    --   del guard della tabella.
    -- =========================================================
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_soggetto_id'),
            NULL::uuid,
            c_chi,
            'manca il soggetto');
    END IF;

    SELECT s.tipo_soggetto_dettaglio_id
      INTO v_natura
      FROM anagrafiche.soggetti s
     WHERE s.id = p_soggetto_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SOGGETTO_NOT_FOUND',
            jsonb_build_object('soggetto_id', p_soggetto_id),
            NULL::uuid,
            p_soggetto_id::text);
    END IF;

    -- ⚠️ La delega si scrive come assegnazione (:=): e' la forma che
    --   dbops.vw_funzioni_check_codici sa leggere per legare i codici.
    v_motivi := anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto(
        v_natura,
        ARRAY(SELECT i.tipo_indirizzo_id
                FROM anagrafiche.indirizzi_soggetti i
               WHERE i.soggetto_id = p_soggetto_id),
        p_tipo_indirizzo_id,
        script.fn_data_operativa(),
        p_soggetto_id);

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_check_tipo_indirizzo_soggetto(p_soggetto_id uuid, p_tipo_indirizzo_id integer)
IS 'I motivi per cui il tipo di indirizzo non si puo'' scrivere sul soggetto salvato: legge la natura e i tipi che il soggetto ha gia'' e li passa a anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto, col giorno di script.fn_data_operativa() (quello del guard della tabella). Array ordinato di motivi, [] se ammesso: il tipo gia'' presente (E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE), poi il tipo che la natura non ammette (E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO). Soggetto mancante E_SCRIPT_CHIAMATA_NON_VALIDA, inesistente E_SOGGETTO_NOT_FOUND. SECURITY INVOKER: i tipi presenti sono quelli che chi chiama vede. La chiama anagrafiche.fn_crea_indirizzo_soggetto, che solleva il primo motivo prima di scrivere.';
```

</div>

---
{% include-markdown "signature-core.md" %}
