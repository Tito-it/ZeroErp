{% include-markdown "it/dbzero/vendite/manual/fn_riapri_riconsegna_reso.md" %}
# ⚙️ Funzione `fn_riapri_riconsegna_reso`

```sql
CREATE FUNCTION fn_riapri_riconsegna_reso(p_reso_id bigint, p_righe jsonb)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_riapri_riconsegna_reso(p_reso_id bigint, p_righe jsonb DEFAULT NULL::jsonb)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- Scopo: annulla una CHIUSURA di ri-consegna. Cancella le rinunce e
--   ri-proietta lo stato ordine (torna PARZIALMENTE_EVASO): la quota
--   torna ri-spedibile e l'accredito torna FACOLTATIVA.
--   Round-trip chiudi -> riapri = stato iniziale.
--   Brief: brief-db-chiusura-riconsegna-reso-definitivo §5.1.
-- Ritorna: numero di RIGHE RESO riaperte (non di rinunce cancellate).
--
-- p_righe NULL = riapre tutte le rinunce del reso. Altrimenti
--   [{resi_riga_id, qta}]: riapre fino a `qta`, scalando dalle
--   rinunce piu' RECENTI (LIFO) — si annulla l'ultimo errore, non il
--   primo evento. qta assente/NULL = riapre tutta la riga.
--
-- GATE NC: consuma script.fn_check_rinuncia_reversibile, che oggi non
--   produce motivi (il ramo NC non esiste). Quando esistera', il
--   divieto si aggiungera' LA' e questa madre lo sollevera' da se'.
DECLARE
    v_stato          config.stati_doc_reso.codice_interno%TYPE;
    v_riga           RECORD;
    v_rin            RECORD;
    v_ord            RECORD;
    v_motivi         jsonb;
    v_da_riaprire    numeric;
    v_scala          numeric;
    v_n              integer := 0;
BEGIN
    -- 1) Guard input.
    IF p_reso_id IS NULL OR p_reso_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_riapri_riconsegna_reso','E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro','reso_id','valore',p_reso_id),
            NULL::uuid, 'reso_id obbligatorio (>0)');
    END IF;

    -- 2) Reso esistente e CONFERMATO (stesso gate delle sorelle).
    SELECT sdr.codice_interno
      INTO v_stato
      FROM vendite.resi r
      JOIN config.stati_doc_reso sdr ON sdr.id = r.stato_doc_reso_id
     WHERE r.id = p_reso_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_riapri_riconsegna_reso','E_RESO_NOT_FOUND',
            jsonb_build_object('reso_id', p_reso_id),
            NULL::uuid, p_reso_id::text);
    END IF;

    IF v_stato IS DISTINCT FROM 'CONFERMATO' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_riapri_riconsegna_reso','E_RESO_NON_CONFERMATO',
            jsonb_build_object('reso_id', p_reso_id, 'stato', v_stato),
            NULL::uuid, p_reso_id::text, COALESCE(v_stato,'NULL'));
    END IF;

    -- 3) Righe con almeno una rinuncia da annullare.
    FOR v_riga IN
        SELECT rr.id AS resi_riga_id,
               (SELECT COALESCE(SUM(x.qta),0)
                  FROM vendite.resi_righe_rinunce x
                 WHERE x.resi_riga_id = rr.id) AS tot_rinunciato,
               (SELECT (e->>'qta')::numeric
                  FROM jsonb_array_elements(COALESCE(p_righe,'[]'::jsonb)) e
                 WHERE (e->>'resi_riga_id')::bigint = rr.id
                 LIMIT 1) AS qta_richiesta
          FROM vendite.resi_righe rr
          JOIN config.tipi_reso tr ON tr.id = rr.tipo_reso_id
         WHERE rr.reso_id = p_reso_id
           AND rr.attivo IS TRUE
           AND tr.riapre_residuo IS TRUE
           AND (p_righe IS NULL OR rr.id IN (
                 SELECT (e->>'resi_riga_id')::bigint
                   FROM jsonb_array_elements(p_righe) e))
         ORDER BY rr.riga_nr, rr.id
    LOOP
        IF v_riga.tot_rinunciato <= 0 THEN
            CONTINUE;  -- nessuna rinuncia su questa riga
        END IF;

        -- Gate dormiente: oggi nessun motivo, domani il divieto NC.
        v_motivi := script.fn_check_rinuncia_reversibile(v_riga.resi_riga_id);
        -- ⭐ La coda del primo motivo sta in un posto solo: l'helper legge il
        --   codice da `v_motivi -> 0`, ne prende i `valori` per la frase, fonde il
        --   `dettaglio` nel contesto e ci mette sempre l'elenco COMPLETO dei motivi
        --   (il backend puo' mostrarli tutti anche se la frase ne nomina uno).
        -- ⚠️ L'IF e' sparito e NON e' fail-open: l'helper tace su un array vuoto,
        --   che e' esattamente la risposta «passa». Su un non-array resta rumoroso.
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'vendite', 'fn_riapri_riconsegna_reso',
            v_motivi,
            NULL,
            NULL::uuid,
            jsonb_build_object('reso_id',      p_reso_id,
                               'resi_riga_id', v_riga.resi_riga_id));

        -- Quanto riaprire: tutto, oppure la quota richiesta troncata
        -- al totale rinunciato.
        IF p_righe IS NOT NULL AND v_riga.qta_richiesta IS NOT NULL THEN
            v_da_riaprire := LEAST(v_riga.qta_richiesta, v_riga.tot_rinunciato);
        ELSE
            v_da_riaprire := v_riga.tot_rinunciato;
        END IF;
        IF v_da_riaprire <= 0 THEN
            CONTINUE;
        END IF;

        -- Scala dalle rinunce piu' RECENTI (LIFO): si annulla
        -- l'ultimo errore, non il primo evento registrato.
        FOR v_rin IN
            SELECT x.id, x.qta
              FROM vendite.resi_righe_rinunce x
             WHERE x.resi_riga_id = v_riga.resi_riga_id
             ORDER BY x.id DESC
        LOOP
            EXIT WHEN v_da_riaprire <= 0;

            IF v_rin.qta <= v_da_riaprire THEN
                -- Rinuncia interamente annullata.
                DELETE FROM vendite.resi_righe_rinunce WHERE id = v_rin.id;
                v_da_riaprire := v_da_riaprire - v_rin.qta;
            ELSE
                -- Annullo PARZIALE della singola rinuncia: si riduce
                -- la qta invece di cancellarla, cosi' resta la traccia
                -- della parte ancora definitiva.
                v_scala := v_rin.qta - v_da_riaprire;
                UPDATE vendite.resi_righe_rinunce
                   SET qta = v_scala
                 WHERE id = v_rin.id;
                v_da_riaprire := 0;
            END IF;
        END LOOP;

        v_n := v_n + 1;
    END LOOP;

    -- 4) Niente da riaprire -> errore parlante.
    IF v_n = 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_riapri_riconsegna_reso','E_RESO_NESSUNA_RICONSEGNA_PENDENTE',
            jsonb_build_object('reso_id', p_reso_id, 'righe', p_righe),
            NULL::uuid, p_reso_id::text);
    END IF;

    -- 5) Ri-proiezione stato ordine: la quota torna a pesare
    --    sull'addendo reso -> il residuo si riapre -> l'ordine torna
    --    PARZIALMENTE_EVASO. Simmetrico alla chiusura.
    FOR v_ord IN
        SELECT DISTINCT orr.ordine_id
          FROM vendite.resi_righe rr
          JOIN vendite.ordini_righe orr ON orr.id = rr.ordine_riga_id
         WHERE rr.reso_id = p_reso_id
           AND rr.ordine_riga_id IS NOT NULL
    LOOP
        -- ⭐ rev 2026-10-11: la proiezione e' il building block
        --    vendite.fn_ordine_proietta_stato_evasione (brief-db-ddt-righe-evase-dall-ordine).
        PERFORM vendite.fn_ordine_proietta_stato_evasione(v_ord.ordine_id);
    END LOOP;

    RETURN v_n;
END;
$function$

COMMENT ON FUNCTION vendite.fn_riapri_riconsegna_reso(p_reso_id bigint, p_righe jsonb)
IS 'Madre RIAPERTURA rinuncia (brief-db-chiusura-riconsegna-reso-definitivo S5.1): annulla una chiusura di ri-consegna cancellando le rinunce e ri-proiettando lo stato ordine (torna PARZIALMENTE_EVASO). La quota torna ri-spedibile e l''accredito torna FACOLTATIVA: round-trip chiudi->riapri = stato iniziale. p_righe NULL = tutte le rinunce del reso; [{resi_riga_id, qta}] scala dalle rinunce piu'' RECENTI (LIFO, si annulla l''ultimo errore) e riduce la qta invece di cancellare quando l''annullo e'' parziale. Ritorna il numero di RIGHE RESO riaperte. GATE NC: consuma script.fn_check_rinuncia_reversibile, oggi senza motivi ostativi - quando la slice NC arrivera'', il divieto si aggiunge LA'' e questa madre lo solleva da se''. rev 2026-07-26. ⭐ rev 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine §5.2): la proiezione dello stato dell''ordine e'' il building block vendite.fn_ordine_proietta_stato_evasione; la copia scritta a mano qui si ritira (regola del 2). Comportamento invariato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
