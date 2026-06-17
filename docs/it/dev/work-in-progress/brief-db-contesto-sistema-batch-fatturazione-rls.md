# Brief DB — Contesto di SISTEMA per il batch fatturazione (prerequisito RLS operatori)

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> **Priorità**: 🟠 ALTA **ma temporizzata** — **bloccante PRIMA di rendere *enforced* la
> RLS operatori**, non prima. Oggi la RLS è dormiente → il batch funziona; quindi non c'è
> urgenza finché la RLS resta dry-run, ma va applicato **nello stesso momento** in cui si
> attiva/forza la RLS, altrimenti il batch notturno si blocca.
> **Data**: 2026-06-16 · **Stato**: 🟡 **Opzione B scelta (Tid, 2026-06-16)** — BE
> predisposto (forward-compatible); **DB da applicare con l'attivazione RLS**.
>
> **Decisione**: **Opzione B** (sentinel `app.ruolo_applicativo='SISTEMA'` + policy
> permissive di sistema). **BE già implementato** (innocuo finché la RLS è dormiente):
> costante `RUOLO_APPLICATIVO_SISTEMA`, e `run_fatturazione_batch` stabilisce/ripristina
> il contesto di sistema sulla connessione (`_system_db_context`). **Resta al team DB**:
> creare le policy `_sistema` (§4 B) sulle tabelle del perimetro, **contestualmente** al
> FORCE/enforce della RLS operatori.
>
> **Origine**: [analisi-commesse-stato-e-sviluppi.md](analisi-commesse-stato-e-sviluppi.md)
> §9 + §10.4 F4 (caveat RLS). Coordinare con
> [analisi-attivazione-rls-operatori-be-fe.md](../work-done/analisi-attivazione-rls-operatori-be-fe.md)
> e [db-brief-rls-ondata2-insert-bloccati.md](../work-done/db-brief-rls-ondata2-insert-bloccati.md).

---

## 1. Contesto

La RLS operatori filtra il ciclo attivo per emittente via GUC di sessione: le policy
sono keyed su `current_setting('app.ruolo_applicativo', true) = 'OPERATORE'` + whitelist
emittente (pattern `rls_<tabella>_ef_whitelist`, USING + WITH CHECK — vedi ondata2). Il
ruolo applicativo `zeroerp_app` è **`NOBYPASSRLS`**.

Il **driver di fatturazione** gira come **management command** (`run_fatturazione_batch`,
cron/systemd — Fase 4), **senza JWT e senza GUC d'identità**: è un **processo di
sistema** che deve operare su **tutti** gli emittenti (la numerazione è per emittente).

**Perché oggi funziona**: la RLS è **dormiente/dry-run** (le tabelle hanno policy ma non
sono *enforced* sul percorso del batch — `NO FORCE` + owner, o RLS non ancora attiva).
Senza GUC, il batch passa.

## 2. Problema (futuro, all'attivazione RLS)

Quando la RLS operatori sarà *enforced* (FORCE / attivazione piena), il batch — che **non
è un operatore** e non setta `app.ruolo_applicativo` — non soddisferà **nessuna** policy
→ **default-deny**:

- `SELECT` vuoti sulla discovery/lettura (lotti, fatture);
- `INSERT`/`UPDATE` negati (`new row violates row-level security policy`) su lotto e fatture.

→ Il batch notturno si bloccherebbe silenziosamente. Serve un **contesto di sistema**
che dia al batch visibilità/scrittura **piena** (tutti gli emittenti), distinto dallo
scope per-emittente degli operatori.

## 3. Tabelle nel perimetro del batch (RLS-enabled)

Scrittura del percorso lotto→fatture: **`vendite.fatturazione_lotti`**, **`vendite.fatture`**,
**`vendite.fatture_scadenze`** (+ eventuali figli `fatture_righe`/`fatture_fondi`/
`fatture_contabili` se RLS-enabled — **da confermare lato DB**: la policy di sistema deve
coprire **ogni** tabella scritta dalla pipeline, altrimenti l'INSERT fallisce sulla prima
non coperta). Letture discovery: `vendite.commesse` / `attivita_fatturabili` (verificare se
RLS-enabled; oggi non risultano nel perimetro ondata2).

## 4. Opzioni (decisione DB)

### Opzione A — Ruolo dedicato `BYPASSRLS` per il batch
- Creare un ruolo es. `zeroerp_batch` con `BYPASSRLS` + grant necessari; il cron usa una
  connessione DB con questo ruolo (alias `DATABASES` Django / credenziali dedicate).
- ➕ semplice, nessuna logica GUC, nessuna policy nuova.
- ➖ bypassa **tutta** la RLS (non solo il ciclo attivo), credenziali/role aggiuntivi da
  gestire (ops), meno granulare/auditabile.

### Opzione B — Sentinel `app.ruolo_applicativo='SISTEMA'` + policy permissive di sistema  ⭐ consigliata
- Aggiungere su **ciascuna** tabella del perimetro batch una policy permissiva
  `rls_<tabella>_sistema` con `USING (current_setting('app.ruolo_applicativo', true) =
  'SISTEMA')` e `WITH CHECK (... = 'SISTEMA')` (mirror delle `_ef_whitelist`, senza filtro
  emittente). Il batch setta la GUC `app.ruolo_applicativo='SISTEMA'` sulla propria
  sessione (parte BE, §5).
- ➕ coerente con l'architettura GUC esistente (stesso meccanismo degli operatori),
  **least-privilege** (solo le tabelle/azioni del ciclo attivo, non un bypass globale),
  nessuna credenziale/role extra, auditabile (la GUC mostra `SISTEMA`).
- ➖ richiede una policy di sistema per ogni tabella scritta; va garantito che il batch
  setti la GUC in modo affidabile (parte BE).
- **Da decidere lato modello**: `'SISTEMA'` è un **valore GUC-only** (sentinel testuale,
  le policy confrontano testo via `current_setting`) **oppure** va aggiunto all'enum
  `config.ruolo_applicativo`? Per il batch (che **non** è un'`identita_digitali`) il
  sentinel GUC-only è sufficiente e meno invasivo; aggiungerlo all'enum solo se serve
  altrove. Confermare.

## 5. Risvolto BE — ✅ FATTO (Opzione B, 2026-06-16, forward-compatible)

Implementato su `dev/backend-tid` (innocuo finché la RLS è dormiente / le policy `_sistema`
non esistono):

- `apps.core.services.auth_constants.RUOLO_APPLICATIVO_SISTEMA = "SISTEMA"` — sentinel
  **GUC-only** (fuori dall'enum mirror `RUOLO_APPLICATIVO`);
- `run_fatturazione_batch._system_db_context()` — context manager che a inizio run setta
  `app.ruolo_applicativo='SISTEMA'` e azzera le GUC d'identità sulla connessione
  (`set_config(..., is_local=false)`), e a fine run **ripristina** tutto (igiene pool);
  il corpo del batch è estratto in `_run_batch` ed eseguito dentro il contesto;
- **Solo percorso headless (cron)**: l'endpoint on-demand `pipeline/run-until-done` NON
  usa il contesto di sistema → resta nello scope **OPERATORE** del chiamante;
- test: `test_stabilisce_contesto_sistema_e_ripristina` (set SISTEMA + reset).

**Resta al team DB** (questo brief): le policy `_sistema` (§4 B), da creare
**contestualmente** al FORCE/enforce della RLS operatori. Finché non esistono, il batch
funziona come oggi.

## 6. Criterio di accettazione

- Con RLS *enforced*: una sessione con `app.ruolo_applicativo='SISTEMA'` (Opz. B) o il
  ruolo `BYPASSRLS` (Opz. A) esegue discovery + INSERT lotto + INSERT fatture/scadenze su
  **tutti** gli emittenti senza `default-deny` né violazioni `WITH CHECK`.
- Una sessione **operatore** resta isolata per emittente (nessuna regressione ondata1/2).
- Una sessione **senza** contesto (né operatore né sistema) resta default-deny (fail-closed).
- pgTAP: caso "sistema vede/scrive tutti gli emittenti" + caso "operatore isolato" + caso
  "no-context negato".

## 7. Coordinamento

Applicare **insieme** all'attivazione/FORCE della RLS operatori (non prima: oggi il batch
funziona perché la RLS è dormiente). Sequenza sicura: (1) policy/role di sistema + GUC BE
(B) → (2) FORCE/enforce RLS operatori → (3) verifica batch + operatore con pgTAP/smoke.
