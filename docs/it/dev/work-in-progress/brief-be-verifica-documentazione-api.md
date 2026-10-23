# Brief BE — La documentazione API confrontata col codice

## ⏭️ Chi riparte — aggiornato al 2026-10-23 (sera)

**Riparte: il BE**, col passaggio unico BE-1 … BE-4 (§I.4). Il lato DB è tutto chiuso: D1, D4,
D5, D6, D7 (`20261023-01` … `-05`) e la scadenza di `error_log` e `audit_log` (§I.6), applicati
su dbdev e scratch, pgTAP verdi (Tid, 2026-10-23). **D2 e D3 sono
usciti da questo brief**: sono il tema del
[brief-modello-documento-vendita](brief-modello-documento-vendita.md) (M-1 … M-4).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB | Giro DB: `20261023-01` … `-05`, sei CSV, due pgTAP (uno nuovo), manual e guida; provato sullo scratch e su dbdev in transazione | §I | — |
| 2 | ✅ **Tid** | Apply su scratch e dbdev (`20261023-01` … `-05` `EXECUTED`), pgTAP verdi (2026-10-23) | §I.3 | 1 |
| 3 | **BE** | Il passaggio unico: BE-1 … BE-4 (⚠️ BE-1 e BE-2 nello stesso rilascio) | §I.4 | 2 |
| 3-bis | ✅ team DB + **Tid** | §I.6: `error_log` e `audit_log` nello scope, 90 giorni (solo CSV + un pgTAP); applicato, pgTAP verdi (2026-10-23) | §I.6 | — |
| 4 | **Tid** | Archiviazione in `work-done/` | — | 3 |

Decisioni aperte di Tid: **nessuna** (§I.5 decisa il 2026-10-23: 90 giorni, anche per
`audit_log`). Lavoro da committare: il giro DB del 2026-10-23 (§I.2 e §I.6), tutto
applicato.

⚠️ Fino a BE-1 + BE-2 il backend usa ancora la sua prenotazione: le colonne nuove restano
vuote sulle righe che scrive (`endpoint` NULL = riga senza legame) e la ripresa dopo 120
secondi non agisce. Nessuna regressione: è il comportamento di prima.

### 🟢 D1, D4-D7 — la forma decisa il 2026-10-21, sviluppata il 2026-10-23 (§I)

| # | Che cosa | Forma |
| --- | --- | --- |
| D1 | `E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE` da TECNICO (500) a DATO_ERRATO (400), un codice solo, col campo | il guard porta `campo` (codice_interno, colonna_numero, colonna_billing_account, colonna_serie) |
| D4 | Testo di `E_IDEMPOTENCY_IN_PROGRESS` per l'operatore | causa, soluzione, riga `en` |
| D5 | `idempotency_keys` e `request_log` non si pulivano | nello scope delle automazioni, scadenza alla nascita; key: un giorno |
| D6 | key `in_progress` orfane | soglia `SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI` (120 s) misurata da `prenotata_at` |
| D7 | key legata a utente ed endpoint | `E_IDEMPOTENCY_KEY_RIUSATA` (DATO_ERRATO, 400) |

Fatti e chiusi: 🔴 A (decisioni A1-A6), B (difetti di codice), C (alert scadenze
listini), E (`copertura_doc_api`), G (terzo giro), H (quarto giro, dialetto unico
della paginazione). Primo, secondo, terzo e quarto giro sono committati.

*Non bloccanti, backend:* `_righe_da_rate_da_payload` (pagamenti) e
`indirizzi_per_madre` (anagrafiche) somigliano al BB `PayloadValidator.voci` e non
sono migrati (§G); il tetto dei tool AI (max 50) resta una riduzione dichiarata
nella descrizione del tool, non un errore (§H).

---

## I. Giro DB del 2026-10-23 — D1, D4, D5, D6, D7

### I.1 Che cosa è cambiato, in parole semplici

* **D1.** Se l'amministratore, nel CRUD delle famiglie di numerazione, scrive una colonna
  che non esiste, o sceglie una sorgente senza tabella, riceve un errore **400 col campo da
  correggere** invece di un 500. Il campo arriva al form: `codice_interno`,
  `colonna_numero`, `colonna_billing_account` o `colonna_serie`.
* **D4.** L'operatore che riclicca un gesto irreversibile mentre il primo invio è ancora in
  corso legge «L'operazione è ancora in corso», con causa e soluzione, anche in inglese.
* **D5.** Le key di idempotenza scadono **dopo un giorno** e si cancellano col job settimanale
  che esiste già. Lo stesso buco c'era su `request_log`: la sua regola da 90 giorni non agiva,
  perché la tabella non era nello scope. Ora agisce.
* **D6.** Una key rimasta «in corso» perché il server è morto a metà si riprende dopo **120
  secondi**, invece di bloccare ogni reinvio fino alla key nuova del frontend.
* **D7.** Una key si rimanda **solo a chi l'ha prenotata, sullo stesso endpoint**. Usata da
  un altro utente, o su un'altra richiesta, dà 400 `E_IDEMPOTENCY_KEY_RIUSATA`.

### I.2 I file

| File | Che cosa |
| --- | --- |
| `20_code/vendite/20261023-01-update-trgfn-famiglie-documento-guard-riferimenti-campo` | D1: il guard porta `campo`; la frase del caso «sorgente senza tabella» parla all'operatore |
| `20_code/dbops/20261023-02-create-trigger-cleanup-at-alla-nascita-idempotency-request-log` | D5: la scadenza nasce con la riga, sulle due tabelle |
| `00_schema/dbops/20261023-03-alter-idempotency-keys-utente-endpoint` | D7: `auth_user_id`, `endpoint`; D6: `prenotata_at`; CHECK «la risposta c'è se e solo se la key è completed»; CHECK endpoint non vuoto |
| `20_code/dbops/20261023-04-create-fn-idempotency-prenota` | D6+D7: `dbops.fn_idempotency_prenota` (ESEGUI / REPLAY / IN_CORSO) |
| `80_data/changelog/20261023-05-delete-stati-check-dichiarazioni-idempotency-in-progress` | presidio C1: `in_progress` ora ha uno scrittore a DB |
| `codici_errore.csv` | D1 classe DATO_ERRATO e nota; D7 `E_IDEMPOTENCY_KEY_RIUSATA` (DATO_ERRATO) |
| `messaggi_errore.csv` | D1 soluzione; D4 riga it riscritta + en (1386); D7 it/en (1387, 1388) |
| `automation_scope.csv`, `automation_rules_tbl.csv` | D5: `dbops.idempotency_keys` e `dbops.request_log` nello scope; regola 24 (un giorno, base `data_insert`) |
| `parameters_sistema.csv` | D6: id 62 `SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI` = 120 |
| `stati_check_dichiarazioni.csv` | via `in_progress`; ragione di `completed`/`failed` riscritta |
| `db/pgtap/dbops/test-idempotency-prenota-v1.sql` (nuovo), `db/pgtap/vendite/test-famiglie-documento-guard-riferimenti.sql` (test 10-13) | i presidi |
| `dbzero/dbops/manual/idempotency_keys.md`, `request_log.md`, `guide/audit-e-tracciabilita.md` §7 | la doc dello stato attuale |

**Tre scelte dichiarate, prese scrivendo:**

* **La prenotazione è una funzione DB.** D6 la lasciava aperta («la funzione del claim, se
  passa al DB»). La regola della soglia e del legame vive così in un posto solo, e il backend
  la chiama.
* **La soglia si misura da `prenotata_at`, non da `data_update`.** Il trigger di audit
  riscrive `data_update` a ogni UPDATE, ed è montato su dbdev e, con lo scope di D5, anche da
  zero. È la stessa regola dei registri: la scadenza si misura da un orario reale.
* **Il CHECK sulla risposta vale nei due versi.** La funzione decide il replay dalla risposta
  e non nomina gli esiti che scrive il backend. Il presidio C1 è testuale: con
  `'completed'` nel corpo l'avrebbe contata fra i loro scrittori (rosso nella prima prova).
  Su dbdev nessuna riga lo viola (fatto datato 2026-10-23: 669 completed tutte con
  risposta, 263 failed tutte senza).

### I.3 La prova (2026-10-23, prima dell'apply) — ✅ dopo l'apply: verde nella corsa di Tid

SQL estratto dai changeSet e seed simulati dai CSV, in una transazione annullata, come
`zeroerp_owner`:

| pgTAP | scratch, senza | scratch, con | dbdev, con |
| --- | --- | --- | --- |
| `dbops/test-idempotency-prenota-v1` (nuovo) | 0/24 | 24/24 | 24/24 |
| `vendite/test-famiglie-documento-guard-riferimenti` | 9/13 (i 4 nuovi rossi) | 13/13 | 13/13 |
| `dbops/test-stati-check-scrittori-v1` | 15/15 | 15/15 | 15/15 |
| `dbops/test-riferimenti-morti-v1`, `script/test-catalogo-messaggi-errore-completo`, `dbops/test-cleanup-framework`, `config/test-codici-errore-*`, `config/test-parameter-fk-surrogate-dispatch-v1`, `vendite/test-famiglie-documento-crud-v1` e `-codice-v1` | verdi | verdi, identici | — |

* ⚠️ La misura **come app** arriva dalla corsa di Tid dopo l'apply: l'owner non è membro di
  `zeroerp_app`.
* Non coperto, dichiarato nel file: il ramo `E_CONFIG_MANCANTE` della soglia. L'applicazione
  non scrive `config.parameters`.
* Rossi preesistenti, non di questo giro: `vendite/test-registri-fatturazione-scadenza-alla-nascita`
  test 14 (rosso anche senza l'SQL estratto); il guardrail del preambolo segnala
  `dbops/test-automazioni-guasto-ambiente-rilanciato-v1.sql` (committato in `dbb810c3d`).
* Guardrail statici verdi: precondition/seed, runOnChange, DDL su trigger di automazione,
  v1 congelato, GRANT ai ruoli batch.

### I.4 Il passaggio unico al BE (dopo l'apply)

| # | Che cosa | Dove |
| --- | --- | --- |
| BE-1 | `IdempotencyStore.claim_or_replay` chiama `dbops.fn_idempotency_prenota(key, auth_user_id, endpoint, request_id)` e ritira il suo SQL. `endpoint` = metodo + percorso, senza query string; `auth_user_id` NULL per una richiesta anonima. ESEGUI → esegue; REPLAY → rimanda `response_payload`; IN_CORSO → 409 `E_IDEMPOTENCY_IN_PROGRESS` come oggi. `E_IDEMPOTENCY_KEY_RIUSATA` arriva dal DB come ogni errore di dominio (400) | `apps/core/services/idempotency_store.py`, `apps/core/api/endpoint_helpers.py` |
| BE-2 | ⛔ **Nello stesso rilascio di BE-1.** `mark_completed` nella STESSA transazione dell'handler (`handle_post_json`). `mark_failed` resta fuori dalla transazione che fa rollback. Senza BE-2, una key ripresa dopo 120 secondi può rifare un'operazione che aveva già fatto commit | `apps/core/api/endpoint_helpers.py` |
| BE-3 | Rigenerare `error_policies_generated.py` ed `error_messages_fallback.py`: D1 diventa DATO_ERRATO, D7 è un codice nuovo, D4 ha il testo nuovo | `apps/core/services/` |
| BE-4 | D1 nel drawer delle famiglie: l'errore ora è un 400 col campo da accendere. Rivedere i commenti di `famiglie_service.py` (righe 11 e 73) | `apps/vendite/services/famiglie_service.py`, FE |

### I.5 Aperto

* ✅ **Deciso da Tid il 2026-10-23: 90 giorni, e la stessa logica per `audit_log`** (§I.6).
  Testo originale della domanda:
* ~~**Per Tid — `dbops.error_log`.**~~ Ha `cleanup_at` come le due tabelle di D5, ma non è
  nello scope (su dbdev c'è per una riga a mano, come c'era `idempotency_keys`): oggi non
  scade, in CI e da zero. È lo stesso buco; non l'ho chiuso perché la sua durata non è
  decisa. Con la sola riga di scope prenderebbe il default di 30 giorni (regola 11). Anche
  `dbops.audit_log` ha la colonna ed è fuori dallo scope. Le due righe a mano di dbdev
  (`error_log`, `idempotency_keys`) restano; la seconda ora coincide col CSV.
* **Debito dichiarato:** `endpoint` resta nullable per le righe nate prima del 2026-10-23.
  Il NOT NULL è un changeSet successivo, quando il primo purge le ha tolte (un giorno dopo
  l'apply, più il giro settimanale).

### I.6 `error_log` e `audit_log` scadono (2026-10-23, decisione di Tid) — ✅ applicato, pgTAP verdi

* **Dove sta il termine.** Non in `config.parameters`: nella regola CLEANUP_AT di
  `dbops.automation_rules_tbl` (`params.ttl_days`), seminata da `automation_rules_tbl.csv`.
  È la sede unica: la leggono il job e il trigger alla nascita. Per cambiare la durata si
  cambia la riga del CSV.
* **Cosa è cambiato:** `dbops,error_log` e `dbops,audit_log` in `automation_scope.csv`;
  regole 25 (`error_log`, 90 giorni, base `occurred_at`) e 26 (`audit_log`, 90 giorni, base
  `executed_at`). Nessun changeSet: solo i due CSV e il pgTAP
  `dbops/test-registri-dbops-scadenza-v1.sql` (nuovo, 4 test).
* ⛔ **Niente trigger alla nascita su queste due**, diversamente da D5: le scrivono anche
  sessioni dblink (`script.fn_log_error_only`, `dbops.fn_audit_log_once`, service
  `zeroerp_log`), e `zeroerp_log` non ha SELECT su `dbops.automation_rules_tbl`. Verificato il
  2026-10-23. Il trigger farebbe fallire la registrazione degli errori. La scadenza la
  calcola il job sulle righe a NULL, come su dbdev dalla riga di scope a mano. Il test 4 lo
  tiene fermo.
* **Cosa porta lo scope:** il trigger TX_ID (`tx_id` c'è su entrambe), già montato su
  dbdev; niente audit, storico e lucchetti (mancano le colonne). Nessuna FK punta alle due
  tabelle, nessun guard sul DELETE; il job gira come owner (`proc_automations_cleanup_job`
  è DEFINER).
* ⚠️ **Su dbdev** le righe di `error_log` che hanno già una scadenza a 30 giorni la tengono:
  il job riempie solo i NULL. I 90 giorni valgono per le righe nuove.
* **Prova** (seed simulati, transazione annullata): `test-registri-dbops-scadenza-v1` senza
  2/4, con 4/4, su scratch e dbdev; `test-cleanup-framework` e `test-idempotency-prenota-v1`
  invariati. Guida §7 e manual di `error_log` aggiornati.

---

## 🔴 I PUNTI APERTI IL 2026-10-20 — e come si sono chiusi

### A. Decisioni di Tid — ✅ prese il 2026-10-20, ✅ applicate il 2026-10-21 (da committare)

1. **`order_by` fuori whitelist → 400 ovunque**, anche in anagrafiche, che oggi
   ripiega in silenzio sul default. È la stessa regola dei filtri a vocabolario. (§3.10)
2. **PATCH vuota → 400 ovunque** (`E_VALIDATION_INPUT`): la risorsa esiste, quindi
   il 404 di geo e soggetti è sbagliato. (§3.10)
3. **`page`/`page_size` in richiesta → 400**, nel BB `parse_list_params`, in un
   punto solo. (§3.10)
4. **Nomi dei parametri allineati, BE e FE nello stesso giro, senza alias**:
   `sort_by`/`sort_dir` delle fatture del lotto diventano `order_by`/`order_dir`;
   fondi-fattura passa da `page`/`page_size` a `limit`/`offset`. (§3.22)
5. **`Idempotency-Key` e `post_permission`** — precisata da Tid il 2026-10-20
   dopo l'inventario (fatto datato: 82 scritture su 457 chiedevano la key, senza
   un criterio — `stato/` 5 sì e 5 no, `emetti/` nessuna):
   - **la key è obbligatoria su ogni POST che scrive**: POST di creazione e di
     azione non sono idempotenti. PATCH, PUT e DELETE lo sono per semantica HTTP
     e restano senza; le POST che leggono (`post_accesso = "view"`) restano fuori.
     api.md («su tutti gli endpoint che modificano stato») va corretta di
     conseguenza;
   - **`post_permission`: azioni gemelle uguali**. Lo stesso verbo su documenti
     diversi ha la stessa forma di permesso. ⚠️ Correzione della prima stesura:
     non «ogni POST dichiara `post_permission`». È il permesso di un'azione di
     processo, e una POST di creazione chiede giustamente `add` sull'area. Dove
     un gemello ha l'azione di processo e un altro no, si verifica a DB quali
     codename esistono; un'azione mancante la si chiede al team DB, non la si
     inventa. (§3.22)
6. **Booleani del trasporto a stringhe: un BB solo**, col vocabolario
   `true`/`false` (assente = default); ogni altro valore è un 400. `as_bool`,
   `qp_bool`, `_parse_optional_bool` di amm-software e `_extract_metadati` di
   documenti si ritirano nello stesso giro. Prima si verifica che il FE mandi solo
   `true`/`false`. (§3.9)

### B. Difetti di codice — ✅ corretti il 2026-10-21 (da committare)

1. ✅ **Date ASC**: lotti e attività di commessa erano già corretti nel primo giro;
   le fatture del lotto con A4. Enti d'incasso e lookup codici partono ASC, ma non
   hanno colonne data: è corretto. (§6.1)
2. ✅ **Chiavi fuori contratto**: la creazione dell'emittente fiscale ora le
   rifiuta come la PATCH; geo, indirizzi e pratica sono stati chiusi con A2. (§6.2)
3. ✅ **`{"attivo": null}`** su un indirizzo è un 400. Le sei PATCH di geo leggono
   i campi per presenza (`_campi_patch_geo`): `null` svuota un campo nullable (prima
   non scriveva niente e rispondeva «salvato»). (§6.3)
4. ✅ **`dry_run`** del cambio stato versione: è un booleano JSON (`"true"` → 400). (§6.4)
5. ✅ **PUT profilo reparto**: le voci passano dal BB `_voci` (estratto con la regola
   del 2 dagli override dell'operatore); una lista assente è un 400 e non svuota più
   il profilo. (§6.5)
6. ✅ **Override parametri senza `value`** → 400 `E_PARAMETER_VALIDATION`. (§3.6)
7. ✅ **`pratiche_service`** solleva il codice vivo `E_PRATICHE_LISTA_CONTESTO_PARAMETRI_ESCLUSIVI`. (§3.8)
8. ✅ **Note del componente**: il componente dev'essere dell'articolo del path, o
   404. (§3.11)
9. ✅ **Gate L2** applicato anche alla creazione del contratto, sul cliente che il
   contratto avrà. (§3.16)
10. ✅ **Schemi OpenAPI**: i dieci lookup passano dal BB `risposta_lookup`;
    l'`order_by` degli ordini legge la whitelist; i tre punti di documenti li ha
    corretti l'altra sessione. (§2.1.4, §6.6)
11. ✅ Minori: docstring di `ApiLottoGruppiList` aggiornata; il ramo
    `PERMESSO_MANCANTE` resta, con la ragione scritta (la capability si calcola dal
    permesso, non dalla porta). (§6.7)

### C. Da verificare sul DB — ✅ confermato e corretto il 2026-10-21

1. ✅ **Alert scadenze dei listini**: confermato sulla struttura (`validita` =
   `daterange(valido_dal, valido_al, '[]')`, quindi `upper()` = `valido_al + 1`) e
   con un test sul DB vero che costruisce i due casi
   (`vendite/tests/db/test_listini_in_scadenza_db.py`, rosso prima della
   correzione): il successore contiguo non contava, e scadenza e giorni uscivano con
   un giorno in più. La query legge ora `valido_al`. (§3.14)

### D. Team DB — da passare (commento in chat a Tid, 2026-10-21)

1. **`E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE` ha classe TECNICO** (500) per un
   errore di input dell'amministratore: dovrebbe essere DATO_ERRATO. (§3.21)
2. ~~**Azioni di processo mancanti fra gemelli**~~ (A5, `post_permission`): ➡️ *Spostato il 2026-10-21 in [brief-modello-documento-vendita](brief-modello-documento-vendita.md) (M-1 … M-4).* emissione e
   cambio stato di contratto, offerta e ordine; stato della versione di listino;
   stato di distinte e righe di pagamenti; stato di inventari e rettifiche. Il
   preventivo, la commessa, la pratica, il DDT e il reso hanno un'azione di processo,
   questi no. Il backend non la inventa.
3. ~~**Cambio stato del DDT**~~ (aggiunto il 2026-10-21, ok Tid): ➡️ *Spostato il 2026-10-21 in [brief-modello-documento-vendita](brief-modello-documento-vendita.md) (M-1 … M-4).* l'emissione chiede
   `emetti_ddt` (`post_permission`), `ApiDdtCambiaStato` nessuna azione di processo,
   mentre il verbo DB applica `emetti_ddt` anche a `EMESSO → ANNULLATO`. Un solo
   `post_permission` sulla view non basta: le transizioni hanno permessi diversi. Al
   team DB la domanda su quale azione governi ciascuna transizione, e se il verbo
   possa dire al backend quale chiedere.
4. **Il testo di `E_IDEMPOTENCY_IN_PROGRESS` è per lo sviluppatore, non per
   l'operatore** (aggiunto il 2026-10-21, ok Tid). Oggi in `config.messaggi_errore`
   c'è solo la riga `it`: «Operazione gia` in elaborazione con la stessa
   Idempotency-Key.». Mancano `causa`, `soluzione` e la riga `en`. L'operatore lo
   vede quando riclicca un gesto irreversibile mentre il primo invio è ancora in
   corso (fatturazione, numerazione, registrazione di una distinta o di un documento
   di magazzino: il FE ora rimanda la stessa key, `useChiaveGesto`, §G). La classe
   `CONFLITTO_STATO` (409, `retryable`) resta giusta. Proposta, da rivedere col team:
   - `it` — messaggio: «L'operazione è ancora in corso.»; causa: «La stessa
     richiesta è già stata inviata e il server la sta eseguendo.»; soluzione:
     «Attendi qualche secondo e riprova: l'operazione non verrà eseguita due volte.»;
   - `en` — message: «The operation is still in progress.»; cause: «The same request
     has already been sent and the server is processing it.»; solution: «Wait a few
     seconds and try again: the operation will not be executed twice.».

   ⚠️ **Ricaduta BE, dopo l'apply.** Il codice non nasce dal DB: lo solleva il
   backend (`handle_post_json`, `apps/core/api/endpoint_helpers.py`) con una frase
   sua. Quindi:
   - la frase va riallineata nel ripiego `error_messages_fallback.py`, rigenerato
     **dopo** l'apply e mai col DB avanti rispetto a git; le policy non cambiano;
   - la `soluzione` del catalogo oggi arriva al client solo per gli errori che
     escono dal DB (`hint` della diagnostica), non per un `ServiceError` sollevato
     in Python. Per questo codice la frase all'operatore resta il ripiego FE
     (`SOLUZIONI_AZIONE_UI` di `useApiHandler`, 2026-10-21). Se si vuole che la
     legga dal catalogo, serve una scelta di disegno BE che vale per tutti i codici
     sollevati dal backend, non solo per questo: da decidere con Tid.

5. **`dbops.idempotency_keys` non si pulisce mai** (aggiunto il 2026-10-21, ok Tid).
   Con la modalità forte accesa (`DJANGO_API_STRONG_IDEMPOTENCY_ENABLED=1`, da Tid
   il 2026-10-21) ogni POST che scrive su un endpoint in modalità forte lascia una
   riga con la risposta intera in `response_payload`. La colonna `cleanup_at`
   esiste, ma nessuno la valorizza e nessun processo cancella: la tabella cresce
   senza limite. Al team DB:
   - chi valorizza `cleanup_at` all'inserimento (un default della colonna o il
     claim), con la ritenzione letta da un parametro di `config.parameters` e non
     scritta nel codice;
   - un processo `dbops` che cancella le righe scadute, sul modello dei processi
     periodici esistenti (accensione per ambiente compresa);
   - il vincolo sulla ritenzione: dev'essere ben sopra la durata del gesto lato FE
     (`DURATA_GESTO_MS` = 10 minuti, `useChiaveGesto`), perché una key cancellata
     prima del reinvio fa rieseguire l'operazione.
6. **Le chiavi rimaste «in corso» restano tali per sempre** (aggiunto il
   2026-10-21, ok Tid). Il claim (`IdempotencyStore.claim_or_replay`) scrive
   `in_progress` in una transazione sua, separata dall'operazione. Se il worker
   muore fra il claim e la marcatura (timeout di gunicorn a 60 secondi, riavvio,
   deploy), la riga resta `in_progress`, e ogni reinvio con quella key riceve 409
   `E_IDEMPOTENCY_IN_PROGRESS`, senza fine. Oggi l'unica uscita è che il FE, dopo
   10 minuti, generi una key nuova, e allora l'operazione si riesegue. Al team DB:
   - una regola per cui un `in_progress` più vecchio di una soglia (sopra il
     timeout di gunicorn, in `config.parameters`) conta come `failed` e si può
     riprendere; dove vive la regola (la funzione del claim, se passa al DB, o il
     processo di pulizia del punto 5);
   - ⚠️ la condizione perché riprenderla sia SICURO: l'`in_progress` orfano deve
     voler dire «l'operazione non ha fatto commit». Oggi non è garantito, perché
     la marcatura `completed` (`mark_completed`) è una scrittura separata dopo
     l'operazione: un crash fra le due lascia orfana un'operazione già fatta.
     **Ricaduta BE:** la marcatura `completed` nella STESSA transazione
     dell'operazione (`handle_post_json`, `apps/core/api/endpoint_helpers.py`); il
     claim resta separato, perché le altre richieste devono vederlo subito.
7. *Minore.* **La key non è legata a chi la usa.** La chiave primaria è la sola
   `idempotency_key`: chi rimanda la key di un altro utente, o la stessa key su un
   altro endpoint, riceve la risposta salvata dell'altro. La key è un UUID casuale,
   ma finisce nei log (`idempotency_replay key=…`). Proposta: registrare utente ed
   endpoint col claim, e fare il replay solo se coincidono (altrimenti un 409 o un
   400). Da valutare insieme al punto 6.

### E. Strumento — ✅ corretto il 2026-10-21

1. ✅ **`copertura_doc_api`**: un esempio con un codice concreto (`ruoli/CL/…`) è
   un'istanza della rotta, non un fantasma; una riga che dichiara di non documentare
   non conta come copertura; le lapidi scritte bene (titolo barrato, «ritirato»,
   «esistevano») si riconoscono. Esito: 722/722 rotte, **0 fantasmi**. Presidi nuovi
   in `core/tests/test_copertura_doc_api.py` (10-12). (§4)

### Secondo giro — da committare (2026-10-21)

Verifiche: suite backend verde (6389 test); sul DB vero (`ZEROERP_TEST_DB_E2E=1`)
6850 test, tre rossi dovuti al gate della key e corretti (`test_login_credenziale_db`);
frontend 938 test ed ESLint verdi; ruff e cricchetto mypy puliti; build della doc
verde (8 avvisi di ancore in `guide/gestione-degli-indirizzi.md`, preesistenti).

⚠️ Il working tree contiene anche il lavoro di `documenti/**` dell'altra sessione
(brief-db-modelli-documento-standard): al commit serve un `git add` mirato. File
toccati da questo giro: `core` (`db/_helpers.py`, `api/base_views.py`,
`api/payload_validators.py`, `api/openapi_params.py`, `api/views_lookup.py`,
`api/views_parameters.py`, `api/views_tracciamento.py`, `api/views.py`,
`api/email_views.py`, `api/partitioned_note_views.py`, `services/…`, il command
`copertura_doc_api`, i test); `amm_software`, `anagrafiche`, `catalogo`, `config`,
`magazzino`, `pagamenti`, `pratiche`, `ui`, `vendite` (view, service, repository,
test); `backend/scripts/tests/_smoke_https.sh`; il frontend (`core/api.js` con
l'interceptor, le funzioni API e gli store da cui è stata tolta la key, `codeJobs`,
`lotti`, `LottoDrawer`, `fondiFatturaDaDecidere`, `StepCompetenzeTab`); la doc
(`api.md`, i due cataloghi BB, le pagine `manual/` e questo brief).

### G. Terzo giro — revisione critica e BB (2026-10-21, da committare)

Revisione del secondo giro con correzioni (dati societari `{}` che azzeravano, valori
della PATCH pratica, gate L2 dei contratti su tipo e cliente, dialog «Personalizza»,
smoke di stampa, errori DB del profilo reparto, lunghezze di geo, tipo del valore dei
parametri, bundle dei listini senza `rows`). Decisioni di Tid applicate:

1. `?limit=abc` / `?offset=xyz` → **400**, BB `pagina_da_query` (ritirato `qp_int`);
   task-runs del lotto da `page_size`+`offset` a `limit`/`offset`, BE e FE;
2. BB `PayloadValidator.campi_per_presenza` (geo, magazzino, UoM, testata commessa) e
   `PayloadValidator.voci` (amm-software, bundle, resi, riconsegna, preferenze di lista
   e dashboard, preset);
3. FE `useChiaveGesto`: una key per GESTO sui verbi irreversibili (registra distinta e
   riga tardiva, verbi del lotto, fatturazione, numerazione, registra documento di
   magazzino, cancella fondo, elimina credenziale); ripiego del toast sul 409 in corso;
4. cambio stato del DDT aggiunto a 🔴 D.

Gesto (ok Tid 2026-10-21): `NumerazioneDataDialog` resta aperto fino all'esito
(prop `azione`, si chiude sul `true`) e chi lo apre azzera la key; le conferme secche
restano col limite dei 10 minuti, che sta sopra il timeout di gunicorn (60 s).
Modalità forte accesa da Tid in `.env.systemd`.

Aperti: `_righe_da_rate_da_payload` (pagamenti) e
`indirizzi_per_madre` (anagrafiche) somigliano a `voci` e non sono migrati; il testo di
`E_IDEMPOTENCY_IN_PROGRESS` è tecnico (team DB). Verifiche: backend 6412 test, frontend
951, ruff, mypy, ESLint e guard verdi; copertura doc 722/722.

### H. Quarto giro — un dialetto solo per la paginazione (2026-10-21, da committare)

Decisioni di Tid del 2026-10-21 («no procediamo senza nuovo brief, procedi»;
poi «il 400 è la cosa giusta», «correggere», «ok cancella»):

1. **Ogni lista pagina con `limit`/`offset`**, letti solo da `pagina_da_query`;
   `page`/`page_size` sono un 400 ovunque. Convertite dashboard, lotti (lista,
   fatture, gruppi, segnalazioni, task run), tracciamento, note, pagamenti,
   lookup codici, tabelle di configurazione, audit permessi, ricerca globale.
   L'envelope resta (`envelope_da_offset`, `pagina_di`); schema OpenAPI da
   `parametri_finestra`. Ritirati `validate_pagination` e `paramsPagina` (ora
   `paramsFinestra`); `useListaDrawerPaginata`, `usePagedDashFetch`, `useNote`,
   `usePagination`, `ConfigTablePanel` mandano la finestra.
2. **Fuori limite → 400** (`limit_fuori_limiti_1_<max>`, `offset_negativo`), non
   più riduzione muta; ritirati i guard duplicati di `pipeline_service` e
   `commesse_service`; il drawer dei registri chiedeva 500, ora 200.
3. **Tendine**: le sette che chiamavano `lookupCodici(rel)` senza `limit` (troncate
   a 25 in silenzio) passano dal BB `useLookupCodici`/`fetchLookupCodici`.
4. **Cancellati** `core/api/pagination.py` (classi DRF mai usate),
   `core/api/examples/domain_search_example.py` e il wrapper `list_ordini`
   (nessun chiamante). Tool AI: il parametro verso il modello è `limit`
   (`safe_limit`), `list_preventivi` parla `limit`/`offset`.
5. Smoke: oltre una dozzina mandavano `page_size` (rotti dal 2026-10-20, A3) e
   quattro chiavi fuori contratto (`iva_id`, `utility_id`, rotti da A2): corretti;
   `pratica-preventivi-bivio` tolto dalla baseline.

Presidi: `test_nessuna_view_legge_page_page_size`, `paginazioneDialetto.spec.js`,
`useLookupCodici.spec.js` § «nessuna tendina legge un rel senza limit».
Verifiche: backend 6410 test, DB vero 4812 (vendite, pagamenti, core, AI), frontend
957, ruff, mypy, ESLint verdi; sonda su 513 rotte senza 5xx nuovi; build della doc
verde. Doc: api.md, Policy, cataloghi BB, ~30 pagine `manual/`.

### F. ✅ Committato (`42c0d29ea`, primo giro)

Il primo giro del 2026-10-20 è nel commit `42c0d29ea`. Il working tree resta
**condiviso con un'altra sessione**, quindi al commit del secondo giro serve un
`git add` mirato. Il primo giro comprendeva:

- codice backend: `core` (BB in `db/_helpers.py`, `api/payload_validators.py`,
  `services/list_helpers.py`), `amm_software`, `anagrafiche`, `pratiche`,
  `pagamenti`, `vendite` (service, view, repository, il nuovo
  `services/_lotto_perimetro.py`) e i test relativi, compresi i file di test nuovi;
- `backend/scripts/tests/smoke-test-preventivi-componenti.sh` (tolto `iva_id`);
- doc: ~110 pagine `docs/it/backend/*/manual/`, `docs/it/dev/api.md`,
  `docs/it/dev/backend/catalogo-building-block-backend.md`, questo brief.

Il backend di sviluppo non si ricarica da solo: `kill -HUP` sul master di gunicorn.

---

## ✅ FATTO il 2026-10-20

- **Verifica** doc ↔ codice di tutte le 17 aree (§1, §2, §5).
- **Doc corretta**: tutte le pagine `manual/`; copertura **721/721 rotte**, 0 senza
  pagina, 5 «fantasmi» tutti falsi positivi noti; indice e regole in `api.md`;
  build della doc verde.
- **Codice corretto** (dettaglio in §3, punto per punto):
  - override operatore solo su credenziali OPERATORE, voci validate (§3.1);
  - righe di contratto e preventivo legate al documento dell'URL (§3.12);
  - flag del corpo solo booleani JSON, un BB solo (§3.13; §3.9 per il corpo);
  - gate L1 sulla PATCH dei componenti nei cinque documenti, gate L1 unico (§3.15);
  - campi obbligatori e codici del client inesistenti: 400 invece di 500 (§3.4-5);
  - satelliti del lotto e contesto-pricing: 404 invece di zeri o `{}` (§3.17);
  - filtri a vocabolario: 400 invece di lista vuota, BB `richiedi_codice_a_vocabolario`
    e registro degli specchi dei CHECK (§3.2, §3.19);
  - parametri morti delle righe di listino tolti (§3.20);
  - date DESC di default, anche riconosciute dal nome (§3.3, §3.18);
  - chiavi fuori contratto: 400 nei gemelli che le scartavano (§3.7, §3.22);
  - `ORIGINE_PREZZO_MANUALE` in una sede sola.
- **Verifiche**: suite backend verde (6347 test), ruff e mypy verdi, test DB verdi sul
  DB vero, a parte 3 guardrail rossi perché il DB di sviluppo è più avanti di git
  (codici `E_DOCUMENTI_*`, etichette del pannello config, `error_policies_generated.py`):
  da non rigenerare finché il lavoro DB non è in git.

---

## 1. Che cosa è stato verificato

Il 2026-10-20 Tid ha chiesto di verificare se la doc API coincide con lo
sviluppo effettivo, in ordine alfabetico di area.

- **Copertura formale.** `./manage-env.sh copertura_doc_api`; fatto datato
  2026-10-20: 720 rotte, 95% nominate, 36 scoperte, 6 fantasmi.
  ⚠️ Il comando misura solo se un path è **nominato**, non se la pagina è giusta.
- **Sostanza.** Per ogni pagina `manual/` che descrive endpoint sono stati
  confrontati view, service, repository ed `extend_schema`:
  - metodi;
  - parametri, paginazione e ordinamento;
  - campi ed envelope;
  - codici errore e status;
  - permessi.

  Analisi statica: nessuna chiamata HTTP; gli status sono dedotti dalla classe
  in `error_policies_generated.py`.
- **Perimetro:** tutte le aree, vendite compresa (vedi §5). acquisti e storico
  non hanno rotte, e la loro doc non ne promette.

Gravità:

- **ALTA** — chi segue la doc sbaglia la chiamata o il parsing;
- **MEDIA** — contratto incompleto (permessi, errori, default);
- **BASSA** — dettaglio.

---

## 2. Divergenze della documentazione — ✅ corrette (2026-10-20)

### 2.1 Difetti trasversali

1. **`page`/`page_size` nella doc, `limit`/`offset` nel codice** — ALTA.
   `parse_list_params` ignora `page`/`page_size` in silenzio, quindi si riceve
   sempre la prima pagina. Succede su categorie_clienti, articoli, template e
   asset di documenti; in documenti lo dice anche l'`extend_schema`.
2. **Default della paginazione 50 (o 100) nella doc, 25 nel codice**
   (`DEFAULT_LIMIT`) — MEDIA. Più di 12 pagine, fra core, amm-software,
   pagamenti, pratiche e documenti.
3. **«Ricerca sotto soglia → 400»**: dal 2026-09-26 il codice non lo dà più —
   MEDIA. Riguarda magazzino, la lista rate di pagamenti e la lista articoli.
4. **Schema OpenAPI con `data` dichiarato lista nuda**, mentre la risposta vera
   è `{data: {results}}` — ALTA per chi genera il client. Riguarda 10 view in
   `core/api/views_lookup.py`: merita un helper unico.
   In documenti lo schema dichiara 201 o 204 dove il codice risponde 200.
5. **Envelope vecchio `status` / `total` / `limit`** — ALTA. Riguarda
   `api_geo_config`, `api_indirizzi`, `api_soggetti`.
6. **Codici errore col nome sbagliato** — MEDIA:
   - in pratiche i codici sono senza prefisso `E_`, ritirati dal 2026-08-05;
   - in anagrafiche compaiono `E_AUTH_REQUIRED` ed `E_FORBIDDEN_ROLE`, che non
     esistono.
7. **Throttle della conferma via token**: la doc dice 3/15m, il codice usa
   10/15m (`ConfermaTokenRateThrottle`) — MEDIA. Riguarda reset password,
   invito operatore e invito portale/shop.
8. **«Ruolo ADMIN»**: oggi è il binding SUPER_ADMIN — BASSA.

### 2.2 Per area

| Area | ALTE | Pagine messe peggio |
| --- | --- | --- |
| admin / auth / portale / shop | 1 | `auth_views_audit.md`: il login vuole `email`, non `username` |
| ai-assistant | 2 | `api_ai_query.md`: azioni `confirm` e protocollo `__confirm__`/`__cancel__` non documentati |
| amm-software | 4 | lista e dettaglio operatori (`ruolo_sistema` ritirato, `*_reason` diventati codici), livelli `COMPLETO` invece di `TUTTO` |
| anagrafiche | ~15 | `api_soggetti`, `api_indirizzi`, `api_indirizzi_ruolo`, `api_geo_config`, `api_clienti`, `api_emittenti_fiscali`, `api_titoli_iva_soggetto` |
| catalogo | 3 | paginazione, `voce_utility` ritirato, conversioni UoM paginate |
| config | 0 | — |
| core | 0 | la sola divergenza ALTA sono gli schemi di §2.1.4 |
| documenti | 4 | modelli standard e `personalizza/` non documentati; «read-only v1» non è più vero |
| magazzino | 2 | blocca e libera merce non documentati |
| pagamenti | 0 | 5 MEDIE (`POST distinte/` non ha più `righe`, envelope di `ente_incasso`) |
| pratiche | 1 | `drift` nelle definizioni workflow non è mai `null` |
| ui | 3 | `Idempotency-Key` obbligatoria e non dichiarata, envelope `{results, count}` |

**Allineate:**

- core: `api_logout`, `api_permessi_effettivi`, `api_retry_policies`,
  `api_sessioni_attive`, `api_tipi_entita_lookup`;
- anagrafiche: `api_risorse_umane_lookup`;
- pratiche: quasi tutte (salvo i codici di §2.1.6).

---

## 3. ⚠️ Possibili difetti del **codice** — il dettaglio punto per punto (✅ corretto; D1 applicato il 2026-10-23, §I)

Qui la doc dice una cosa giusta, o una regola del progetto, e il codice fa
altro.

1. ✅ **Corretto il 2026-10-20** (da committare): i sei metodi passano dalla guardia `get_operatore`, come le altre `operatori/{id}/`; il test DB `test_override_oggetti_catalogo_db` usava un utente di categoria SISTEMA ed e' passato a `fn_pgtap_crea_operatore_umano` — **amm-software, `operatori/<id>/override-{aree,azioni,oggetti}/`**: manca il
   controllo «credenziale di categoria OPERATORE». Un PUT scrive override anche
   su una macchina o un cliente del portale (`amm_software/api/views.py:215-262`).
2. ✅ **Corretto il 2026-10-20** (da committare), col gruppo «lista vuota invece di 400/404» — **pagamenti, `GET distinte/`**: un valore di `stato` / `origine` fuori
   vocabolario dà una lista vuota con 200. La doc promette il 400
   (`pagamenti_service.py:377-416`).
3. ✅ **Corretto il 2026-10-20** (da committare; Tid: «inferenza nel BB») — `sql_order_clause`: la colonna di default nominata da `parse_list_params` segue `default_desc`, ogni altra colonna data parte DESC anche riconosciuta dal NOME (`e_chiave_data`); i 13 `ORDER BY` composti a mano con `sql_order_direction` fanno lo stesso; `default_desc=True` su categorie-clienti-listini, pratiche e promo — **Date ordinate ASC di default**, contro la regola «date DESC»: lista pratiche
   e `categorie_clienti_listini`.
4. ✅ **Corretto il 2026-10-20** (da committare), con tutto il gruppo «500 invece di 400»: campi obbligatori del corpo dal BB in pratiche (9 punti) e preventivi (3), voci dei PUT di override validate prima del repository, `qp_int_optional` in `views_conti_bancari`, i tre id del pricing (`int(x or 0)`), e un codice scelto dal client che non esiste (`nuovo_stato`, tipo nota/allegato) e' un 400 sul campo invece del 500 di `E_CONFIG_MANCANTE` (BB `resolve_config_id_by_codice_interno` col `codice_errore` del chiamante). Smentiti alla verifica: `int()` grezzo e date delle offerte davano gia' 400 — **Campo obbligatorio assente → 500 invece di 400**, perché letto con
   `payload["x"]`: view di pratiche, item dei PUT di amm-software.
5. ✅ (con il punto 4) **`anagrafiche/api/views_conti_bancari.py:194`**: un `int()` grezzo su un
   query param dà 500. La gemella dei contatti usa `qp_int_optional`.
6. ✅ **Corretto il 2026-10-21** (🔴 B6) — **Override dei parametri senza `value`**: scrive un override vuoto e risponde
   200.
7. ✅ **Corretto il 2026-10-20** (con il punto 22) — **POST clienti**: i campi ritirati vengono scartati in silenzio, mentre la
   PATCH li rifiuta.
8. ✅ **Corretto il 2026-10-21** (🔴 B7) — **`pratiche_service.py:537`**: solleva a mano un codice ritirato.
9. **Booleani non rigorosi** — ✅ *trasporto a stringhe chiuso il 2026-10-21 con A6 (`qp_bool_optional`).* *Storia:* *il corpo JSON e' risolto (2026-10-20, Tid: «corpo rigoroso, un BB»): `optional_bool` delle view delega a `PayloadValidator.optional_bool`. Resta il trasporto a stringhe: `as_bool` (11 consumatori, fuori vocabolario → False muto), `qp_bool`, `_parse_optional_bool` di amm-software e il multipart di `documenti/api/views.py` `_extract_metadati` — un vocabolario unico e 400 fuori vocabolario.* (`ok=abc` su job-runs, `is_active` operatori): ogni
   valore sbagliato vale `false`.
10. ✅ **Deciso da Tid il 2026-10-20, applicato il 2026-10-21** (🔴 A1-A3) — **Asimmetrie fra domini sullo stesso caso:**
    - un `order_by` fuori whitelist ricade in silenzio in un dominio e dà 400 in
      un altro;
    - una PATCH vuota dà 400 in un dominio e 404 in un altro;
    - `page`/`page_size` vengono ignorati invece che rifiutati.
11. ✅ **Corretto il 2026-10-21** (🔴 B8) — Minore: le note di un componente del catalogo ignorano l'`articolo_id` del
    path.
12. *(da qui, vendite — §5)* ✅ **Corretto il 2026-10-20** (da committare) — **Riga fuori dal documento dell'URL.** `PATCH`/`DELETE` di una riga di
    contratto (`views_contratti.py:470,486`) o di preventivo
    (`preventivi_service.py:1178-1330, 1656-1673`) non verificano che la riga sia
    del documento indicato nell'URL: si può modificare o cancellare la riga di un
    altro documento. I gemelli (componenti, resi) il controllo lo fanno.
13. ✅ **Corretto il 2026-10-20** (da committare), insieme a tutti i flag del corpo letti con `bool(...)` o col test di verita' (17 punti, il piu' grave `is_super_admin` in creazione operatore) — **`chiudi_esistente` letto con `bool(...)`** (`views_offerte.py:524`): la
    stringa `"false"` vale True e attiva la successione, che chiude il contratto
    esistente.
14. ✅ **Confermato e corretto il 2026-10-21** (🔴 C1) — **Alert scadenze dei listini, probabile sfasamento di un giorno.**
    `upper(validita)` su un daterange chiuso (`listini_repository.py:1044-1063`)
    fa uscire `valido_al` aumentato di 1 e scarta il listino successore
    contiguo. Da confermare sul DB.
15. ✅ **Corretto il 2026-10-20** (da committare; Tid: «gate L1 + unifica L1»): il gate L1 sta nel BB `dati_patch_componente` e vale per i **cinque** documenti, non solo il preventivo — mancava in tutti; `validate_componenti_overrides_authorization` delega a `check_permesso_override_prezzo` — **PATCH componente del preventivo senza il controllo
    `prezzo_override_manuale`** che la doc dichiara (TODO in
    `preventivi_service.py:1846-1886`).
16. ✅ **Corretto il 2026-10-21** (🔴 B9) — **Gate L2 sulla variazione globale dei contratti: c'è solo in PATCH**, non
    in create (`contratti_service.py:802`).
17. ✅ **Corretto il 2026-10-20** (da committare): BB `lotto_visibile` su **tutti** i satelliti del lotto (anche fatture e gruppi, che davano `200 []`), contesto-pricing di contratto e preventivo dalla testata — **Lettura senza perimetro: zeri o `{}` invece di 404** su un documento
    inesistente o fuori perimetro:
    - lotto: segnalazioni, `segnalazioni/rows/`, `task-runs/`;
    - contesto-pricing di contratto e preventivo.
18. ✅ **Corretto il 2026-10-20** (vedi il punto 3) — **Ordinamento ASC di default nonostante `default_desc`.** La causa è
    `parse_list_params(default_order=…)` senza `colonne_desc`. Succede su
    ordini, resi e promo, probabilmente anche ddt e contratti, e sulle
    dashboard. Si estende il punto 3.
19. ✅ **Corretto il 2026-10-20** (da committare; Tid: due regole) — tabella: BB `richiedi_codice_a_vocabolario` (codici dismessi ammessi) su stato di **sei** liste documento + natura fattura + `entity_type` + stato distinte; CHECK: specchi + `validate_enum_param`, presidiati dal registro `test_specchi_dei_check_db` — **Vocabolari non validati → lista vuota:**
    - lista fatture (`natura_doc_codice`, `stato_codice_interno`);
    - giornale (`entity_type`);
    - fatture del lotto (`stato_esecuzione`);
    - offerte e ordini (`stato_codice_interno`);
    - attività di commessa (`stato_emissione`, `stato_approvazione`).

    Si estende il punto 2.
20. ✅ **Corretto il 2026-10-20** (da committare): tolti i parametri morti delle righe di listino (vista, service, repository, schema); `esclusa` delle fatture del lotto e' un errore della sola doc — **Filtri accettati e ignorati:**
    - righe di listino (`billing_account_id`, `utility_id`);
    - fatture del lotto (`esclusa`).
21. ✅ **Applicato il 2026-10-23** (🔴 D1, §I; ricaduta BE in §I.4) — **`E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE` ha classe TECNICO**, quindi
    risponde 500 a un errore di input. → brief al team DB.
22. ✅ **Corretto (2026-10-20/21: chiavi ignote; emittente con 🔴 B2; `sort_by`, fondi-fattura, key e `post_permission` con A4-A5)**. *Storia:* **In parte corretto il 2026-10-20** (da committare; Tid ha scelto la sola voce «chiavi ignote»): una chiave fuori contratto e' un 400 anche nei 13 punti che la scartavano (righe e prelievi DDT, testata/righe/rientri dei resi, testata e righe degli ordini, testata e righe dei preventivi) e nella creazione del cliente; verificato prima che il frontend mandi solo chiavi del contratto. Ancora da allineare alla stessa regola: la CREAZIONE di un emittente fiscale (`emittenti_fiscali_service`) scarta le chiavi fuori contratto, la sua PATCH le rifiuta. Restano aperte, per decisione: `sort_by`/`order_by`, `page`/`page_size` di fondi-fattura, `Idempotency-Key`/`post_permission` non uniformi — **Asimmetrie fra gemelli in vendite:**
    - `sort_by` sulle fatture del lotto contro `order_by` sui gruppi;
    - fondi-fattura ancora su `page`/`page_size`;
    - chiavi ignote rifiutate in un gemello e scartate nell'altro
      (preventivo/ordini/resi, prelievi DDT);
    - `Idempotency-Key` e `post_permission` presenti in modo non uniforme.

---

## 4. Rotte senza pagina e fantasmi — ✅ documentate tutte (2026-10-20)

- **Rotte senza pagina, confermate:**
  - amm-software: `override-oggetti/`, `permessi-riepilogo/`,
    `processi/<codice>/accensione/`, `processi/<codice>/identita/riattiva/`,
    `setup-status/`, più 4 rotte `processi/…` che la pagina stessa dichiara non
    documentate;
  - anagrafiche: `billing-account/<id>/utilities/`, `istanze-utility/<id>/lookup/`;
  - catalogo: `articoli/<uuid>/uom/lookup/`;
  - documenti: `templates/<id>/personalizza/`, `asset/<id>/miniatura/`;
  - magazzino: `disponibilita/blocchi/` (POST) e `…/<id>/libera/`;
  - pratiche: `flussi/<id>/pratica/`.
- **Fantasmi:** nessuno è vero.
  - 4 sono falsi positivi del comando: esempi con un valore concreto (`EF`,
    `CL`, `digest_presidi`) e un riferimento storico (`/auth/token/`);
  - gli altri 2 sono lapidi di endpoint ritirati.
- **Il comando `copertura_doc_api`**, da ritoccare:
  - riconosce come esempio solo le cifre e gli uuid;
  - conta come coperta una nota che dice «queste rotte non sono documentate».
    È il verso permissivo.

---

## 5. Vendite

Verificata il 2026-10-20 con lo stesso metodo, in 6 gruppi di sotto-risorsa.
I difetti trasversali di §2.1 ci sono quasi tutti, soprattutto i punti 2, 4 e 5.
I possibili difetti di codice sono in §3, dal punto 12 al 22.

| Gruppo | ALTE | Pagine messe peggio |
| --- | --- | --- |
| approvazioni-prezzo / commesse / contratti | 3 | `api_contratti` (BA/istanza oggi modificabili in bozza, whitelist `order_by`), `api_commessa_attivita` (`count` è il totale) |
| dashboard / ddt | 4 | `api_ddt` (filtri `stato_codice_interno`/`data_a`, `utility_id` → 400), `api_dashboard_competenza`, `api_dashboard_backlog` (`ritardo_giorni`) |
| famiglie / fatturazione / fatture / fondi / giornale / iva | 0 | `api_fatturazione` (`lotti[]` su numera, status di `…_INCOERENTE` 422), `api_fattura_dettaglio` (`rettifiche`) |
| listini / lookup / lotti / pipeline / pricing / promo / registri | ~9 | `api_listini` (paginazione, `emittente_soggetto_ruolo_id` obbligatorio, rotta bundle inesistente), `api_lotto_fatture_list`, `api_lotto_segnalazioni_summary`, `api_lotto_task_runs`, reset del lotto (semantica cambiata) |
| eccezioni-offerta / offerte / ordini | 3 | `api_offerte` (`solo_ultima_revisione`, envelope lista e revisioni), `api_ordini` (whitelist, `iva_id` scartato) |
| preventivi / resi / righe | 6 | `api_preventivi` (`solo_ultima_revisione`, paginazione, revisioni, `fatturazione_immediata` all'accettazione, whitelist componente) |

Fra gli errori ricorrenti, gli status sono spesso scritti 422 dove la classe dà
400 o 409. In più, varie POST che sono letture dichiarano «LETTURA basta» ma
chiedono TUTTO, perché manca `post_accesso="view"`.

**Rotte senza pagina (vendite):**

- `commesse/<id>/registro/`;
- prelievi DDT;
- rientri, `chiudi-riconsegna` e `riapri-riconsegna` dei resi;
- componenti delle eccezioni d'offerta e `preview-componenti/`;
- `offerte/<id>/contratto-sovrapposto/`;
- `ordini/form-defaults/`;
- `preventivi/da-pratica/<id>/stato/`, `preventivi/<id>/riepilogo-iva/`,
  `DELETE preventivi/<id>/`;
- lotti: `documenti/escludi/`, `riporta-a-draft/`, `segnalazioni/rows/`,
  `mensile/` e gli export;
- `pricing/diagnose/`;
- `DELETE listini/.../bundle/<padre_id>/`.

Le `…/righe/lista/export/` sono invece coperte in modo generico da
`api_righe_documento.md`.

---

## 6. Residui di backend emersi correggendo la doc (2026-10-20) — ✅ chiusi il 2026-10-21, vedi 🔴 B

La doc descrive il codice com'è; questi punti sono difetti del codice, da decidere
o correggere:

1. **Date ancora ASC**, contro la regola di §3.3, perché la direzione e' forzata a
   monte del BB: lista ed export lotti (`_parse_lotti_query`: `order_dir or "asc"`),
   fatture del lotto (`sort_dir` default `"asc"`), lista attivita' di commessa (il
   service passa `order_dir="asc"`).
2. **Chiavi fuori contratto ancora scartate**: creazione emittente fiscale, PATCH di
   geo e indirizzi, PATCH della pratica.
3. **`{"attivo": null}` disattiva un indirizzo** (`GeoService.update_indirizzo`:
   `optional_bool` con default False).
4. **`dry_run` del cambio stato versione listino** (`listini_service.py`): `is True`,
   una stringa `"true"` vale false senza 400.
5. **PUT profilo reparto**: le voci di `aree`/`azioni` non sono validate, una chiave
   mancante e' un 500 (gemello degli override operatore, corretti in §3.1).
6. **Schemi OpenAPI che non coincidono col codice**: `ApiTemplateList`/`ApiAssetList`
   (`page`/`page_size`), `DocumentoGenera` e `ApiTemplateList.post` (201 invece di 200),
   la request di `ApiTemplatePersonalizza` (2 campi su 5), `order_by` di `views_ordini`,
   e i dieci lookup di `core/api/views_lookup.py` (§2.1.4).
7. Minori: docstring di `ApiLottoGruppiList` superata («elenco vuoto», ora 404); il
   motivo `PERMESSO_MANCANTE` della coda approvazioni e' irraggiungibile.
