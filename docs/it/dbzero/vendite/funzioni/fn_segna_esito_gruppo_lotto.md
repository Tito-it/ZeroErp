{% include-markdown "it/dbzero/vendite/manual/fn_segna_esito_gruppo_lotto.md" %}
# ⚙️ Funzione `fn_segna_esito_gruppo_lotto`

```sql
CREATE FUNCTION fn_segna_esito_gruppo_lotto(p_lotto_id bigint, p_stato text, p_gruppo_key text, p_commessa_id bigint, p_errore_codice text, p_errore_messaggio text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_segna_esito_gruppo_lotto(p_lotto_id bigint, p_stato text, p_gruppo_key text DEFAULT NULL::text, p_commessa_id bigint DEFAULT NULL::bigint, p_errore_codice text DEFAULT NULL::text, p_errore_messaggio text DEFAULT NULL::text)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⚠️ Tipi espliciti, e nessuno dei tre e' una svista: un
    --    contatore, la risposta a una domanda, e l'array composto
    --    delle chiavi candidate. `%TYPE` solo dove c'e' una colonna.
    v_scritti      integer := 0;
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
        RETURN 0;
    END IF;

    IF p_stato IS NULL THEN
        RAISE WARNING
            'fn_segna_esito_gruppo_lotto: stato non indicato per il lotto %, esito non scritto.',
            p_lotto_id;
        RETURN 0;
    END IF;

    IF p_gruppo_key IS NULL AND p_commessa_id IS NULL THEN
        RAISE WARNING
            'fn_segna_esito_gruppo_lotto: per il lotto % non e'' stato indicato ne'' il documento ne'' la commessa: non c''e'' modo di sapere che cosa scrivere.',
            p_lotto_id;
        RETURN 0;
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
        RETURN 0;
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
        RETURN 0;
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
    IF v_scritti = 0 THEN
        RAISE WARNING
            'fn_segna_esito_gruppo_lotto: nessun documento trovato per il lotto % (documento=%, commessa=%): esito non appeso a niente.',
            p_lotto_id, p_gruppo_key, p_commessa_id;
    END IF;

    RETURN v_scritti;
END;
$function$

COMMENT ON FUNCTION vendite.fn_segna_esito_gruppo_lotto(p_lotto_id bigint, p_stato text, p_gruppo_key text, p_commessa_id bigint, p_errore_codice text, p_errore_messaggio text)
IS 'Scrive l''esito di UN documento dentro un lotto su vendite.fatturazione_lotti_esiti. ⭐ Rev 2026-09-08: la risoluzione «questa commessa quali documenti alimenta, dentro questo lotto» non e'' piu'' scritta qui — la fa script.fn_gruppi_di_commessa_nel_lotto, che serve anche a CHI SCRIVE la segnalazione di un pull fallito (il backend ha in mano la commessa, non il documento). La madre non riscrive il predicato, lo chiama: linee-guida-sql §12.5.2. ⭐ Firma, valore di ritorno e comportamento invariati. ⚠️ Il perimetro si riapplica qui e non e'' un doppione: presidia il p_gruppo_key passato dal chiamante, che la funzione estratta non vede; sulla via della commessa e'' idempotente. ⛔ NON solleva mai (la chiama un gestore d''eccezione), quindi il guard su una commessa <= 0 sta QUI, prima della chiamata alla funzione estratta, che invece solleva: prima un id negativo usciva come «nessun documento trovato», cioe'' la diagnosi sbagliata. ⚠️ Il ramo si sceglie con un IF e non dentro la query: una funzione che torna un array, messa nel FROM, verrebbe valutata anche sul ramo escluso dalla WHERE. ⭐ Rev 2026-09-07: prima scriveva sulle colonne di vendite.fatturazione_lotti_gruppi, cioe'' sul PERIMETRO — e sui giri che un perimetro non lo dichiarano (quelli di massa) non trovava niente da marcare e tornava 0, lasciando muto un documento fallito. Ora la riga si CREA. ⭐ Il chiamante passa il documento se ce l''ha, altrimenti la COMMESSA. Se il lotto dichiara un perimetro si marca solo dentro quello; se non lo dichiara si marcano tutte le chiavi della commessa, perche'' le stava lavorando tutte. ⚠️ Un secondo tentativo sullo stesso lotto SOVRASCRIVE (la domanda e'' «com''e'' finita», non «quante volte»), e il passaggio a COMPLETED azzera causa, frase e orario. Torna quante righe ha scritto — zero e'' una risposta e va guardata. Brief: brief-db-esito-gruppo-lotto §15 · brief-db-uscita-documento-dal-giro §6.1.';
```

---
{% include-markdown "signature-core.md" %}
