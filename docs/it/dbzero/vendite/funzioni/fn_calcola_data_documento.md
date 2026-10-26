{% include-markdown "it/dbzero/vendite/manual/fn_calcola_data_documento.md" %}
# ⚙️ Funzione `fn_calcola_data_documento`

```sql
CREATE FUNCTION fn_calcola_data_documento(p_registro_id bigint, p_competenza_mese date, p_serie character varying, p_data_dichiarata date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_calcola_data_documento(p_registro_id bigint, p_competenza_mese date, p_serie character varying, p_data_dichiarata date DEFAULT NULL::date)
 RETURNS date
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_politica  vendite.registri_fatturazione.politica_data_documento%TYPE;
    v_data      vendite.fatture.data%TYPE;
    v_pav_emi   vendite.fatture.data%TYPE;
    v_pav_seq   vendite.registri_fatturazione_progressivi.ultima_data%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Che data porta un documento emesso su questo sezionale,
    --   per questa competenza, con questa eventuale
    --   dichiarazione dell'operatore — e gia' CONFORME ai due
    --   pavimenti.
    --
    -- Regole:
    --   - la dichiarata vince su tutto e NON si tocca;
    --   - altrimenti decide la politica del registro;
    --   - poi la data calcolata entra nei due pavimenti;
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

    -- ─── 1) LA DICHIARAZIONE VINCE, E NON SI TOCCA ───────────
    -- ⭐ Vale per TUTTI i documenti del lotto, qualunque sia il
    --    loro registro: e' il senso di «una data sola per l'intero
    --    atto».
    -- ⛔ E IL RETURN STA QUI, PRIMA DEI DUE CLAMP: una scelta
    --    esplicita non si sposta in silenzio. Se e' sotto i
    --    pavimenti, a rifiutarla sara' il cancello — che lo DICE.
    IF p_data_dichiarata IS NOT NULL THEN
        RETURN p_data_dichiarata;
    END IF;

    -- ─── 2) ALTRIMENTI DECIDE IL SEZIONALE ───────────────────
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

        -- ℹ️ date_trunc anche se la competenza e' il primo del
        --    mese per abitudine: la funzione non deve dipendere
        --    da un'abitudine che nessun vincolo impone.
        v_data := (date_trunc('month', p_competenza_mese)
                   + interval '1 month - 1 day')::date;

    ELSIF v_politica = 'OGGI' THEN
        v_data := script.fn_data_operativa();

    ELSE
        -- ─── ⭐ Nessun ramo che ingoia ───────────────────────
        -- Il CHECK di colonna rende questo ramo irraggiungibile
        -- finche' regge; se un giorno si allargasse, la funzione
        -- si ferma e lo DICE invece di datare i documenti a oggi
        -- fingendo di aver capito. Stesso ragionamento gia'
        -- scritto in fn_genera_scadenze_fattura sulla
        -- ripartizione non gestita.
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_calcola_data_documento',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('registro_id', p_registro_id,
                               'politica_data_documento', v_politica),
            NULL::uuid,
            concat('politica data documento non gestita: ',
                   quote_literal(v_politica),
                   ' sul registro ', p_registro_id));
    END IF;

    -- ─── 3) ⭐ CLAMP DEL LIMITE DI EMISSIONE ─────────────────
    -- Se la politica produce una data non piu' emettibile si
    -- riparte da OGGI, NON dal pavimento: nascere sul pavimento
    -- e' nascere gia' scaduti il giorno dopo.
    -- ⚠️ SUL RAMO `OGGI` QUESTO E' UN NO-OP PER COSTRUZIONE: la
    --    politica da' data_operativa() e il pavimento e'
    --    data_operativa() - giorni. Sull'immediata il limite vive
    --    come cancello e come targa, mai come clamp.
    v_pav_emi := vendite.fn_get_pavimento_emissione(
                     p_registro_id, p_competenza_mese);

    IF v_data < v_pav_emi THEN
        v_data := script.fn_data_operativa();
    END IF;

    -- ─── 4) ⭐ CLAMP DEL PAVIMENTO DI SEQUENZA ───────────────
    -- Qui il GREATEST e' giusto: quel pavimento spinge IN AVANTI
    -- verso una data ammessa, e un documento nato sotto di esso
    -- verrebbe rifiutato al primo tentativo di numerarlo.
    -- ⚠️ GREATEST ignora i NULL: da una sequenza vergine il
    --    pavimento e' NULL e la data resta quella calcolata.
    -- ⚠️ Conseguenza accettata (decisione D-3): su un sezionale
    --    che porta gia' una data FUTURA il documento nasce con
    --    quella data, anche su un registro OGGI.
    v_pav_seq := vendite.fn_get_pavimento_sequenza(p_registro_id, p_serie);
    v_data := GREATEST(v_data, v_pav_seq);

    RETURN v_data;
END;
$function$

COMMENT ON FUNCTION vendite.fn_calcola_data_documento(p_registro_id bigint, p_competenza_mese date, p_serie character varying, p_data_dichiarata date)
IS 'Che data porta un documento emesso su questo sezionale, gia'' CONFORME ai due pavimenti. Ordine: (1) la data DICHIARATA sul lotto vince su tutto — vale per tutti i documenti dell''atto, qualunque sia il loro registro; (2) altrimenti decide la politica del sezionale — OGGI usa script.fn_data_operativa(), FINE_MESE_COMPETENZA l''ultimo giorno di competenza_mese; (3) poi la data CALCOLATA entra nei due pavimenti. ⛔ IL CLAMP VALE SOLO SUL RAMO CALCOLATO, MAI SU QUELLO DICHIARATO, e il RETURN della dichiarata sta PRIMA dei clamp apposta: spostare in silenzio una scelta esplicita e'' la classe di difetto che il cantiere della numerazione ha passato tre giorni a togliere — il clamp vale per il default, il cancello vale per la dichiarazione. ⭐ IL CLAMP DEL LIMITE ATTERRA SU OGGI E NON SUL PAVIMENTO: un GREATEST farebbe nascere il documento esattamente sul pavimento, cioe'' con margine di trasmissione ZERO — nato il 14/08 quando oggi e'' il 26/08, sarebbe intrasmissibile il giorno dopo (brief §10 V-4). ⚠️ SUL RAMO OGGI QUEL CLAMP E'' UN NO-OP PER COSTRUZIONE (politica = oggi, pavimento = oggi - giorni), ed e'' scritto perche'' non lo si provi con una fixture impossibile: sull''immediata il limite vive come cancello e come targa, mai come clamp. ⭐ IL CLAMP DELLA SEQUENZA RESTA UN GREATEST: quello spinge IN AVANTI verso una data ammessa, e un documento nato sotto di esso verrebbe rifiutato al primo tentativo di numerarlo. ⚠️ Conseguenza accettata (D-3): su un sezionale che porta gia'' una data FUTURA il documento nasce con quella data, anche su un registro OGGI. ⭐ rev 2026-08-26: arriva p_serie, OBBLIGATORIO e in TERZA posizione (i parametri con DEFAULT stanno in coda). Il pavimento di sequenza e'' per (registro, SERIE) e senza la serie si leggerebbe il contatore di un''ALTRA sequenza, rispondendo «nessun pavimento» — la risposta piu'' permissiva possibile proprio dove il cancello rifiuta. ⛔ p_serie NON ha DEFAULT: un default farebbe dimenticare il parametro. NULL resta legittimo e significa «la serie di default del registro». ⛔ LA FIRMA SERVE DUE CANTIERI (decisione D-8): la chiamano fn_get_or_create_fattura_header e le due viste della dashboard di brief-db-registro-e-data-prevista-in-competenza, che la serie ce l''hanno gia'' da fn_resolve_registro_documento. ⚠️ LA DATA DI NASCITA E'' DIPENDENTE DAL TEMPO, ED E'' UNA DECISIONE: lo stesso lotto generato oggi e domani nasce con due date diverse. E'' il prezzo di «nascere conforme», ed e'' cio'' che fa comparire nei «recuperi del mese» un lotto lavorato in ritardo. ℹ️ Tre letture del registro per fattura CREATA (questa piu'' le due delle funzioni chiamate): e'' il prezzo per non avere tre copie della stessa regola. Brief: brief-db-limite-emissione-e-data-verificata §11 DB-6.';
```

</div>

---
{% include-markdown "signature-core.md" %}
