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
    v_scritti      integer := 0;
    v_ha_perimetro boolean;
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
    -- serve solo a restringere le chiavi della commessa, non a
    -- decidere se scrivere.
    v_ha_perimetro := EXISTS (
        SELECT 1 FROM vendite.fatturazione_lotti_gruppi g
         WHERE g.lotto_id = p_lotto_id);

    WITH chiavi AS (
        -- Il documento indicato, oppure quelli che la commessa
        -- alimenta. ⭐ La chiave si costruisce con la funzione che
        -- la costruisce gia' per la dashboard: una sola sede.
        SELECT p_gruppo_key AS gruppo_key
         WHERE p_gruppo_key IS NOT NULL
        UNION
        SELECT DISTINCT vendite.fn_build_gruppo_fatturabile_key(
                   ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id)
          FROM vendite.commesse_attivita ca
         WHERE p_gruppo_key IS NULL
           AND ca.commessa_id = p_commessa_id
    ),
    ammesse AS (
        SELECT k.gruppo_key
          FROM chiavi k
         WHERE k.gruppo_key IS NOT NULL
           -- Se il lotto dichiara un perimetro, fuori da quello
           -- non stava lavorando quel documento. Se non lo
           -- dichiara, li stava lavorando tutti.
           AND (NOT v_ha_perimetro
                OR EXISTS (SELECT 1
                             FROM vendite.fatturazione_lotti_gruppi g
                            WHERE g.lotto_id = p_lotto_id
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
IS 'Scrive l''esito di UN documento dentro un lotto su vendite.fatturazione_lotti_esiti. ⭐ Rev 2026-09-07: prima scriveva sulle colonne di vendite.fatturazione_lotti_gruppi, cioe'' sul PERIMETRO — e sui giri che un perimetro non lo dichiarano (quelli di massa) non trovava niente da marcare e tornava 0, lasciando muto un documento fallito. Ora la riga si CREA. ⭐ Firma e valore di ritorno invariati: il backend non cambia di una riga. ⭐ Il chiamante passa il documento se ce l''ha, altrimenti la COMMESSA — che e'' cio'' che ha in mano quando fallisce — e le chiavi si costruiscono con vendite.fn_build_gruppo_fatturabile_key, una sola sede. Se il lotto dichiara un perimetro si marca solo dentro quello; se non lo dichiara si marcano tutte le chiavi della commessa, perche'' le stava lavorando tutte. ⚠️ Un secondo tentativo sullo stesso lotto SOVRASCRIVE (la domanda e'' «com''e'' finita», non «quante volte»), e il passaggio a COMPLETED azzera causa, frase e orario. ⛔ NON solleva mai: la chiama un gestore d''eccezione. Torna quante righe ha scritto — zero e'' una risposta e va guardata. Brief: brief-db-esito-gruppo-lotto §15.';
```

---
{% include-markdown "signature-core.md" %}
