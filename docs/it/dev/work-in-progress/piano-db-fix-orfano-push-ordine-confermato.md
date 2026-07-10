# Piano — Fix «orfano da push» ordine trigger CONFERMATO evaso (decoupling fatturazione ↔ spedizione)

> **Tipo**: piano di sviluppo (slice DB su `dev/db-tid` + handoff BE/FE) · **Data**: 2026-07-10 · **Owner**: Tid
> **Origine**: rilievo in-app 2026-07-10 (giro preventivo→ordine→DDT), proposto come §16 di
> [brief-db-ddt-vendita-evasione-e-stati.md](brief-db-ddt-vendita-evasione-e-stati.md);
> questo documento è l'esito dell'**analisi critica** di quella proposta e la **sostituisce**
> come design-of-record del fix (il §16 del brief punta qui).
> **Decisioni Tid 2026-07-10**: (1) **decoupling pulito** — il push NON cambia più lo stato
> ordine; (2) perimetro trigger CONFERMATO = intero ordine; «fattura su spedito» è già
> parametrico per cliente via `billing_account.fatturazione_ordini` (nessun nuovo parametro).

---

## 1. Il problema (rilievo confermato sul codice vivo)

Un ordine con `fatturazione_trigger = CONFERMATO` **evaso in DDT prima di essere pushato**
resta orfano: nessuna delle due sorgenti è eleggibile al push → documento **non fatturabile**.

Verificato (2026-07-10):

- `vendite.fn_list_ordini_da_pushare` richiede stato documento **= CONFERMATO**
  (oltre al filtro `fatturazione_trigger='CONFERMATO'`): l'evasione
  (`fn_genera_ddt_da_ordine`, proiezione stato §4 del brief) porta l'ordine a
  `PARZIALMENTE_EVASO`/`EVASO` → chiude la finestra di push.
- `vendite.fn_list_ddt_da_pushare` esclude by design i DDT ordine-sourced con
  `src_fatturazione_trigger = 'CONFERMATO'` (l'ordine è l'unica sorgente per quel trigger).
- Repro con dati reali: `ORD0000163` (id 174) → `DDT0000031` (id 55): entrambe le fn
  ritornano 0 righe, `commesse_attivita` vuota, `can_push_commessa=false`.

**Causa radice**: spedizione (asse evasione) e fatturazione-su-conferma (asse billing) sono
**ortogonali**, ma il modello le accoppia in due punti: l'eleggibilità push vincolata allo
stato-spedizione, e lo stato `EVASO` usato con **due semantiche** (vedi §2).

## 2. Analisi critica della proposta §16 originale (Fix C)

La proposta originale (rilassare la whitelist stati a `{CONFERMATO, PARZIALMENTE_EVASO,
EVASO}` in `fn_list_ordini_da_pushare` + allineare `fn_available_actions_ordine`) individua
bene il problema ma è **incompleta** e in un punto **pericolosa**:

| # | Rilievo | Dettaglio |
| --- | --- | --- |
| A | **Il gate effettivo del push singolo è nel BE, non nel DB** | `ordini_service.push_a_commessa` ha `_STATI_PUSHABILI={CONFERMATO}` → con fix solo-DB il bottone comparirebbe ma il POST fallirebbe (`E_ORD_STATO_TRANSIZIONE`). Solo il percorso batch (che chiama la fn direttamente) verrebbe sanato. |
| B | **Collisione semantica di EVASO** | Il BE, dopo push COMPLETATO, forza l'ordine a `EVASO` («fatturato»); il flusso DDT usa lo **stesso** `EVASO` per «spedizione completa». Con la whitelist §16, il push di un ordine PARZIALMENTE_EVASO lo marcherebbe **come completamente spedito quando non lo è** (corruzione stato spedizione). Inoltre `fn_available_actions_ordine` mappa `EVASO → ORDINE_GIA_EVASO` («già pushato»), asserendo la semantica opposta. |
| C | **Rimozione della cintura anti-re-push** | Oggi la transizione a EVASO fa cadere subito l'ordine dalla whitelist. Ammettendo EVASO tra i pushabili, nella finestra pre-`EMESSA` l'anti-doppione resta affidato alla sola dedup `segment_key` (+ advisory lock) di `pr_run_commesse_push_one` → da presidiare con pgTAP (caso 10). |
| D | **Whitelist di stati fragile** | Enumerare stati di *spedizione* per l'eleggibilità di *fatturazione* ripete l'accoppiamento: un futuro passaggio per `ALLOCATO`/`SPEDITO`/`CONSEGNATO` (già nel CSV stati) ricreerebbe l'orfano. |

## 3. Decisioni (Tid, 2026-07-10)

1. **Decoupling pulito.** Per trigger CONFERMATO la fatturabilità dipende **solo** da
   «confermato e non ancora fatturato», **mai** dallo stato di spedizione. Il «fatturato» si
   legge da `commesse_attivita.stato_emissione='EMESSA'` (verità già usata dal `NOT EXISTS`),
   **non** si stampa più sullo stato ordine: la transizione forzata `→EVASO` post-push (BE) va
   **rimossa**. `EVASO` torna ad avere **una sola semantica**: spedizione completa.
2. **Perimetro trigger CONFERMATO = intero ordine** (righe/qta ordinate), indipendente dalla
   spedizione — è la definizione di «fattura su conferma». Chi vuole fatturare solo lo
   spedito **non ha bisogno di un nuovo parametro**: usa `fatturazione_trigger='SPEDITO'`,
   già parametrico **per cliente** (`billing_account.fatturazione_ordini`, ereditato
   dall'ordine all'INSERT via `trgfn_ordini_normalize`, override per-ordine in DRAFT).
   Valori: `CONFERMATO | SPEDITO | CONSEGNATO` (CHECK su entrambe le tabelle).
3. **Predicato state-agnostic, non whitelist.** L'eleggibilità esclude solo gli stati che
   negano l'esistenza commerciale del documento (`DRAFT`, `ANNULLATO`) più la cintura
   `FATTURATO`; ogni altro stato presente o futuro dell'asse spedizione è ininfluente.

### Parametricità futura (fuori scope, annotato)

- Default di colonna/seed oggi = `CONFERMATO`; se si preferisce `SPEDITO` come default
  aziendale prudente è una micro-slice a parte (default colonna + seed BA).
- Esposizione di `billing_account.fatturazione_ordini` in scheda cliente (BE/FE) — slice a parte.

## 4. Slice DB (questa, `dev/db-tid`) — SOLO DB

### 4.1 ChangeSet

| # | File | Contenuto |
| --- | --- | --- |
| `20260710-01` | `20_code/vendite/20260710-01-update-fn-list-ordini-da-pushare-stati-evasione-mctit.yaml` | `fn_list_ordini_da_pushare`: sostituisce il vincolo `stato = CONFERMATO` con `codice_interno NOT IN ('DRAFT','ANNULLATO','FATTURATO')` (risolto per `codice_interno`, join su `config.stati_doc_ordini`). Invariati: filtro `fatturazione_trigger='CONFERMATO'`, `NOT EXISTS … EMESSA`, guard righe attive/qta/prezzo, firma. |
| `20260710-02` | `20_code/script/20260710-02-update-fn-available-actions-ordine-decoupling-fatturazione-mctit.yaml` | `fn_available_actions_ordine`: capability `can_push_commessa` allineata alla stessa condizione (riuso `fn_list_ordini_da_pushare`); reason ricalcolati: `ORDINE_NON_CONFERMATO` (DRAFT/ANNULLATO), **`ORDINE_FATTURA_DA_DDT`** (trigger ≠ CONFERMATO — nuovo, più parlante del generico «nessuna riga»), **`ORDINE_GIA_FATTURATO`** (predicato EMESSA — sostituisce `ORDINE_GIA_EVASO`, che asseriva EVASO=fatturato), `ORDINE_NESSUNA_RIGA_PUSHABILE` (fallback). |

Nessun nuovo codice errore (i reason di capability non sono `messaggi_errore`).

**Nota XOR (§8 del brief)**: il rilassamento tocca solo ordini `trigger='CONFERMATO'`; per
quel trigger il DDT ordine-sourced resta **escluso** da `fn_list_ddt_da_pushare`
(`src_trigger != 'CONFERMATO'`) → l'ordine resta l'unica sorgente del perimetro. Congelato dal
pgTAP caso 8.

### 4.2 pgTAP

| File | Casi |
| --- | --- |
| `db/pgtap/vendite/test-fn-list-ordini-da-pushare-v3.sql` | 7) recupero orfano: ordine trigger CONFERMATO evaso full → EVASO → `fn_list` ≥1; 7b) parziale → PARZIALMENTE_EVASO → ≥1; 8) XOR: il suo DDT portato a SPEDITO **non** compare in `fn_list_ddt_da_pushare`; 9) non-regressione SPEDITO: ordine trigger SPEDITO evaso → `fn_list_ordini`=0 e DDT eleggibile; 10) no-doppione: simulato il push a livello DB (`fn_get_or_create_commessa` + `fn_upsert_commessa_attivita` con `stato_emissione='EMESSA'`) la re-list = 0; DRAFT/ANNULLATO esclusi. |
| `db/pgtap/script/test-fn-available-actions-ordine-v2.sql` | orfano EVASO → `can_push_commessa=true` + azione `push_commessa`; PARZIALMENTE_EVASO → true; dopo EMESSA → false + `ORDINE_GIA_FATTURATO`; trigger SPEDITO → `ORDINE_FATTURA_DA_DDT`; DRAFT → `ORDINE_NON_CONFERMATO` (non-regressione); CONFERMATO pushabile → true (non-regressione v1). |

I pgTAP esistenti restano verdi: `…-v1.sql` testa l'esclusione del **DRAFT** (che resta
esclusa) e `…-v2.sql` firma/smoke; `test-fn-available-actions-ordine-v1.sql` non asserisce
il reason su EVASO.

### 4.3 Doc

- Manual `vendite/manual/fn_list_ordini_da_pushare.md` e
  `script/manual/fn_available_actions_ordine.md` aggiornate (predicato, reason, decoupling).
- §16 del brief riscritto come puntatore a questo piano.
- Doc auto-gen dbzero: la rigenera Tid dopo l'applicazione.

### 4.4 Effetti collaterali attesi (voluti)

- **Dashboard due lenti / backlog**: gli ordini orfani (trigger CONFERMATO, evasi, mai
  pushati) ora **compaiono** nel backlog — è la correzione della «fatturazione persa».
- **Proiezione stato dominio**: con il decoupling (BE, §5) un ordine pushato ma non ancora
  spedito resta `CONFERMATO` (IN_CORSO) finché l'evasione non lo porta a EVASO — semantica
  onesta: il documento non è «finito» finché non è spedito. La chiusura pratica **non**
  dipende dallo stato ordine (lo step `INVIO_COMMESSA` si completa nel push, chiamata
  indipendente dalla transizione — verificato in `ordini_service.py`).

## 5. Handoff BE (`dev/backend-tid`, slice successiva — GATE: DB applicato)

> ⚠️ **Finestra di incoerenza nota** (accettata, progetto non in produzione): tra
> l'applicazione della slice DB e quella BE, il drawer ordine mostra `push_commessa` su
> ordini PARZIALMENTE_EVASO/EVASO ma il POST fallisce con `E_ORD_STATO_TRANSIZIONE`
> (guard BE `_STATI_PUSHABILI` ancora `{CONFERMATO}`). Chiudere la slice BE subito dopo.

1. **`ordini_service.push_a_commessa`**: rimuovere il guard whitelist `_STATI_PUSHABILI`
   (logica duplicata DB↔Python) — l'eleggibilità è già decisa da `count_righe_pushable`
   (riuso `fn_list_ordini_da_pushare`) + guard `E_ORD_NESSUNA_RIGA`.
2. **Rimuovere la transizione forzata `CONFERMATO→EVASO` post-push** (blocco savepoint
   best-effort): il «fatturato» vive in `commesse_attivita`, EVASO = solo spedizione.
   La chiusura step-pratica `_completa_flusso_ordine_pratica` resta invariata.
3. Aggiornare i test (`test_ordini_service.py` asserisce oggi la transizione EVASO e il
   guard stato).
4. Matrice `transizioni_stati_ordini`: la riga automatica `CONFERMATO→EVASO` **resta**
   (serve alla proiezione stato dell'evasione full in `fn_genera_ddt_da_ordine`).

## 6. Handoff FE (dopo BE)

Nessuna logica: il pulsante segue la capability data-driven. Aggiungere le traduzioni dei
nuovi reason key: `ordini.push_commessa_reason.gia_fatturato`,
`ordini.push_commessa_reason.fattura_da_ddt` (rimuovere `gia_evaso` quando il BE atterra).

## 7. Stato avanzamento

- [x] ChangeSet `20260710-01/02` scritti
- [x] pgTAP v3 + v2 scritti
- [x] Doc manual aggiornate, §16 brief → puntatore
- [x] **Applicazione su DB Tid + pgTAP verdi (2026-07-10)** — migrations `20260710-01/02`
  EXECUTED, `test-fn-list-ordini-da-pushare-v3.sql` (plan 10) e
  `test-fn-available-actions-ordine-v2.sql` (plan 8) **verdi**; nessuna regressione sui
  pgTAP collegati (`fn-list-ordini v1/v2`, `available-actions v1`, `genera-ddt v1`).
  NON committato (attendere «procedi»); doc auto-gen dbzero la rigenera Tid.
- [ ] Slice BE (handoff §5) — `dev/backend-tid`, prossima
- [ ] Slice FE (handoff §6)

### Consuntivo DB (2026-07-10)

Slice DB realizzata e applicata su `dev/db-tid`. L'orfano è chiuso: un ordine
`fatturazione_trigger=CONFERMATO` evaso in DDT (`PARZIALMENTE_EVASO`/`EVASO`) torna
eleggibile al push (`fn_list_ordini_da_pushare` ≥1) e la capability lo espone
(`can_push_commessa=true`), mentre l'XOR §8 resta presidiato (il DDT ordine-sourced
`src_trigger=CONFERMATO` resta escluso) e il re-push è bloccato dal `NOT EXISTS … EMESSA`
(caso 10 verde). **Aperto**: la finestra di incoerenza col guard BE `_STATI_PUSHABILI`
resta finché non atterra la slice BE (§5) — da avviare subito.
