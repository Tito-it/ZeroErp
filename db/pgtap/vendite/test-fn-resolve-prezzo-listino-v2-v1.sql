-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test F1-DB-T5: vendite.fn_resolve_prezzo_listino_v2 (resolver pricing v5).
-- Verifica i 3 stadi e la gestione errori.
--
-- Elenco test (1..7):
--   1) Precondizione: esiste listino attivo coerente con utility/tipologia
--   2) STADIO 2 CATEGORIA: match con classe specifica + variazione PERCENTUALE
--   3) STADIO 2 CATEGORIA: fallback classe NULL
--   4) STADIO 1 CONTRATTO_OVERRIDE: prezzo_unitario su riga contratto batte listino
--   5) STADIO 0 PROMO: overlay PREZZO_FISSO sovrascrive origine e prezzo_finale
--   6) Errore E_CATEGORIA_LISTINO_NON_MAPPATA: nessun match in matrice
--   7) Errore E_PARAMETRO_INVALIDO: BA inesistente
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- Precondizioni condivise.
-- Il BA deve essere su utility SENZA dimensione tipo/classe: il trigger
-- di snapshot contratti_utilities scatterebbe il guard tipo/classe se la
-- utility avesse tipi_utenze popolata.
CREATE TEMP TABLE tmp_ctx AS
SELECT
    ba.id                       AS ba_id,
    ba.categoria_cliente_id     AS categoria_id,
    ba.istanza_utility_id       AS istanza_utility_id,
    ba.utility_id               AS utility_id,
    -- 2026-10-08 (§F.2): l'emittente e' quello del BA, non il primo per id: il
    --   listino del contratto dev'essere del suo emittente (guard nuovo), e la riga
    --   della matrice categorie_clienti_listini con lui.
    (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.id = anagrafiche.fn_get_emittente_fiscale_pk(ba.id)) AS emittente_srid,
    a.id                        AS articolo_id,
    a.uom_id                    AS uom_id,
    a.listino_tipologia_id      AS tipologia_id
  FROM anagrafiche.billing_account ba
  JOIN catalogo.articoli a
    ON a.attivo IS TRUE
   AND a.listino_tipologia_id IS NOT NULL
   -- rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): la riga di
   --   contratto del test 3 vuole la tipologia dell'articolo fra quelle della utility del
   --   cliente (guard del perimetro).
   AND EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                WHERE ltu.utility_id = ba.utility_id
                  AND ltu.tipologia_id = a.listino_tipologia_id
                  AND ltu.attivo)
 WHERE ba.categoria_cliente_id IS NOT NULL
   AND NOT EXISTS (
       SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
   )
   -- 🔴 UTILITY COMPATIBILE CON L'EMITTENTE, aggiunto il 2026-08-18.
   --   `config.utilities_tipi_ruolo` e' una matrice: non tutte le utility
   --   ammettono tutti i tipi di ruolo. La fixture sceglieva il billing account
   --   e l'emittente in modo INDIPENDENTE, e la coppia che ne usciva —
   --   utility 4 + tipo ruolo 7 — la matrice non la ammette. Il guard
   --   rispondeva «Tipo ruolo 7 non ammesso per utility 4» e il file moriva
   --   nella fixture.
   --   ⚠️ La condizione si legge dalla matrice, non si fissa una utility a
   --   mano: cosi' la fixture segue la configurazione invece di scommetterci
   --   contro, e non torna rossa il giorno che la matrice cambia.
   AND EXISTS (
       SELECT 1
         FROM config.utilities_tipi_ruolo utr
         JOIN anagrafiche.soggetti_ruoli sr
           ON sr.id = (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
                        WHERE ef.id = anagrafiche.fn_get_emittente_fiscale_pk(ba.id))
        WHERE utr.utility_id = ba.utility_id
          AND utr.tipo_ruolo_id = sr.tipo_ruolo_id
          AND utr.attivo IS TRUE
   )
   -- ⚠️ E senza contratti sull'istanza. Spostando la scelta sulla utility
   --   compatibile si finiva su un billing account la cui istanza ha un
   --   contratto «modalita' C», che pretende l'articolo negoziato e fa fallire
   --   la risoluzione con «articolo .../uom 1 non negoziato».
   --   Questo file verifica la risoluzione del prezzo **da listino**: un
   --   contratto di mezzo e' un'altra strada del resolver, e un'altra storia.
   --   Escluderlo non indebolisce il test — lo mette sul percorso che dichiara
   --   di verificare. (Candidati che soddisfano tutte le condizioni: 3.)
   AND NOT EXISTS (
       SELECT 1 FROM vendite.contratti c
        WHERE c.istanza_utility_id = ba.istanza_utility_id
   )
   -- 2026-10-08 (§F.2): e un listino della tipologia dell'articolo, della utility e
   --   dell'emittente del BA (quello che tmp_ctx_listino sceglie qui sotto).
   AND EXISTS (
       SELECT 1 FROM vendite.listini l
         JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = l.emittente_soggetto_ruolo_id
        WHERE l.attivo IS TRUE
          AND l.tipologia_id = a.listino_tipologia_id
          AND l.utility_id   = ba.utility_id
          AND ef.id = anagrafiche.fn_get_emittente_fiscale_pk(ba.id)
   )
 ORDER BY ba.id, a.id
 LIMIT 1;

-- Listino di test: tipologia coerente con l'articolo (il guard
-- trgfn_listini_righe_guard_tipologia verifica articolo.listino_tipologia_id =
-- listino.tipologia_id).
-- ⚠️ 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: qui c'era scritto
--   «l'utility del listino puo' essere qualsiasi». Non e' piu' vero: il listino di
--   un contratto e' della sua utility e del suo emittente (guard nuovo). Articolo e
--   tipologia vengono dai dati e sono il soggetto del test, quindi si FILTRA invece
--   di ricostruire: stessa utility ed emittente del BA.
CREATE TEMP TABLE tmp_ctx_listino AS
SELECT l.id AS listino_id
  FROM vendite.listini l, tmp_ctx t
 WHERE l.tipologia_id = t.tipologia_id
   AND l.attivo       = TRUE
   AND l.utility_id   = t.utility_id
   AND l.emittente_soggetto_ruolo_id = t.emittente_srid
 ORDER BY l.id
 LIMIT 1;

-- Se non esiste un listino coerente, creiamo condizioni minime (non facciamo
-- insert su listini in questo test: richiede FK a emittente + tipologia +
-- utility, si tratta di dato master; assumiamo disponibile in dev). In mancanza,
-- i test falliranno in modo diagnosticabile.
SELECT isnt(
    (SELECT COUNT(*)::int FROM tmp_ctx_listino),
    0,
    '(precondizione) esiste almeno un listino attivo coerente con utility/tipologia dell''articolo di test'
);

-- Riduce a 1 test + 5 da qui; aggiorno plan a posteriori nei commenti se mancano setup.
-- Creo la versione attiva del listino (se non c'e' gia' una che copre oggi).
INSERT INTO vendite.listini_versioni(listino_id, codice_versione, valido_dal, valido_al, stato, attivo)
SELECT l.listino_id, 'PGTAP_V5_VER', script.fn_data_operativa(), script.fn_data_operativa() + 365, 'ATTIVA', TRUE
  FROM tmp_ctx_listino l
WHERE NOT EXISTS (
    SELECT 1 FROM vendite.listini_versioni lv
     WHERE lv.listino_id = l.listino_id
       AND lv.attivo = TRUE
       AND lv.validita @> script.fn_data_operativa()
)
ON CONFLICT DO NOTHING;

CREATE TEMP TABLE tmp_ctx_versione AS
SELECT lv.id AS versione_id, lv.listino_id
  FROM vendite.listini_versioni lv, tmp_ctx_listino l
 WHERE lv.listino_id = l.listino_id
   AND lv.attivo IS TRUE
   AND lv.validita @> script.fn_data_operativa()
 ORDER BY lv.id DESC
 LIMIT 1;

-- Riga listino con prezzo base 100.
INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.versione_id, t.articolo_id, t.uom_id, 100
  FROM tmp_ctx_versione v, tmp_ctx t
ON CONFLICT DO NOTHING;

-- Matrice categoria -> listino: classe specifica + variazione PERCENTUALE -10%
INSERT INTO anagrafiche.categorie_clienti_listini(
    categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id,
    classe_utenza_id, listino_id,
    tipo_variazione, valore_variazione,
    valido_dal, valido_al)
SELECT t.categoria_id, t.utility_id, t.emittente_srid,
       (SELECT id FROM config.classi_utenze ORDER BY id LIMIT 1),
       v.listino_id,
       'PERCENTUALE', -10,
       script.fn_data_operativa(), script.fn_data_operativa() + 365
  FROM tmp_ctx t, tmp_ctx_versione v;

-- Seconda riga matrice: fallback classe NULL + variazione VALORE_FISSO -5
INSERT INTO anagrafiche.categorie_clienti_listini(
    categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id,
    classe_utenza_id, listino_id,
    tipo_variazione, valore_variazione,
    valido_dal, valido_al)
SELECT t.categoria_id, t.utility_id, t.emittente_srid,
       NULL,
       v.listino_id,
       'VALORE_FISSO', -5,
       script.fn_data_operativa(), script.fn_data_operativa() + 365
  FROM tmp_ctx t, tmp_ctx_versione v;

-- 1) STADIO 2 CATEGORIA: match con classe specifica -> prezzo = 100 * (1 + (-10)/100) = 90
SELECT is(
    (SELECT prezzo_finale FROM vendite.fn_resolve_prezzo_listino_v2(
        (SELECT articolo_id FROM tmp_ctx),
        (SELECT uom_id FROM tmp_ctx),
        script.fn_data_operativa(),
        (SELECT ba_id FROM tmp_ctx),
        (SELECT utility_id FROM tmp_ctx),
        (SELECT emittente_srid FROM tmp_ctx),
        (SELECT id FROM config.classi_utenze ORDER BY id LIMIT 1)
    )),
    90::numeric,
    'STADIO 2 CATEGORIA con classe specifica + PERCENTUALE -10%: prezzo_finale = 90'
);

-- 2) STADIO 2 CATEGORIA: classe diversa -> fallback classe NULL -> 100 + (-5) = 95
-- Cerco una classe DIVERSA da quella mappata sopra (se esiste).
SELECT is(
    (SELECT prezzo_finale FROM vendite.fn_resolve_prezzo_listino_v2(
        (SELECT articolo_id FROM tmp_ctx),
        (SELECT uom_id FROM tmp_ctx),
        script.fn_data_operativa(),
        (SELECT ba_id FROM tmp_ctx),
        (SELECT utility_id FROM tmp_ctx),
        (SELECT emittente_srid FROM tmp_ctx),
        (SELECT id FROM config.classi_utenze
          WHERE id <> (SELECT id FROM config.classi_utenze ORDER BY id LIMIT 1)
          ORDER BY id LIMIT 1)
    )),
    95::numeric,
    'STADIO 2 CATEGORIA fallback classe NULL + VALORE_FISSO -5: prezzo_finale = 95'
);

-- 3) STADIO 1 CONTRATTO_OVERRIDE: contratto con riga prezzo_unitario = 42
-- 🔴 SI COMPONE IN DRAFT E POI SI ATTIVA, corretto il 2026-08-18.
--   Il contratto nasceva gia' ATTIVO e la riga si inseriva dopo: da quando
--   esiste `trg_contratti_righe_a05_doc_righe_lock_fuori_bozza` quella sequenza e'
--   vietata (il pricing di un contratto attivo e' immutabile). Lo stato finale
--   non cambia — serve ATTIVO perche' il resolver lo consideri — cambia il
--   momento in cui ci si arriva, che e' anche l'ordine che segue l'applicazione.
--   ⚠️ `tipo_eccezione` = OVERRIDE, non a caso: il CHECK
--   `chk_contrighe_prezzo_per_tipo_eccezione` pretende un prezzo valorizzato per
--   OVERRIDE/AGGIUNTA, e qui il prezzo (42) e' proprio il punto del test —
--   e' un prezzo che SCAVALCA il listino, che e' la definizione di OVERRIDE.
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id, stato_doc_contratto_id,
    valido_dal, valido_al, listino_id, tipo_variazione_globale, valore_variazione_globale)
SELECT 'PGTAP_V5_CONTR', t.ba_id, t.istanza_utility_id, t.utility_id,
       (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),
       script.fn_data_operativa(), script.fn_data_operativa(), v.listino_id, NULL, NULL
  FROM tmp_ctx t, tmp_ctx_versione v;

-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, prezzo_unitario,
                                    tipo_eccezione, attivo, qta_operativa, tipo_erogazione)
SELECT c.id, t.articolo_id, 42,
       -- rev 2026-10-07 (giro B3): erogazione VUOTA, la riga la eredita dalla tipologia
       --   dell'articolo (era CANONE scritto a mano).
       -- rev 2026-10-07 (§D.4 punto 2, 20261007-28/-30): la quantita' solo se la fonte
       --   ereditata la porta (FISSA); con una fonte a valle (es. le LETTURE di un
       --   articolo CONSUMO) resta vuota. L'articolo viene dai dati: si chiede alla sede unica.
       'OVERRIDE'::vendite.tipo_eccezione_contratto, TRUE,
       (SELECT 1 FROM vendite.fn_articolo_erogazioni(t.articolo_id) e
         WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA'),
       NULL
  FROM vendite.contratti c, tmp_ctx t
 WHERE c.numero = 'PGTAP_V5_CONTR';

-- rev 2026-10-27 (brief-modello-documento-vendita §11, debito del giro 8): il contratto ha la
--   porta sulla colonna di stato; l'attivazione passa dal verbo, che la fixture chiama con
--   emetti_contratto concessa (prima un UPDATE diretto, ora fermato dalla porta).
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, c.id, 'ATTIVO')
  FROM vendite.contratti c
 WHERE c.numero = 'PGTAP_V5_CONTR';

SELECT is(
    (SELECT origine FROM vendite.fn_resolve_prezzo_listino_v2(
        (SELECT articolo_id FROM tmp_ctx),
        (SELECT uom_id FROM tmp_ctx),
        script.fn_data_operativa(),
        (SELECT ba_id FROM tmp_ctx),
        (SELECT utility_id FROM tmp_ctx),
        (SELECT emittente_srid FROM tmp_ctx),
        NULL
    )),
    'CONTRATTO_OVERRIDE'::varchar,
    'STADIO 1 CONTRATTO_OVERRIDE: riga con prezzo_unitario batte listino'
);

-- 4) STADIO 0 PROMO: overlay PREZZO_FISSO sovrascrive origine (la categoria deve partecipare)
-- Controllo: la categoria del BA deve avere partecipa_promo = true (cambio flag se serve).
UPDATE anagrafiche.categorie_clienti
   SET partecipa_promo = TRUE
 WHERE id = (SELECT categoria_id FROM tmp_ctx);

-- 🔴 LA PROMO PARTE DOMANI, corretto il 2026-08-18.
--   `trgfn_promo_articoli_guard_data_driven` vieta una promo con `valido_dal`
--   antecedente o uguale a oggi: una promozione si annuncia, non si retrodata.
--   La fixture la faceva partire da `CURRENT_DATE` e moriva li'.
--   ⚠️ Non basta spostare la promo: va spostata anche la DATA A CUI SI CHIEDE
--   il prezzo, piu' sotto. Se la promo parte domani e si risolve per oggi, il
--   test diventa verde senza aver mai attraversato lo stadio PROMO — il modo
--   piu' silenzioso di perdere una copertura.
INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
    tipo_variazione, valore_variazione, valido_dal, valido_al)
SELECT 'PGTAP_V5_PROMO', 'Promo test', t.articolo_id, t.uom_id,
       'PREZZO_FISSO', 12.5,
       script.fn_data_operativa() + 1, script.fn_data_operativa() + 365
  FROM tmp_ctx t;

-- 🔴 IL CONTRATTO NON SI CANCELLA PIU': SCADE. Corretto il 2026-08-18.
--   Qui si cancellavano righe e contratto per non far vincere lo STADIO 1. Non
--   e' piu' possibile: `trg_contratti_righe_a05_doc_righe_lock_fuori_bozza` blocca
--   anche il DELETE su un contratto ATTIVO, ed e' giusto — un contratto attivo
--   non si smonta, si chiude.
--   ⚠️ Cosi' il fixture dice anche una cosa piu' vera: il contratto vale FINO A
--   OGGI (`valido_al = script.fn_data_operativa()`), e le asserzioni che seguono chiedono il
--   prezzo per DOMANI, quando non applica piu'. E' la stessa data in cui vive la
--   promo. Nessuna cancellazione, nessuno stato forzato: due documenti con
--   validita' diverse e una domanda posta nel giorno giusto.

SELECT is(
    (SELECT origine FROM vendite.fn_resolve_prezzo_listino_v2(
        (SELECT articolo_id FROM tmp_ctx),
        (SELECT uom_id FROM tmp_ctx),
        script.fn_data_operativa() + 1,   -- il giorno in cui la promo e' viva (vedi sopra)
        (SELECT ba_id FROM tmp_ctx),
        (SELECT utility_id FROM tmp_ctx),
        (SELECT emittente_srid FROM tmp_ctx),
        (SELECT id FROM config.classi_utenze ORDER BY id LIMIT 1)
    )),
    'PROMO'::varchar,
    'STADIO 0 PROMO: overlay sovrascrive origine (PREZZO_FISSO applicato sul prezzo base)'
);

-- 5) E_CATEGORIA_LISTINO_NON_MAPPATA: rimuovo le righe matrice e riprovo senza contratto
DELETE FROM anagrafiche.categorie_clienti_listini
 WHERE categoria_cliente_id = (SELECT categoria_id FROM tmp_ctx);

-- Rimuovo anche la promo per evitare che STADIO 0 mascheri l'errore
-- (la promo si applica DOPO la risoluzione del prezzo base, quindi un fallimento
-- in STADIO 2 risale al resolver comunque -> la promo non "salva" nulla).
DELETE FROM vendite.promo_articoli WHERE codice = 'PGTAP_V5_PROMO';

SELECT throws_ok(
    $$SELECT * FROM vendite.fn_resolve_prezzo_listino_v2(
        (SELECT articolo_id FROM tmp_ctx),
        (SELECT uom_id FROM tmp_ctx),
        script.fn_data_operativa() + 1,   -- il contratto e' scaduto ieri: qui non applica
        (SELECT ba_id FROM tmp_ctx),
        (SELECT utility_id FROM tmp_ctx),
        (SELECT emittente_srid FROM tmp_ctx),
        NULL
    )$$,
    'P0001',
    NULL,
    'Nessun match in matrice -> E_CATEGORIA_LISTINO_NON_MAPPATA'
);

-- 6) BA inesistente -> E_PARAMETRO_INVALIDO
SELECT throws_ok(
    $$SELECT * FROM vendite.fn_resolve_prezzo_listino_v2(
        (SELECT articolo_id FROM tmp_ctx),
        (SELECT uom_id FROM tmp_ctx),
        script.fn_data_operativa(),
        999999999,
        (SELECT utility_id FROM tmp_ctx),
        (SELECT emittente_srid FROM tmp_ctx),
        NULL
    )$$,
    'P0001',
    NULL,
    'BA inesistente -> E_PARAMETRO_INVALIDO'
);

SELECT * FROM finish();
ROLLBACK;
