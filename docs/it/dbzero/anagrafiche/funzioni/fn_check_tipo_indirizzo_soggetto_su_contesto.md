# ⚙️ Funzione `fn_check_tipo_indirizzo_soggetto_su_contesto`

```sql
CREATE FUNCTION fn_check_tipo_indirizzo_soggetto_su_contesto(p_tipo_soggetto_dettaglio_id bigint, p_tipi_presenti integer[], p_tipo_indirizzo_id integer, p_oggi date, p_soggetto_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto(p_tipo_soggetto_dettaglio_id bigint, p_tipi_presenti integer[], p_tipo_indirizzo_id integer, p_oggi date, p_soggetto_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    c_chi        CONSTANT text := 'anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto';
    v_motivi     jsonb := '[]'::jsonb;
    v_tipo_nome  config.tipi_indirizzi.descrizione%TYPE;
    v_natura_nome config.tipi_soggetto_dettaglio.descrizione%TYPE;
    v_dettaglio  jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   I motivi per cui il tipo di indirizzo non si puo'
    --   scrivere su un soggetto con questo contesto: la natura
    --   e i tipi che il soggetto ha gia'. [] = ammesso.
    --
    -- Regole:
    --   - l'ordine dell'array e' il contratto: la madre solleva
    --     il primo (§12.5.2);
    --   - il predicato della natura e' quello del guard
    --     (fn_tipo_indirizzo_ammesso_per_natura), sul giorno
    --     passato dal chiamante;
    --   - soggetto NULL: il soggetto non esiste ancora (picker
    --     in creazione); conta solo per il dettaglio.
    -- =========================================================
    IF p_tipo_indirizzo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_tipo_indirizzo_id'),
            NULL::uuid,
            c_chi,
            'manca il tipo di indirizzo');
    END IF;

    IF p_oggi IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_oggi'),
            NULL::uuid,
            c_chi,
            'manca il giorno');
    END IF;

    SELECT ti.descrizione INTO v_tipo_nome
      FROM config.tipi_indirizzi ti
     WHERE ti.id = p_tipo_indirizzo_id;
    v_tipo_nome := COALESCE(v_tipo_nome, p_tipo_indirizzo_id::text);

    v_dettaglio := jsonb_build_object(
        'tipo_indirizzo_id',          p_tipo_indirizzo_id,
        'tipo_soggetto_dettaglio_id', p_tipo_soggetto_dettaglio_id,
        'soggetto_id',                p_soggetto_id);

    -- ---- 1. il soggetto ha gia' un indirizzo di quel tipo ----
    IF p_tipo_indirizzo_id = ANY (COALESCE(p_tipi_presenti, '{}'::integer[])) THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE',
            'reason',     'TIPO_GIA_PRESENTE',
            'reason_key', 'anagrafiche.indirizzi.tipo_blocco.gia_presente',
            'dettaglio',  v_dettaglio,
            'valori',     jsonb_build_array(v_tipo_nome));
    END IF;

    -- ---- 2. la natura non ammette il tipo -------------------
    IF NOT anagrafiche.fn_tipo_indirizzo_ammesso_per_natura(
               p_tipo_soggetto_dettaglio_id, p_tipo_indirizzo_id, p_oggi) THEN
        SELECT COALESCE(tsd.descrizione, tsd.codice_interno) INTO v_natura_nome
          FROM config.tipi_soggetto_dettaglio tsd
         WHERE tsd.id = p_tipo_soggetto_dettaglio_id;
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO',
            'reason',     'TIPO_NON_AMMESSO_DALLA_NATURA',
            'reason_key', 'anagrafiche.indirizzi.tipo_blocco.non_ammesso_dalla_natura',
            'dettaglio',  v_dettaglio,
            'valori',     jsonb_build_array(
                              COALESCE(v_natura_nome, p_tipo_soggetto_dettaglio_id::text),
                              v_tipo_nome));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto(p_tipo_soggetto_dettaglio_id bigint, p_tipi_presenti integer[], p_tipo_indirizzo_id integer, p_oggi date, p_soggetto_id uuid)
IS 'I motivi per cui un tipo di indirizzo non si puo'' scrivere su un soggetto, dato il contesto: la natura di dettaglio, i tipi che il soggetto ha gia'', il giorno. Check pura: array ordinato di {codice, reason, reason_key, dettaglio, valori}, [] se ammesso. In ordine: il tipo gia'' presente (TIPO_GIA_PRESENTE, E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE, chiave anagrafiche.indirizzi.tipo_blocco.gia_presente; valori: il tipo); il tipo che la natura non ammette (TIPO_NON_AMMESSO_DALLA_NATURA, E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO, chiave anagrafiche.indirizzi.tipo_blocco.non_ammesso_dalla_natura; valori: la natura e il tipo, nell''ordine della frase), col predicato di anagrafiche.fn_tipo_indirizzo_ammesso_per_natura. Il soggetto serve solo al dettaglio: NULL quando il soggetto non esiste ancora. Tipo o giorno mancanti: E_SCRIPT_CHIAMATA_NON_VALIDA. La compone anagrafiche.fn_check_tipo_indirizzo_soggetto, che legge il contesto dal soggetto salvato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
