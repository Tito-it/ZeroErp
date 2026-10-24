-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_resolve_iva_riga (il guscio) e fn_resolve_iva_riga_it
--       brief-db-be-iva-risolutore-e-regime-cliente, voce `I2`
-- rev 2026-10-24 (brief-modello-documento-vendita Q-4): la fixture si COSTRUISCE
--   intera coi builder di dbops (mondo, articoli, cliente sulla utility con
--   tipo/classe, scheda precontrattuale, contratto ATTIVO); prima pescava
--   articoli, un contratto da clonare e un soggetto, assenti su un database
--   ricostruito da zero.
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): il contratto nasce in
--   bozza e si porta avanti con dbops.fn_pgtap_porta_a_stato (prima nasceva
--   gia' ATTIVO).
-- ------------------------------------------------------------
-- A cosa serve, in una frase
--   Il risolutore decide QUALE codice IVA porta una riga di documento. Fino a
--   ieri quella decisione era sparsa fra chi scriveva la riga; da oggi ha una
--   sede sola, e questo file e' cio' che impedisce alle vecchie sedi di
--   ricrescere senza che nessuno se ne accorga.
--
-- ⭐ PERCHE' LA FORNITURA SE LA FABBRICA
--   La verifica in transazione fatta il 2026-08-29 ha lasciato UN RAMO
--   SCOPERTO, e va detto perche': i contratti attivi di questa macchina stanno
--   tutti su utility SENZA dimensione tipo/classe, e quella dimensione non si
--   puo' forzare — `trgfn_contratti_utilities_guard_tipo_classe` impone che una
--   utility l'abbia SE E SOLO SE esistono `config.tipi_utenze` per lei, e allora
--   tipo e classe sono obbligatori e coerenti. Forzarla non sarebbe una
--   scorciatoia di test: sarebbe un dato che il dominio non ammette.
--   ⚠️ Quindi qui il contratto attivo si COSTRUISCE, su un cliente della utility
--   che quella dimensione ce l'ha davvero, con la scheda precontrattuale che
--   dichiara la classe (rev 2026-10-24, Q-4: prima si clonava un contratto
--   esistente). Un test che CERCA il caso e non lo trova diventa muto; uno che
--   lo costruisce no.
--
-- ⚠️ E la riga di `vendite.contratti_utilities` NON si inserisce: la crea un
--   trigger sul contratto (`uq_contratti_utilities_contratto_id` lo dimostra al
--   primo tentativo). Si aggiorna.
--
-- ⛔ Dal 2026-10-04 bis (R-DB-C10) nessuna domanda prende un importo: i casi
--   chiamano con p_imponibile NULL (l'anteprima) o con p_consumo. Un importo
--   compare solo dove si prova che e' RIFIUTATO (12, 18).
--
-- ℹ️ Il guscio si chiama sempre lui, mai `_it` direttamente: e' il guscio che
--   smista sul paese, e provare l'implementazione scavalcando il dispatcher
--   vorrebbe dire non provare `D21`.
--
-- Indice test
-- 1)  La fixture e completa (e se non lo e, dice cosa manca)
-- 2)  Stadio A: l articolo che ha un opinione vince
-- 3)  ⭐ Stadio A2: l uso della fornitura entra DOVE l articolo tace (D17)
-- 4)  ⭐ E il verso opposto: con l articolo che parla, la fornitura NON scavalca
-- 5)  Articolo muto senza fornitura: origine ASSENTE, e NON solleva
-- 6)  Il ritorno e un COMPOSITO, non un numero (D18)
-- 7)  Anteprima senza importo: una riga sola, quota NULL
-- 8)  ⭐ Il guscio SMISTA: un paese non implementato SOLLEVA, non tace (D21)
-- 9)  Stadio B: un titolo sostituisce l aliquota ordinaria
-- 10) ⭐ Fra due titoli vince il PIU SPECIFICO (D13)
-- 11) ⛔ Due titoli in pari specificita: si SOLLEVA, non si sceglie a caso
-- 12) ⛔ La proiezione e RITIRATA: un importo SOLLEVA, anche dove spezzerebbe
-- 13) E sul titolo a tetto l anteprima resta una riga sola, quota NULL
-- 14) is_reverse_charge arriva dalla NATURA (D22)
-- 15) ⭐ Senza il soggetto la coppia esigibilita/split dice «non lo so» INSIEME
-- 16) ⭐ CONSUMO (p_consumo, in coda): titolo a tetto -> DUE righe, prima il titolo, quota NULL
-- 17) ⭐ CONSUMO a residuo zero: il titolo resta; l anteprima risponde con l ordinario
-- 18) il consumo non prende un importo: p_consumo con p_imponibile SOLLEVA
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- ⭐ rev 2026-10-24 (Q-4): il mondo — azienda, operatore, contesto aperto su di
--   lui, un cliente legato a quella azienda — si costruisce qui.
-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_mondo_cliente
CREATE TEMP TABLE tmp_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('PGTAP-IVA');

SELECT plan(18);

-- ============================================================
-- La fixture: si COSTRUISCE, non si cerca
-- ============================================================
CREATE TEMP TABLE tmp_fix (
  art_parla        uuid,
  art_muto         uuid,
  iva_articolo     integer,
  contratto_id     bigint,
  ba_id            bigint,
  utility_id       integer,
  tipo_utenza_id   integer,
  iva_tipo_utenza  integer,
  emittente_id     bigint,
  soggetto_id      uuid,
  mancante         text
);

DO $fix$
DECLARE
  v_art_parla   catalogo.articoli.id%TYPE;
  v_art_muto    catalogo.articoli.id%TYPE;
  v_iva_art     config.iva.id%TYPE;
  v_utility     config.tipi_utenze.utility_id%TYPE;
  v_tipo        config.tipi_utenze.id%TYPE;
  v_classe      config.classi_utenze.id%TYPE;
  v_iva_tipo    config.iva.id%TYPE;
  v_new         vendite.contratti.id%TYPE;
  v_ba          anagrafiche.billing_account.id%TYPE;
  v_ist         anagrafiche.billing_account.istanza_utility_id%TYPE;
  v_emitt       anagrafiche.emittenti_fiscali.id%TYPE;
  v_sogg        anagrafiche.soggetti.id%TYPE;
  v_manca       text := NULL;
BEGIN
  -- ── l'articolo che PARLA: ha un codice IVA, e con aliquota > 0 perche' una
  --    prova fra zeri passerebbe anche con il risolutore rotto.
  --    rev 2026-10-24 (Q-4): COSTRUITO, col codice ordinario 22 letto per
  --    codice_interno: diverso da quelli dei titoli (NI35, 10, 4), cosi' un
  --    risolutore che ignorasse il titolo non passerebbe per coincidenza.
  --    Il builder non sceglie l'IVA: la si scrive subito, sull'articolo mai usato.
  v_art_parla := dbops.fn_pgtap_crea_articolo('PGTAP-IVA-PARLA', false);
  UPDATE catalogo.articoli
     SET iva_id = (SELECT i.id FROM config.iva i WHERE i.codice_interno = '22' AND i.attivo IS TRUE)
   WHERE id = v_art_parla
  RETURNING iva_id INTO v_iva_art;

  -- ── l'articolo che TACE: dichiara di non avere un'opinione sull'IVA
  --    (il builder lo fa nascere senza codice IVA)
  v_art_muto := dbops.fn_pgtap_crea_articolo('PGTAP-IVA-MUTO', false);

  -- ── ⭐ la utility che ha DAVVERO la dimensione tipo/classe, con una classe
  --    coerente: e' la condizione che il guard impone, e senza di essa il ramo
  --    TIPO_UTENZA non e' raggiungibile in nessun modo lecito. Catalogo di
  --    sistema, ordine stabile.
  SELECT tu.utility_id, tu.id, cl.id, tu.iva_id
    INTO v_utility, v_tipo, v_classe, v_iva_tipo
    FROM config.tipi_utenze tu
    JOIN config.classi_utenze cl ON cl.tipo_utenza_id = tu.id
   ORDER BY tu.id, cl.id LIMIT 1;

  -- ── il contratto ATTIVO: si COSTRUISCE (rev 2026-10-24, Q-4).
  --    Un cliente di QUELLA utility, sotto il contesto del mondo (il trigger
  --    z90 lega il BA all'azienda di chi agisce), poi la scheda precontrattuale
  --    con la classe: e' da li' che la nascita del contratto scrive la
  --    fornitura (vendite.fn_doc_fornitura_da_anagrafica). Poi il contratto,
  --    che nasce DRAFT e si attiva per la matrice dentro il builder
  --    (brief-modello-documento-vendita N-1), col listino del mondo.
  IF v_utility IS NOT NULL THEN
    SELECT c.billing_account_id, c.istanza_utility_id
      INTO v_ba, v_ist
      FROM dbops.fn_pgtap_crea_cliente_ba('PGTAP-IVA fornitura', v_utility) c;

    INSERT INTO anagrafiche.istanze_dati_precontrattuali
        (istanza_utility_id, utility_id, classe_utenza_id, meta)
    VALUES (v_ist, v_utility, v_classe,
            jsonb_build_object('test_scope', 'pgtap_resolve_iva'));

    SELECT k.contratto_id, k.emittente_fiscale_id
      INTO v_new, v_emitt
      FROM dbops.fn_pgtap_crea_contratto('PGTAP-IVA', 'ATTIVO', v_ba,
                                         p_valido_dal => DATE '2026-01-01') k;

    -- ⚠️ La riga la CREA un trigger sul contratto, alla nascita, dai dati
    --    precontrattuali dell'istanza: non si inserisce e non si modifica.
    -- ⛔ rev 2026-10-11 (brief-db-testata-dopo-emissione §11.7): dal lock dei
    --    satelliti (20261011-24) la fornitura di un documento fuori bozza non
    --    si cambia piu' (E_DOC_DATI_COLLEGATI_NON_BOZZA): si LEGGE il tipo d'uso
    --    che lo snapshot ha scritto, e il codice IVA si mette su quello (sotto),
    --    che e' catalogo.
    SELECT cu.tipo_utenza_id, cu.classe_utenza_id, tu.iva_id
      INTO v_tipo, v_classe, v_iva_tipo
      FROM vendite.contratti_utilities cu
      LEFT JOIN config.tipi_utenze tu ON tu.id = cu.tipo_utenza_id
     WHERE cu.contratto_id = v_new;

    -- il codice IVA sul tipo d'uso: e' l'anello che lo stadio A2 legge
    IF v_tipo IS NOT NULL AND v_iva_tipo IS NULL THEN
      UPDATE config.tipi_utenze SET iva_id = (
          SELECT i.id FROM config.iva i
           WHERE i.attivo IS TRUE AND i.aliquota_iva > 0 ORDER BY i.id LIMIT 1)
       WHERE id = v_tipo
      RETURNING iva_id INTO v_iva_tipo;
    END IF;
  END IF;

  -- ── un soggetto SENZA titoli: i casi 9-12 ne fabbricano di propri, e uno
  --    gia' esistente li renderebbe illeggibili
  --    ⭐ rev 2026-10-10: e con una NATURA. Un titolo su un soggetto senza
  --    natura e' rifiutato (trgfn_soggetti_titoli_iva_guard_tipo_soggetto,
  --    20261010-92, D-1 di brief-db-dati-fiscali-e-societari-del-soggetto).
  --    rev 2026-10-24 (Q-4): il cliente del mondo, appena costruito (il
  --    builder gli da' la natura); prima era «il primo soggetto senza titoli».
  SELECT s.id INTO v_sogg
    FROM tmp_mondo m
    JOIN anagrafiche.soggetti s ON s.id = m.cliente_soggetto_id
   WHERE NOT EXISTS (SELECT 1 FROM anagrafiche.soggetti_titoli_iva t
                      WHERE t.soggetto_id = s.id)
     AND s.tipo_soggetto_dettaglio_id IS NOT NULL;

  v_manca := NULLIF(concat_ws(', ',
      CASE WHEN v_art_parla IS NULL OR v_iva_art IS NULL
           THEN 'articolo con aliquota > 0' END,
      CASE WHEN v_art_muto  IS NULL THEN 'articolo senza codice IVA'   END,
      CASE WHEN v_utility   IS NULL THEN 'utility con dimensione tipo/classe' END,
      CASE WHEN v_new       IS NULL THEN 'contratto attivo costruito'  END,
      CASE WHEN v_new IS NOT NULL AND v_tipo IS NULL
           THEN 'fornitura del contratto con tipo d uso (dati precontrattuali dell istanza)' END,
      CASE WHEN v_iva_tipo  IS NULL THEN 'codice IVA sul tipo d uso'   END,
      CASE WHEN v_emitt     IS NULL THEN 'emittente fiscale'           END,
      CASE WHEN v_sogg      IS NULL THEN 'soggetto senza titoli'       END), '');

  INSERT INTO tmp_fix VALUES (v_art_parla, v_art_muto, v_iva_art, v_new, v_ba,
                              v_utility, v_tipo, v_iva_tipo, v_emitt, v_sogg, v_manca);
END $fix$;

-- ============================================================
-- 1) La fixture, e cosa manca se manca
-- ============================================================
-- ⚠️ Un `ok(...)` muto qui renderebbe illeggibili tutti i rossi a valle: se la
--   fornitura non si e' costruita, i casi 3 e 4 falliscono per un motivo che
--   non c'entra niente con il risolutore.
SELECT is(
  (SELECT mancante FROM tmp_fix),
  NULL,
  '1) la fixture e completa: ' || COALESCE((SELECT mancante FROM tmp_fix), 'niente manca')
);

-- ============================================================
-- 2) Stadio A: l'articolo che ha un'opinione vince
-- ============================================================
SELECT is(
  (SELECT r.origine FROM tmp_fix f,
          LATERAL vendite.fn_resolve_iva_riga(f.art_parla, DATE '2026-06-15', NULL) r),
  'ARTICOLO'::varchar(16),
  '2) l articolo che dichiara un codice IVA decide da solo'
);

-- ============================================================
-- 3) ⭐ Stadio A2: l'uso della fornitura entra DOVE l'articolo tace
-- ============================================================
-- ⛔ E' il ramo che la verifica in transazione del 2026-08-29 aveva lasciato
--   SCOPERTO, ed e' il motivo per cui questo file costruisce una fornitura
--   invece di cercarne una.
-- ⚠️ Si asserisce il CODICE e non solo l'origine: un'origine giusta con il
--   codice sbagliato sarebbe verde e falsa.
SELECT is(
  (SELECT r.origine || ':' || r.iva_id::text FROM tmp_fix f,
          LATERAL vendite.fn_resolve_iva_riga(f.art_muto, DATE '2026-06-15', NULL,
                                              f.ba_id, f.utility_id) r),
  (SELECT 'TIPO_UTENZA:' || f.iva_tipo_utenza::text FROM tmp_fix f),
  '3) dove l articolo tace parla l uso della fornitura, e porta il SUO codice'
);

-- ============================================================
-- 4) ⭐ Il verso opposto, che e' la meta' di `D17` che si dimentica
-- ============================================================
-- ⚠️ Senza questo caso, un risolutore che applicasse SEMPRE il tipo d'uso
--   passerebbe il test 3 e sarebbe sbagliato: `tipi_utenze` non sa dire «non ho
--   opinione», quindi applicato per primo si prenderebbe cauzioni e servizi.
SELECT is(
  (SELECT r.origine FROM tmp_fix f,
          LATERAL vendite.fn_resolve_iva_riga(f.art_parla, DATE '2026-06-15', NULL,
                                              f.ba_id, f.utility_id) r),
  'ARTICOLO'::varchar(16),
  '4) con l articolo che parla, la fornitura NON lo scavalca'
);

-- ============================================================
-- 5) Articolo muto e nessuna fornitura: si dice ASSENTE, non si esplode
-- ============================================================
-- ⭐ In bozza una riga senza IVA e' legittima: il cancello sta all'emissione.
--   Se il risolutore sollevasse qui, non si potrebbe piu' salvare una bozza.
SELECT is(
  (SELECT r.origine || '/' || COALESCE(r.iva_id::text, 'NULL') FROM tmp_fix f,
          LATERAL vendite.fn_resolve_iva_riga(f.art_muto, DATE '2026-06-15', NULL) r),
  'ASSENTE/NULL',
  '5) articolo muto senza fornitura: origine ASSENTE e codice NULL, e NON solleva'
);

-- ============================================================
-- 6) Il ritorno e' un COMPOSITO, non un numero (`D18`)
-- ============================================================
-- ⚠️ E' la decisione che rende il risolutore usabile una volta sola invece che
--   tre: se tornasse la sola aliquota, chi costruisce la riga dovrebbe
--   ri-andare a prendere natura, esigibilita' e riferimento normativo — cioe'
--   ricostruire la decisione fuori dalla sua sede.
--
-- ⛔ rev `D32`. La prima stesura di questo caso chiamava il risolutore SENZA
--   soggetto e pretendeva comunque i campi valorizzati. Era sbagliato, ed e'
--   sbagliato in un modo istruttivo: il caso era stato scritto insieme a
--   `20260829-52`, la correzione che allineava la coppia esigibilita/split
--   verso il valore — e **ne aveva ereditato la premessa**, cementandola. Un
--   test scritto nello stesso momento della correzione non la verifica: la
--   ripete.
-- ⭐ La pienezza si prova sul percorso VERO, quello che ha il soggetto. Il caso
--   senza soggetto e' un'altra domanda, e ha un caso suo (il 15).
SELECT ok(
  (SELECT r.aliquota IS NOT NULL
      AND r.esigibilita IS NOT NULL
      AND r.split_payment IS NOT NULL
      AND r.riferimento_normativo IS NOT NULL
     FROM tmp_fix f,
          LATERAL vendite.fn_resolve_iva_riga(f.art_parla, DATE '2026-06-15', NULL,
                                              NULL, NULL, f.soggetto_id, f.emittente_id) r),
  '6) col soggetto noto il composito esce pieno: aliquota, esigibilita, split e norma'
);

-- ============================================================
-- 7) Anteprima senza importo: una riga sola, e non si inventa la spezzatura
-- ============================================================
SELECT is(
  (SELECT count(*) FROM tmp_fix f,
          LATERAL vendite.fn_resolve_iva_riga(f.art_parla, DATE '2026-06-15') r),
  1::bigint,
  '7) senza imponibile si risponde con UNA riga (quota NULL), non con due'
);

-- ============================================================
-- 8) ⭐ Il guscio SMISTA, e l'ELSE non tace (`D21`)
-- ============================================================
-- ⛔ Il precedente da cui il guscio e' copiato — il dispatcher CF/PIVA
--   `trgfn_soggetti_valida_cf_piva_dispatch` — quel ramo NON ce l'ha: su un
--   paese non previsto passa in silenzio, cioe' non valida niente e nessuno lo
--   sa. Qui si e' scelto il contrario, e questo caso e' cio' che lo tiene.
-- ⚠️ `throws_ok` CON lo SQLSTATE: senza, accetterebbe qualunque errore, compreso
--   un errore di sintassi in una riscrittura futura.
SELECT throws_ok(
  format('SELECT * FROM vendite.fn_resolve_iva_riga(%L::uuid, %L::date, NULL,
                 NULL, NULL, NULL, NULL, %L::character(2))',
         (SELECT art_parla FROM tmp_fix), DATE '2026-06-15', 'DE'),
  'P0001',
  NULL,
  '8) un paese non implementato SOLLEVA: il guscio smista e l ELSE non tace'
);

-- ============================================================
-- Stadio B: i titoli. Da qui in poi si fabbricano e si smontano.
-- ============================================================
-- ⭐ rev 2026-10-10 (brief-db-dati-fiscali-e-societari-del-soggetto, Parte D):
--   un titolo vigente deve essere ammesso dalla natura del titolare (matrice
--   config.tipi_titolo_iva_tipi_soggetto_dettaglio, guard 20261010-92). Questo
--   file mette QUATTRO tipi sullo stesso soggetto per misurare il risolutore
--   (specificita', parita', plafond), e nessuna natura reale li ammette tutti:
--   l'agevolazione L. 104 e' solo del privato, l'intento mai. Dentro la
--   transazione la natura del soggetto della fixture li ammette tutti e quattro;
--   la regola della matrice la misura anagrafiche/test-soggetti-titoli-iva-tipo-soggetto-v1.
INSERT INTO config.tipi_titolo_iva_tipi_soggetto_dettaglio
    (tipo_titolo_iva_id, tipo_soggetto_dettaglio_id, attivo)
SELECT tt.id, s.tipo_soggetto_dettaglio_id, true
  FROM tmp_fix f
  JOIN anagrafiche.soggetti s ON s.id = f.soggetto_id
 CROSS JOIN config.tipi_titolo_iva tt
 WHERE tt.codice_interno IN ('USO_INDUSTRIALE', 'AGEVOLATA_104', 'COOPERATIVA', 'INTENTO')
ON CONFLICT (tipo_titolo_iva_id, tipo_soggetto_dettaglio_id) DO UPDATE SET attivo = true;
-- ⚠️ Ogni caso riparte da zero titoli: due casi che si lasciano dietro il
--   proprio dato si verificano a vicenda, e il primo che sbaglia rende
--   illeggibile il secondo.

-- ── 9) un titolo su TUTTO sostituisce l'aliquota ordinaria
INSERT INTO anagrafiche.soggetti_titoli_iva
    (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id, ambito, valido_dal, meta)
SELECT f.soggetto_id, f.emittente_id,
       (SELECT id FROM config.tipi_titolo_iva WHERE codice_interno = 'USO_INDUSTRIALE'),
       (SELECT id FROM config.iva WHERE codice_interno = 'NI35'),
       'TUTTO', DATE '2026-01-01',
       jsonb_build_object('test_scope', 'pgtap_resolve_iva')
  FROM tmp_fix f;

SELECT is(
  (SELECT r.origine || ':' || r.iva_id::text FROM tmp_fix f,
          LATERAL vendite.fn_resolve_iva_riga(f.art_parla, DATE '2026-06-15', NULL,
                                              NULL, NULL, f.soggetto_id, f.emittente_id) r),
  (SELECT 'TITOLO:' || id::text FROM config.iva WHERE codice_interno = 'NI35'),
  '9) un titolo valido sostituisce l aliquota che l articolo avrebbe portato'
);

-- ── 10) ⭐ fra due titoli vince il piu' specifico (`D13`)
-- ⚠️ Il titolo ristretto e' di un ALTRO tipo: due titoli dello stesso tipo su
--   TUTTO non possono coesistere, e non per una regola di test —
--   `ex_soggetti_titoli_iva_no_overlap` lo impedisce nel DB.
INSERT INTO anagrafiche.soggetti_titoli_iva
    (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id, ambito, valido_dal, meta)
SELECT f.soggetto_id, f.emittente_id,
       (SELECT id FROM config.tipi_titolo_iva WHERE codice_interno = 'AGEVOLATA_104'),
       (SELECT id FROM config.iva WHERE attivo IS TRUE AND aliquota_iva = 10 ORDER BY id LIMIT 1),
       'RISTRETTO', DATE '2026-01-01',
       jsonb_build_object('test_scope', 'pgtap_resolve_iva')
  FROM tmp_fix f;

INSERT INTO anagrafiche.soggetti_titoli_iva_ambiti (titolo_iva_id, livello, articolo_id, meta)
SELECT t.id, 'ARTICOLO', f.art_parla, jsonb_build_object('test_scope', 'pgtap_resolve_iva')
  FROM anagrafiche.soggetti_titoli_iva t, tmp_fix f
 WHERE t.meta->>'test_scope' = 'pgtap_resolve_iva' AND t.ambito = 'RISTRETTO';

SELECT is(
  (SELECT r.iva_id FROM tmp_fix f,
          LATERAL vendite.fn_resolve_iva_riga(f.art_parla, DATE '2026-06-15', NULL,
                                              NULL, NULL, f.soggetto_id, f.emittente_id) r),
  (SELECT id FROM config.iva WHERE attivo IS TRUE AND aliquota_iva = 10 ORDER BY id LIMIT 1),
  '10) fra il titolo su TUTTO e quello sul singolo articolo vince il PIU SPECIFICO'
);

-- ── 11) ⛔ due titoli in pari specificita': si solleva, non si sceglie a caso
DELETE FROM anagrafiche.soggetti_titoli_iva_ambiti
 WHERE meta->>'test_scope' = 'pgtap_resolve_iva';
DELETE FROM anagrafiche.soggetti_titoli_iva
 WHERE meta->>'test_scope' = 'pgtap_resolve_iva'
   AND tipo_titolo_iva_id = (SELECT id FROM config.tipi_titolo_iva WHERE codice_interno = 'AGEVOLATA_104');

INSERT INTO anagrafiche.soggetti_titoli_iva
    (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id, ambito, valido_dal, meta)
SELECT f.soggetto_id, f.emittente_id,
       (SELECT id FROM config.tipi_titolo_iva WHERE codice_interno = 'COOPERATIVA'),
       (SELECT id FROM config.iva WHERE attivo IS TRUE AND aliquota_iva = 4 ORDER BY id LIMIT 1),
       'TUTTO', DATE '2026-01-01',
       jsonb_build_object('test_scope', 'pgtap_resolve_iva')
  FROM tmp_fix f;

-- ⭐ Due titoli su TUTTO, tipi diversi: entrambi specificita' 1. Scegliere il
--   piu' basso per id sarebbe una risposta arbitraria su un dato fiscale, e
--   nessuno saprebbe mai che c'era una scelta da fare.
SELECT throws_ok(
  format('SELECT * FROM vendite.fn_resolve_iva_riga(%L::uuid, %L::date, NULL,
                 NULL, NULL, %L::uuid, %s::bigint)',
         (SELECT art_parla FROM tmp_fix), DATE '2026-06-15',
         (SELECT soggetto_id FROM tmp_fix), (SELECT emittente_id FROM tmp_fix)),
  'P0001',
  NULL,
  '11) due titoli in pari specificita SOLLEVANO: non si sceglie a caso su un dato fiscale'
);

-- ── 12/13) un titolo a tetto con plafond incapiente: la proiezione non c'e' piu'
DELETE FROM anagrafiche.soggetti_titoli_iva
 WHERE meta->>'test_scope' = 'pgtap_resolve_iva';

INSERT INTO anagrafiche.soggetti_titoli_iva
    (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id, ambito,
     valido_dal, plafond, meta)
SELECT f.soggetto_id, f.emittente_id,
       (SELECT id FROM config.tipi_titolo_iva WHERE codice_interno = 'INTENTO'),
       (SELECT id FROM config.iva WHERE codice_interno = 'NI35'),
       'TUTTO', DATE '2026-01-01', 100.00,
       jsonb_build_object('test_scope', 'pgtap_resolve_iva')
  FROM tmp_fix f;

-- ⛔ rev 2026-10-04 bis (R-DB-C10, 20261004-15): la PROIEZIONE sul residuo e'
--   RITIRATA. Questi due casi provavano la spezzatura con un importo (250 su
--   un plafond di 100 -> 100 al titolo e 150 all'ordinaria); ora l'importo e'
--   rifiutato, e la spezzatura la decide solo la madre del consumo sul netto.
-- ⚠️ Il caso e' costruito DOVE la proiezione avrebbe risposto qualcosa di
--   plausibile (titolo a tetto, plafond incapiente): un rifiuto provato su un
--   articolo senza titolo non direbbe che il ramo e' davvero sparito.
SELECT throws_like(
  format('SELECT * FROM vendite.fn_resolve_iva_riga(%L::uuid, %L::date, 250.00,
                 NULL, NULL, %L::uuid, %s::bigint)',
         (SELECT art_parla FROM tmp_fix), DATE '2026-06-15',
         (SELECT soggetto_id FROM tmp_fix), (SELECT emittente_id FROM tmp_fix)),
  '%imponibile%',
  '12) la proiezione e ritirata: un importo, senza consumo, SOLLEVA invece di spezzare'
);

-- ⭐ E sullo stesso titolo a tetto l'anteprima resta quella di sempre: UNA riga,
--   il trattamento del primo euro (residuo 100 > 0 -> il titolo), quota NULL.
SELECT is(
  (SELECT string_agg(r.origine || ':' || COALESCE(r.quota::text, 'NULL'), ' + ')
     FROM tmp_fix f,
          LATERAL vendite.fn_resolve_iva_riga(f.art_parla, DATE '2026-06-15', NULL,
                                              NULL, NULL, f.soggetto_id, f.emittente_id) r),
  'TITOLO:NULL',
  '13) titolo a tetto, anteprima: una riga sola, il titolo, quota NULL'
);

-- ============================================================
-- 14) is_reverse_charge arriva dalla NATURA, non dal prefisso del codice
-- ============================================================
-- ⚠️ Caso a scadenza dichiarata: oggi NESSUN codice IVA attivo porta una natura
--   di inversione contabile, quindi il ramo non e' esercitabile senza inventare
--   un codice di catalogo dentro un test — che sarebbe un dato finto in una
--   tabella vera. Si dichiara lo skip invece di scrivere un'asserzione fra
--   `false` e `false`, che sarebbe verde anche con il valore inchiodato.
-- ⭐ Il giorno che un codice N6 entra in catalogo, questo caso si accende da
--   solo e diventa una verifica vera.
SELECT CASE
  WHEN (SELECT count(*) FROM config.iva i
          JOIN config.iva_natura n ON n.id = i.natura_iva_id
         WHERE i.attivo IS TRUE AND n.is_reverse_charge) = 0
  THEN skip('14) nessun codice IVA attivo porta una natura di inversione contabile: il ramo non e esercitabile senza inventare un dato di catalogo', 1)
  ELSE is(
    (SELECT r.is_reverse_charge
       FROM catalogo.articoli a
       JOIN config.iva i ON i.id = a.iva_id
       JOIN config.iva_natura n ON n.id = i.natura_iva_id AND n.is_reverse_charge
      CROSS JOIN LATERAL vendite.fn_resolve_iva_riga(a.id, DATE '2026-06-15', NULL) r
      ORDER BY a.id LIMIT 1),
    true,
    '14) il flag di inversione contabile arriva dalla natura, non dal prefisso del codice'
  )
END;

-- ============================================================
-- 15) ⭐ Senza il soggetto, la coppia dice «non lo so» INSIEME (`D32`)
-- ============================================================
-- ⛔ E' il caso che mancava, ed e' il motivo per cui il difetto ha avuto DUE
--   revisioni invece di una. `20260829-49` lasciava `split_payment` a NULL e
--   `esigibilita` a 'I' — due campi in disaccordo. `20260829-52` li ha allineati
--   VERSO IL VALORE, motivandolo con «esigibilita non ammette il nullo»: falso,
--   quella colonna e' nullabile e non ha nemmeno un CHECK.
--
-- ⭐ La regola vera: senza il soggetto il regime di scissione NON E' STATO
--   DETERMINATO, e «immediata, non scissa» sarebbe un'AFFERMAZIONE su un
--   documento che potrebbe andare a una PA. Il nullo dice il vero.
--
-- ⚠️ E si asserisce la COPPIA, non i due campi separatamente: il difetto non era
--   «un campo nullo», era «due campi che rispondono alla stessa domanda in
--   disaccordo». Due asserzioni separate sarebbero passate anche con la coppia
--   di nuovo rotta nell'altro verso.
SELECT is(
  (SELECT COALESCE(r.esigibilita::text, 'NULL') || '/' || COALESCE(r.split_payment::text, 'NULL')
     FROM tmp_fix f,
          LATERAL vendite.fn_resolve_iva_riga(f.art_parla, DATE '2026-06-15', NULL) r),
  'NULL/NULL',
  '15) senza soggetto esigibilita e split escono ENTRAMBI NULL: la coppia dice «non lo so» insieme'
);

-- ============================================================
-- 16-18) ⭐ La domanda di CONSUMO (decisione C, 2026-10-04)
-- ============================================================
-- ⚠️ p_consumo e' un parametro NUOVO in coda alla firma (20261004-03/-04): i
--   casi qui sopra non cambiano. Per nominarlo si passano tutti quelli prima,
--   per posizione, come fa il backend. Il titolo a tetto e' quello del 12-13
--   (INTENTO, NI35, plafond 100). Nel consumo il risolutore dice QUALE titolo
--   e i DUE trattamenti, sempre e nell'ordine: quanto copre lo decide la madre
--   del consumo sul NETTO della fattura (brief-db-bom-flag-quantita-e-kit-in-
--   fattura §13.4). L'ordine si legge da WITH ORDINALITY, non dai valori.
SELECT is(
  (SELECT string_agg(r.origine || ':' || r.iva_id::text || ':' || COALESCE(r.quota::text, 'NULL'),
                     ' + ' ORDER BY r.n)
     FROM tmp_fix f,
          LATERAL vendite.fn_resolve_iva_riga(f.art_parla, DATE '2026-06-15', NULL,
                                              NULL, NULL, f.soggetto_id, f.emittente_id,
                                              NULL, NULL, NULL, true)
                  WITH ORDINALITY AS r(quota, iva_id, aliquota, natura_codice, is_reverse_charge,
                                       esigibilita, split_payment, riferimento_normativo,
                                       origine, titolo_iva_id, n)),
  (SELECT 'TITOLO:' || (SELECT id FROM config.iva WHERE codice_interno = 'NI35')::text
          || ':NULL + ARTICOLO:' || a.iva_id::text || ':NULL'
     FROM tmp_fix f JOIN catalogo.articoli a ON a.id = f.art_parla),
  '16) consumo con titolo a tetto: due righe, prima il titolo e poi l ordinario, quota NULL'
);

-- ⭐ Residuo zero (una forzatura che consuma tutto il plafond): il CONSUMO vede
--   ancora il titolo — e' la madre a dire che non copre piu' niente, e una riga
--   negativa della stessa fattura potrebbe restituire capienza — mentre
--   l'ANTEPRIMA risponde con l'ordinario, il trattamento del primo euro.
INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti
    (titolo_iva_id, tipo_movimento, imponibile, data_movimento, motivo)
SELECT t.id, 'FORZATURA', 100.00, DATE '2026-03-01', 'pgTAP: plafond esaurito'
  FROM anagrafiche.soggetti_titoli_iva t
 WHERE t.meta->>'test_scope' = 'pgtap_resolve_iva';

SELECT is(
  (SELECT string_agg(r.origine, '+' ORDER BY r.n)
     FROM tmp_fix f,
          LATERAL vendite.fn_resolve_iva_riga(f.art_parla, DATE '2026-06-15', NULL,
                                              NULL, NULL, f.soggetto_id, f.emittente_id,
                                              NULL, NULL, NULL, true)
                  WITH ORDINALITY AS r(quota, iva_id, aliquota, natura_codice, is_reverse_charge,
                                       esigibilita, split_payment, riferimento_normativo,
                                       origine, titolo_iva_id, n))
  || ' / ' ||
  (SELECT string_agg(r.origine, '+')
     FROM tmp_fix f,
          LATERAL vendite.fn_resolve_iva_riga(f.art_parla, DATE '2026-06-15', NULL,
                                              NULL, NULL, f.soggetto_id, f.emittente_id) r),
  'TITOLO+ARTICOLO / ARTICOLO',
  '17) a residuo zero il consumo vede ancora il titolo, l anteprima risponde con l ordinario'
);

-- ⚠️ Il consumo non prende un importo: quanto copre il titolo lo decide la
--   madre sul netto. Dal 20261004-15 lo rifiuta lo stesso guard del 12 (nessuna
--   domanda prende un importo): il caso resta, perche' e' la combinazione che
--   un chiamante del giro scriverebbe per errore.
SELECT throws_like(
  format('SELECT * FROM vendite.fn_resolve_iva_riga(%L::uuid, %L::date, 100.00,
                 NULL, NULL, NULL, NULL, NULL, NULL, NULL, true)',
         (SELECT art_parla FROM tmp_fix), DATE '2026-06-15'),
  '%imponibile%',
  '18) il consumo non prende un importo: p_consumo con p_imponibile solleva'
);

-- ============================================================
-- Smontaggio (la transazione si chiude comunque in ROLLBACK)
-- ============================================================
-- ⚠️ I titoli non si cancellano piu' (dal 2026-10-04): il caso 17 scrive una
--   FORZATURA, e il registro e' append-only, quindi un titolo con movimenti
--   non si cancella. Il ROLLBACK porta via tutto.
DELETE FROM anagrafiche.soggetti_titoli_iva_ambiti
 WHERE meta->>'test_scope' = 'pgtap_resolve_iva';

SELECT * FROM finish();

ROLLBACK;
