# WIP — Sviluppo Preventivi: Backend + Frontend

> Stato: DA IMPLEMENTARE
>
> Data: aprile 2026
>
> Prerequisiti DB:
>
> * Schema `vendite` operativo: preventivi, preventivi_righe, preventivi_indirizzi, note_preventivo
> * Schema `acquisti` operativo: ordini, ordini_righe, ddt (pattern fornitore via `soggetto_ruolo_id`)
> * Schema `config` operativo: stati_doc_preventivi, termini_pagamento, valute, iva
> * Schema `catalogo` operativo: articoli, articoli_uom_operativa, unita_misura
> * Listini operativi: listini, listini_versioni, listini_righe, listini_associazioni
> * Commesse operative: commesse, commesse_attivita, commesse_sorgenti, attivita_fatturabili
> * Funzioni DB operative: `fn_list_preventivi_da_pushare`, `fn_get_or_create_commessa`, `fn_upsert_commessa_attivita`, `fn_emit_attivita_fatturabili_da_commessa`, `fn_resolve_prezzo_listino`
> * Trigger operativi: `trgfn_preventivi_gen_codice`, `trgfn_preventivi_normalize`
>
> Riferimenti:
>
> * [gestione-commesse-v2.md](gestione-commesse-v2.md) — architettura commesse e pipeline fatturazione
> * [../work-done/gestione-articoli.md](../work-done/gestione-articoli.md) — dominio catalogo completato (articoli, UoM, BoM, note)
> * [sviluppo-listini.md](sviluppo-listini.md) — backend+frontend listini + architettura pricing + resolver
> * [docs/it/guide/gestione-commesse.md](../../guide/gestione-commesse.md) — API commesse DB layer
> * [docs/it/guide/fatturazione.md](../../guide/fatturazione.md) — pipeline fatturazione
> * [docs/it/dev/api.md](../api.md) — linee guida API
> * [docs/it/dev/frontend/frontend-standards.md](../frontend/frontend-standards.md) — standard frontend

---

## Contesto

Il documento copre **due direzioni** del preventivo:

1. **Preventivo di vendita** (`vendite.preventivi`) — offerta al cliente, legata a BA/utility. Tabelle DB mature, pipeline commesse/fatturazione operativa. Manca backend + frontend.
2. **Preventivo di acquisto** (`acquisti.preventivi`) — richiesta di preventivo al fornitore (RFQ). Tabelle DB **da creare**, seguendo il pattern gia' consolidato in `acquisti.ordini` (controparte via `soggetto_ruolo_id` del fornitore).

Entrambi condividono: articoli da catalogo, UoM operative, macchina a stati, revisioni, note, indirizzi snapshot. Il preventivo di vendita si predispone alla **fatturazione** (via commesse/attivita_fatturabili) e all'**esecuzione tramite pratiche**. Il preventivo di acquisto si predispone alla **generazione ordine fornitore** (`acquisti.ordini`).

### Due schemi, stesso pattern anagrafico

| Aspetto | Preventivo vendita | Preventivo acquisto |
|---------|-------------------|---------------------|
| Schema | `vendite` | `acquisti` |
| Controparte | `billing_account_id` (cliente/BA) | `soggetto_ruolo_id` (fornitore) |
| Contesto | `utility_id`, `istanza_utility_id` | Opzionale (dipende dal tipo fornitura) |
| Downstream | Commessa → AF → fatturazione | Ordine fornitore (`acquisti.ordini`) |
| Pratiche | Si (esecuzione operativa) | Si (es. sopralluogo, verifica tecnica) |
| App Django | `apps/vendite/` | `apps/acquisti/` |
| Endpoint | `/api/v1/vendite/preventivi/` | `/api/v1/acquisti/preventivi/` |

---

---

## PARTE A — Preventivo di vendita (`vendite.preventivi`)

---

## 1. Perimetro funzionale

### 1.1 Gestione preventivi vendita (core)

1. **CRUD testata preventivo**: creazione, modifica, consultazione, disattivazione
2. **Gestione righe preventivo**: articoli da catalogo, quantita', prezzi (da listino o manuali), sconto, IVA, UoM operativa con conversione
3. **Revisioni**: creazione nuova revisione da preventivo esistente, attivazione/disattivazione revisione
4. **Indirizzi preventivo**: snapshot indirizzi da soggetto/BA con tipo indirizzo
5. **Note preventivo**: note testata e note riga, markdown, visibilita'/solo stampa
6. **Cambio stato**: transizioni controllate sulla macchina a stati del preventivo
7. **Calcolo totali**: ricalcolo automatico imponibile, IVA, totale documento
8. **Validita' temporale**: date validita' dal/al con controllo coerenza
9. **Competenza**: mese di competenza allineato al primo del mese
10. **Stampa/PDF**: generazione documento preventivo (fuori scope v1, predisposto)

### 1.2 Integrazione listini e pricing

1. **Risoluzione prezzo da listino**: quando si aggiunge un articolo alla riga, il sistema propone il prezzo risolto via `fn_resolve_prezzo_listino` (dimensioni: articolo + UoM + BA/utility/emittente + data competenza)
2. **Override manuale**: l'operatore puo' sovrascrivere il prezzo proposto dal listino
3. **Snapshot prezzo**: il prezzo confermato viene salvato nella riga (`prezzo_unitario`), sganciato dal listino (il listino puo' cambiare senza effetto sui preventivi gia' emessi)
4. **UoM operativa**: selezione UoM dalla lista delle UoM operative dell'articolo, con `factor_to_base` snapshotato nella riga

### 1.3 Integrazione fatturazione (via commesse)

Il preventivo **non genera fatture direttamente**. Il flusso e':

```
PREVENTIVO (ACCETTATO)
    |
    | fn_list_preventivi_da_pushare() — discovery preventivi eleggibili
    v
COMMESSA (fn_get_or_create_commessa)
    |
    | fn_upsert_commessa_attivita — righe operative con segment_key PREV:{uid}:R:{riga_id}
    v
COMMESSE_ATTIVITA (stato_approvazione: APPROVATA, stato_emissione: NON_EMESSA)
    |
    | fn_emit_attivita_fatturabili_da_commessa — pull deterministico e idempotente
    v
ATTIVITA_FATTURABILI
    |
    v
PIPELINE FATTURAZIONE (lotti -> fatture)
```

**Funzionalita' backend per l'integrazione:**

1. **Push preventivo in commessa**: endpoint che invoca il flusso discovery -> get_or_create_commessa -> upsert righe. Puo' essere manuale (operatore) o automatico (su accettazione)
2. **Fatturazione immediata**: preventivi con `fatturazione_immediata = true` vengono instradati verso lotto giornaliero automaticamente
3. **Monitoraggio stato fatturazione**: dal preventivo si deve poter vedere se le righe sono state emesse come attivita' fatturabili e se sono state fatturate

### 1.4 Integrazione pratiche (esecuzione operativa)

I preventivi accettati possono generare pratiche per l'esecuzione operativa delle attivita' previste (es. installazione, attivazione, sopralluogo).

#### 1.4.1 Tabella ponte `pratiche.pratiche_sorgenti`

**Decisione**: collegamento via tabella ponte (pattern `commesse_sorgenti`), non colonne dirette.

**Motivazione**: la pratica e' un aggregatore operativo — puo' servire piu' sorgenti commerciali
(es. preventivo + ordine successivo) e un preventivo puo' generare piu' pratiche. Colonne dirette
limiterebbero a relazione 1:1. Il pattern tabella ponte e' gia' collaudato su `vendite.commesse_sorgenti`.

```
pratiche.pratiche_sorgenti
├── id (bigint PK)
├── pratica_id (bigint FK → pratiche.pratiche)
├── sorgente_tipo_id (bigint FK → config.sorgenti)
├── sorgente_uid (text)              -- es. UUID del preventivo
├── sorgente_riga (bigint NULL)      -- es. ID riga preventivo (opzionale)
├── ruolo_link (varchar, default 'ROOT')  -- ROOT, COLLEGATO
├── meta (jsonb, default '{}')
├── storicizza (boolean, default true)
├── tx_id (uuid)
├── audit columns
└── UNIQUE (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
```

Relazioni supportate:

| Direzione | Cardinalita' | Query |
|-----------|:------------:|-------|
| Preventivo → pratiche | 1:N | `WHERE sorgente_tipo = 'PREVENTIVO' AND sorgente_uid = :uid` |
| Pratica → preventivi | N:1 | `WHERE pratica_id = :id AND sorgente_tipo = 'PREVENTIVO'` |
| Pratica → sorgenti miste | N:M | `WHERE pratica_id = :id` (preventivo + ordine + contratto...) |

#### 1.4.2 Contesto anagrafico sulla pratica

Quando si genera una pratica da preventivo, i campi anagrafico della pratica vengono precompilati:

| Campo pratica | Origine | Note |
|---------------|---------|------|
| `emittente_fiscale_id` | Dal BA del preventivo | Obbligatorio |
| `soggetto_id` | Dal soggetto del BA | Obbligatorio |
| `soggetto_ruolo_id` | Dal ruolo del BA | E' il campo chiave per il contesto operativo |
| `istanza_utility_id` | Dal preventivo | Opzionale (solo utility) |

La catena anagrafica sulla pratica e' validata dal trigger `trgfn_pratiche_guard_contesto`:
istanza richiede ruolo, ruolo richiede soggetto.

#### 1.4.3 Contratto parametri handler — come il flusso accede al preventivo

Il contratto `BaseFlussoHandler.execute()` gia' riceve `flusso_id` e `pratica_id` come parametri diretti:

```python
class BaseFlussoHandler(Protocol):
    def execute(
        self,
        flusso_id: int,               # ← ID istanza flusso
        pratica_id: int,               # ← ID pratica padre
        meta: dict[str, Any],          # runtime JSONB dal flusso
        handler_params: dict[str, Any], # config statica dal template
    ) -> dict[str, Any]: ...
```

La catena di risalita dal flusso al preventivo e':

```
flusso_id (parametro diretto)
    ↓
pratica_id (parametro diretto)
    ↓ query pratiche.pratiche
    ├── soggetto_ruolo_id     ← contesto operativo principale
    ├── soggetto_id
    ├── istanza_utility_id
    ├── emittente_fiscale_id
    ↓ query pratiche.pratiche_sorgenti
    └── sorgente_uid          ← UUID del preventivo di origine
         ↓ query vendite.preventivi (WHERE uid = sorgente_uid)
         ├── billing_account_id
         ├── righe, prezzi, articoli
         └── tutto il contesto commerciale
```

**Nessuna modifica al contratto handler e' necessaria.** Il `pratica_id` gia' presente
consente la navigazione completa: pratica → contesto anagrafico + sorgenti → preventivo.

Il campo `meta` JSONB del flusso resta disponibile per dati runtime aggiuntivi
(es. note operatore, scelte fatte durante l'esecuzione dello step), ma i
riferimenti strutturali sono tutti in tabelle relazionali con FK e validazione DB.

#### 1.4.4 Funzionalita'

1. **Generazione pratica da preventivo**: creazione pratica con contesto precompilato (§1.4.2) + record in `pratiche_sorgenti` con `sorgente_tipo = 'PREVENTIVO'` e `sorgente_uid = preventivo.uid`. L'operatore sceglie il tipo pratica e i flussi da attivare
2. **Link bidirezionale**: dal preventivo si vedono le pratiche collegate (query su `pratiche_sorgenti`), dalla pratica si risale al preventivo di origine
3. **Stato esecuzione**: il completamento della pratica non cambia automaticamente lo stato del preventivo, ma l'operatore ha visibilita' per procedere con la fatturazione
4. **Pratiche multiple**: un preventivo puo' generare piu' pratiche (es. una per sopralluogo, una per installazione)
5. **Sorgenti multiple**: una pratica puo' essere collegata a piu' sorgenti (es. preventivo + ordine + contratto) con ruoli distinti (ROOT, COLLEGATO)

### 1.5 Fuori scope v1

1. Generazione PDF/stampa preventivo
2. Firma digitale / accettazione online cliente
3. Import/export massivo preventivi
4. Duplicazione automatica preventivo
5. Template preventivi predefiniti
6. Workflow approvazione interna multi-livello

---

## 2. Macchina a stati del preventivo vendita

### Stati documento (`config.stati_doc_preventivi`)

| Codice | Descrizione | Modificabile | Fatturabile | Genera pratica |
|--------|-------------|:------------:|:-----------:|:--------------:|
| BOZZA | Preventivo in preparazione | si | no | no |
| EMESSO | Preventivo emesso/inviato al cliente | no (solo campi limitati) | no | no |
| ACCETTATO | Cliente ha accettato | no | si | si |
| RIFIUTATO | Cliente ha rifiutato | no | no | no |
| SCADUTO | Superata validita_al senza risposta | no | no | no |
| ANNULLATO | Annullato dall'operatore | no | no | no |

### Transizioni ammesse

```
BOZZA ---------> EMESSO ---------> ACCETTATO ---------> (push commessa / genera pratica)
                    |                   |
                    |                   +-> ANNULLATO
                    +-> RIFIUTATO
                    +-> SCADUTO
                    +-> ANNULLATO

BOZZA ---------> ANNULLATO (cancellazione diretta bozza)
```

### Regole di transizione

1. Da BOZZA a EMESSO: richiede almeno una riga attiva e totale_documento > 0
2. Da EMESSO a ACCETTATO: conferma operatore (o integrazione esterna futura)
3. Da EMESSO a RIFIUTATO/SCADUTO: irreversibile
4. Da qualsiasi stato a ANNULLATO: ammesso sempre, ma se gia' fatturato richiede storno
5. La revisione (`rev`) e' ammessa solo su preventivi EMESSI o ACCETTATI: crea nuova rev in BOZZA

---

## 3. Architettura backend (vendita)

### 3.1 Struttura app Django

```
apps/vendite/
  api/
    preventivi_views.py         # View per preventivi (testata + righe + indirizzi)
    preventivi_urls.py          # URL patterns /api/v1/vendite/preventivi/...
  services/
    preventivi_service.py       # Orchestrazione: CRUD, cambio stato, push commessa, genera pratica
  db/
    preventivi_repository.py    # Accesso DB: list, detail, create, update, righe, indirizzi, note
  types.py                      # TypedDict per preventivi (estendere file esistente)
  tests/
    api/
      test_preventivi_api.py    # Test endpoint HTTP
    services/
      test_preventivi_service.py # Test logica service
```

### 3.2 Repository (`preventivi_repository.py`)

Operazioni raggruppate per contesto:

**Testata:**

| Funzione | Tipo | Note |
|----------|------|------|
| `fn_list_preventivi` | READ | Lista paginata con filtri (stato, BA, utility, data_da/data_al, search) |
| `fn_get_preventivo` | READ | Dettaglio singolo con JOIN su stato, BA, utility, valuta, termini |
| `fn_create_preventivo` | WRITE | INSERT testata con validazione campi obbligatori |
| `fn_update_preventivo` | WRITE | UPDATE campi modificabili (dipende dallo stato) |
| `fn_cambia_stato_preventivo` | WRITE | UPDATE stato con validazione transizione |
| `fn_crea_revisione` | WRITE | INSERT nuova rev copiando testata + righe, disattiva rev precedente |

**Righe:**

| Funzione | Tipo | Note |
|----------|------|------|
| `fn_list_righe_preventivo` | READ | Righe con JOIN articolo, UoM, IVA |
| `fn_create_riga_preventivo` | WRITE | INSERT riga con risoluzione prezzo da listino |
| `fn_update_riga_preventivo` | WRITE | UPDATE riga (prezzo, qta, sconto) |
| `fn_delete_riga_preventivo` | WRITE | DELETE logica (attivo = false) o fisica |
| `fn_ricalcola_totali_preventivo` | WRITE | Ricalcolo totali testata da righe |

**Indirizzi:**

| Funzione | Tipo | Note |
|----------|------|------|
| `fn_list_indirizzi_preventivo` | READ | Indirizzi con tipo |
| `fn_upsert_indirizzo_preventivo` | WRITE | Upsert con snapshot JSONB |

**Integrazione:**

| Funzione | Tipo | Note |
|----------|------|------|
| `fn_push_preventivo_a_commessa` | WRITE | Invoca fn_list_preventivi_da_pushare + fn_get_or_create_commessa + fn_upsert_commessa_attivita |
| `fn_stato_fatturazione_preventivo` | READ | Stato delle righe nel pipeline (commessa -> AF -> fatturato) |

### 3.3 Service (`preventivi_service.py`)

Orchestrazione ad alto livello:

| Metodo | Scopo |
|--------|-------|
| `list_preventivi(filtri, auth_user_id, page, page_size)` | Lista con filtro emittente |
| `get_preventivo(preventivo_id)` | Dettaglio completo (testata + righe + indirizzi) |
| `crea_preventivo(payload)` | Validazione input + create + ricalcolo totali |
| `aggiorna_preventivo(preventivo_id, payload)` | Guard su stato modificabile + update |
| `cambia_stato(preventivo_id, nuovo_stato)` | Validazione transizione + update stato |
| `crea_revisione(preventivo_id)` | Guard su stato ammesso + copia completa |
| `gestisci_riga(preventivo_id, payload)` | Create/update riga + ricalcolo totali |
| `elimina_riga(preventivo_id, riga_id)` | Guard + delete + ricalcolo |
| `push_a_commessa(preventivo_id)` | Guard stato ACCETTATO + invoca pipeline commessa |
| `genera_pratica(preventivo_id, tipo_pratica_id)` | Guard stato ACCETTATO + crea pratica con contesto |
| `stato_fatturazione(preventivo_id)` | Query stato pipeline downstream |

### 3.4 Endpoint API

Seguendo le convenzioni di `api.md`:

**Testata:**

```
GET    /api/v1/vendite/preventivi/                   → lista paginata
POST   /api/v1/vendite/preventivi/                   → crea preventivo
GET    /api/v1/vendite/preventivi/{id}/              → dettaglio
PATCH  /api/v1/vendite/preventivi/{id}/              → aggiorna
POST   /api/v1/vendite/preventivi/{id}/stato/        → cambio stato
POST   /api/v1/vendite/preventivi/{id}/revisione/    → crea nuova revisione
```

**Righe:**

```
GET    /api/v1/vendite/preventivi/{id}/righe/        → lista righe
POST   /api/v1/vendite/preventivi/{id}/righe/        → aggiungi riga
PATCH  /api/v1/vendite/preventivi/{id}/righe/{rid}/  → aggiorna riga
DELETE /api/v1/vendite/preventivi/{id}/righe/{rid}/  → elimina riga
```

**Indirizzi:**

```
GET    /api/v1/vendite/preventivi/{id}/indirizzi/            → lista indirizzi
POST   /api/v1/vendite/preventivi/{id}/indirizzi/            → upsert indirizzo
```

**Integrazione:**

```
POST   /api/v1/vendite/preventivi/{id}/push-commessa/        → push in commessa per fatturazione
GET    /api/v1/vendite/preventivi/{id}/stato-fatturazione/   → stato pipeline fatturazione
POST   /api/v1/vendite/preventivi/{id}/genera-pratica/       → genera pratica esecutiva
GET    /api/v1/vendite/preventivi/{id}/pratiche/             → pratiche collegate
```

---

## 4. Architettura frontend (vendita)

### 4.1 Struttura cartelle

```
src/vendite/
  preventivi/
    api/
      preventiviApi.js          # Client API preventivi
    components/
      PreventiviList.vue        # Tabella lista preventivi (useSearchTable)
      PreventiviForm.vue        # Form testata preventivo
      PreventiviRigheTable.vue  # Tabella righe inline con editing
      PreventiviRigaForm.vue    # Form singola riga (articolo, qta, prezzo, UoM)
      PreventiviStatoBadge.vue  # Badge colorato per stato documento
      PreventiviIndirizzi.vue   # Gestione indirizzi preventivo
      PreventiviDrawer.vue      # Drawer laterale per dettaglio/edit preventivo
      PreventiviIntegrazione.vue # Sezione integrazione (fatturazione + pratiche)
    views/
      PreventiviView.vue        # Pagina principale lista preventivi
```

### 4.2 UX — Lista preventivi

- Filtri: stato, data da/a, BA/cliente, utility, search testo libero
- Colonne: numero, rev, data, cliente (da BA), stato (badge), totale documento, validita', azioni
- Azioni riga: apri dettaglio, cambia stato (dropdown con transizioni ammesse)
- Paginazione standard via `useSearchTable`
- Filtro data obbligatorio con default `data_da = anno corrente - 1`

### 4.3 UX — Dettaglio/form preventivo

**Layout drawer o pagina dedicata (da valutare):**

- **Sezione testata**: cliente/BA (autocomplete), utility, validita', competenza, termini pagamento, valuta, fatturazione immediata (toggle)
- **Sezione righe** (tabella inline editabile):
  - Articolo (autocomplete da catalogo con lookup)
  - UoM operativa (dropdown filtrato per articolo)
  - Quantita'
  - Prezzo unitario (proposto da listino, editabile)
  - Sconto %
  - Importo riga (calcolato: qta * prezzo * (1 - sconto/100))
  - Aliquota IVA
  - Azioni: modifica, elimina, riordina (drag)
- **Sezione totali**: imponibile, IVA, totale documento (ricalcolati)
- **Sezione indirizzi**: sede legale, sede operativa, indirizzo spedizione (da snapshot BA)
- **Sezione note**: note testata, note per riga
- **Sezione integrazione** (solo per stato ACCETTATO):
  - Pulsante "Invia a fatturazione" (push commessa)
  - Stato pipeline fatturazione (commessa/AF/fatturato)
  - Pulsante "Genera pratica" con scelta tipo pratica
  - Lista pratiche collegate con stato

### 4.4 UX — Cambio stato

- Toolbar con pulsanti contestuali basati sullo stato corrente e transizioni ammesse
- Conferma modale per transizioni irreversibili (RIFIUTATO, ANNULLATO)
- Feedback toast su successo/errore

### 4.5 UX — Revisioni

- Indicatore revisione nella testata (rev N, badge "attiva" / "storica")
- Pulsante "Nuova revisione" (copia testata + righe in BOZZA, disattiva revisione corrente)
- Storico revisioni consultabile (lista rev con date e stato)

---

## 5. Integrazione con moduli esistenti

### 5.1 Catalogo (articoli + listini)

- Lookup articoli condiviso con altri moduli (ordini, commesse) — usa endpoint `GET /api/v1/catalogo/articoli/lookup/`
- Lookup UoM operative per articolo — usa endpoint `GET /api/v1/catalogo/articoli/{id}/uom/`
- Risoluzione prezzo da listino — invoca `fn_resolve_prezzo_listino` nel backend, non nel frontend

### 5.2 Anagrafiche (BA, soggetti)

- Lookup BA (Billing Account) con autocomplete — endpoint anagrafiche esistente
- Snapshot indirizzi da soggetto/BA — pattern gia' usato in preventivi_indirizzi

### 5.3 Commesse e fatturazione

- Push a commessa: usa le funzioni DB gia' operative (fn_get_or_create_commessa, fn_upsert_commessa_attivita)
- Segment key deterministica: `PREV:{preventivo_uid}:R:{riga_id}` — replay-safe e idempotente
- Monitoraggio: query sullo stato delle commesse_attivita e attivita_fatturabili collegate

### 5.4 Pratiche

- Generazione pratica: crea pratica con contesto precompilato (BA, utility, istanza, soggetto ruolo) — vedi §1.4.2
- Link via tabella ponte `pratiche.pratiche_sorgenti` con `sorgente_tipo = 'PREVENTIVO'` + `sorgente_uid = preventivo.uid` — vedi §1.4.1
- Bidirezionalita': dal preventivo si navigano le pratiche, dalla pratica si risale al preventivo
- Contratto handler invariato: `pratica_id` gia' nel contratto consente navigazione completa — vedi §1.4.3

---

## 6. Errori strutturati

Codici errore da registrare in `error_policies.py`:

| Codice | HTTP | Descrizione |
|--------|------|-------------|
| `E_PREV_NOT_FOUND` | 404 | Preventivo non trovato |
| `E_PREV_VALIDAZIONE` | 400 | Validazione input fallita |
| `E_PREV_STATO_TRANSIZIONE` | 409 | Transizione stato non ammessa |
| `E_PREV_STATO_NON_MODIFICABILE` | 409 | Preventivo non modificabile nello stato corrente |
| `E_PREV_RIGA_NOT_FOUND` | 404 | Riga preventivo non trovata |
| `E_PREV_NESSUNA_RIGA` | 400 | Nessuna riga attiva (richiesta per emissione) |
| `E_PREV_GIA_IN_COMMESSA` | 409 | Preventivo gia' pushato in commessa |
| `E_PREV_REVISIONE_ATTIVA` | 409 | Esiste gia' una revisione attiva |
| `E_PREV_PRATICA_STATO` | 409 | Stato preventivo non ammette generazione pratica |

---

## 7. Test

### 7.1 Test service (mock repository)

1. Creazione preventivo: campi obbligatori, default, validazione
2. Aggiornamento: guard su stato modificabile
3. Cambio stato: transizioni valide e invalide
4. Gestione righe: CRUD, ricalcolo totali
5. Push commessa: guard stato ACCETTATO, idempotenza
6. Genera pratica: guard stato, creazione contesto
7. Revisione: copia, disattivazione precedente

### 7.2 Test API (endpoint HTTP)

1. CRUD preventivo: create, list, detail, update
2. Cambio stato: transizioni e errori
3. Righe: add, update, delete, ricalcolo
4. Push commessa: successo e conflitto
5. Genera pratica: successo e guard

---

---

## PARTE B — Preventivo di acquisto (`acquisti.preventivi`)

---

## 9. Perimetro funzionale acquisti

### 9.1 Contesto

Lo schema `acquisti` ha gia' ordini e DDT con il pattern fornitore consolidato:
controparte via `soggetto_ruolo_id` (ruolo FORNITORE), serie/numero/anno,
`sorgente_tipo_id` + `sorgente_uid` per tracciabilita' documento sorgente.

Il preventivo di acquisto (RFQ — Richiesta di Preventivo) segue lo stesso pattern.
E' il documento che precede l'ordine fornitore, come il preventivo di vendita
precede la commessa/fatturazione.

### 9.2 Tabelle DB da creare

```
acquisti.preventivi                    -- testata RFQ
acquisti.preventivi_righe              -- righe articoli richiesti
acquisti.preventivi_indirizzi          -- indirizzi snapshot (consegna, fatturazione)
acquisti.note_preventivi               -- note (partizione note system)
```

#### 9.2.1 Testata `acquisti.preventivi`

Modello allineato a `acquisti.ordini` per la parte fornitore e a `vendite.preventivi` per la parte documentale:

| Campo | Tipo | Note |
|-------|------|------|
| `id` | bigint PK | |
| `uid` | uuid, default uuidv7() | Identificatore universale |
| `soggetto_ruolo_id` | bigint NOT NULL FK | **Fornitore** — ruolo FORNITORE, come `acquisti.ordini` |
| `serie` | varchar NULL | Serie documento |
| `numero` | varchar | Codice documento (trigger-generated) |
| `rev` | integer, default 0 | Revisione (come vendite.preventivi) |
| `anno` | smallint | Anno documento |
| `data` | date, default CURRENT_DATE | Data emissione |
| `stato_doc_preventivo_acq_id` | bigint NOT NULL FK | FK a `config.stati_doc_preventivi_acq` |
| `valuta_id` | integer FK | |
| `tasso_cambio` | numeric, default 1 | Per fornitori esteri |
| `modalita_pagamento_id` | integer FK | Dal fornitore o override |
| `termine_pagamento_id` | bigint FK | |
| `validita_dal` | date | Validita' offerta fornitore |
| `validita_al` | date | Scadenza offerta |
| `competenza_mese` | date | Primo del mese |
| `totale_imponibile` | numeric | |
| `totale_iva` | numeric | |
| `totale_documento` | numeric | |
| `sorgente_tipo_id` | bigint FK | Tracciabilita' (es. da pratica, da richiesta interna) |
| `sorgente_uid` | uuid | |
| `indirizzo_consegna_id` | bigint FK | Come acquisti.ordini |
| `indirizzo_cons_snapshot` | jsonb | |
| `note_generali` | text | Note libere |
| `meta` | jsonb | |
| `tx_id` | uuid | |
| `storicizza` | boolean, default true | |
| audit columns | | |

**Revisione attiva — pattern derivato (simmetrico a `vendite.preventivi` post-refactor 2026-05-15):**

Nessuna colonna `is_revision_attiva` persistita sulla tabella. Il predicato "è la
rev viva del numero" è derivato in `acquisti.vw_preventivi` (e `vw_preventivi_list`)
come:

```sql
NOT EXISTS (
    SELECT 1 FROM acquisti.preventivi p2
      JOIN config.stati_doc_preventivi_acq s2 ON s2.id = p2.stato_doc_preventivo_acq_id
     WHERE p2.numero = p.numero
       AND p2.rev > p.rev
       AND s2.is_abortito IS FALSE
) AS is_attiva
```

Dipendenza: `config.stati_doc_preventivi_acq` deve esporre colonna
`is_abortito BOOLEAN NOT NULL DEFAULT FALSE` (true solo per lo stato ANNULLATO).

Razionale: vedi `docs/it/dev/work-done/brief-db-preventivi-revisione-attiva-derivata.md`
per il modello e i pgTAP applicati su vendite. Un flag persistito mantenuto
manualmente diverge dai dati strutturali appena uno stato terminale di una
revisione viene applicato (rev annullata che non rifluisce al predecessore).
Il predicato derivato chiude per costruzione tutti i casi senza trigger di
sincronizzazione.

`fn_crea_revisione_preventivo_acq` (futura): copia testata + righe + componenti
BoM (se la sorgente acquisti adotterà il modello componenti) + indirizzi.
NON tocca `is_revision_attiva` su preventivo precedente — la derivazione è
automatica.

**Differenze chiave rispetto a `vendite.preventivi`:**

| Aspetto | Vendita | Acquisto |
|---------|---------|----------|
| Controparte | `billing_account_id` (cliente) | `soggetto_ruolo_id` (fornitore) |
| Contesto utility | `utility_id` NOT NULL, `istanza_utility_id` | Assente (non pertinente) |
| Fatturazione immediata | `fatturazione_immediata` flag | Assente |
| Serie/anno | Solo numero + rev | `serie` + `numero` + `anno` (come ordini acq.) |
| Tasso cambio | `valuta_id` only | `valuta_id` + `tasso_cambio` (fornitori esteri) |
| Indirizzo consegna | Snapshot da BA | `indirizzo_consegna_id` + snapshot (come ordini acq.) |
| Downstream | Commessa → AF → fattura | Ordine fornitore (`acquisti.ordini`) |

#### 9.2.2 Righe `acquisti.preventivi_righe`

Stessa struttura di `vendite.preventivi_righe`, con in piu' il pattern acquisti:

| Campo | Tipo | Note |
|-------|------|------|
| `id` | bigint PK | |
| `preventivo_id` | bigint FK | → acquisti.preventivi |
| `articolo_id` | uuid FK | → catalogo.articoli |
| `descrizione` | varchar | Descrizione riga (override articolo) |
| `quantita` | numeric | Quantita' richiesta |
| `prezzo_unitario` | numeric | Prezzo offerto dal fornitore |
| `sconto_percentuale` | numeric, default 0 | |
| `iva_id` | integer FK | |
| `uom_operativa_id` | bigint FK | → catalogo.unita_misura |
| `qta_operativa` | numeric | Quantita' in UoM operativa |
| `factor_to_base` | numeric | Snapshot conversione |
| `ordine` | smallint | Ordine visualizzazione |
| `attivo` | boolean | |
| `meta` | jsonb | |
| audit columns | | |

### 9.3 Macchina a stati preventivo acquisto

**Tabella config**: `config.stati_doc_preventivi_acq` (separata da vendita per indipendenza ciclo di vita)

| Codice | Descrizione | Modificabile | Genera ordine |
|--------|-------------|:------------:|:-------------:|
| BOZZA | RFQ in preparazione | si | no |
| INVIATA | Inviata al fornitore | no | no |
| RICEVUTA | Offerta ricevuta (con prezzi compilati) | parziale (prezzi) | no |
| ACCETTATA | Offerta accettata internamente | no | si |
| RIFIUTATA | Offerta rifiutata | no | no |
| SCADUTA | Superata validita_al | no | no |
| ANNULLATA | Annullata dall'operatore | no | no |

**Transizioni:**

```
BOZZA ---------> INVIATA ---------> RICEVUTA ---------> ACCETTATA ---------> (genera ordine fornitore)
                    |                   |                    |
                    |                   |                    +-> ANNULLATA
                    |                   +-> RIFIUTATA
                    |                   +-> SCADUTA
                    +-> ANNULLATA

BOZZA ---------> ANNULLATA
```

**Differenza rispetto a vendita:** lo stato RICEVUTA consente la compilazione dei prezzi
offerti dal fornitore (la RFQ parte senza prezzi o con prezzi indicativi, il fornitore
risponde con i prezzi reali).

### 9.4 Flusso downstream: da preventivo a ordine fornitore

```
PREVENTIVO ACQUISTO (ACCETTATA)
    |
    | genera ordine fornitore
    v
ACQUISTI.ORDINI
    |-- soggetto_ruolo_id (stesso fornitore)
    |-- sorgente_tipo_id = 'PREVENTIVO_ACQ'
    |-- sorgente_uid = preventivo_acq.uid
    |-- righe copiate da preventivi_righe (prezzi confermati)
    v
CICLO ACQUISTI (DDT ingresso, fattura passiva...)
```

Il collegamento ordine → preventivo usa il pattern `sorgente_tipo_id` + `sorgente_uid`
gia' presente su `acquisti.ordini` (FK `fk_ao_sorgente_tipo`, indice `uq_ordini_v_sorgente_fk`).

### 9.5 Integrazione pratiche

Il preventivo acquisto puo' generare pratiche operative (es. sopralluogo tecnico prima
dell'ordine, verifica campioni, audit fornitore) con lo stesso meccanismo della vendita:

- Link via `pratiche.pratiche_sorgenti` con `sorgente_tipo = 'PREVENTIVO_ACQ'`
- Contesto pratica: `soggetto_ruolo_id` del fornitore (non del BA)
- Catena handler invariata (§1.4.3): `pratica_id` → `pratiche_sorgenti` → `acquisti.preventivi`

### 9.6 Architettura backend acquisti

```
apps/acquisti/
  api/
    preventivi_views.py           # View per preventivi acquisto
    preventivi_urls.py            # /api/v1/acquisti/preventivi/...
  services/
    preventivi_acq_service.py     # Orchestrazione RFQ
  db/
    preventivi_acq_repository.py  # Accesso DB preventivi acquisto
  tests/
    api/
      test_preventivi_acq_api.py
    services/
      test_preventivi_acq_service.py
```

**Endpoint API:**

```
GET    /api/v1/acquisti/preventivi/                   → lista RFQ
POST   /api/v1/acquisti/preventivi/                   → crea RFQ
GET    /api/v1/acquisti/preventivi/{id}/              → dettaglio
PATCH  /api/v1/acquisti/preventivi/{id}/              → aggiorna (es. prezzi ricevuti)
POST   /api/v1/acquisti/preventivi/{id}/stato/        → cambio stato
POST   /api/v1/acquisti/preventivi/{id}/revisione/    → nuova revisione
GET    /api/v1/acquisti/preventivi/{id}/righe/        → lista righe
POST   /api/v1/acquisti/preventivi/{id}/righe/        → aggiungi riga
PATCH  /api/v1/acquisti/preventivi/{id}/righe/{rid}/  → aggiorna riga
DELETE /api/v1/acquisti/preventivi/{id}/righe/{rid}/  → elimina riga
POST   /api/v1/acquisti/preventivi/{id}/genera-ordine/ → genera ordine fornitore
POST   /api/v1/acquisti/preventivi/{id}/genera-pratica/ → genera pratica operativa
GET    /api/v1/acquisti/preventivi/{id}/pratiche/     → pratiche collegate
```

### 9.7 Architettura frontend acquisti

```
src/acquisti/
  preventivi/
    api/
      preventiviAcqApi.js
    components/
      PreventiviAcqList.vue
      PreventiviAcqForm.vue
      PreventiviAcqRigheTable.vue
      PreventiviAcqDrawer.vue
      PreventiviAcqStatoBadge.vue
    views/
      PreventiviAcqView.vue
```

**Differenze UX rispetto a vendita:**

- Controparte: autocomplete fornitore (da `soggetti_ruoli` con ruolo FORNITORE) invece di BA
- Stato RICEVUTA: form per inserire/aggiornare prezzi offerti dal fornitore sulle righe
- Azione "Genera ordine" invece di "Invia a fatturazione"
- Nessun campo utility/istanza_utility (non pertinente lato acquisti)
- Tasso cambio visibile per fornitori esteri

### 9.8 Errori strutturati acquisti

| Codice | HTTP | Descrizione |
|--------|------|-------------|
| `E_PREV_ACQ_NOT_FOUND` | 404 | Preventivo acquisto non trovato |
| `E_PREV_ACQ_VALIDAZIONE` | 400 | Validazione input fallita |
| `E_PREV_ACQ_STATO_TRANSIZIONE` | 409 | Transizione stato non ammessa |
| `E_PREV_ACQ_STATO_NON_MODIFICABILE` | 409 | Non modificabile nello stato corrente |
| `E_PREV_ACQ_RIGA_NOT_FOUND` | 404 | Riga non trovata |
| `E_PREV_ACQ_NESSUNA_RIGA` | 400 | Nessuna riga attiva |
| `E_PREV_ACQ_GIA_ORDINATO` | 409 | Ordine fornitore gia' generato |
| `E_PREV_ACQ_PREZZI_MANCANTI` | 400 | Prezzi non compilati (richiesti per accettazione) |

---

## 10. Elementi condivisi vendita/acquisto

### 10.1 Tabella ponte pratiche (unica)

`pratiche.pratiche_sorgenti` (§1.4.1) serve entrambe le direzioni:

| sorgente_tipo | Uso |
|---------------|-----|
| `PREVENTIVO_VENDITA` | Pratiche da preventivo cliente |
| `PREVENTIVO_ACQ` | Pratiche da RFQ fornitore |

Entrambi i tipi vanno registrati in `config.sorgenti`.

### 10.2 Componenti frontend riusabili

Dove possibile, i componenti core sono condivisi:

| Componente | Riuso |
|------------|-------|
| Tabella righe (articolo + UoM + prezzo) | Stesso layout, diverso contesto controparte |
| Badge stato | Stessa logica, diversa mappa colori/stati |
| Indirizzi snapshot | Stesso meccanismo |
| Note testata/riga | Stesso sistema note |

I componenti specifici (form testata, lookup controparte, azioni downstream) restano separati per dominio.

### 10.3 Catalogo articoli

Entrambi i preventivi usano lo stesso catalogo articoli e UoM operative.
Il lookup articoli e' cross-dominio (§5.1).

---

## 11. Note implementative

1. **Ordine di sviluppo**: seguire il modello concentrico — prima repository read (list/detail), poi write (create/update), poi service, poi API, poi frontend
2. **Riuso building block**: usare `useSearchTable`, `DrawerFooter`, `NewButton`, `StatoBadge` dal catalogo BB frontend
3. **Pricing**: il resolver prezzo e' una **proposta** — l'operatore conferma sempre. Non forzare mai il prezzo del listino
4. **Idempotenza**: il push commessa deve essere idempotente via segment_key. Ri-pushare lo stesso preventivo non crea duplicati
5. **Permessi**: `area_funzionale = "vendite"`, azioni processo da definire per cambio stato e push commessa
6. **Storicizzazione**: la testata ha `storicizza = true` — i trigger di storicizzazione sono gia' attivi

---
---

## 12. Piano di sviluppo — Preventivi vendita

> Scope: solo `vendite.preventivi` (PARTE A). Il preventivo acquisti (PARTE B) sara' pianificato separatamente.
>
> Convenzione: `[DB]` = eseguito da Tid lato DB, `[BE]` = backend Django, `[FE]` = frontend Vue

---

### FASE 1 — DB: tabelle, viste, funzioni — COMPLETATA

> Completata il 3 aprile 2026. Dettagli completi in [sviluppo-preventivi-fase1-db.md](sviluppo-preventivi-fase1-db.md).

#### Decisioni architetturali prese in FASE 1

| # | Decisione | Impatto backend |
|---|-----------|-----------------|
| 1 | `config.sorgenti` usa `PREVENTIVO` esistente (id=2), non `PREVENTIVO_VENDITA` | Repository e service aggiornati per usare codice `PREVENTIVO` |
| 2 | Matrice transizioni: nuova tabella `config.transizioni_stati_preventivi` | Le transizioni sono configurabili da DB, la funzione le valida |
| 3 | Trigger AFTER ricalcolo totali su `preventivi_righe` | Il service non chiama piu' `ricalcola_totali()` manualmente |
| 4 | Guard annullamento con commessa attiva: blocco duro | La funzione DB blocca, nessun warning soft |
| 5 | `emittente_fiscale_id` nella vista lista (da `fn_get_emittente_fiscale_id`) | Scope emittente via campo vista, non funzione SQL nel WHERE |
| 6 | Due viste fatturazione: righe dettaglio + aggregato | Backend usa la vista aggregata per badge UI |
| 7 | Stato ANNULLATO aggiunto (id=9) | Allineato nel seed, transizioni attive |
| 8 | Vista pratiche filtra per sorgente_tipo codice `PREVENTIVO` | Allineato al codice esistente in config.sorgenti |

#### Oggetti DB creati

- [x] `[DB]` Tabella `pratiche.pratiche_sorgenti` — tabella ponte pratiche ↔ sorgenti
- [x] `[DB]` Tabella `config.transizioni_stati_preventivi` — matrice transizioni configurabile + seed 7 transizioni
- [x] `[DB]` Seed `config.stati_doc_preventivi` — aggiunto ANNULLATO (id=9)
- [x] `[DB]` Seed `config.messaggi_errore` — 8 codici `PREV_*` (id 350-357)
- [x] `[DB]` Vista `vendite.vw_preventivi_list` — lista con JOIN + `emittente_fiscale_id`
- [x] `[DB]` Vista `vendite.vw_preventivi_righe_dettaglio` — righe + importo_riga + importo_iva calcolati
- [x] `[DB]` Funzione `vendite.fn_cambia_stato_preventivo()` — transizioni via matrice + guard EMESSO/ANNULLATO
- [x] `[DB]` Funzione `vendite.fn_crea_revisione_preventivo()` — copia testata+righe+indirizzi, rev+1
- [x] `[DB]` Funzione `vendite.fn_ricalcola_totali_preventivo()` — ricalcolo imponibile/IVA/totale
- [x] `[DB]` Trigger `trg_preventivi_righe_z90_ricalcola_totali_ins_upd_dlt` — ricalcolo automatico su righe
- [x] `[DB]` Vista `vendite.vw_preventivi_stato_fatturazione_righe` + `vw_preventivi_stato_fatturazione` — dettaglio + aggregato
- [x] `[DB]` Vista `vendite.vw_preventivi_pratiche` — pratiche collegate via pratiche_sorgenti
- [x] `[DB]` Test pgTAP: 9 test `fn_cambia_stato_preventivo` + 8 test `fn_crea_revisione` + 8 test `fn_ricalcola_totali` = **25 test OK**

---

### FASE 2 — Backend: repository + service + API

> Dipende da: FASE 1 completata (viste e funzioni disponibili)

#### 2.1 Repository

- [x] `[BE]` Creare `apps/vendite/db/preventivi_repository.py` — **FATTO + ALLINEATO DB**
  - Lista via `vw_preventivi_list` (con `emittente_fiscale_id` per scope)
  - Righe via `vw_preventivi_righe_dettaglio` (con `importo_riga`, `importo_iva_riga` calcolati)
  - Stato fatturazione via `vw_preventivi_stato_fatturazione` (per `preventivo_id`)
  - Pratiche via `vw_preventivi_pratiche` (per `preventivo_id`)
  - Lookup config via `codice_interno` (immutabile), non `codice`
  - Sorgente tipo: `PREVENTIVO` (config.sorgenti id=2), non `PREVENTIVO_VENDITA`
  - Campi jsonb: `json.dumps()` + cast `%s::jsonb` (allineato a psycopg3/commesse_repository)
  - Nomi tabelle corretti: `config.utilities`, `config.tipi_indirizzi`, `s.ragione_sociale_completa`

#### 2.2 Service

- [x] `[BE]` Creare `apps/vendite/services/preventivi_service.py` — **FATTO + ALLINEATO DB**
  - Guard stato via `stato_codice_interno` (DRAFT, EMESSO, ACCETTATO)
  - Ricalcolo totali rimosso (trigger AFTER DB lo gestisce)
  - Genera pratica via BB `pratiche_service.crea_pratica` (cross-dominio)
  - Paginazione via `paginated_envelope` core (no duplicazione)

#### 2.3 API views + urls

- [x] `[BE]` Creare `apps/vendite/api/preventivi_views.py` — **FATTO** (11 view classes con `@extend_schema`)
- [x] `[BE]` Creare `apps/vendite/api/preventivi_urls.py` — **FATTO** (12 route)
- [x] `[BE]` Registrare urls in `apps/vendite/api/urls_v1.py` — **FATTO**

#### 2.4 Errori e permessi

- [x] `[BE]` Registrare codici errore in `error_policies.py` — **FATTO** (9 codici `E_PREV_*`)
- [ ] `[BE]` Definire azioni processo per permessi: `cambia_stato_preventivi`, `push_commessa_preventivi`, `genera_pratica_preventivi` (seed DB necessario)

#### 2.5 Test backend

- [x] `[BE]` Test service: 17 test OK — **FATTO** (`test_preventivi_service.py`)
- [x] `[BE]` Test API: 7 test OK — **FATTO** (`test_preventivi_api.py`)
- [x] `[BE]` Suite completa: 1052 test OK, 0 regressioni

#### 2.6 Documentazione e smoke test

- [x] `[BE]` Documentazione API: `docs/it/backend/vendite/manual/api_preventivi.md` — **FATTO** (16 endpoint documentati)
- [x] `[BE]` Smoke test bash: `scripts/tests/smoke-test-preventivi.sh` — **FATTO + VERIFICATO END-TO-END**
- [x] `[BE]` Catalogo BB backend aggiornato — **FATTO**

#### 2.7 Fix emersi dallo smoke test (allineamento DB → Backend)

- [x] `codice` → `codice_interno` per lookup stato DRAFT (campo immutabile)
- [x] `stato_codice` → `stato_codice_interno` per tutti i confronti applicativi
- [x] `PREVENTIVO_VENDITA` → `PREVENTIVO` (config.sorgenti id=2 esistente)
- [x] `config.utilita` → `config.utilities` (nome tabella corretto)
- [x] `config.tipi_indirizzo` → `config.tipi_indirizzi` (nome tabella corretto)
- [x] `s.denominazione` → `s.ragione_sociale_completa` (campo corretto soggetti)
- [x] `meta or {}` → `json.dumps(meta or {})` + `%s::jsonb` (compatibilita' psycopg3)
- [x] Gestione `dict` → jsonb anche in `update_preventivo` e `update_riga` (dynamic update)
- [x] Rimosso `ricalcola_totali()` manuale dal service (trigger AFTER lo gestisce)
- [x] `pratica_data_insert` → `data_apertura` nella vista pratiche

---

### FASE 3 — Frontend: componenti e viste

> Dipende da: FASE 2 completata (API disponibili)

#### 3.1 API client

- [ ] `[FE]` Creare `src/vendite/preventivi/api/preventiviApi.js`
  - Metodi per tutti gli endpoint: list, get, create, update, cambiaStato, creaRevisione, listRighe, addRiga, updateRiga, deleteRiga, listIndirizzi, upsertIndirizzo, pushCommessa, statoFatturazione, generaPratica, listPratiche

#### 3.2 Componenti lista

- [ ] `[FE]` Creare `PreventiviList.vue` — tabella lista con `useSearchTable`
  - Filtri: stato, data da/a, cliente/BA, utility, search
  - Colonne: numero, rev, data, cliente, stato (badge), totale, validita'
  - Filtro data obbligatorio default anno-1
- [ ] `[FE]` Creare `PreventiviStatoBadge.vue` — badge colorato per stato

#### 3.3 Componenti form/dettaglio

- [ ] `[FE]` Creare `PreventiviForm.vue` — form testata (BA autocomplete, utility, validita', competenza, termini, valuta, fatturazione immediata)
- [ ] `[FE]` Creare `PreventiviRigheTable.vue` — tabella righe inline editabile
- [ ] `[FE]` Creare `PreventiviRigaForm.vue` — form singola riga (articolo autocomplete, UoM dropdown, qta, prezzo, sconto, IVA)
- [ ] `[FE]` Creare `PreventiviIndirizzi.vue` — gestione indirizzi snapshot
- [ ] `[FE]` Creare `PreventiviDrawer.vue` — drawer laterale dettaglio/edit con sezioni: testata, righe, totali, indirizzi, note

#### 3.4 Sezione integrazione

- [ ] `[FE]` Creare `PreventiviIntegrazione.vue` — sezione per stato ACCETTATO
  - Pulsante "Invia a fatturazione" + stato pipeline
  - Pulsante "Genera pratica" + lista pratiche collegate
  - Badge stato fatturazione (non in commessa / in commessa / emesso AF / fatturato)

#### 3.5 Vista pagina e routing

- [ ] `[FE]` Creare `PreventiviView.vue` — pagina principale
- [ ] `[FE]` Aggiungere route in `src/router/` per `/vendite/preventivi`
- [ ] `[FE]` Aggiungere voce sidebar in `src/core/navigation.js`
- [ ] `[FE]` Aggiungere traduzioni in `src/locales/it.json`
