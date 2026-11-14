# Brief DB — Gli stati dei documenti: ogni significato dal vocabolario

## ⏭️ Chi riparte — aggiornato al 2026-11-14

**Riparte: il team DB**, col giro 6a (il preventivo, §6.15). Il giro 5 è applicato e verde (Tid, 2026-11-14). D-LOCK e i giri 3 e 4, con D-ANN, sono applicati e verdi
(Tid, 2026-11-14). In parallelo il team BE (BE-V1, BE-T1, BE-T2: la rigenerazione dei codici, aggiunta il 2026-11-14 su segnalazione del BE) e il team FE
(FE-V2, FE-S8). Via di Tid del 2026-11-14 a tutti i giri («procedi anche con tutti gli altri giri»). Il giro 2-bis (V-1: `20261113-38`, `-39`) è applicato e verde (Tid, 2026-11-14). Il BE/FE ha fatto le richieste del giro 2 e di
D-SCAD (`fec6a713fa`, PR #112, 2026-11-14) e ha trovato V-1 e V-2 (§6.9).
Il giro 1 è applicato, verde e mergiato (2026-11-13); il BE ha fatto R-2 (`e174a302e2`), quindi nel giro 5 la
colonna `in_gioco` esce dalla vista.
Il 2026-11-12 il DB ha riverificato il brief sul catalogo di dbdev (§5) e, col via di Tid, ha scritto il giro 1 (§6).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ DB | i difetti, trovati riscrivendo le pagine `config/manual/stati_doc_*` (giro DOC.4 di `brief-db-sorgente-documento-e-riga`), verificati sul DB | §2 | — |
| 2 | ✅ Tid | il brief si apre: i difetti degli stati vanno qui, non nel cantiere della provenienza (2026-11-08) | — | — |
| 3 | ✅ Tid | **S-1**: `terminale` = nessun passaggio **a mano** in uscita; gli automatismi restano (A, 2026-11-08) | §3 | — |
| 4 | ✅ DB | censimento: per ogni difetto i lettori e gli scrittori, la proposta di correzione, il pgTAP, le ricadute (2026-11-08) | §4 | — |
| 5 | ✅ Tid | S-2 … S-10 come proposte dal DB («confermo la tua proposta», 2026-11-08) | §4.9 | — |
| 6 | ✅ Tid | via allo sviluppo (2026-11-12) | — | — |
| 7 | ✅ DB | giro 1, il vocabolario fiscale (②, ⑥, S-6, S-7 e la parte fiscale di S-2): nove changeSet, prova in transazione, pgTAP adeguati e nuovi (2026-11-12) | §6.2, §6.3 | — |
| 8 | ✅ Tid | apply del giro 1 (`20261112-44 … -52`) e pgTAP del §6.3: verdi (2026-11-13) | §6.3 | — |
| 8b | ✅ Tid | R-1 … R-3 come proposte dal DB; per R-2 il ritiro di `in_gioco` (2026-11-13) | §6.4 | — |
| 9 | ✅ DB | giro 2, l'offerta (③, S-3, S-10, S-2 per l'offerta, il builder): sei changeSet, due CSV, prova in transazione, pgTAP nuovo e uno adeguato (2026-11-13) | §6.5, §6.6 | via di Tid (2026-11-13) |
| 9b | ✅ Tid | apply di `20261112-59 … -64` e dei due mirror; pgTAP del §6.6: verdi (2026-11-13) | §6.6 | 9 |
| 9c | ✅ BE/FE | le richieste del giro 2: il rifiuto dal vocabolario (BE), `stato_terminale` al posto di `STATI_OFFERTA_TERMINALI` (FE) (`fec6a713fa`, 2026-11-14) | §6.7 | 9b |
| 9c-bis | ✅ Tid | D-SCAD: (a), `esito IS NULL` (2026-11-13) | §6.8 | — |
| 9c-ter | ✅ DB | D-SCAD: `20261112-65`, pgTAP esteso (plan 15), prova in transazione (2026-11-13) | §6.8 | 9c-bis |
| 9c-quater | ✅ Tid | apply di `20261112-65`, pgTAP `test-offerta-guard-dal-vocabolario-v1`: verde (2026-11-13) | §6.8 | 9c-ter |
| 9c-quinquies | ✅ BE/FE | le richieste di D-SCAD: `is_scaduta` nel dettaglio (BE), il badge dal flag da solo e il ritiro di `STATI_OFFERTA_SEGNALA_SCADENZA` (FE) (`fec6a713fa`, 2026-11-14) | §6.8 | 9c-quater |
| 9c-sexies | ✅ BE/FE | la verifica dei giri 2 e D-SCAD: V-1 e V-2, richieste al team DB (2026-11-14) | §6.9 | — |
| 9c-septies | ✅ DB | giro 2-bis, V-1: `20261113-38` (`vendite.fn_offerta_scaduta`), `-39` (la vista la compone), pgTAP esteso (plan 18), prova in transazione (2026-11-14) | §6.10 | via di Tid (2026-11-14) |
| 9c-octies | ✅ Tid | apply di `20261113-38`, `-39`; pgTAP `test-offerta-guard-dal-vocabolario-v1` (plan 18): verde (2026-11-14) | §6.10 | 9c-septies |
| 9c-nonies | **BE** ⏭️ | BE-V1: il dettaglio chiama `vendite.fn_offerta_scaduta` al posto della sottoquery sulla vista | §6.10 | 9c-octies |
| 9c-decies | ✅ Tid | **D-LOCK**: (a), il lock riconosce la bozza da `iniziale` (2026-11-14) | §6.10 | — |
| 9c-undecies | ✅ DB | D-LOCK (a) e V-2: `20261113-40` (`script.fn_doc_lock_regola`), `-41` (`can_edit_eccezioni` dal lock); 48 pgTAP con l'estratto, tre riportati al modello, cinque test nuovi (2026-11-14) | §6.11 | 9c-decies |
| 9c-terdecies | ✅ Tid | apply di `20261113-40`, `-41`; i pgTAP del §6.11: verdi (2026-11-14) | §6.11 | 9c-undecies |
| 9c-duodecies | **FE** ⏭️ | FE-V2: il lucchetto del drawer dalle chiavi `can_edit_*` della capability, non dal codice BOZZA | §6.10 | — |
| 9d | ✅ DB | giro 3: `terminale`, bolla e reso (④, ⑦, S-4, S-5, S-3 del reso): `20261113-42 … -50`, 129 pgTAP con l'estratto, uno nuovo e tre adeguati (2026-11-14) | §6.12 | via di Tid (2026-11-14) |
| 9e | ✅ DB | giro 4: gli stati che nessun passaggio raggiunge (⑤, S-8, R-3): `20261114-03`, due CSV, il presidio nuovo della raggiungibilità (2026-11-14) | §6.13 | via di Tid (2026-11-14) |
| 9f | ✅ Tid | apply (verde, 2026-11-14) dei giri 3 e 4 (`20261113-42 … -50`, `20261114-03`); i pgTAP dei §6.12 e §6.13, e `vendite/test-documenti-numerazione-trasloco-v1` e `vendite/test-fn-list-ordini-da-pushare-v1`, che lo strumento non lancia | §6.12, §6.13 | 9d, 9e |
| 9g | ✅ Tid | **D-ANN**: (a), ANNULLATA non vale per la fattura (`applica_fattura` = false, dal CSV, 2026-11-14) | §6.12, §6.13 | — |
| 9h | ✅ Tid | i numeri dei giri 5 e 6: dal primo libero (Tid, 2026-11-14: «-04»; il `-04` l'aveva preso l'altra sessione, si parte dal `-05`) | §6.13 | — |
| 9i | ✅ DB | giro 5: il listino, i COMMENT stantii, `in_gioco` (⑧, S-9, §4.8, R-2): `20261114-05 … -07`, 31 pgTAP con l'estratto, tre adeguati (2026-11-14) | §6.14 | 9h |
| 9i-bis | ✅ Tid | apply di `20261114-05 … -07` (il `-05` al secondo tentativo, dopo la correzione della `preCondition`); i pgTAP del §6.14: verdi (2026-11-14) | §6.14 | 9i |
| 9i-ter | ✅ DB | giro 6: il censimento, circa 55 oggetti in sei documenti, e l'ordine (2026-11-14) | §6.15 | — |
| 9i-quater | **DB** ⏭️ | giri 6a … 6f, un documento per volta: preventivo, ordine, contratto, bolla, reso, listino | §6.15 | — |
| 9j | **BE** ⏭️ | BE-T1: la frase di `doc_terminale` in `api_percorso.md` | §6.12 | — |
| 9k | **FE** ⏭️ | FE-S8: costanti, chiavi i18n e commenti dei quattro stati d'ordine ritirati | §6.13 | 9f |
| 10 | BE/FE | le ricadute del §4.10 degli altri giri (FE: costanti degli ordini, giro 4). Il giro 1 non ne ha; quelle del giro 2 sono la riga 9c | §4.10 | il giro che le porta |
| 11 | ✅ BE | R-2: il test Django che legge `in_gioco` passa a `pre_fiscale` (`e174a302e2`, 2026-11-13) | §6.4 | — |

**Decisioni aperte di Tid:** nessuna; D-ANN e D-LOCK decise il 2026-11-14 (a). D-SCAD decisa il 2026-11-13 (a). Decise il 2026-11-13 (§6.4): R-1, S-3 revocata per il fiscale (il cancello IVA
resta su EMESSA, eccezione voluta); R-2, `in_gioco` si ritira (giro 5, dopo la riga 11); R-3, il lotto non diventa
REGISTRATO (`applica_lotto` = false, giro 4). Decise il 2026-11-08: S-1, lettura A; S-2 … S-10 come proposte dal DB (§4.9; per S-8 il ritiro, non
l'`attivo = false`). **Lavoro da committare:** il giro 2-bis (§6.10: due changeSet, il pgTAP, tre pagine `manual/`) e D-LOCK (§6.11: due changeSet, quattro pgTAP, quattro pagine `manual/`), i giri 3 e 4 (§6.12, §6.13: undici changeSet, sei CSV e tre mirror, due pgTAP nuovi e cinque adeguati, dodici pagine), il giro 5 (§6.14: tre changeSet, tre pgTAP adeguati, due pagine), questo brief; D-SCAD (§6.8) è nel commit di questo brief, il giro 2 nel commit `2502514207`; la verifica del 2026-11-12
(§5) e il giro 1 (§6) sono nel commit `a9b7a0f32e` (PR #108).

> **Chi scrive:** team DB (`dev/db-tid`), 2026-11-08. **A chi:** Tid, poi il team DB.
> **Origine:** il giro DOC.4 di `brief-db-sorgente-documento-e-riga` (§7.3 «Trovato da DOC.4»): riscrivendo le dieci
> pagine dei vocabolari degli stati sono emersi difetti fuori dal tema della provenienza. Tid, 2026-11-08: si apre un
> brief per gli stati.
> **Brief vicini verificati:** `work-done/brief-modello-documento-vendita` (chiuso il 2026-10-31: il significato di uno
> stato lo dice il vocabolario, non un letterale; questo brief ne chiude i residui, non ne revoca niente);
> `analisi-pratiche-valutazione-stato` e `brief-design-proiezione-stato-dominio` (leggono `fase`/`esito`/`terminale` per
> la proiezione nelle pratiche: sono i consumatori di S-1, non lo decidono); `gestione-pratiche-come-procedere` §3 (le
> segnalazioni di `pratiche`, separate per decisione di Tid). Nessun brief aperto sui vocabolari degli stati.
> **Ambito:** i vocabolari `config.stati_doc_*`, le loro matrici, i guard e i verbi che li leggono. ⚠️ Tocca tutti i
> documenti di vendita: è ammesso dal fermo allentato (PROJECT_CONTEXT, «poggia su un pezzo comune già fatto»: il
> vocabolario) e Tid ne ha dato l'ok (2026-11-08).

---

## 1. Il buco in una frase

La guida del modello del documento dice che il significato di uno stato (iniziale, emissione, accettazione, terminale,
annullo) lo dice il vocabolario; in alcuni punti il codice lo dice ancora con un letterale, o il vocabolario dichiara un
significato che la matrice smentisce.

## 2. I difetti (verificati sul DB, 2026-11-08; non provati in transazione)

| # | Difetto | Dove |
| --- | --- | --- |
| ② | Il lotto di fatturazione non nasce dal vocabolario: `vendite.fn_create_fatturazione_lotto` sceglie lo stato col letterale `'DRAFT'`, e `trgfn_doc_stato_iniziale` non è montato su `vendite.fatturazione_lotti` (mentre `fn_riporta_lotto_a_draft` legge già `iniziale`) | `vendite.fatturazione_lotti` |
| ③ | Il guard di transizione dell'offerta confronta i codici (`'BOZZA'`, `'EMESSA'`, `'ACCETTATA'`, `'ANNULLATA'`) nelle condizioni e nelle date del passaggio, invece di `emissione`, `accettazione`, `is_abortito` | `vendite.trgfn_offerte_commerciali_guard_transizione` |
| ④ | `terminale` è dichiarato su stati che hanno passaggi attivi in uscita (automatici): `SUPERATA→EMESSA` (offerte), `EVASO→ACCETTATO` (preventivi), `EVASO→PARZIALMENTE_EVASO` ed `EVASO→CONFERMATO` (ordini). Il COMMENT dice «non evolverà più», e `pratiche.fn_stato_sorgente` lo legge | vocabolari e matrici; S-1 |
| ⑤ | Quattro stati d'ordine attivi che nessun passaggio raggiunge: `ALLOCATO`, `SPEDITO`, `CONSEGNATO`, `FATTURATO` | `config.stati_doc_ordini` |
| ⑥ | Il controllo di `applica_fattura` in `trgfn_fatture_guard_stato` sta nel solo ramo «prima assegnazione» (UPDATE con stato precedente NULL), che non scatta: lo stato è NOT NULL e lo mette il trigger alla nascita | `vendite.fatture` |
| ⑦ | Bolla e reso non dichiarano `esito` e `terminale`: li ricavano `vw_stato_sorgente_ddt` e `vw_stato_sorgente_reso` con una regola scritta nella vista | `config.stati_doc_ddt`, `config.stati_doc_reso` |
| ⑧ | (minore) `config.stati_doc_listino_versioni` non ha `fase` (e quindi il CHECK che lega `terminale` a `fase`), e l'indice di `iniziale` si chiama `ux_…` invece di `uq_…` | `config.stati_doc_listino_versioni` |

**COMMENT stantii** (ognuno è un changeSet): `config.stati_doc_reso` e la sua `meta` (`fase` in `meta.fase`: è una
colonna); `config.stati_doc_offerte_transizioni` («5 transizioni»: sono 7); `config.stati_doc_offerte` (manca
`accettazione`) e le colonne `ordine` (manca 60) e `is_superato` (lo scrive `vendite.fn_offerta_proietta_stato_revisione`);
`codice` di `stati_doc_contratti` (`SOSPESO`, che non c'è), `stati_doc_ddt` e `stati_doc_ordini` (CONFERMATA/ALLOCATA);
`stati_doc_fiscale.fase`; `vendite.contratti.is_abortito_snapshot` (trigger, colonna e vincolo che non ci sono più: oggi
`partecipa_overlap_snapshot`, `ex_contratti_no_overlap`); le colonne di significato degli stati («Emetti» produce numero e
PDF: per offerta, contratto e ordine il numero è assegnato alla nascita).

Le pagine `manual/` descrivono già lo stato di oggi, difetti compresi (DOC.4, 2026-11-08).

## 3. Da decidere (Tid)

* **S-1 — che cosa vuol dire `terminale`.** Due letture, e decidono ④:
  * **A** «nessun passaggio **a mano** in uscita»: gli automatismi (la revisione che riapre, l'evasione che si
    riapre) restano ammessi; si corregge il COMMENT e si dichiara nella matrice quali passaggi sono di sistema
    (`meta.manuale` c'è già). Chi legge `terminale` per dire «finito per sempre» va censito.
  * **B** «nessun passaggio **in assoluto**»: gli stati con uscite perdono `terminale`, e chi oggi lo legge
    (la proiezione nelle pratiche) va rivisto perché un'offerta superata o un ordine evaso non sono più «chiusi».
  * ✅ **Decisa: A** (Tid, 2026-11-08). Proposta DB era A, perché `meta.manuale` distingue già i passaggi di sistema e la proiezione nelle pratiche vuole
    sapere se l'operatore ha ancora qualcosa da fare. Da confermare col censimento dei lettori.

## 4. Il censimento (team DB, 2026-11-08)

Fonti: i corpi in `pg_proc.prosrc` (commenti tolti), `pg_get_viewdef`, `pg_trigger`, `pg_constraint` su dbdev in sola
lettura; `grep` in `backend/apps` e `frontend/src`. Si legge la **struttura** (corpi, vincoli, seed in `80_data`, che è
contratto): nessun conteggio di righe entra come motivo. Nessuna prova in transazione: è un censimento.

Per ogni difetto: (1) chi scrive e chi legge, (2) la correzione sul modello (guida `modello-documento-di-vendita` §4: il
significato di uno stato lo dice il vocabolario), (3) il pgTAP che la presidia **costruendo** il caso, (4) le ricadute.

### 4.1 ② Il lotto non nasce dal vocabolario

**Chi scrive e chi legge.**

| Oggetto | Che cosa fa con lo stato del lotto |
| --- | --- |
| `vendite.fn_create_fatturazione_lotto` | **scrive**: sceglie `codice_interno = 'DRAFT' AND applica_lotto AND attivo … ORDER BY ordine LIMIT 1`, poi `INSERT`. È l'unico `INSERT` del DB sul lotto; lo chiamano `vendite.fn_get_or_create_lotto` (BE: `pipeline_repository.py:516`) e `dbops.fn_pgtap_crea_lotto` |
| `vendite.fatturazione_lotti.stato_doc_fiscale_id` | **nullable** (la fattura invece è `NOT NULL`); nessun trigger della nascita: `script.trgfn_doc_stato_iniziale` è montato su undici testate, non sul lotto |
| `vendite.fn_riporta_lotto_a_draft` | legge già `iniziale` (rev 2026-10-27): il modello giusto, accanto |
| `vendite.trgfn_fatturazione_lotti_guard_stato` | legge il NULL: il ramo «prima assegnazione» (vedi ⑥) |
| `vendite.vw_documenti_trattenuti_da_lotto`, `vendite.vw_lotti_fase` | gestiscono il lotto **senza stato** (LEFT JOIN fail-closed, stato «IGNOTO»): lo ammettono perché la colonna è nullable |

Trovati dal censimento, stessa famiglia (letterale `'DRAFT'` per dire «iniziale» sul vocabolario fiscale):
`script.fn_check_lotto_fatture_pre_fiscali`, `vendite.trgfn_fatture_guard_uscita_draft`; e
`vendite.fn_imposta_data_documento_lotto` con `codice_interno IN ('DRAFT','EMESSA')`, una copia sopravvissuta della
regola «prima del congelamento» che gli altri lettori leggono già da `congela_fiscale` (i commenti di
`fn_genera_scadenze_fattura` e fratelli lo dicono: «erano OTTO copie»). Entrano in S-2.

**Correzione.** (a) montare `script.trgfn_doc_stato_iniziale('stato_doc_fiscale_id', 'config.stati_doc_fiscale')` su
`vendite.fatturazione_lotti` (fascia `_a05_`, `BEFORE INSERT`); (b) `fn_create_fatturazione_lotto` non sceglie più lo
stato: passa NULL e lo mette il trigger (come la fattura); (c) `stato_doc_fiscale_id NOT NULL` (S-6); (d) CHECK sul
vocabolario «lo stato iniziale si applica al lotto e alla fattura» (`NOT iniziale OR (applica_lotto AND applica_fattura)`),
così il filtro `applica_lotto` della madre non serve più (vedi ⑥).

**pgTAP (costruito).** Estendere `db/pgtap/script/test-trgfn-doc-stato-iniziale-v1.sql` col montaggio sul lotto:

1. un lotto inserito senza stato nasce nello stato marcato `iniziale`; uno inserito in uno stato diverso →
   `E_DOC_STATO_INIZIALE_NON_VALIDO`;
2. **la marca spostata**: in transazione `iniziale` passa da DRAFT a un altro stato con `applica_lotto` e
   `applica_fattura`; `vendite.fn_create_fatturazione_lotto` crea il lotto **lì** (prova che la madre non ricorda un codice);
3. il CHECK: uno stato iniziale senza `applica_lotto` è rifiutato.

Builder: `dbops.fn_pgtap_crea_lotto` (passa già dalla madre), `dbops.fn_pgtap_crea_mondo_cliente`,
`dbops.fn_pgtap_crea_emittente`.
⚠️ pgTAP da adeguare, perché inseriscono il lotto **a mano** e lo stato lo scelgono loro: con il trigger un lotto si
costruisce in bozza e si porta avanti con `dbops.fn_pgtap_porta_a_stato` (o si crea con `fn_pgtap_crea_lotto`). Passano
la colonna di stato: `vendite/test-vw-lotti-fase-v1`, `test-documento-trattenuto-da-lotto-v1`,
`test-annullamento-chiude-la-vita-v1`, `test-stati-doc-transizioni-giornaliero`, `test-reset-fattura-plafond-consumato-v1`,
`test-lotti-fermi-verdetto-a-db-v1`, `test-stampa-coda-tipo-documento-v1`, `test-vw-dash-competenza-v1` (DRAFT: passa).
La omettono (NULL → bozza, da rileggere se contano sul NULL): `test-registri-fatturazione-scadenza-alla-nascita`,
`test-ricalcola-riepiloghi-iva`, `test-motivo-non-fatturata-v1`, `test-fondi-fattura-lotto`,
`pagamenti/test-fn-get-or-create-vendite-contabile`, `rls/test-rls-lotti-satelliti`, `rls/test-rls-vendite-contabili-lotti`.
Con S-6 il caso «lotto senza stato» di `test-vw-lotti-fase-v1` (test 4, 5, 8) e di `test-documento-trattenuto-da-lotto-v1`
(test 4) non è più costruibile: si ritira insieme al ramo che provava.

**Ricadute.** BE: nessuna sul codice (il BE crea i lotti da `fn_get_or_create_lotto`, firma invariata). Due test Django
inseriscono un lotto a mano passando DRAFT (`backend/apps/vendite/tests/db/test_giornale_trasversale_perimetro.py:60`,
`test_riepilogo_esclude_trattenuti.py:152`): DRAFT è lo stato iniziale, passano anche col trigger. FE: nessuna
(`grep fatturazione_lotti frontend/src`: solo lettura da API).

### 4.2 ③ Il guard dell'offerta confronta i codici

**Chi scrive e chi legge.** `vendite.trgfn_offerte_commerciali_guard_transizione` (montato `BEFORE UPDATE OF
stato_doc_offerta_id`) legge i codici `BOZZA`, `EMESSA`, `ACCETTATA`, `ANNULLATA`, `RIFIUTATA` in sei punti: il
congelamento del listino, indirizzi e righe su BOZZA→EMESSA; i prezzi verso EMESSA/ACCETTATA; l'annullabilità verso
ANNULLATA; le quattro date del passaggio. Il superamento lo legge già da `is_superato`. I significati in colonna ci sono
tutti tranne il rifiuto: `iniziale` (BOZZA), `emissione` (EMESSA), `accettazione` (ACCETTATA), `is_abortito`
(ANNULLATA); **`RIFIUTATA` non ha una colonna** (S-3). Lettori delle date: BE `offerte_repository.py` (97-111, 194-195),
`types.py:937-938`, `script.fn_available_actions_offerta` (campi fermi).

⚠️ **Trovato dal censimento: ③ non è solo dell'offerta.** La stessa forma (un letterale per dire un significato che la
colonna già dichiara) sta nei guard di transizione di **ordine** (`'DRAFT'`→`'CONFERMATO'`, `'ANNULLATO'`),
**contratto** (`'ATTIVO'`, `'CESSATO'`), **preventivo** (`'ACCETTATO'`; l'emissione la legge già dal vocabolario) e
**bolla** (`'DRAFT'`→`'EMESSO'`), e in una quarantina di altri corpi (capability, verbi, guard di bolla, reso e listino):

| Famiglia | Corpi (letterale → colonna che lo dice già) |
| --- | --- |
| guard di transizione | `trgfn_ordini_guard_transizione` (DRAFT→iniziale, CONFERMATO→emissione, ANNULLATO→is_abortito); `trgfn_contratti_guard_transizione_stato` (ATTIVO→emissione, CESSATO→cessazione); `trgfn_preventivi_guard_transizione` (ACCETTATO→accettazione); `trgfn_ddt_guard_transizione` (DRAFT, EMESSO); `trgfn_preventivi_guard_annullamento` (ANNULLATO) |
| capability | `script.fn_available_actions_{contratto,ddt,offerta,ordine,preventivo,reso}` (`v_stato_cod = 'DRAFT'/'BOZZA'` per «in bozza»; EMESSO, ANNULLATO) |
| bolla | `trgfn_ddt_gen_numero_emesso`, `trgfn_ddt_guard_causale_emissione`, `trgfn_ddt_guard_indirizzi_obbligatori`, `trgfn_ddt_guard_transizione_approvazione` (EMESSO→emissione); `script.vw_stati_doc_ddt_merce_partita` (aggiunta il 2026-11-12, §5: EMESSO→emissione per trovare lo stato da cui si conta; il «da lì in poi» per `ordine` resta, scelta (a) di Tid del 2026-10-12) |
| contratto | `trgfn_contratti_freeze_listino_versione`, `trgfn_contratti_set_categoria_cliente_snapshot` (DRAFT, ATTIVO); `fn_get_contratto_attivo` (ATTIVO) |
| reso | `fn_conferma_reso`, `fn_annulla_reso`, `script.fn_check_reso_merce`, `trgfn_resi_righe_guard_quantita` (DRAFT, ANNULLATO) |
| preventivo, ordine | `fn_crea_revisione_preventivo` (DRAFT); `fn_list_ordini_da_pushare` (DRAFT, ANNULLATO) |
| listino | `trgfn_listini_kit_guard`, `trgfn_listini_righe_guard_stato`, `trgfn_listini_righe_guard_periodicita_quota_fissa`, `trgfn_listini_righe_comp_guard_immutabilita_v5`, `trgfn_listini_versioni_guard_per_stato`, `script.fn_check_versione_listino_eliminabile`, `fn_check_listino_provenienza`, `fn_listino_ha_storia`, `fn_resolve_prezzo_listino_v2_esito` (BOZZA→iniziale) |
| fiscale | i tre di ② (DRAFT); `trgfn_fatture_guard_stato` (`'EMESSA'` per il cancello IVA: il vocabolario fiscale non ha `emissione`, e non la avrà, R-1 del §6.4) |

Gli altri letterali del censimento nominano uno stato **senza** un significato dichiarato (EVASO, PARZIALMENTE_EVASO;
SPEDITO, CONSEGNATO, RESO della bolla; CONFERMATO del reso; ATTIVA, CHIUSA del listino): sono destinazioni o condizioni
di un processo, e il modello non ha ancora una colonna per dirle. Sono S-3.

**Correzione (l'offerta).** I confronti si scrivono sulle colonne della riga del vocabolario, lette una volta con la
`SELECT` che il guard fa già (la guida: «chi ha già in mano la riga legge la colonna»): `iniziale`/`emissione` per
l'emissione, `emissione OR accettazione` per i prezzi, `is_abortito` per l'annullo; le date per significato
(`emissione` → `data_emissione`, `accettazione` → `data_accettazione`, `is_abortito` → `data_annullamento`, il rifiuto
dalla colonna nuova se S-3). Il resto della famiglia, documento per documento (guida §11), se S-2.

**pgTAP (costruito).** Nuovo `vendite/test-offerta-guard-dal-vocabolario-v1.sql`:

1. il comportamento: BOZZA→EMESSA congela la versione di listino e scrive `data_emissione`; ACCETTATA→ANNULLATA con un
   contratto vivo nato dall'offerta → il motivo di `fn_check_offerta_annullabile`;
2. **la marca spostata**: in transazione `accettazione` passa da ACCETTATA a RIFIUTATA (indice unico parziale: prima
   false, poi true); EMESSA→RIFIUTATA ora scrive `data_accettazione` e solleva il cancello dei prezzi (con un prezzo in
   attesa costruito sulla riga): prova che il guard non ricorda un codice;
3. presidio **sulla forma**, dichiarato tale: il corpo (senza commenti) non nomina più i cinque codici.

Builder: `dbops.fn_pgtap_crea_mondo_cliente`, `dbops.fn_pgtap_crea_listino` + `dbops.fn_pgtap_listino_aggiungi_articoli`,
`dbops.fn_pgtap_porta_a_stato` (offerta, sui passaggi manuali), `dbops.fn_pgtap_concedi_azione`,
`dbops.fn_pgtap_crea_contratto` (`p_offerta_id`, per l'annullabilità). ⚠️ **Non c'è un builder dell'offerta**: oggi ogni
pgTAP che ne serve una la scrive a mano (`test-offerta-al-modello-v1`, `test-fn-available-actions-offerta-v1`,
`test-righe-*`…), cioè la regola di come nasce un'offerta è ricopiata. Proposta: `dbops.fn_pgtap_crea_offerta(p_etichetta,
p_stato_codice_interno, p_billing_account_id, …)` sulla falsariga di `fn_pgtap_crea_contratto`, nello stesso cantiere.

**Ricadute.** Dell'offerta sola: nessuna (codici d'errore e loro parametri invariati; `grep` in `backend/apps`
`frontend/src` dei codici d'errore del guard: solo `_db_errors`, che non cambia). Se S-3 (`rifiuto`):
`backend/apps/vendite/services/offerte_service.py` `registra_rifiuto` sceglie lo stato con `StatoOfferta.RIFIUTATA`, una
copia del significato: passerebbe a un lettore del vocabolario come `registra_accettazione` (`stato_di_accettazione`).

### 4.3 ④ `terminale` con passaggi in uscita (S-1 = A)

**La regola del seed contro la matrice** (lettura del contratto, 2026-11-08):

| Vocabolario | Stato | `terminale` | Uscite attive a mano | Uscite di processo | Con A |
| --- | --- | --- | --- | --- | --- |
| offerte | SUPERATA | true | — | →EMESSA | ✅ |
| preventivi | EVASO | true | — | →ACCETTATO | ✅ |
| ordini | EVASO | true | — | →CONFERMATO, →PARZIALMENTE_EVASO | ✅ |
| bolla (derivato) | CONSEGNATO | true | — (→ANNULLATO c'è, spenta) | →RESO | ✅ |
| bolla (derivato) | RESO | true | — | →CONSEGNATO | ✅ |
| **reso (derivato)** | **CONFERMATO** | **true** (`fase = CHIUSO`) | **→ANNULLATO** (`conferma_reso`) | — | ❌ (S-5) |
| ordini | PARZIALMENTE_EVASO | false | — | →CONFERMATO, →EVASO | ✅ (vedi S-4) |
| listino | ATTIVA | false | — | →CHIUSA | ✅ (vedi S-4) |

Con A i quattro casi del §2 sono **giusti**: correggere il COMMENT basta. Il solo stato che A smentisce è il reso
confermato, e lo produce la regola scritta nella vista (⑦), non un vocabolario.

**`meta.manuale` c'è già, ed è dichiarato ovunque.** Ogni matrice di vendita ha il CHECK
`ck_*_meta_manuale_dichiarato` (`meta ? 'manuale'` e booleano: preventivi, offerte, contratti, ordini, ddt, reso, listino,
fiscale, commessa) e `ck_*_meta_ui` (una riga manuale ha `action_key` e `label_key`). Lo leggono
`script.fn_doc_passaggio` (il verbo comune: `E_DOC_PASSAGGIO_DI_PROCESSO`) e `dbops.fn_pgtap_porta_a_stato`. Accanto,
`meta.nessuna_azione_key` sul vocabolario dichiara gli stati senza uscita a mano (lo presidia
`config/test-transizioni-uscita-manuale-v1`, regola R1). **Non serve dichiarare niente di nuovo nella matrice**: serve
che `terminale` e la matrice non possano dissentire.

**I lettori di `terminale`.**

| Lettore | Dove | Che cosa ci legge | Con A |
| --- | --- | --- | --- |
| `vendite.vw_stato_sorgente_{offerta,preventivo,ordine,contratto}` | DB | passano la colonna | ✅ trasporto |
| `vendite.vw_stato_sorgente_{ddt,reso}` | DB | la **calcolano** (`fase = 'CHIUSO'`) | ❌ ⑦ |
| `script.vw_stato_sorgente`, `pratiche.fn_stato_sorgente` | DB | unione e lettura per chiave | ✅ trasporto |
| `script.vw_pratica_doc_sorgente`, `script.vw_flusso_doc_sorgente` | DB | spareggio dell'ancora: prima il documento **non** terminale («il più vivo») | ✅ «niente da fare a mano»: una SUPERATA cede alla revisione viva; tornata EMESSA, risale (lettura a ogni query, nessuna copia) |
| `pratiche.fn_reconcile_sorgente` | DB | legge **solo** `esito`, non `terminale` | — (l'«auto-chiusura su terminale» del brief di design non è costruita) |
| `backend/apps/pratiche/db/pratiche_repository.py:75, 105`; `types.py:247` | BE | `doc_terminale` dalle due viste, al FE | ✅ trasporto |
| `frontend/src/pratiche/components/PraticaPercorso.vue:206, 337` | FE | sui passi fatti il Tag dello stato del documento si mostra finché non è terminale | ✅ «niente da fare a mano» |
| `frontend/src/vendite/offerte/constants.js:40` `STATI_OFFERTA_TERMINALI` (letto da `OffertaDrawer.vue:205`) | FE | severity del banner; il commento dice già «stati in cui l'operatore non ha più nulla da fare» e che SUPERATA può tornare EMESSA | ✅ di significato, ❌ **copia** del vocabolario in JS (S-10) |
| `config.stati_doc_*` COMMENT di `terminale` (offerte, ordini, preventivi, contratti) | DB | «non evolverà più» | ❌ da riscrivere |
| `config.stati_doc_listino_versioni.terminale` COMMENT | DB | «Nessun passaggio esce da qui» (lettura B) | ❌ da allineare |
| `brief-design-proiezione-stato-dominio.md:175` | doc | «il documento non evolverà più (auto-chiusura milestone)» | ❌ da allineare (debito documentale: fuori da questo file) |
| `db/pgtap/script/test-seed-stati-doc-ordini-evaso-v1.sql:16` | pgTAP | «resta terminale per l'operatore: nessuna uscita manuale» | ✅ |

Nessun lettore usa `terminale` per «finito per sempre» in modo da **fermare** qualcosa (un guard, un job, una copia
persistente): tutti proiettano a lettura. A regge.

**Correzione.** (a) Il COMMENT nuovo di `terminale`, uguale sui cinque vocabolari che la hanno (e su bolla e reso con ⑦):

> true = da questo stato non esce nessun passaggio **a mano**: nessuna riga attiva della matrice con `meta.manuale` =
> true. L'operatore non ha più niente da fare sul documento. Il sistema può ancora spostarlo coi passaggi di processo
> (`manuale` = false: la revisione annullata che riporta emessa la precedente, l'evasione che si riapre); per questo chi
> lo legge lo rilegge, non lo copia. CHECK: implica `fase` = CHIUSO. Non sostituisce `is_abortito`.

(b) Un **building block** che rende la regola un vincolo e non un'abitudine: `script.trgfn_doc_terminale_senza_uscita_manuale`,
montato sulle matrici (`INSERT`, `UPDATE OF stato_da_id, attivo, meta`) e sui vocabolari (`INSERT`, `UPDATE OF terminale`),
col montaggio che nomina vocabolario e matrice come `script.fn_doc_stato_modello`; rifiuta una riga attiva `manuale =
true` che esce da uno stato terminale, e `terminale = true` su uno stato che ne ha una. Codice nuovo (es.
`E_DOC_TERMINALE_CON_USCITA_MANUALE`), sollevato solo da chi scrive la configurazione (le migrazioni). Implicazione,
non equivalenza: S-4.

**pgTAP (costruito).** Nuovo `config/test-terminale-senza-uscita-manuale-v1.sql`, tutto in transazione sulla
configurazione (nessun builder: si scrivono vocabolario e matrice):

1. uno stato nuovo terminale e una riga **manuale** attiva che ne esce → rifiutata; la stessa riga `manuale = false` →
   ammessa; spenta (`attivo = false`) → ammessa, e riaccenderla → rifiutata;
2. `terminale = true` su uno stato con un'uscita manuale attiva → rifiutato;
3. il lettore, a lettura: un'offerta EMESSA con una revisione (`vendite.fn_crea_revisione_offerta`) è SUPERATA e
   `pratiche.fn_stato_sorgente` dice `terminale = true`; annullata la revisione (`vendite.fn_annulla_offerta`) torna
   EMESSA e dice `false`. Builder: quelli dell'offerta di ③ (e `fn_pgtap_crea_offerta`, se si fa).

**Ricadute.** BE: nessuna (`pratiche_repository.py` trasporta). FE: nessuna di comportamento; la copia
`STATI_OFFERTA_TERMINALI` è S-10.

### 4.4 ⑤ Quattro stati d'ordine che nessun passaggio raggiunge

**Chi li nomina.**

| Dove | Che cosa |
| --- | --- |
| seed `config.stati_doc_ordini` | ALLOCATO 30, SPEDITO 40, CONSEGNATO 50 (`fase` IN_CORSO), FATTURATO 70 (CHIUSO, POSITIVO, terminale, `nessuna_azione_key` `vendite.ordini.stato_info.fatturato`); nessuna riga della matrice entra né esce |
| `vendite.fn_list_ordini_da_pushare` | `NOT IN ('DRAFT','ANNULLATO','FATTURATO')`: FATTURATO come «cintura» (il commento: l'anti doppia fatturazione vera è il NOT EXISTS sulle attività EMESSA) |
| `acquisti.ordini`, `acquisti.ordini_righe`, `vendite.ordini_righe` | FK su `config.stati_doc_ordini`: il vocabolario è **condiviso** con l'acquisto, che non ha guard di transizione (guida §10, ❌). Sull'acquisto quei quattro stati non li ferma nessuno |
| `vendite.ordini.fatturazione_trigger` | CHECK `CONFERMATO / SPEDITO / CONSEGNATO`: **un altro asse** (l'evento che rende la merce fatturabile), che riusa i nomi; non legge il vocabolario |
| FE `frontend/src/vendite/ordini/constants.js:15-19` | `STATO_ORDINE.ALLOCATO/SPEDITO/CONSEGNATO/FATTURATO`: dichiarati, **nessun lettore** (`grep STATO_ORDINE.ALLOCATO …`: vuoto) |
| FE `frontend/src/locales/{it,en}.json` | `vendite.ordini.stato_info.fatturato` |
| BE | nessun riferimento fuori dai test (`grep` di ALLOCATO e FATTURATO in `backend/apps`, file `.py`) |
| pgTAP | `pratiche/test-proiezione-stato-sorgente` (test 19, la mappa D1 dei nove stati), `vendite/test-testata-dopo-emissione-v1:109`, `script/test-doc-lock-montaggio-v1:470`; ordinamento in `script/test-seed-stati-doc-ordini-evaso-v1` e `vendite/test-vw-situazione-merce-ordine-v1` |
| guide e brief | `guide/gestione-ordini.md:399` («fasi logistiche/finanziarie future, ⏳ non ancora raggiunti»); `work-done/brief-ordini-azioni-data-driven` §7.2 e D-2; `work-done/brief-modello-documento-vendita:1649-1654` («si dichiara, non si tocca»); `work-done/brief-db-proiezione-stato-dominio-rollout-offerte-ordini-contratti:88-92, 249`; `work-in-progress/analisi-simmetria-ordini-acquisto` §4.2 (③: il vocabolario condiviso «parla vendite»; FATTURATO ha un altro posto nel ciclo d'acquisto) |

**La storia della decisione.** Nati col vocabolario (`2a8d6324f6`, 2025-09-12, «preparazione tabelle ordini vendita»).
Il 2026-06-05 (`e52204a37f`, brief-ordini-azioni-data-driven) Tid ratifica **D-2**: fuori dalla matrice «finché privi di
driver», perché la spedizione e la consegna vivono negli stati della bolla e la fatturazione nel `fatturazione_trigger`;
«verranno aggiunti quando magazzino/DDT ne saranno i driver». Il 2026-06-08 (`76c81c832a`) arriva EVASO, poi
PARZIALMENTE_EVASO: l'avanzamento dell'ordine lo proietta il DB dalle bolle. Il modello del documento (ottobre) li
dichiara e non li tocca.

**Correzione.** È S-8. Proposta DB: ritirarli (vedi §4.9).

**pgTAP (costruito).** Un presidio sulla **forma** del contratto (il seed lo è), dichiarato tale: ogni stato attivo di
ogni vocabolario della mappa `script.fn_doc_stato_modello` è raggiungibile dallo stato iniziale lungo righe attive della
matrice. Perché non sia verde per sottrazione, il pgTAP **costruisce** il controesempio: in transazione inserisce uno
stato attivo senza righe in entrata e verifica che il presidio lo trovi. Nessun builder.

**Ricadute (se ritirati).** FE: `frontend/src/vendite/ordini/constants.js` (quattro voci), `frontend/src/locales/it.json`
e `en.json` (`vendite.ordini.stato_info.fatturato`); i commenti che citano `ALLOCATO` come esempio di descrizione
restano veri come esempio solo se lo stato c'è: da riscrivere. ⚠️ Elenco corretto il 2026-11-12 (§5): sono **sei**,
non tre — `frontend/src/vendite/preventivi/components/PreventiviDrawer.vue`,
`frontend/src/vendite/components/CommessaGestioneDrawer.vue`, `frontend/src/vendite/components/ContrattoDrawer.vue`,
`frontend/src/vendite/ordini/components/OrdiniDrawer.vue`, `frontend/src/vendite/ddt/components/DdtDrawer.vue`,
`frontend/src/vendite/resi/components/ResoDrawer.vue`. BE: nessuna. Doc: `guide/gestione-ordini.md` (la riga della
tabella «⏳ non ancora raggiunti»).

### 4.5 ⑥ Il controllo di `applica_fattura` in un ramo che non scatta

**Chi scrive e chi legge.** `vendite.trgfn_fatture_guard_stato` (`BEFORE UPDATE OF stato_doc_fiscale_id`) controlla
`applica_fattura` solo se `OLD.stato_doc_fiscale_id IS NULL`: sulla fattura la colonna è `NOT NULL` e la mette
`trg_fatture_a05_stato_iniziale_ins`, quindi il ramo non è raggiungibile **per contratto**. Il gemello
`vendite.trgfn_fatturazione_lotti_guard_stato` ha lo stesso ramo su `applica_lotto`, e lì **è raggiungibile** perché la
colonna del lotto è nullable (②). Gli altri lettori di `applica_*`: `vendite.fn_create_fatturazione_lotto` (filtro sulla
bozza), `vendite.fn_list_fatturazione_pipeline_steps`, `config.fn_get_stati_doc_fiscale`, `dbops.fn_pgtap_crea_lotto`.
Il FE ne ha solo le etichette (`locales`, «Si applica alla fattura»). Il passaggio normale (OLD non NULL) **non** guarda
`applica_*` della destinazione: lo dice solo la matrice (`solo_lotto`/`solo_fattura`), che non lega la riga alle colonne.

**Correzione.** La regola sulla **destinazione**, non sulla prima assegnazione: a ogni cambio di stato il guard della
fattura chiede `applica_fattura` allo stato d'arrivo, quello del lotto `applica_lotto` (stesso codice
`E_LOTTO_PARAMETRO_NON_COERENTE`, parametro `stato_doc_fiscale_id`); la nascita è coperta dal CHECK di ② (lo stato
iniziale si applica a entrambi). Il ramo «prima assegnazione» si ritira dai due guard. È S-7.

**pgTAP (costruito).** In `vendite/test-stati-doc-transizioni-giornaliero` (o un file nuovo): in transazione
`applica_fattura = false` su uno stato raggiunto da una riga della fattura; la fattura costruita
(`dbops.fn_pgtap_crea_fattura`) portata lì da `vendite.fn_fattura_proietta_stato` → rifiutata; il lotto, con
`applica_lotto = false` e `dbops.fn_pgtap_crea_lotto` + `vendite.fn_lotto_proietta_stato_step` → rifiutato.

**Ricadute.** Nessuna (BE e FE non leggono `applica_*` se non come etichetta).

### 4.6 ⑦ Bolla e reso non dichiarano `esito` e `terminale`

**Chi scrive e chi legge.** `vendite.vw_stato_sorgente_ddt` e `vendite.vw_stato_sorgente_reso` scrivono la regola nella
vista: `esito` = NEGATIVO se `is_abortito`, POSITIVO se `fase = 'CHIUSO'`; `terminale` = `fase = 'CHIUSO'`. Li leggono
`script.vw_stato_sorgente` → `pratiche.fn_stato_sorgente`, `pratiche.fn_reconcile_sorgente` (l'**esito** fa avanzare il
milestone e si scrive in `pratiche.flussi.esito`), le due viste d'ancora, e da lì il BE (`pratiche_repository.py`) e il
FE (`PraticaPercorso.vue`). Lo fissa `vendite/test-vw-stato-sorgente-ddt-reso-v1` (test 3-8, 13). Gli altri vocabolari
dichiarano le due colonne, con il guard `config.trgfn_stati_doc_guard_esito_verdetto` (montato su preventivi, offerte,
ordini, contratti) e il CHECK `terminale ⇒ fase = CHIUSO`.

La regola della vista dissente da A sul reso confermato (§4.3): `fase = CHIUSO` ma l'annullo a mano è attivo.

**Correzione.** Le colonne `esito` e `terminale` (NOT NULL) su `config.stati_doc_ddt` e `config.stati_doc_reso`, il CHECK
`chk_*_terminale_chiuso`, il montaggio del guard dell'esito; il seed dichiara i valori che oggi calcola la vista, tranne
quello che A smentisce (S-5); le due viste leggono le colonne. I COMMENT stantii del reso (`meta.fase`) nello stesso
changeSet.

**pgTAP (costruito).** Adeguare `vendite/test-vw-stato-sorgente-ddt-reso-v1` (test 7 secondo S-5) e aggiungere **la
marca spostata**: in transazione `terminale`/`esito` cambiati su uno stato della bolla, la vista segue (prova che non
ricalcola da `fase`). Builder: `dbops.fn_pgtap_crea_ddt_da_ordine` (CONSEGNATO, EMESSO), `dbops.fn_pgtap_crea_reso` più
`vendite.fn_conferma_reso`/`vendite.fn_annulla_reso`, `dbops.fn_pgtap_concedi_azione`.

**Ricadute.** Nessuna: le viste espongono le stesse colonne (BE `pratiche_repository.py`, FE `PraticaPercorso.vue`
leggono `doc_esito`/`doc_terminale`, invariati). Cambia un valore (il reso confermato), se S-5.

### 4.7 ⑧ Il vocabolario della versione di listino (minore)

**Chi scrive e chi legge.** `config.stati_doc_listino_versioni` ha `iniziale` e `terminale`, non `fase`. La versione di
listino **non è una sorgente** (`config.sorgenti` non la nomina) e nessun corpo legge una sua `fase`: il CHECK
`terminale ⇒ fase = CHIUSO` esiste per la proiezione nelle pratiche, che il listino non ha. Il nome dell'indice
`ux_stati_doc_listino_versioni_iniziale` compare solo nello YAML `20261028-03` e nella pagina auto-gen; nessun pgTAP lo
nomina. I letterali BOZZA del listino sono in S-2, ATTIVA/CHIUSA in S-3.

**Correzione.** Rinominare l'indice in `uq_stati_doc_listino_versioni_iniziale`; allineare il COMMENT di `terminale` al
testo di ④; `fase` secondo S-9.

**pgTAP.** `has_index` sul nome nuovo nel pgTAP del listino al modello (`vendite/test-listino-versione-al-modello-v1`); è
un presidio sulla forma, dichiarato tale.

**Ricadute.** Nessuna.

### 4.8 COMMENT stantii del §2

Ognuno entra nel changeSet del vocabolario che si tocca (②, ④, ⑦, ⑧) o, per i vocabolari che il cantiere non tocca
altrimenti (contratti, fiscale, `vendite.contratti.is_abortito_snapshot`), in un changeSet di soli COMMENT. Nessun lettore
(i COMMENT li legge la doc auto-gen).

### 4.9 Le decisioni che il censimento chiede a Tid

* **S-2 — Il perimetro di ③.** Il guard dell'offerta è un caso di una famiglia (§4.2): un letterale per dire un
  significato che il vocabolario dichiara già in colonna (`iniziale`, `emissione`, `accettazione`, `cessazione`,
  `is_abortito`, `scadenza`, `is_superato`). **Proposta DB:** il cantiere prende **tutta la famiglia**, un documento per
  volta (offerta, preventivo, ordine, contratto, bolla, reso, listino, fiscale), con il presidio sulla forma per
  documento. *Perché:* la guida (§4, §11) non distingue fra un guard e una capability: una copia del significato è una
  seconda verità ovunque stia, e portarne via una sola lascia la regola ricopiata nelle altre.
* **S-3 — I significati che il vocabolario non ha.** Tre stati hanno un significato che il codice usa ma nessuna colonna
  dice: il **rifiuto** (offerta RIFIUTATA: `data_rifiuto`, la motivazione obbligatoria; preventivo RIFIUTATO),
  l'**emissione del reso** (CONFERMATO: lì nasce il numero, `trgfn_resi_gen_numero`; e da lì la merce è rientrata,
  `script.vw_stati_doc_reso_merce_rientrata`, nata il 2026-11-09, §5) e l'**emissione fiscale** (EMESSA: il
  cancello IVA di `trgfn_fatture_guard_stato`). **Proposta DB:** una colonna `rifiuto` su offerte e preventivi (come
  `accettazione`, col suo lettore `script.fn_stato_rifiuto_id`), `emissione` su `stati_doc_reso` e `stati_doc_fiscale`
  (⚠️ per `stati_doc_fiscale` **revocata** da Tid il 2026-11-13, R-1 del §6.4).
  Restano nominati col codice, attraverso `script.fn_doc_stato_id`, gli stati che sono **la destinazione di un
  processo** (EVASO, PARZIALMENTE_EVASO, SPEDITO, CONSEGNATO, RESO della bolla, ATTIVA e CHIUSA del listino): il processo
  nomina la sua destinazione come la nomina la riga della matrice. *Perché:* la colonna serve dove c'è un lettore che
  usa lo stato **per il suo significato**; dove il lettore vuole proprio quello stato, il codice è la chiave giusta.
* **S-4 — `terminale`: implicazione o equivalenza.** **Proposta DB:** implicazione: `terminale ⇒ nessuna uscita attiva a
  mano`, non il contrario. *Perché:* PARZIALMENTE_EVASO non ha uscite a mano ma l'operatore ha ancora da fare (le bolle):
  il lavoro può stare fuori dalla matrice; «niente da fare a mano» vuol dire anche niente da fare fuori dai bottoni di
  stato, e quello lo dichiara il vocabolario, non lo si deduce dalla matrice. Una riga spenta (`attivo = false`) non
  conta come uscita.
* **S-5 — Il reso confermato.** Con A non è terminale: l'annullo (storno) è un passaggio a mano attivo. **Proposta DB:**
  `terminale = false`, `esito` POSITIVO, `fase` resta CHIUSO (il CHECK lega solo terminale → CHIUSO; il reso ha fatto il
  suo lavoro, come l'offerta accettata che resta annullabile). *Perché:* è la stessa regola che vale per offerta e
  preventivo accettati, annullabili e non terminali. Il test 7 di `test-vw-stato-sorgente-ddt-reso-v1` cambia insieme.
* **S-6 — Lo stato del lotto `NOT NULL`.** **Proposta DB:** sì, come la fattura. *Perché:* la guida (§3) vuole che un
  documento nasca nel suo stato iniziale; un lotto senza stato non è sul modello, e i rami fail-closed che lo gestiscono
  (`vw_documenti_trattenuti_da_lotto`, `vw_lotti_fase`) proteggono un caso che il contratto non deve ammettere. I due
  test che lo costruiscono si ritirano con lui.
* **S-7 — `applica_*` sulla destinazione.** **Proposta DB:** il controllo a ogni ingresso nello stato, nei guard di
  fattura e lotto, più il CHECK «l'iniziale si applica a entrambi»; il ramo «prima assegnazione» si ritira. *Perché:* la
  matrice dice da dove a dove, il vocabolario dice a chi si applica lo stato: la regola sulla destinazione copre ogni
  strada, anche quelle future (lo stesso ragionamento del cancello IVA, «sulla destinazione, non sulla coppia»).
* **S-8 — ALLOCATO, SPEDITO, CONSEGNATO, FATTURATO.** **Proposta DB:** ritirarli dal vocabolario (con le loro chiavi
  i18n, le costanti FE e la «cintura» di `fn_list_ordini_da_pushare`). *Perché:* nel modello di oggi l'avanzamento
  dell'ordine lo proietta il DB dalle bolle (EVASO, PARZIALMENTE_EVASO), la spedizione e la consegna sono stati della
  bolla, la fatturazione è della commessa e della fattura: quattro stati d'ordine che le ripetono sarebbero una seconda
  verità, e D-2 li teneva solo «finché privi di driver». In più il vocabolario è condiviso con l'acquisto, che non ha
  guard: finché ci sono, un ordine d'acquisto li può prendere senza regola. Il giorno che servissero, il ciclo d'acquisto
  li dichiarerà nel suo cantiere (`analisi-simmetria-ordini-acquisto` §4.2 propone già il vocabolario per ambito).
  Alternativa: tenerli come «previsti», `attivo = false` e documentati.
* **S-9 — `fase` sulla versione di listino.** **Proposta DB:** non aggiungerla; solo il nome dell'indice e il COMMENT.
  *Perché:* `fase` è l'asse della proiezione nelle pratiche, e la versione di listino non è una sorgente; una colonna
  senza lettore è una dichiarazione che nessuno verifica.
* **S-10 — Le copie fuori dal DB.** `STATI_OFFERTA_TERMINALI` (FE) ripete `terminale`; `StatoOfferta.RIFIUTATA` in
  `registra_rifiuto` (BE) ripete il rifiuto (se S-3). **Proposta DB:** la capability dell'offerta
  (`script.fn_available_actions_offerta`) espone `terminale` dello stato corrente, il FE legge quella e ritira la costante;
  il BE sceglie il rifiuto dal vocabolario. *Perché:* la guida §11: le copie si ritirano nello stesso lavoro.

### 4.10 Le ricadute BE/FE, elenco chiuso

| Difetto | BE | FE |
| --- | --- | --- |
| ② | nessuna (due test Django passano DRAFT, che è l'iniziale) | nessuna |
| ③ | nessuna; con S-3: `backend/apps/vendite/services/offerte_service.py` (`registra_rifiuto`) | nessuna |
| ④ | nessuna | nessuna; con S-10: `frontend/src/vendite/offerte/constants.js`, `frontend/src/vendite/offerte/components/OffertaDrawer.vue` |
| ⑤ (S-8) | nessuna | `frontend/src/vendite/ordini/constants.js`, `frontend/src/locales/it.json`, `frontend/src/locales/en.json`; commenti nei sei drawer del §4.4 (elenco corretto il 2026-11-12) |
| ⑥ | nessuna | nessuna |
| ⑦ | nessuna (stesse colonne; cambia un valore con S-5) | nessuna |
| ⑧ | nessuna | nessuna |

Il codice d'errore nuovo di ④ lo solleva solo chi scrive la configurazione: da registrare (`codici_errore.csv`,
`messaggi_errore.csv`), senza ricadute sul BE oltre al catalogo generato.

## 5. Riverifica sul catalogo (team DB, 2026-11-12)

Fonti: `pg_proc.prosrc`, `pg_get_viewdef`, `pg_trigger`, `pg_index`, `pg_description`, seed e matrici su dbdev (applicato
fino al 2026-11-12), in sola lettura; `grep` in `backend/apps` e `frontend/src`. Fra il 2026-11-08 e il 2026-11-12 sono
entrati circa 400 changeSet, e un centinaio tocca oggetti nominati qui.

**Reggono tutti i difetti del §2 e i fatti del §4.** Letterale `'DRAFT'` nella madre del lotto, nessun trigger della
nascita sul lotto, colonna di stato nullable (②); i cinque codici nel guard dell'offerta, nessuna colonna `rifiuto`
(③); le uscite di processo da SUPERATA, EVASO (preventivi e ordini), CONSEGNATO e RESO della bolla, l'uscita a mano
CONFERMATO→ANNULLATO del reso (④, S-5); i quattro stati d'ordine fuori dalla matrice, la «cintura» FATTURATO di
`fn_list_ordini_da_pushare` (⑤); il ramo «prima assegnazione» di `trgfn_fatture_guard_stato` (⑥); la regola su
`fase = 'CHIUSO'` nelle due viste di bolla e reso (⑦); l'indice `ux_…` e la `fase` che manca sul listino (⑧); tutti i
COMMENT stantii del §2; nessun `terminale` letto da `fn_available_actions_offerta` (S-10). Esistono tutti i pgTAP
citati; non esistono ancora quelli nuovi (`test-offerta-guard-dal-vocabolario-v1`,
`test-terminale-senza-uscita-manuale-v1`) e il builder `dbops.fn_pgtap_crea_offerta`.

**Corretto in questa verifica.**

1. **Mancava al censimento di ③ la vista della bolla** `script.vw_stati_doc_ddt_merce_partita` (BB del 2026-10-12):
   trova lo stato da cui si conta col letterale `'EMESSO'`, mentre `config.stati_doc_ddt.emissione` lo dice già.
   Aggiunta alla riga «bolla» del §4.2. Il resto della regola, «da quello stato in poi» per `ordine`, è la scelta (a)
   di Tid del 2026-10-12 e **non** si tocca qui.
2. **Una vista nuova dopo il brief:** `script.vw_stati_doc_reso_merce_rientrata` (2026-11-09, gemella della
   precedente; la leggono `dbops.vw_resi_confermati_senza_carico`, `vendite.vw_resi_righe_effettive`,
   `vendite.vw_resi_da_riconsegnare`) trova lo stato col letterale `'CONFERMATO'`. È un lettore dell'**emissione del
   reso** di S-3: quando nasce `config.stati_doc_reso.emissione`, legge quella. Aggiunta a S-3.
3. **Le ricadute FE di S-8 erano incomplete.** I commenti che citano `ALLOCATO` come esempio stanno in sei drawer, non
   in tre, e due dei tre percorsi erano sbagliati. Elenco chiuso, coi percorsi interi, corretto nel §4.4 e nel §4.10.
4. Riferimenti di riga che si sono spostati: `guide/gestione-ordini.md` (la riga «⏳ non ancora raggiunti» oggi è la
   402); in `backend/apps/pratiche/db/pratiche_repository.py` il secondo lettore di `terminale` è la `LATERAL` su
   `script.vw_flusso_doc_sorgente` (intorno alla 104).

⚠️ **Per chi sviluppa: i corpi sono cambiati dopo il 2026-11-08.** Il comportamento letto qui regge, ma molti oggetti
del censimento hanno una revisione più recente del brief, e alcune sono più recenti della doc auto-generata:
`vendite.fn_conferma_reso`, `vendite.fn_annulla_reso` (2026-11-09/10), `vendite.fn_list_ordini_da_pushare`
(2026-11-08), `vendite.fn_resolve_prezzo_listino_v2_esito` (2026-11-12),
`vendite.trgfn_listini_righe_comp_guard_immutabilita_v5` (2026-11-11), `pratiche.fn_stato_sorgente` e
`pratiche.fn_reconcile_sorgente` (2026-11-08), `dbops.fn_pgtap_crea_lotto` e i builder di bolla, ordine, preventivo,
fattura e reso (2026-11-08). Il DDL si prende dalla doc auto-gen solo se è stata rigenerata dopo l'ultimo changeSet
sull'oggetto; altrimenti da `pg_get_functiondef`. Mai dagli YAML.

## 6. Lo sviluppo (team DB)

### 6.1 L'ordine dei giri

Un giro per vocabolario o per difetto, così ogni oggetto si apre una volta sola:

| Giro | Che cosa | Difetti e decisioni |
| --- | --- | --- |
| 1 ✅ applicato | il vocabolario fiscale: lotto e fattura | ②, ⑥, S-6, S-7; S-2 sul fiscale. L'emissione fiscale di S-3 è revocata (R-1) |
| 2 ✅ applicato | l'offerta | ③, S-3 (`rifiuto` su offerte e preventivi), S-10 per l'offerta, il builder `dbops.fn_pgtap_crea_offerta` |
| 2-bis ✅ applicato (V-1) | i trovati della verifica BE/FE | V-1 (la sede della scadenza) |
| 2-ter ✅ applicato | D-LOCK (a) e V-2 | ⑨: il lock riconosce la bozza dal vocabolario (§6.11) |
| 3 ✅ applicato | `terminale`, bolla e reso | ④ (il BB e i COMMENT), ⑦, S-4, S-5, S-3 (`emissione` del reso, coi due lettori del §5) |
| 4 ✅ applicato | gli stati d'ordine senza passaggi | ⑤, S-8, il presidio della raggiungibilità; R-3 (`applica_lotto` = false su REGISTRATA) |
| 5 ✅ applicato | il vocabolario del listino e i COMMENT stantii | ⑧, S-9, §4.8; R-2 (il ritiro di `in_gioco`, se la riga 11 è fatta) |
| 6 … | il resto della famiglia di S-2 | un documento per volta: preventivo, ordine, contratto, bolla, reso, listino |

### 6.2 Giro 1 — il vocabolario fiscale (2026-11-12)

| ChangeSet | Che cosa |
| --- | --- |
| `00_schema/config/20261112-44` | CHECK `chk_stati_doc_fiscale_iniziale_applica`: lo stato iniziale si applica a lotto e fattura (§4.1 d) |
| `20_code/vendite/20261112-45` | il trigger della nascita sul lotto, `trg_fatturazione_lotti_a05_stato_iniziale_ins` (§4.1 a) |
| `00_schema/vendite/20261112-46` | `vendite.fatturazione_lotti.stato_doc_fiscale_id NOT NULL` (S-6) |
| `20_code/vendite/20261112-47` | `vendite.fn_create_fatturazione_lotto` non sceglie più lo stato (§4.1 b) |
| `20_code/vendite/20261112-48` | `vendite.trgfn_fatture_guard_stato`: `applica_fattura` sulla destinazione, via il ramo «prima assegnazione» (S-7) |
| `20_code/vendite/20261112-49` | `vendite.trgfn_fatturazione_lotti_guard_stato`: lo stesso con `applica_lotto` (S-7) |
| `20_code/script/20261112-50` | `script.fn_check_lotto_fatture_pre_fiscali`: «pre-fiscale» da `congela_fiscale`, non da DRAFT ed EMESSA (S-2) |
| `20_code/vendite/20261112-51` | `vendite.trgfn_fatture_guard_uscita_draft`: la bozza da `iniziale` (S-2) |
| `20_code/vendite/20261112-52` | `vendite.fn_imposta_data_documento_lotto`: la finestra da `congela_fiscale` (S-2) |

Corpi presi da `pg_get_functiondef` su dbdev, testate ri-ancorate con `%TYPE`, COMMENT riscritti al presente; ogni
changeSet porta nel rollback il corpo e il COMMENT di prima. Il cancello IVA del guard della fattura resta sul codice
EMESSA (R-1: eccezione voluta). Fatto datato, 2026-11-12: ogni stato fiscale ha `applica_lotto` e `applica_fattura` true, e DRAFT ed
EMESSA sono gli unici con `congela_fiscale` false, quindi nessun passaggio di oggi cambia esito. I rami fail-closed di
`vendite.vw_lotti_fase` e `vendite.vw_documenti_trattenuti_da_lotto` restano (sono un LEFT JOIN corretto anche col
NOT NULL); si ritirano i casi dei pgTAP che li costruivano.

Guardrail delle forme, del COMMENT al presente e del preambolo pgTAP: verdi. Estratto provato in `ROLLBACK` sullo
scratch con `scripts/prova_changeset.py`: eseguito per intero, catalogo identico prima e dopo. BE/FE: nessuna ricaduta
(i due test Django che inseriscono un lotto passano DRAFT, che è lo stato iniziale). Pagine `manual/` riscritte:
`config/stati_doc_fiscale`, `vendite/fn_create_fatturazione_lotto`, `vendite/fatturazione_lotti`,
`script/fn_check_lotto_fatture_pre_fiscali`, `vendite/trgfn_fatture_guard_uscita_draft`,
`vendite/fn_imposta_data_documento_lotto`. La doc auto-generata non è rigenerata.

### 6.3 I pgTAP del giro 1

Nuovi o estesi:

* `script/test-trgfn-doc-stato-iniziale-v1` (plan 18 → 22): il lotto nel censimento dei montaggi (test 5, 6: dodici
  testate); nuovi 19 (il lotto dalla madre nasce nello stato iniziale), 20 (un lotto che nasce DEFINITIVA è
  rifiutato), 21 (la marca spostata: con `iniziale` su EMESSA la madre crea il lotto in EMESSA), 22 (il CHECK);
* `vendite/test-stato-fiscale-dal-vocabolario-v1` (nuovo, plan 8): S-7 su fattura e lotto, ognuno col suo contrasto;
  «pre-fiscale» con la marca spostata su `congela_fiscale`; il presidio sulla forma, che tiene a un punto solo l'eccezione di R-1.

Adeguati, perché facevano nascere il lotto in uno stato che il trigger ora rifiuta:

* `vendite/test-annullamento-chiude-la-vita-v1`, `vendite/test-lotti-fermi-verdetto-a-db-v1`,
  `vendite/test-motivo-non-fatturata-v1`: il lotto nasce in bozza e si porta allo stato voluto con
  `dbops.fn_pgtap_porta_a_stato`;
* `vendite/test-vw-lotti-fase-v1` (plan 8 → 5) e `vendite/test-documento-trattenuto-da-lotto-v1` (plan 7 → 6):
  stessa forma, e ritirati i test del lotto senza stato (S-6). In `test-lotti-fermi-verdetto-a-db-v1` c'era un terzo
  caso uguale, il test 24, che il §4.1 non elencava: ritirato anche quello (plan 24 → 23). Tolto da
  `test-vw-lotti-fase-v1` anche il testimone REGISTRATA, che un lotto non raggiunge (R-3);
* `test-documento-trattenuto-da-lotto-v1` ora **costruisce** il suo mondo (`dbops.fn_pgtap_crea_emittente_operatore`,
  runner owner come il gemello): prendeva emittente e tipo documento «da un lotto che c'è già», e su un database senza
  lotti (lo scratch, la CI) non scriveva niente, verde per sottrazione;
* `vendite/test-fondi-fattura-lotto`: solo il commento della fixture (il lotto ora nasce in bozza, come le figlie).

Regressione con `prova_changeset.py --pgtap`, senza e con l'estratto, su 118 file che nominano il vocabolario fiscale,
il lotto, il BB della nascita o gli oggetti toccati: tutti uguali o migliori. I rossi rimasti sono di prima:
`script/test-vw-giornale-entita` si interrompe senza e con l'estratto su un dato che lo scratch non ha (passa dalla
madre e non nomina lo stato del lotto); i test di perimetro RLS sono rossi da owner per costruzione. I pgTAP li lancia
Tid.

**Esito (Tid, 2026-11-13):** giro 1 applicato su dbdev, pgTAP del §6.3 verdi.

### 6.4 Trovati dal giro 1 — decisi da Tid (2026-11-13)

Decise da Tid il 2026-11-13, tutte e tre come proposte dal DB (per R-2 il ritiro, non il mantenimento).

* **R-1 — L'emissione fiscale di S-3: revocata.** S-3 proponeva `emissione` su `config.stati_doc_fiscale`, per il
  cancello IVA del guard della fattura. Il 2026-10-25 (`20261025-37`, brief-modello-documento-vendita §8) la colonna era
  nata **solo** sui cinque documenti che passano da «Emetti», e la fattura ne era stata esclusa apposta: «la pipeline
  non emette, il lettore risponde NULL». Il backend legge `script.fn_stato_emissione_id` per rifiutare l'emissione sul
  cambio stato generico: dare la colonna alla fattura cambierebbe anche quella risposta. **Deciso:** per il fiscale
  niente colonna `emissione`; il cancello IVA nomina EMESSA, ed è l'**unico** punto del fiscale che nomina un codice.
  Non è un debito: è un'eccezione voluta, tenuta a un punto solo dal test 8 di
  `test-stato-fiscale-dal-vocabolario-v1` (frase aggiornata il 2026-11-13). Se un giorno un secondo lettore vorrà
  sapere «da qui la fattura è emessa», serve una colonna col suo nome, non quella di «Emetti».
* **R-2 — `in_gioco` senza un caso suo: si ritira.** `vendite.vw_lotti_fase` ha due flag, `pre_fiscale` e `in_gioco`,
  e l'unico caso in cui dissentivano era il lotto senza stato (il test 8 di `test-vw-lotti-fase-v1`: «è tutta la
  ragione per cui sono due flag»). Con S-6 quel caso non esiste più: `in_gioco` è una copia di `pre_fiscale`, e una
  copia si ritira nello stesso cantiere. Lettori, censiti sul catalogo di dbdev e nel codice il 2026-11-13:

  | Lato | Lettore | Cosa cambia |
  | --- | --- | --- |
  | DB | `vendite.vw_dash_competenza_attivita` (`lfase.in_gioco`, motivo GIRO_IN_CORSO) | legge `pre_fiscale` |
  | DB | `vendite.vw_documenti_trattenuti_da_lotto` (`f.in_gioco`) | legge `pre_fiscale` |
  | DB | `script.fn_check_attivita_riportabile_da_emettere` (`f.in_gioco AS marchio_in_gioco`) | legge `pre_fiscale` |
  | BE | `backend/apps/vendite/tests/db/test_riepilogo_esclude_trattenuti.py` (righe 119-225: `SELECT in_gioco FROM vendite.vw_lotti_fase`, il metodo `_crea_lotto_in_gioco` e i commenti) | legge `pre_fiscale` |
  | FE | nessuno | — |

  **Chi cambia per primo:** il BE (riga 11 della testata), perché `pre_fiscale` c'è già e vale quanto `in_gioco`: il test
  passa prima e dopo. Poi il DB, nel giro 5: i tre lettori passano a `pre_fiscale` e la colonna esce dalla vista (che va
  ricreata con le sue dipendenti), insieme alle pagine `vw_lotti_fase`, `vw_documenti_trattenuti_da_lotto`,
  `vw_dash_competenza_attivita` e `fn_check_attivita_riportabile_da_emettere`, e ai pgTAP che la nominano
  (`test-vw-lotti-fase-v1`, `test-documento-trattenuto-da-lotto-v1`, `test-motivo-non-fatturata-v1`). Se il BE non ha
  ancora fatto la sua parte, il DB porta i tre lettori e lascia la colonna.
* **R-3 — REGISTRATA e il lotto: il lotto non diventa REGISTRATO.** REGISTRATA ha `applica_lotto` = true, ma nessuna riga
  della matrice porta un lotto in REGISTRATA (INVIATA → REGISTRATA è solo della fattura): la registrazione è un fatto
  della singola fattura. **Deciso:** `applica_lotto` = false su REGISTRATA, dal CSV, nel giro 4, insieme al presidio
  della raggiungibilità di ⑤, che altrimenti la segnalerebbe sull'asse del lotto. Così il vocabolario dice la stessa
  cosa della matrice.

Minori, da chiudere quando si riaprono gli oggetti: il BB della nascita, sul lotto, nomina la tabella
(`fatturazione_lotti`) nella frase del rifiuto, perché il lotto non è in `config.sorgenti` (come la versione di
listino; lo raggiunge solo un `INSERT` diretto, la madre non passa lo stato); il commento nel corpo di
`dbops.fn_pgtap_crea_lotto` dice ancora che lo stato DRAFT lo decide la madre.

### 6.5 Giro 2 — l'offerta (2026-11-13)

Il via di Tid è del 2026-11-13; il range `20261112-59 … -64` l'ha dato Tid, con una seconda sessione DB attiva.

| ChangeSet | Che cosa |
| --- | --- |
| `00_schema/config/20261112-59` | la colonna `rifiuto` su `config.stati_doc_offerte` e `config.stati_doc_preventivi` (S-3): `NOT NULL DEFAULT false`, `chk_<vocabolario>_rifiuto_attivo`, `uq_<vocabolario>_rifiuto`, come `accettazione` |
| `80_data`, due CSV e due mirror | `stati_doc_offerte.csv` e `stati_doc_preventivi.csv`: colonna `rifiuto` in coda, vera su RIFIUTATA e RIFIUTATO; `- column: rifiuto` nei mirror `20260524-04` e `20250917-01` (`runOnChange` + `ANY`, §11.2) |
| `20_code/script/20261112-60` | `script.fn_stato_rifiuto_id(regclass)`, gemello di `fn_stato_accettazione_id` sul lettore comune (S-3). Nel DB non ha consumatori: il guard ha già la riga del vocabolario. Lo legge il BE (§6.7) |
| `20_code/vendite/20261112-61` | ③: `vendite.trgfn_offerte_commerciali_guard_transizione` legge le colonne. L'emissione è `iniziale` → `emissione`; i prezzi vanno verso `emissione` o `accettazione`; l'annullo verso `is_abortito`; le date dalla colonna della destinazione (`rifiuto` → `data_rifiuto`) |
| `20_code/script/20261112-62` | S-2 e S-10 per la capability: `script.fn_available_actions_offerta` legge «in bozza» da `iniziale` (i motivi delle righe dell'emissione, `can_edit_eccezioni`) ed espone la chiave nuova `stato_terminale`. Firma ancorata con `%TYPE`; il COMMENT, che era una cronaca, è riscritto al presente |
| `20_code/vendite/20261112-63` | S-2 per il cruscotto: `vendite.vw_dash_fatturazione_offerte` dà `DOC_BOZZA` da `iniziale` e `IN_ATTESA_ACCETTAZIONE` da `emissione`. Le colonne sono le stesse; `security_invoker` si ripete, perché un `CREATE OR REPLACE VIEW` senza opzioni le azzera |
| `20_code/dbops/20261112-64` | il builder `dbops.fn_pgtap_crea_offerta` (§4.2). Compone `fn_pgtap_cliente_del_builder` e `fn_pgtap_crea_listino`, fa nascere la testata come il backend (con l'indirizzo di default da `vendite.fn_doc_indirizzo_default`) e porta allo stato con `fn_pgtap_porta_a_stato` |

**Trovato riaprendo la famiglia dell'offerta** (non era nel censimento del §4.2): la vista
`vendite.vw_dash_fatturazione_offerte` nominava `'BOZZA'` ed `'EMESSA'` per il motivo del fermo. È entrata in questo
giro, perché S-2 prende la famiglia un documento per volta. Gli altri letterali che il censimento del 2026-11-13 ha
trovato non sono stati dell'offerta: `'RIFIUTATA'` delle commesse è l'approvazione delle attività, e
`'ANNULLATA'` di `vendite.fn_documento_lineage_legami` è lo stato di emissione di un'attività. I due `v_stato_cod`
che restano nella capability vanno ai building block del lucchetto (`fn_doc_testata_in_stato`,
`fn_doc_riga_modificabile`), che ragionano per codice nel loro montaggio: non sono una copia del significato.
⚠️ **Smentito il 2026-11-14 (§6.10, V-2):** il montaggio scrive la bozza con un codice (`stato_bozza`), e con
`iniziale` spostata il lock e la capability si separano. È il difetto ⑨, e la decisione è D-LOCK.

Corpi presi da `pg_get_functiondef` e `pg_get_viewdef` su dbdev il 2026-11-13. Ogni changeSet porta nel rollback la
definizione e il COMMENT di prima, letti dal catalogo e non ricopiati a mano. Con il vocabolario del seed ogni
passaggio ha l'esito di prima: cambia solo da dove si legge il significato. I codici d'errore, i loro parametri e il
montaggio del trigger restano gli stessi.

Pagine `manual/` scritte o riscritte: `config/stati_doc_offerte`, `config/stati_doc_preventivi`,
`script/fn_stato_rifiuto_id` (nuova), `script/fn_stato_per_colonna_id`, `script/fn_available_actions_offerta`,
`vendite/trgfn_offerte_commerciali_guard_transizione` (riscritta: descriveva ancora la versione di listino fissata
dal backend), `vendite/vw_dash_fatturazione_offerte`, `dbops/fn_pgtap_crea_offerta` (nuova); guida
`modello-documento-di-vendita` (il lettore del rifiuto). La doc auto-generata non è rigenerata.

### 6.6 La prova e i pgTAP del giro 2

* **Nuovo** `vendite/test-offerta-guard-dal-vocabolario-v1` (plan 12). Prova il builder, le date dal significato, il
  lettore del rifiuto sui tre casi, l'indice unico, `stato_terminale`, e due **marche spostate** in transazione,
  ognuna col suo contrasto. Con l'accettazione su RIFIUTATA, lo stesso passaggio scrive `data_accettazione`. Con
  l'iniziale su EMESSA, l'offerta emessa ha `can_edit_eccezioni` e il motivo `DOC_BOZZA`. Il test 12 è il presidio
  sulla forma: guard, capability e vista non nominano i codici dell'offerta. Il builder per ora non ha un test suo
  come i fratelli: lo provano i test 1-3.
* **Adeguato** `vendite/test-indirizzi-documento-seguono-cliente-v1`, test 3. È il censimento dei chiamanti di
  `vendite.fn_doc_indirizzo_default`, e il builder nuovo è un chiamante voluto, perché fa nascere l'offerta come il
  backend.

**Prova (scratch `zeroerp_ruoli`, 2026-11-13).** Il guardrail delle forme, del COMMENT al presente, dei letterali,
del `runOnChange` e del preambolo pgTAP è verde. L'estratto dei sei changeSet gira per intero in `ROLLBACK` e il
catalogo resta identico.

⚠️ **Il mirror è simulato.** `prova_changeset.py` non esegue i `loadUpdateData`, quindi i valori di `rifiuto` li ha
scritti un changeSet di sola prova nello scratchpad (un `UPDATE` per vocabolario), che non entra nel repo. Il
caricatore vero lo prova l'apply.

**Regressione** con `--pgtap`, senza e con l'estratto, sui 104 file che nominano gli oggetti toccati (i due
vocabolari, il guard, la capability, le due viste del cruscotto, i lettori degli stati):

* 103 uguali;
* uno peggiore, `test-indirizzi-documento-seguono-cliente-v1` (il chiamante nuovo), adeguato e poi verde con
  l'estratto (18/18). Senza l'estratto ora è rosso: chiede un builder che prima dell'apply non c'è;
* il test nuovo: 12/12 con l'estratto, interrotto senza (il builder non c'è).

Rossi uguali senza e con l'estratto, quindi già presenti: `test-ordine-al-modello-v1` (1) e
`test-refactor-qta-operativa-preventivi-v1` (5). I pgTAP li lancia Tid.

**Esito (Tid, 2026-11-13):** giro 2 applicato su dbdev, mirror compresi; pgTAP verdi.

### 6.7 Richieste al team BE/FE del giro 2 (elenco chiuso)

**Chi cambia per primo: il DB.** Le colonne e la chiave nuova devono esserci prima che BE e FE le leggano. Finché il
BE/FE non cambia, il comportamento resta quello di oggi: la chiave nuova la ignora chi non la legge.

| Lato | File | Che cosa |
| --- | --- | --- |
| BE | `backend/apps/core/db/documento_modello_repository.py` | il lettore `_LETTORE_RIFIUTO = "script.fn_stato_rifiuto_id"` e il metodo `stato_di_rifiuto(testata)`, gemelli di `stato_di_accettazione` |
| BE | `backend/apps/core/services/documento_modello.py` | `stato_di_rifiuto(testata, *, function_name)`, gemello di `stato_di_accettazione` |
| BE | `backend/apps/vendite/services/offerte_service.py` | `registra_rifiuto` sceglie lo stato con `stato_di_rifiuto(TESTATA_OFFERTE, …)` invece di `StatoOfferta.RIFIUTATA`, come `registra_accettazione`. `RIFIUTATA` resta come **parola dell'API** in `_ESITI`, come oggi `ACCETTATA` |
| FE | `frontend/src/vendite/offerte/components/OffertaDrawer.vue` | `isStatoTerminale` legge `capabilities.stato_terminale` invece di `STATI_OFFERTA_TERMINALI` |
| FE | `frontend/src/vendite/offerte/constants.js` | ritira `STATI_OFFERTA_TERMINALI` e il suo commento |

Non serve altro nel BE perché la capability viaggia intera sotto `capabilities` (`offerte_service.get_offerta`).

⚠️ **Fuori da questo elenco: D-SCAD, la scadenza dell'offerta.** ✅ Decisa da Tid il 2026-11-13: (a). Sviluppo al
§6.8. Trovata scrivendo S-10, verificata
sul catalogo il 2026-11-13. La regola «quest'offerta è scaduta» oggi sta in due metà:

* il DB, in `vendite.vw_offerte_commerciali_lista.is_scaduta`, dice solo «`validita_al` è passata
  (`script.fn_data_operativa`)», in **qualunque** stato;
* il FE la completa con `STATI_OFFERTA_SEGNALA_SCADENZA` (`BOZZA`, `EMESSA`), in **due** punti:
  `OfferteSearchTable.vue` (il badge della lista) e `OffertaDrawer.vue` (il badge del dettaglio). Un'offerta accettata,
  rifiutata o annullata con la validità passata non è «scaduta» per l'operatore.

È una regola di dominio scritta per metà nel frontend, ed è lavoro **DB**: la regola intera va nella vista, e il FE
legge il flag e ritira la costante. Il seed della lista ha anche la colonna configurabile «Scaduta» su `is_scaduta`
(`ui.lista_colonna` id 92), che oggi dice «sì» anche su un'offerta accettata: con la regola intera direbbe la stessa
cosa del badge.

**Che cosa vuol dire «gli stati in cui la scadenza conta».** Sul modello sono gli stati in cui il cliente non ha
ancora risposto: la bozza e l'offerta emessa. Due modi di dirlo dal vocabolario, e decide Tid:

* **(a) proposta DB: `esito IS NULL`**, cioè nessun verdetto ancora. È la domanda giusta («il cliente ha già
  risposto?») e regge uno stato futuro di attesa senza toccare la regola. Contro: `esito` nasce come proiezione per il
  motore pratiche, e qui gli si dà un secondo lettore;
* **(b) `iniziale OR emissione`**: due colonne che ci sono già, ma descrive gli stati di oggi, non la domanda. Uno
  stato nuovo di attesa andrebbe aggiunto alla regola.

Il giro, se Tid lo apre: un changeSet sulla vista (la stessa colonna, con il suo significato intero, e il COMMENT),
il pgTAP con la marca spostata, e una richiesta FE (due file). Il preventivo non ha questo problema: lì la scadenza
è uno stato (`scadenza`, scritto dal job).

### 6.8 D-SCAD — la scadenza dell'offerta (2026-11-13)

**Decisione (Tid, 2026-11-13): (a)**, `esito IS NULL`. Numero dato da Tid: `20261112-65`.

✅ **Applicato da Tid il 2026-11-13**, con il pgTAP `test-offerta-guard-dal-vocabolario-v1` (plan 15) verde; la pagina
generata della vista è rigenerata.

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/vendite/20261112-65` | `vendite.vw_offerte_commerciali_lista.is_scaduta` = `esito IS NULL` **e** la validità passata (`script.fn_data_operativa`, come prima). Stesse colonne, `security_invoker` ripetuto; il COMMENT della vista, una cronaca, è riscritto al presente; `is_scaduta` prende il suo COMMENT di colonna |

`esito` prende un secondo lettore, per la stessa domanda («il cliente ha già risposto?»): scritto nella pagina
`config/stati_doc_offerte`. Pagina `vendite/vw_offerte_commerciali_lista` riscritta sulla regola intera.

**pgTAP.** `vendite/test-offerta-guard-dal-vocabolario-v1` passa da plan 12 a plan 15:

* 13: l'emessa con la validità passata è scaduta;
* 14: la rifiutata con la validità passata non lo è;
* 15: con la marca spostata (un esito sullo stato EMESSA), l'emessa non è più scaduta.

**Prova (scratch, 2026-11-13).** I guardrail sono verdi. L'estratto gira per intero in `ROLLBACK` e il catalogo resta
identico. La regressione, senza e con l'estratto, sui 9 pgTAP che leggono la vista più quello esteso:

* 9 uguali;
* il test esteso: 13 ok / 2 not ok senza l'estratto, 15 ok con. I due rossi senza sono i test 14 e 15, cioè il
  difetto: la regola di prima dice «scaduta» anche a un'offerta rifiutata.

**Trovato:** il badge «Scaduta» del **dettaglio** (`OffertaDrawer.vue`) non si accende mai. Legge
`detail.is_scaduta`, che il dettaglio non porta: `offerte_service.get_offerta` legge la sua proiezione
(`_SELECT_COLS_OFFERTA`), non la vista.

**Richieste al team BE/FE (elenco chiuso).** Chi cambia per primo: il DB. Fino al passo FE la lista mostra il badge
come oggi, perché il filtro FE e la regola nuova dicono la stessa cosa sugli stati di oggi.

| Lato | File | Che cosa |
| --- | --- | --- |
| BE | `backend/apps/vendite/db/offerte_repository.py` | il dettaglio porta `is_scaduta` letto da `vendite.vw_offerte_commerciali_lista` (la sede della regola), non ricalcolato |
| FE | `frontend/src/vendite/offerte/components/OfferteSearchTable.vue` | il badge legge `data.is_scaduta` da solo, senza `STATI_OFFERTA_SEGNALA_SCADENZA` |
| FE | `frontend/src/vendite/offerte/components/OffertaDrawer.vue` | il badge legge `detail.is_scaduta` da solo |
| FE | `frontend/src/vendite/offerte/constants.js` | ritira `STATI_OFFERTA_SEGNALA_SCADENZA` e il commento in testa che la giustifica |


### 6.9 Trovati dalla verifica BE/FE dei giri 2 e D-SCAD (2026-11-14) — richieste al team DB

Le richieste del §6.7 e del §6.8 sono fatte sul branch `dev/backend-tid` (non committate al 2026-11-14), con i test
sul DB vero verdi. La verifica ha trovato due punti che si chiudono **solo nel DB**. Il BE/FE non mette un ripiego
nell'attesa.

* **V-1. `is_scaduta` del dettaglio costa la vista intera.** Il dettaglio legge il flag con una sottoquery
  correlata su `vendite.vw_offerte_commerciali_lista` (`_SELECT_COLS_OFFERTA`). Il piano su dbdev (2026-11-14,
  `EXPLAIN`) mostra che, per un solo booleano, la vista esegue la `LATERAL pratiche.fn_pratica_del_documento`, la
  sottoquery di `config.sorgenti` e rifà la RLS dell'offerta: il planner non scarta una funzione in `LATERAL`. Il
  risultato è giusto, ma il costo del dettaglio dipende da colonne che non legge. **Richiesta:** la regola ha una
  sede che si legge da sola, per esempio `vendite.fn_offerta_scaduta(offerta_id)` (o la chiave nella capability
  `fn_available_actions_offerta`), e la vista la compone. Il BE allora la legge da lì, in un solo punto.
* **V-2. «In bozza» nel drawer è ancora un codice.** `OffertaDrawer.vue` decide il lucchetto di corpo
  (`isWorkflowLocked`) con `stato !== STATO_OFFERTA.BOZZA`. È la stessa domanda che la capability ora legge da
  `iniziale` (S-2), e che il FE non può chiedere, perché la capability espone `stato_terminale` ma non «stato
  iniziale». Il commento del drawer dice che il lucchetto «sullo stato» è lo stesso nei cinque drawer gemelli
  (righe, utility, indirizzi). **Richiesta:** la chiave `stato_iniziale` (colonna `iniziale` del vocabolario)
  accanto a `stato_terminale`, nella capability dell'offerta e, giro per giro, in quelle degli altri documenti. Poi
  una richiesta FE: il lucchetto legge la chiave e non il codice.

Fuori dal DB, lato BE: il permesso della rotta `registra-esito` (`PassaggioDocumento`, campo `esito`) cercava la riga
della matrice con la **parola dell'API** (`ACCETTATA` / `RIFIUTATA`), mentre il verbo scrive lo stato del vocabolario
(`accettazione` / `rifiuto`). ✅ **Deciso da Tid il 2026-11-14 (opzione A) e fatto**: `PassaggioDocumento` prende
`stato_del_campo`, la mappa parola → ruolo (`offerte_service.RUOLO_DEGLI_ESITI`, la stessa del routing del service),
e cerca la riga verso lo stato del ruolo letto dal vocabolario. L'API non cambia. Presidi:
`core/tests/api/test_permesso_passaggio.py` (15-18) e `core/tests/test_passaggio_rotte.py` (8, sul DB vero).

⚠️ **Risposta del team DB: §6.10** (2026-11-14). V-1 è scritto; per V-2 la chiave chiesta non serve, e la
verifica ha trovato un difetto del lock (⑨, decisione D-LOCK).

### 6.10 Giro 2-bis — V-1 e V-2 (team DB, 2026-11-14)

Col via di Tid (2026-11-14, «procedi come da proposte»). **V-1 è applicato e verde (Tid, 2026-11-14); V-2 si ferma su
una decisione (D-LOCK).**

#### V-1 — la regola della scadenza ha una sede sua

**Il percorso, censito (2026-11-14).** Lato DB l'unico lettore della regola è la vista della lista: le altre funzioni
dell'offerta che nominano `validita_al` la ricopiano (revisione, contratto), ma non giudicano se è scaduta. Lato BE il
dettaglio (`offerte_repository._SELECT_COLS_OFFERTA`) la legge con una sottoquery sulla vista. Lato FE il drawer e la
lista leggono già il solo flag (§6.8). Il dettaglio è il secondo consumatore: la regola si estrae (regola del 2).

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/vendite/20261113-38` | **nuova** `vendite.fn_offerta_scaduta(p_esito, p_validita_al, p_data_riferimento)`: `esito IS NULL` e la validità passata. Riceve i valori e non l'id (linee-guida-sql §13.8): pura, `IMMUTABLE`, `LANGUAGE sql`, si incorpora. **Non** `STRICT`: l'esito vuoto è il caso normale. La data è un argomento, perché una sottoquery nel corpo impedirebbe l'incorporazione; chi chiama passa `script.fn_data_operativa()` |
| `20_code/vendite/20261113-39` | `vendite.vw_offerte_commerciali_lista.is_scaduta` = `vendite.fn_offerta_scaduta(sdo.esito, o.validita_al, (SELECT script.fn_data_operativa()))`. Stesse colonne, `security_invoker` ripetuto, i due COMMENT rimandano alla funzione. Rollback: il `20261112-65`, verificato uguale al vivo |

Non c'è una chiave nella capability. `is_scaduta` è un fatto del record, non un'azione. Se la capability si rompe, il
dettaglio arriva con il blob vuoto (`capabilities_o_vuoto`): il badge sparirebbe insieme alle azioni.

**La prova (2026-11-14).** `scripts/prova_changeset.py` sui due changeSet, con il pgTAP in coda: **18 ok / 0 not ok**;
catalogo identico dopo il `ROLLBACK`. Piano su dbdev come app (funzione in `pg_temp`, transazione annullata): la
funzione si incorpora, e la data operativa resta una `InitPlan`, calcolata una volta. Equivalenza con la vista viva su
dbdev: nessuna differenza. È un fatto datato e non prova la regola: la regola la provano i test 13-16, che i casi li
costruiscono.

**pgTAP.** `vendite/test-offerta-guard-dal-vocabolario-v1` passa da plan 15 a plan 18:

* 16: la funzione sui valori: scaduta senza esito e con la validità passata; non con un esito, senza validità, o con
  la validità che scade oggi;
* 17: `IMMUTABLE` e non `STRICT`;
* 18: forma: la vista compone la funzione e non riscrive la regola (presidio sulla **forma**, dichiarato tale).

**Pagine `manual/`.** `vendite/fn_offerta_scaduta` (nuova), `vendite/vw_offerte_commerciali_lista` (la sezione di
`is_scaduta`, e la nota operativa «`is_scaduta` è grezzo», ferma a prima di D-SCAD), `config/stati_doc_offerte`. La doc
auto-generata non è rigenerata.

**Richiesta al team BE (elenco chiuso), dopo l'apply di `-38` e `-39`:**

| # | File | Che cosa |
| --- | --- | --- |
| BE-V1 | `backend/apps/vendite/db/offerte_repository.py` | in `_SELECT_COLS_OFFERTA` la sottoquery su `vendite.vw_offerte_commerciali_lista` diventa `vendite.fn_offerta_scaduta(sd.esito, o.validita_al, script.fn_data_operativa()) AS is_scaduta` (`sd` è già `config.stati_doc_offerte`); il commento in testa alla proiezione (righe 144-147) e quello sopra la colonna rimandano alla funzione, non alla vista |
| BE-V1b | `docs/it/backend/vendite/manual/api_offerte.md` | se cita la vista come sede di `is_scaduta` del dettaglio, la sede è la funzione |

Il contratto dell'API non cambia; il FE non ha niente da fare.

#### V-2 — il lucchetto del corpo: la domanda c'è già, ma ha due risposte

**La domanda del FE è «il corpo si modifica?», non «lo stato è l'iniziale?».** Per l'offerta la capability la risponde
già, sezione per sezione: `can_edit_eccezioni` (le righe dell'offerta sono `vendite.offerte_commerciali_eccezioni`),
`can_edit_utility`, `can_edit_indirizzi`, e `non_editable_fields` per la testata. Una chiave `stato_iniziale`, o una
`can_edit_righe` come quella di ordine e DDT, darebbe un secondo nome alla risposta che `can_edit_eccezioni` dà già.
⚠️ Questo **corregge la proposta del DB** fatta in chat il 2026-11-14 (`can_edit_righe`), e la richiesta V-2 del §6.9
(`stato_iniziale`).

**Il difetto trovato (⑨, nuovo: non è nel censimento del §4).** Le chiavi della capability e il trigger che ferma la
riga rispondono da due sedi diverse:

* `can_edit_eccezioni` = la colonna `iniziale` dello stato (giro 2, `20261112-62`);
* `can_edit_utility` e `can_edit_indirizzi` = `script.fn_doc_riga_modificabile`, che legge il montaggio del lock;
* il lock (`vendite.trgfn_doc_righe_lock_fuori_bozza`, `vendite.trgfn_doc_testata_lock_fuori_bozza`) riconosce la
  bozza dal **codice** scritto negli argomenti del trigger: la regola di `script.fn_doc_lock_regola` porta
  `stato_bozza = 'BOZZA'`, e `script.fn_doc_lock_colonna_bloccata` confronta `p_stato = stato_bozza`.

Con il vocabolario del seed le tre risposte coincidono. Con la marca spostata (test 10: `iniziale` su EMESSA) si
separano: la capability dice «modificabile» su un'offerta emessa, e il trigger rifiuta la riga. È la «terza via» di
linee-guida-sql §12.1: un'azione proposta che il guard rifiuta. Sul modello il caso esiste: `iniziale` è una colonna
del vocabolario, e il vocabolario si cambia.

⚠️ **Revoca un giudizio del giro 2.** Il §6.5 (2026-11-13) diceva che i building block del lucchetto «ragionano per codice
nel loro montaggio: non sono una copia del significato». Lo sono: `stato_bozza` dice lo stesso significato della colonna
`iniziale`, con un codice. Era un giudizio del team DB, non una decisione di Tid.

**Il perimetro (struttura, letta da `pg_trigger` su dbdev il 2026-11-14):** il lock è montato su **tutti e sette i
documenti di vendita**: offerta (`BOZZA`); preventivo, ordine, contratto, DDT, reso (`DRAFT`). Sono 28 tabelle tra
testate, righe, componenti, indirizzi e satelliti. È un tema di famiglia: tocca il fermo dei temi trasversali sui
documenti di vendita (PROJECT_CONTEXT), ed è ammesso perché poggia sul vocabolario, come il resto del brief.

**D-LOCK — da decidere (Tid).**

* **(a) Proposta DB.** Il building block del lock riconosce la bozza dalla colonna `iniziale` del vocabolario del
  documento, non dall'argomento `stato_bozza`. Il vocabolario si trova dal documento, come fa
  `script.fn_doc_stato_iniziale_id`. Poi la capability legge il lock in ogni sezione: `can_edit_eccezioni` da
  `script.fn_doc_riga_modificabile`, come utility e indirizzi, e la sede resta una. È un giro a sé, sui sette
  documenti. Va dentro S-2, che ha già preso la famiglia (Tid, 2026-11-08). ⚠️ Gli argomenti dei trigger non si toccano
  (linee-guida-sql §11.5, se il montaggio nasce da `ci_apply`): `stato_bozza` si ritira dalla **lettura**, e il suo
  ritiro dal montaggio è un passo che va censito a parte.
* **(b)** Solo la capability, subito: `can_edit_eccezioni` legge il lock (specchia il guard, §12.2 punto 1), e il lock
  resta sul codice fino al giro di (a). Il test 10 cambia significato: con `iniziale` spostata, la riga resta chiusa
  come il trigger. Chiude la divergenza capability/trigger sull'offerta, ma lascia il significato scritto per codice
  in 28 montaggi.

**La richiesta al FE non aspetta D-LOCK.** Le chiavi ci sono già, e la loro sede si corregge sotto, senza che il FE
cambi di nuovo:

| # | File | Che cosa |
| --- | --- | --- |
| FE-V2 | `frontend/src/vendite/offerte/components/OffertaDrawer.vue` | `isWorkflowLocked` non confronta `stato` con `STATO_OFFERTA.BOZZA`: ogni sezione si chiude dalla sua chiave della capability (`can_edit_eccezioni` per le righe, `can_edit_utility`, `can_edit_indirizzi`; la testata ha già `non_editable_fields`). Con la capability vuota il corpo resta chiuso (fail-closed, come `useTestataDocumento`). Il banner `banner_locked_post_bozza` si accende quando una sezione è chiusa |
| FE-V2b | i drawer gemelli che il commento del drawer nomina (righe, utility, indirizzi) | lo stesso, ciascuno con la chiave della sua sezione |

⚠️ `STATO_OFFERTA.BOZZA` può avere altri lettori nel FE: il censimento lo fa il team FE.

### 6.11 D-LOCK (a) — il lock riconosce la bozza dal vocabolario (team DB, 2026-11-14)

**Decisione (Tid, 2026-11-14): (a).** Questa sezione chiude anche V-2 dal lato DB.

**La correzione sta in un punto solo.** Tutti i lettori del lock passano da una sola grammatica,
`script.fn_doc_lock_regola`: i due trigger, `script.fn_doc_lock_montaggi`, e da lì `fn_doc_riga_modificabile`,
`fn_doc_colonna_modificabile`, `fn_doc_testata_in_stato` e le capability dei sette documenti. La regola calcola
`stato_bozza` dal vocabolario del documento, e tutti la seguono senza cambiare. L'argomento dello stato bozza resta
nella grammatica, nella sua posizione, e non si legge: i 28 montaggi restano com'erano. Con il seed lo stato iniziale di
ogni vocabolario è il codice che il montaggio scrive (preventivi, contratti, ordini, DDT, reso `DRAFT`; offerte `BOZZA`;
dbdev, 2026-11-14), quindi il comportamento di oggi non cambia.

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/script/20261113-40` | `script.fn_doc_lock_regola`: `stato_bozza` = il codice dello stato iniziale (tipo documento → `config.sorgenti.target_table` → `script.fn_doc_stato_modello` → `script.fn_stato_iniziale_id`). Un tipo documento che non porta a uno stato iniziale è un montaggio sbagliato (`errore`, sollevato dal chiamante con `E_DOC_RIGHE_LOCK_MONTAGGIO`). COMMENT riscritto al presente |
| `20_code/script/20261113-41` | `script.fn_available_actions_offerta`: `can_edit_eccezioni` = `script.fn_doc_riga_modificabile('vendite.offerte_commerciali_eccezioni', stato)`, come utility e indirizzi |

Fuori dal difetto: `vendite.trgfn_doc_guard_delete_solo_bozza` legge già lo stato iniziale dal vocabolario. Solo la mail
(`config.email_outbox`) dice `DRAFT`, perché non ha un vocabolario.

**La prova (2026-11-14).** `scripts/prova_changeset.py` sui due changeSet, con ognuno dei **48** pgTAP che nominano il
lock o la capability dell'offerta. Tre fissavano il contratto vecchio e sono stati riportati al modello:

| pgTAP | Che cosa cambia |
| --- | --- |
| `vendite/test-trgfn-doc-righe-lock-fuori-bozza-v1` (21) | provava «lo stato bozza è parametrico» (`TG_ARGV[2]` = EMESSO). Ora prova il contrario: l'argomento non si legge, e la riga passa sul DDT in bozza e non su quello emesso. Rosso senza l'estratto, verde con |
| `vendite/test-doc-emittente-utility-fermi-v1` (1-3) | la grammatica con un tipo documento finto (`'X'`). Ora usa `PREVENTIVO`, e la decisione «in bozza» si chiede con lo `stato_bozza` della regola |
| `vendite/test-testata-dopo-emissione-rdb-v1` (1) | il tipo documento finto `'DDT'` diventa `DDT_VENDITA` |

Esito con l'estratto: tutti verdi, tranne `vendite/test-esecutivi-ba-coppia-v1`, con un rosso che c'era già senza
l'estratto (fuori da questo cantiere). Catalogo identico dopo ogni `ROLLBACK`.

**pgTAP nuovi.** `vendite/test-offerta-guard-dal-vocabolario-v1` passa da plan 18 a plan 23. Senza l'estratto 4 test
sono rossi, con l'estratto 23 su 23:

* 19: contrasto. Con lo stato iniziale su BOZZA, l'indirizzo dell'offerta emessa non si toglie
  (`E_DOC_DATI_COLLEGATI_NON_BOZZA`), e la capability lo dice;
* 20: ⭐ marca spostata. Con `iniziale` su EMESSA il lock legge EMESSA come bozza;
* 21: … l'indirizzo dell'offerta in BOZZA non si toglie più;
* 22: … quello dell'offerta emessa sì, e la capability lo proponeva;
* 23: … ed è tolto davvero.

**Pagine `manual/`.** `script/fn_doc_lock_regola`, `vendite/trgfn_doc_righe_lock_fuori_bozza`,
`vendite/trgfn_doc_testata_lock_fuori_bozza`, `script/fn_available_actions_offerta`.

**Debito residuo, dichiarato.** I 28 montaggi portano ancora l'argomento dello stato bozza, che non si legge. Toglierlo
vuol dire cambiare la grammatica (per la testata è un argomento posizionale obbligatorio) e rimontare 28 trigger. Non è
una seconda verità, perché nessuno lo legge, ma è rumore nel montaggio. Si toglie quando un giro rimonta quei trigger per
un'altra ragione; nel frattempo la pagina di `fn_doc_lock_regola` dice che non si legge.

**Ricadute BE/FE.** Nessuna nuova: il contratto della capability non cambia, e FE-V2 (§6.10) vale com'è.

### 6.12 Giro 3 — `terminale`, bolla e reso (team DB, 2026-11-14)

Col via di Tid (2026-11-14, «procedi anche con tutti gli altri giri»). Chiude ④, ⑦, S-4, S-5 e S-3 per il reso.

| ChangeSet | Che cosa |
| --- | --- |
| `00_schema/config/20261113-42` | ⑦ e S-3: `esito` (FK verso `config.esiti_flussi_pratiche`) e `terminale` (CHECK verso `fase` CHIUSO) su `config.stati_doc_ddt` e `config.stati_doc_reso`; `emissione` su `config.stati_doc_reso` (indice unico parziale, CHECK attivo). COMMENT al presente |
| `00_schema/config/20261113-43` | ④ a: il COMMENT di `terminale` su offerte, ordini, preventivi, contratti, versioni di listino: nessun passaggio **a mano** in uscita (S-1, A), implicazione e non equivalenza (S-4) |
| `20_code/config/20261113-44` | il guard del verdetto (`config.trgfn_stati_doc_guard_esito_verdetto`) montato su bolla e reso |
| `20_code/script/20261113-45` | **nuova** `script.fn_doc_terminali_con_uscita_manuale(testata)`: le coppie (stato terminale, destinazione a mano) della configurazione |
| `20_code/script/20261113-46` | ④ b: **nuovo** building block `script.trgfn_doc_terminale_senza_uscita_manuale`, `CONSTRAINT TRIGGER` differito su sette vocabolari e sette matrici (14 montaggi, la testata come argomento); codice nuovo `E_DOC_TERMINALE_CON_USCITA_MANUALE` |
| `20_code/vendite/20261113-47` | ⑦: `vendite.vw_stato_sorgente_ddt` e `_reso` passano `esito` e `terminale` del vocabolario, non li calcolano da `fase` |
| `20_code/vendite/20261113-48` | S-3: `vendite.trgfn_resi_gen_numero` numera nello stato di `emissione`, non nel codice CONFERMATO |
| `20_code/script/20261113-49` | S-3, e la gemella della bolla trovata al §5: `script.vw_stati_doc_reso_merce_rientrata` e `script.vw_stati_doc_ddt_merce_partita` contano dallo stato di `emissione`, non da `'CONFERMATO'` ed `'EMESSO'` |
| `80_data/changelog/20261113-50` | il mirror della bolla ri-applicato dopo il seed degli esiti (`20260701-04`): `esito` ha una FK, e il mirror del `20250915-01` lo salta (`type: SKIP`). linee-guida-sql §11.2 |

**I dati (80_data).** CSV `stati_doc_ddt` (`esito`, `terminale`) e `stati_doc_reso` (`esito`, `terminale`, `emissione`), con
le colonne dichiarate nei due mirror. Sono i valori che la vista calcolava, tranne **S-5**: il reso CONFERMATO ha
`terminale` = false, `esito` POSITIVO, `fase` CHIUSO, ed è lo stato di `emissione`. Il codice nuovo è in coda a
`codici_errore.csv` e `messaggi_errore.csv` (id 1483). I CSV sono riscritti con `csv.writer` e `\n`: nessun CR.

**Il seed rispetta A** (dbdev, 2026-11-14, sulla configurazione): nessuno stato terminale ha un passaggio a mano in
uscita, tranne il reso CONFERMATO, che S-5 rende non terminale nello stesso giro. Il trigger nuovo è differito: da zero
i mirror lo attraversano a transazione finita. I changeSet storici di `80_data` che scrivono quelle tabelle toccano
`esito` e `meta`, non `terminale` né le uscite a mano.

**Il reso «non si emetteva».** Due pgTAP fissavano «reso, commessa e fattura non si emettono»: S-3 (Tid, 2026-11-08) dà al
reso la sua emissione. Sono stati riportati al modello: `script/test-doc-lettori-stato-e-preventivo-al-modello-v1`
(test 6-8) e `script/test-doc-stato-codice-v1` (test 2-3). Nessun lettore BE legge l'emissione del reso (i
`stato_di_emissione` del backend sono di preventivo, offerta, contratto, ordine e bolla), e nel DB
`script.fn_doc_azione_passaggio` non ha chiamanti: aggiungere `emissione` al reso non cambia nessun percorso.

**La prova (2026-11-14).** `scripts/prova_changeset.py` sui changeSet di `00_schema` e `20_code`, più un changeSet di
scratch che simula i due CSV e le righe del codice d'errore: il loader `loadUpdateData` non lo prova nessuno strumento,
e il token `NULL` è già misurato (§11.2). Esito con l'estratto, sui **129** pgTAP che nominano gli oggetti del giro:

* `config/test-terminale-senza-uscita-manuale-v1` (**nuovo**, plan 10): 10 su 10 (senza l'estratto, interrotto);
* `vendite/test-vw-stato-sorgente-ddt-reso-v1` (adeguato, plan 14): 14 su 14. Il test 7 cambia con S-5 (reso confermato
  non terminale); il nuovo test 14 sposta le marche (`esito` su EMESSO, `terminale` su CONSEGNATO) e la vista le segue;
* i due test dell'emissione del reso, riportati al modello: verdi;
* gli altri: invariati. I rossi che restano c'erano già senza l'estratto, e sono rossi da owner per costruzione
  (`test-doc-lettori-…` 23, `test-esecutivi-ba-coppia-v1`, `test-doc-verbo-comune-e-porta-v1`,
  `test-fn-available-actions-ddt-reason-catch-all-v1`);
* `vendite/test-documenti-numerazione-trasloco-v1` **non** l'ho fatto girare: non è transazionale (comincia con un
  `DO`), e lo strumento non lo lancia. Numera il reso alla conferma (test 8-9): con il seed lo stato di emissione è
  CONFERMATO, quindi deve restare verde. **Lo lancia Tid.**

**pgTAP nuovo** `config/test-terminale-senza-uscita-manuale-v1`, sulla matrice vera del reso, in transazione:

1. una riga a mano attiva ANNULLATO → DRAFT: rifiutata;
2. la stessa di processo: ammessa;
3. diventare a mano (`UPDATE` del solo `meta`): rifiutata;
4. spenta, e a mano: ammessa;
5. riaccesa (`UPDATE` del solo `attivo`): rifiutata;
6. `terminale` = true sul reso CONFERMATO, che ha l'annullo a mano: rifiutato;
7. la configurazione dei sette documenti: nessuna coppia (il seed di catalogo, non una popolazione);
8. forma: 14 montaggi differiti, per funzione e argomento;
9. la fattura, che non ha `terminale`: `E_SCRIPT_CHIAMATA_NON_VALIDA`;
10. il lettore rilegge: l'offerta SUPERATA è terminale, e annullata la revisione torna EMESSA e non lo è più.

**Pagine `manual/`.** `config/stati_doc_ddt`, `config/stati_doc_reso`, `config/stati_doc_listino_versioni`,
`vendite/vw_stato_sorgente_ddt`, `vendite/vw_stato_sorgente_reso`, `vendite/trgfn_resi_gen_numero`,
`script/vw_stati_doc_ddt_merce_partita`, `script/fn_doc_terminali_con_uscita_manuale` (nuova, anche per il trigger).

**Ricadute BE/FE (elenco chiuso).** Nessuna di comportamento: le viste espongono le stesse colonne, e il BE e il FE leggono
`doc_esito` e `doc_terminale` come prima. Cambia un valore: il reso confermato non è più terminale nel percorso della
pratica (`PraticaPercorso.vue` mostra il Tag dello stato finché il documento non è terminale: è il comportamento voluto
da S-5). Il codice d'errore nuovo lo solleva solo chi scrive la configurazione: niente nella tassonomia di `api.md`.
⚠️ *Corretto il 2026-11-14 (segnalazione del BE):* la frase sopra bastava per la tassonomia, non per l'elenco.
`backend/apps/core/services/error_policies_generated.py` ricopia **tutto** il catalogo, quindi ogni codice nuovo in
`codici_errore.csv` vuole la rigenerazione, chiunque lo sollevi. Le richieste sono due:

| # | File | Che cosa |
| --- | --- | --- |
| BE-T1 | `docs/it/backend/pratiche/manual/api_percorso.md:121` | `doc_terminale` non vuol dire «il documento non evolverà più»: vuol dire «da questo stato non esce nessun passaggio a mano; il sistema può ancora spostarlo» (S-1, A) |
| BE-T2 | `backend/apps/core/services/error_policies_generated.py` | rigenerare (`manage.py genera_error_policies`): entra `E_DOC_TERMINALE_CON_USCITA_MANUALE` (`DATO_ERRATO`, id 1483). Va bene nello stesso giro della rigenerazione chiesta dal cantiere dei template (`20261114-01 … -04`) |

#### ⑩ Trovato dal giro 4: ANNULLATA della fattura — ✅ deciso da Tid il 2026-11-14 (a), fatto nel §6.13

Il presidio della raggiungibilità (giro 4, §6.13) trova, oltre agli stati attesi, un caso che il censimento del §4 non
aveva visto. In `config.stati_doc_fiscale` lo stato ANNULLATA ha `applica_fattura` = true, ma nessuna riga della matrice
porta una **fattura** in ANNULLATA: l'unica entrata è DRAFT → ANNULLATA, che vale solo per il lotto (`solo_lotto`). Con il
modello di oggi una fattura pre-fiscale si cancella (`vendite.fn_elimina_fattura_da_lotto`, e l'annullo del lotto
`vendite.fn_annulla_lotto_da_draft` le elimina), e una fattura numerata si corregge con una nota di credito. Il guard
`vendite.trgfn_fatture_numerata_non_annulabile`, che rifiuta il passaggio in ANNULLATA di una fattura numerata (col
letterale `'ANNULLATA'`), protegge quindi un passaggio che la matrice non ammette.

È la stessa forma di R-3 (il vocabolario dice di più della matrice). **D-ANN, proposta DB:** `applica_fattura` = false su
ANNULLATA, dal CSV. Il guard `trgfn_fatture_numerata_non_annulabile` resta a presidio di una strada che la matrice
chiude: si ritira solo se nessuno scrive lo stato della fattura fuori dalla matrice, e il censimento di chi la scrive va
fatto prima. In alternativa (b): una riga di matrice DRAFT → ANNULLATA per la fattura, se l'annullo di una fattura
pre-fiscale deve esistere come stato e non come cancellazione.

**Deciso (Tid, 2026-11-14): (a).** `applica_fattura` = false su ANNULLATA, dal CSV (§6.13). Il guard
`trgfn_fatture_numerata_non_annulabile` resta: il censimento di chi scrive lo stato della fattura fuori dalla matrice non
è fatto, e finché non lo è il guard è una rete.

### 6.13 Giro 4 — gli stati che nessun passaggio raggiunge (team DB, 2026-11-14)

Col via di Tid (2026-11-14). Chiude ⑤, S-8 e R-3.

| ChangeSet / file | Che cosa |
| --- | --- |
| `80_data/changelog/20261114-03` | S-8: `DELETE` di ALLOCATO, SPEDITO, CONSEGNATO e FATTURATO da `config.stati_doc_ordini`, forward-only (linee-guida-sql §11.2: `loadUpdateData` non cancella). Nessuna riga della matrice li nomina e nessun documento, di vendita o d'acquisto, li porta (dbdev, 2026-11-14): se un database ne avesse, la FK ferma il `DELETE` e lo dice |
| CSV `stati_doc_ordini` | le quattro righe escono |
| CSV `stati_doc_fiscale` | R-3: `applica_lotto` = false su REGISTRATA; D-ANN (a): `applica_fattura` = false su ANNULLATA |

⚠️ **Numero.** Lavora un'altra sessione DB sullo stesso albero (i template dei documenti, `20261114-01`, `-02`). Il
`20261114-03` l'ha dato `scripts/prossimo_changeset.py` ed è stato occupato subito. Per i giri 5 e 6 il range lo dà
Tid.

**Fuori, di proposito.** La «cintura» FATTURATO di `vendite.fn_list_ordini_da_pushare` (`NOT IN ('DRAFT', 'ANNULLATO',
'FATTURATO')`): un codice che non esiste più non nomina niente, e la funzione si riapre nel giro dell'ordine (giro 6),
dove anche DRAFT e ANNULLATO escono dal letterale. Così si apre una volta sola. `vendite.ordini.fatturazione_trigger` è un
altro asse, che riusa i nomi: non c'entra.

**pgTAP nuovo** `config/test-stati-raggiungibili-v1` (plan 5). È un presidio sulla **forma** della configurazione (il seed
di catalogo), dichiarato tale:

1. per le dieci testate della mappa `script.fn_doc_stato_modello`, ogni stato attivo si raggiunge dallo stato iniziale
   lungo righe attive della matrice, col filtro della mappa; per fattura e lotto contano gli stati che valgono per loro
   (`applica_fattura`, `applica_lotto`). Nessuna eccezione: ANNULLATA della fattura (⑩) l'ha chiusa D-ANN;
2. controesempio costruito: uno stato attivo nuovo del reso, senza entrate, è trovato;
3. controesempio costruito: spenta l'unica riga che entra nel reso CONFERMATO, lo stato è trovato;
4. S-8: i quattro stati non ci sono più;
5. R-3 e D-ANN: REGISTRATA vale solo per la fattura, ANNULLATA solo per il lotto.

Senza l'estratto 1, 4 e 5 sono rossi; con l'estratto 5 su 5.

**La prova (2026-11-14).** Il `DELETE` estratto, più un changeSet di scratch che simula il CSV fiscale (R-3), con ognuno
dei **127** pgTAP che nominano i quattro stati, REGISTRATA, `applica_lotto` o i due vocabolari: 122 verdi, e un rosso nuovo atteso, riportato al modello: `pratiche/test-proiezione-stato-sorgente` (test 19, la mappa D1 dei nove stati d'ordine), ora sui cinque stati e col codice nel confronto, non per posizione: 31 su 31. Gli altri sono interruzioni presenti anche senza l'estratto (`script/test-vw-giornale-entita`; i due test dell'emissione del reso del §6.12, che vogliono le colonne del giro 3). `vendite/test-fn-list-ordini-da-pushare-v1` non è transazionale (manca il `ROLLBACK`) e lo strumento non lo lancia: **lo lancia Tid**.

pgTAP adeguato: `pratiche/test-proiezione-stato-sorgente` (19).

**D-ANN (a), la prova (2026-11-14).** Con il CSV fiscale simulato (R-3 e D-ANN), sui **73** pgTAP che nominano il vocabolario fiscale, `applica_fattura` o il guard della fattura numerata: 72 verdi, e `script/test-vw-giornale-entita`, interrotto anche senza l'estratto. Il presidio della raggiungibilità passa senza eccezioni. L'unico lettore che cambia risposta è `config.fn_get_stati_doc_fiscale('FATTURA')`, che non elenca più ANNULLATA fra gli stati della fattura; il backend non lo chiama. Pagina `config/stati_doc_fiscale` aggiornata.

**Pagine.** `config/stati_doc_ordini` (le righe dei quattro stati e la nota «restano attivi»), guida
`gestione-ordini` (la riga «⏳ non ancora raggiunti»).

**Richieste al team FE (elenco chiuso, dal §4.4 corretto al §5):**

| # | File | Che cosa |
| --- | --- | --- |
| FE-S8a | `frontend/src/vendite/ordini/constants.js` | via `STATO_ORDINE.ALLOCATO`, `SPEDITO`, `CONSEGNATO`, `FATTURATO` (nessun lettore) |
| FE-S8b | `frontend/src/locales/it.json`, `en.json` | via `vendite.ordini.stato_info.fatturato` |
| FE-S8c | `frontend/src/vendite/preventivi/components/PreventiviDrawer.vue`, `frontend/src/vendite/components/CommessaGestioneDrawer.vue`, `frontend/src/vendite/components/ContrattoDrawer.vue`, `frontend/src/vendite/ordini/components/OrdiniDrawer.vue`, `frontend/src/vendite/ddt/components/DdtDrawer.vue`, `frontend/src/vendite/resi/components/ResoDrawer.vue` | i commenti che citano `ALLOCATO` come esempio di descrizione: l'esempio è uno stato che non c'è più |

BE: nessuna (nessun riferimento fuori dai test).

### 6.14 Giro 5 — il listino, i COMMENT stantii, `in_gioco` (team DB, 2026-11-14)

Col via di Tid (2026-11-14), numeri dal primo libero: il `-04` lo aveva preso l'altra sessione, si parte dal `-05`. Chiude
⑧, S-9, i COMMENT del §2 (§4.8) e R-2. ✅ **Applicato da Tid il 2026-11-14**, pgTAP verdi.

| ChangeSet | Che cosa |
| --- | --- |
| `00_schema/config/20261114-05` | ⚠️ Il primo apply (2026-11-14) si è fermato sulla `preCondition`: `indexExists` con il solo schema non trova l'indice su PostgreSQL. Il changeSet non era applicato: la `preCondition` diventa un `sqlCheck` sul catalogo, come in `20260703-05`. ⑧: l'indice `ux_stati_doc_listino_versioni_iniziale` diventa `uq_stati_doc_listino_versioni_iniziale`, il nome degli altri vocabolari. Nessun corpo, vincolo o pgTAP lo nominava. S-9: la versione di listino non prende `fase` |
| `00_schema/config/20261114-06` | §4.8: sedici COMMENT al presente, letti contro il catalogo di dbdev: `config.stati_doc_offerte` (mancavano accettazione e rifiuto), la sua matrice («5 transizioni»: sono sette, due di processo), `config.stati_doc_reso` e la sua `meta` (`fase` era «in meta.fase»), `ordine` e `is_superato` dell'offerta, `codice` di contratti, bolla e ordini (stati che non ci sono), `stati_doc_fiscale.fase`, `vendite.contratti.is_abortito_snapshot` (trigger, colonna e vincolo che non ci sono più), `emissione` dei cinque vocabolari («Emetti produce numero e PDF»: vero solo per la bolla; gli altri hanno il numero dalla nascita) |
| `20_code/vendite/20261114-07` | R-2: i tre lettori di `in_gioco` passano a `pre_fiscale` (`script.fn_check_attivita_riportabile_da_emettere`, dove l'alias diventa `marchio_pre_fiscale`; `vendite.vw_documenti_trattenuti_da_lotto`; `vendite.vw_dash_competenza_attivita`), e `vendite.vw_lotti_fase` perde la colonna. `CREATE OR REPLACE VIEW` non toglie colonne: la vista e le sue **otto** dipendenti (catena da `pg_depend`) si tolgono dalla cima senza `CASCADE` e si ricreano dalla base, con `security_invoker` e i COMMENT, anche di colonna. I privilegi li danno i default dello schema per `zeroerp_owner`. I COMMENT che spiegavano `in_gioco` sono al presente |

**La prova (2026-11-14).** I tre changeSet, con ognuno dei **31** pgTAP che nominano le nove viste, la funzione,
l'indice o la postura `security_invoker`: tutti verdi. Una prova di scratch conferma che le nove viste ricreate hanno
`SELECT` per `zeroerp_app`, `security_invoker` e il COMMENT. Catalogo identico dopo ogni `ROLLBACK`.

**pgTAP adeguati.** `vendite/test-vw-lotti-fase-v1`: il test 1 (il contratto della vista) senza `in_gioco`; il test 5 ora
presidia, sulla forma, che nessuna vista e nessuna funzione lo legga più. Rosso senza l'estratto, verde con.
`vendite/test-motivo-non-fatturata-v1` (la fixture separa i due lotti su `pre_fiscale`) e
`vendite/test-documento-trattenuto-da-lotto-v1` (un commento).

**Pagine.** `vendite/vw_lotti_fase` (lo stato che non si risolve: non succede più, la vista lo difende lo stesso),
`script/fn_check_attivita_riportabile_da_emettere`. La doc auto-generata non è rigenerata.

**Ricadute BE/FE.** Nessuna: il BE legge `pre_fiscale` dal 2026-11-13 (`e174a302e2`); nel test Django restano solo i
commenti che raccontano il ritiro.

**Trovato per il giro 6.** Il contratto copia `is_draft_snapshot` da `config.stati_doc_contratti.is_bozza`
(montaggio di `vendite.trgfn_doc_snapshot_da_stato`), una colonna che dice la stessa cosa di `iniziale`: è una copia del
significato, della famiglia di S-2. Entra nel giro del contratto.

### 6.15 Giro 6 — il censimento (team DB, 2026-11-14)

**Il perimetro.** Il testo delle funzioni (commenti tolti) e delle viste degli schemi applicativi, contro i codici dei
sei vocabolari del giro (preventivo, ordine, contratto, bolla, reso, versione di listino), sul catalogo di dbdev il
2026-11-14: 104 oggetti nominano almeno un codice. Molti sono falsi positivi: lo stesso codice vive in vocabolari
diversi (BOZZA e CHIUSA di commesse, pratiche, template dei documenti; DRAFT dei documenti interni di magazzino e della
mail; ATTIVO delle automazioni, delle vesti, dei dispositivi). Tolti quelli, restano **circa 55 oggetti**.

**La regola per classificarli** (S-2 e S-3, Tid 2026-11-08):

* un codice usato **per il suo significato** (in bozza, emesso, accettato, annullato, terminale) si legge dalla colonna
  del vocabolario: è S-2;
* un codice che nomina **la destinazione di un processo** (EVASO, PARZIALMENTE_EVASO, SPEDITO, CONSEGNATO, RESO della
  bolla, ATTIVA e CHIUSA del listino) resta, attraverso `script.fn_doc_stato_id`: il processo nomina la sua
  destinazione come la nomina la riga della matrice;
* un codice di **un altro asse** che riusa i nomi (`vendite.ordini.fatturazione_trigger`: CONFERMATO, SPEDITO,
  CONSEGNATO) non è uno stato e non si tocca.

**Gli oggetti, per documento** (da classificare uno per uno sul corpo vivo):

| Documento | Oggetti |
| --- | --- |
| preventivo | `script.fn_available_actions_preventivo`, `vendite.fn_crea_revisione_preventivo`, `vendite.fn_preventivo_proietta_stato_smistamento`, `vendite.trgfn_preventivi_guard_annullamento`, `vendite.trgfn_preventivi_guard_transizione`, `vendite.vw_dash_fatturazione_preventivi` |
| ordine | `script.fn_available_actions_ordine`, `vendite.fn_list_ordini_da_pushare` (con la «cintura» FATTURATO del §6.13), `vendite.fn_ordine_proietta_stato_evasione`, `vendite.fn_situazione_merce_ordine`, `vendite.fn_genera_ddt_da_ordine`, `vendite.trgfn_ordini_guard_transizione`, `vendite.trgfn_ordini_normalize`, `vendite.vw_dash_fatturazione_ordini` |
| contratto | `script.fn_available_actions_contratto`, `vendite.fn_get_contratto_attivo`, `vendite.trgfn_contratti_freeze_listino_versione`, `vendite.trgfn_contratti_guard_transizione_stato`, `vendite.trgfn_contratti_set_categoria_cliente_snapshot`; lo snapshot `is_draft_snapshot` da `is_bozza` (§6.14) |
| bolla | `script.fn_available_actions_ddt` (`can_edit_righe = DRAFT`), `script.fn_check_ddt_emittibile`, `script.fn_check_ddt_riga_correggi_qta_evasa`, `vendite.fn_annulla_ddt`, `vendite.fn_cambia_stato_ddt`, `vendite.fn_ddt_push_diagnosi`, `vendite.trgfn_ddt_gen_numero_emesso`, `vendite.trgfn_ddt_guard_causale_emissione`, `vendite.trgfn_ddt_guard_indirizzi_obbligatori`, `vendite.trgfn_ddt_guard_transizione`, `vendite.trgfn_ddt_guard_transizione_approvazione`, `vendite.trgfn_ddt_riga_legame_guard`, `vendite.vw_dash_fatturazione_ddt`, `dbops.vw_ddt_trasferimenti_consegnati_senza_arrivo` |
| reso | `script.fn_available_actions_reso`, `script.fn_check_reso_merce`, `vendite.fn_conferma_reso`, `vendite.fn_annulla_reso`, `vendite.fn_chiudi_riconsegna_reso`, `vendite.fn_riapri_riconsegna_reso`, `vendite.fn_genera_ddt_riconsegna`, `vendite.trgfn_resi_guard_ddt_consegnato`, `vendite.trgfn_resi_righe_guard_quantita` |
| versione di listino | `vendite.fn_attiva_versione_listino`, `script.fn_check_listino_congelabile`, `script.fn_check_versione_listino_chiudibile`, `script.fn_check_versione_listino_eliminabile`, `vendite.fn_chiudi_versioni_listino_scadute`, `vendite.fn_versioni_listino_da_chiudere`, `vendite.fn_listino_versione_in_vigore`, `vendite.fn_listino_ha_storia`, `vendite.fn_listini_attivi_uom_non_convertibili`, `vendite.fn_prezzi_legame_oltre_la_fine`, `vendite.fn_resolve_prezzo_listino_v2_esito`, `vendite.fn_check_listino_provenienza_emittente`, `vendite.trgfn_listini_kit_guard`, `vendite.trgfn_listini_righe_comp_guard_immutabilita_v5`, `vendite.trgfn_listini_righe_guard_periodicita_quota_fissa`, `vendite.trgfn_listini_righe_guard_stato`, `vendite.trgfn_listini_versioni_guard_per_stato`, `vendite.trgfn_listini_versioni_guard_transizione_stato` |

**L'ordine proposto.** Un documento per giro (6a … 6f), così ogni oggetto si apre una volta sola e ogni giro ha la sua
prova e il suo apply: preventivo, ordine, contratto, bolla, reso, listino. Ogni giro porta il presidio sulla forma
del documento (nessun codice dei suoi stati nei corpi dei suoi lettori di significato), come il test 12 di
`vendite/test-offerta-guard-dal-vocabolario-v1` per l'offerta, e una marca spostata dove il significato lo permette.
