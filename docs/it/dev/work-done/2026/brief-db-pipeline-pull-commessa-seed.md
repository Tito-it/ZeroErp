# Brief DB — Seed pipeline: aggancio del pull commessa → attività fatturabili (+ corsia GIORNALIERO, chiude_lotto)

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> Spiega *cosa* serve e *perché*; **non contiene DDL/seed pronto** — il *come*
> (changeset liquibase, righe CSV, ordini, id) è scelta del team DB.
>
> **Data**: 2026-06-15 · **Stato**: ✅ **IMPLEMENTATO** (2026-06-15) — seed atterrato
> su `dev/db-tid`, pgTAP verde (`test-seed-pull-commessa-pipeline-v1.sql`). Vedi §0.
>
> **Origine**: [analisi-commesse-stato-e-sviluppi.md §10](analisi-commesse-stato-e-sviluppi.md)
> (piano driver di orchestrazione fatturazione). La verifica seed (Fase 0) ha
> trovato che la catena commessa → fatturazione è **interrotta a livello di seed**.
>
> **Prerequisito di**: il **driver di orchestrazione fatturazione** (lavoro BE:
> avanzamento multi-step, management command, timer near-real-time/mensile). Il
> driver non può essere testato end-to-end finché questi seed non esistono.

---

## 0. Stato implementazione (2026-06-15, dal team DB)

✅ **Atterrato su `dev/db-tid` e pushato, pgTAP verde** (`test-seed-pull-commessa-pipeline-v1.sql`).
Solo seed/config, nessuna logica DB nuova.

| Deliverable | Esito |
|---|---|
| **D1** pull → select → genera | `pull_attivita_da_commessa` registrato in `dbops.pipeline_task_registry`/`_impl` (dominio `FATTURAZIONE`, handler `pull_attivita_da_commessa_default`) e messo **in testa** alla pipeline MASSIVO/DRAFT. *(Senza la registrazione il dispatch falliva "Task non registrato": l'array `processi` da solo non bastava.)* |
| **D2** corsia GIORNALIERO/DRAFT | Aggiunta pipeline GIORNALIERO/DRAFT (stato 1) con gli stessi 3 task della massiva (no fondi/IVA, che sono fase EMESSA). Riusa la transizione 1→8. Vecchia riga GIORNALIERO/EMESSA (vuota, mai raggiunta) lasciata: cleanup opzionale. |
| **D3** `chiude_lotto` | **Opzione A su DEFINITIVA** (spostato da REGISTRATA, inerte). Non INVIATA perché SDI è fuori scope ora. |
| task_policy | Aggiunte righe pull (massivo+giornaliero) e select/genera giornalieri per il tracing. |

### Impatti comportamentali da tenere a mente lato BE (vincoli per il driver)

1. **Chiusura lotto ora attiva**: `is_stato_doc_chiude_lotto(DEFINITIVA) == true` → quando
   gira lo step DEFINITIVA (`numera_fatture`), `pipeline_runner._process_close_lotto_by_flag`
   chiude il lotto (`close_lotto_operativo`). Prima non si chiudeva mai. **Il driver
   multi-step non deve fare doppia chiusura; verificare l'idempotenza di
   `close_lotto_operativo` nel flusso.**
2. **Perimetro del pull dal `LottoContext`**: il pull deriva il perimetro da
   `competenza_mese`/`utility_id`/`billing_account_id`/`emittente_soggetto_ruolo_id`.
   **Il context va valorizzato sul lotto in DRAFT**: con filtri NULL la discovery prende
   **tutte** le commesse emittibili nella competenza.
3. **Futuro SDI**: quando l'invio SDI diventerà reale, valutare lo spostamento di
   `chiude_lotto` su INVIATA.

> **Resta a carico BE** (fuori scope DB, come da brief): scheduler/timer corsia
> immediata+differita, management command, avanzamento multi-step di `run_pipeline`
> (oggi 1 step per run), endpoint on-demand. **Nessun pgAgent.**

---

## 1. Contesto e problema

Il flusso atteso è:

```
commessa PRONTA_FATTURAZIONE → [PULL] attivita_fatturabili → [SELECT+LOCK] → [GENERA righe] → [NUMERA] → [SDI]
```

Lo **step di PULL** (commessa → `attivita_fatturabili`) è l'unica porta che popola
le attività fatturabili a partire dalle commesse (guard DB
`trgfn_attivita_fatturabili_guard_commessa`: nessuna AF senza commessa).

**Lato backend il pull è già pronto e completo**: il task
`pull_attivita_da_commessa` (handler `_handle_pull_attivita_da_commessa_task`) fa da
solo la **discovery** delle commesse emittibili (`fn_list_commesse_emittibili` dal
perimetro del lotto) e l'**emissione per-commessa** (`fn_emit_attivita_fatturabili_da_commessa`),
con isolamento errori per commessa. **Non serve logica DB aggiuntiva** per il pull.

**Il problema è di sola configurazione (seed)**: il task `pull_attivita_da_commessa`
**non è agganciato a nessuno step di pipeline**. Le pipeline seedate
(`vendite.fatturazione_pipeline`) per la fase DRAFT eseguono `select_attivita` +
`generate_fatture_righe`, che **assumono le AF già esistenti** (`select_attivita`
seleziona/blocca AF esistenti, non le crea). Risultato: **oggi nessun flusso pipeline
emette le AF dalle commesse** — la catena è di fatto interrotta a questa giunzione.

In più la verifica ha rilevato due gap collegati (vedi §2.2 e §2.3).

---

## 2. Cosa serve (risultati attesi)

### 2.1 D1 — Agganciare il pull commessa alla pipeline (prima del select)

**Risultato atteso**: durante la fase iniziale del lotto (DRAFT), **prima** di
`select_attivita`, deve essere eseguito il task **`pull_attivita_da_commessa`**, così
che le attività fatturabili vengano materializzate dalle commesse emittibili e poi
selezionate/lockate.

- Vale per la corsia **MASSIVO** e per la corsia **GIORNALIERO** (§2.2).
- Ordine richiesto nella fase DRAFT: **pull → select → genera righe**.
- Il *come* (task aggiunto in testa all'array `processi` dello step DRAFT esistente,
  oppure step dedicato a monte) è scelta del team DB: conta solo che il pull avvenga
  **prima** del select, nello stesso lotto.
- Nessun parametro speciale necessario: l'handler usa il perimetro del lotto.

### 2.2 D2 — Completare la corsia GIORNALIERO (near-real-time)

**Contesto**: il driver avrà due corsie — **differita** (batch mensile su competenza,
tipicamente `MASSIVO`) e **immediata/near-real-time** (`GIORNALIERO`).

**Problema**: la pipeline `GIORNALIERO` oggi è seedata per le fasi a valle
(numerazione, SDI) ma **manca la fase iniziale DRAFT** (quella che fa pull + select +
genera righe). Quindi la corsia immediata non ha da dove partire.

**Risultato atteso**: la corsia `GIORNALIERO` deve avere una fase iniziale DRAFT
equivalente a quella MASSIVO (pull → select → genera righe), così da essere eseguibile
end-to-end come la massiva.

### 2.3 D3 — Chiusura del lotto a fine catena (decisione di modello)

**Problema**: nessuno stato in `config.stati_doc_fiscale` ha `chiude_lotto = true`,
quindi la chiusura del lotto guidata da flag non scatta mai. Il driver ha bisogno di un
segnale chiaro di "catena conclusa".

**Decisione da concordare** (Tid + team DB) — due opzioni alternative:

- **Opzione A (lato DB/seed)**: impostare `chiude_lotto = true` sullo stato finale
  della catena (INVIATA, oppure DEFINITIVA se l'invio SDI resta fuori scope per ora),
  così la chiusura è data-driven e coerente col meccanismo esistente.
- **Opzione B (lato driver/BE)**: nessuna modifica al seed; il driver considera
  "concluso" il lotto quando ha eseguito l'ultimo step del catalogo.

> Raccomandazione: **Opzione A** (coerente col flag `chiude_lotto` già previsto dal
> modello, evita logica di fine-catena duplicata nel BE). Ma è una scelta di modello:
> decide Tid col team DB. Indicare quale stato è "finale" per il perimetro attuale.

---

## 3. Criteri di accettazione

- Avviando la pipeline di un lotto (MASSIVO **o** GIORNALIERO) su un perimetro con
  commesse in `PRONTA_FATTURAZIONE` aventi righe `APPROVATA`/`NON_EMESSA`, la fase DRAFT
  **crea** le relative `attivita_fatturabili` (pull) e poi le seleziona/genera, **senza**
  che siano state pre-create da test/chiamate dirette.
- La corsia `GIORNALIERO` è eseguibile end-to-end come la `MASSIVO`.
- (Se Opzione A) raggiunto lo stato finale, il lotto risulta chiuso via flag
  `chiude_lotto`.
- Copertura pgTAP coerente con lo stile dei test pipeline/commesse esistenti.

---

## 4. Fuori scope (non DB — sono lavori BE già pianificati, §10 analisi)

- **Scheduler/timer** (systemd/cron) e **management command** della corsia
  immediata/differita: **solo BE**, nessun pgAgent (riservato a manutenzione DB).
- **Avanzamento multi-step** di `run_pipeline` (oggi esegue un solo step per run): **solo
  BE**.
- **Endpoint on-demand** per avvio da interfaccia operatore: **solo BE**.
- Invio reale SDI, note di credito, UI commesse: fuori scope di questo brief.

---

## 5. Domande aperte per il team DB / Tid

1. **D3**: si procede con Opzione A (set `chiude_lotto` sullo stato finale) o B (stop
   lato driver)? Se A, quale stato è "finale" oggi: INVIATA o DEFINITIVA?
2. **D2**: la corsia `GIORNALIERO` deve avere esattamente gli stessi task DRAFT della
   MASSIVO, o differenze previste (es. niente fondi/IVA massiva)?
3. Esistono perimetri (`utility_id` / `tipo_doc_fiscale_id`) per cui servono pipeline
   dedicate, o il default attuale (`utility_id`/`tipo_doc_fiscale_id` NULL) copre tutto?
