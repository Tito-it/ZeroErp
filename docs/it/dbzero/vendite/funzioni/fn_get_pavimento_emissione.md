{% include-markdown "it/dbzero/vendite/manual/fn_get_pavimento_emissione.md" %}
# ⚙️ Funzione `fn_get_pavimento_emissione`

```sql
CREATE FUNCTION fn_get_pavimento_emissione(p_registro_id bigint, p_competenza_mese date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_pavimento_emissione(p_registro_id bigint, p_competenza_mese date)
 RETURNS date
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_politica    vendite.registri_fatturazione.politica_data_documento%TYPE;
    v_giorni      vendite.registri_fatturazione.limite_emissione_giorni%TYPE;
    v_giorno_mese vendite.registri_fatturazione.limite_emissione_giorno_mese%TYPE;
    -- ⚠️ Ancorate a fatture.data e non a `date` nudo: sono date di
    --    DOCUMENTO, ed e' la colonna che ne decide il tipo.
    v_oggi        vendite.fatture.data%TYPE;
    v_primo_succ  vendite.fatture.data%TYPE;
    v_fine_succ   vendite.fatture.data%TYPE;
    v_scadenza    vendite.fatture.data%TYPE;
    v_fine_comp   vendite.fatture.data%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Da quale data in poi un documento di questo sezionale e'
    --   ancora EMETTIBILE. Non dice niente sulla sequenza dei
    --   numeri: quello e' l'altro pavimento.
    --
    -- Regole:
    --   - una regola generale (oggi - giorni) e un PERMESSO della
    --     sola differita che scade;
    --   - il valore e' un DATO (config.parameters + override sul
    --     registro), mai una costante nel codice;
    --   - nessun ELSE che ingoia: una politica non riconosciuta
    --     solleva.
    -- =========================================================

    -- Guard di parametro: un id nullo o non positivo non esce da
    -- nessuna interfaccia — lo produce solo un chiamante rotto,
    -- ed e' per questo che il codice e' TECNICO.
    IF p_registro_id IS NULL OR p_registro_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_pavimento_emissione',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'registro_id obbligatorio e maggiore di zero',
                'p_registro_id', p_registro_id),
            NULL::uuid,
            'vendite.fn_get_pavimento_emissione',
            'p_registro_id (obbligatorio, maggiore di zero)');
    END IF;

    -- ⚠️ Questa tabella non ha RLS: «non trovato» vuol dire
    --    davvero «non esiste».
    SELECT r.politica_data_documento,
           r.limite_emissione_giorni,
           r.limite_emissione_giorno_mese
      INTO v_politica, v_giorni, v_giorno_mese
      FROM vendite.registri_fatturazione r
     WHERE r.id = p_registro_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_pavimento_emissione',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('registro_id', p_registro_id),
            NULL::uuid,
            concat('registro di fatturazione ', p_registro_id, ' inesistente'));
    END IF;

    v_oggi := script.fn_data_operativa();

    -- ⭐ I GIORNI SERVONO SEMPRE, anche sulla differita: sono la
    --    REGOLA GENERALE, e la differita ci ricade appena il suo
    --    permesso scade. NULL sull'override = vale il default
    --    globale, non «nessun limite».
    IF v_giorni IS NULL THEN
        v_giorni := vendite.fn_get_limite_emissione_default(
                        'VENDITE_LIMITE_EMISSIONE_IMMEDIATA_GIORNI');
    END IF;

    -- ─── 1) IMMEDIATA: solo la regola generale ────────────────
    IF v_politica = 'OGGI' THEN
        RETURN v_oggi - v_giorni;
    END IF;

    -- ─── 2) DIFFERITA: la regola, piu' il permesso finche' dura ─
    IF v_politica = 'FINE_MESE_COMPETENZA' THEN

        -- ⛔ Niente ripiego su oggi: la competenza decide il
        --    permesso, e senza permesso il pavimento sarebbe piu'
        --    severo del vero senza dirlo.
        IF p_competenza_mese IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'vendite.fn_get_pavimento_emissione',
                'E_VENDITE_CHIAMATA_NON_VALIDA',
                jsonb_build_object(
                    'detail', 'competenza obbligatoria con politica FINE_MESE_COMPETENZA',
                    'registro_id', p_registro_id,
                    'politica', v_politica),
                NULL::uuid,
                'vendite.fn_get_pavimento_emissione',
                'p_competenza_mese (obbligatorio con politica FINE_MESE_COMPETENZA)');
        END IF;

        IF v_giorno_mese IS NULL THEN
            v_giorno_mese := vendite.fn_get_limite_emissione_default(
                                 'VENDITE_LIMITE_EMISSIONE_DIFFERITA_GIORNO_MESE');
        END IF;

        -- ℹ️ date_trunc anche se la competenza e' il primo del
        --    mese per abitudine: la funzione non deve dipendere
        --    da un'abitudine che nessun vincolo impone.
        v_primo_succ := (date_trunc('month', p_competenza_mese)
                         + interval '1 month')::date;
        v_fine_succ  := (v_primo_succ + interval '1 month - 1 day')::date;

        -- ⭐ IL GIORNO SI APPOGGIA AL MESE, NON LO SCAVALCA
        --    (decisione D-6): con 30 su un febbraio la scadenza
        --    e' il 28 (o il 29), non il 2 marzo. Il CHECK di
        --    colonna ammette 1..31 apposta — un vincolo non
        --    conosce il mese su cui il valore cadra'.
        v_scadenza := LEAST(v_primo_succ + (v_giorno_mese - 1), v_fine_succ);

        IF v_oggi <= v_scadenza THEN
            -- Il permesso e' ancora aperto: la data di fine
            -- competenza resta ammessa ANCHE se e' piu' vecchia
            -- del pavimento mobile.
            v_fine_comp := (date_trunc('month', p_competenza_mese)
                            + interval '1 month - 1 day')::date;

            -- ⚠️ LEAST e non GREATEST: si prende la piu'
            --    PERMISSIVA delle due, perche' sono due ragioni
            --    INDIPENDENTI per cui una data e' ammessa — la
            --    regola generale e il permesso — e basta che ne
            --    valga una.
            RETURN LEAST(v_oggi - v_giorni, v_fine_comp);
        END IF;

        -- Permesso scaduto: torna la regola generale (decisione
        -- D-2, ramo B). ⛔ Non «solo oggi»: i giorni sono la
        -- regola di tutti i documenti, e quando un permesso in
        -- piu' scade non ne compare uno piu' severo.
        RETURN v_oggi - v_giorni;
    END IF;

    -- ─── 3) ⭐ Nessun ELSE che ingoia ─────────────────────────
    -- Il CHECK di colonna rende questo ramo irraggiungibile
    -- finche' regge; se un giorno si allargasse, la funzione si
    -- ferma e lo DICE invece di inventare un pavimento.
    PERFORM script.fn_log_and_raise_error(
        'database', 'vendite.fn_get_pavimento_emissione',
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

COMMENT ON FUNCTION vendite.fn_get_pavimento_emissione(p_registro_id bigint, p_competenza_mese date)
IS 'Da quale data in poi un documento di questo sezionale e'' ancora EMETTIBILE. ⛔ Non dice niente sulla sequenza dei numeri: quello e'' l''altro pavimento (vendite.fn_get_pavimento_sequenza), e a comporli e'' vendite.fn_get_pavimento_data_documento. ⭐ UNA REGOLA GENERALE CON LA SUA ESENZIONE, non due forme: pavimento = LEAST(data_operativa - giorni, fine_mese(competenza) se il permesso della differita e'' ancora aperto). I giorni valgono su ENTRAMBE le politiche — sulla differita sono il pavimento a cui si ricade appena il permesso scade (decisione D-2, ramo B): quando un permesso IN PIU'' scade non ne compare uno piu'' SEVERO di quello di tutti. ⛔ La forma alternativa — la scadenza «15 del mese successivo» dentro un GREATEST con la data della politica — e'' SBAGLIATA e va nominata perche'' sembra giusta: una scadenza vive nello spazio «quando stai lavorando», un pavimento nello spazio «data del documento», e messe insieme farebbero nascere OGNI documento differito datato il 15 del mese dopo (brief §10 V-1). ⚠️ LEAST e non GREATEST nel ramo del permesso: la regola generale e il permesso sono due ragioni INDIPENDENTI per cui una data e'' ammessa, e basta che ne valga una. ⭐ IL GIORNO DEL MESE SI CALCOLA SUL MESE (decisione D-6): LEAST(primo_del_mese_successivo + giorno - 1, ultimo_del_mese_successivo), quindi 31 su un febbraio da'' il 28 (o il 29). Il CHECK di colonna ammette 1..31 apposta — un vincolo non conosce il mese su cui il valore cadra''. ⛔ IL PARAMETRO SI LEGGE NUDO, mai con script.fn_get_parameter_full: la cascata di override darebbe ALLO STESSO documento limiti diversi secondo chi lo genera, e l''unico asse di override e'' il registro. ⛔ NESSUN ELSE CHE INGOIA: una politica non riconosciuta solleva invece di comportarsi come OGGI. ℹ️ Torna SEMPRE una data, mai NULL: il pavimento generale esiste sempre, e chi vuole un sezionale senza limite pratico configura un numero grande (e'' cio'' che fanno le fixture pgTAP che numerano con date d''archivio). ℹ️ STABLE: legge configurazione e si appoggia a script.fn_data_operativa(), che e'' STABLE perche'' now() e'' l''istante di inizio transazione. Brief: brief-db-limite-emissione-e-data-verificata §11 DB-3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
