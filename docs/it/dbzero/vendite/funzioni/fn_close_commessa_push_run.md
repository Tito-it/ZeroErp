{% include-markdown "it/dbzero/vendite/manual/fn_close_commessa_push_run.md" %}
# ⚙️ Funzione `fn_close_commessa_push_run`

```sql
CREATE FUNCTION fn_close_commessa_push_run(p_id bigint, p_stato character varying, p_risultato jsonb, p_durata_ms integer, p_source_types text[])
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_close_commessa_push_run(p_id bigint, p_stato character varying, p_risultato jsonb DEFAULT NULL::jsonb, p_durata_ms integer DEFAULT NULL::integer, p_source_types text[] DEFAULT NULL::text[])
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⭐ UNA SOLA SEDE per l'elenco: il guard lo legge, e il messaggio lo
    --   compone da qui. Scriverlo due volte e' il difetto che ha prodotto
    --   questo changeSet — il CHECK di tabella ammetteva quattro valori e la
    --   funzione che ci scriveva ne ammetteva tre, e nessuno dei due lo sapeva.
    --   ⚠️ Sono un SOTTOINSIEME del vocabolario di chk_commesse_push_log_stato,
    --   che ammette anche IN_ESECUZIONE: quello e' lo stato di un giro aperto,
    --   non un esito. La relazione fra i due insiemi e' asserita dal pgTAP
    --   test-commesse-push-log-function-v1, che rilegge il CHECK.
    v_finali CONSTANT text[] := ARRAY['COMPLETATO', 'PARZIALE', 'ERRORE'];
    v_stato  vendite.commesse_push_log.stato%TYPE;
    v_prima  vendite.commesse_push_log.stato%TYPE;
BEGIN
    -- Scopo: chiude il giro aperto da vendite.fn_start_commessa_push_run —
    --        esito, risultato per handler e durata — e rifiuta le due forme in
    --        cui un chiamante puo' aver perso il filo della propria corsa.

    IF p_id IS NULL OR p_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_close_commessa_push_run', 'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_id', 'valore', p_id),
            NULL::uuid,
            'vendite.fn_close_commessa_push_run',
            'p_id obbligatorio e maggiore di zero');
    END IF;

    IF p_durata_ms IS NOT NULL AND p_durata_ms < 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_close_commessa_push_run', 'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_durata_ms', 'valore', p_durata_ms),
            NULL::uuid,
            'vendite.fn_close_commessa_push_run',
            'p_durata_ms non puo'' essere negativo');
    END IF;

    v_stato := upper(btrim(COALESCE(p_stato, '')));

    -- ── GUARD 1: IN_ESECUZIONE non chiude un giro ────────────────────────
    --   Un giro «chiuso in esecuzione» e' una riga che nessuno riaprira' mai e
    --   che ogni conteggio leggera' come aperta per sempre: e' peggio di una
    --   chiusura mancata, perche' assomiglia a un giro interrotto e non lo e'.
    --   Lo stesso guard intercetta il valore vuoto e quello sconosciuto: hanno
    --   la stessa origine — chi chiude non sa come e' andata.
    IF v_stato <> ALL (v_finali) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_close_commessa_push_run', 'E_COMMESSA_PUSH_RUN_STATO_NON_FINALE',
            jsonb_build_object('push_log_id', p_id, 'stato', p_stato),
            NULL::uuid,
            COALESCE(NULLIF(v_stato, ''), '(vuoto)'),
            array_to_string(v_finali, ', '));
    END IF;

    -- ⚠️ Il filtro sullo stato sta nel WHERE e non in un SELECT ... FOR UPDATE
    --   che precede: cosi' due chiusure in corsa non possono vincere entrambe.
    --   Il perdente non trova la riga e finisce nel guard 2, che e' la verita'.
    --   ⭐ E i COALESCE fanno la loro parte: chi chiude senza ripetere gli
    --   handler non cancella quelli dichiarati all'apertura.
    UPDATE vendite.commesse_push_log l
       SET stato        = v_stato,
           risultato    = COALESCE(p_risultato, l.risultato),
           durata_ms    = COALESCE(p_durata_ms, l.durata_ms),
           source_types = COALESCE(p_source_types, l.source_types)
     WHERE l.id = p_id
       AND l.stato = 'IN_ESECUZIONE';

    -- ── GUARD 2: si chiude un giro che non e' aperto ─────────────────────
    --   Due casi, un codice: la riga non esiste, oppure qualcuno l'ha gia'
    --   chiusa. Sono la stessa cosa per chi legge — il chiamante ha perso il
    --   filo della propria corsa — e il valore nel messaggio dice quale dei
    --   due. ⛔ Non si sovrascrive un esito gia' registrato: verrebbe da
    --   un'altra corsa, e a perdersi sarebbe la storia di entrambe.
    IF NOT FOUND THEN
        SELECT l.stato INTO v_prima
          FROM vendite.commesse_push_log l
         WHERE l.id = p_id;

        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_close_commessa_push_run', 'E_COMMESSA_PUSH_RUN_NON_APERTO',
            jsonb_build_object('push_log_id', p_id, 'stato_corrente', v_prima),
            NULL::uuid,
            p_id::text,
            CASE WHEN v_prima IS NULL
                 THEN 'non esiste'
                 ELSE format('e'' gia'' chiuso in stato %s', v_prima)
            END);
    END IF;
END;
$function$

COMMENT ON FUNCTION vendite.fn_close_commessa_push_run(p_id bigint, p_stato character varying, p_risultato jsonb, p_durata_ms integer, p_source_types text[])
IS 'Chiude il giro di push aperto da vendite.fn_start_commessa_push_run: esito finale, risultato per handler, durata. ⛔ Due rifiuti, ed erano il punto della richiesta del backend: (1) IN_ESECUZIONE non e'' un esito — un giro «chiuso in esecuzione» resterebbe aperto per sempre agli occhi di chi lo conta; (2) una riga che non e'' IN_ESECUZIONE non si chiude — o non esiste, o e'' gia'' chiusa, e sovrascriverne l''esito perderebbe la storia di due corse. Entrambi TECNICO: quel dato lo produce solo un chiamante che ha perso il filo. ⭐ L''elenco degli esiti finali sta in UNA sede dentro la funzione, e il messaggio lo compone da li'': il difetto da cui nasce questo changeSet e'' proprio un CHECK di tabella e un guard di funzione che dicevano cose diverse senza saperlo. ⚠️ I COALESCE non cancellano cio'' che l''apertura aveva dichiarato: chi chiude senza ripetere gli handler li conserva.';
```

</div>

---
{% include-markdown "signature-core.md" %}
