{% include-markdown "it/dbzero/script/manual/fn_data_operativa.md" %}
# ⚙️ Funzione `fn_data_operativa`

```sql
CREATE FUNCTION fn_data_operativa()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_data_operativa()
 RETURNS date
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- ⚠️ %TYPE e non `text` nudo: il tipo lo decide la colonna
    --    che lo contiene, non questa funzione.
    v_fuso config.parameters.default_value%TYPE;
    v_oggi date;
BEGIN
    -- =========================================================
    -- Scopo:
    --   La data di oggi NEL FUSO DELL'AZIENDA, non in quello
    --   della sessione. Sostituisce current_date sul percorso
    --   della data documento.
    --
    -- Regole:
    --   - il fuso e' un DATO (config.parameters), mai una
    --     costante nel codice;
    --   - il fuso si VALIDA QUANDO SI SCRIVE (registro
    --     config.parameter_fk_surrogate ->
    --     pg_timezone_names): qui non lo si rilegge a ogni
    --     chiamata, perche' costa ~8 ms e questa funzione sta
    --     dentro viste lette per riga;
    --   - fail-loud su tutte e tre le forme di guasto: assente,
    --     vuoto, non riconosciuto. Mai un ripiego a UTC.
    -- =========================================================

    -- ⛔ Si legge il default NUDO e non script.fn_get_parameter_full:
    --    la cascata di override (utente/gruppo/sessione/emittente)
    --    farebbe dare alla STESSA fattura date diverse a seconda di
    --    chi la genera, cioe' il difetto che questa funzione chiude.
    SELECT p.default_value
      INTO v_fuso
      FROM config.parameters p
     WHERE p.code = 'SYSTEM_FUSO_ORARIO';

    -- 1) Assente, oppure presente e vuoto.
    --    ⚠️ Il vuoto passa il registro (che lo ammette per tutti i
    --    parametri, 20260831-36): si ferma qui.
    IF v_fuso IS NULL OR btrim(v_fuso) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_data_operativa', 'E_CONFIG_MANCANTE',
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
    --    ⛔ Senza, `AT TIME ZONE` alza un 22023 grezzo: il
    --    contratto «P0001 + CONSTRAINT = errore di dominio» salta
    --    e il guasto arriva al backend come 500 non tradotto.
    BEGIN
        -- ℹ️ now() e' l'istante di inizio transazione: dentro la
        --    stessa transazione la risposta e' per costruzione
        --    identica, ed e' il motivo per cui la funzione e' STABLE.
        v_oggi := (now() AT TIME ZONE v_fuso)::date;
    EXCEPTION
        WHEN invalid_parameter_value THEN
            PERFORM script.fn_log_and_raise_error(
                'script', 'fn_data_operativa', 'E_CONFIG_MANCANTE',
                jsonb_build_object('code', 'SYSTEM_FUSO_ORARIO',
                                   'valore', v_fuso),
                NULL::uuid,
                concat('SYSTEM_FUSO_ORARIO = ', quote_literal(v_fuso),
                       ' (fuso orario non riconosciuto)'));
    END;

    RETURN v_oggi;
END;
$function$

COMMENT ON FUNCTION script.fn_data_operativa()
IS 'La data di oggi NEL FUSO DELL''AZIENDA (config.parameters.SYSTEM_FUSO_ORARIO), non in quello della sessione. ⛔ Sostituisce current_date sul percorso della data documento: current_date segue il fuso della SESSIONE, e la sessione di Django e'' UTC (USE_TZ senza TIME_ZONE in DATABASES) mentre psql e pgAgent sono Europe/Rome — lo stesso oggetto dava due date diverse secondo il canale, e ogni documento nato fra mezzanotte e le 02:00 locali portava la data del giorno prima (misurato 2026-08-25: 7 fatture su 18 sfasate). ⭐ IL FUSO SI VALIDA QUANDO SI SCRIVE (rev 2026-10-08, 20261008-40): il registro config.parameter_fk_surrogate (riga 7) vuole il valore in pg_timezone_names e lo rifiuta alla scrittura con E_PARAMETER_DEFAULT_VALUE_INVALID. Qui non lo si rilegge piu'' a ogni chiamata: pg_timezone_names rilegge dal disco l''archivio dei fusi (~8 ms), e questa funzione sta dentro viste lette per riga (dashboard di competenza: 1,3 s su 84 gruppi). ⛔ Non basterebbe catturare l''errore di AT TIME ZONE: accetta anche stringhe POSIX come UTC+1 (segno rovesciato), cioe'' una data plausibile e sbagliata — quel caso lo ferma il registro. ⛔ FAIL-LOUD su tre condizioni, tutte con E_CONFIG_MANCANTE: parametro assente, valore vuoto (il registro ammette il vuoto), valore che il sistema non riconosce (rete di sicurezza EXCEPTION sul 22023: nome sparito dall''archivio dei fusi o scritto col registro spento). La domanda «riuso o conio un codice?» si risponde su CHI PUO'' RIMEDIARE (sempre chi amministra la configurazione, classe TECNICO) e a distinguere i casi e'' la frase. Nessun ripiego a UTC o a current_date. ⛔ NON usa script.fn_get_parameter_full: la sua cascata di override farebbe portare ALLA STESSA fattura date diverse a seconda di chi la genera. ℹ️ STABLE perche'' now() e'' l''istante di inizio transazione. Brief di origine: brief-db-numerazione-data-documento-e-sequenza §4 DB-2.';
```

---
{% include-markdown "signature-core.md" %}
