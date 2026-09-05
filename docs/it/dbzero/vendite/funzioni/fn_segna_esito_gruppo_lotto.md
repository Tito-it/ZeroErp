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
    v_marcati integer := 0;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire come e' andato UN documento dentro un lotto, sulla
    --   riga che il lotto ha gia' scritto quando ha deciso cosa
    --   lavorare. Serve perche' un documento che fallisce prima
    --   di diventare fattura non ha nessun'altra riga dove
    --   comparire, e senza questa resta invisibile due volte:
    --   assente dal lotto, e apparentemente sano nella
    --   competenza.
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
            'fn_segna_esito_gruppo_lotto: per il lotto % non e'' stato indicato ne'' il gruppo ne'' la commessa: non c''e'' modo di sapere quale riga marcare.',
            p_lotto_id;
        RETURN 0;
    END IF;

    -- ⚠️ Il CHECK di tabella pretende, su ERRORE, almeno una fra
    --   causa e frase. Qui si controlla PRIMA: farlo scoprire al
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

    -- =========================================================
    -- Si marca il gruppo indicato, oppure QUELLI che quella
    -- commessa alimenta dentro QUESTO lotto.
    -- ⭐ La chiave si costruisce con la funzione che la
    --   costruisce gia' per la dashboard: non se ne riscrive
    --   una seconda versione.
    -- =========================================================
    UPDATE vendite.fatturazione_lotti_gruppi g
       SET stato_esecuzione  = p_stato,
           errore_codice     = CASE WHEN p_stato = 'ERRORE' THEN p_errore_codice END,
           errore_messaggio  = CASE WHEN p_stato = 'ERRORE' THEN p_errore_messaggio END,
           errore_quando     = CASE WHEN p_stato = 'ERRORE' THEN clock_timestamp() END
     WHERE g.lotto_id = p_lotto_id
       AND (
            (p_gruppo_key IS NOT NULL AND g.gruppo_key = p_gruppo_key)
         OR (p_gruppo_key IS NULL AND EXISTS (
                SELECT 1
                  FROM vendite.commesse_attivita ca
                 WHERE ca.commessa_id = p_commessa_id
                   AND vendite.fn_build_gruppo_fatturabile_key(
                           ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id
                       ) = g.gruppo_key))
       );

    GET DIAGNOSTICS v_marcati = ROW_COUNT;

    -- ⚠️ Zero e' una risposta, e va detta: vuol dire che il
    --   fallimento non e' stato appeso a niente, cioe' che il
    --   lotto continuera' a raccontare un errore su un documento
    --   che non mostra.
    IF v_marcati = 0 THEN
        RAISE WARNING
            'fn_segna_esito_gruppo_lotto: nessun gruppo trovato nel lotto % (gruppo=%, commessa=%): esito non appeso a nessun documento.',
            p_lotto_id, p_gruppo_key, p_commessa_id;
    END IF;

    RETURN v_marcati;
END;
$function$

COMMENT ON FUNCTION vendite.fn_segna_esito_gruppo_lotto(p_lotto_id bigint, p_stato text, p_gruppo_key text, p_commessa_id bigint, p_errore_codice text, p_errore_messaggio text)
IS 'Scrive l''esito di UN documento dentro un lotto sulla riga di vendite.fatturazione_lotti_gruppi che il lotto ha gia'' creato quando ha deciso cosa lavorare. ⭐ Nasce dal lotto LTF-0009578: tre ordini presi in carico, due fatturati, e il terzo caduto al primo passo — che restava fuori dal lotto (nessuna fattura a cui appendersi) e dentro i documenti da emettere senza un segno, quindi sembrava fatturabile. ⭐ Il chiamante passa il gruppo se ce l''ha, altrimenti la COMMESSA — che e'' cio'' che ha in mano quando fallisce — e la funzione ritrova il gruppo dentro quel lotto riusando vendite.fn_build_gruppo_fatturabile_key: la derivazione resta in un posto solo. ⚠️ Puo'' marcare piu'' di un gruppo se la commessa ne alimenta piu'' d''uno in quel lotto: erano tutti nel giro fallito, e sceglierne uno sarebbe una scommessa. ⛔ NON solleva mai: la chiama un gestore d''eccezione, e un errore su di se'' coprirebbe l''errore vero. Ogni via d''uscita e'' un WARNING e torna quanti gruppi ha marcato — zero e'' una risposta e va guardata. ⛔ Non tocca la commessa ne'' l''emittibilita'': dice che un tentativo e'' fallito, non che il documento non si possa fatturare (decisione di Tid, 2026-09-06).';
```

---
{% include-markdown "signature-core.md" %}
