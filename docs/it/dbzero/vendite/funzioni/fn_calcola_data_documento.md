{% include-markdown "it/dbzero/vendite/manual/fn_calcola_data_documento.md" %}
# ⚙️ Funzione `fn_calcola_data_documento`

```sql
CREATE FUNCTION fn_calcola_data_documento(p_registro_id bigint, p_competenza_mese date, p_data_dichiarata date)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_calcola_data_documento(p_registro_id bigint, p_competenza_mese date, p_data_dichiarata date DEFAULT NULL::date)
 RETURNS date
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_politica vendite.registri_fatturazione.politica_data_documento%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Che data porta un documento emesso su questo registro,
    --   per questa competenza, con questa eventuale
    --   dichiarazione dell'operatore.
    --
    -- Regole:
    --   - la dichiarata vince su tutto;
    --   - altrimenti decide la politica del registro;
    --   - non esiste un terzo caso silenzioso: ogni ramo non
    --     previsto solleva.
    -- =========================================================

    -- Guard di parametro: un id nullo o non positivo non esce da
    -- nessuna interfaccia — lo produce solo un chiamante rotto,
    -- ed e' per questo che il codice e' TECNICO.
    IF p_registro_id IS NULL OR p_registro_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_calcola_data_documento',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'registro_id obbligatorio e maggiore di zero',
                'p_registro_id', p_registro_id),
            NULL::uuid,
            'vendite.fn_calcola_data_documento',
            'p_registro_id (obbligatorio, maggiore di zero)');
    END IF;

    -- Il registro si legge SEMPRE, anche quando la data e' gia'
    -- dichiarata: e' l'unico punto in cui un registro inesistente
    -- si fa notare. ⚠️ Questa tabella non ha RLS: «non trovato»
    -- vuol dire davvero «non esiste».
    SELECT r.politica_data_documento
      INTO v_politica
      FROM vendite.registri_fatturazione r
     WHERE r.id = p_registro_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_calcola_data_documento',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('registro_id', p_registro_id),
            NULL::uuid,
            concat('registro di fatturazione ', p_registro_id, ' inesistente'));
    END IF;

    -- 1) La dichiarazione vince. ⭐ Vale per TUTTI i documenti del
    --    lotto, qualunque sia il loro registro: e' il senso di
    --    «una data sola per l'intero atto» (decisione 5).
    IF p_data_dichiarata IS NOT NULL THEN
        RETURN p_data_dichiarata;
    END IF;

    -- 2) Altrimenti decide il sezionale.
    IF v_politica = 'FINE_MESE_COMPETENZA' THEN
        -- ⛔ Niente ripiego su oggi: una data plausibile e
        --    sbagliata su un documento fiscale non la nota
        --    nessuno, e quando la si nota il numero e' gia'
        --    stato consumato.
        IF p_competenza_mese IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'vendite.fn_calcola_data_documento',
                'E_VENDITE_CHIAMATA_NON_VALIDA',
                jsonb_build_object(
                    'detail', 'competenza obbligatoria con politica FINE_MESE_COMPETENZA',
                    'registro_id', p_registro_id,
                    'politica', v_politica),
                NULL::uuid,
                'vendite.fn_calcola_data_documento',
                'p_competenza_mese (obbligatorio con politica FINE_MESE_COMPETENZA)');
        END IF;

        -- ℹ️ date_trunc anche se la competenza e' gia' il primo
        --    del mese in tutti i 49 lotti misurati: la funzione
        --    non deve dipendere da un'abitudine che nessun
        --    vincolo impone.
        RETURN (date_trunc('month', p_competenza_mese)
                + interval '1 month - 1 day')::date;

    ELSIF v_politica = 'OGGI' THEN
        RETURN script.fn_data_operativa();
    END IF;

    -- 3) ⭐ Nessun ELSE che ingoia. Il CHECK di colonna rende
    --    questo ramo irraggiungibile finche' regge; se un giorno
    --    si allargasse, la funzione si ferma e lo DICE invece di
    --    datare i documenti a oggi fingendo di aver capito.
    --    Stesso ragionamento gia' scritto in
    --    fn_genera_scadenze_fattura sulla ripartizione.
    PERFORM script.fn_log_and_raise_error(
        'database', 'vendite.fn_calcola_data_documento',
        'E_CONFIG_MANCANTE',
        jsonb_build_object('registro_id', p_registro_id,
                           'politica_data_documento', v_politica),
        NULL::uuid,
        concat('politica data documento non gestita: ',
               quote_literal(v_politica),
               ' sul registro ', p_registro_id));

    -- Irraggiungibile: la riga sopra solleva sempre. Serve al
    -- compilatore, che pretende un ritorno su ogni percorso.
    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.fn_calcola_data_documento(p_registro_id bigint, p_competenza_mese date, p_data_dichiarata date)
IS 'Che data porta un documento emesso su questo registro. Ordine: (1) la data DICHIARATA sul lotto vince su tutto — vale per tutti i documenti dell''atto, qualunque sia il loro registro, ed e'' il senso della decisione «una data sola per l''intero atto»; (2) altrimenti decide la politica del sezionale — OGGI usa script.fn_data_operativa(), FINE_MESE_COMPETENZA l''ultimo giorno di competenza_mese. ⛔ NESSUN RIPIEGO, in due punti: competenza assente con politica FINE_MESE_COMPETENZA solleva (E_VENDITE_CHIAMATA_NON_VALIDA, TECNICO: competenza_mese e'' NOT NULL sul lotto, quindi un NULL qui e'' un guasto di programma), e una politica non riconosciuta solleva invece di comportarsi come OGGI. Una data PLAUSIBILE E SBAGLIATA su un documento fiscale non la nota nessuno, e quando la si nota il numero e'' gia'' stato consumato — e'' lo stesso ragionamento gia'' scritto in fn_genera_scadenze_fattura sulla ripartizione non gestita. ⚠️ Il registro si legge SEMPRE, anche con la data dichiarata: costa una lettura per PK su sei righe ed e'' l''unico punto in cui un registro inesistente si fa notare; la tabella non ha RLS, quindi «non trovato» vuol dire davvero «non esiste». ℹ️ date_trunc sulla competenza anche se nei 49 lotti misurati e'' sempre il primo del mese: nessun vincolo lo impone. Brief: docs/it/dev/work-in-progress/brief-db-numerazione-data-documento-e-sequenza.md §4 DB-5.';
```

---
{% include-markdown "signature-core.md" %}
