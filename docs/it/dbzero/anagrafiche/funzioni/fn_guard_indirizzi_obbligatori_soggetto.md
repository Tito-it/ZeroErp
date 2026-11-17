# ⚙️ Funzione `fn_guard_indirizzi_obbligatori_soggetto`

```sql
CREATE FUNCTION fn_guard_indirizzi_obbligatori_soggetto(p_soggetto_id uuid, p_tx_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_indirizzi_obbligatori_soggetto(p_soggetto_id uuid, p_tx_id uuid)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    c_chi         CONSTANT text := 'anagrafiche.fn_guard_indirizzi_obbligatori_soggetto';
    v_natura_id   anagrafiche.soggetti.tipo_soggetto_dettaglio_id%TYPE;
    v_tipo_id     config.tipi_soggetto_dettaglio_tipi_indirizzo.tipo_indirizzo_id%TYPE;
    v_ripiego_id  config.tipi_soggetto_dettaglio_tipi_indirizzo.fallback_tipo_indirizzo_id%TYPE;
    v_natura_nome config.tipi_soggetto_dettaglio.descrizione%TYPE;
BEGIN
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('soggetto_id', p_soggetto_id),
            p_tx_id,
            c_chi,
            'il soggetto da controllare non e'' indicato');
    END IF;

    SELECT s.tipo_soggetto_dettaglio_id
      INTO v_natura_id
      FROM anagrafiche.soggetti s
     WHERE s.id = p_soggetto_id;

    -- Il soggetto non c'e' piu' (cancellato nella stessa
    -- transazione), o non ha natura: niente da pretendere.
    IF NOT FOUND OR v_natura_id IS NULL THEN
        RETURN;
    END IF;

    SELECT m.tipo_indirizzo_id, m.ripiego_tipo_indirizzo_id
      INTO v_tipo_id, v_ripiego_id
      FROM anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto(
               p_soggetto_id, v_natura_id, script.fn_data_operativa()) m
     ORDER BY m.tipo_indirizzo_id
     LIMIT 1;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    SELECT COALESCE(tsd.descrizione, tsd.codice_interno) INTO v_natura_nome
      FROM config.tipi_soggetto_dettaglio tsd
     WHERE tsd.id = v_natura_id;

    -- Codice PROPRIO di questo layer (giro 3). Valori per
    -- descrizione, nell'ordine della frase: la natura, poi il tipo
    -- richiesto col suo ripiego. Gli id nel contesto.
    PERFORM script.fn_log_and_raise_error(
        'anagrafiche', c_chi, 'E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO',
        jsonb_build_object(
            'soggetto_id',                p_soggetto_id,
            'tipo_soggetto_dettaglio_id', v_natura_id,
            'tipo_indirizzo_id_required', v_tipo_id,
            'fallback_tipo_indirizzo_id', v_ripiego_id),
        p_tx_id,
        COALESCE(v_natura_nome, v_natura_id::text),
        COALESCE(anagrafiche.fn_nomi_tipo_indirizzo_richiesto(v_tipo_id, v_ripiego_id),
                 v_tipo_id::text));
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_guard_indirizzi_obbligatori_soggetto(p_soggetto_id uuid, p_tx_id uuid)
IS 'Guard: il soggetto deve avere, fra i suoi indirizzi (anagrafiche.indirizzi_soggetti), ogni tipo che config.tipi_soggetto_dettaglio_tipi_indirizzo dichiara obbligatorio per la sua natura, in una riga attiva e valida il giorno di script.fn_data_operativa() (anagrafiche.fn_tipo_indirizzo_ammesso_per_natura), oppure il ripiego della riga: i mancanti li dice anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto, sulla natura del soggetto. Al primo mancante, per tipo, E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO coi valori della frase nell''ordine natura e tipo richiesto col ripiego, per descrizione (anagrafiche.fn_nomi_tipo_indirizzo_richiesto); gli id nel contesto. Natura NULL, o soggetto che non esiste (cancellato nella stessa transazione): tace. Id NULL: E_SCRIPT_CHIAMATA_NON_VALIDA. Il tx_id va al log dell''errore. Sede unica del controllo del layer SOGGETTO: la chiamano i constraint trigger differiti di anagrafiche.soggetti (anagrafiche.trgfn_soggetti_guard_indirizzi_required) e di anagrafiche.indirizzi_soggetti (anagrafiche.trgfn_indirizzi_soggetti_guard_obbligatori_soggetto). Gemello di anagrafiche.fn_guard_indirizzi_obbligatori_ruolo, il layer RUOLO. SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
