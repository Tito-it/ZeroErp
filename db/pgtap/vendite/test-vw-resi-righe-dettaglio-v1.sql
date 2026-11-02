-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.vw_resi_righe_dettaglio — le righe del reso, che dal
--       2026-08-25 hanno una sede nel database (changeSet 20260825-25).
--
-- Perche' la vista esiste: le righe del reso erano l'UNICO dettaglio documento
--   servito da SQL scritto in Python (resi_repository.py::list_righe), ed e'
--   quello il motivo per cui il motivo di blocco dell'annullo — chiesto dal
--   team BE «sia sulle righe del reso sia sulla coda accrediti» — poteva
--   arrivare su una superficie sola. ⚠️ E proprio non quella giusta: misurato
--   il 2026-08-25, le tre righe con un accredito sono tutte USCITE dalla coda
--   al verbo, quindi il pulsante «Annulla l'accredito» vive QUI.
--   Cantiere: brief-design-note-credito-resi §45.
--
-- Impostazione: tutte le asserzioni sono SEED-AGNOSTICHE — forma, perimetro e
--   coerenza valgono su qualunque dato, anche su un DB vuoto.
--
-- Indice test (1..6):
--   1) la vista esiste
--   2) security_invoker attivo (la RLS di chi chiede resta applicata)
--   3) le colonne, tutte e 29
--   4) ⛔ PERIMETRO: nessuna riga appartiene a un reso che il chiamante non vede
--   5) ⚠️ NESSUN FILTRO NASCOSTO: la vista proietta, non seleziona
--   6) ⛔⛔ annullo_blocco_codice coincide con script.fn_check_accredito_annullabile
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Qui non e' una formalita': il test 4
-- misura proprio il perimetro, e come owner sarebbe verde per costruzione.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- ---- 1..3: la forma ------------------------------------------------------
SELECT has_view('vendite', 'vw_resi_righe_dettaglio',
                '1) vw_resi_righe_dettaglio esiste');

-- Senza security_invoker la vista risponderebbe col perimetro del PROPRIETARIO
-- e il test 4 diventerebbe muto: le due cose si tengono insieme.
SELECT ok(
    EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) opt
             WHERE c.oid = 'vendite.vw_resi_righe_dettaglio'::regclass
               AND opt IN ('security_invoker=on','security_invoker=true')),
    '2) security_invoker attivo');

SELECT columns_are('vendite', 'vw_resi_righe_dettaglio',
    ARRAY['id','reso_id','riga_nr','attivo','ddt_riga_id','ordine_riga_id',
          'articolo_id','articolo_codice','articolo_descrizione','descrizione',
          'quantita','qta_operativa','factor_to_base','uom_operativa_id',
          'uom_codice','tipo_reso_id','tipo_reso_codice_interno',
          'tipo_reso_descrizione','riapre_residuo','motivo',
          'qta_riconsegnata','qta_rinunciata','qta_residua','stato_riconsegna',
          'gia_accreditato',
          -- ⭐ la colonna per cui questa vista e' nata
          'annullo_blocco_codice',
          'meta','data_insert','data_update'],
    '3) le colonne di vw_resi_righe_dettaglio');

-- ---- 4: il perimetro -----------------------------------------------------
-- ⛔ vendite.resi ha la RLS (rls_resi_ef_whitelist), vendite.resi_righe NO.
--    Una vista costruita sulle sole righe sarebbe leggibile per QUALUNQUE
--    reso_id, anche fuori dal perimetro emittente di chi chiede. Che il service
--    autorizzi prima non basta: un oggetto di database dev'essere sicuro da
--    solo, perche' il prossimo consumatore non sa cosa faceva il primo.
--    ⚠️ Stessa classe di difetto degli archi B/E/F/G del grafo di genealogia,
--    chiusa lo stesso giorno (20260825-19). Quando se ne trova una, si cercano
--    i gemelli.
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_resi_righe_dettaglio v
      WHERE NOT EXISTS (SELECT 1 FROM vendite.resi r WHERE r.id = v.reso_id)),
    0, '4) perimetro: nessuna riga appartiene a un reso non visibile');

-- ---- 5: nessun filtro nascosto -------------------------------------------
-- ⚠️ `attivo` e' una COLONNA, non un filtro incorporato: la vista proietta e il
--    chiamante filtra. Una vista «dettaglio» che nascondesse righe darebbe un
--    conteggio diverso da quello della tabella senza che niente lo dica — ed e'
--    il genere di sorpresa che si scopre contando male mesi dopo.
--    Il confronto e' a perimetro pari: entrambi i lati passano da vendite.resi.
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_resi_righe_dettaglio),
    (SELECT count(*)::int FROM vendite.resi_righe rr
       JOIN vendite.resi r ON r.id = rr.reso_id),
    '5) nessun filtro nascosto: la vista proietta tutte le righe del perimetro');

-- ---- 6: la colonna che motiva la vista -----------------------------------
-- ⛔⛔ IL PRESIDIO. La colonna deve dire ESATTAMENTE quello che dice la sede
--     unica del predicato — la stessa che vendite.fn_annulla_accredito_riga_reso
--     interroga per sollevare. Se le due divergessero si tornerebbe al difetto
--     che il cantiere chiude: pulsante spento su un annullo che sarebbe
--     passato, o acceso su uno che verra' rifiutato.
--     ⚠️ `IS DISTINCT FROM` e non `<>`: entrambi i lati sono NULL quando
--     l'annullo e' ammesso, ed e' il caso piu' frequente — con `<>` il
--     confronto darebbe NULL, la riga non verrebbe contata e il test passerebbe
--     senza aver verificato niente.
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_resi_righe_dettaglio v
      WHERE v.annullo_blocco_codice IS DISTINCT FROM
            (script.fn_check_accredito_annullabile(v.id) -> 0 ->> 'reason')),
    0, '6) annullo_blocco_codice coincide con la sede unica del predicato');

SELECT * FROM finish();
ROLLBACK;
