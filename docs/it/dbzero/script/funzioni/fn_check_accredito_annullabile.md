{% include-markdown "it/dbzero/script/manual/fn_check_accredito_annullabile.md" %}
# ⚙️ Funzione `fn_check_accredito_annullabile`

```sql
CREATE FUNCTION fn_check_accredito_annullabile(p_resi_riga_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_accredito_annullabile(p_resi_riga_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono di ANNULLARE l'accredito
--   di una riga di reso. Funzione PURA (fn_check_*): nessun raise di
--   dominio, nessuna scrittura.
-- Consumatori: vendite.fn_annulla_accredito_riga_reso (solleva il
--   codice del PRIMO motivo) e il read-side — vw_resi_da_accreditare
--   e le righe del reso — per spegnere il pulsante e dire perche',
--   invece di far scoprire il vincolo sbagliando.
-- Ritorna: [] se l'accredito si puo' annullare; altrimenti array
--   ORDINATO di {codice, reason, reason_key, dettaglio, valori}.
--   `valori` e' il VARIADIC che la madre passa a
--   fn_log_and_raise_error: sta qui perche' la frase che l'operatore
--   legge non si ricomponga in due posti diversi.
DECLARE
    v_motivi        jsonb := '[]'::jsonb;
    -- integer espliciti: sono CONTEGGI, non il valore di una colonna.
    v_n_coppie      integer;
    v_n_rettifiche  integer;
    v_n_viste       integer;
    v_n_bloccate    integer;
    -- ⚠️ bigint[] esplicito: colonna%TYPE[] non esiste in PostgreSQL.
    v_ids           bigint[];
BEGIN
    -- Guard parametro (AGENTS.md): un id assente o non positivo non
    -- esce da nessuna interfaccia, lo produce un chiamante rotto.
    IF p_resi_riga_id IS NULL OR p_resi_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script','fn_check_accredito_annullabile','E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro','resi_riga_id','valore',p_resi_riga_id),
            NULL::uuid, 'resi_riga_id obbligatorio (>0)');
    END IF;

    -- ---- L'INSIEME -------------------------------------------------
    -- Si legge dal ponte, che NON ha RLS: e' la sola fonte che dica la
    -- verita' su quante rettifiche compongono questo accredito.
    -- Due conteggi distinti e non uno: oggi il rapporto coppia/rettifica
    -- e' 1:1 per costruzione, ma nessun vincolo lo impone
    -- (uq_resi_accrediti_pair e' sulla coppia, non su
    -- commessa_attivita_id).
    SELECT count(*)::integer,
           count(DISTINCT a.commessa_attivita_id)::integer,
           array_agg(DISTINCT a.commessa_attivita_id)
      INTO v_n_coppie, v_n_rettifiche, v_ids
      FROM vendite.resi_righe_accrediti a
     WHERE a.resi_riga_id = p_resi_riga_id;

    -- ---- MOTIVO 1 — non c'e' niente da annullare -------------------
    -- ⚠️ «Mai accreditato» e «gia' annullato» finiscono qui INSIEME, e
    --    non e' un difetto: l'annullo cancella le righe di ponte,
    --    quindi lo stato osservabile e' lo stesso. Un flag per
    --    distinguerle sarebbe il soft-delete che romperebbe il gate
    --    della rinuncia E la guardia dell'annullo reso (C-3).
    IF COALESCE(v_n_coppie, 0) = 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_ACCREDITO_NON_TROVATO',
            'reason',     'NESSUN_ACCREDITO',
            'reason_key', 'vendite.resi.annullo_blocco.nessun_accredito',
            'dettaglio',  p_resi_riga_id,
            'valori',     jsonb_build_array(p_resi_riga_id::text));
        -- I due motivi successivi leggono l'insieme: senza insieme non
        -- hanno niente da dire, e aggiungerli direbbe il falso.
        RETURN v_motivi;
    END IF;

    -- ---- MOTIVO 2 — il perimetro ----------------------------------
    -- vendite.commesse_attivita ha la RLS, il ponte no: una rettifica
    -- fuori perimetro emittente si legge come «non c'e'». Zero non e'
    -- un dato, e' fail-closed — e la madre rifiuterebbe comunque, qui
    -- si dice PERCHE' prima che l'operatore ci sbatta.
    SELECT count(*)::integer
      INTO v_n_viste
      FROM vendite.commesse_attivita ca
     WHERE ca.id = ANY(v_ids);

    IF v_n_viste <> v_n_rettifiche THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_ACCREDITO_ANNULLO_INCOMPLETO',
            'reason',     'FUORI_PERIMETRO',
            'reason_key', 'vendite.resi.annullo_blocco.fuori_perimetro',
            'dettaglio',  jsonb_build_object('viste',  v_n_viste,
                                             'attese', v_n_rettifiche),
            'valori',     jsonb_build_array(p_resi_riga_id::text,
                                            v_n_viste::text,
                                            v_n_rettifiche::text));
        -- Il motivo 3 conterebbe su un insieme che non si vede tutto:
        -- direbbe un numero piu' basso del vero.
        RETURN v_motivi;
    END IF;

    -- ---- MOTIVO 3 — almeno una rettifica e' uscita dalla finestra --
    -- ⛔ TUTTO-O-NIENTE: basta UNA rettifica bloccata per rifiutare
    --    l'intero accredito. Un annullo parziale lascerebbe la coda a
    --    chiedere un residuo che nessuno puo' piu' soddisfare, che e'
    --    la malattia per cui il cantiere esiste.
    -- ⚠️ Le TRE condizioni si tengono tutte e tre: dopo un reset di
    --    lotto la riga di attivita_fatturabili SOPRAVVIVE
    --    (fn_cleanup_fatture_by_ids la sblocca e le azzera
    --    fattura_riga_id, non la cancella). «Esiste una AF ->
    --    bloccato» vieterebbe per sempre l'annullo dopo un reset
    --    legittimo: e' il ramo che sembra piu' prudente ed e' sbagliato.
    SELECT count(*)::integer
      INTO v_n_bloccate
      FROM vendite.commesse_attivita ca
     WHERE ca.id = ANY(v_ids)
       AND ( ca.stato_emissione <> 'NON_EMESSA'
             OR EXISTS (
                 SELECT 1
                   FROM vendite.attivita_fatturabili af
                  WHERE af.commessa_attivita_id = ca.id
                    AND ( COALESCE(af.lock_in_fatturazione, false)
                          OR af.fattura_riga_id IS NOT NULL ) ) );

    IF v_n_bloccate > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_ACCREDITO_ANNULLO_NON_AMMESSO',
            'reason',     'RETTIFICA_EMESSA',
            'reason_key', 'vendite.resi.annullo_blocco.rettifica_emessa',
            'dettaglio',  jsonb_build_object('bloccate', v_n_bloccate,
                                             'totali',   v_n_rettifiche),
            'valori',     jsonb_build_array(p_resi_riga_id::text,
                                            v_n_bloccate::text,
                                            v_n_rettifiche::text));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_accredito_annullabile(p_resi_riga_id bigint)
IS 'I motivi che impediscono di ANNULLARE l''accredito di una riga di reso. Funzione PURA (fn_check_*), undicesima della famiglia: nessun raise di dominio, nessuna scrittura. Ritorna [] se si puo'' annullare, altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio, valori}. ⭐ SORGENTE UNICA condivisa da vendite.fn_annulla_accredito_riga_reso (che solleva il codice del PRIMO motivo) e dal read-side — vw_resi_da_accreditare e le righe del reso — che spegne il pulsante e mostra il perche''. Nasce da una richiesta del team BE del 2026-08-25: il pulsante «Annulla l''accredito» era acceso anche quando l''annullo non era piu'' possibile, e l''operatore scopriva il vincolo dopo aver scritto il motivo obbligatorio e confermato. ⛔ E'' UNA SEDE SOLA, non un predicato gemello: se lettura e guardia divergessero si tornerebbe al punto di partenza, col pulsante spento su un annullo che sarebbe passato. E la madre avverte gia'' di un vincolo reciproco su TRE posti (C-3) — un predicato ricopiato ne farebbe un quarto. ⚠️ L''ORDINE dei motivi e'' il contratto, perche'' la madre solleva il primo: (1) nessun accredito, che copre insieme «mai accreditato» e «gia'' annullato» perche'' l''annullo cancella; (2) fuori perimetro, che nasce dalla RLS su commesse_attivita mentre il ponte non ce l''ha — e'' l''unico motivo che dipende da CHI GUARDA; (3) almeno una rettifica bloccata. I motivi 2 e 3 leggono l''insieme, quindi ognuno esce subito: senza insieme direbbero il falso, e su un insieme non visibile per intero il conteggio uscirebbe piu'' basso del vero. ⚠️ Le TRE condizioni del motivo 3 si tengono tutte e tre: dopo un reset di lotto la riga di attivita_fatturabili SOPRAVVIVE sbloccata e senza fattura_riga_id, quindi «esiste una AF -> bloccato» vieterebbe per sempre l''annullo dopo un reset legittimo. ⛔ TUTTO-O-NIENTE: basta UNA rettifica bloccata per rifiutare l''intero accredito, perche'' un annullo parziale lascerebbe la coda a chiedere un residuo che nessuno puo'' piu'' soddisfare. ℹ️ `valori` porta il VARIADIC che la madre passa a fn_log_and_raise_error: sta qui perche'' la frase che l''operatore legge non si ricomponga in due posti. I tre `codice` esistono gia'' a catalogo — questa funzione non li solleva, li nomina. Brief: brief-design-note-credito-resi §45.';
```

</div>

---
{% include-markdown "signature-core.md" %}
