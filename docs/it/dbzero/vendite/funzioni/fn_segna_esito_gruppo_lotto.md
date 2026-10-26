{% include-markdown "it/dbzero/vendite/manual/fn_segna_esito_gruppo_lotto.md" %}
# ⚙️ Funzione `fn_segna_esito_gruppo_lotto`

```sql
CREATE FUNCTION fn_segna_esito_gruppo_lotto(p_lotto_id bigint, p_stato text, p_gruppo_key text, p_commessa_id bigint, p_errore_codice text, p_errore_messaggio text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_segna_esito_gruppo_lotto(p_lotto_id bigint, p_stato text, p_gruppo_key text DEFAULT NULL::text, p_commessa_id bigint DEFAULT NULL::bigint, p_errore_codice text DEFAULT NULL::text, p_errore_messaggio text DEFAULT NULL::text)
 RETURNS TABLE(marcati integer, usciti integer, fuori_perimetro integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⚠️ Tipi espliciti, e nessuno dei tre e' una svista: un
    --    contatore, la risposta a una domanda, e l'array composto
    --    delle chiavi candidate. `%TYPE` solo dove c'e' una colonna.
    v_scritti      integer := 0;
    v_usciti       integer := 0;
    v_fuori        integer := 0;
    v_ha_perimetro boolean;
    v_chiavi       jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire come e' andato UN documento dentro un lotto, su
    --   vendite.fatturazione_lotti_esiti. La riga si crea quando
    --   c'e' qualcosa da dire: cosi' vale anche per i giri che
    --   non dichiarano nessun perimetro, che prima restavano muti.
    --
    -- ⛔ Nessun RAISE: la chiama un gestore d'eccezione.
    -- =========================================================

    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        RAISE WARNING
            'fn_segna_esito_gruppo_lotto: lotto non indicato, esito non scritto.';
        RETURN QUERY SELECT 0, 0, 0;
        RETURN;
    END IF;

    IF p_stato IS NULL THEN
        RAISE WARNING
            'fn_segna_esito_gruppo_lotto: stato non indicato per il lotto %, esito non scritto.',
            p_lotto_id;
        RETURN QUERY SELECT 0, 0, 0;
        RETURN;
    END IF;

    IF p_gruppo_key IS NULL AND p_commessa_id IS NULL THEN
        RAISE WARNING
            'fn_segna_esito_gruppo_lotto: per il lotto % non e'' stato indicato ne'' il documento ne'' la commessa: non c''e'' modo di sapere che cosa scrivere.',
            p_lotto_id;
        RETURN QUERY SELECT 0, 0, 0;
        RETURN;
    END IF;

    -- ⛔ IL GUARD DELLA COMMESSA STA QUI, PRIMA DELLA CHIAMATA.
    --   script.fn_gruppi_di_commessa_nel_lotto SOLLEVA su un id
    --   <= 0 — giustamente, perche' il backend la chiama diretta e
    --   li' e' un chiamante rotto. Questa funzione invece non deve
    --   sollevare mai: il guard e' la sola cosa che fa convivere le
    --   due promesse.
    -- ⭐ E dice il vero: prima un id negativo usciva come «nessun
    --   documento trovato», cioe' la diagnosi sbagliata.
    IF p_gruppo_key IS NULL AND p_commessa_id <= 0 THEN
        RAISE WARNING
            'fn_segna_esito_gruppo_lotto: commessa % non valida sul lotto %: esito non scritto.',
            p_commessa_id, p_lotto_id;
        RETURN QUERY SELECT 0, 0, 0;
        RETURN;
    END IF;

    -- ⚠️ Il vincolo di tabella pretende, su ERRORE, almeno una fra
    --   causa e frase. Si controlla PRIMA: farlo scoprire al
    --   vincolo vorrebbe dire sollevare, ed e' cio' che questa
    --   funzione non deve fare.
    IF p_stato = 'ERRORE'
       AND p_errore_codice IS NULL
       AND p_errore_messaggio IS NULL THEN
        RAISE WARNING
            'fn_segna_esito_gruppo_lotto: errore senza causa ne'' frase sul lotto %: un errore muto non si scrive.',
            p_lotto_id;
        RETURN QUERY SELECT 0, 0, 0;
        RETURN;
    END IF;

    -- Il lotto dichiara un perimetro? La domanda si fa UNA volta:
    -- serve solo a restringere le chiavi, non a decidere se
    -- scrivere.
    v_ha_perimetro := EXISTS (
        SELECT 1 FROM vendite.fatturazione_lotti_gruppi g
         WHERE g.lotto_id = p_lotto_id);

    -- Le chiavi candidate: il documento indicato, oppure quelli che
    -- la commessa alimenta.
    -- ⭐ La risoluzione dalla commessa NON e' scritta qui: vive in
    --   script.fn_gruppi_di_commessa_nel_lotto, perche' serve anche
    --   a chi SCRIVE la segnalazione di un pull fallito, che ha in
    --   mano la commessa e non il documento (linee-guida-sql
    --   §12.5.2: la madre non riscrive il predicato, lo chiama).
    -- ⚠️ Il ramo si sceglie con un IF e non dentro la query: una
    --   funzione che torna un array, messa nel FROM, verrebbe
    --   valutata anche sul ramo escluso dalla WHERE — e con
    --   p_commessa_id NULL solleverebbe.
    IF p_gruppo_key IS NOT NULL THEN
        v_chiavi := jsonb_build_array(p_gruppo_key);
    ELSE
        v_chiavi := script.fn_gruppi_di_commessa_nel_lotto(
                        p_lotto_id, p_commessa_id);
    END IF;

    -- ⭐ I TRE ZERI SI CONTANO PRIMA, perche' dopo la scrittura non si
    --   distinguono piu'. «Nessuna riga marcata» ha TRE cause e una sola e' un
    --   difetto:
    --     · nessun documento appeso a questa commessa        -> difetto
    --     · gli unici documenti sono usciti dal giro         -> normale
    --     · i documenti ci sono ma nessuno nel perimetro     -> sospetto, e
    --       c'era gia' prima di questo cantiere
    --   ⛔ Un numero solo non le sa dire, e chi legge va a cercare la cosa
    --   sbagliata: e' la ragione per cui questa funzione ne restituisce tre.
    SELECT count(*) FILTER (WHERE x.stato_esecuzione = 'ESCLUSO'),
           count(*) FILTER (WHERE v_ha_perimetro AND g.gruppo_key IS NULL)
      INTO v_usciti, v_fuori
      FROM jsonb_array_elements_text(v_chiavi) AS k(gruppo_key)
      LEFT JOIN vendite.fatturazione_lotti_esiti x
             ON x.lotto_id = p_lotto_id AND x.gruppo_key = k.gruppo_key
      LEFT JOIN vendite.fatturazione_lotti_gruppi g
             ON g.lotto_id = p_lotto_id AND g.gruppo_key = k.gruppo_key
     WHERE k.gruppo_key IS NOT NULL;

    WITH ammesse AS (
        SELECT k.gruppo_key
          FROM jsonb_array_elements_text(v_chiavi) AS k(gruppo_key)
         WHERE k.gruppo_key IS NOT NULL
           -- ⚠️ Il perimetro si riapplica qui, e non e' un doppione:
           --   presidia l'ingresso che la funzione estratta non
           --   vede, cioe' il p_gruppo_key passato dal chiamante.
           --   Sulla via della commessa e' idempotente.
           AND (NOT v_ha_perimetro
                OR EXISTS (SELECT 1
                             FROM vendite.fatturazione_lotti_gruppi g
                            WHERE g.lotto_id   = p_lotto_id
                              AND g.gruppo_key = k.gruppo_key))
           -- ⛔ UN DOCUMENTO USCITO DAL GIRO NON SI MARCA. ESCLUSO e'
           --   terminale (D-3) e il trigger a10_uscita rifiuta QUALUNQUE
           --   cambio di stato, in entrambi i versi: guarda che il valore
           --   CAMBI, non quale sia. Senza questa riga il marcatore tentava,
           --   il trigger sollevava, e l'eccezione usciva dal marcatore
           --   uccidendo il rilancio del lotto.
           -- ⚠️ E il danno non era il documento uscito: il trigger e' BEFORE
           --   ROW dentro un INSERT ... ON CONFLICT unico, quindi saltava
           --   l'INTERO statement e restavano senza esito anche i documenti
           --   SANI della stessa commessa. Per questo il filtro sta QUI
           --   dentro e non in un controllo che precede: gli altri devono
           --   passare.
           -- ⚠️ `ESCLUSO` e' un LETTERALE, ed e' il quinto punto del database
           --   che lo scrive a mano (con i due guard dell'uscita, la check
           --   dell'escludibilita' e il conteggio delle segnalazioni). Sta qui
           --   dichiarato, non nascosto: l'asse gemello di questo dominio — il
           --   confine pre-fiscale — un flag ce l'ha
           --   (config.stati_doc_fiscale.congela_fiscale, letto fail-closed) e
           --   il commento di fn_check_documento_escludibile_da_giro scrive a
           --   chiare lettere «mai un elenco di stati scritto a mano». Qui non
           --   c'e' catalogo: stato_esecuzione e' un text con un CHECK a
           --   cinque valori. Farne un catalogo con un flag «fuori_dal_giro»
           --   tocca il CHECK e un seed: e' un cantiere suo, e mescolarlo a un
           --   difetto che blocca un lotto sarebbe sbagliato.
           AND NOT EXISTS (SELECT 1
                             FROM vendite.fatturazione_lotti_esiti x
                            WHERE x.lotto_id   = p_lotto_id
                              AND x.gruppo_key = k.gruppo_key
                              AND x.stato_esecuzione = 'ESCLUSO')
    )
    INSERT INTO vendite.fatturazione_lotti_esiti AS e
           (lotto_id, gruppo_key, stato_esecuzione,
            errore_codice, errore_messaggio, errore_quando)
    SELECT p_lotto_id,
           a.gruppo_key,
           p_stato,
           CASE WHEN p_stato = 'ERRORE' THEN p_errore_codice END,
           CASE WHEN p_stato = 'ERRORE' THEN p_errore_messaggio END,
           CASE WHEN p_stato = 'ERRORE' THEN clock_timestamp() END
      FROM ammesse a
        ON CONFLICT ON CONSTRAINT uq_fatturazione_lotti_esiti_documento
        DO UPDATE
           SET stato_esecuzione = EXCLUDED.stato_esecuzione,
               -- ⭐ Un documento che ci riprova e riesce non resta
               --   col rosso addosso: un rosso che non scade mai
               --   e' peggio di nessun rosso.
               errore_codice    = EXCLUDED.errore_codice,
               errore_messaggio = EXCLUDED.errore_messaggio,
               errore_quando    = EXCLUDED.errore_quando,
               data_update      = now(),
               user_update      = CURRENT_USER;

    GET DIAGNOSTICS v_scritti = ROW_COUNT;

    -- ⚠️ Zero e' una risposta, e va detta: vuol dire che il
    --   fallimento non e' stato appeso a nessun documento.
    -- ⚠️ GLI ZERI SONO TRE, non due, e vanno detti diversi: «nessun documento
    --   appeso» (difetto), «gli unici documenti sono usciti dal giro»
    --   (normale, e possibile da oggi) e — gia' prima di questo changeSet —
    --   «la commessa ha documenti, ma nessuno nel perimetro di questo lotto».
    --   Un avviso solo per tre cause manda a cercare la cosa sbagliata.
    -- ⚠️ Il VALORE DI RITORNO resta «quante righe di esito sono state
    --   scritte»: non cambia, quindi nessun chiamante si rompe. Ma il backend
    --   decide il proprio allarme su `if not marcati`, quindi sul caso
    --   legittimo vedra' uno zero e avvisera' a vuoto. E' la decisione aperta
    --   §4.1 del brief, e da qui il DB puo' solo dirlo nel log.
    IF v_scritti = 0 AND v_usciti > 0 THEN
        RAISE NOTICE
            'fn_segna_esito_gruppo_lotto: sul lotto % (documento=%, commessa=%) tutti i % documenti hanno gia'' lasciato il giro: niente da marcare, e non e'' un difetto.',
            p_lotto_id, p_gruppo_key, p_commessa_id, v_usciti;
    ELSIF v_scritti = 0 THEN
        RAISE WARNING
            'fn_segna_esito_gruppo_lotto: nessun documento trovato per il lotto % (documento=%, commessa=%): esito non appeso a niente (% fuori perimetro).',
            p_lotto_id, p_gruppo_key, p_commessa_id, v_fuori;
    ELSIF v_usciti > 0 THEN
        RAISE NOTICE
            'fn_segna_esito_gruppo_lotto: sul lotto % marcati % documenti, % gia'' usciti dal giro e saltati.',
            p_lotto_id, v_scritti, v_usciti;
    END IF;

    -- ⭐ Tre numeri, non uno: il chiamante puo' distinguere «non c'era niente
    --   da fare» da «qualcosa non torna» senza leggere il log.
    RETURN QUERY SELECT v_scritti, v_usciti, v_fuori;
END;
$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
