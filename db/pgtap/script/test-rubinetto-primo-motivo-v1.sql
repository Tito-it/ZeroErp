-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: P-2 — IL RUBINETTO della coda «solleva il primo motivo»
--       Piano: brief-db-coda-primo-motivo-in-un-posto-solo, sezione 7
-- ------------------------------------------------------------
-- Elenco test (plan 7) — numerati come li stampa il TAP:
--  1) l'helper esiste, con la firma dichiarata
--  2) ⭐⭐ IL RUBINETTO: zero punti IN PERIMETRO sollevano il primo motivo a mano
--  3) ⭐ zero punti NON CLASSIFICATI — un presidio che non sa leggere un sito
--        deve diventare ROSSO, non saltarlo
--  4) il debito FUORI perimetro non cresce (soglia 6, puo' solo calare)
--  5) le venticinque funzioni bonificate CHIAMANO davvero l'helper (una
--        chiamata, non una menzione: i commenti sono fuori dal conteggio)
--  6) ⚠️ il marcatore non e' troppo LARGO: un codice LETTERALE resta fuori
--  7) ⭐⭐ la canarina: il marcatore non e' troppo STRETTO
--
-- Scopo:
--   ⭐⭐ QUESTO E' IL PRESIDIO CHE CONTA, piu' della bonifica. Senza, i dieci
--   punti sanati tornano: chi scrive una fn_check_* copia la coda dalla guard
--   accanto, ed e' cosi' che si e' arrivati a ventitre' senza che nessuno
--   avesse deciso niente. «Rincorrere gli esistenti senza chiudere il rubinetto
--   e' la forma in cui questi registri non calano mai.»
--
--   ⭐ IL PERIMETRO SI DERIVA, NON SI ELENCA. Un punto e' in perimetro quando
--   fa DUE cose insieme:
--     1) il CODICE che solleva non e' un letterale: lo legge da un motivo
--     2) la fn_check_* da cui viene l'array emette `valori`
--   Solo li' l'helper puo' stare. Dove la check NON emette `valori` la frase la
--   compone il chiamante dai propri dati, e delegare la spezzerebbe:
--   uscirebbero i `%s` grezzi a video (§2.2 del brief). ⇒ Li' il `-> 0` e'
--   LEGITTIMO, e pretendere zero anche li' sarebbe un cancello che boccia il
--   caso giusto — dopo due blocchi sbagliati qualcuno lo spegne.
--   ⭐ Derivandolo, una check che domani aggiunge `valori` fa entrare il suo
--   sito nel perimetro DA SOLA, senza che nessuno aggiorni un elenco.
--
--   🔴 IL MARCATORE E' `->> 'codice'` E NON `-> 0 ->> 'codice'`, e questa riga
--   e' costata una prova per mutazione. Col secondo, il presidio era VERDE PER
--   COSTRUZIONE: prendeva solo la forma scritta INLINE, mentre i dieci siti
--   bonificati usano una variabile d'appoggio —
--       v_primo := v_motivi -> 0;      <- riga a se'
--       ... v_primo ->> 'codice' ...   <- dentro la chiamata
--   cioe' proprio la forma che questo cantiere ha appena tolto non era
--   presidiabile. Rimessa a mano una coda vecchia, il conteggio non si muoveva.
--   ⇒ L'invariante VERO non e' come e' scritto l'indice: e' che **il codice non
--   e' un letterale**. Ed e' lo stesso fatto che rende questi siti invisibili
--   al rubinetto degli accumulatori, che i letterali `'E_...'` li cerca (§7.3).
--
--   ⚠️ QUESTO FILE LEGGE `pg_proc.prosrc`, cioe' il TESTO delle funzioni. E'
--   un'euristica, e va detto: riconosce la forma scritta, non il significato.
--   Per questo esistono il test 3 (un sito che non si riesce a legare alla sua
--   check e' ROSSO, non saltato) e il test 7 (la canarina che si accorge se il
--   marcatore viene ristretto).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- Fixture — la classificazione, in una vista temporanea sola: i test la
--   interrogano invece di ripetere la derivazione cinque volte (e di poter
--   divergere fra loro, che e' il difetto classico dei presidi copiati).
-- ============================================================

-- ⭐ DAL 2026-09-08 LA DERIVAZIONE NON VIVE PIU' QUI (passo V-0 del brief
--   «i motivi si fermano dentro la check»). Stava in questo `pg_temp`, dove
--   nessun altro presidio poteva leggerla — e infatti lo scanner dell'arita'
--   dei messaggi, che ne aveva bisogno, se la sarebbe ricopiata: due letture
--   dello stesso fatto che cominciano a dissentire senza che nessuno lo veda.
--   Adesso e' dbops.vw_punti_primo_motivo (changeSet 20260908-34), e questo
--   file la INTERROGA. Le regole portanti — marcatore `->> 'codice'` e non
--   `-> 0 ->> 'codice'`, tutte le fn_check_* nominate nel corpo e non solo
--   quella assegnata a `v_motivi`, perimetro PESSIMISTA — sono le stesse, e
--   stanno scritte nel commento della vista.
-- ⚠️ Da qui in avanti questo file DIPENDE da quella vista.

-- Il testimone del test 7 nasce PRIMA della fotografia qui sotto, perche' la
--   canarina legga la stessa fotografia dei test 2-6 (vedi laggiu').
CREATE FUNCTION pg_temp.pgtap_coda_variabile_appoggio() RETURNS void
LANGUAGE plpgsql AS $f$
DECLARE
    v_motivi jsonb;
    v_primo  jsonb;
BEGIN
    v_motivi := script.fn_check_sorgente_chiudibile(1::bigint, 'PGTAP');
    IF jsonb_array_length(v_motivi) > 0 THEN
        v_primo := v_motivi -> 0;
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'pgtap_coda_variabile_appoggio', v_primo ->> 'codice',
            '{}'::jsonb, NULL::uuid,
            VARIADIC ARRAY(SELECT jsonb_array_elements_text(v_primo -> 'valori')));
    END IF;
END
$f$;

-- ⭐ UNA FOTOGRAFIA, NON CINQUE LETTURE (2026-10-10). La vista scandisce
--   pg_proc ed e' cara (~1,4 s a lettura come app, misurato il 2026-10-10 su
--   dbdev): letta attraverso una TEMP VIEW dai test 2, 3, 4, 6 e di nuovo dal 7
--   costava ~7 s. Fra le asserzioni non si crea e non si scrive niente, quindi
--   il file ha un MOMENTO solo e la copia contiene esattamente le righe della
--   vista viva. Si fotografa la vista intera, com'e': il filtro sui testimoni e
--   l'aggregazione restano nella TEMP VIEW sopra, non riscritti nella copia.
CREATE TEMP TABLE _vw_punti_primo_motivo AS
SELECT * FROM dbops.vw_punti_primo_motivo;

CREATE TEMP VIEW punti_primo_motivo AS
SELECT sch,
       fn,
       count(DISTINCT check_funzione)::int                 AS check_trovate,
       -- (i testimoni del test 7 restano fuori dai conteggi: vedi laggiu')
       -- ⭐ PESSIMISTA: basta UNA delle check nominate che emetta `valori`
       --   perche' il sito sia in perimetro. Un presidio che sceglie il ramo
       --   ottimista assolve il caso che dovrebbe segnalare.
       coalesce(bool_or(check_emette_valori), false)       AS in_perimetro
  FROM _vw_punti_primo_motivo
 WHERE fn !~ '^pgtap_'
 GROUP BY sch, fn;

-- ============================================================
-- Asserzioni
-- ============================================================

-- 1) L'helper c'e', e con la firma che il brief dichiara. ⚠️ Il confronto
--    include i NOMI dei parametri, perche' pg_get_function_identity_arguments()
--    li restituisce: scritta coi soli tipi, questa asserzione e' rossa a vuoto.
SELECT is(
    (SELECT pg_get_function_identity_arguments(p.oid)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script' AND p.proname = 'fn_raise_primo_motivo_se_presente'),
    'p_area text, p_funzione text, p_motivi jsonb, p_campo text, p_tx_id uuid, p_context_extra jsonb',
    'script.fn_raise_primo_motivo_se_presente esiste con la firma dichiarata');

-- 2) ⭐⭐ IL RUBINETTO. Zero, e non «pochi»: qui l'helper puo' stare, quindi
--    ogni punto rimasto e' una coda copiata.
SELECT is(
    (SELECT count(*)::int FROM punti_primo_motivo WHERE in_perimetro),
    0,
    'nessun punto IN PERIMETRO solleva ancora il primo motivo a mano');

-- 3) ⭐ Il ramo cieco e' rosso. Un punto marcato di cui non si trovi nessuna
--    fn_check_* non e' «a posto»: e' un sito che il presidio non sa leggere, e
--    un presidio che salta cio' che non capisce diventa verde per sottrazione.
SELECT is(
    (SELECT count(*)::int FROM punti_primo_motivo WHERE check_trovate = 0),
    0,
    'ogni punto marcato si riesce a legare alla sua check: nessun ramo cieco');

-- 4) Il debito fuori perimetro. ⚠️ E' un REGISTRO, non una lista di eccezioni:
--    la soglia puo' solo calare. Cala quando una di quelle check impara a
--    emettere `valori` e il suo sito passa all'helper — il cantiere lasciato
--    aperto nel §6 del brief.
--    ⛔ Non si alza per far passare la CI: un numero piu' alto significa che
--    qualcuno ha scritto una coda nuova, ed e' esattamente la cosa da vedere.
SELECT cmp_ok(
    (SELECT count(*)::int FROM punti_primo_motivo WHERE NOT in_perimetro),
    '<=', 6,
    -- ⭐ 2026-09-09: da 13 a 6. Sei funzioni sono uscite dal debito con C-1/C-2
    --   (escludi_documento_da_giro, riapri_riconsegna_reso, i guard di
    --   transizione di commesse/ordini/preventivi e il guard della chiusura
    --   sorgente), perche' le loro check hanno imparato a emettere `valori`.
    --   ⛔ Non e' un allentamento: la soglia CALA, ed e' l'unico verso ammesso.
    'il debito dei siti FUORI perimetro non cresce (soglia 6, puo'' solo calare)');

-- 5) La bonifica e' arrivata dove diceva: dieci funzioni chiamano l'helper.
--    ⭐ E' il test che ha morso nella prova per mutazione, quando il 2 non
--    mordeva: rimessa una coda vecchia, qui il conteggio scende a nove.
--    🔴 DAL 2026-09-18 SI CONTA UNA CHIAMATA, NON UNA MENZIONE: si tolgono i
--    commenti `--` e si pretende il nome seguito da `(` — la stessa forma con
--    cui dbops.vw_punti_primo_motivo riconosce `fn_log_and_raise_error\s*\(`.
--    Fino a quel giorno il predicato era `prosrc ~ 'fn_raise_primo_motivo_se_presente'`,
--    cioe' il TESTO: e il 18-09 e' entrata script.fn_check_disponibilita_uscita,
--    una fn_check_* PURA che nel proprio commento di testa nomina l'helper
--    come cosa che fa il suo CONSUMATORE. Il predicato vecchio la contava fra
--    «le funzioni che chiamano l'helper» — 20 invece di 19 — e l'asserzione
--    avrebbe affermato una cosa falsa aggiornando il numero. E' la lezione gia'
--    pagata da `_sorgente_senza_commenti` (2026-08-26): un presidio che cerca
--    una stringa nel sorgente si accende sulla PROSA che la spiega.
SELECT is(
    (SELECT count(*)::int FROM pg_proc p
      WHERE regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ 'fn_raise_primo_motivo_se_presente\s*\('
        AND p.proname <> 'fn_raise_primo_motivo_se_presente'),
    44,
    -- ⚠️ 2026-09-09: da 10 a 16. E' un'uguaglianza ESATTA, non una soglia:
    --   scende se una bonifica viene disfatta (ed e' il test che ha morso nella
    --   prova per mutazione), sale se qualcuno ne bonifica un'altra senza
    --   aggiornare questa riga. In entrambi i casi va guardato.
    -- ⭐ 2026-09-14: da 16 a 17. Non una bonifica: un sito NUOVO nato gia'
    --   sull'helper — pagamenti.trgfn_vendite_contabili_righe_guard_contenuto
    --   (D17, brief riga-manuale-nasce-abbinata-ed-elimina-riga), che solleva
    --   il primo motivo di script.fn_check_riga_contabile_eliminabile.
    -- ⭐ 2026-09-18: da 17 a 19. Due siti NUOVI nati sull'helper col Lotto 2 del
    --   magazzino (brief-db-magazzino-lotto-2-motore): magazzino.fn_scrivi_movimento
    --   (20260918-18, due chiamate: fn_check_riga_magazzino e
    --   fn_check_disponibilita_uscita — si conta la FUNZIONE, non le chiamate)
    --   e magazzino.fn_posta_inventario (20260918-23, fn_check_riga_magazzino).
    --   La terza menzione del giorno — fn_check_disponibilita_uscita — e' un
    --   commento, e da questa rev non conta (vedi sopra).
    -- ⭐ 2026-09-18 (sera): da 19 a 20. Un sito NUOVO nato sull'helper —
    --   pagamenti.trgfn_vendite_contabili_guard_validazione (20260918-37,
    --   D20-a, brief-db-validata-e-registrazione-tardiva), che entrando in
    --   VALIDATA solleva il primo motivo di script.fn_check_contabile_validabile.
    -- ⭐ 2026-09-22: da 20 a 21. Un sito NUOVO, e nasce da una bonifica vera:
    --   magazzino.fn_posta_rettifica (20260922-21, R-1 del Lotto 2-bis) non
    --   controllava piu' stato e righe nel proprio corpo — li chiede a
    --   script.fn_check_documento_interno_registrabile, la STESSA funzione da cui
    --   la capability del drawer accende «Registra», e ne solleva il primo motivo.
    --   La gemella fn_posta_inventario era gia' nel conto dal 18-09 (chiamava
    --   l'helper sul motivo di riga) e non si muove: si conta la FUNZIONE, non le
    --   chiamate.
    -- ⭐ 2026-09-24: da 21 a 23. Due siti NUOVI nati sull'helper col building
    --   block dei prezzi non autorizzati (brief-db-preventivi-congelamento-
    --   pricing): vendite.trgfn_contratti_guard_transizione_stato (20260924-25,
    --   verso ATTIVO) e vendite.trgfn_offerte_commerciali_guard_transizione
    --   (20260924-27, verso EMESSA e ACCETTATA), che sollevano il primo motivo di
    --   script.fn_check_prezzi_autorizzati. Il contratto sostituisce un codice
    --   letterale (E_COMPONENTE_PREZZO_PENDENTE), l'offerta un controllo che non
    --   c'era. Le altre due chiamate nuove dello stesso giro — Regola 3 di
    --   trgfn_preventivi_guard_transizione (-22) e Regola 5 di
    --   trgfn_ordini_guard_transizione (-29) — stanno in funzioni gia' nel conto:
    --   si conta la FUNZIONE, non le chiamate.
    -- ⭐ 2026-09-24 (sera): da 23 a 25. Due siti NUOVI nati sull'helper: le
    --   madri delle revisioni vendite.fn_crea_revisione_preventivo (20260924-34)
    --   e vendite.fn_crea_revisione_offerta (20260924-35), che rifiutano una
    --   revisione col primo motivo di script.fn_check_prezzi_in_attesa (§10 del
    --   brief-db-preventivi-congelamento-pricing).
    -- ⭐ 2026-09-28: da 25 a 26. Un sito NUOVO, e nasce da un'estrazione:
    --   vendite.trgfn_contratti_righe_guard_esclusione_figlio_bundle
    --   (20260928-31) non contiene piu' il predicato del figlio di bundle — lo
    --   chiede a script.fn_check_esclusione_articolo_contratto (20260928-29), la
    --   stessa funzione con cui fn_contratto_righe_preview spegne «Escludi», e ne
    --   solleva il primo motivo (brief-db-liste-righe-documento §8.13).
    -- ⭐ 2026-09-28 (Lotto 3 di magazzino): da 26 a 29. Tre siti NUOVI nati
    --   sull'helper (brief-db-magazzino-lotto-3-scarico-da-ddt):
    --   vendite.fn_cambia_stato_ddt (20260928-75, primo motivo di
    --   script.fn_check_ddt_merce all'emissione), magazzino.fn_posta_trasferimento
    --   (20260928-79, di script.fn_check_documento_interno_registrabile) e
    --   magazzino.fn_apri_blocco (20260928-80, di script.fn_check_riga_magazzino).
    -- ⭐ 2026-09-28 (Lotto 3-bis di magazzino): da 29 a 30. Un sito NUOVO:
    --   vendite.fn_conferma_reso (20260928-95), che alla conferma di un reso che
    --   fa rientrare merce solleva il primo motivo di script.fn_check_reso_merce
    --   (brief-db-magazzino-lotto-3-bis-carico-da-reso).
    -- ⭐ 2026-10-03: da 30 a 31. Un sito NUOVO, e nasce da un debito del
    --   backend: script.fn_blocca_credenziale (20261003-02) solleva il primo
    --   motivo di script.fn_check_credenziale_bloccabile (20261003-01), la
    --   stessa funzione da cui il dettaglio credenziale spegne «Blocca accesso»
    --   (brief-db-credenziale-verbi-amministratore R-DB-A5/A6).
    -- ⭐ 2026-10-06: da 31 a 32. Un sito NUOVO nato sull'helper:
    --   script.fn_elimina_credenziale (20261006-14) solleva il primo motivo di
    --   script.fn_check_credenziale_eliminabile (20261006-13), la stessa
    --   funzione da cui «Altri accessi» spegne «Elimina accesso». Due chiamate
    --   (prima del DELETE e nella rete del 23503): si conta la FUNZIONE
    --   (brief-db-elimina-credenziale-senza-veste §4.2).
    -- ⭐ 2026-10-07: da 32 a 33. Un sito NUOVO nato sull'helper:
    --   vendite.trgfn_contratti_freeze_listino_versione (20261007-45) solleva
    --   il primo motivo di script.fn_check_listino_congelabile (20261007-41),
    --   la stessa funzione da cui fn_available_actions_contratto spegne
    --   «Attiva». La gemella dell'offerta,
    --   vendite.trgfn_offerte_commerciali_guard_transizione (20261007-43), era
    --   gia' nel conto per i prezzi: si conta la FUNZIONE, non le chiamate
    --   (brief-db-offerta-emissione-ed-erogazione §C.1.3).
    -- ⭐ 2026-10-07 (sera): da 33 a 34. Un sito NUOVO nato sull'helper:
    --   script.trgfn_righe_guard_erogazione_perimetro (20261007-63), montato su
    --   contratti_righe e offerte_commerciali_eccezioni, solleva il primo motivo
    --   di script.fn_check_riga_erogazione (20261007-61). La lettura per il form,
    --   vendite.fn_documento_riga_erogazioni, chiama la stessa check ma non solleva
    --   (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3).
    -- ⭐ 2026-10-08: da 34 a 35. Un sito NUOVO nato sull'helper:
    --   script.trgfn_doc_guard_listino_documento (20261008-14), montato su
    --   vendite.contratti e vendite.offerte_commerciali, solleva il primo motivo
    --   di script.fn_check_listino_documento (20261008-13). La lettura per il
    --   form, vendite.fn_listini_selezionabili, chiama la stessa check ma non
    --   solleva (brief-db-offerta-emissione-ed-erogazione §F.2).
    -- ⭐ 2026-10-11: da 35 a 36. Un sito NUOVO nato sull'helper:
    --   vendite.fn_ddt_riga_correggi_qta_evasa (20261011-18) solleva il primo
    --   motivo di script.fn_check_ddt_riga_correggi_qta_evasa (20261011-17), la
    --   stessa funzione da cui vendite.vw_ddt_righe_dettaglio spegne «Correggi
    --   quantita' evasa» (brief-db-ddt-righe-evase-dall-ordine, D-2).
    -- ⭐ 2026-10-11: da 36 a 37. Un sito NUOVO nato sull'helper:
    --   script.trgfn_doc_guard_listino_con_righe (20261011-28) solleva il primo
    --   motivo di script.fn_check_listino_cambiabile (20261011-27): il listino di
    --   contratto e offerta non cambia sotto righe gia' caricate
    --   (brief-db-testata-dopo-emissione §11, R-DB-4).
    -- ⭐ 2026-10-11: da 37 a 38. Un sito NUOVO nato sull'helper:
    --   vendite.trgfn_ordini_righe_guard_data_consegna_spedita (20261012-06)
    --   solleva il primo motivo di script.fn_check_ordine_riga_data_consegna_confermata
    --   (20261012-05), la stessa funzione da cui vendite.vw_ordini_righe_dettaglio
    --   spegne il cambio della data confermata su una riga gia' spedita
    --   (brief-db-date-consegna-righe-in-blocco, D-7).
    -- ⭐ 2026-10-12: da 38 a 39. Un sito NUOVO nato sull'helper:
    --   vendite.fn_documento_ritira_legami (20261012-22) solleva, PRIMA della
    --   conferma dell'annullo con legami, il primo motivo della check che il
    --   guard della testata solleverebbe (fn_check_preventivo_annullabile,
    --   fn_check_ordine_annullabile, fn_check_commessa_annullabile,
    --   fn_check_sorgente_chiudibile): prima cio' che vieta, poi la conferma
    --   (brief-db-annullo-a-valle-riapre-a-monte, D-3).
    -- ⭐ 2026-10-13: da 39 a 40. Un sito NUOVO nato sull'helper:
    --   script.trgfn_righe_guard_articolo_ammesso (20261013-41), il guard di
    --   tabella delle righe di preventivo, ordine e bolla, solleva il primo
    --   motivo di script.fn_check_articolo_riga (20261013-40), la stessa check
    --   da cui leggera' il picker degli articoli ammessi
    --   (brief-db-articoli-ammessi-per-documento, A-2). Il guard che ritira
    --   (vendite.trgfn_preventivi_righe_set_natura_vendita) sollevava un codice
    --   letterale e non era nel conto.
    -- ⭐ 2026-10-13 (sera): da 40 a 39. Un sito RITIRATO per estrazione:
    --   script.trgfn_righe_guard_esclusione_figlio_bundle (20261013-57) se ne va,
    --   e il suo predicato (script.fn_check_esclusione_articolo_documento) lo
    --   compone ora script.fn_check_articolo_riga, che il guard di tabella
    --   script.trgfn_righe_guard_articolo_ammesso — gia' nel conto — solleva anche
    --   sulle righe di offerta e contratto (Lotto 3b del
    --   brief-db-articoli-ammessi-per-documento).
    -- ⭐ 2026-10-13 (sera, Lotto 3c): da 39 a 40. Un sito NUOVO nato sull'helper:
    --   catalogo.trgfn_articoli_componenti_guard_componente (20261013-60), il guard
    --   della distinta, solleva il primo motivo di script.fn_check_articolo_riga
    --   (documento ARTICOLO). I guard per regola che sostituisce (un livello, IVA)
    --   sollevavano codici letterali e non erano nel conto.
    -- ⭐ 2026-10-21: da 40 a 41. Un sito NUOVO nato sull'helper:
    --   vendite.fn_genera_ordine_da_offerta (20261021-61, brief-db-offerta-
    --   emissione-ed-erogazione §I.2, I-D2), che solleva il primo motivo di
    --   script.fn_check_righe_offerta_in_ordine. I due guard di transizione che
    --   chiamano ora anche script.fn_check_righe_documento e
    --   script.fn_check_offerta_annullabile (-57, -59) erano gia' nel conto: si
    --   conta la FUNZIONE, non le chiamate.
    -- ⭐ 2026-10-22: da 41 a 42. Un sito NUOVO nato sull'helper:
    --   vendite.trgfn_fatture_guard_stato (20261022-07) solleva, entrando in
    --   EMESSA, il primo motivo di script.fn_check_fattura_emettibile
    --   (20261022-06): il cancello IVA della fattura (D-3 di Tid, §9.9 di
    --   brief-be-utenti-di-sviluppo).
    -- ⭐ 2026-10-28: da 42 a 44. Due siti NUOVI nati sull'helper col giro 12 di
    --   brief-modello-documento-vendita (§16, la versione di listino):
    --   vendite.trgfn_listini_versioni_guard_transizione_stato (20261028-08) e
    --   il verbo vendite.fn_attiva_versione_listino (20261028-12), che
    --   sollevano il primo motivo di script.fn_check_versione_listino_attivabile.
    'le quarantaquattro funzioni bonificate chiamano l''helper');

-- 6) ⚠️ Il marcatore non e' troppo LARGO. vendite.fn_cleanup_fatture_by_ids
--    solleva un codice LETTERALE e dal primo motivo legge solo un valore per la
--    frase (`-> 0 ->> 'dettaglio'`): con un marcatore su `-> 0` entrerebbe nel
--    perimetro e sarebbe un falso positivo. Se questo test diventa rosso,
--    qualcuno ha allargato il marcatore e il cancello ha cominciato a bocciare
--    il caso giusto.
SELECT ok(
    NOT EXISTS (SELECT 1 FROM punti_primo_motivo
                 WHERE sch = 'vendite' AND fn = 'fn_cleanup_fatture_by_ids'),
    'un sito che solleva un codice LETTERALE resta fuori dal perimetro');

-- 7) ⭐⭐ LA CANARINA: il marcatore non e' troppo STRETTO. L'helper e' l'unico
--    posto dove la coda vive ancora, e la scrive nella forma con la variabile
--    d'appoggio — la stessa dei dieci siti bonificati. Se il marcatore smette
--    di riconoscerla, questo test si accorge PRIMA che il rubinetto diventi
--    verde per costruzione.
--    ⚠️ E' successo davvero: la prima stesura cercava `-> 0 ->> 'codice'` e non
--    vedeva nessuno dei dieci. Solo una prova per mutazione l'ha mostrato.
--    ⭐ DAL 2026-09-08 LA CANARINA E' UN TESTIMONE COSTRUITO, e il cambio e'
--    la lezione del file gemello: prima l'asserzione ri-scriveva il marcatore
--    QUI e lo applicava all'helper — cioe' sorvegliava una COPIA del marcatore,
--    non la sede. Da quando la derivazione vive in dbops.vw_punti_primo_motivo,
--    restringerlo LA' lasciava questa riga verde.
--    ⇒ Adesso il test si fabbrica un sito nella forma con la variabile
--    d'appoggio e pretende che la VISTA lo veda. Se qualcuno riporta il
--    marcatore a `-> 0 ->> 'codice'`, questo diventa rosso.
--    ⚠️ Il testimone e' escluso dai conteggi dei test 2-4 (`fn !~ '^pgtap_'`):
--    un presidio che si conta addosso i propri semi sposta le sue soglie.
--    ⚠️ Il testimone (pg_temp.pgtap_coda_variabile_appoggio) e' creato nella
--    Fixture, prima della fotografia: la canarina interroga la copia della
--    vista, che e' la vista com'era con il testimone gia' dentro.
SELECT ok(
    EXISTS (SELECT 1 FROM _vw_punti_primo_motivo
             WHERE sch ~ '^pg_temp' AND fn = 'pgtap_coda_variabile_appoggio'
               AND check_funzione = 'fn_check_sorgente_chiudibile'),
    'la vista riconosce la forma con la variabile d''appoggio e la lega alla sua check (canarina)');

SELECT * FROM finish();
ROLLBACK;
