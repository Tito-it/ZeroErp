# Brief DB — Macchina di transizioni stati commessa (+ emittibilità)

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> Spiega *cosa* fare e *perché*; **non contiene DDL pronto** (lo scrive il team
> DB nel changelog liquibase, mirando ai template citati).
>
> **Data**: 2026-06-07 · **Stato**: ✅ **IMPLEMENTATO** (2026-06-08) — changeset
> applicati, pgTAP verdi. Vedi §0.
>
> **Origine**: prerequisito **V9** del
> [brief-db-pratica-preventivi.md](brief-db-pratica-preventivi.md). La verifica
> critica (2026-06-07) ha trovato che il ramo commessa→fattura è **dormiente**:
> la commessa nasce in `BOZZA` e **nessuna** funzione/trigger la porta a
> `PRONTA_FATTURAZIONE`, né le righe ad `APPROVATA`. Le commesse — a differenza
> di preventivi e ordini — **non hanno macchina di transizioni**. Questo brief la
> costruisce.
>
> **Decisioni di prodotto (Tid, 2026-06-07)** già prese, qui solo implementate:
> macchina di transizioni completa; righe auto-approvate nel push; testata auto a
> `PRONTA_FATTURAZIONE` (zero click, il preventivo accettato è l'autorizzazione);
> guard "≥1 riga `APPROVATA`+`NON_EMESSA`"; meccanismo righe via funzione
> dedicata; grafo con riapertura inclusa.

---

## 0. Stato implementazione (2026-06-08)

✅ **Tutto implementato e testato (pgTAP verdi).** Mappa deliverable → changeset:

| Deliverable | File | Stato |
|---|---|---|
| C1 tabella `transizioni_stati_commessa` | `00_schema/vendite/20260607-01-create-transizioni-stati-commessa` | ✅ |
| C2 guard trigger `trgfn_commesse_guard_transizione` | `20_code/vendite/20260607-02-create-trgfn-commesse-guard-transizione` | ✅ |
| C3 `fn_cambia_stato_commessa` | `20_code/vendite/20260607-03-create-fn-cambia-stato-commessa` | ✅ |
| C4 `fn_approva_commessa_attivita` | `20_code/vendite/20260607-04-create-fn-approva-commessa-attivita` | ✅ |
| C5 seed transizioni (11 righe) | `80_data/sql/vendite/transizioni_stati_commessa.csv` + `80_data/changelog/20260607-05-seed-transizioni-stati-commessa` | ✅ |
| C6 codici errore | `80_data/changelog/20260607-06-upsert-messaggi-errore-commessa-transizione` (472/473; `E_COMMESSA_NON_TROVATA` **riusato** id 376, non ri-aggiunto) | ✅ |
| C7 pgTAP | `db/pgtap/vendite/test-commesse-transizioni-stati-v1.sql` (nuovo) + `test-commesse-stati-commessa-v1.sql` riconciliato | ✅ verdi |
| Doc | 4 manual: `docs/it/dbzero/vendite/manual/{transizioni_stati_commessa,trgfn_commesse_guard_transizione,fn_cambia_stato_commessa,fn_approva_commessa_attivita}.md` | ✅ |

**Deliverable emerso durante l'integrazione** (non previsto dal brief, scoperto
dal pgTAP `af-commessa-aware`):

- **Bug `fn_emit_attivita_fatturabili_da_commessa`** — referenziava la tabella e
  la colonna `lotto_attivita_id` **droppate** dalla deprecazione `20260227-16`
  (sottosistema pipeline → commesse v2). Ripulito: `20_code/vendite/20260607-09-cleanup-fn-emit-drop-lotto-attivita` (nuova firma a 3 param) + backend
  `apps/vendite/db/commesse_repository.py` (rimosso `lotto_attivita_id`). Nessun
  altro chiamante DB; `pipeline_step_executor` non passava il parametro.
- **Resurrezione suite pgTAP commesse** — 8 file erano stale (firma `fn_upsert`
  v5 con 8 param obbligatori, riferimenti `lotto`, `listini.dominio` rimossa,
  `listini_versioni.priorita` rimossa). Tutti allineati allo schema attuale.

> **Nota numerazione**: 07/08 del 2026-06-07 erano già occupati dal lavoro
> "univocità offerta-ordine"; il cleanup `fn_emit` è quindi a `20260607-09`
> (il gen-script ha auto-risolto la collisione).

---

## 1. Scope DB

In scope:

1. Nuova tabella `vendite.transizioni_stati_commessa` (matrice transizioni).
2. Seed delle transizioni ammesse (CSV `80_data`).
3. Guard trigger `trgfn_commesse_guard_transizione` (BEFORE UPDATE stato) che
   rifiuta transizioni non in matrice.
4. Funzione `vendite.fn_cambia_stato_commessa(...)` — entrypoint sanzionato
   (valida, applica, logga), chiamata da handler/app.
5. Funzione `vendite.fn_approva_commessa_attivita(...)` — approvazione righe
   (`stato_approvazione BOZZA→APPROVATA`).
6. Codici errore in `config.messaggi_errore`.
7. pgTAP della macchina + **riconciliazione dei pgTAP commesse esistenti** che
   fanno `UPDATE` diretto di stato.

**Esplicitamente NON in scope**: l'handler `vendita.push_preventivo` (è BE, vedi
[brief-be](brief-be-pratica-preventivi.md)); la scelta immediata/differita (vive
in `handler_params`, non qui); `fn_available_actions_commessa` per la UI (utile
ma rinviabile — vedi §7).

---

## 2. Riscontro schema reale (verificato 2026-06-07)

| Oggetto | Stato reale | Azione |
|---|---|---|
| `vendite.stati_commessa` (id 1..6, flag `emittibile`/`chiude_commessa`/`modificabile`) | **Esiste** ([20260226-01](../../../../db/changelog/migrations_v2/00_schema/vendite/20260226-01-create-stati-commessa-mctit.yaml)) | Nessuna |
| Stato `PRONTA_FATTURAZIONE` (id 4, unico `emittibile=true`) | **Esiste** | Nessuna |
| `commesse.stato_commessa_id` default `1` (BOZZA) | **Esiste** | Nessuna |
| `commesse_attivita.stato_approvazione` default `BOZZA`, `stato_emissione` default `NON_EMESSA` | **Esistono** | Nessuna |
| `fn_get_or_create_commessa` (crea in BOZZA) / `fn_upsert_commessa_attivita` (righe in BOZZA) | **Esistono** | Nessuna |
| `fn_list_commesse_emittibili` (richiede testata `emittibile=true` + righe `NON_EMESSA`) | **Esiste** ([20260226-08](../../../../db/changelog/migrations_v2/20_code/vendite/20260226-08-update-fn-list-commesse-emittibili-emittente-mctit.yaml)) | Nessuna |
| `fn_emit_attivita_fatturabili_da_commessa` (emette righe `APPROVATA`) | **Esiste** | Nessuna |
| **Macchina transizioni commesse** (tabella + trigger + fn) | **Manca** | **Crea** (C1–C5) |
| Funzione transizione testata / approvazione righe | **Manca** (solo UPDATE manuale nei pgTAP) | **Crea** (C3/C4) |

**Template da rispecchiare** (sibling già in repo):
- Ordini (il più fresco, 2026-06-05): tabella
  [`20260605-08`](../../../../db/changelog/migrations_v2/00_schema/config/20260605-08-create-transizioni-stati-ordini-mctit.yaml) +
  guard trigger
  [`20260605-10`](../../../../db/changelog/migrations_v2/20_code/vendite/20260605-10-create-trgfn-ordini-guard-transizione-mctit.yaml) +
  seed
  [`20260605-11`](../../../../db/changelog/migrations_v2/80_data/changelog/20260605-11-seed-transizioni-stati-ordini-mctit.yaml).
- Preventivi: fn entrypoint
  [`fn_cambia_stato_preventivo` 20260403-08](../../../../db/changelog/migrations_v2/20_code/vendite/20260403-08-create-fn-cambia-stato-preventivo-mctit.yaml).

---

## 3. Modello: grafo stati e transizioni da seedare

Stati (da `vendite.stati_commessa`): `BOZZA(1)`, `APERTA(2)`, `IN_ESECUZIONE(3)`,
`PRONTA_FATTURAZIONE(4, emittibile)`, `CHIUSA(5, terminale)`, `ANNULLATA(6,
terminale)`.

```text
BOZZA ─▶ APERTA ─▶ IN_ESECUZIONE ─▶ PRONTA_FATTURAZIONE ─▶ CHIUSA
  │        │            │                   │  ▲
  │        │            │                   └──┘  (riapertura PRONTA→IN_ESECUZIONE)
  └────────┴────────────┴───────────────────┴──▶ ANNULLATA
  (salti diretti del push: BOZZA/APERTA ─▶ PRONTA_FATTURAZIONE)
```

**Transizioni da seedare** (matrice `stato_da → stato_a`):

| da | a | note |
|---|---|---|
| BOZZA | APERTA | avvio commessa |
| BOZZA | PRONTA_FATTURAZIONE | **salto del push** (commessa nata confermata) |
| BOZZA | ANNULLATA | |
| APERTA | IN_ESECUZIONE | |
| APERTA | PRONTA_FATTURAZIONE | **salto del push** |
| APERTA | ANNULLATA | |
| IN_ESECUZIONE | PRONTA_FATTURAZIONE | |
| IN_ESECUZIONE | ANNULLATA | |
| PRONTA_FATTURAZIONE | IN_ESECUZIONE | **riapertura** (correzione pre-fattura) |
| PRONTA_FATTURAZIONE | CHIUSA | |
| PRONTA_FATTURAZIONE | ANNULLATA | |

`CHIUSA` e `ANNULLATA` sono terminali (nessuna uscita). I salti diretti
`BOZZA/APERTA → PRONTA_FATTURAZIONE` servono al percorso push: l'handler non fa
passare la commessa per gli stati intermedi quando nasce già confermata.

---

## 4. Deliverable DB

| ID | Oggetto | Cosa fare |
|---|---|---|
| **C1** | `vendite.transizioni_stati_commessa` (tabella) | Stessa struttura di `transizioni_stati_ordini`/`_preventivi`: `id` PK, `stato_da_id`/`stato_a_id` (FK a `vendite.stati_commessa`), `attivo`, `meta jsonb` (UI: severity/label), audit. `UNIQUE(stato_da_id, stato_a_id)`, CHECK `da≠a`, CHECK `meta_ui`, trigger `dbops.trgfn_child_requires_active_parent` su entrambi gli stati + audit. **In schema `vendite`** (lì vive `stati_commessa`), non `config` |
| **C2** | `vendite.trgfn_commesse_guard_transizione` (+ trigger BEFORE UPDATE) | Rispecchia `trgfn_ordini_guard_transizione`: su `UPDATE OF stato_commessa_id`, se `OLD<>NEW`, verifica che `(OLD, NEW)` esista in `transizioni_stati_commessa` con `attivo`; altrimenti `fn_log_and_raise_error('E_COMMESSA_TRANSIZIONE_NON_AMMESSA', ...)`. Trigger fase `_a10_` |
| **C3** | `vendite.fn_cambia_stato_commessa(p_commessa_id, p_nuovo_stato codice, p_user)` | Entrypoint sanzionato, sul modello `fn_cambia_stato_preventivo`: valida parametri → stato corrente → stato target esiste/attivo → (il guard C2 valida la matrice; qui resta il **guard di dominio**) → `UPDATE` → `RETURNS TABLE(...)`. **Guard di dominio su `→ PRONTA_FATTURAZIONE`**: ammessa solo se la commessa ha ≥1 riga `commesse_attivita` con `stato_approvazione='APPROVATA'` **e** `stato_emissione='NON_EMESSA'`, altrimenti `E_COMMESSA_NESSUNA_RIGA_APPROVATA`. Codici via `script.fn_log_and_raise_error` |
| **C4** | `vendite.fn_approva_commessa_attivita(p_commessa_id, p_righe_ids bigint[] DEFAULT NULL, p_user)` | Porta `stato_approvazione` BOZZA→APPROVATA per le righe indicate (NULL = tutte le righe `NON_EMESSA` della commessa). Idempotente (righe già APPROVATA = no-op). Restituisce il numero di righe approvate. È la funzione che l'handler chiama prima di `fn_cambia_stato_commessa(...,'PRONTA_FATTURAZIONE')` |
| **C5** | Seed `vendite.transizioni_stati_commessa` | CSV in `80_data/sql/vendite/transizioni_stati_commessa.csv` (convenzione seed CSV) caricato da changelog `80_data`, come `transizioni_stati_ordini`. Righe = tabella §3, con `meta` UI (severity/label) coerente con preventivi/ordini |
| **C6** | Seed `config.messaggi_errore` | `E_COMMESSA_TRANSIZIONE_NON_AMMESSA`, `E_COMMESSA_NESSUNA_RIGA_APPROVATA` (+ eventuali di C4). Formato CSV `(codice, lingua, messaggio, ...)` con placeholder `%s` |
| **C7** | pgTAP | (1) transizione ammessa OK / non ammessa rifiutata; (2) `→PRONTA_FATTURAZIONE` senza righe approvate → `E_COMMESSA_NESSUNA_RIGA_APPROVATA`; (3) `fn_approva_commessa_attivita` idempotente; (4) E2E: push-like → righe APPROVATA → testata PRONTA_FATTURAZIONE → compare in `fn_list_commesse_emittibili`. **+ riconciliare i pgTAP esistenti** (vedi §6) |

> Tutti i salti del push (`BOZZA→PRONTA_FATTURAZIONE`) sono **seedati come
> transizioni valide** (§3): così il guard C2 li ammette e l'handler li può
> eseguire via C3 senza passare per gli stati intermedi.

---

## 5. Integrazione con l'handler `vendita.push_preventivo` (riferimento BE)

L'handler, dopo aver creato commessa + righe via il push esistente, chiude la
sequenza con due chiamate (lo step "approvazione + emittibilità" tra i punti 6 e
7 dello pseudo-flow del [brief BE §5](brief-be-pratica-preventivi.md)):

```text
fn_approva_commessa_attivita(commessa_id)                  # righe → APPROVATA
fn_cambia_stato_commessa(commessa_id, 'PRONTA_FATTURAZIONE', user)
   # guard C3: passa perché ora c'è ≥1 riga APPROVATA+NON_EMESSA
```

A valle, `fn_list_commesse_emittibili(p_competenza_mese)` include la commessa nel
lotto giusto (mese corrente per IMMEDIATA, mese scelto per DIFFERITA): il timing
resta governato da `competenza_mese` delle righe, **non** dallo stato testata.

---

## 6. Caveat e rischi (verificati)

- **pgTAP commesse esistenti fanno `UPDATE` diretto di stato.**
  `db/pgtap/vendite/test-commesse-stati-commessa-v1.sql` e
  `test-trigger-af-commessa-aware-v1.sql` eseguono `UPDATE vendite.commesse SET
  stato_commessa_id = 4/5` saltando stati. Con il guard C2 attivo, questi
  `UPDATE` **falliranno** se i salti non sono in matrice. → Riconciliare:
  aggiornare i test perché usino transizioni valide (o `fn_cambia_stato_commessa`).
  **No produzione**: nessuna sanatoria dati, solo i test (memoria
  `feedback_guard_breaks_existing_tests` → grep pgTAP prima del trigger
  BEFORE UPDATE).
- **`child_requires_active_parent`**: come preventivi/ordini, i due trigger sulla
  tabella transizioni richiedono che gli stati referenziati siano `attivo=true`.
  Tutti gli stati commessa lo sono: nessun problema, ma non disattivare uno stato
  con transizioni attive.
- **Doppia difesa (trigger C2 + guard C3)**: il trigger valida la **matrice** su
  qualunque UPDATE (anche fuori dalla fn); la fn aggiunge il **guard di dominio**
  (righe approvate) e il logging. Non è duplicazione: sono due livelli (struttura
  vs dominio). La regola "righe approvate" sta **solo** in C3 (la fn), non nel
  trigger, perché è semantica di dominio, non di matrice.

---

## 7. Domande aperte (minime)

1. **C4 firma**: `fn_approva_commessa_attivita` con `p_righe_ids` opzionale
   (NULL=tutte) va bene per il push (che approva tutte le righe)? Per ora sì; il
   parametro lascia spazio ad approvazioni parziali future.
2. **C5 meta UI**: severity/label delle transizioni per una futura
   `fn_available_actions_commessa` — seedare un `meta` minimale ora (come
   ordini/preventivi) o `{}` e arricchire quando si fa la UI? Proposta: minimale
   ora, coerente con i sibling.
3. **`fn_available_actions_commessa`** (capability per detail API, come
   `fn_available_actions_ordine`/`_preventivo`): fuori scope di questo brief o da
   includere? Proposta: **fuori scope** (la si fa quando serve la UI commesse),
   ma le transizioni seedate la abilitano senza rework.

---

*Brief DB — Macchina transizioni stati commessa — ZeroERP (2026-06-07).
Prerequisito V9 di brief-db-pratica-preventivi. Da passare a `dev/db-tid`.*
