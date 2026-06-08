# Brief BE — Pratica `PREVENTIVI` (handler `vendita.push_preventivo`)

> **Tipo documento**: brief backend (Django). Prerequisito: deliverable DB del
> [brief-db-pratica-preventivi.md](brief-db-pratica-preventivi.md) +
> [brief-db-commesse-transizioni-stati.md](brief-db-commesse-transizioni-stati.md).
> Coerente con [feedback_be_fe_attende_prerequisiti_db]: **non** anticipare codice
> che dipende da oggetti DB non ancora consegnati.
>
> **Data**: 2026-06-06 · **Rev. critica**: 2026-06-08 (allineamento allo split DB)
> · **Stato**: pronto, riscontri di codice risolti
>
> **Decisione di prodotto (Tid)**: politica immediata/differita **in
> configurazione** (`handler_params`), non scelta dall'operatore al runtime.
>
> **⚠ Allineamento allo split DB (2026-06-08)** — il team DB ha verificato e
> diviso il piano. Conseguenze su questo brief, recepite sotto:
>
> 1. **`config.modalita_fatturazione` RIMOSSA** → la validazione di
>    `modalita_fatturazione` è **in codice** (set `{IMMEDIATA, DIFFERITA}`), non
>    via lookup. (C4, pseudo-flow §5)
> 2. **Commessa emittibile = IMPLEMENTATO** (brief commesse, changeset
>    `20260607-01..06`): l'handler **deve** chiamare `fn_approva_commessa_attivita`
>    + `fn_cambia_stato_commessa(...,'PRONTA_FATTURAZIONE', user)`. Non è più una
>    domanda aperta → nuovo deliverable **C8** + step espliciti in §5.
> 3. **Prerequisiti esito-aware + `COMPLETATO ⇒ esito NOT NULL`** (B-PREREQ): ogni
>    `completa_flusso` deve passare un `esito`; `CONFERMA` si abilita solo dopo
>    `APPROVAZIONE_CLIENTE` `COMPLETATO`+`POSITIVO`. Vedi §8.
> 4. **Giornale**: colonne reali `azione`/`dettaglio`/`origine`; `azione` passa
>    regex `^DOMINIO_*`. (C5)
> 5. **Nuovi rischi di robustezza** (atomicità transazione, idempotenza
>    multi-step, accoppiamento accettazione↔flusso): **§8**.

---

## 1. Obiettivo BE

Registrare il **primo handler reale** del motore pratiche
(`HANDLER_MAP` oggi vuoto) e cablarne il dispatch. L'handler
`vendita.push_preventivo`, al passaggio del flusso `CONFERMA` in `IN_CORSO`:

1. valida i propri `handler_params` (politica) — Contratto handler (D-f);
2. risolve la competenza secondo la politica;
3. **riusa il push esistente** preventivo→commessa applicando la politica;
4. aggancia la pratica al preventivo (ROOT) e alla commessa (COLLEGATO);
5. scrive gli eventi di dominio nel giornale;
6. porta il preventivo a `EVASO`.

**Principio guida** ([feedback_regola_del_2_estrai_bb], analisi §2.2): l'handler
**non reimplementa** il push — delega all'orchestratore esistente
`pr_run_commesse_push_one` (livello sotto `push_a_commessa`, vedi §8.1 per il
perché non si riusa il wrapper). È un orchestratore sottile sopra il dominio.

---

## 2. Riscontri di codice (verificati)

| Elemento | Stato reale | File |
|---|---|---|
| `BaseFlussoHandler` (Protocol) `execute(flusso_id, pratica_id, meta, handler_params)->dict` | **Esiste** | `apps/pratiche/services/handler_registry.py:14` |
| `HANDLER_MAP` | **Esiste, vuoto** | `handler_registry.py:32` |
| `dispatch_handler(flusso_id)` (lookup handler_key + params, instanzia, `execute`) | **Esiste, NON auto-wired** | `apps/pratiche/services/pratiche_service.py:338` |
| Transizioni flusso (`avvia_flusso`, `completa_flusso`, `cambia_stato_flusso`) | **Esistono** | `pratiche_service.py:252-314` |
| `push_a_commessa(preventivo_id)` → `pr_run_commesse_push_one(sorgente_codice='PREVENTIVO', sorgente_uid)` | **Esiste** | `apps/vendite/services/preventivi_service.py`, `commesse_service.py` |
| Pattern RPC fn DB (`cursor.execute("SELECT vendite.fn_...(p_x => %s)")`) | **Esiste** | `apps/vendite/db/commesse_repository.py` |
| `log_evento_dominio` / scrittura giornale da Python | **ASSENTE** (solo trigger) | — |
| `apps/vendite/handlers/` | **NON esiste** (da creare) | — |
| `ErrorManager.require(cond, code=, message=)` → `ServiceError` → envelope DRF | **Esiste** | `apps/core/services/error_manager.py:19`, `service_errors.py` |
| `PayloadValidator` (whitelist chiavi, estrazione tipata) | **Esiste** | `apps/core/services/payload_helpers.py:60` |

---

## 3. Deliverable BE

### C1 — `apps/vendite/handlers/push_preventivo_handler.py`

Nuovo package `apps/vendite/handlers/` (oggi assente). Classe che implementa il
Protocol `BaseFlussoHandler`. Logica in §5. **Delega** il push a
`preventivi_service`, **non** chiama direttamente le fn commessa.

### C2 — Registrazione in `HANDLER_MAP`

`handler_registry.py`: `HANDLER_MAP["vendita.push_preventivo"] =
PushPreventivoHandler`. Primo handler reale → validare la firma del Protocol su
un caso vero.

> **Attenzione import cycle**: l'handler vive in `apps/vendite`, il registry in
> `apps/pratiche`. Per non creare dipendenza `pratiche→vendite`, registrare via
> **lazy import / registry pluggable** (es. `apps/vendite/apps.py:ready()` che
> popola `HANDLER_MAP`, oppure import differito dentro `get_handler`). Decidere
> il pattern in apertura: è il primo caso, fa giurisprudenza.

### C3 — Wiring del dispatch (oggi NON automatico)

`dispatch_handler` esiste ma **non** è invocato sul cambio stato. Serve il
trigger applicativo: quando il flusso `CONFERMA` entra in `IN_CORSO`, chiamare
`dispatch_handler(flusso_id)`. Due opzioni — **scegliere e dichiarare**:

- **(a)** dentro `avvia_flusso`/`cambia_stato_flusso`: se il nuovo stato è
  `IN_CORSO` e il template ha `handler_id`, invoca `dispatch_handler`. Automatico
  e uniforme per ogni futuro handler.
- **(b)** azione API esplicita "esegui handler" sul flusso, chiamata dalla UI.

> **Raccomandazione**: (a) — il dispatch automatico su `IN_CORSO` è il
> comportamento atteso dalla guida pratiche e rende il motore "configurabile per
> dati" senza UI dedicata. Da fare con guardia: solo se `handler_id` valorizzato.

### C4 — Validazione `handler_params` (D-f)

Validare con `ErrorManager.require`: `modalita_fatturazione ∈ {IMMEDIATA,
DIFFERITA}` — **set definito in codice nell'handler** (costante/enum Python),
**non** lookup DB (la tabella `config.modalita_fatturazione` è stata rimossa,
modeling 06-07). Fuori set o assente → `E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA`.
Mai `KeyError` grezzo. Questa è esattamente la "validazione in codice dall'handler"
prevista dalla decisione DB V10.

### C5 — Wrapper scrittura giornale di dominio

Sopra la fn DB `pratiche.fn_log_evento_dominio(p_pratica_id, p_flusso_id,
p_tipo_evento, p_meta)` (deliverable DB B-NEW): metodo repository
`PraticheRepository.log_evento_dominio(...)` + facade
`pratiche_service.log_evento_dominio(...)`. La fn DB mappa `azione=p_tipo_evento`,
`dettaglio=p_meta`, `origine='HANDLER'` (colonne reali del giornale; **non**
`tipo_evento`/`meta`). I `tipo_evento` devono rispettare il prefisso
`DOMINIO_*` (CHECK regex DB). Chiamato dall'handler per `DOMINIO_COMMESSA_CREATA`
e `DOMINIO_PREVENTIVO_EVASO`.

### C8 — Approvazione righe + transizione commessa (era V9 aperto, ora concreto)

Le funzioni del [brief commesse](brief-db-commesse-transizioni-stati.md) (✅
implementate) vanno cablate come metodi repository + chiamate dall'handler tra il
push e l'aggancio sorgenti (vedi §5):

- `vendite.fn_approva_commessa_attivita(p_commessa_id, p_righe_ids DEFAULT NULL, p_user)`
  → righe `BOZZA→APPROVATA` (NULL = tutte le `NON_EMESSA`). Idempotente.
- `vendite.fn_cambia_stato_commessa(p_commessa_id, p_nuovo_stato, p_user)` →
  testata `→PRONTA_FATTURAZIONE`. Guard DB: ammessa solo con ≥1 riga
  `APPROVATA`+`NON_EMESSA` (l'ordine delle due chiamate è vincolante: prima
  approva, poi cambia stato).

Serve threading dell'utente acting (`p_user`): vedi §8 punto 4 — `dispatch_handler`
oggi non porta lo user, va deciso come passarlo.

### C6 — Aggancio `pratiche_sorgenti` dal BE

Metodo repository che fa l'INSERT idempotente (`ON CONFLICT DO NOTHING` sulla
UNIQUE `(pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link)`):
- preventivo come `ROOT` (può già esistere se agganciato in `PREVENTIVAZIONE`);
- commessa come `COLLEGATO`.

### C7 — Riconciliazione politica sul percorso pratica (conseguenza decisione)

Il push esistente prende `fatturazione_immediata`/`competenza` dal preventivo.
Sul percorso pratica **la config è autorevole**. L'handler deve garantire che la
commessa riceva la politica da `handler_params`/`flussi.meta`, **non** dal valore
d'accettazione. Due strade — **da decidere (verifica BE)**:

- **(c7-1)** parametrizzare il push: estendere `pr_run_commesse_push_one` (+
  orchestratore + handler sorgente) con `fatturazione_immediata` +
  `competenza_mese` espliciti che **sovrascrivono** la sorgente. **Verificato
  (§8.6)**: questi parametri **oggi non esistono** — è un lavoro reale, non un
  semplice passaggio di argomenti;
- **(c7-2)** l'handler scrive `fatturazione_immediata`/`competenza` sul
  preventivo **prima** del push, così la pipeline li propaga.

> **Raccomandazione**: (c7-1) — parametri espliciti evitano di mutare lo stato
> del preventivo come effetto collaterale e tengono l'handler l'unica fonte
> autorevole. Il default dei parametri resta "leggi dalla sorgente" per non
> rompere il push autonomo. Vedi §8.6 per il punto esatto di lettura.

---

## 4. Idempotenza (riuso, non riscrittura)

L'idempotenza è **già garificata** a valle:
- `commesse_sorgenti` ha UNIQUE `(sorgente_tipo_id, sorgente_uid, ruolo_link)` →
  un preventivo non genera due commesse;
- la riga commessa è idempotente su `(commessa_id, segment_key)`.

L'handler aggiunge solo l'**errore semantico** `E_VENDITA_PREVENTIVO_GIA_PUSHATO`
quando il push è già avvenuto, in difesa-in-profondità:
- **strato alto**: prima del push, l'handler verifica nel giornale/sorgenti se
  `DOMINIO_COMMESSA_CREATA` è già presente per quel preventivo → se sì, non
  riprova e propaga l'errore parlante (Opzione 1 conservativa, §5.3.3 analisi);
- **strato basso**: la UNIQUE DB resta l'ultima linea.

> **Verifica BE**: l'orchestratore `pr_run_commesse_push_one` oggi *come* reagisce
> al ri-push (errore? no-op? report con 0 righe)? Se solleva una unique violation
> grezza, mapparla a `E_VENDITA_PREVENTIVO_GIA_PUSHATO` (vedi
> `map_integrity_error` / `ErrorManager`).

---

## 5. Pseudo-flow handler `vendita.push_preventivo`

Invocato da `dispatch_handler` quando `CONFERMA` entra in `IN_CORSO`.

```text
execute(flusso_id, pratica_id, meta, handler_params):

  # TUTTO il corpo gira in UNA transazione atomica (vedi §8.1)

 1. modalita = handler_params["modalita_fatturazione"]
    require modalita in {IMMEDIATA, DIFFERITA}   # set in codice, NO lookup DB
        else E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA

 2. preventivo_id = meta["preventivo_id"]
    carica preventivo; verifica stato == ACCETTATO (id 4)

 3. competenza:
      IMMEDIATA → mese corrente; fatturazione_immediata = true
      DIFFERITA → meta["competenza_fatturazione"]
                  else E_VENDITA_COMPETENZA_RICHIESTA
                  fatturazione_immediata = false

 4. idempotenza alta: se commessa già esiste per questo preventivo
        (commesse_sorgenti / giornale DOMINIO_COMMESSA_CREATA)
        → riconosci e NON ricreare. Vedi §8.2 (idempotenza step-level):
          se commessa esiste ma NON è ancora PRONTA_FATTURAZIONE, riprendi
          da dove serve; se già completata → E_VENDITA_PREVENTIVO_GIA_PUSHATO

 5. report = pr_run_commesse_push_one(            # NON push_a_commessa (vedi §8.1)
              sorgente_codice='PREVENTIVO',
              sorgente_uid=preventivo_id,
              fatturazione_immediata=<step 3>,    # param DA AGGIUNGERE (§8.6)
              competenza_mese=<step 3>)           # param DA AGGIUNGERE (§8.6)
    # destinazione FISSA = commessa diretta (no split natura in questo brief)

 6. fn_approva_commessa_attivita(commessa_id, NULL, user)   # righe → APPROVATA (idemp.)

 7. fn_cambia_stato_commessa(commessa_id, 'PRONTA_FATTURAZIONE', user)
    # guard DB: ≥1 riga APPROVATA+NON_EMESSA (garantito da step 6)
    # idempotenza: se già PRONTA, NON richiamare (PRONTA→PRONTA non in matrice → §8.2)

 8. pratiche_sorgenti:
      upsert (pratica_id, PREVENTIVO, preventivo.uid, ROOT)   # idempotente
      upsert (pratica_id, COMMESSA,  commessa_id,   COLLEGATO)

 9. preventivo → EVASO (id 10)   # transizione ESPLICITA nell'handler, SENZA
    # try/except che ingoia (a differenza di push_a_commessa, §8.1). Non riusare
    # push_a_commessa proprio per non ereditare il swallow.

10. giornale:
      log_evento_dominio(DOMINIO_COMMESSA_CREATA,
          meta={commessa_id, preventivo_id, competenza, modalita})
      log_evento_dominio(DOMINIO_PREVENTIVO_EVASO, meta={preventivo_id})

11. return {commessa_id, preventivo_id, modalita, competenza}
```

A valle, senza altra logica: `fn_list_commesse_emittibili(p_competenza_mese)`
includerà la commessa nel lotto giusto (mese corrente per IMMEDIATA, mese scelto
per DIFFERITA): la commessa è ora `PRONTA_FATTURAZIONE` (step 7) con righe
`APPROVATA`+`NON_EMESSA` (step 6) → soddisfa i requisiti di emittibilità.

---

## 6. Test (Django + smoke)

| ID | Test | Atteso |
|---|---|---|
| BE-T1 | dispatch su `CONFERMA` `IMMEDIATA`, preventivo ACCETTATO | commessa con `fatturazione_immediata=true`, righe `competenza_mese=mese corrente`; sorgenti agganciate; preventivo `EVASO` |
| BE-T2 | `DIFFERITA` con `meta.competenza_fatturazione` | commessa `fatturazione_immediata=false`, `competenza_mese=mese scelto` |
| BE-T3 | `DIFFERITA` senza competenza | `E_VENDITA_COMPETENZA_RICHIESTA`, nessuna commessa |
| BE-T4 | `handler_params.modalita_fatturazione` ignota | `E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA` |
| BE-T5 | doppio dispatch sullo stesso preventivo | seconda volta `E_VENDITA_PREVENTIVO_GIA_PUSHATO`, **nessuna** commessa duplicata |
| BE-T6 | giornale | `DOMINIO_COMMESSA_CREATA` + `DOMINIO_PREVENTIVO_EVASO` con meta corretto |
| BE-T7 | wiring dispatch | entrando in `IN_CORSO` su flusso con `handler_id`, l'handler parte; su flusso senza handler, no-op |
| BE-S1 | smoke E2E (idempotente, cleanup proattivo — [feedback_smoke_test_idempotenti]) | crea pratica → flussi → accetta preventivo → CONFERMA → commessa emittibile, pratica CHIUSA |

---

## 8. Punti critici emersi dalla revisione vs split DB (da chiudere prima del codice)

### 8.1 Atomicità della transazione (rischio #1) — ✅ VERIFICATO (2026-06-08)

L'handler compie più scritture in sequenza (push → approva righe → cambia stato
testata → `pratiche_sorgenti` → preventivo `EVASO` → giornale). Devono stare in
**una sola transazione atomica**. Verifica sul codice reale:

- **`pr_run_commesse_push_one` NON committa per conto proprio**:
  [commesse_service.py:156](../../../backend/apps/vendite/services/commesse_service.py#L156)
  usa un semplice `with transaction.atomic()` (no `durable`, no `commit()`
  esplicito). In Django `atomic()` è **rientrante** → annidato diventa un
  **savepoint**, partecipa alla transazione del chiamante. La paura "commit
  indipendente" **non si realizza**. L'advisory lock è session-level, rilasciato
  in `finally`: ok.
- **MA `dispatch_handler` NON è `@transaction.atomic()`**
  ([pratiche_service.py:341](../../../backend/apps/pratiche/services/pratiche_service.py#L341))
  — unico metodo del service senza decoratore. Quindi senza un atomic esterno gli
  step girano in **autocommit** (ognuno committa da sé → incoerenza).

**Decisione (verificata, non più aperta)**: l'`execute()` dell'handler **apre lui
un `with transaction.atomic()` esterno** attorno a tutto il corpo. Auto-contenuto,
indipendente da come si cabla il dispatch; il push annidato diventa savepoint e
rolla insieme al resto.

> **⚠ Conseguenza scoperta — NON riusare `push_a_commessa` as-is.**
> [preventivi_service.py:1665](../../../backend/apps/vendite/services/preventivi_service.py#L1665)
> `push_a_commessa` fa **già** la transizione `ACCETTATO→EVASO` dopo il push, in
> un `try/except DatabaseError → log e prosegue`. Due problemi dentro un atomic
> esterno: (a) lo step `EVASO` dell'handler diventa **ridondante** (doppia
> transizione `EVASO→EVASO` → errore); (b) **ingoiare un `DatabaseError` dentro
> un atomic poisona la transazione** (Django: ogni query successiva →
> `TransactionManagementError`). → L'handler **non** chiama `push_a_commessa`, ma
> orchestra al livello sotto: `pr_run_commesse_push_one` (vedi §8.6) + `EVASO`
> esplicito **senza** swallow, tutto nell'atomic dell'`execute()`.

### 8.2 Idempotenza ora multi-step → ✅ DECISO (Opz. 3+1, Tid 2026-06-08)

Problema: con più step in fila, una ri-esecuzione (doppio click / retry /
ri-dispatch) rischia di esplodere — es. `fn_cambia_stato_commessa(→PRONTA)` su una
commessa **già** PRONTA fallisce (matrice non ha `PRONTA→PRONTA`, CHECK `da≠a`).

**Decisione — transazione unica (3) + guard "già fatto" (1)**:

1. **Una sola `transaction.atomic()` avvolge l'intera CONFERMA**: flusso
   `→IN_CORSO` + `execute()` dell'handler + flusso `→COMPLETATO (POSITIVO)`. Così
   **non esiste mai un mezzo-stato**: o la CONFERMA è interamente committata o per
   niente (un crash a metà rolla tutto, §8.1). Elimina alla radice il "bordo" che
   avrebbe richiesto un replay step-level.
2. **Su fallimento dell'handler**, lo stato `ERRORE`/`SOSPESO` del flusso va
   scritto in una transazione **separata** (nel blocco `except`), altrimenti il
   rollback dell'atomic lo cancellerebbe. Pattern:
   `try: atomic{IN_CORSO + execute + COMPLETATO} except: tx_separata{flusso→ERRORE/SOSPESO + log}`.
3. **Guard "già fatto" up-front** nell'handler: se esiste già una commessa per il
   preventivo (`commesse_sorgenti` / giornale) → `E_VENDITA_PREVENTIVO_GIA_PUSHATO`
   parlante, niente retry alla cieca. È la rete per il doppio click.
4. **Anti-race**: lock di riga sul flusso (`SELECT ... FOR UPDATE`) all'inizio
   della transizione, così due click concorrenti si serializzano e il secondo
   vede `COMPLETATO` (oppure il dispatch **salta** un flusso già `COMPLETATO`).

Niente logica di "riprendi a metà" (Opz. 2 scartata): non serve, perché (1) rende
impossibile il mezzo-stato.

### 8.3 Accoppiamento accettazione preventivo ↔ flusso `APPROVAZIONE_CLIENTE` → ✅ DECISO (Tid 2026-06-08)

Con i prerequisiti **esito-aware** (DB B-PREREQ), `CONFERMA` si abilita solo se
`APPROVAZIONE_CLIENTE` è `COMPLETATO` con `esito='POSITIVO'`. La decisione DB V15
dichiara che "completare `APPROVAZIONE_CLIENTE` POSITIVO" e "preventivo→`ACCETTATO`"
sono **la stessa azione del dialog**.

**Decisione — lo fa il BE, nella stessa azione di accettazione, atomico**: lo
**stesso** metodo di servizio che porta il preventivo a `ACCETTATO` deve anche
completare il flusso `APPROVAZIONE_CLIENTE` con esito `POSITIVO` (e `NEGATIVO` sul
rifiuto), nella **stessa transazione**, quando il preventivo è collegato a una
pratica `PREVENTIVI`.

Perché:
- tiene vera e **atomica** l'equazione "accetto = completo il flusso": non possono
  divergere;
- il FE resta sottile: mostra il dialog esistente, chiama **un** endpoint (vedi
  brief FE F1) — nessuna orchestrazione FE che si desincronizza;
- un passo FE separato lascerebbe la finestra "preventivo `ACCETTATO` ma flusso
  aperto" → `CONFERMA` bloccata e operatore confuso.

⚠ Implementazione: il BE deve **risalire** dal preventivo alla pratica (via
`pratiche_sorgenti` ROOT) e individuare il flusso `APPROVAZIONE_CLIENTE` da
completare. Caso limite: più pratiche `PREVENTIVI` collegate → in v1 è di fatto
una, ma mettere un **guard sull'ambiguità** (errore parlante, non scelta
silenziosa).

### 8.4 `COMPLETATO ⇒ esito NOT NULL`: grep dei call site

Il nuovo vincolo DB rifiuta un flusso `COMPLETATO` senza `esito`. Prima di
attivarlo: **grep di tutti i `completa_flusso` / `cambia_stato_flusso`** in
backend + pgTAP e garantire che passino sempre un `esito`
([feedback_guard_breaks_existing_tests]). Possibile breakage di flussi/test
esistenti.

### 8.5 Threading dello user (`p_user`) → ✅ DECISO (Tid 2026-06-08)

`fn_cambia_stato_commessa` e `fn_approva_commessa_attivita` vogliono `p_user`, ma
`dispatch_handler(flusso_id)` non porta l'utente acting.

**Decisione — parametro esplicito, niente utente "di sistema"**: estendere
`dispatch_handler(flusso_id, *, user)`; chi avvia la transizione del flusso (il
service, che ha `request.user`) passa l'utente; l'handler lo inoltra alle fn DB.

Perché:
- l'attore che conta per l'**accountability** è l'operatore che ha mandato avanti
  il flusso, non un finto `SYSTEM`. Che sia automazione lo dice già
  `origine='HANDLER'` nel giornale;
- esplicito = **testabile** (un contesto request-local "magico" è più fragile);
- si incastra con §C3/§8.2: se il dispatch parte dentro il service di transizione
  (atomico), l'utente è già a portata di mano.

### 8.6 La policy NON è parametrizzabile sul push (verificato 2026-06-08)

`push_a_commessa(preventivo_id)`
([preventivi_service.py:1619](../../../backend/apps/vendite/services/preventivi_service.py#L1619))
e `pr_run_commesse_push_one(sorgente_codice, sorgente_uid, dry_run)`
([commesse_service.py:119](../../../backend/apps/vendite/services/commesse_service.py#L119))
**non hanno** parametri `fatturazione_immediata`/`competenza_mese`.

**Punto di lettura esatto (verificato 2026-06-08)** — i valori sono **intrinseci
di riga**: arrivano da `fetch_pushable_rows` → `fn_list_preventivi_da_pushare`
come campi del `PushableRow`, e l'handler li consuma in
[commesse_source_handlers.py](../../../backend/apps/vendite/services/commesse_source_handlers.py):

| Valore | Letto da | Usato in | Livello |
|---|---|---|---|
| `row.fatturazione_immediata` | `fn_list_preventivi_da_pushare` | `cache_key` (L365) + `get_or_create_commessa(...)` (L379) | testata |
| `row.competenza_dal` / `_al` | idem | `cache_key` (L367-368) + `get_or_create_commessa` (L381-382) | testata |
| `row.competenza_mese` | idem | `_build_attivita_input(...)` (L449) | **riga** (manopola politica) |

**Mappa injection per c7-1** (override uniforme su tutto il push del preventivo):

1. **Threading**: aggiungere `override_fatturazione_immediata` +
   `override_competenza_mese` lungo `pr_run_commesse_push_one` →
   `CommessaPushOrchestrator.run` → `HandlerPreventivi.run` → `_process_rows`
   ([L324](../../../backend/apps/vendite/services/commesse_source_handlers.py#L324),
   già predisposto con kwargs `competenza_mese`/`billing_account_id`/`limit` non
   passati da `run`).
2. **Testata**: applicare l'override su `fatturazione_immediata` (+ `competenza_dal/_al`
   coerenti col mese) nella `get_or_create_commessa` (L374-383) **e** nel
   `cache_key` (L360-369), altrimenti la cache commessa diverge.
3. **Riga**: applicare l'override su `competenza_mese` in `_build_attivita_input`
   (L449) — è il valore che `fn_list_commesse_emittibili` filtra.

**Raccomandazione**: applicare l'override **in Python** a livello `_process_rows`,
**senza** toccare `fn_list_preventivi_da_pushare` (blast radius minimo; l'handler
resta l'unica fonte autorevole, default invariato = "leggi dalla riga"). C7 passa
così da "lavoro da stimare" a **3 punti precisi** + threading kwargs. ✅ nodo chiuso.

---

## 7. Domande aperte BE (prima del piano)

1. **C3**: dispatch automatico su `IN_CORSO` (a) vs azione esplicita (b)?
   (raccomandato a).
2. **C7**: override politica via parametri push (c7-1) vs scrittura su preventivo
   (c7-2)? Dipende da *dove* la pipeline legge `fatturazione_immediata`/
   `competenza` oggi (verifica preliminare).
3. **C2**: pattern di registrazione handler cross-app per evitare ciclo
   `pratiche→vendite` (lazy import in `vendite/apps.py:ready()`?).
4. **§4**: comportamento attuale dell'orchestratore sul ri-push (per il mapping
   a errore semantico).
5. ~~**§8.1 atomicità**~~ → **CHIUSO** (verificato): handler apre atomic esterno;
   non riusare `push_a_commessa` (swallow-EVASO).
6. ~~**§8.2 idempotenza**~~ → **CHIUSO** (Opz. 3+1): transazione unica
   flusso+handler + guard "già fatto" + lock anti-race.
7. ~~**§8.3**~~ → **CHIUSO**: completa `APPROVAZIONE_CLIENTE` il BE dell'azione
   accetta-preventivo, atomico.
8. ~~**§8.5**~~ → **CHIUSO**: `p_user` parametro esplicito sul dispatch.
9. ~~**§8.6**~~ → **CHIUSO**: override policy in Python a `_process_rows` (3 punti).

**Residuo aperto (non bloccante)**: C3 (dispatch automatico vs esplicito —
raccomandato automatico, ora confluisce nella transazione unica §8.2), C2 (pattern
registrazione handler cross-app), §4 (comportamento orchestratore sul ri-push, per
il mapping errore). Decisioni minori, chiudibili in apertura piano.

---

*Brief BE — Pratica PREVENTIVI / handler vendita.push_preventivo — ZeroERP
(2026-06-06, rev. critica 2026-06-08).*
