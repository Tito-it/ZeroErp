# ⚙️ Funzione `fn_fuso_operativo`

```sql
CREATE FUNCTION fn_fuso_operativo()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_fuso_operativo()
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- ⚠️ %TYPE e non `text` nudo: il tipo lo decide la colonna
    --    che lo contiene, non questa funzione.
    v_fuso  config.parameters.default_value%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il NOME del fuso dell'azienda. Sede unica: chi deve
    --   passare fra un istante e il calendario lo chiede qui.
    --
    -- Regole:
    --   - il fuso e' un DATO (config.parameters), mai una
    --     costante nel codice;
    --   - il fuso si VALIDA QUANDO SI SCRIVE (registro
    --     config.parameter_fk_surrogate ->
    --     pg_timezone_names): qui non lo si rilegge a ogni
    --     chiamata, perche' costa ~8 ms e i chiamanti stanno
    --     dentro viste lette per riga;
    --   - fail-loud su tutte e tre le forme di guasto: assente,
    --     vuoto, non riconosciuto. Mai un ripiego a UTC.
    -- =========================================================

    -- ⛔ Si legge il default NUDO e non script.fn_get_parameter_full:
    --    la cascata di override (utente/gruppo/sessione/emittente)
    --    farebbe dare allo STESSO fatto giorni diversi a seconda di
    --    chi lo guarda.
    SELECT p.default_value
      INTO v_fuso
      FROM config.parameters p
     WHERE p.code = 'SYSTEM_FUSO_ORARIO';

    -- 1) Assente, oppure presente e vuoto.
    --    ⚠️ Il vuoto passa il registro (che lo ammette per tutti i
    --    parametri, 20260831-36): si ferma qui.
    IF v_fuso IS NULL OR btrim(v_fuso) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_fuso_operativo', 'E_CONFIG_MANCANTE',
            jsonb_build_object('code', 'SYSTEM_FUSO_ORARIO',
                               'valore', v_fuso),
            NULL::uuid,
            'SYSTEM_FUSO_ORARIO');
    END IF;

    v_fuso := btrim(v_fuso);

    -- 2) C'e' ed e' pieno, ma il sistema non lo riconosce.
    --    ⭐ Rete di sicurezza, non il controllo principale: la
    --    validita' la decide il registro alla scrittura. Qui
    --    arriva solo un nome sparito dall'archivio dei fusi del
    --    sistema operativo, o un valore scritto con la riga del
    --    registro spenta.
    --    ⛔ Senza, `AT TIME ZONE` alza un 22023 grezzo nel
    --    chiamante: il contratto «P0001 + CONSTRAINT = errore di
    --    dominio» salta e il guasto arriva al backend come 500
    --    non tradotto.
    BEGIN
        -- La prova e' l'espressione stessa: il risultato non serve.
        PERFORM now() AT TIME ZONE v_fuso;
    EXCEPTION
        WHEN invalid_parameter_value THEN
            PERFORM script.fn_log_and_raise_error(
                'script', 'fn_fuso_operativo', 'E_CONFIG_MANCANTE',
                jsonb_build_object('code', 'SYSTEM_FUSO_ORARIO',
                                   'valore', v_fuso),
                NULL::uuid,
                concat('SYSTEM_FUSO_ORARIO = ', quote_literal(v_fuso),
                       ' (fuso orario non riconosciuto)'));
    END;

    RETURN v_fuso;
END;
$function$

COMMENT ON FUNCTION script.fn_fuso_operativo()
IS 'Il NOME del fuso dell''azienda (config.parameters.SYSTEM_FUSO_ORARIO). ⭐ SEDE UNICA della lettura e della validazione del fuso (brief-be-db-fe-un-solo-fuso-aziendale D-1, 20261009-40): la usano fn_data_operativa (che giorno e'' oggi), fn_inizio_giorno_operativo (quando comincia il giorno D), fn_giorno_operativo (in che giorno cade un istante) e il backend (ore a video). Nessun altro legge il parametro. ⛔ Legge il default NUDO e non script.fn_get_parameter_full: la cascata di override darebbe allo stesso fatto giorni diversi secondo chi lo guarda. ⛔ FAIL-LOUD su tre condizioni, tutte con E_CONFIG_MANCANTE: parametro assente, valore vuoto (il registro ammette il vuoto), valore che il sistema non riconosce (rete di sicurezza EXCEPTION sul 22023 di AT TIME ZONE). La validita'' del nome la decide il registro config.parameter_fk_surrogate alla scrittura (riga 7 -> pg_timezone_names): qui non si rilegge pg_timezone_names, che costa ~8 ms. Mai un ripiego a UTC. ℹ️ STABLE: il parametro non cambia dentro un''istruzione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
