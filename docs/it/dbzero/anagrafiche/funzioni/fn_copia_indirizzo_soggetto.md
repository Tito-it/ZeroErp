# ⚙️ Funzione `fn_copia_indirizzo_soggetto`

```sql
CREATE FUNCTION fn_copia_indirizzo_soggetto(p_soggetto_id uuid, p_indirizzo_soggetto_id bigint, p_tipi_indirizzo_codice_interno text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_copia_indirizzo_soggetto(p_soggetto_id uuid, p_indirizzo_soggetto_id bigint, p_tipi_indirizzo_codice_interno text[])
 RETURNS bigint[]
 LANGUAGE plpgsql
AS $function$
DECLARE
    c_chi    CONSTANT text := 'anagrafiche.fn_copia_indirizzo_soggetto';
    v_src    record;  -- la riga sorgente, da una SELECT statica
    v_el     jsonb;
    v_codice config.tipi_indirizzi.codice_interno%TYPE;
    v_ids    bigint[] := '{}';  -- vedi RETURNS
BEGIN
    -- =========================================================
    -- Scopo:
    --   Copiare un indirizzo del soggetto in uno o piu' tipi: la
    --   stessa riga col tipo sostituito. Ritorna gli id nuovi,
    --   nell'ordine dei tipi. Tutto o niente.
    -- =========================================================
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_soggetto_id'),
            NULL::uuid,
            c_chi,
            'manca il soggetto');
    END IF;
    IF p_indirizzo_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_indirizzo_soggetto_id'),
            NULL::uuid,
            c_chi,
            'manca l''indirizzo da copiare');
    END IF;
    IF COALESCE(cardinality(p_tipi_indirizzo_codice_interno), 0) = 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_tipi_indirizzo_codice_interno'),
            NULL::uuid,
            c_chi,
            'manca il tipo di destinazione');
    END IF;

    -- 1. La sorgente, di quel soggetto.
    SELECT isg.indirizzo_dettaglio_id, isg.indirizzo_libero, isg.stato_id,
           isg.comune_id, isg.codice_postale_id, isg.administrative_area,
           isg.locality, isg.sublocality, isg.postal_code
      INTO v_src
      FROM anagrafiche.indirizzi_soggetti isg
     WHERE isg.id = p_indirizzo_soggetto_id
       AND isg.soggetto_id = p_soggetto_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_INDIRIZZO_SOGGETTO_NON_TROVATO',
            jsonb_build_object('soggetto_id', p_soggetto_id,
                               'indirizzo_soggetto_id', p_indirizzo_soggetto_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 2. Il motivo di riga: quello che la vista mostra spento.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'anagrafiche', c_chi,
        anagrafiche.fn_check_copia_indirizzo_soggetto(p_indirizzo_soggetto_id));

    -- 3. Una riga per tipo, dalla singolare.
    v_el := anagrafiche.fn_indirizzo_elemento_da_riga(
                v_src.indirizzo_dettaglio_id, v_src.indirizzo_libero, v_src.stato_id,
                v_src.comune_id, v_src.codice_postale_id, v_src.administrative_area,
                v_src.locality, v_src.sublocality, v_src.postal_code);

    FOREACH v_codice IN ARRAY p_tipi_indirizzo_codice_interno LOOP
        v_ids := v_ids || anagrafiche.fn_crea_indirizzo_soggetto(
                     p_soggetto_id,
                     v_el || jsonb_build_object('tipo_indirizzo_codice_interno', v_codice));
    END LOOP;

    RETURN v_ids;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_copia_indirizzo_soggetto(p_soggetto_id uuid, p_indirizzo_soggetto_id bigint, p_tipi_indirizzo_codice_interno text[])
IS 'Verbo: copia un indirizzo del soggetto in uno o piu'' tipi (codici interni, nell''ordine dato), tutto o niente, e ritorna gli id delle righe nuove nello stesso ordine. La sorgente dev''essere del soggetto (E_INDIRIZZO_SOGGETTO_NON_TROVATO). Solleva il primo motivo di anagrafiche.fn_check_copia_indirizzo_soggetto (E_INDIRIZZO_COPIA_NESSUN_TIPO), quello della vista di riga anagrafiche.vw_indirizzi_soggetti_azioni. Ogni riga la scrive la singolare anagrafiche.fn_crea_indirizzo_soggetto con l''elemento di anagrafiche.fn_indirizzo_elemento_da_riga e il tipo: tipo inesistente E_TIPO_INDIRIZZO_NON_TROVATO, gia'' presente (anche ripetuto nell''elenco) E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE, non ammesso dalla natura E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO, e i guard della tabella. Soggetto, indirizzo o elenco mancanti o vuoti: E_SCRIPT_CHIAMATA_NON_VALIDA. Il permesso lo controlla il backend. SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
