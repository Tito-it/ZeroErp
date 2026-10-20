{% include-markdown "it/dbzero/script/manual/fn_check_annullo_movimento_titolo_iva.md" %}
# ⚙️ Funzione `fn_check_annullo_movimento_titolo_iva`

```sql
CREATE FUNCTION fn_check_annullo_movimento_titolo_iva(p_movimento_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_annullo_movimento_titolo_iva(p_movimento_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'anagrafiche', 'config', 'script'
AS $function$
-- Scopo: elencare i motivi che impediscono di ANNULLARE un
--   movimento del registro plafond IVA. Funzione PURA
--   (fn_check_*): nessun raise di dominio, nessuna scrittura.
-- Consumatori: anagrafiche.fn_annulla_movimento_titolo_iva
--   (solleva il codice del PRIMO motivo) e il read-side
--   vw_stiva_movimenti_dettaglio, che spegne il pulsante e dice
--   perche' invece di far scoprire il vincolo sbagliando.
-- Ritorna: [] se l'annullo si puo' fare; altrimenti array
--   ORDINATO di {codice, reason, reason_key, dettaglio, valori}.
--   `valori` e' il VARIADIC che la madre passa a
--   fn_log_and_raise_error: sta qui perche' la frase che
--   l'operatore legge non si ricomponga in due posti diversi.
--   Piano: brief-db-titoli-iva-movimenti-annullo, decisione B-3.
--
-- ⛔ SECURITY DEFINER: legge una riga di
--   anagrafiche.soggetti_titoli_iva_movimenti, che ha la RLS
--   attiva. Da INVOKER non distinguerebbe «non esiste» da «non la
--   vedo» — mentre la FK, che la RLS la scavalca sempre,
--   accetterebbe lo stesso riferimento: i due divergerebbero in
--   silenzio. Il perimetro non si perde, perche' la MADRE resta
--   INVOKER e l'INSERT passa comunque dalla policy.
DECLARE
    v_motivi     jsonb := '[]'::jsonb;
    v_mov        RECORD;
    v_n_annulli  integer;
    v_somma_post anagrafiche.soggetti_titoli_iva.imponibile_utilizzato%TYPE;
    v_tipo_descr config.tipi_titolo_iva.descrizione%TYPE;
BEGIN
    -- Guard di parametro: un id assente o non positivo non esce da
    -- nessuna interfaccia, lo produce un chiamante rotto — quindi
    -- e' TECNICO, e la frase nomina il parametro perche' il
    -- lettore e' chi ha scritto la chiamata.
    IF p_movimento_id IS NULL OR p_movimento_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script','fn_check_annullo_movimento_titolo_iva',
            'E_TITOLO_IVA_ANNULLO_INCOERENTE',
            jsonb_build_object('parametro','p_movimento_id',
                               'valore', p_movimento_id),
            NULL::uuid,
            COALESCE(p_movimento_id::text, 'assente'),
            'identificativo del movimento non valido');
    END IF;

    SELECT m.id, m.titolo_iva_id, m.tipo_movimento, m.imponibile,
           m.data_movimento, m.annulla_movimento_id
      INTO v_mov
      FROM anagrafiche.soggetti_titoli_iva_movimenti m
     WHERE m.id = p_movimento_id;

    -- ---- MOTIVO 0 — non c'e' niente da annullare ---------------
    -- ⚠️ Qui «non esiste» e' davvero «non esiste»: la funzione e'
    --   DEFINER, quindi non c'e' il caso «non lo vedo» che
    --   renderebbe ambiguo questo ramo.
    IF NOT FOUND THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_TITOLO_IVA_ANNULLO_NON_AMMESSO',
            'reason',     'MOVIMENTO_NON_TROVATO',
            'reason_key', 'anagrafiche.titoli_iva.annullo_blocco.non_trovato',
            'dettaglio',  jsonb_build_object('movimento_id', p_movimento_id),
            'valori',     jsonb_build_array('', ''));
        -- I motivi successivi leggono il movimento: senza, non
        -- hanno niente da dire e aggiungerli direbbe il falso.
        RETURN v_motivi;
    END IF;

    SELECT tt.descrizione
      INTO v_tipo_descr
      FROM anagrafiche.soggetti_titoli_iva t
      JOIN config.tipi_titolo_iva tt ON tt.id = t.tipo_titolo_iva_id
     WHERE t.id = v_mov.titolo_iva_id;

    -- ---- MOTIVO 1 — non e' una forzatura ----------------------
    -- Un movimento FATTURA o NOTA_CREDITO e' il riflesso di un
    -- documento: si corregge DAL DOCUMENTO, con una nota di
    -- credito, ed e' materia di I4. Annullarlo qui scollegherebbe
    -- il plafond dal documento che lo ha consumato.
    IF v_mov.tipo_movimento IS DISTINCT FROM 'FORZATURA' THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_TITOLO_IVA_ANNULLO_NON_AMMESSO',
            'reason',     'NON_FORZATURA',
            'reason_key', 'anagrafiche.titoli_iva.annullo_blocco.non_forzatura',
            'dettaglio',  jsonb_build_object('movimento_id', v_mov.id,
                                             'tipo_movimento', v_mov.tipo_movimento),
            'valori',     jsonb_build_array(
                              COALESCE(v_tipo_descr, ''),
                              to_char(v_mov.data_movimento, 'DD/MM/YYYY')));
        -- I due motivi che seguono valgono solo sulle forzature.
        RETURN v_motivi;
    END IF;

    -- ---- MOTIVO 2 — e' esso stesso un annullo -----------------
    -- Decisione B-2 di Tid (2026-08-30): un annullo non si
    -- annulla. Se la forzatura serve ancora, se ne scrive una
    -- NUOVA col suo motivo — il registro si legge come un racconto
    -- dritto invece che come una catena da risalire.
    IF v_mov.annulla_movimento_id IS NOT NULL THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_TITOLO_IVA_ANNULLO_NON_AMMESSO',
            'reason',     'RIGA_DI_ANNULLO',
            'reason_key', 'anagrafiche.titoli_iva.annullo_blocco.e_un_annullo',
            'dettaglio',  jsonb_build_object('movimento_id', v_mov.id,
                                             'annulla_movimento_id', v_mov.annulla_movimento_id),
            'valori',     jsonb_build_array(
                              COALESCE(v_tipo_descr, ''),
                              to_char(v_mov.data_movimento, 'DD/MM/YYYY')));
    END IF;

    -- ---- MOTIVO 3 — e' gia' annullato ------------------------
    -- L'indice unique parziale lo impedirebbe comunque, ma con un
    -- errore di vincolo: qui si dice PERCHE', e prima del clic.
    SELECT count(*)::integer
      INTO v_n_annulli
      FROM anagrafiche.soggetti_titoli_iva_movimenti a
     WHERE a.annulla_movimento_id = v_mov.id;

    IF COALESCE(v_n_annulli, 0) > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_TITOLO_IVA_ANNULLO_NON_AMMESSO',
            'reason',     'GIA_ANNULLATO',
            'reason_key', 'anagrafiche.titoli_iva.annullo_blocco.gia_annullato',
            'dettaglio',  jsonb_build_object('movimento_id', v_mov.id),
            'valori',     jsonb_build_array(
                              COALESCE(v_tipo_descr, ''),
                              to_char(v_mov.data_movimento, 'DD/MM/YYYY')));
    END IF;

    -- ---- MOTIVO 4 — porterebbe l'usato sotto zero ------------
    -- ⚠️ Non e' un caso di scuola: basta che nel frattempo le note
    --   di credito superino le fatture su quel titolo. Senza
    --   questo motivo l'operatore prenderebbe
    --   E_TITOLO_IVA_UTILIZZATO_NEGATIVO dall'accumulatore — vero,
    --   ma che in quel momento non spiega ne' cosa e' successo ne'
    --   cosa puo' fare.
    -- ⭐ Si calcola la somma SENZA questo movimento, che e'
    --   esattamente cio' che l'accumulatore troverebbe dopo aver
    --   sommato il contro-movimento: -x annulla +x.
    SELECT COALESCE(SUM(m.imponibile), 0)
      INTO v_somma_post
      FROM anagrafiche.soggetti_titoli_iva_movimenti m
     WHERE m.titolo_iva_id = v_mov.titolo_iva_id
       AND m.id <> v_mov.id;

    IF v_somma_post < 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_TITOLO_IVA_ANNULLO_NON_AMMESSO',
            'reason',     'PLAFOND_NEGATIVO',
            'reason_key', 'anagrafiche.titoli_iva.annullo_blocco.plafond_negativo',
            'dettaglio',  jsonb_build_object('movimento_id', v_mov.id,
                                             'titolo_iva_id', v_mov.titolo_iva_id,
                                             'somma_post', v_somma_post),
            'valori',     jsonb_build_array(
                              COALESCE(v_tipo_descr, ''),
                              to_char(v_mov.data_movimento, 'DD/MM/YYYY')));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_annullo_movimento_titolo_iva(p_movimento_id bigint)
IS 'Funzione PURA (fn_check_*): i motivi che impediscono di ANNULLARE un movimento del registro plafond IVA. ⭐ rev 2026-08-31: il `reason` del motivo «e'' esso stesso un annullo» passa da E_UN_ANNULLO a RIGA_DI_ANNULLO. ⛔ Il vecchio nome non era un errore di dominio ma una frase italiana abbreviata («e'' un annullo»), e il prefisso E_ lo faceva leggere come un CODICE dal guardrail che cerca i letterali E_* nei corpi delle funzioni: il test apps/core/tests/test_error_codes_db_policy_guardrail.py lo segnalava come codice senza policy. Il codice vero e'' e resta E_TITOLO_IVA_ANNULLO_NON_AMMESSO, che e'' a catalogo — E_UN_ANNULLO non lo e'' mai stato. ⭐ Il nuovo nome NON e'' GIA_UN_ANNULLO, ed e'' una scelta: accanto vive gia'' GIA_ANNULLATO, e i due dicono cose OPPOSTE — questa riga E'' l''annullo di un''altra, contro questa riga E'' STATA annullata. Due motivi che differiscono per una parola, su un pulsante spento, si leggono male esattamente quando conta: RIGA_DI_ANNULLO dice COSA E'' la riga invece di ripetere l''avverbio. ⚠️ Il `reason_key` NON cambia (…annullo_blocco.e_un_annullo): e'' un INDIRIZZO, non un valore, e il frontend rende il testo da li'' — cambiarlo costerebbe due file di locales per comprare zero. ⚠️ La convenzione ora e'' scritta in linee-guida-sql §12.5.1: un `reason` di fn_check_* non porta il prefisso E_, riservato ai codici a catalogo. Gli altri quattro reason di questa funzione la rispettavano gia''. Piano: brief-db-reason-e-un-annullo-collide-col-prefisso. Ritorna [] se ammesso, altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio, valori}. Motivi, in ordine: movimento non trovato · non e'' una FORZATURA (un FATTURA si corregge dal documento, con una nota di credito - I4) · e'' esso stesso un annullo (decisione B-2: un annullo non si annulla, se la forzatura serve ancora se ne scrive una nuova) · e'' gia'' annullato · l''annullo porterebbe l''usato del titolo sotto zero. ⭐ Due lettori della stessa regola: vw_stiva_movimenti_dettaglio spegne il pulsante col motivo, e anagrafiche.fn_annulla_movimento_titolo_iva la CHIAMA invece di riscrivere il predicato — cosi'' non possono divergere. ⚠️ L''ordine dell''array e'' il contratto: la superficie mostra il primo motivo e la madre solleva il primo codice. ⛔ SECURITY DEFINER, e non e'' pigrizia: la tabella ha la RLS attiva e da INVOKER la lettura non distinguerebbe «non esiste» da «non la vedo», mentre la FK la RLS la scavalca sempre — i due divergerebbero in silenzio. La MADRE resta INVOKER, quindi il perimetro sulla scrittura non si perde. `valori` e'' il VARIADIC della madre e sta qui perche'' la frase non si ricomponga in due posti. Piano: brief-db-titoli-iva-movimenti-annullo, B-b.';
```

</div>

---
{% include-markdown "signature-core.md" %}
