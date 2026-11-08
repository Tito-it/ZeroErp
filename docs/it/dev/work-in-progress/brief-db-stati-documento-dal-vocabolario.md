# Brief DB — Gli stati dei documenti: ogni significato dal vocabolario

## ⏭️ Chi riparte — aggiornato al 2026-11-08

**Riparte: Tid**, col via allo sviluppo (S-2 … S-10 decise come proposte dal DB, 2026-11-08); poi il **team DB**, un giro per difetto.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ DB | i difetti, trovati riscrivendo le pagine `config/manual/stati_doc_*` (giro DOC.4 di `brief-db-sorgente-documento-e-riga`), verificati sul DB | §2 | — |
| 2 | ✅ Tid | il brief si apre: i difetti degli stati vanno qui, non nel cantiere della provenienza (2026-11-08) | — | — |
| 3 | ✅ Tid | **S-1**: `terminale` = nessun passaggio **a mano** in uscita; gli automatismi restano (A, 2026-11-08) | §3 | — |
| 4 | ✅ DB | censimento: per ogni difetto i lettori e gli scrittori, la proposta di correzione, il pgTAP, le ricadute (2026-11-08) | §4 | — |
| 5 | ✅ Tid | S-2 … S-10 come proposte dal DB («confermo la tua proposta», 2026-11-08) | §4.9 | — |
| 6 | Tid | via allo sviluppo | — | 5 |
| 7 | DB | sviluppo, prova in transazione, pgTAP | — | 6 |
| 8 | BE/FE | le ricadute del §4.10 (FE: costanti degli ordini e copia degli stati terminali dell'offerta; BE: il rifiuto dell'offerta, se S-3) | §4.10 | 7 |

**Decisioni aperte di Tid:** nessuna. Decise il 2026-11-08: S-1, lettura A; S-2 … S-10 come proposte dal DB (§4.9; per S-8 il ritiro, non l'`attivo = false`). **Lavoro da committare:** questo brief.

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
| bolla | `trgfn_ddt_gen_numero_emesso`, `trgfn_ddt_guard_causale_emissione`, `trgfn_ddt_guard_indirizzi_obbligatori`, `trgfn_ddt_guard_transizione_approvazione` (EMESSO→emissione) |
| contratto | `trgfn_contratti_freeze_listino_versione`, `trgfn_contratti_set_categoria_cliente_snapshot` (DRAFT, ATTIVO); `fn_get_contratto_attivo` (ATTIVO) |
| reso | `fn_conferma_reso`, `fn_annulla_reso`, `script.fn_check_reso_merce`, `trgfn_resi_righe_guard_quantita` (DRAFT, ANNULLATO) |
| preventivo, ordine | `fn_crea_revisione_preventivo` (DRAFT); `fn_list_ordini_da_pushare` (DRAFT, ANNULLATO) |
| listino | `trgfn_listini_kit_guard`, `trgfn_listini_righe_guard_stato`, `trgfn_listini_righe_guard_periodicita_quota_fissa`, `trgfn_listini_righe_comp_guard_immutabilita_v5`, `trgfn_listini_versioni_guard_per_stato`, `script.fn_check_versione_listino_eliminabile`, `fn_check_listino_provenienza`, `fn_listino_ha_storia`, `fn_resolve_prezzo_listino_v2_esito` (BOZZA→iniziale) |
| fiscale | i tre di ② (DRAFT); `trgfn_fatture_guard_stato` (`'EMESSA'` per il cancello IVA: il vocabolario fiscale non ha `emissione`, S-3) |

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
(`PreventiviDrawer.vue:781`, `CommessaGestioneDrawer.vue:403`, `ContrattoDrawer.vue:735`) restano veri come esempio
solo se lo stato c'è: da riscrivere. BE: nessuna. Doc: `guide/gestione-ordini.md:399`.

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
  l'**emissione del reso** (CONFERMATO: lì nasce il numero, `trgfn_resi_gen_numero`) e l'**emissione fiscale** (EMESSA: il
  cancello IVA di `trgfn_fatture_guard_stato`). **Proposta DB:** una colonna `rifiuto` su offerte e preventivi (come
  `accettazione`, col suo lettore `script.fn_stato_rifiuto_id`), `emissione` su `stati_doc_reso` e `stati_doc_fiscale`.
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
| ⑤ (S-8) | nessuna | `frontend/src/vendite/ordini/constants.js`, `frontend/src/locales/it.json`, `frontend/src/locales/en.json`; commenti in `PreventiviDrawer.vue`, `CommessaGestioneDrawer.vue`, `ContrattoDrawer.vue` |
| ⑥ | nessuna | nessuna |
| ⑦ | nessuna (stesse colonne; cambia un valore con S-5) | nessuna |
| ⑧ | nessuna | nessuna |

Il codice d'errore nuovo di ④ lo solleva solo chi scrive la configurazione: da registrare (`codici_errore.csv`,
`messaggi_errore.csv`), senza ricadute sul BE oltre al catalogo generato.
