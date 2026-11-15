# ⚙️ Funzione `fn_check_copia_indirizzo_ruolo`

```sql
CREATE FUNCTION fn_check_copia_indirizzo_ruolo(p_indirizzo_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_check_copia_indirizzo_ruolo(p_indirizzo_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    c_chi     CONSTANT text := 'anagrafiche.fn_check_copia_indirizzo_ruolo';
    v_ruolo   anagrafiche.indirizzi.soggetto_ruolo_id%TYPE;
    v_istanza anagrafiche.indirizzi.istanza_utility_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   I motivi per cui l'indirizzo del ruolo non si puo' copiare
    --   in nessun tipo, nel suo ruolo e nella sua istanza.
    --   [] = la copia si puo' proporre.
    -- =========================================================
    IF p_indirizzo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_indirizzo_id'),
            NULL::uuid,
            c_chi,
            'manca l''indirizzo');
    END IF;

    SELECT i.soggetto_ruolo_id, i.istanza_utility_id
      INTO v_ruolo, v_istanza
      FROM anagrafiche.indirizzi i
     WHERE i.id = p_indirizzo_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_INDIRIZZO_RUOLO_NON_TROVATO',
            jsonb_build_object('indirizzo_id', p_indirizzo_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- ---- nessun tipo in cui copiarlo, sulla chiave della riga -
    IF NOT EXISTS (SELECT 1
                     FROM anagrafiche.fn_tipi_indirizzo_proponibili_ruolo(v_ruolo, v_istanza) t
                    WHERE t.ammesso) THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_INDIRIZZO_COPIA_NESSUN_TIPO',
            'reason',     'NESSUN_TIPO_PROPONIBILE',
            'reason_key', 'anagrafiche.indirizzi.copia_blocco.nessun_tipo_proponibile',
            'dettaglio',  jsonb_build_object(
                              'indirizzo_id',       p_indirizzo_id,
                              'soggetto_ruolo_id',  v_ruolo,
                              'istanza_utility_id', v_istanza),
            'valori',     jsonb_build_array()));
    END IF;

    RETURN '[]'::jsonb;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_check_copia_indirizzo_ruolo(p_indirizzo_id bigint)
IS 'Il motivo di riga dell''azione «Copia come…» su un indirizzo del ruolo: check pura, array ordinato di {codice, reason, reason_key, dettaglio, valori}, [] se la copia si puo'' proporre. Un motivo: nessun tipo in cui copiarlo (NESSUN_TIPO_PROPONIBILE, E_INDIRIZZO_COPIA_NESSUN_TIPO, chiave anagrafiche.indirizzi.copia_blocco.nessun_tipo_proponibile, senza valori), quando anagrafiche.fn_tipi_indirizzo_proponibili_ruolo non ha un tipo ammesso sulla chiave (ruolo, istanza) della riga: la copia resta nel ruolo e nell''istanza della sorgente. Indirizzo mancante E_SCRIPT_CHIAMATA_NON_VALIDA, inesistente E_INDIRIZZO_RUOLO_NON_TROVATO. La chiamano il verbo anagrafiche.fn_copia_indirizzo_ruolo, che ne solleva il primo motivo, e la vista di riga anagrafiche.vw_indirizzi_ruolo_azioni. Gemella di anagrafiche.fn_check_copia_indirizzo_soggetto. SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
