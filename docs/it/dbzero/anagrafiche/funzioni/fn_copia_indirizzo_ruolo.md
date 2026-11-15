# ⚙️ Funzione `fn_copia_indirizzo_ruolo`

```sql
CREATE FUNCTION fn_copia_indirizzo_ruolo(p_soggetto_ruolo_id bigint, p_indirizzo_id bigint, p_tipi_indirizzo_codice_interno text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_copia_indirizzo_ruolo(p_soggetto_ruolo_id bigint, p_indirizzo_id bigint, p_tipi_indirizzo_codice_interno text[])
 RETURNS bigint[]
 LANGUAGE plpgsql
AS $function$
DECLARE
    c_chi    CONSTANT text := 'anagrafiche.fn_copia_indirizzo_ruolo';
    v_src    record;  -- la riga sorgente, da una SELECT statica
    v_el     jsonb;
    v_codice config.tipi_indirizzi.codice_interno%TYPE;
    v_ids    bigint[] := '{}';  -- vedi RETURNS
BEGIN
    -- =========================================================
    -- Scopo:
    --   Copiare un indirizzo del ruolo in uno o piu' tipi, nello
    --   stesso ruolo e nella stessa istanza. Ritorna gli id nuovi,
    --   nell'ordine dei tipi. Tutto o niente.
    -- =========================================================
    IF NOT EXISTS (SELECT 1 FROM anagrafiche.soggetti_ruoli sr
                    WHERE sr.id = p_soggetto_ruolo_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SOGGETTO_RUOLO_NON_TROVATO',
            jsonb_build_object('soggetto_ruolo_id', p_soggetto_ruolo_id),
            NULL::uuid,
            COALESCE(p_soggetto_ruolo_id::text, '-'));
    END IF;
    IF p_indirizzo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_indirizzo_id'),
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

    -- 1. La sorgente, di quel ruolo.
    SELECT i.istanza_utility_id,
           i.indirizzo_dettaglio_id, i.indirizzo_libero, i.stato_id,
           i.comune_id, i.codice_postale_id, i.administrative_area,
           i.locality, i.sublocality, i.postal_code
      INTO v_src
      FROM anagrafiche.indirizzi i
     WHERE i.id = p_indirizzo_id
       AND i.soggetto_ruolo_id = p_soggetto_ruolo_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_INDIRIZZO_RUOLO_NON_TROVATO',
            jsonb_build_object('soggetto_ruolo_id', p_soggetto_ruolo_id,
                               'indirizzo_id', p_indirizzo_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 2. Il motivo di riga: quello che la vista mostra spento.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'anagrafiche', c_chi,
        anagrafiche.fn_check_copia_indirizzo_ruolo(p_indirizzo_id));

    -- 3. Una riga per tipo, dalla singolare, nella stessa istanza.
    v_el := anagrafiche.fn_indirizzo_elemento_da_riga(
                v_src.indirizzo_dettaglio_id, v_src.indirizzo_libero, v_src.stato_id,
                v_src.comune_id, v_src.codice_postale_id, v_src.administrative_area,
                v_src.locality, v_src.sublocality, v_src.postal_code)
            || jsonb_strip_nulls(jsonb_build_object(
                   'istanza_utility_id', v_src.istanza_utility_id));

    FOREACH v_codice IN ARRAY p_tipi_indirizzo_codice_interno LOOP
        v_ids := v_ids || anagrafiche.fn_crea_indirizzo_ruolo(
                     p_soggetto_ruolo_id,
                     v_el || jsonb_build_object('tipo_indirizzo_codice_interno', v_codice));
    END LOOP;

    RETURN v_ids;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_copia_indirizzo_ruolo(p_soggetto_ruolo_id bigint, p_indirizzo_id bigint, p_tipi_indirizzo_codice_interno text[])
IS 'Verbo: copia un indirizzo del ruolo in uno o piu'' tipi (codici interni, nell''ordine dato), nello stesso ruolo e nella stessa istanza della sorgente, tutto o niente, e ritorna gli id delle righe nuove nello stesso ordine. Ruolo inesistente E_SOGGETTO_RUOLO_NON_TROVATO; la sorgente dev''essere del ruolo (E_INDIRIZZO_RUOLO_NON_TROVATO). Solleva il primo motivo di anagrafiche.fn_check_copia_indirizzo_ruolo (E_INDIRIZZO_COPIA_NESSUN_TIPO), quello della vista di riga anagrafiche.vw_indirizzi_ruolo_azioni. Ogni riga la scrive la singolare anagrafiche.fn_crea_indirizzo_ruolo con l''elemento di anagrafiche.fn_indirizzo_elemento_da_riga, l''istanza della sorgente e il tipo: tipo inesistente E_TIPO_INDIRIZZO_NON_TROVATO, gia'' presente sulla chiave (anche ripetuto nell''elenco) E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE, non ammesso dal tipo di ruolo E_TIPO_INDIRIZZO_NON_PERMESSO, e i guard della tabella. Indirizzo o elenco mancanti o vuoti: E_SCRIPT_CHIAMATA_NON_VALIDA. La copia fra layer (soggetto e ruolo) non e'' di questo verbo. Il permesso lo controlla il backend. SECURITY INVOKER. Gemello di anagrafiche.fn_copia_indirizzo_soggetto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
