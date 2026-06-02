# Piano BE/FE — Attivazione RLS scope Emittente Fiscale (operatori)

> **Destinatari**: backend agent (Python/Django), frontend (Vue). **Branch**: `dev/backend-tid`.
> **Origine**: [analisi-attivazione-rls-operatori.md](analisi-attivazione-rls-operatori.md) (decisioni §11) + brief DB gemello (DB-side completo) [analisi-attivazione-rls-db.md](analisi-attivazione-rls-db.md).
> **Natura**: piano **dettagliato** con prerequisiti DB espliciti per ogni stream. Le sigle `C#/R#/§#` rimandano all'analisi.
> Convenzione: `[VERIFICATO]` su codice; `[DA CONFERMARE]` = riga/firma da ricontrollare prima di toccare.

---

## 0. Mappa degli stream e dipendenze

| Stream | Cosa | Dipende da DB? | Stato |
|---|---|---|---|
| **A — Fix R-GUC** | reset GUC per-richiesta, fail-closed | **No** (BE puro) | **✅ FATTO 2026-06-02** (gate per l'`ENABLE` sbloccato) |
| **B — Consolidamento scope read-side** | `get_emittenti_ids` → canonica guarded | Sì: canonica guarded (consegnata) | **✅ FATTO 2026-06-02** |
| **C — FE robustezza** | gestione 404 IDOR + verifica liste filtrate | Sì: RLS attiva (già ENABLE) | ✅ **BE no-op + FE FATTO 2026-06-02** (drawer 404→toast+chiusura); resta solo smoke runtime |

> **Stato 2026-06-02:** Stream A e B implementati su `dev/backend-tid` (test verdi). Restano:
> - (a) test d'integrazione leak GUC sotto pool concorrente [follow-up];
> - (b) ✅ **RISOLTO** — `parameter_repository.get_emittente_fiscale_id_for_user` riscritto (soluzione 3) per leggere la whitelist **direttamente** da `config.user_emittenti_fiscali` (1:1, no guard di scope) anziché via la legacy: comportamento SUPER_ADMIN preservato (lavora sul proprio emittente). **Nessun lettore Python residuo** della legacy `script.fn_get_emittenti_scope` → **può essere dismessa lato DB** [brief DB];
> - (c) Stream C dopo l'`ENABLE` Ondata 1.

Ordine logico: **A subito** (sblocca l'`ENABLE` lato DB) → **B** quando la canonica è pronta → **C** durante/dopo l'attivazione RLS.

---

## 1. Stream A — Fix R-GUC (priorità massima, BE puro)

> **✅ IMPLEMENTATO 2026-06-02** (`dev/backend-tid`). Vedi `jwt_audit_middleware.process_request` + costanti `JWT_IDENTITY_GUCS`/`JWT_GUC_RESET_SQL` in `jwt_audit_authentication.py`. Il testo sotto resta come spec di riferimento.

**Problema** (§11.1, `[VERIFICATO]`): i 5 GUC d'identità sono **session-scoped** (`set_config(..., is_local=false)`) e `CONN_MAX_AGE=600` tiene vive le connessioni. Oggi il reset esiste ma è su `process_response` (fine richiesta) ed è best-effort: se non gira (eccezione a valle/crash/ritorno al pool) i GUC sopravvivono → con RLS attiva una richiesta eredita lo scope di quella precedente sulla stessa connessione (**leak silenzioso**, modo di fallire = "vede troppo"). Il commento in codice assume `CONN_MAX_AGE=0`, assunzione **già falsa**.

**Decisione (§11.1)**: reset **all'inizio** di ogni richiesta, **incondizionato**, **fail-closed**. (Transaction-local scartato: richiederebbe `ATOMIC_REQUESTS=True` globale, troppo invasivo.)

### 1.1 Modifiche

**File**: [backend/apps/core/middleware/jwt_audit_middleware.py](../../../backend/apps/core/middleware/jwt_audit_middleware.py) (reset oggi in `process_response`) + [backend/apps/core/api/jwt_audit_authentication.py](../../../backend/apps/core/api/jwt_audit_authentication.py) (`set_jwt_gucs`, scrive i valori reali a `authenticate()`).

1. **Reset all'inizio**: azzerare i 5 GUC (`app.jwt_user`, `app.current_user_id`, `app.current_identita_id`, `app.ruolo_applicativo`, `app.soggetto_ruolo_id`) in `process_request` del middleware (gira nei Django middleware, **prima** del dispatch DRF dove `authenticate()` imposta i valori reali). Ordine garantito: reset (vuoto) → auth (valori reali per gli autenticati) → query della view.
2. **Incondizionato**: il reset NON deve dipendere dal marker `_zeroerp_jwt_guc_set`. Oggi le richieste **anonime** non toccano i GUC → ereditano quelli della richiesta precedente sulla stessa connessione. Con il reset incondizionato l'anonimo riparte sempre da vuoto (→ fail-closed).
3. **Fail-closed sul fallimento**: se la query di reset fallisce (`DatabaseError`), la richiesta deve **interrompersi** (es. 500), **non** proseguire. ⚠️ Differenza chiave rispetto all'attuale `process_response` che **inghiotte** l'errore: per il reset-at-start NON va inghiottito.
4. **`process_response`**: il reset di fine richiesta può restare come difesa secondaria oppure essere rimosso (il reset-at-start è la garanzia). Scelta del backend agent; se resta, mantenere l'elenco dei 5 GUC allineato.

> Nota: `set_jwt_gucs` resta com'è (scrive i valori reali per gli autenticati). Il fix agisce sul *prima* (azzeramento garantito), non sul *come* si popolano i valori.

### 1.2 Test
- **Unit**: due richieste simulate sulla **stessa connessione** — A autenticato (operatore EF_A) → B anonima e B' operatore EF_B; asserire che dopo il reset i GUC di B non contengono i valori di A (leggere `current_setting('app.current_user_id', true)` ecc.). Caso `DatabaseError` sul reset → la richiesta fallisce, non serve dati.
- **Concorrenza**: scenario con pool/`CONN_MAX_AGE>0` (il leak è invisibile a connessione singola). `[VERIFICATO §8 analisi]`
- Aggiornare i mock GUC esistenti (`apps/core/tests/_helpers/jwt_mock.py`) se cambia il punto di reset.

### 1.3 Prerequisiti DB
**Nessuno.** È BE puro e si può rilasciare e testare **subito**. È però **bloccante per l'`ENABLE`**: il team DB non attiva la RLS in produzione-interna prima che questo fix sia in piedi e verificato sotto pool concorrente (brief DB §13).

---

## 2. Stream B — Consolidamento scope read-side sulla canonica guarded

> **✅ IMPLEMENTATO 2026-06-02** (`dev/backend-tid`). `get_emittenti_ids` delega a `get_emittenti_pk_ids`; `parameter_repository.get_emittente_fiscale_id_for_user` legge la whitelist diretta (soluzione 3). Zero lettori Python della legacy. Il testo sotto resta come spec di riferimento.

**Problema** (B5, §2.3 `[VERIFICATO]`): `PermissionResolver.get_emittenti_ids` ([backend/apps/core/services/permissions_resolver.py](../../../backend/apps/core/services/permissions_resolver.py) `[DA CONFERMARE riga ~183]`) avvolge la funzione **legacy senza guard** `script.fn_get_emittenti_scope` — non fa fail-closed su identità OPERATORE disattivata e non ha il bypass SUPER_ADMIN coerente. È ancora usata da `documenti`, `ai_assistant`, `parameter_repository.py` `[DA CONFERMARE riga ~353]`.

### 2.1 Modifiche
1. **`get_emittenti_ids` → canonica guarded**: puntarlo alla famiglia guarded (`fn_get_emittenti_scope_pk_ids`/`_sr_ids`, o la canonica consegnata dal DB), eliminando l'uso della legacy no-guard. Semantica invariata per i chiamanti: `None` = nessuna restrizione, `[]` = nessun accesso, array = whitelist.
2. **Allineare i caller**: rivedere i punti che usano `get_emittenti_ids` (`documenti/services/_scope.py`, `ai_assistant`, `parameter_repository.py`) — verificare che la convenzione PK/SR attesa dal filtro SQL combaci con quella restituita (`get_emittenti_pk_ids` vs `get_emittenti_sr_ids`).
3. **Chiudere i buchi di lettura B1/B2** (opzionale pre-RLS, automatico post-RLS): la lista offerte (`offerte_repository.list_offerte`) e i getter by-id (`get_contratto/get_preventivo/get_offerta`) oggi **non** filtrano per EF. Con la RLS attiva il buco si chiude da solo; **finché la RLS non è attiva**, valutare se aggiungere il filtro applicativo (coerente con preventivi/contratti) per non lasciare scoperta la finestra temporale tra ora e l'`ENABLE`. `[DECISIONE]` se anticiparlo o affidarsi alla RLS.

### 2.2 Test
- Unit resolver: identità OPERATORE attiva/inattiva, SUPER_ADMIN, whitelist vuota/popolata → coerenti con la canonica DB (parità con il "test di dualità" pgTAP del brief DB).
- Regression sui caller (documenti, parametri, ai_assistant): nessuna lista che prima filtrava deve smettere di filtrare.

### 2.3 Prerequisiti DB
- **Canonica guarded + (eventuale) dismissione legacy** consegnate dal brief DB (§1, §3). Fino ad allora lo stream B non parte.
- La convenzione PK/SR delle funzioni guarded deve essere stabile (brief DB §2).

---

## 3. Stream C — FE: robustezza e verifica post-RLS

> **Stato 2026-06-02 — RLS già ENABLE (Ondata 1+2) dal team DB.**
> - **BE 3.1: ✅ GIÀ SODDISFATTO (no-op) — deviazione dal piano.** Verificato che TUTTI i caller dei getter by-id (`get_contratto`/`get_preventivo`/`get_offerta` via service + i caller interni `approvazioni_prezzo_service`, document context builders) fanno già `ErrorManager.require(row is not None, E_VENDITE_NOT_FOUND / E_PREV_NOT_FOUND / E_DOCUMENTI_NOT_FOUND)` → e quei codici mappano su **HTTP 404** (`error_policies.py`). Quindi RLS-filtrato = `None` = **stesso 404** di id inesistente: **nessuna modifica BE necessaria**. Il design "concentrico" (i service guardano sempre `None`) ha assorbito la RLS.
> - **FE 3.1: ✅ FATTO 2026-06-02.** Nuovo composable `useDrawerDetailLoad` (`frontend/src/core/composables/`): su detail-load fallito (404 inesistente/fuori scope) → toast (`notifications.detail_non_accessibile`, it+en) + **chiusura drawer**, niente drawer vuoto. Adottato da `ContrattoDrawer`, `OffertaDrawer`, `PreventiviDrawer` (i 3 target IDOR §3.1). eslint+JSON verdi. *(documenti/pratiche: composable pronto, adozione come follow-up se hanno drawer dettaglio by-id.)*
> - **3.2 liste: ⏳ verifica runtime** via smoke `backend/scripts/tests/smoke-test-rls-emittente-operatore.sh`.

Con la RLS attiva, lo scope è applicato lato DB: il FE **non deve filtrare a mano**, ma ci sono due punti da presidiare.

### 3.1 Detail-by-id fuori scope → 404 gestito (IDOR B2)
Con la RLS attiva, la `SELECT ... WHERE id = X` di un record fuori scope torna **0 righe** → il backend risponde **404** (non 500), e il FE deve gestirlo con uno stato pulito ("non trovato / non autorizzato"), non un crash o uno spinner infinito.
- **BE**: ✅ **già fatto** — i getter ritornano `None`, i caller sollevano `E_*_NOT_FOUND` → 404 (vedi nota di stato sopra).
- **FE**: `[DA CONFERMARE]` che drawer/dettaglio di contratti, preventivi, offerte, documenti, pratiche gestiscano il 404 in apertura (anche da link diretto/refresh) — è lo **stesso** 404 di un id inesistente, quindi probabile già coperto.

### 3.2 Liste: niente regressioni di conteggio/paginazione
Le liste già filtrate lato server (preventivi, contratti) mostreranno gli stessi dati; quelle **non** filtrate (offerte, B1) mostreranno **meno** righe a un operatore ristretto — è il fix voluto, ma verificare:
- conteggi/paginazione coerenti (il totale rispetta lo scope);
- nessun doppio-filtraggio anomalo dove il BE filtrava già;
- la lista offerte di un operatore ristretto ora non mostra più gli emittenti altrui.

### 3.3 Prerequisiti DB
- RLS attiva (Ondata 1/2) **oppure** lo stream B (filtro applicativo) per la parte di filtro; la gestione 404 (3.1) è indipendente e si può fare prima.

---

## 4. Sequenza consigliata e gate

1. **Stream A (R-GUC)** — subito, BE puro. **Gate**: senza, niente `ENABLE`.
2. **Stream C.1 (404 IDOR)** — in parallelo, BE+FE, indipendente.
3. **(DB consegna canonica)** → **Stream B** — consolidamento scope read-side; chiude B5; opzionale anticipo B1/B2 applicativo.
4. **(DB esegue Ondata 1 ENABLE, dopo che A è verificato)** → **Stream C.2** — verifica liste filtrate, smoke operatore EF-limitato.
5. **(DB Ondata 2)** → verifica estesa (preventivi/contratti/offerte/documenti/pratiche/ordini/billing_account).

---

## 5. Smoke e2e (a valle, idempotente)

> **✅ Script pronto 2026-06-02**: `backend/scripts/tests/smoke-test-rls-emittente-operatore.sh` (read-only → idempotente per costruzione, niente seed da pulire). Bersaglio **contratti** (la lista espone `emittente_fiscale_id`; il dettaglio→404 è la prova RLS-specifica perché `get_contratto` non ha filtro applicativo). Parametri: `SMOKE_USER`/`SMOKE_PASSWORD` (operatore con whitelist), opzionale `OUT_OF_SCOPE_CONTRATTO_ID` per il test 404. Diagnosi categorie inclusa. **Da eseguire contro un'istanza viva.**

Coerente con `feedback_smoke_test_idempotenti` (idempotenza + diagnosi categoria):
1. Seed: 2 emittenti EF_A/EF_B, 1 operatore con whitelist su EF_A, ≥1 documento per EF.
2. Login reale (endpoint JWT) → token → percorso reale `set_jwt_gucs`.
3. GET lista fatture/offerte → assert: solo EF_A, zero EF_B.
4. GET dettaglio by-id di un record EF_B → assert **404** (non 500, non 200).
5. Controprova operatore whitelist-vuota → vede entrambi.
6. **Diagnosi categoria** se fallisce: lista vuota → GUC non propagati (Stream A) o ruolo BYPASSRLS lato sbagliato; lista completa (anche EF_B) → vista definer (brief DB §8) o RLS non attiva o `zeroerp_app` BYPASSRLS; lista filtrata → verde.

> Lo smoke "non vede troppo" va eseguito **dopo** che Stream A è risolto e **sotto pool concorrente**: a connessione singola il leak cross-request resta mascherato.

---

## 6. Riepilogo prerequisiti DB per stream

| Stream | Prerequisito DB |
|---|---|
| A — R-GUC | **Nessuno** (ma è gate per l'`ENABLE`) |
| B — scope read-side | Canonica guarded consegnata; (eventuale) dismissione legacy |
| C.1 — 404 IDOR | Nessuno (gestione errore BE/FE) |
| C.2 — verifica liste | RLS attiva (Ondata 1/2) o filtro applicativo dello Stream B |

> Le decisioni di dominio sono chiuse in [analisi-attivazione-rls-operatori.md §11](analisi-attivazione-rls-operatori.md). Questo piano è la proiezione BE/FE; il brief DB gemello copre la parte database.
