{% include-markdown "it/dbzero/anagrafiche/manual/fn_check_copia_indirizzo_soggetto.md" %}
# ⚙️ Funzione `fn_check_copia_indirizzo_soggetto`

```sql
CREATE FUNCTION fn_check_copia_indirizzo_soggetto(p_indirizzo_soggetto_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_check_copia_indirizzo_soggetto(p_indirizzo_soggetto_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    c_chi      CONSTANT text := 'anagrafiche.fn_check_copia_indirizzo_soggetto';
    v_soggetto anagrafiche.indirizzi_soggetti.soggetto_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   I motivi per cui l'indirizzo del soggetto non si puo'
    --   copiare in nessun tipo. [] = la copia si puo' proporre.
    --
    -- Regole:
    --   - nessun tipo proponibile: lo dice il picker del soggetto,
    --     che legge la check della madre singolare;
    --   - il verbo della copia la chiama e solleva il primo
    --     motivo (§12.5.2); la vista di riga ne espone il motivo.
    -- =========================================================
    IF p_indirizzo_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_indirizzo_soggetto_id'),
            NULL::uuid,
            c_chi,
            'manca l''indirizzo');
    END IF;

    SELECT isg.soggetto_id
      INTO v_soggetto
      FROM anagrafiche.indirizzi_soggetti isg
     WHERE isg.id = p_indirizzo_soggetto_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_INDIRIZZO_SOGGETTO_NON_TROVATO',
            jsonb_build_object('indirizzo_soggetto_id', p_indirizzo_soggetto_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- ---- nessun tipo in cui copiarlo -------------------------
    IF NOT EXISTS (SELECT 1
                     FROM anagrafiche.fn_tipi_indirizzo_proponibili_soggetto(v_soggetto) t
                    WHERE t.ammesso) THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_INDIRIZZO_COPIA_NESSUN_TIPO',
            'reason',     'NESSUN_TIPO_PROPONIBILE',
            'reason_key', 'anagrafiche.indirizzi.copia_blocco.nessun_tipo_proponibile',
            'dettaglio',  jsonb_build_object(
                              'indirizzo_soggetto_id', p_indirizzo_soggetto_id,
                              'soggetto_id',           v_soggetto),
            'valori',     jsonb_build_array()));
    END IF;

    RETURN '[]'::jsonb;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_check_copia_indirizzo_soggetto(p_indirizzo_soggetto_id bigint)
IS 'Il motivo di riga dell''azione «Copia come…» su un indirizzo del soggetto: check pura, array ordinato di {codice, reason, reason_key, dettaglio, valori}, [] se la copia si puo'' proporre. Un motivo: nessun tipo in cui copiarlo (NESSUN_TIPO_PROPONIBILE, E_INDIRIZZO_COPIA_NESSUN_TIPO, chiave anagrafiche.indirizzi.copia_blocco.nessun_tipo_proponibile, senza valori), quando anagrafiche.fn_tipi_indirizzo_proponibili_soggetto non ha un tipo ammesso. Indirizzo mancante E_SCRIPT_CHIAMATA_NON_VALIDA, inesistente E_INDIRIZZO_SOGGETTO_NON_TROVATO. La chiamano il verbo anagrafiche.fn_copia_indirizzo_soggetto, che ne solleva il primo motivo, e la vista di riga anagrafiche.vw_indirizzi_soggetti_azioni (colonne copia_blocco_reason, copia_blocco_reason_key). SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
