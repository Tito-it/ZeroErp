# Gestione Soggetti — WIP

> Documento di lavoro per pianificazione e avanzamento della gestione soggetti completa.
> Data: 2026-03-15 | Stato: **DA INIZIARE**
>
> Documenti di riferimento:
>
> * [Guida Soggetti e Ruoli Anagrafici](/guide/soggetti-e-ruoli-anagrafici) — modello dati, trigger, matrici
> * [Guida Gestione degli Indirizzi](/guide/gestione-degli-indirizzi) — due layer, normalizzato/libero
> * [Guida Gestione dei Contatti](/guide/gestione-dei-contatti) — tre livelli contesto, default
> * [Guida Generazione Cliente](/guide/generazione-cliente) — flusso soggetto → ruolo → cliente
> * [Architettura Building Block](componenti-riutilizzabili.md) — building block DB/BE/FE
> * [Sviluppo Indirizzi](sviluppo-indirizzi.md) — gestione geografica (COMPLETATO)
> * [Frontend Standards](/frontend/frontend-standards) — regole UI vincolanti
> * [API Contract](/dev/api) — contratto API REST

---

## Posizionamento nello Sviluppo Concentrico

La gestione soggetti appartiene all'**Anello 1 — Dati Base**.
E' il nucleo anagrafico su cui tutti i domini costruiscono:
clienti, fornitori, operatori, vettori, banche.

```
    Anello 1 (Dati Base)
    ┌────────────────────────────────────────────────────────────┐
    │  Gestione Soggetti (NUOVO)                                 │
    │                                                            │
    │  + CRUD soggetti PF/PG/ENTE con tipo dinamico             │
    │  + Gestione contatti obbligatori (guard DEFERRED)          │
    │  + Gestione indirizzi soggetto (layer identita')           │
    │  + Dati societari per SC/ENC                               │
    │  + Assegnazione ruoli (cliente, fornitore, ecc.)           │
    │  + Frontend: area Anagrafiche > Soggetti                   │
    └────────────────────────────────────────────────────────────┘
           ↑ usa
    Gestione Geografica (COMPLETATO)
    ┌────────────────────────────────────────────────────────────┐
    │  Indirizzi, Toponomastica, Comuni, CAP, Province,          │
    │  Regioni, Stati — CRUD completo, 7 tab                     │
    └────────────────────────────────────────────────────────────┘
```

---

## Strategia: dal piccolo al grande

L'approccio e' **bottom-up**: iniziare dagli elementi atomici piu' piccoli
(config tables, form building block) che generano componenti riutilizzabili,
poi comporli nelle viste complesse.

```
Fase 0 — Config tables manutenzione (tipi_contatti, forme_giuridiche, ecc.)
Fase 1 — Building block form (ContattoForm, IndirizzoForm, DatiSocietariForm)
Fase 2 — Backend API soggetti (repository, service, views)
Fase 3 — Frontend vista soggetti (SoggettoDrawer, SoggettiSearchTable)
Fase 4 — Integrazione ruoli (collegamento con domini futuri)
```

---

## Prerequisiti gia' esistenti

### DB (tutto operativo)

- [x] `anagrafiche.fn_crea_soggetto_pf()` — building block creazione PF con contatto default
- [x] `anagrafiche.fn_crea_indirizzo_soggetto()` — creazione indirizzo layer soggetto
- [x] `anagrafiche.fn_get_or_create_indirizzo_dettaglio()` — upsert civico normalizzato
- [x] `script.fn_get_or_create_soggetto_ruolo()` — assegnazione ruolo con dedup
- [x] Trigger DEFERRED: `E_SOGGETTO_NO_CONTATTI`, `E_SOGGETTO_NO_INDIRIZZI`, `E_DATI_SOCIETARI_REQUIRED`
- [x] Matrici: `tipi_ruoli_nature_ammesse`, `tipi_soggetto_dettaglio_tipi_indirizzo`, `tipi_ruolo_tipi_indirizzo`
- [x] View risolte: `vw_indirizzi_resolved_all`, `vw_soggetti_ruoli_dettaglio`
- [ ] `anagrafiche.fn_crea_soggetto_pg()` — **DA CREARE** per PG (SC, SP, ENC)

### Backend (parziale)

- [x] `AnagraficheCoreRepository.crea_soggetto_pf()` — building block testato
- [x] `AuthRepository.crea_auth_user()` — building block testato
- [x] `RisorseUmaneCoreRepository.crea_risorsa_umana()` — building block testato
- [x] `GeoService` + `GeoRepository` — gestione geografica completa
- [x] `IndirizziRepository` — CRUD indirizzi dettaglio + stradario
- [x] Lookup generico per config tables standard (`/core/lookup/codici/`)

### Frontend (parziale)

- [x] `SoggettoForm.vue` — form universale PF/PG/ENTE guidato da matrice
- [x] `useSoggettoForm.js` — state, computed (isPF, showPartitaIva, showDatiSocietari, matriceIndirizzi)
- [x] `AuthUserForm.vue` + `useAuthUser.js`
- [x] `ComuneAutocomplete.vue`, `StradarioAutocomplete.vue`
- [x] `UtenteDrawer.vue` — esempio di composizione building block (tipoForzato=1)
- [x] Infrastruttura: `useSearchTable`, `useDrawerState`, `DrawerFooter`, `NewButton`

---

## Fase 0 — Config tables manutenzione

Le tabelle config necessarie per soggetti che NON hanno ancora gestione UI.
Seguono lo stesso pattern della gestione geografica (SearchTable + Drawer standard).

### Analisi tabelle config per soggetti

| Tabella | In whitelist | Ha `attivo` | Struttura | UI necessaria |
| --- | --- | --- | --- | --- |
| `config.tipi_contatti` | Si | No | Semplice (codice_interno, descrizione) | Lookup generico sufficiente |
| `config.titoli_cortesia` | Si (aggiunto) | No | Semplice (descrizione, descrizione_breve) | Lookup generico sufficiente |
| `config.tipi_soggetto_dettaglio` | Si | No | Complessa (15 colonne, policy) | CRUD dedicato (futuro) |
| `config.tipi_ruoli` | Si | No | Standard (codice, descrizione) | Lookup generico sufficiente |
| `config.forme_giuridiche` | Si | Si | Complessa (attivo, policy REA/capitale, per-paese) | CRUD dedicato necessario |
| `config.tipi_indirizzi` | Si | No | Semplice (codice_interno, descrizione) | Lookup generico sufficiente |

### CFG-1 — Gestione Forme Giuridiche (CRUD dedicato)

Serve un tab dedicato perche' ha `attivo`, policy REA/capitale_sociale, organizzazione per stato.

**Backend:**
- `GeoRepository`: aggiungere `list_forme_giuridiche()`, `get_forma_giuridica()`, `create_forma_giuridica()`, `update_forma_giuridica()`
- `GeoService`: aggiungere metodi corrispondenti
- View: `FormeGiuridicheView` (GET+POST), `FormeGiuridicheDetailView` (GET+PATCH)
- URL: `GET/POST /anagrafiche/forme-giuridiche/`, `GET/PATCH /anagrafiche/forme-giuridiche/<id>/`

**Frontend:**
- `FormeGiuridicheSearchTable.vue` (core/components)
- `FormeGiuridicheDrawer.vue` (core/components) — campi: descrizione, codice, stato_id (select), rea_policy, capitale_sociale_policy, attivo
- Store `formeGiuridiche.js`
- Tab in IndirizziView (o nuova vista Config) — **da decidere**

**Prerequisiti:** nessuno
**Effort:** 1 sessione

### CFG-2 — Verifica seed data

Controllare che le tabelle config abbiano dati seed completi per l'Italia:
- `tipi_contatti` — 4 tipi (PRINCIPALE, REFERENTE, SEGRETERIA, ALTRO) — OK
- `titoli_cortesia` — 9 titoli — OK
- `tipi_soggetto_dettaglio` — 5 tipi (PR, DI, SP, SC, ENC) — OK
- `tipi_ruoli` — 12 ruoli — OK
- `tipi_indirizzi` — 10 tipi — OK
- `forme_giuridiche` — verificare completezza (SRL, SPA, SNC, SAS, COOP, ecc.)

**Prerequisiti:** nessuno
**Effort:** 30 minuti (solo verifica)

---

## Fase 1 — Building block form frontend

Componenti atomici riutilizzabili. Ogni form e' indipendente e testabile in isolamento.

### BB-1 — ContattoForm.vue + useContattoForm.js

**Scopo:** form contatto associabile a soggetto, ruolo o utility.

**Campi:**

| Campo | Tipo | Obbligatorio | Note |
| --- | --- | --- | --- |
| nominativo | InputText | Si | Nome referente |
| email | InputText | No* | Almeno un canale consigliato |
| telefono | InputText | No | |
| cellulare | InputText | No | |
| pec | InputText | No | |
| tipo_contatto_id | Select (lookup generico) | No | Categoria |
| unita_organizzativa_id | Select | No | Reparto/ufficio |
| note | Textarea | No | |

**Props:**
```js
defineProps({
  form: { type: Object, required: true },
  requireEmail: { type: Boolean, default: false },
  showUO: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false }
})
```

**Composable `useContattoForm(options)`:**
```js
export function useContattoForm(options = {}) {
  const { requireEmail = false } = options
  const form = reactive({ nominativo: '', email: '', telefono: '',
    cellulare: '', pec: '', tipo_contatto_id: null,
    unita_organizzativa_id: null, note: '' })
  // validate(), reset()
}
```

**Collocazione:** `core/components/` — usato da soggetti, clienti, fornitori
**Prerequisiti:** lookup `tipi_contatti` (gia' in whitelist), lookup `unita_organizzative` (gia' esistente)
**Effort:** 1 sessione

### BB-2 — IndirizzoSoggettoForm.vue + useIndirizzoSoggettoForm.js

**Scopo:** form indirizzo per layer soggetto (identita': residenza, sede legale, domicilio fiscale).
Supporta modalita' normalizzata (ComuneAutocomplete + StradarioAutocomplete + civico)
e modalita' libera (indirizzo_libero + stato + comune/locality).

**Campi modalita' normalizzata:**

| Campo | Tipo | Obbligatorio |
| --- | --- | --- |
| tipo_indirizzo_id | Select | Si (filtrato da matrice) |
| comune_id | ComuneAutocomplete | Si |
| stradario / via nuova | StradarioAutocomplete o switch | Si |
| civico, estensione, palazzina, scala, piano, interno | InputText/Number | No (civico consigliato) |

**Campi modalita' libera:**

| Campo | Tipo | Obbligatorio |
| --- | --- | --- |
| tipo_indirizzo_id | Select | Si |
| indirizzo_libero | InputText | Si |
| stato_id | Select | Si |
| comune_id / locality | InputText | Si (uno dei due) |

**Props:**
```js
defineProps({
  form: { type: Object, required: true },
  tipiIndirizzo: { type: Array, default: () => [] }, // filtrati dalla matrice
  disabled: { type: Boolean, default: false }
})
```

**Nota:** questo form e' diverso da `IndirizzoDrawer` (che gestisce indirizzi_dettaglio standalone).
Qui gestiamo `indirizzi_soggetti` — l'assegnazione di un indirizzo a un soggetto con tipo.

**Collocazione:** `core/components/`
**Prerequisiti:** BB-1 non richiesto, ma `ComuneAutocomplete`, `StradarioAutocomplete` gia' esistenti
**Effort:** 1-2 sessioni

### BB-3 — DatiSocietariForm.vue + useDatiSocietariForm.js

**Scopo:** form dati camerali per PG/ENC (SC e ENC obbligatorio, SP opzionale).

**Campi:**

| Campo | Tipo | Obbligatorio | Note |
| --- | --- | --- | --- |
| forma_giuridica_id | Select | Si per SC/ENC | Filtrato da `forme_giuridiche_tipi_soggetto_dettaglio` |
| rea | InputText | Dipende da policy | `rea_policy` della forma giuridica |
| capitale_sociale | InputNumber | Dipende da policy | `capitale_sociale_policy` |

**Visibilita':** controllata da `useSoggettoForm.showDatiSocietari` e `requireDatiSocietari`.

**Props:**
```js
defineProps({
  form: { type: Object, required: true },
  required: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false }
})
```

**Collocazione:** `core/components/`
**Prerequisiti:** CFG-1 (forme giuridiche gestibili)
**Effort:** 1 sessione

---

## Fase 2 — Backend API soggetti

### API-1 — Repository soggetti

File: `backend/apps/anagrafiche/db/soggetti_repository.py`

**Metodi:**

| Metodo | Scopo |
| --- | --- |
| `list_soggetti(search, tipo_soggetto_dettaglio_id, limit, offset, order_by, order_dir)` | Lista paginata con search su ragione_sociale_completa, codice_fiscale, partita_iva |
| `get_soggetto(soggetto_id)` | Dettaglio completo soggetto + tipo + natura |
| `get_soggetto_contatti(soggetto_id)` | Lista contatti del soggetto |
| `get_soggetto_indirizzi(soggetto_id)` | Lista indirizzi layer soggetto |
| `get_soggetto_ruoli(soggetto_id)` | Lista ruoli assegnati |
| `crea_soggetto_pf(payload)` | Chiama `fn_crea_soggetto_pf()` |
| `crea_soggetto_pg(payload)` | Chiama `fn_crea_soggetto_pg()` (**richiede funzione DB**) |
| `update_soggetto(soggetto_id, payload)` | UPDATE campi modificabili |
| `crea_contatto(soggetto_id, payload)` | INSERT in `anagrafiche.contatti` |
| `update_contatto(contatto_id, payload)` | UPDATE contatto |
| `crea_indirizzo_soggetto(soggetto_id, payload)` | Chiama `fn_crea_indirizzo_soggetto()` |

**Prerequisiti:** funzione DB `fn_crea_soggetto_pg()` per PG
**Effort:** 1-2 sessioni

### API-2 — Service soggetti

File: `backend/apps/anagrafiche/services/soggetti_service.py`

**Metodi principali:**

| Metodo | Scopo |
| --- | --- |
| `create_soggetto(payload)` | Orchestratore: determina PF/PG dal tipo, chiama il building block corretto, crea contatto, crea indirizzi. Tutto in una transazione (DEFERRED check al COMMIT) |
| `get_soggetto(soggetto_id)` | Dettaglio + contatti + indirizzi + ruoli |
| `update_soggetto(soggetto_id, payload)` | Aggiorna campi soggetto |
| `create_contatto(soggetto_id, payload)` | Validazione + INSERT |
| `update_contatto(contatto_id, payload)` | Validazione + UPDATE |
| `create_indirizzo_soggetto(soggetto_id, payload)` | Validazione tipo da matrice + INSERT |
| `assign_ruolo(soggetto_id, tipo_ruolo_id)` | Assegna ruolo (chiama `fn_get_or_create_soggetto_ruolo`) |

**Prerequisiti:** API-1
**Effort:** 1-2 sessioni

### API-3 — Views soggetti

File: `backend/apps/anagrafiche/api/views_soggetti.py`

| Endpoint | Metodo | Scopo |
| --- | --- | --- |
| `soggetti/` | GET | Lista paginata con search |
| `soggetti/` | POST | Crea soggetto completo (PF o PG + contatto + indirizzi) |
| `soggetti/<uuid>/` | GET | Dettaglio con contatti, indirizzi, ruoli |
| `soggetti/<uuid>/` | PATCH | Aggiorna soggetto |
| `soggetti/<uuid>/contatti/` | GET | Lista contatti |
| `soggetti/<uuid>/contatti/` | POST | Aggiungi contatto |
| `soggetti/<uuid>/contatti/<id>/` | PATCH | Modifica contatto |
| `soggetti/<uuid>/indirizzi/` | GET | Lista indirizzi soggetto |
| `soggetti/<uuid>/indirizzi/` | POST | Aggiungi indirizzo |
| `soggetti/<uuid>/ruoli/` | GET | Lista ruoli |
| `soggetti/<uuid>/ruoli/` | POST | Assegna ruolo |

**Nota:** soggetti usa UUID come PK, non BIGINT.

**Prerequisiti:** API-2
**Effort:** 1-2 sessioni

### API-4 — Test

- Unit test `soggetti_service.py` (mock repository)
- Smoke test curl `smoke-test-soggetti.sh`

**Prerequisiti:** API-3
**Effort:** 1 sessione

---

## Fase 3 — Frontend vista soggetti

### FE-1 — API client + store

File: `frontend/src/anagrafiche/api/anagrafiche.js` — aggiungere funzioni soggetti
File: `frontend/src/anagrafiche/stores/soggetti.js` — store Pinia

**Prerequisiti:** API-3
**Effort:** 30 minuti

### FE-2 — SoggettoDrawer.vue (composizione building block)

File: `frontend/src/anagrafiche/components/SoggettoDrawer.vue`

Drawer COMPLEX (800px) che compone i building block:

```
┌──────────────────────────────────────────────┐
│ Nuovo Soggetto / Modifica Soggetto           │
├──────────────────────────────────────────────┤
│                                              │
│  SoggettoForm (tipo NON forzato)             │
│    → tipo_soggetto_dettaglio select          │
│    → campi PF (cognome, nome, sesso, ...)    │
│    → campi PG (ragione_sociale)              │
│    → codice_fiscale, partita_iva             │
│                                              │
│  --- Contatto (obbligatorio) ---             │
│  ContattoForm                                │
│    → nominativo, email, telefono, pec        │
│                                              │
│  --- Indirizzo (se obbligatorio da matrice)  │
│  IndirizzoSoggettoForm                       │
│    → tipo, comune, via, civico               │
│                                              │
│  --- Dati Societari (se SC/ENC) ---          │
│  DatiSocietariForm (condizionale)            │
│    → forma giuridica, REA, capitale          │
│                                              │
├──────────────────────────────────────────────┤
│  [Annulla]                      [Salva]      │
└──────────────────────────────────────────────┘
```

Il drawer manda un **payload unificato** al backend:
```json
{
  "tipo_soggetto_dettaglio_id": 1,
  "cognome": "Rossi", "nome": "Mario",
  "codice_fiscale": "...",
  "contatto": { "nominativo": "Mario Rossi", "email": "..." },
  "indirizzo": { "tipo_indirizzo_id": 1, "indirizzo_dettaglio_id": 123 },
  "dati_societari": null
}
```

Il backend (SoggettiService) scompone e chiama i building block nella sequenza corretta,
tutto in una transazione. I trigger DEFERRED verificano al COMMIT.

**Prerequisiti:** BB-1, BB-2, BB-3, FE-1
**Effort:** 2 sessioni

### FE-3 — SoggettiSearchTable.vue + SoggettiView.vue

**SoggettiSearchTable:** DataTable paginata con:
- Search su nome/ragione_sociale/CF/PIVA
- Filtro tipo soggetto (PF/PG/ENTE)
- Colonne: codice, ragione_sociale_completa, codice_fiscale, tipo, comune (se disponibile)
- Click riga → SoggettoDrawer in edit

**SoggettiView:** nuova vista in `anagrafiche/views/` con potenzialmente piu' tab:
- Tab Soggetti (lista + CRUD)
- Tab futuri: contatti per soggetto, indirizzi per soggetto

**Navigazione:** aggiungere voce menu L2 `soggetti` in `DOMAIN_MENUS['anagrafiche']`

**Prerequisiti:** FE-2
**Effort:** 1-2 sessioni

---

## Fase 4 — Integrazione ruoli

### RUOLI-1 — Assegnazione ruolo da drawer soggetto

Aggiungere sezione nel SoggettoDrawer (in edit mode) per:
- Vedere i ruoli assegnati
- Aggiungere un ruolo (select da `tipi_ruoli` filtrato dalla matrice nature ammesse)
- Il backend chiama `fn_get_or_create_soggetto_ruolo`

**Prerequisiti:** FE-3
**Effort:** 1 sessione

### RUOLI-2 — Preparazione per domini clienti/fornitori

Quando si crea un soggetto e si assegna il ruolo CLIENTE:
- Il soggetto diventa disponibile per il dominio `vendite`
- I building block (SoggettoForm, ContattoForm, IndirizzoForm) sono gia' riutilizzabili

Il dominio `vendite` creera' il proprio drawer `ClienteDrawer` che compone:
- SoggettoForm (o seleziona soggetto esistente)
- ContattoForm (contatto commerciale)
- IndirizzoForm (indirizzo spedizione/fatturazione — layer ruolo)
- Campi specifici cliente

**Prerequisiti:** RUOLI-1
**Effort:** da pianificare separatamente

---

## Ordine di esecuzione

```
Passo  Task                                              Prerequisiti    Stato
─────  ────────────────────────────────────────────────   ────────────    ──────
 0.1   CFG-1  Forme giuridiche CRUD                     nessuno         FATTO
 0.2   CFG-2  Verifica seed data config                 nessuno         FATTO
 1.1   BB-1   ContattoForm + useContattoForm            —               FATTO
 1.2   BB-2   IndirizzoSoggettoForm + useIndirizzoForm  —               FATTO
 1.3   BB-3   DatiSocietariForm + useDatiSocietariForm  CFG-1           FATTO
 2.1   API-1  Repository soggetti                       fn_crea_pg (DB) FATTO
 2.2   API-2  Service soggetti                          API-1           FATTO
 2.3   API-3  Views soggetti                            API-2           FATTO
 2.4   API-4  Test                                      API-3           FATTO
 3.1   FE-1   API client + store                        API-3           FATTO
 3.2   FE-2   SoggettoDrawer                            BB-1..3, FE-1   FATTO
 3.3   FE-3   SoggettiSearchTable + View                FE-2            FATTO
 4.1   RUOLI-1 Assegnazione ruoli                       FE-3            FATTO
 4.2   RUOLI-2 Preparazione domini futuri               RUOLI-1         FATTO
```

---

## Dipendenza DB — fn_crea_soggetto_pg

L'unica dipendenza DB bloccante e' la funzione `anagrafiche.fn_crea_soggetto_pg()`.
Deve essere creata sul server DB (migration Liquibase) prima di iniziare la Fase 2.

Firma prevista:
```sql
fn_crea_soggetto_pg(
  p_ragione_sociale text,
  p_codice_fiscale text,
  p_partita_iva text,
  p_tipo_soggetto_dettaglio_id bigint,
  p_email text,
  p_stato_iso2 varchar DEFAULT 'IT',
  p_forma_giuridica_id bigint DEFAULT NULL,
  p_rea text DEFAULT NULL,
  p_capitale_sociale numeric DEFAULT NULL
) RETURNS uuid  -- soggetti.id
```

Deve:
1. INSERT in `anagrafiche.soggetti` con tipo PG
2. INSERT in `anagrafiche.contatti` (contatto default con email)
3. INSERT in `anagrafiche.dati_societari` (se tipo richiede: SC, ENC)
4. Chiamare `fn_get_or_create_soggetto_ruolo` se ruolo specificato

---

## Vincoli DEFERRED — cosa il frontend deve garantire

Il DB verifica al COMMIT della transazione:

| Trigger | Errore | Cosa serve nel form |
| --- | --- | --- |
| `trgfn_soggetti_guard_soggetto_contatti` | `E_SOGGETTO_NO_CONTATTI` | Almeno un contatto con nominativo |
| `trgfn_soggetti_guard_indirizzi_required` | `E_SOGGETTO_NO_INDIRIZZI` | Indirizzi obbligatori dalla matrice tipo |
| `trgfn_soggetti_guard_dati_societari_required` | `E_DATI_SOCIETARI_REQUIRED` | Dati societari per SC/ENC |

Il frontend **non deve validare questi vincoli** — li valida il DB al COMMIT.
Il frontend deve pero' **guidare l'utente** mostrando le sezioni obbligatorie
in base al tipo selezionato (via `useSoggettoForm.indirizziObbligatori` e `requireDatiSocietari`).

---

## Stato: IN TEST UI (completato 15 marzo 2026)

Tutti i task delle 4 fasi sono completati. Il sistema e' in fase di test UI.

### Extra completati (fuori piano originale)

- Pannello config generico (67 tabelle CRUD) con drawer dinamico
- Tab CAP in IndirizziView (CRUD codici postali)
- CF validator italiano con supporto omocodia
- Code review: fix race condition watcher, cleanup timeout, eliminato doppio fetchList

### Note aperte — Tracciamento pratiche

Le operazioni CRUD anagrafiche (crea/modifica soggetto, contatto, indirizzo)
**non** passano dal sistema pratiche (Anello 2).

Il tracciamento attuale e' puramente tecnico (Anello 0):
- Audit DB: `data_insert`, `user_insert`, `data_update`, `user_update` (trigger automatico)
- `tx_id`: correla tutte le scritture nella stessa transazione
- Storicizzazione: snapshot JSONB su UPDATE/DELETE in `storico.<tabella>`
- Request log: ogni chiamata API in `dbops.request_log`

**Non** viene scritto il giornale di bordo (`pratiche.giornale`).

Quando si vorranno orchestrare le operazioni anagrafiche tramite pratica
(es. "Onboarding cliente", "Variazione dati societari"), il service dovra':
1. Aprire una pratica con tipo e flusso appropriato
2. Scrivere nel giornale di bordo ad ogni step significativo
3. Chiudere la pratica al completamento

Questa integrazione e' prevista per Anello 2/3, non per Anello 1 (dati base).

---

*Gestione Soggetti — ZeroERP (15 marzo 2026)*
*Sviluppo Concentrico — Anello 1, Dati Base*
