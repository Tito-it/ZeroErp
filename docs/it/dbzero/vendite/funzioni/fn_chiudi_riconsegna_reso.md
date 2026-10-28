{% include-markdown "it/dbzero/vendite/manual/fn_chiudi_riconsegna_reso.md" %}
# ⚙️ Funzione `fn_chiudi_riconsegna_reso`

```sql
CREATE FUNCTION fn_chiudi_riconsegna_reso(p_reso_id bigint, p_righe jsonb, p_note character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_chiudi_riconsegna_reso(p_reso_id bigint, p_righe jsonb DEFAULT NULL::jsonb, p_note character varying DEFAULT NULL::character varying)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- Scopo: madre della CHIUSURA della ri-consegna. Dichiara che una
--   quota di merce resa PER RI-CONSEGNA non tornera' al cliente:
--   scrive vendite.resi_righe_rinunce e ri-proietta lo stato ordine
--   (il residuo si chiude -> EVASO).
--   Speculare a fn_genera_ddt_riconsegna: stesso gate, stessa
--   semantica p_righe, stesso errore "niente da lavorare".
--   Brief: brief-db-chiusura-riconsegna-reso-definitivo §4.3.
-- Ritorna: numero di righe reso chiuse (quante rinunce scritte).
--
-- NON crea documenti e NON cambia numeri (brief §3): l'importo
--   dell'accredito resta identico, cambia la NATURA della quota
--   pendente (da "tornera' indietro" a "definitiva"). L'accredito
--   passa da FACOLTATIVA a DOVUTA in vw_resi_da_accreditare.
--
-- MERCE FISICA (§5.4): la quota rinunciata resta materialmente al
--   fornitore. Senza modulo magazzino non c'e' nulla da movimentare;
--   quando il magazzino arrivera', il movimento parte da qui.
DECLARE
    v_stato          config.stati_doc_reso.codice_interno%TYPE;
    v_riga           RECORD;
    v_ord            RECORD;
    v_residuo        numeric;
    v_qta            numeric;
    v_n              integer := 0;
BEGIN
    -- 1) Guard input.
    IF p_reso_id IS NULL OR p_reso_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_chiudi_riconsegna_reso','E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro','reso_id','valore',p_reso_id),
            NULL::uuid, 'reso_id obbligatorio (>0)');
    END IF;

    -- 2) Reso esistente e CONFERMATO (stesso gate della generazione:
    --    si chiude cio' che si potrebbe ri-spedire).
    SELECT sdr.codice_interno
      INTO v_stato
      FROM vendite.resi r
      JOIN config.stati_doc_reso sdr ON sdr.id = r.stato_doc_reso_id
     WHERE r.id = p_reso_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_chiudi_riconsegna_reso','E_RESO_NOT_FOUND',
            jsonb_build_object('reso_id', p_reso_id),
            NULL::uuid, p_reso_id::text);
    END IF;

    IF v_stato IS DISTINCT FROM 'CONFERMATO' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_chiudi_riconsegna_reso','E_RESO_NON_CONFERMATO',
            jsonb_build_object('reso_id', p_reso_id, 'stato', v_stato),
            NULL::uuid, p_reso_id::text, COALESCE(v_stato,'NULL'));
    END IF;

    -- 3) Righe di tipo ri-consegna con copertura residua.
    --    Il residuo viene dall'helper unico (al netto di ri-consegne
    --    E rinunce precedenti): una riga gia' chiusa o gia' tutta
    --    ri-spedita ha residuo 0 e viene saltata.
    FOR v_riga IN
        SELECT rr.id AS resi_riga_id,
               vendite.fn_resi_riga_residuo_riconsegna(rr.id) AS residuo,
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
        v_residuo := v_riga.residuo;
        IF v_residuo <= 0 THEN
            CONTINUE;  -- nulla da chiudere su questa riga
        END IF;

        -- p_righe NULL = si chiude TUTTA la copertura residua.
        -- Altrimenti si tronca la richiesta al residuo (race-proof,
        -- stessa disciplina della generazione).
        IF p_righe IS NOT NULL THEN
            v_qta := LEAST(COALESCE(v_riga.qta_richiesta, 0), v_residuo);
        ELSE
            v_qta := v_residuo;
        END IF;
        IF v_qta IS NULL OR v_qta <= 0 THEN
            CONTINUE;
        END IF;

        -- Unica scrittura di dominio: la dichiarazione. Il guard
        -- trgfn_resi_rinunce_guard verifica tipo e non-eccedenza.
        INSERT INTO vendite.resi_righe_rinunce (resi_riga_id, qta, note)
        VALUES (v_riga.resi_riga_id, v_qta, p_note);

        v_n := v_n + 1;
    END LOOP;

    -- 4) Niente da chiudere -> errore parlante (riuso del codice
    --    della gemella: la condizione e' la stessa, "nessuna
    --    ri-consegna pendente su cui agire").
    IF v_n = 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_chiudi_riconsegna_reso','E_RESO_NESSUNA_RICONSEGNA_PENDENTE',
            jsonb_build_object('reso_id', p_reso_id, 'righe', p_righe),
            NULL::uuid, p_reso_id::text);
    END IF;

    -- 5) Ri-proiezione stato ordine: e' il passo che CHIUDE l'ordine.
    --    La quota rinunciata non pesa piu' sull'addendo reso
    --    (fn_ordine_riga_qta_riconsegna, rev 2026-07-26), quindi se
    --    non resta altro residuo l'ordine passa a EVASO.
    --    Identico allo step 7 di fn_genera_ddt_riconsegna.
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

COMMENT ON FUNCTION vendite.fn_chiudi_riconsegna_reso(p_reso_id bigint, p_righe jsonb, p_note character varying)
IS 'Madre CHIUSURA ri-consegna (brief-db-chiusura-riconsegna-reso-definitivo S4.3): dichiara che una quota di merce resa PER RI-CONSEGNA non tornera'' al cliente. Scrive vendite.resi_righe_rinunce e ri-proietta lo stato ordine (il residuo si chiude -> EVASO). Speculare a fn_genera_ddt_riconsegna: gate reso CONFERMATO, p_righe NULL = tutta la copertura residua altrimenti [{resi_riga_id, qta}] troncata al residuo, E_RESO_NESSUNA_RICONSEGNA_PENDENTE se non c''e'' nulla da chiudere. Ritorna il numero di righe chiuse. NON crea documenti e NON cambia numeri: l''importo dell''accredito resta identico, passa solo da FACOLTATIVA a DOVUTA. MERCE FISICA: la quota rinunciata resta materialmente al fornitore - senza modulo magazzino non c''e'' nulla da movimentare, ma quando il magazzino arrivera'' il movimento parte da qui (S5.4). rev 2026-07-26. ⭐ rev 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine §5.2): la proiezione dello stato dell''ordine e'' il building block vendite.fn_ordine_proietta_stato_evasione; la copia scritta a mano qui si ritira (regola del 2). Comportamento invariato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
