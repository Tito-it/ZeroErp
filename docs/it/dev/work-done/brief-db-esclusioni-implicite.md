# Brief DB — Le esclusioni implicite: chi passa senza dire chi è

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-04. **A chi:** Tid (apply, pgTAP, decisioni
> aperte); poi BE/FE per le ricadute di §9.
> **Origine:** §2-bis di [migliorie-generali-da-test-valutazione.md](migliorie-generali-da-test-valutazione.md)
> (valutazione qualitativa scritta dal BE il 2026-10-04), verificata dal team DB sul catalogo di
> dbdev lo stesso giorno (§2-bis.8 del documento). Voce **D17** del documento.
> **Decisioni di Tid (2026-10-04):** Q-4 sì (guard); Q-1 sì, come proposto; Q-6
> `emittente_soggetto_ruolo_id`; il v1 non si tocca; `UPDATE OF`: doc corretta e guard censiti;
> per Q-2 la madre del ritorno a DRAFT diventa DEFINER; Q-3 sì (presidio + §10.5). **Rimandata:** Q-2
> nel suo insieme («lo facciamo dopo», Tid, 2026-10-04; §4).
> **Stato:** ✅ **DB chiuso per Q-4, Q-1, Q-3, `UPDATE OF`, v1 e Q-6** il 2026-10-04:
> `20261004-80 → -86` applicati su dev (22:50, automazioni alle 23:19), pgTAP verdi (§10).
> Cancello v1 in CI dalla prossima corsa. ⏳ **Q-2 rimandata** (§4): è la parte che tiene aperta D17.
> ⏳ BE: R-1 di §9 (due codici nuovi). **Non committato.**

## 1. Perché un brief solo

I quattro rilievi hanno la stessa forma: un'esclusione dalla regola che regge su un invariante che
nessuno scrive e nessun cancello tiene.

| # | L'esclusione | L'invariante implicito |
| --- | --- | --- |
| Q-1 | utente NULL = vede tutto | «l'utente non è mai NULL quando la veste c'è» |
| Q-2 | una GUC spegne il blocco | «la GUC la accende solo chi deve» |
| Q-3 | le DEFINER leggono oltre la RLS | «le tabelle sono del migratore e `FORCE` è spento» |
| Q-4 | la DELETE di un lotto passa | «nessuno numera fra la check e la DELETE» |

Sono giusti oggi, e quando smettono di esserlo non danno errore.

## 2. Q-4 — Una fattura numerata non si cancella e non cambia numero ✍✅

### 2.1 Il difetto

1. **La corsa.** `fn_riporta_lotto_a_draft`, `fn_annulla_lotto_da_draft` e
   `fn_elimina_fattura_da_lotto` controllano «nessuna fattura numerata» **prima** del lock, e il
   lock nomina la coppia (funzione, lotto). La numerazione (`fn_assign_numero_fattura`) blocca solo
   la riga della fattura e quel lock non lo prende. `fn_cleanup_fatture_by_ids` cancella con
   `WHERE id = ANY(...)`, senza `numero IS NULL`. Una numerazione che si chiude fra la check e la
   DELETE produce una fattura numerata cancellata: un buco nella sequenza fiscale. Su
   `vendite.fatture` non c'era nessun guard `BEFORE DELETE` (solo lo storico).
2. **Il retro.** `numero` non era protetto. Il lock di colonna generico non è adatto, perché blocca
   anche NULL → valore, cioè la numerazione stessa. In EMESSA, prima del congelamento, un UPDATE
   poteva togliere il numero, e la DELETE successiva passava. Chiudere la sola DELETE avrebbe
   lasciato aperta la porta accanto.

La domanda del BE («lo stato della pipeline esclude già i due percorsi?») ha risposta no: a DB
niente li esclude. Un pgTAP non lo prova, perché la corsa vuole due sessioni. La risposta giusta è
un invariante di tabella, che rende la corsa innocua: se succede, la transazione fallisce invece
di lasciare il buco.

### 2.2 La forma

* Una funzione e un trigger, `trg_fatture_a05_guard_numero_fiscale_upd_dlt`:
  `BEFORE UPDATE OR DELETE`, `WHEN (OLD.numero IS NOT NULL)`, fascia `_a05_` («questa cosa non si
  tocca» parla prima dei guard `_a10_` e dello storico `_z90_`).
* Il discriminante è `OLD.numero`, non lo stato: la fattura viene numerata mentre è ancora EMESSA.
  È la scelta dei due guard fratelli, `trgfn_fatture_guard_data_numerata` e
  `trgfn_fatture_numerata_non_annulabile`.
* Sull'UPDATE si confrontano `registro_id`, `anno`, `serie`, `numero`. Il trigger è senza `OF`
  (§6): il confronto sta nella funzione. La numerazione parte da NULL e il `WHEN` la lascia fuori.
* Nessuna GUC di bypass: è un invariante fiscale.
* Nessuna `fn_check_*`: le tre check dei percorsi esistono già e spengono i pulsanti col motivo.
  Questo guard è la rete sotto di loro.

### 2.3 Chi scrive (censito il 2026-10-04)

* **DELETE**: solo `vendite.fn_cleanup_fatture_by_ids`, chiamata dai tre verbi del lotto, che
  rifiutano già le numerate (`E_LOTTO_FATTURE_NUMERATE`, `E_FATTURA_GIA_NUMERATA`). Nessuna FK
  `ON DELETE CASCADE` verso `fatture`, nessuna DELETE nel backend né nei test Django.
* **`registro_id`/`anno`/`serie`/`numero`**: solo `fn_assign_numero_fattura`, da numero NULL. Il
  backend non li scrive.

### 2.4 Consegna

| ChangeSet | Cosa |
| --- | --- |
| `20_code/vendite/20261004-80-create-trgfn-fatture-guard-numero-fiscale` | la funzione |
| `20_code/vendite/20261004-81-create-trigger-fatture-guard-numero-fiscale` | il trigger `_a05_` |
| CSV `codici_errore` + `messaggi_errore` (id 1196, 1197) | `E_FATTURA_NUMERATA_NON_CANCELLABILE`, `E_FATTURA_NUMERO_NON_MODIFICABILE`, entrambi `CONFLITTO_STATO` |

pgTAP: nuovo `vendite/test-fatture-guard-numero-fiscale-v1.sql` (11 asserzioni: quattro controlli
che passano, cinque rifiuti, struttura, codici). Aggiornato `vendite/test-numera-fattura-opz-emessa`:
la sua pulizia in coda cancellava una fattura numerata, e al suo posto il test 6 asserisce il
rifiuto. Gli altri 15 pgTAP che cancellano fatture lavorano su fatture **non** numerate (censito
il 2026-10-04): il builder `fn_pgtap_crea_fattura` non numera.

## 3. Q-1 — Utente NULL = nessun accesso ✍✅

### 3.1 Il difetto, ed è un residuo

`script.fn_check_user_emittente_scope` rispondeva `true` con l'utente NULL («job batch»). Le policy
`ef_whitelist` restavano chiuse solo perché chiedono **anche** la veste OPERATORE. Una sessione con
la veste impostata e `app.current_user_id` vuoto vedeva tutte le aziende. Il BE imposta le GUC
«tutto o niente» in una CTE, quindi serve un difetto applicativo per arrivarci. Ma è proprio il
«backend che sbaglia» da cui il modello promette di proteggere.

Il 2026-09-04 il guard di scrittura (`trgfn_guard_emittente_scope`) aveva già tolto lo stesso ramo.
Senza utente passa solo chi bypasserebbe comunque la RLS (`row_security_active`), e il guard decide
quel caso **prima** di chiamare la canonica. La lettura era rimasta indietro.

La famiglia è di **tre** funzioni:

| Funzione | Prima | Dopo |
| --- | --- | --- |
| `script.fn_check_user_emittente_scope` | utente NULL → `true` | → `false` |
| `script.fn_scope_ef_whitelist_via_efba` (policy del billing account) | utente NULL → `true`; il commento diceva «whitelist vuota = tutto», falso dal P-2a | → `false`; commento allineato |
| `script.fn_get_emittenti_scope_sr_effettivo` (le due ricerche) | utente NULL → la restrizione del chiamante, cioè con NULL «tutto» | → `'{}'` |

### 3.2 Chi chiama con utente NULL (censito il 2026-10-04)

* **Le policy**: con la veste e senza utente non vedono niente. Owner, superuser e `BYPASSRLS` non
  passano dalle policy.
* **I verbi DEFINER che ricopiano il filtro** (`magazzino.fn_posta_*`, `fn_apri/libera_blocco`,
  `vendite.fn_cambia_stato_ddt`, `fn_conferma/annulla_reso`): nessun job li chiama. Senza utente
  rispondono «non trovato»; i verbi di magazzino rifiutano già prima, con `fn_guard_azione`.
* **`fn_check_user_can_create_ba`, `fn_resolve_emittente_for_user`**: entrano nella canonica solo
  con l'emittente attivo valorizzato, cioè da una richiesta.
* **Le due ricerche** (`fn_search_soggetti_universale`, `fn_get_search_detail`): INVOKER, leggono
  l'utente dalla GUC, nessun job le chiama.
* **`trgfn_guard_emittente_scope`**: tratta l'utente NULL da sé, invariato.

### 3.3 Consegna

| ChangeSet | Cosa |
| --- | --- |
| `20_code/script/20261004-82-update-fn-check-user-emittente-scope-utente-nullo` | la canonica |
| `20_code/script/20261004-83-update-fn-scope-ef-whitelist-via-efba-utente-nullo` | l'adapter del billing account |
| `20_code/script/20261004-84-update-fn-get-emittenti-scope-sr-effettivo-utente-nullo` | lo scope delle ricerche |

Corpi presi dalla doc auto-generata, confrontati col DB vivo (uguali, a parte i `COMMENT`).

pgTAP:

* **asserzioni nuove**: `script/test-scope-emittenti-fail-closed-v1` (test 8-11, le tre funzioni
  con utente NULL) e `script/test-guard-emittente-senza-utente` (test 9-10: la **policy vera**,
  come applicazione, vede l'ordine con l'utente e non lo vede senza);
* **asserzioni girate di segno** (pinnavano «NULL = true»): `script/test-emittente-attivo-impersonazione-scope`
  (7), `script/test-permessi-fn-check-emittente-scope` (6), `script/test-permessi-funzioni-risoluzione`
  (14), `script/test-search-scope-interno-v1` (6, 7);
* **fixture riscritta**: `anagrafiche/test-billing-account-auto-link-ef`, test 1. Faceva
  `INSERT … RETURNING` su `billing_account` con la veste e senza utente, e il RETURNING passa dalla
  policy di lettura. Ora l'id si prende prima da `nextval` e l'INSERT non ha RETURNING; il soggetto
  del test (il trigger d'aggancio) resta lo stesso;
* **solo commenti**: `anagrafiche/test-stiva-movimenti-annullo-v1`,
  `rls/test-rls-email-ambito-reparto-operatore`.

Gli altri pgTAP che svuotano l'utente (22, censiti) si aspettano già un rifiuto o zero righe,
oppure girano da owner, oppure leggono funzioni che non toccano `billing_account`.

## 4. Q-2 — Le GUC di bypass legate al proprietario ⏳ rimandata (Tid, 2026-10-04)

### 4.1 In parole semplici

Alcuni blocchi del DB hanno una «chiave di servizio»: una variabile di sessione (GUC) che, accesa
a `on`, li spegne. Serve alla manutenzione: correggere un refuso su un codice bloccato, ripulire i
log, riportare un lotto in bozza. Il problema è che **quella chiave la può girare chiunque si
connetta**, anche l'applicazione: basta un `SET`. Un blocco che l'applicazione può spegnere da
sola protegge solo finché l'applicazione non sbaglia. Il progetto lo sa già: «una GUC è un
cartello, non un cancello» (`trgfn_guard_emittente_scope`).

Il rimedio esiste già nel progetto, su due porte (`zeroerp.ddt_cambio_stato`,
`zeroerp.reso_cambio_stato`): la chiave funziona **solo se chi la gira è il proprietario delle
tabelle**, cioè il migratore, il DBA, un job di manutenzione, oppure una funzione DEFINER del
proprietario che l'applicazione chiama come verbo. L'applicazione da sola non spegne più niente.

### 4.2 Le dieci GUC (censite il 2026-10-04)

| GUC | Cosa spegne | Chi la accende oggi |
| --- | --- | --- |
| `allow_lock_columns_override` | il lock di colonna (anche `codice_interno`, l'aliquota IVA…) | nessun codice; 9 pgTAP |
| `maintenance_ruoli_delete` (via `trgfn_delete_block_by_guc`, 8 tabelle) | il divieto di DELETE su clienti, emittenti, banche… | nessun codice; 2 pgTAP |
| `allow_contabile_riga_delete_override` | il contenuto delle righe di distinta | nessun codice; 8 pgTAP |
| `allow_user_emittente_delete_override` | il divieto di togliere la whitelist a un utente attivo | nessun codice; 23 pgTAP |
| `maintenance_allow_attivita_bypass` | il guard commessa delle attività fatturabili | nessuno |
| `maintenance_allow_delete_logs` | l'append-only dei log di vendita | nessun codice; 9 pgTAP |
| `maintenance_indirizzi_dettaglio` | la protezione degli indirizzi | `maintenance.proc_bump_indirizzi_dettaglio` (job) |
| `maintenance_toponomastica` | la protezione della toponomastica | `maintenance.proc_bump_toponomastica` (job) |
| `maintenance_reset_lotto_draft` | **otto** guard del lotto e delle fatture | `vendite.fn_cleanup_fatture_by_ids` (INVOKER, chiamata dai verbi del lotto); 9 pgTAP |

Il backend non ne accende nessuna.

### 4.3 La proposta

1. **Un building block**, `script.fn_bypass_attivo(p_guc text, p_tabella regclass) RETURNS
   boolean`: `current_setting(p_guc, true) = 'on' AND script.fn_is_proprietario_tabella(p_tabella)`.
   Le dieci letture lo chiamano, nello stesso giro (regola del 2: dieci copie della stessa regola).
2. **Il ritorno a DRAFT passa da una madre DEFINER** (✅ approvato da Tid). I tre verbi del lotto
   diventano `SECURITY DEFINER` del proprietario: dentro di loro la chiave funziona, fuori no.
   Diventando DEFINER leggono oltre la RLS, quindi il perimetro lo controllano da sé
   (`fn_scope_ef_whitelist_via_lotto`, come già fanno `fn_cambia_stato_ddt` e i verbi di
   magazzino); `fn_cleanup_fatture_by_ids` perde l'EXECUTE per l'app.
3. **I job di manutenzione** girano già come proprietario: nessun cambio.

### 4.4 Quanto costa

* **I pgTAP**: 45 file con il runner applicativo accendono queste GUC come scorciatoia di fixture
  (pulizie, stati forzati). Con il legame al proprietario cadono. Ognuno va riscritto passando dal
  verbo, oppure dichiara `pgtap-runner: owner` col suo motivo. Il costo maggiore è qui, e a
  pensarci è anche la conferma del difetto: quei test fanno ciò che oggi l'applicazione potrebbe
  fare.
* **Il DB**: un building block, dieci funzioni ritoccate, tre verbi DEFINER con il controllo del
  perimetro.

Raccomandazione: farlo, in un brief suo, partendo da `allow_lock_columns_override` e
`maintenance_reset_lotto_draft` (le due che proteggono dati fiscali e chiavi fra ambienti).

## 5. Q-3 — L'invariante «tabelle del migratore, `FORCE` spento» ✍✅

### 5.1 In parole semplici

La RLS non vale per il **proprietario** della tabella, a meno di accendere `FORCE`. Il progetto ci
conta: le funzioni DEFINER, che girano come il proprietario, leggono oltre la RLS, ed è così che i
risolutori di scope vedono i dati che servono per decidere. Funziona perché valgono due cose:
le tabelle sono del migratore (non dell'applicazione) e `FORCE` è spento. Su dbdev è vero
(2026-10-04: le 172 tabelle con RLS sono di `titodb`, nessuna ha `FORCE`). Però **non è scritto da
nessuna parte che debba restare vero, e nessun test lo guarda.** Due errori possibili, entrambi
silenziosi:

* una tabella nuova creata dall'applicazione (proprietario `zeroerp_app`): l'applicazione non subisce
  più la RLS su quella tabella;
* qualcuno accende `FORCE` «per sicurezza», come §10.5 sembra suggerire: i risolutori DEFINER
  smettono di vedere e lo scope diventa vuoto, oppure sbagliato.

### 5.2 La proposta

1. **Un pgTAP di postura**, `dbops/test-postura-proprietario-rls-v1`, con tre asserzioni a criterio:
   * nessuna tabella degli schemi applicativi è di proprietà di `zeroerp_app`;
   * nessuna tabella con RLS ha `relforcerowsecurity` acceso (elenco delle eccezioni dichiarato e
     vuoto);
   * il proprietario di ogni funzione DEFINER è il proprietario delle tabelle (oggi lo tiene il
     registro `sec_functions_owner`: il test lo verifica dal catalogo, non dal registro).
2. **Riscrivere §10.5 di linee-guida-sql** con l'invariante in chiaro, e il perché `FORCE` resta
   spento. Oggi il testo dice «usare sempre `FORCE` se la tabella è di `zeroerp_app`»: la regola
   giusta è che quel caso non deve esistere.

Costo piccolo, nessun cambio di comportamento. ✅ Deciso da Tid il 2026-10-04.

### 5.3 Consegna (2026-10-04)

* **pgTAP nuovo** `dbops/test-postura-proprietario-rls-v1.sql` (runner applicativo: legge solo il
  catalogo), sei asserzioni a criterio: precondizione, un solo proprietario per le tabelle con RLS
  (quello di `vendite.fatture`), nessuna tabella di `zeroerp_app` fuori da `django`, nessun `FORCE`
  sulle tabelle persistenti, ogni DEFINER del proprietario delle tabelle o di un superuser,
  `zeroerp_app` senza `BYPASSRLS`. Estensioni escluse per appartenenza (`pg_depend`), non per nome.
  Il terzo punto della proposta è diventato questo criterio: le sette DEFINER di `postgres`
  (dblink, log fuori transazione, nel registro `sec_functions_owner`) passano perché superuser.
* **Le query** del test girate su dbdev come applicazione il 2026-10-04: 172 tabelle con RLS, un
  solo proprietario (`titodb`), zero violazioni sui punti 2-4. È il presidio di un invariante che
  oggi regge: il suo valore è il giorno in cui smette di reggere.
* **linee-guida-sql §10.5** riscritto: l'invariante in chiaro, il divieto di accendere `FORCE`
  «per sicurezza», il presidio; §10.9 allineato. Un pgTAP può accendere `FORCE` dentro la propria
  transazione (`rls/test-rls-offerte-satelliti`): il `ROLLBACK` lo spegne.

## 6. `UPDATE OF` — doc corretta, trigger censiti ✍✅

### 6.1 La doc

`linee-guida-trigger.md` diceva che un trigger `UPDATE OF col` «non scatta se non cambiano quelle
colonne». In PostgreSQL scatta se la colonna è nel `SET`, anche a valore uguale, e **non** scatta se
la colonna la cambia un altro trigger `BEFORE`. Riscritta la sezione: per reagire a un cambio di
valore si usa `UPDATE` senza `OF` con `WHEN (OLD.x IS DISTINCT FROM NEW.x)`; `OF` resta giusto per
«la colonna è stata chiesta nel `SET`», su colonne senza scrittori automatici.

### 6.2 Il censimento (2026-10-04)

Ogni trigger con colonne (`tgattr`) confrontato con i trigger `BEFORE UPDATE` della stessa tabella
che scrivono `NEW.<colonna>`: 34 coppie.

| Esito | Coppie |
| --- | --- |
| 🔴 **Mordeva** | i cinque `z90_propaga_qta_componenti` (righe di preventivo, ordine, DDT, contratto, eccezione d'offerta): `AFTER UPDATE OF quantita`, ma `quantita` la ricalcola `trgfn_qta_from_operativa` da `qta_operativa`. Il backend sui preventivi aggiorna `qta_operativa` e `uom_operativa_id`, non `quantita` (`backend/apps/vendite/db/preventivi_repository.py`, `RIGA_UPDATE_COLUMNS`): i componenti del kit restavano con la quantità vecchia |
| ✅ Innocue | `gen_codice` (scrive solo se NULL), `normalize` idempotenti, l'emittente dei DDT/resi (solo in INSERT), `tipo_doc_fiscale_id` delle attività (solo se NULL), la conferma del regime dell'emittente (lo scrittore è il percorso legittimo), `resi_righe_guard_quantita` (ha già `qta_operativa` fra le colonne) |
| ⚠️ Da verificare | `registro_id` scritto da `trgfn_ddt_gen_numero_emesso` / `trgfn_resi_gen_numero` all'emissione: il require «registro attivo» non scatta (dipende da come `fn_get_registro_documento` sceglie il registro); `data_attivazione` azzerata da `trgfn_clienti_set_periodo` all'annullamento: `trgfn_clienti_set_parent_istanza` non scatta |

### 6.3 Consegna

| ChangeSet | Cosa |
| --- | --- |
| `20_code/script/20261004-85-update-trgfn-componenti-propaga-qta-commento` | solo commenti: il corpo ripeteva la frase sbagliata |
| `20_code/vendite/20261004-86-recreate-trigger-propaga-qta-componenti-when` | i cinque trigger: `AFTER UPDATE … WHEN (OLD.quantita IS DISTINCT FROM NEW.quantita)` |

pgTAP nuovo: `vendite/test-componenti-propaga-qta-da-operativa-v1.sql` (struttura sulle cinque
tabelle, e su un kit di preventivo: cambiando solo `qta_operativa` il componente segue; un UPDATE
del padre che non cambia la quantità non riscrive il componente, letto dal `ctid`).
⚠️ La quantità di un componente non si sceglie a mano: `trgfn_componenti_calcola_quantita`
(BEFORE sul componente) la impone = coeff × padre. La prima versione del test scriveva 7 sul
componente e aspettava che restasse: rossa alla prima corsa di Tid (2026-10-04), riscritta sul
`ctid`. La prova su cluster usa-e-getta non l'aveva vista perché lo stub non aveva quel trigger.

⚠️ **Dati di dev**: i componenti dei kit la cui quantità è cambiata solo tramite `qta_operativa`
portano la quantità vecchia. Se servono, si correggono a mano (AGENTS.md, «bug di dati in
sviluppo»).

## 7. Il v1 non si tocca, e la regola sull'emittente ✍✅

* **v1**: `scripts/guardrail_v1_congelato.py` + manifesto `db/changelog/v1-congelato.json`
  (sha256 di 558 file: `baseline/`, `migrations/`, `changelog-master.yaml`), step nuovo in
  `ci-validate.yaml`, divieto in linee-guida-sql **§11.11**, riga nella mappa di `.codex/AGENTS.md`.
  Un'eccezione si concorda con Tid e rigenera il manifesto nello stesso commit (`--rigenera`).
* **Q-6**: linee-guida-sql §2, «L'emittente si nomina col suo ruolo»: ogni tabella nuova usa
  `emittente_soggetto_ruolo_id`; le esistenti convergono quando un cantiere ne tocca il modello.
* **Q-5**: accorpata a D8 del documento di valutazione (modello di `acquisti`).

## 8. Verifica

* **Cluster PG18 usa-e-getta** (2026-10-04), con tabelle minime e uno stub di
  `fn_log_and_raise_error`. Eseguito l'SQL **estratto** dagli YAML: prima i rollback (stato di
  oggi: `fn_check_user_emittente_scope(NULL, …)` = `t`, trigger `UPDATE OF`, propagazione mancata
  riprodotta: padre 3, componente 2), poi i changes, poi i rollback in ordine inverso, poi di nuovo
  i changes. Esiti dopo i changes: componente 6; un UPDATE senza cambio di quantità non propaga;
  le tre funzioni con utente NULL danno `false`/`false`/`'{}'`; il guard lascia passare la DELETE
  di una non numerata, la numerazione da NULL e un UPDATE senza cambi fiscali, e rifiuta DELETE,
  numero tolto, serie e anno cambiati, col contesto atteso (`colonne`, `bersaglio`).
* **Guardrail statici** verdi: `run_on_change`, `pgtap_preambolo`, `precondition_seed`,
  `ddl_su_trigger_automazione`, `grant_ruolo_batch`, `sql_letterali`, `timestamp_senza_fuso`,
  `v1_congelato` (anche in negativo: un file v1 toccato dà rosso).
* **Non coperto dal cluster**: l'apply su dbdev, la corsa pgTAP vera, `plpgsql_check` e i presidi
  trasversali. Fatti da Tid il 2026-10-04 (§10).

## 9. Ricadute su BE/FE

* **R-1 (BE) — l'unica attività richiesta**: due codici nuovi, `E_FATTURA_NUMERATA_NON_CANCELLABILE`
  ed `E_FATTURA_NUMERO_NON_MODIFICABILE` (`CONFLITTO_STATO`, 409). Si rigenera
  `backend/apps/core/services/error_policies_generated.py` con `manage.py genera_error_policies` e
  si committa. ⚠️ Non è facoltativo: `apps/core/tests/test_error_policies_divergenza_db.py` è rosso
  finché il file non coincide col catalogo. Nessuna chiave i18n FE: la frase la dà il catalogo
  (`config.messaggi_errore`), come per i fratelli `E_FATTURA_GIA_NUMERATA` e
  `E_FATTURA_NON_ANNULLABILE`, che nel frontend non compaiono. Nessuna interfaccia produce i due
  codici nel percorso normale: arrivano solo da una corsa (ritorno a DRAFT mentre si numera).
* **R-2 (BE)**: nessun cambio richiesto da Q-1. Il backend imposta già le GUC «tutto o niente»;
  da oggi una sessione con la veste e senza utente non vede niente, invece di vedere tutto.
* **R-3 (BE/FE)**: nessun cambio per la propagazione dei kit: la correzione è tutta a DB.

## 10. Applicazione (Tid)

✅ Applicato su dev il 2026-10-04 alle 22:50 (`20261004-80 → -86`, poi il mirror dei CSV dei
codici), automazioni alle 23:19. ✅ **pgTAP verdi** (Tid, 2026-10-04) su:

* `dbops/test-postura-proprietario-rls-v1` (Q-3);
* i tre pgTAP nuovi o nuovi in parte: `vendite/test-fatture-guard-numero-fiscale-v1`,
  `vendite/test-componenti-propaga-qta-da-operativa-v1`, `script/test-guard-emittente-senza-utente`;
* quelli aggiornati in §2.4 e §3.3;
* i presidi trasversali: `dbops/test-riferimenti-morti-v1` (`plpgsql_check` sulla funzione nuova),
  `script/test-catalogo-messaggi-errore-completo`;
* la baseline degli schemi `script`, `vendite`, `anagrafiche`, `rls`.

Due rossi alla prima corsa, entrambi del test e non del DB, corretti lo stesso giorno:

* `script/test-scope-emittenti-fail-closed-v1`: l'elenco in testa diceva `plan 12`, il
  `SELECT plan(8)` era rimasto (le quattro asserzioni nuove giravano e risultavano oltre il piano);
* `vendite/test-componenti-propaga-qta-da-operativa-v1`: il numero del preventivo superava
  `varchar(30)`, e il controllo 4 aspettava una quantità di componente scelta a mano che il modello
  non ammette (§6.3).

## 11. Resta aperto

* **Q-2** (§4), rimandata da Tid: in un brief suo, partendo da `allow_lock_columns_override` e
  `maintenance_reset_lotto_draft`.
* **R-1** al BE (§9): i due codici nuovi in `error_policies_generated.py`.
* **Da verificare** dal censimento `UPDATE OF` (§6.2): il registro scelto all'emissione di DDT e
  resi senza il require «attivo», e `trgfn_clienti_set_parent_istanza` all'annullamento del cliente.
* **Dati di dev**: i componenti dei kit con la quantità vecchia (§6.3), se servono, a mano.
