# Brief DB — Cockpit processi fatturazione (Fase A/B/C)

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` · **Data**: 2026-07-19
> · **Owner**: Tid · **Stato**: ⬜ **DA ESEGUIRE**
>
> **Design-of-record**:
> [brief-design-gestione-processi-fatturazione.md](brief-design-gestione-processi-fatturazione.md)
> — decisioni **D-1..D-7** chiuse da Tid il 2026-07-19.
> **Gate**: BE/FE partono a oggetti DB applicati ([[feedback_be_fe_attende_prerequisiti_db]]).
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]]) → breaking
> secchi ammessi, nessuna compatibilità da mantenere.
>
> **Sintesi**: il motore di fatturazione è già completo. Questo brief chiede **solo seed**
> — due azioni di processo e un task di stampa dentro lo step di numerazione. **Nessun DDL,
> nessuna vista, nessuna funzione nuova.**

---

## 1. Perché (contesto in tre righe)

La pipeline di fatturazione oggi si pilota solo da cron/curl: nessuna superficie in app.
Il design collegato porta i processi **dentro la Dashboard Competenza** (approva → fattura
→ rendi definitive). Perché il BE possa esporre le azioni servono due permessi di processo
seedati, e perché siano rispettate **D-1** («numerazione e stampa sono **un processo
unico**, mai duplicato tra corsia immediata e massiva») e **D-7** («la stampa è un processo
separato e senza logica») serve che la stampa viva **nello stesso step di pipeline** della
numerazione — cioè in **configurazione**, non nel codice del chiamante — pur restando un
**task a sé**, ri-eseguibile e delegante (§3).

---

## 2. D1 — Due azioni di processo (append `config/azioni_processo.csv`)

**Pattern**: append al CSV esistente; il loader
`80_data/changelog/20260228-18-upsert-config-azioni-processo-mctit.yaml` è
`runOnChange: true` + `validCheckSums: [ANY]` → ripesca da solo. **Nessun loader nuovo**
(stessa nota già scritta nel seed `motivi_fermo`: *«Nuovi codici futuri = append al CSV»*).

Ultimo `id` occupato: **25**. `area_id = 2` = `vendite` (verificato in `aree_funzionali.csv`).

```csv
26,2,approva_attivita_commessa,Approva attivita di commessa per la fatturazione,f,t,{},2026-07-19 00:00:00+02,postgres,2026-07-19 00:00:00+02,postgres
27,2,numera_fatture_lotti,Numerazione fiscale fatture di lotto (irreversibile),t,t,{},2026-07-19 00:00:00+02,postgres,2026-07-19 00:00:00+02,postgres
```

Razionale delle due righe:

| Codename | `pericolosa` | Perché serve |
| --- | :--: | --- |
| `approva_attivita_commessa` | `f` | Gate dell'azione **Approva** (riga, commessa, massiva mese — D-3). Oggi `fn_approva_commessa_attivita` non ha né endpoint né permesso: l'approvazione non è distruttiva ma decide *cosa entra in fattura*, quindi merita un permesso proprio e non va sotto `genera_fatture_lotti` |
| `numera_fatture_lotti` | **`t`** | D-1: la numerazione è **irreversibile** (dopo la DEFINITIVA non c'è rollback, solo NC) e per il massivo è **atto umano esplicito**. Va separata da `genera_fatture_lotti`, che resta il permesso del giro fino a EMESSA (tutto pre-fiscale e demolibile) |

**Non servono altre azioni**: `genera_fatture_lotti` (giro/pipeline), `run_commesse_push`
(push sorgenti), `reset_lotto_draft` / `reset_lotto_fattura_draft` (demolizioni) esistono
già e coprono il resto del cockpit.

---

## 3. D2 — Task di stampa accodato allo step di numerazione (D-1 + D-7)

**I due vincoli di Tid, che convivono.**

* **D-1**: *«il processo che esegue la numerazione include la stampa e deve essere un
  processo unico; i processi devono essere sempre gli stessi, mai duplicati, anche se in
  immediato sono eseguiti diversamente dal massivo.»*
* **D-7**: *«il processo di stampa deve essere separato da tutti gli altri, in pratica
  "stupido": legge tutte le informazioni esistenti e genera un documento / n documenti.»*

Non si contraddicono perché vivono su assi diversi: **un solo atto per l'utente** (D-1) e
**un solo componente, senza logica, per il codice** (D-7). Il modo di ottenerli entrambi in
questo motore è **configurativo**: la stampa diventa un **task accodato a `numera_fatture`
dentro lo stesso step DEFINITIVA**.

* **D-1 soddisfatto per costruzione**: MASSIVO e GIORNALIERO puntano alla stessa coppia di
  task; chiunque avvii lo step (pulsante umano, cron, batch) esegue necessariamente
  entrambi. Nessun chiamante può "dimenticarsi" la stampa, nessuna seconda implementazione
  da tenere allineata.
* **D-7 soddisfatto**: il task è un **adattatore sottile** — dice solo *«questi sono i
  documenti da produrre»* e delega al processo di stampa generico
  (`documenti.DocumentGenerationService`, già sorgente-agnostico e già usato da 5 domini).
  La logica di rendering **non entra** nella pipeline, e il processo di stampa resta
  invocabile **da solo** (ristampa singola, on-demand, ristampa massiva) senza passare dalla
  fatturazione.

> **Perché un task e non uno step dedicato**: gli step del lotto sono **stati fiscali**
> (`config.stati_doc_fiscale`). «Stampata» non è uno stato fiscale e inventarlo sporcherebbe
> la macchina a stati. Il task ha già il suo `task_run` con tentativi/esito ed è
> ri-eseguibile da solo: è esattamente l'unità di lavoro separata che D-7 chiede.

Verificato oggi: la stampa **non è** un task del motore (registry handler:
`select_attivita`, `generate_fatture_righe`, `genera_fondi_source_lotto`,
`applica_fondi_lotto`, `ricalcola_iva_lotto`, `prepare_sdi_payload_lotto`,
`numera_fatture`, `close_lotto`, `reset_lotto_draft`, `pull_attivita_da_commessa`).

### 3.1 `dbops/pipeline_task_registry.csv` (append)

Ultimo `id`: **17**. `dominio_id = 1` (stesso dominio degli altri task di fatturazione).

```csv
18,1,stampa_documenti_lotto,Stampa dei documenti del lotto (delega al processo stampa generico),true,{},2026-07-19 00:00:00+02,titodb,,
```

Nome scelto `stampa_documenti_lotto` (non `genera_stampa_fatture`): dice ciò che il task
**fa davvero** — raccoglie i documenti del lotto e li passa al processo di stampa. La
generazione non è sua (D-7).

### 3.2 `dbops/pipeline_task_registry_impl.csv` (append)

Ultimo `id`: **17**.

```csv
18,18,default,stampa_documenti_lotto_default,true,true,{},2026-07-19 00:00:00+02,titodb,,
```

`handler_code` = `stampa_documenti_lotto_default`: è la chiave che il BE registrerà nel
dispatch di `PipelineStepExecutor` (implementazione lato Python — vedi brief BE/FE, non è
lavoro del team DB).

### 3.3 `vendite/fatturazione_pipeline.csv` — accodare il task ai due step DEFINITIVA

Le righe da toccare sono **due**, e sono simmetriche (è esattamente il punto di D-1):

| id | Step | `processi` oggi | Diventa |
| --- | --- | --- | --- |
| **4** | Pipeline **massiva** (DEFINITIVA), `stato_doc_fiscale_id=8` | `[numera_fatture]` | `[numera_fatture, stampa_documenti_lotto]` |
| **6** | Pipeline **giornaliera** (DEFINITIVA), `stato_doc_fiscale_id=8` | `[numera_fatture]` | `[numera_fatture, stampa_documenti_lotto]` |

Elemento da accodare all'array `processi` (dopo `numera_fatture`, l'ordine conta: si stampa
un documento che ha già il suo numero fiscale):

```json
{"task":"stampa_documenti_lotto","fase":"Generazione stampa fatture","params":{"implementation_key":"default"}}
```

`rollback` resta `[]` su entrambi gli step (dalla DEFINITIVA non si torna indietro).

### 3.4 ⚠️ Decisione da confermare — stampa bloccante o best-effort?

Domanda onesta da chiudere prima di applicare (impatta solo il **comportamento in errore**,
non il seed):

* **Best-effort** *(proposta)*: se la stampa fallisce (template mancante, render in
  errore), la **numerazione resta valida** — non è annullabile — il task-run va in ERRORE, il
  lotto resta segnalato e la stampa è **ri-eseguibile** con un rerun del solo task
  (idempotente). Il documento fiscale esiste, manca solo la sua rappresentazione.
* **Bloccante**: il fallimento stampa fa fallire l'intero step. Ma la numerazione è già
  avvenuta e non si può ritirare → si otterrebbe uno step "fallito" su un fatto compiuto,
  con stato incoerente. Sconsigliato.

La proposta **non indebolisce D-1**: il processo resta **uno solo** (stesso step, stessi due
task, per entrambe le corsie); cambia solo che l'anello ri-eseguibile è trattato come tale.

---

## 4. D3 — Verifica chiusa: nessuna vista nuova per i lotti

Il design ipotizzava una possibile aggregata dei lotti per competenza (**DB-2** del brief di
design). **Verificato: non serve.** `vendite.fatturazione_lotti` è già interrogabile con
tutti i filtri che servono al cockpit, con display fields e scope emittente applicati:
`competenza_mese`, `stato_lotto`, `tipo_doc_fiscale_id`, `emittente_soggetto_ruolo_id`,
`utility_id`, `area_geografica_id` + paginazione
(`VenditeRepository.list_lotti`, esposta da `GET /api/v1/vendite/lotti/`).

➡️ **Nessuna azione DB.** Voce chiusa; la lista/drawer lotti è puro lavoro FE su endpoint
esistenti.

---

## 5. Cosa NON è richiesto (per non cercarlo)

* Nessun DDL: niente colonne, tabelle, indici.
* Nessuna funzione o trigger nuovi: `fn_approva_commessa_attivita`,
  `fn_cambia_stato_commessa`, `fn_available_actions_commessa`,
  `fn_emit_attivita_fatturabili_da_commessa`, `fn_set_fatturazione_lotto_stato` e la
  famiglia task-run coprono già tutto il fabbisogno del cockpit.
* Nessuna modifica alle viste `vw_dash_*`: le tre lenti restano read-only e invariate — le
  azioni sono endpoint di comando **accanto** alla dashboard, non dentro le viste.
* Nessun cambio alla matrice transizioni stati (commessa, doc fiscale): il cockpit usa le
  transizioni esistenti.

---

## 6. Verifica attesa dopo l'apply

```sql
-- D1: le due azioni esistono, attive, sull'area vendite
SELECT id, permission_codename, pericolosa, attivo
FROM config.azioni_processo
WHERE permission_codename IN ('approva_attivita_commessa','numera_fatture_lotti');
-- atteso: 2 righe, attivo=t, numera_fatture_lotti.pericolosa=t

-- D2a: il task è nel registry ed è dispatchabile
SELECT r.task_code, i.handler_code, i.is_default, i.attivo
FROM dbops.pipeline_task_registry r
JOIN dbops.pipeline_task_registry_impl i ON i.task_registry_id = r.id
WHERE r.task_code = 'stampa_documenti_lotto';
-- atteso: 1 riga, handler_code=stampa_documenti_lotto_default, is_default+attivo true

-- D2b: entrambi gli step DEFINITIVA hanno numerazione E stampa, in quest'ordine
SELECT tipo_lotto,
       jsonb_path_query_array(processi, '$[*].task') AS tasks
FROM vendite.fatturazione_pipeline
WHERE stato_doc_fiscale_id = 8 AND attivo;
-- atteso: 2 righe (MASSIVO, GIORNALIERO), entrambe ["numera_fatture","stampa_documenti_lotto"]

-- D2c: nessuna asimmetria fra le due corsie (invariante D-1)
SELECT count(DISTINCT processi) AS varianti
FROM vendite.fatturazione_pipeline
WHERE stato_doc_fiscale_id = 8 AND attivo;
-- atteso: 1  → le due corsie eseguono lo STESSO processo
```

## 7. pgTAP

Un file test è opportuno per l'invariante di D-1, che è la cosa che si può rompere in
silenzio nel tempo (qualcuno aggiunge un task a una corsia sola):

`db/pgtap/vendite/test-pipeline-definitiva-numerazione-stampa-v1.sql`

1. le 2 azioni di processo esistono e sono attive; `numera_fatture_lotti.pericolosa = true`;
2. `stampa_documenti_lotto` è nel registry con un impl `default` attivo;
3. lo step DEFINITIVA MASSIVO contiene `numera_fatture` **seguito da** `stampa_documenti_lotto`;
4. idem per GIORNALIERO;
5. **invariante**: i `processi` dei due step DEFINITIVA attivi sono **identici** (una sola
   variante distinta) — è la traduzione in test di *«mai processi duplicati/divergenti»*.

---

## 8. Sequenza

1. Team DB: conferma §3.4 (best-effort proposto) → applica D1 + D2 → pgTAP verdi → PR.
2. A oggetti applicati parte il **BE/FE** — piano in
   [brief-be-fe-processi-fatturazione.md](brief-be-fe-processi-fatturazione.md),
   che include l'handler Python `stampa_documenti_lotto_default` (il seed qui sopra lo
   dichiara, il codice lo implementa).

*Le azioni DB non le esegue l'agent ([[feedback_db_actions_passaggio_team]]).*
