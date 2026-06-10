# Brief BE — Pratica `PREVENTIVI` (handler `vendita.push_preventivo`)

> **Tipo documento**: brief backend (Django). Prerequisito: deliverable DB del
> [brief-db-pratica-preventivi.md](../work-done/brief-db-pratica-preventivi.md) +
> [brief-db-commesse-transizioni-stati.md](../work-done/brief-db-commesse-transizioni-stati.md).
> Coerente con [feedback_be_fe_attende_prerequisiti_db]: **non** anticipare codice
> che dipende da oggetti DB non ancora consegnati.
> [brief-db-pratica-preventivi.md](../work-done/brief-db-pratica-preventivi.md) — **✅ CONSEGNATI
> e applicati (2026-06-08)**: seed catalogo, `handler_params` (JSONB, **nessuna**
> tabella `config.modalita_fatturazione`), `fn_log_evento_dominio`, GRANT, codici
> errore, motore prerequisiti esito-aware, macchina transizioni commesse (V9). Il
> contratto pronto per l'handler è in **§0**. Coerente con
> [feedback_be_fe_attende_prerequisiti_db]: i prerequisiti DB ora ci sono, il BE può partire.
>
> **Data**: 2026-06-06 · **Stato**: pronto, riscontri di codice risolti
>
> **Decisione di prodotto (Tid)**: politica immediata/differita **in
> configurazione** (`handler_params`), non scelta dall'operatore al runtime.

---

## 0. Contratto DB verificato (analisi push 2026-06-08)

Tutti i prerequisiti DB sono **consegnati e applicati**. Oggetti reali che
l'handler userà (verificati contro changelog):

| Oggetto DB | Identità reale | Uso BE |
|---|---|---|
| `tipi_prestazione` | `9002 PREVENTIVI_IMMEDIATA`, `9003 PREVENTIVI_DIFFERITA` | creazione pratica |
| `template_flussi` CONFERMA | `9004` (IMM., `handler_params {"modalita_fatturazione":"IMMEDIATA"}`), `9008` (DIFF., `"DIFFERITA"`), entrambi `handler_id=9001` | dispatch |
| `handler_flussi` | `9001 handler_key='vendita.push_preventivo'` | **chiave `HANDLER_MAP`** |
| prerequisiti esito-aware | catena 10→20→30→40 con `esito_richiesto='POSITIVO'`; fn `fn_check_prerequisiti_flusso` esito-aware; guard `COMPLETATO⇒esito NOT NULL` | §8.3/§8.4 |
| `pratiche.fn_log_evento_dominio(p_pratica_id, p_flusso_id, p_tipo_evento text, p_meta jsonb DEFAULT '{}') RETURNS bigint` | mappa `azione/dettaglio`, `origine='HANDLER'`, forza `DOMINIO_*` | C5 |
| `vendite.fn_approva_commessa_attivita`, `vendite.fn_cambia_stato_commessa` | macchina commesse (✅) | C8 |
| codici errore | `474` PARAM_MODALITA, `475` COMPETENZA_RICHIESTA, `476` PREVENTIVO_GIA_PUSHATO; `473` COMMESSA_NESSUNA_RIGA_APPROVATA | mappatura `ErrorManager` |
| GRANT `competenze_flussi` | applicato | coda lavoro |

> ⚠ **`config.modalita_fatturazione` NON esiste** (decisione modeling): la
> validazione di `modalita_fatturazione` è **in codice** (C4). Lo confermano i
> seed (`handler_params` JSONB) e l'assenza della tabella.

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

| Elemento                                                                                                  | Stato reale                                                                                    | File                                                                 |
| --------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `BaseFlussoHandler` (Protocol) `execute(flusso_id, pratica_id, meta, handler_params)->dict`               | **Esiste**                                                                                     | `apps/pratiche/services/handler_registry.py:14`                      |
| `HANDLER_MAP`                                                                                             | **Esiste, vuoto**                                                                              | `handler_registry.py:32`                                             |
| `dispatch_handler(flusso_id)` (lookup handler_key + params, instanzia, `execute`)                         | **Esiste, NON auto-wired**                                                                     | `apps/pratiche/services/pratiche_service.py:338`                     |
| Transizioni flusso (`avvia_flusso`, `completa_flusso`, `cambia_stato_flusso`)                             | **Esistono**                                                                                   | `pratiche_service.py:252-314`                                        |
| `push_a_commessa(preventivo_id)` → `pr_run_commesse_push_one(sorgente_codice='PREVENTIVO', sorgente_uid)` | **Esiste**                                                                                     | `apps/vendite/services/preventivi_service.py`, `commesse_service.py` |
| Pattern RPC fn DB (`cursor.execute("SELECT vendite.fn_...(p_x => %s)")`)                                  | **Esiste**                                                                                     | `apps/vendite/db/commesse_repository.py`                             |
| `log_evento_dominio` / scrittura giornale da Python                                                       | fn DB **CONSEGNATA** (`pratiche.fn_log_evento_dominio`, §0); wrapper Python **da creare** (C5) | DB ✅ / BE —                                                          |
| `apps/vendite/handlers/`                                                                                  | **NON esiste** (da creare)                                                                     | —                                                                    |
| `ErrorManager.require(cond, code=, message=)` → `ServiceError` → envelope DRF                             | **Esiste**                                                                                     | `apps/core/services/error_manager.py:19`, `service_errors.py`        |
| `PayloadValidator` (whitelist chiavi, estrazione tipata)                                                  | **Esiste**                                                                                     | `apps/core/services/payload_helpers.py:60`                           |

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
DIFFERITA}` — **set definito in codice** (la tabella `config.modalita_fatturazione`
**non esiste**, decisione modeling: il valore vive in `handler_params` JSONB e si
valida in codice). Fuori set o assente →
`E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA` (codice DB id 474). Mai
`KeyError` grezzo.

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

Le funzioni del [brief commesse](../work-done/brief-db-commesse-transizioni-stati.md) (✅
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

### C7 — Riconciliazione politica sul percorso pratica → ✅ IMPLEMENTATO (c7-2)

Il push esistente prende `fatturazione_immediata`/`competenza` dal preventivo.
Sul percorso pratica **la config è autorevole**. **Scelta finale: c7-2** —
l'handler scrive `fatturazione_immediata` + `competenza_mese` **sul preventivo**
(`update_preventivo`) **prima** del push; la pipeline esistente li propaga a
testata/righe commessa senza modifiche.

**Inversione rispetto alla raccomandazione iniziale (c7-1), giustificata da due
verifiche di codice (2026-06-08)**:

1. `fatturazione_immediata` e `competenza_mese` sono **colonne di testata di
   `vendite.preventivi`**, già scritte all'accettazione
   ([preventivi_service.py:572-577](../../../backend/apps/vendite/services/preventivi_service.py#L572))
   e lette da `fn_list_preventivi_da_pushare`. Scriverle è il pattern esistente.
2. **Nessun trigger di immutabilità** su `vendite.preventivi` blocca l'UPDATE di
   un preventivo `ACCETTATO` (solo norm/default/guard-transizione/scope).

→ c7-2 **non tocca il path di push condiviso** (niente threading attraverso
`BaseSourceHandler`/orchestratore, usato anche dal cron batch): blast radius
molto minore di c7-1. Sul percorso pratica non è un side-effect occulto: il
dialog di accettazione (FE F1) non chiede quei campi, quindi la scrittura
dell'handler è la **prima e unica** scrittura autorevole. §8.6 (c7-1) resta
documentato come alternativa scartata.

---

## 4. Idempotenza (riuso, non riscrittura)

L'idempotenza è **già garantita** a valle:
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
        else E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA   # (codice DB id 474)

 2. preventivo_id = meta["preventivo_id"]
    carica preventivo; verifica stato == ACCETTATO (id 4)

 3. competenza:
      IMMEDIATA → mese corrente; fatturazione_immediata = true
      DIFFERITA → meta["competenza_fatturazione"]
                  else E_VENDITA_COMPETENZA_RICHIESTA           # (id 475)
                  fatturazione_immediata = false

 4. idempotenza alta: se commessa già esiste per questo preventivo
        (commesse_sorgenti / giornale DOMINIO_COMMESSA_CREATA)
        → riconosci e NON ricreare. Vedi §8.2 (idempotenza step-level):
          se commessa esiste ma NON è ancora PRONTA_FATTURAZIONE, riprendi
          da dove serve; se già completata → E_VENDITA_PREVENTIVO_GIA_PUSHATO  # (id 476)

 5. report = pr_run_commesse_push_one(            # NON push_a_commessa (vedi §8.1)
              sorgente_codice='PREVENTIVO',
              sorgente_uid=preventivo_id,
              fatturazione_immediata=<step 3>,    # param DA AGGIUNGERE (§8.6)
              competenza_mese=<step 3>)           # param DA AGGIUNGERE (§8.6)
    # destinazione FISSA = commessa diretta (no split natura in questo brief — §9)

 6. fn_approva_commessa_attivita(commessa_id, NULL, user)   # righe → APPROVATA (idemp.)

 7. fn_cambia_stato_commessa(commessa_id, 'PRONTA_FATTURAZIONE', user)
    # guard DB: ≥1 riga APPROVATA+NON_EMESSA (E_COMMESSA_NESSUNA_RIGA_APPROVATA id 473)
    # idempotenza: se già PRONTA, NON richiamare (PRONTA→PRONTA non in matrice → §8.2)

 8. pratiche_sorgenti:
      upsert (pratica_id, PREVENTIVO, preventivo.uid, ROOT)   # idempotente
      upsert (pratica_id, COMMESSA,  commessa_id,   COLLEGATO)

 9. preventivo → EVASO (id 10)   # transizione ESPLICITA nell'handler, SENZA
    # try/except che ingoia (a differenza di push_a_commessa, §8.1). Non riusare
    # push_a_commessa proprio per non ereditare il swallow.

10. giornale (fn DB pratiche.fn_log_evento_dominio, §0):
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

| ID    | Test                                                                           | Atteso                                                                                                                     |
| ----- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| BE-T1 | dispatch su `CONFERMA` `IMMEDIATA`, preventivo ACCETTATO                       | commessa con `fatturazione_immediata=true`, righe `competenza_mese=mese corrente`; sorgenti agganciate; preventivo `EVASO` |
| BE-T2 | `DIFFERITA` con `meta.competenza_fatturazione`                                 | commessa `fatturazione_immediata=false`, `competenza_mese=mese scelto`                                                     |
| BE-T3 | `DIFFERITA` senza competenza                                                   | `E_VENDITA_COMPETENZA_RICHIESTA`, nessuna commessa                                                                         |
| BE-T4 | `handler_params.modalita_fatturazione` ignota                                  | `E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA`                                                                           |
| BE-T5 | doppio dispatch sullo stesso preventivo                                        | seconda volta `E_VENDITA_PREVENTIVO_GIA_PUSHATO`, **nessuna** commessa duplicata                                           |
| BE-T6 | giornale                                                                       | `DOMINIO_COMMESSA_CREATA` + `DOMINIO_PREVENTIVO_EVASO` con meta corretto                                                   |
| BE-T7 | wiring dispatch                                                                | entrando in `IN_CORSO` su flusso con `handler_id`, l'handler parte; su flusso senza handler, no-op                         |
| BE-S1 | smoke E2E (idempotente, cleanup proattivo — [feedback_smoke_test_idempotenti]) | crea pratica → flussi → accetta preventivo → CONFERMA → commessa emittibile, pratica CHIUSA                                |

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

**Decisione finale (Tid 2026-06-08): M2 — il completamento del flusso GUIDA
l'accettazione.** L'operatore completa `APPROVAZIONE_CLIENTE` (POSITIVO/NEGATIVO)
dalla dashboard; il BE, nella **stessa transazione**, su POSITIVO porta il
preventivo collegato a `ACCETTATO`. La policy di fatturazione è **neutra** qui
(`False`/mese corrente): l'autorità sul percorso pratica è l'handler a `CONFERMA`
(c7-2), non l'accettazione.

Perché M2 (vs M1 = accept guida il flusso): è l'azione naturale nel contesto
pratica, **non tocca** il dialog di accettazione standalone (percorso autonomo
invariato), e la direzione delle dipendenze resta `vendite→pratiche`.

**✅ IMPLEMENTATO** (BE):
- `preventivi_service.completa_approvazione_da_flusso(preventivo_id, *, flusso_id,
  esito, note_esito, user)` — `@transaction.atomic`: `completa_flusso` (pratiche)
  + su POSITIVO `cambia_stato(ACCETTATO, fatturazione neutra)`. Import lazy
  `pratiche_service` (vendite→pratiche).
- endpoint `POST /api/v1/vendite/preventivi/<id>/approvazione-flusso/`
  (`ApiPreventivoApprovazioneFlusso`), body `{flusso_id, esito, note_esito}`. La
  FE passa entrambi gli id (ha il contesto), niente risoluzione cross-schema.
- NEGATIVO: solo completamento flusso (preventivo resta EMESSO) in v1.

→ **FE**: per `APPROVAZIONE_CLIENTE` di una pratica `PREVENTIVI`, la FE chiama
questo endpoint invece del generico `/flussi/<id>/stato/` (vedi brief FE F1).

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

| Valore                       | Letto da                        | Usato in                                                     | Livello                      |
| ---------------------------- | ------------------------------- | ------------------------------------------------------------ | ---------------------------- |
| `row.fatturazione_immediata` | `fn_list_preventivi_da_pushare` | `cache_key` (L365) + `get_or_create_commessa(...)` (L379)    | testata                      |
| `row.competenza_dal` / `_al` | idem                            | `cache_key` (L367-368) + `get_or_create_commessa` (L381-382) | testata                      |
| `row.competenza_mese`        | idem                            | `_build_attivita_input(...)` (L449)                          | **riga** (manopola politica) |

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

## 9. Semplificazione natura v1 (gap dichiarato — verificato 2026-06-08)

Il push del 2026-06-08 ha consegnato `config.nature_vendita` (MERCE→ORDINE,
SERVIZIO_UNA_TANTUM→COMMESSA, SERVIZIO_RICORRENTE→CONTRATTO) + colonne su
`articoli` e `preventivi_righe` — **fuori dallo scope di questo brief**. Verifica
dell'impatto sull'handler:

- `preventivi_righe.natura_vendita_id` è **NULLABLE**, derivata da trigger
  (`trgfn_preventivi_righe_set_natura_vendita`, da `articoli.natura_vendita_id`),
  **nessun override operatore**;
- **nessun vincolo NOT NULL, nessun guard a CONFERMA** che richieda natura;
- i codici `E_VENDITA_RIGA_SENZA_NATURA` / `E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA`
  **non sono stati consegnati**; la pipeline di push **non** instrada per natura.

**Conseguenza v1 (consapevole)**: l'handler pusha **tutte** le righe → commessa
diretta, ignorando `natura_vendita_id`. Una riga `SERVIZIO_RICORRENTE` (che il
modello §11.0.1 dichiara "errore in preventivo") finirebbe **silenziosamente in
commessa**, perché il guard che la bloccherebbe non esiste ancora.

**Decisione**: si lascia come **gap dichiarato di v1** (coerente con "destinazione
fissa = commessa, no split natura"). Lo split per natura + i guard
(`E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA`, ecc.) sono materia del **brief natura
separato**, quando il DB esporrà i guard. L'handler v1 **non** li anticipa
(eviterebbe di duplicare a mano una validazione che il modello vuole a DB).

---

## 7. Domande aperte BE — tutte chiuse

1. ~~**C3** dispatch automatico vs esplicito~~ → **automatico su `IN_CORSO`**,
   confluito nella transazione unica §8.2.
2. ~~**C7** override policy~~ → **CHIUSO** (§8.6: 3 punti injection in Python).
3. **C2** registrazione handler cross-app (lazy import in `vendite/apps.py:ready()`)
   — pattern da fissare in apertura codice (è il primo handler, fa giurisprudenza).
4. ~~**§4** ri-push~~ → da osservare in implementazione: mappare l'eventuale
   unique-violation a `E_VENDITA_PREVENTIVO_GIA_PUSHATO` (id 476).
5. ~~**DB V9** emittibilità commessa~~ → **CHIUSO** (macchina commesse consegnata,
   §0/C8).
6. ~~**§8.1-8.6**~~ → tutti **CHIUSI** (verificati/decisi). ~~§8.3~~ accoppiamento
   accettazione↔flusso e ~~§8.5~~ `p_user`: decisi (BE atomico, param esplicito).

Residuo reale per l'implementazione: solo **C2** (pattern registrazione) e la
verifica runtime di §8.4 (grep `completa_flusso`/`cambia_stato` per il vincolo
`COMPLETATO⇒esito`).

---

*Brief BE — Pratica PREVENTIVI / handler vendita.push_preventivo — ZeroERP
(2026-06-06, rev. critica 2026-06-08).*
