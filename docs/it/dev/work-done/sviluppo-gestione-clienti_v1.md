# WIP — Sviluppo Gestione Clienti

> **SUPERATO** — Questo documento e' stato spostato e riorganizzato:
>
> * Parte completata: [sviluppo-gestione-clienti.md (work-done)](../work-done/sviluppo-gestione-clienti.md)
> * Parte da fare: [sviluppo-gestione-clienti-v2.md](sviluppo-gestione-clienti-v2.md) — subentro, disdetta, billing account parent/child
>
> Il contenuto sottostante e' conservato come riferimento storico.

---

> Stato originale: IN ANALISI
>
> Data inizio: 23 marzo 2026
>
> Prerequisiti letti: generazione-cliente, gestione-delle-istanze-utility, soggetti-e-ruoli-anagrafici, gestione-pratiche, architettura-permessi-e-autorizzazioni, mappa-concentrica

---

## Obiettivo

Implementare la **gestione clienti** nel frontend e backend di ZeroERP. Il sistema deve essere **riusabile**: lo stesso `ClienteService` viene invocato sia dalla creazione manuale (fuori pratica) sia dal motore pratiche, differenziandosi solo per gli input ricevuti.

---

## Decisione architetturale: discriminante `richiede_pdp`

Il flag `config.utilities.richiede_pdp` viene usato come **unico discriminante** per stabilire:

| `richiede_pdp` | Creazione manuale | Istanza | Indirizzo | Workflow |
|:-:|:-:|:-:|:-:|:-:|
| `false` | Ammessa | Sempre fittizia | Facoltativo (a discrezione operatore) | Non richiesto |
| `true` | Bloccata | Reale (con PDP) | Obbligatorio | Solo via pratiche |

### Motivazione

La correlazione e' reale, non forzata:

- Se un'utility richiede PDP ha per natura un ciclo tecnico complesso (contatore, allaccio, verifica fisica) che giustifica il passaggio per pratiche.
- Se non richiede PDP, il ciclo e' semplificato e la creazione manuale ha senso.
- L'istanza fittizia e' coerente col modello: e' un contenitore tecnico trasparente (la definizione stessa di "fittizia" nel modello DB).
- L'indirizzo, anche se fornito, resta un dato informativo — non un vincolo di erogazione. Il DB lo ammette: `fittizia = true` consente `indirizzo_dettaglio_id` valorizzato o NULL.

### Rischio noto e mitigazione

Se in futuro servira' un'utility senza PDP che richiede comunque il workflow pratiche, bastera' aggiungere un boolean `solo_pratica` su `config.utilities` (default `false`). Operazione da 15 minuti, non vale la pena anticiparla. Questa decisione e' documentata qui per dare contesto futuro.

---

## Decisione architetturale: ClienteService riusabile

Il `ClienteService.crea_cliente()` accetta parametri **opzionali** per istanza e billing account:

```python
def crea_cliente(
    self,
    soggetto_id,           # obbligatorio
    utility_id,            # obbligatorio
    # --- opzionali: se forniti, usa quelli esistenti ---
    istanza_utility_id=None,
    billing_account_id=None,
    # --- dati per generazione automatica ---
    indirizzo_dettaglio_id=None,
    billing_account_data=None,  # dict con dati BA se immessi a video
    ...
)
```

### Comportamento condizionale

| Parametro | Fornito | Non fornito |
| --- | --- | --- |
| `istanza_utility_id` | Usa l'istanza esistente (validandola) | Crea istanza fittizia in trasparenza |
| `billing_account_id` | Usa il BA esistente (validandolo) | Crea BA automaticamente (gen_codice trigger) |
| `billing_account_data` | Usa i dati immessi dall'operatore per il BA | Valori default (generazione trasparente) |

### Chi chiama il service

| Chiamante | `istanza_utility_id` | `billing_account_id` | Scenario |
| --- | --- | --- | --- |
| Creazione manuale (fuori pratica) | `NULL` — genera | `NULL` — genera | Utility con `richiede_pdp = false` |
| Motore pratiche (handler flusso) | Valorizzato — gia' creato dal flusso | Valorizzato o NULL | Utility con `richiede_pdp = true` |
| Subentro (futuro) | `NULL` — genera nuova | `NULL` — genera nuovo | Chiude il precedente, crea nuovo ciclo |

Questo rende il service un **building block riusabile** senza duplicazione di logica tra creazione manuale e pratiche.

---

## Billing account: visibilita' e input operatore

Il billing account e' **sempre visibile** nel drawer cliente (sia in creazione che in visualizzazione).

### Regole di compilazione

| Scenario | Comportamento |
| --- | --- |
| BA generato in trasparenza | Codice auto (trigger), dati default. Visibile in sola lettura dopo la creazione |
| BA con dati richiesti | L'operatore compila i campi necessari (es. fatturazione_ordini, parent_account). Il drawer mostra la sezione BA editabile |
| BA gia' esistente (da pratica) | Arriva pre-compilato, visibile in sola lettura |

In modifica cliente, la sezione BA e' sempre visibile con i dati correnti.

---

## Flusso operativo (creazione manuale)

```
Operatore apre ClienteDrawer in modalita' "crea"
  1. Seleziona soggetto (SoggettoResolver — building block esistente)
  2. Sceglie utility (Select filtrato: solo utility con richiede_pdp = false)
     → guard utility_tipo_ruolo verifica compatibilita' automaticamente
  3. Opzionalmente collega un indirizzo del soggetto
  4. Opzionalmente compila dati billing account (se non automatizzato)
  5. Conferma

Backend (ClienteService) — transazione atomica:
  a. fn_get_or_create_soggetto_ruolo(soggetto_id, 'CL') → ruolo CLIENTE
  b. istanza_utility_id non fornito →
     INSERT istanza_utilities (fittizia=true, soggetto_id, indirizzo_dettaglio_id opzionale)
  c. billing_account_id non fornito →
     INSERT billing_account (istanza_utility_id, soggetto_ruolo_id, utility_id, + dati operatore)
  d. INSERT clienti (istanza_utility_id, billing_account_id, soggetto_ruolo_id, stato=AT)

I trigger DB fanno il resto:
  - gen_codice su istanza e BA
  - normalize e guard su tutte le tabelle
  - sync_utility_from_ba su clienti
  - set_periodo su clienti
```

---

## Piano di sviluppo per step

### STEP 1 — Backend: ClienteService (orchestrator) ✅ FATTO

**Completato 23 marzo 2026** — `clienti_repository.py` + `clienti_service.py` riusabile (manuale + pratiche)

Crea il service che incapsula la sequenza di creazione in una transazione atomica.

| # | Task | File | Note |
|:-:|------|------|------|
| 1.1 | Repository: INSERT istanza + BA + cliente | `apps/anagrafiche/repositories/cliente_repository.py` | SQL diretto con cursor, sfrutta trigger DB |
| 1.2 | Repository: lista clienti + dettaglio | stesso file | Vista `vw_clienti_dettaglio` (da creare se non esiste) |
| 1.3 | Service: `crea_cliente()` riusabile | `apps/anagrafiche/services/cliente_service.py` | Accetta istanza_utility_id e billing_account_id opzionali: se forniti li valida e usa, se NULL li genera. Riusabile da creazione manuale e da pratiche |
| 1.4 | Service: `get_detail()`, `list_clienti()` | stesso file | Lettura con filtri |
| 1.5 | Test unitari service | `apps/anagrafiche/tests/services/test_cliente_service.py` | Test: creazione con generazione automatica, creazione con istanza/BA pre-esistenti, validazione utility, flusso completo |

### STEP 2 — Backend: API endpoint ✅ FATTO

**Completato 23 marzo 2026** — 3 endpoint + 14 test unitari + smoke test bash

| # | Task | File | Note |
|:-:|------|------|------|
| 2.1 | Endpoint POST `/api/v1/anagrafiche/clienti/` | `apps/anagrafiche/api/cliente_views.py` | Creazione cliente (chiama ClienteService) |
| 2.2 | Endpoint GET `/api/v1/anagrafiche/clienti/` | stesso file | Lista con paginazione, filtri: search, utility_id, stato_cliente_id |
| 2.3 | Endpoint GET `/api/v1/anagrafiche/clienti/{id}/` | stesso file | Dettaglio cliente con dati istanza + BA + soggetto |
| 2.4 | Endpoint lookup utility ammesse | `apps/anagrafiche/api/cliente_views.py` o core | GET utility con `richiede_pdp = false` per popolare il Select |
| 2.5 | URL routing | `apps/anagrafiche/api/urls_v1.py` | Aggiungere rotte clienti |
| 2.6 | Test API | `apps/anagrafiche/tests/api/test_cliente_api.py` | Test endpoint con mock |
| 2.7 | Documentazione API | `docs/it/backend/anagrafiche/manual/api_clienti.md` | Standard manual template |

### STEP 3 — DB: Vista dettaglio clienti ✅ FATTO (non necessaria)

**Completato 23 marzo 2026** — JOIN diretto nel repository, coerente col pattern SoggettiRepository

| # | Task | Note |
|:-:|------|------|
| 3.1 | Verifica se `vw_clienti_dettaglio` o equivalente esiste gia' | Potrebbe bastare un JOIN nel repository |
| 3.2 | Se serve: creare vista in `migrations_v2/20_code/` | Join clienti + istanza + BA + soggetto + utility + stato_cliente |
| 3.3 | Documentazione vista | `docs/it/dbzero/anagrafiche/views/` |

### STEP 4 — Frontend: Store e API client

**Priorita': MEDIA — dopo che backend funziona**

| # | Task | File | Note |
|:-:|------|------|------|
| 4.1 | API functions | `frontend/src/anagrafiche/api/anagrafiche.js` | `listClienti()`, `getCliente()`, `createCliente()`, `lookupUtilitiesManual()` |
| 4.2 | Store Pinia | `frontend/src/anagrafiche/stores/clienti.js` | Pattern standard: filters, items, totalRecords, fetchList, fetchDetail |

### STEP 5 — Frontend: Componenti UI

**Priorita': MEDIA — ultimo step funzionale**

| # | Task | File | Note |
|:-:|------|------|------|
| 5.1 | ClientiSearchTable | `frontend/src/anagrafiche/components/ClientiSearchTable.vue` | Vedi dettaglio sotto |
| 5.2 | ClienteDrawer (creazione) | `frontend/src/anagrafiche/components/ClienteDrawer.vue` | SoggettoResolver + Select utility + indirizzo opzionale + sezione BA |
| 5.3 | ClienteDrawer (visualizzazione/modifica) | stesso file | Dati cliente editabili, istanza (readonly), BA (sempre visibile) |
| 5.4 | Integrazione in sezione Anagrafiche | Da decidere | Tab "Clienti" nella navigazione, con routing dedicato |
| 5.5 | i18n chiavi it/en | `frontend/src/locales/it.json`, `en.json` | Chiavi `clienti.*` |

#### 5.1 — ClientiSearchTable: specifica dettagliata

La ClientiSearchTable segue il pattern della SoggettiSearchTable ma con **filtri e colonne specifici per il dominio clienti**.

**Filtri toolbar:**

| Filtro | Componente | Note |
| --- | --- | --- |
| Ricerca testo | InputText | Cerca su ragione_sociale, codice_fiscale, codice_cliente |
| Utility | Select | Filtro per utility (tutte, non solo richiede_pdp=false) |
| Stato cliente | Select | AT, CH, AN, ecc. da `config.stati_cliente` |

**Colonne DataTable:**

| Colonna | Campo | Note |
| --- | --- | --- |
| Codice | `codice_cliente` | Codice generato dal BA |
| Ragione sociale | `ragione_sociale_completa` | Dal soggetto |
| Codice fiscale | `codice_fiscale` | Dal soggetto |
| Utility | `utility_descrizione` | **Al posto della colonna "Ruoli"** presente in SoggettiSearchTable. Mostra le utility attive del cliente (tag colorati come i ruoli) |
| Stato | `stato_cliente_descrizione` | Badge colorato (AT=success, CH=danger, AN=warn) |
| Data attivazione | `data_attivazione` | Formattata con displayDate |

**Differenze principali rispetto a SoggettiSearchTable:**

- Colonna **Utility** al posto di **Ruoli** — il contesto e' diverso: qui interessa sapere su quali servizi il soggetto e' cliente, non quali ruoli ha
- Filtro **Stato cliente** — specifico del dominio clienti
- Filtro **Utility** — per filtrare per tipo servizio
- Nessuna colonna azioni inline (contatti, indirizzi) — queste azioni saranno nel drawer dettaglio

#### 5.2/5.3 — ClienteDrawer: sezione Billing Account

Il drawer cliente include una sezione dedicata al **billing account**, sempre visibile:

**In creazione:**

- Se la generazione BA e' automatica (default): sezione BA non mostrata, generato in trasparenza
- Se servono dati dall'operatore: sezione BA editabile con campi `fatturazione_ordini`, `parent_account_id`
- Dopo il salvataggio: codice BA generato visibile in sola lettura

**In visualizzazione/modifica:**

- Sezione BA sempre visibile con: codice, utility, parent account, validita'
- Dati BA in sola lettura (le modifiche al BA passano per un eventuale drawer dedicato futuro)

### STEP 6 — Permessi e azioni processo

**Priorita': BASSA — puo' seguire dopo il primo rilascio funzionale**

| # | Task | Note |
|:-:|------|------|
| 6.1 | Seed azioni processo | `anagrafiche.crea_cliente`, `anagrafiche.modifica_cliente`, `anagrafiche.disattiva_cliente` |
| 6.2 | Prop `action` su NewButton e DrawerFooter | Come fatto per operatori |
| 6.3 | Backend: decorare endpoint con `@extend_schema` + `ZeroERPPermission` | Area `anagrafiche` |

### STEP 7 — Contatti, indirizzi e conti bancari a livello cliente (ruolo) ✅ FATTO

**Completato 23 marzo 2026** — contatti + conti bancari a livello ruolo, indirizzi a livello soggetto

Il ClienteDrawer in modalita' edit deve mostrare indirizzi e conti bancari con **due livelli**:

- **Livello soggetto** (ereditati, sola lettura): indirizzi e conti del soggetto, non modificabili dal contesto cliente. Visibili come fallback.
- **Livello ruolo/cliente** (specifici, modificabili): indirizzi e conti collegati al `soggetto_ruolo_id` del cliente. L'operatore puo' aggiungere, modificare, eliminare.

Pattern UX: stesso standard grafico della gestione soggetti (sezione in fondo al drawer con lista esistenti + pulsante aggiungi), ma con distinzione visiva tra ereditati e specifici.

#### Cosa esiste gia'

| Componente | Stato | Note |
| --- | --- | --- |
| Backend API conti ruolo | Operativo | `GET/POST /ruoli/{soggetto_ruolo_id}/conti-bancari/`, `PATCH/DELETE .../conti-bancari/{cb_id}/` |
| Backend API indirizzi soggetto | Operativo | `GET/POST /soggetti/{id}/indirizzi/` — gli indirizzi sono sempre del soggetto |
| Frontend ContiBancariDrawer | Operativo (solo context soggetto) | Commento nel codice prevede gia' context "ruolo" |
| Frontend IndirizziSoggettoDrawer | Operativo | Filtra tipi ammessi da matrice DB |

#### Cosa manca

| # | Task | Dettaglio |
| --- | --- | --- |
| 7.1 | API functions frontend per conti ruolo | `listRuoloContiBancari(ruoloId)`, `createRuoloContoBancario(ruoloId, payload)`, `updateRuoloContoBancario(ruoloId, cbId, payload)`, `deleteRuoloContoBancario(ruoloId, cbId)` in `anagrafiche.js` |
| 7.2 | ContiBancariDrawer: branching context ruolo | Aggiungere prop `context` ('soggetto' o 'ruolo') e `ruoloId`. Se context='ruolo', usa API ruolo invece di API soggetto |
| 7.3 | ClienteDrawer: sezione indirizzi a due livelli | Lista indirizzi soggetto (readonly, badge "Soggetto") + lista/form indirizzi ruolo (editabili, badge "Cliente"). Da valutare se servono API indirizzi a livello ruolo o se bastano quelli del soggetto con filtro tipo |
| 7.4 | ClienteDrawer: sezione conti a due livelli | Lista conti soggetto (readonly, badge "Soggetto") + lista/form conti ruolo (editabili, badge "Cliente"). Usa ContiBancariDrawer con context='ruolo' |
| 7.5 | Distinzione visiva ereditati vs specifici | Card con bordo/sfondo diverso: ereditati (grigio chiaro, no azioni), specifici (bordo primario, azioni edit/delete) |

#### Schema visivo nel drawer (edit mode)

```text
--- Indirizzi ---
  [Badge: Soggetto]  RES — Via Roma 1, Milano          (readonly, sfondo grigio)
  [Badge: Soggetto]  DOMFISC — Via Roma 1, Milano       (readonly, sfondo grigio)
  [Badge: Cliente]   SPED — Via Verdi 5, Roma           (click → modifica)
  [Badge: Cliente]   FATT — Via Verdi 5, Roma           (click → modifica)
  [+ Aggiungi indirizzo cliente]

--- Conti Bancari ---
  [Badge: Soggetto]  IT60X054...  INCASSO              (readonly, sfondo grigio)
  [Badge: Cliente]   IT80Y032...  PAGAMENTO             (click → modifica)
  [+ Aggiungi conto cliente]
```

### STEP 8 — Funzionalita' avanzate (fuori scope prima release)

**Priorita': FUTURA — non ora**

| # | Task | Note |
| --- | --- | --- |
| 8.1 | Subentro manuale | Richiede `fn_subentro_cliente` + nuovo ciclo — solo per utility con PDP, quindi solo via pratiche |
| 8.2 | Disdetta manuale | `fn_disdetta_cliente` — da valutare se ammessa fuori pratica |

---

## Building block gia' disponibili (riuso)

| Componente | Dove | Uso previsto |
|-----------|------|-------------|
| SoggettoResolver | `core/components/SoggettoResolver.vue` | Selezione soggetto nel drawer creazione |
| useSearchTable | `core/composables/useSearchTable.js` | Lista clienti paginata |
| useDrawerState | `core/composables/useDrawerState.js` | Gestione apertura/chiusura drawer |
| useTabFreshness | `core/composables/useTabFreshness.js` | Auto-refresh lista dopo save |
| fn_get_or_create_soggetto_ruolo | `script` (DB) | Creazione/recupero ruolo CLIENTE automatico |
| fn_guard_utility_tipo_ruolo | `script` (DB) | Guard combinazione utility/ruolo |
| trgfn_billing_account_gen_codice | `anagrafiche` (DB) | Generazione codice BA automatica |
| trgfn_istanze_utilities_gen_codice | `anagrafiche` (DB) | Generazione codice istanza automatica |

---

## Documenti da aggiornare dopo implementazione

| Documento | Aggiornamento |
|-----------|--------------|
| `docs/it/guide/generazione-cliente.md` | Sezione "Creazione manuale" con il flusso, il discriminante `richiede_pdp` e i vincoli |
| `docs/it/guide/gestione-delle-istanze-utility.md` | Postilla: istanza fittizia generata automaticamente per utility senza PDP |
| `docs/it/mappa-concentrica.md` | Aggiornare stato "ClienteService" da "breve termine" a "in corso" / "fatto" |
| `docs/it/dbzero/config/manual/utilities.md` | Documentare uso di `richiede_pdp` come discriminante creazione manuale |

---

*WIP — Gestione Clienti — ZeroERP (marzo 2026)*
