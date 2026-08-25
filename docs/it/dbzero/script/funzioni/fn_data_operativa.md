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
    --   - fail-loud su tutte e tre le forme di guasto: assente,
    --     vuoto, non riconosciuto. Mai un ripiego a UTC.
    -- =========================================================

    -- ⛔ Si legge il default NUDO e non script.fn_get_parameter_full:
    --    la cascata di override (utente/gruppo/sessione/emittente)
    --    farebbe dare alla STESSA fattura date diverse a seconda di
    --    chi la genera, cioe' il difetto che questa funzione chiude.
    --    Vedi la testata del changeSet.
    SELECT p.default_value
      INTO v_fuso
      FROM config.parameters p
     WHERE p.code = 'SYSTEM_FUSO_ORARIO';

    -- 1) Assente, oppure presente e vuoto.
    --    ⚠️ Il secondo caso e' raggiungibile davvero:
    --    config.parameters.default_value e' NOT NULL ma non ha
    --    nessun CHECK di non-vuoto, e a catalogo ci sono gia'
    --    parametri a stringa vuota.
    IF v_fuso IS NULL OR btrim(v_fuso) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_data_operativa', 'E_CONFIG_MANCANTE',
            jsonb_build_object('code', 'SYSTEM_FUSO_ORARIO',
                               'valore', v_fuso),
            NULL::uuid,
            -- ⭐ Nel VARIADIC va la CHIAVE DI CONFIGURAZIONE, che
            --    un amministratore riconosce e sa dove mettere —
            --    non il nome di una variabile PL/pgSQL.
            'SYSTEM_FUSO_ORARIO');
    END IF;

    v_fuso := btrim(v_fuso);

    -- 2) C'e' ed e' pieno, ma non e' un fuso.
    --    ⛔ Senza questo controllo `AT TIME ZONE` alza un 22023
    --    grezzo da dentro la funzione: il contratto
    --    «P0001 + CONSTRAINT = errore di dominio» salta e il
    --    guasto arriva al backend come 500 non tradotto.
    IF NOT EXISTS (SELECT 1 FROM pg_timezone_names tz
                    WHERE tz.name = v_fuso) THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_data_operativa', 'E_CONFIG_MANCANTE',
            jsonb_build_object('code', 'SYSTEM_FUSO_ORARIO',
                               'valore', v_fuso),
            NULL::uuid,
            -- ⭐ Qui la frase nomina anche IL VALORE: e' l'unica
            --    cosa che dice a chi legge dove sta l'errore di
            --    battitura.
            concat('SYSTEM_FUSO_ORARIO = ', quote_literal(v_fuso),
                   ' (fuso orario non riconosciuto)'));
    END IF;

    -- ℹ️ now() e' l'istante di inizio transazione: dentro la
    --    stessa transazione la risposta e' per costruzione
    --    identica, ed e' il motivo per cui la funzione e' STABLE.
    RETURN (now() AT TIME ZONE v_fuso)::date;
END;
$function$

COMMENT ON FUNCTION script.fn_data_operativa()
IS 'La data di oggi NEL FUSO DELL''AZIENDA (config.parameters.SYSTEM_FUSO_ORARIO), non in quello della sessione. ⛔ Sostituisce current_date sul percorso della data documento: current_date segue il fuso della SESSIONE, e la sessione di Django e'' UTC (USE_TZ senza TIME_ZONE in DATABASES) mentre psql e pgAgent sono Europe/Rome — lo stesso oggetto dava due date diverse secondo il canale, e ogni documento nato fra mezzanotte e le 02:00 locali portava la data del giorno prima (misurato 2026-08-25: 7 fatture su 18 sfasate). ⛔ FAIL-LOUD su tre condizioni — parametro assente, valore vuoto, valore non presente in pg_timezone_names — tutte con E_CONFIG_MANCANTE: la domanda «riuso o conio un codice?» si risponde su CHI PUO'' RIMEDIARE (sempre chi amministra la configurazione, classe TECNICO) e a distinguere i casi e'' la frase. Nessun ripiego a UTC o a current_date: darebbe una data PLAUSIBILE e SBAGLIATA, cioe'' il difetto stesso in forma piu'' difficile da vedere. ⛔ NON usa script.fn_get_parameter_full, che pure esiste ed e'' il lettore canonico: la sua cascata di override (utente/gruppo/sessione/emittente) farebbe portare ALLA STESSA fattura date diverse a seconda di chi la genera. Il default nudo e'' la scelta, non una dimenticanza. ℹ️ STABLE perche'' now() e'' l''istante di inizio transazione. ⚠️ PERIMETRO: la usano solo fn_calcola_data_documento, fn_get_or_create_fattura_header e il DEFAULT di vendite.fatture.data; CURRENT_DATE resta in 25 tabelle e 67 funzioni, la cui bonifica e'' un cantiere separato. Brief: docs/it/dev/work-in-progress/brief-db-numerazione-data-documento-e-sequenza.md §4 DB-2.';
```

---
{% include-markdown "signature-core.md" %}
