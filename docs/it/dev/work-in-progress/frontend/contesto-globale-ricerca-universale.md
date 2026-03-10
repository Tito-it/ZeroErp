# ZeroERP — Contesto Globale e Ricerca Universale

> Questo documento descrive il meccanismo di navigazione contestuale di ZeroERP.
> L'obiettivo e' permettere all'utente di selezionare un'entita' centrale e navigare
> liberamente tra i domini mantenendo il filtro implicito su quell'entita'.
>
> Concettualmente e' un **subfile AS/400 evoluto**: l'operatore cerca, seleziona una
> riga dalla lista, e il sistema mantiene il contesto su quell'entita' attraverso
> tutte le schermate correlate.
>
> Data inizio: 2026-03-10

---

## Il problema

ZeroERP e' un sistema multi-dominio. Le informazioni relative a un soggetto — fatture,
pagamenti, pratiche, letture, contratti — sono distribuite su domini diversi. Senza un
meccanismo di collegamento, l'utente deve reimpostare il filtro ogni volta che cambia
schermata. Questo e' il problema della navigazione cliente-centrica in un ERP orizzontale.

---

## La soluzione — Contesto Globale

L'utente seleziona un'entita' (soggetto per un dato tipo ruolo) e questa diventa il
**contesto attivo** per tutta la sessione di navigazione. Ogni schermata che ha una
relazione con quell'entita' si filtra automaticamente. Il contesto rimane attivo finche'
l'utente non lo rimuove esplicitamente.

Il contesto e' uno stato globale gestito da uno store Pinia dedicato (`stores/context.js`).

---

## Struttura del contesto

Il contesto attivo contiene:

| Campo                | Descrizione                                                       |
| -------------------- | ----------------------------------------------------------------- |
| `tipo_ruolo_id`      | Tipo ruolo selezionato (CLIENTE, FORNITORE, ecc.)                 |
| `soggetto_id`        | UUID del soggetto — chiave primaria per navigazione cross-dominio |
| `soggetto_ruolo_id`  | ID del ruolo specifico — per navigazione verso tabelle ruolo      |
| `label`              | Nome visualizzabile (es. "Mario Rossi", "Comune di Bergamo")      |
| `meta`               | Informazioni aggiuntive opzionali (es. codice, utility, CF/P.IVA) |

Un solo contesto attivo alla volta. Non e' possibile avere due entita' in focus
contemporaneamente.

---

## Ricerca Universale — Drawer in Topbar

Il punto di ingresso per impostare il contesto e' la **ricerca universale**, accessibile
da un'icona nella topbar in ogni schermata. Si apre come drawer da destra (640px).

### Schema visivo

```text
+----------------------------------------------------------------+
| [Clienti v]   [  Cerca per nome, CF/P.IVA, codice...   ] [x]  |   <- fisso
| Comune: [                                          v]          |   <- filtro secondario
+----------------------------------------------------------------+
| Codice   | Ragione Sociale    | CF / P.IVA       | Comune  | Utility  |
|----------+--------------------+------------------+---------+----------|
| S-0042   | Rossi Mario        | RSSMRA80A01F205X | Bergamo | GAS, EE  |
| S-0108   | Bianchi Laura      | BNCLRA85B42F205Y | Milano  | EE       |
| S-0200   | Eni Gas e Luce SpA | 00484960588      | Roma    | --       |
+----------+--------------------+------------------+---------+----------+
|  v Dettaglio (row expansion al click)                                  |
|  ┌─ CLIENTE ─────────────────────────────────────────────────────────┐ |
|  │ Codice   | Istanza  | Utility | Indirizzo          | Stato       │ |
|  │ CLI-0042 | IST-001  | GAS     | Via Roma 12, BG    | ATTIVO      │ |
|  │ CLI-0043 | IST-002  | GAS     | Via Dante 5, BG    | SOSPESO     │ |
|  │ CLI-0108 | IST-003  | EE      | Via Roma 12, BG    | ATTIVO      │ |
|  └───────────────────────────────────────────────────────────────────┘ |
|  [Imposta contesto ->]        [Apri scheda completa ->]                |
+------------------------------------------------------------------------+
|                          [Paginazione]                                 |
+------------------------------------------------------------------------+
```

### Componenti del drawer

- **Selettore tipo ruolo** — dropdown con solo i tipi ruolo abilitati per l'utente
  corrente (filtrati in base ai permessi). Il parametro `p_tipo_ruolo_id` e' **obbligatorio**.
- **Campo di ricerca** — cerca su `ragione_sociale_completa` e `id_fiscale_univoco_cf_piva`.
  La ricerca parte dopo almeno 3 caratteri. Debounce 300ms.
- **Filtro comune** — AutoComplete su `config.comuni`. Appare come filtro secondario
  per ridurre risultati con cognomi comuni. Parametro `comune_id` inviato al backend.
- **Tabella risultati (livello 1)** — DataTable PrimeVue, una riga per soggetto:
  - Codice (`soggetto_codice`)
  - Ragione Sociale (`ragione_sociale_completa`)
  - CF / P.IVA (`id_fiscale_univoco_cf_piva`)
  - Comune (`comune_descrizione`)
  - Utility (`utility_list` — "GAS, EE" — solo per clienti, "--" per altri)
- **Row expansion (livello 2)** — click su riga espande dettaglio inline per tipo ruolo.
  Mostra tutte le righe specifiche del soggetto per quel tipo ruolo (es. tutti i clienti
  con relative istanze, indirizzi, stati). Dati caricati lazy (seconda chiamata API).
  Ampliabile in futuro con informazioni aggiuntive (contratti, saldi, PDR/POD, ecc.).
- **Azioni** — dalla riga espansa:
  - "Imposta contesto" — setta il contesto globale e chiude il drawer
  - "Apri scheda completa" — naviga alla scheda anagrafica

### Comportamento

1. L'utente clicca l'icona di ricerca nella topbar
2. Si apre il drawer — seleziona tipo e digita almeno 3 caratteri
3. Appaiono i risultati in tabella paginata
4. (Opzionale) Filtra per comune per ridurre i risultati
5. Click su riga — si espande il dettaglio inline
6. "Imposta contesto" — il contesto globale viene impostato, drawer si chiude
7. La chip del contesto appare nella topbar
8. L'utente naviga liberamente — le schermate correlate si filtrano automaticamente
9. Si chiude con ESC, clic fuori, o selezione contesto

---

## Stati — solo nel dettaglio (livello 2)

Lo stato non appare nella lista principale (livello 1). E' visibile nella **row expansion**
(livello 2), dove ogni riga specifica del tipo ruolo mostra il proprio stato.

### Clienti — `config.stati_cliente`

| codice_interno | Descrizione            | Macro (codice) |
| -------------- | ---------------------- | -------------- |
| AT             | Attivo                 | AT             |
| PR             | Pre-contrattuale       | IS             |
| RS             | Richiesta sospensione  | AT             |
| SF             | Sospeso fatturabile    | SM             |
| SC             | Sospeso non fatturabile| SM             |
| CH             | Chiuso                 | CH             |
| CF             | Chiuso e fatturato     | CH             |
| CM             | Chiuso per morosita'   | CH             |
| CW             | Chiuso per switch      | CH             |
| AN             | Annulla servizio       | AN             |
| AG             | Aggregante             | AN             |

Lo stato "pre-contrattuale" (PR) corrisponde a un cliente in fase di attivazione
(ex concetto "in corso" — ha istanza utility ma attivazione non completata).

### Fornitori

| Condizione          | Stato visualizzato |
| ------------------- | ------------------ |
| `fornitori.attivo`  | ATTIVO / INATTIVO  |

### Altri tipi ruolo

Stato = "-" (non applicabile nella prima iterazione).

---

## Dettaglio riga — Row Expansion (livello 2)

Il click su una riga espande un pannello inline sotto la riga stessa (pattern subfile
con dettaglio). Il dettaglio mostra **tutte le righe specifiche** del soggetto per il
tipo ruolo selezionato, raggruppate per tipo ruolo.

### Architettura a due livelli

```text
Livello 1 — Lista soggetti (fn_search_soggetti_universale)
  Una riga per soggetto. Nessun JOIN su tabelle ruolo specifiche.
  Colonne: Codice, Ragione Sociale, CF/P.IVA, Comune, Utility list.

Livello 2 — Dettaglio per tipo ruolo (fn_get_search_detail)
  Tutte le righe specifiche del soggetto per quel tipo ruolo.
  Es. per CLIENTE: tutti i clienti con istanza, utility, indirizzo, stato.
  Chiamata API lazy — solo quando l'utente espande la riga.
```

### Architettura componenti dettaglio

```text
SearchDrawer.vue
  +-- DataTable (expandedRows)
        +-- <template #expansion="{ data }">
              <component :is="getDetailComponent(data.tipo_ruolo_codice)" :row="data" />
```

Mappa componenti (per tipo ruolo, senza utility nel componente):

| tipo_ruolo | Componente           | Dati nel dettaglio                                         |
| ---------- | -------------------- | ---------------------------------------------------------- |
| CLIENTE    | `ClienteDetail.vue`  | Tutte le righe cliente: istanza, utility, stato, indirizzo |
| FORNITORE  | `FornitoreDetail.vue`| Codice, stato attivo/inattivo                              |
| (altri)    | `GenericDetail.vue`  | Dati base del ruolo (ampliabile in futuro)                 |

Il componente `ClienteDetail.vue` mostra una tabella interna con tutte le righe cliente
del soggetto (una per istanza/utility). Non serve un componente separato per utility
(GAS/EE/ACQUA) — la utility e' una colonna della tabella interna.

Vantaggi row expansion vs pop-up:

- L'utente resta nella lista, vede la riga sopra e sotto
- Puo' espandere piu' righe e confrontare
- Nessun overlay — fluidita' operativa
- PrimeVue DataTable supporta `expandedRows` nativamente

Il livello 2 e' progettato per essere **ampliabile**: in futuro si potranno aggiungere
contratti, saldi, PDR/POD, ultimo pagamento, ecc. senza modificare il livello 1.

---

## Chip contesto nella Topbar

Quando un contesto e' attivo, la topbar mostra una chip permanente:

```text
+-- TOPBAR ---------------------------------------------------------------+
|  [ricerca]   Anagrafiche > Soggetti    [Mario Rossi x]     10/03/2026   |
+-------------------------------------------------------------------------+
```

- La chip mostra: icona del tipo + nome dell'entita' + pulsante di rimozione `[x]`
- Il colore della chip varia per tipo di entita' per riconoscimento visivo immediato
- Il pulsante `[x]` rimuove il contesto — la navigazione torna non filtrata
- La chip e' sempre visibile in tutte le schermate finche' il contesto e' attivo

---

## Comportamento delle schermate con contesto attivo

Ogni schermata di lista dichiara se supporta il contesto globale e per quali tipi.

Quando l'utente naviga in una schermata che supporta il tipo di entita' attivo:

- La lista viene automaticamente pre-filtrata per quell'entita'
- Un indicatore visivo sotto la toolbar segnala che il filtro contestuale e' attivo:
  *"Risultati filtrati per: Mario Rossi"*
- L'utente puo' rimuovere il filtro contestuale localmente senza rimuovere il contesto globale
- Se rimuove il contesto globale dalla topbar, tutte le schermate tornano non filtrate

Quando l'utente naviga in una schermata che **non** supporta il tipo di entita' attivo:

- La schermata si apre normalmente senza filtro
- La chip del contesto rimane visibile nella topbar ma non influenza quella schermata

---

## Esempi di navigazione contestuale

**Scenario operatore front-office utility:**

1. Apre qualsiasi schermata — clicca icona ricerca in topbar
2. Tipo: Clienti — cerca "Rossi Mario" — espande riga per verificare PDR
3. "Imposta contesto" — contesto attivo: `Mario Rossi`
4. Naviga in Vendite > Fatture — vede solo le fatture di Mario Rossi
5. Naviga in Pagamenti — vede solo i pagamenti di Mario Rossi
6. Naviga in Pratiche — vede solo le pratiche di Mario Rossi
7. Naviga in Magazzino > Stock — il contesto non si applica, vista normale
8. Torna in Anagrafiche — i dati di Mario Rossi sono gia' in primo piano

**Scenario operatore acquisti:**

1. Clicca icona ricerca — Tipo: Fornitori — cerca "Eni Gas"
2. Seleziona il risultato — contesto attivo: `Eni Gas e Luce S.p.A.`
3. Naviga in Acquisti > Ordini — vede solo gli ordini di quel fornitore
4. Naviga in Pagamenti — vede solo i pagamenti verso quel fornitore

---

## Store Pinia — `stores/context.js`

Lo store gestisce il contesto attivo con le seguenti operazioni:

| Metodo | Descrizione |
| --- | --- |
| `setContext(tipo_ruolo_id, soggetto_id, soggetto_ruolo_id, label, meta)` | Imposta il contesto attivo |
| `clearContext()` | Rimuove il contesto attivo |
| `hasContext` | `true` se un contesto e' attivo |
| `contextLabel` | Stringa visualizzabile per la chip |

Il contesto non viene persistito tra sessioni — ogni login parte senza contesto attivo.
In futuro si potra' propagare nell'URL (`?ctx=tipo_ruolo:soggetto_id`) per link condivisibili.

---

## Regole di implementazione

- Ogni componente lista che supporta il contesto legge lo store e applica il filtro
  come parametro aggiuntivo nella chiamata API — non filtra lato frontend
- Il backend deve supportare il parametro di filtro contestuale per ogni endpoint che
  lo richiede (es. `GET /api/vendite/fatture/?soggetto_ruolo_id=123`)
- La ricerca universale ha il proprio endpoint dedicato sul backend
- Il tipo predefinito del selettore e' configurabile per ruolo utente nel profilo
- La ricerca rispetta lo scope emittente: un utente OPERATIVO con whitelist emittenti
  vede solo soggetti/clienti nel proprio scope
- Il filtro comune e' opzionale — riduce i risultati senza essere obbligatorio

---

## Prerequisiti

| Prerequisito | Stato | Dove |
| --- | --- | --- |
| Tabella `anagrafiche.soggetti` con `ragione_sociale_completa` (campo generato) | OK | Schema `anagrafiche` |
| Tabella `anagrafiche.soggetti_ruoli` con tipi ruolo | OK | Schema `anagrafiche` |
| Colonna `id_fiscale_univoco_cf_piva` (COALESCE CF/P.IVA) | OK | `anagrafiche.soggetti` |
| Tabella `config.utility` (GAS, EE, ACQUA, ecc.) | OK | Schema `config` |
| Tabella `config.comuni` per filtro comune | OK | Schema `config` |
| Tabella `anagrafiche.istanze_utilities` per stato "in corso" | OK | Schema `anagrafiche` |
| Vista `vw_soggetti_ruoli_dettaglio` | OK | Schema `anagrafiche` |
| `AppDrawer.vue` riutilizzabile (PrimeVue Drawer) | OK | `frontend/src/core/components/` |
| PrimeVue 4.5 (Drawer, Chip, DataTable, AutoComplete) | OK | `package.json` |
| Store Pinia + `api.js` interceptor | OK | `frontend/src/stores/`, `frontend/src/core/` |
| `search_validators.py` (min 3 caratteri) | OK | `apps/core/api/` |
| `SearchBurstRateThrottle` | OK | `apps/core/api/throttling.py` |
| Scope emittente (`EmittenteFiscaleScopeMixin`) | OK | `apps/core/mixins.py` |
| `DRAWER_WIDTH.STANDARD` (640px) | OK | `frontend/src/core/constants.js` |
| Estensione `pg_trgm` su PostgreSQL | **Da verificare** | Database |

---

## Piano di Implementazione

### Fase 1 — DB: Funzione di ricerca universale

| Step | Descrizione | Stato | Dipende da |
| --- | --- | --- | --- |
| 1.1 | Verificare/abilitare estensione `pg_trgm` su PostgreSQL | **Da fare** | -- |
| 1.2 | Creare indice GIN trigram su `soggetti.ragione_sociale_completa` e `soggetti.id_fiscale_univoco_cf_piva` per performance ILIKE | **Da fare** | 1.1 |
| 1.3 | Creare `script.fn_search_soggetti_universale(p_search_term, p_tipo_ruolo_id, p_comune_id, p_emittente_ids, p_limit, p_offset)` — `p_tipo_ruolo_id` obbligatorio. Cerca su `ragione_sociale_completa` e `id_fiscale_univoco_cf_piva` con ILIKE. Paginazione LIMIT/OFFSET + `COUNT(*) OVER()` + hard cap 10.000. Ritorna: `total_count`, `soggetto_id`, `soggetto_ruolo_id`, `tipo_ruolo_id`, `comune_id`, `soggetto_codice`, `ragione_sociale_completa`, `id_fiscale_univoco`, `comune_descrizione`, `utility_list`. Una riga per soggetto, nessun JOIN su tabelle ruolo specifiche. LEFT JOIN leggero su `clienti` + `utilities` solo per aggregare `utility_list` (string_agg) | **Da fare** | 1.1, 1.2 |
| 1.4 | Creare `script.fn_get_search_detail(p_soggetto_id, p_tipo_ruolo_id)` — dettaglio per row expansion (livello 2). Ritorna tutte le righe specifiche del soggetto per il tipo ruolo: per CLIENTE tutte le righe con istanza, utility, indirizzo, stato (`stati_cliente`); per FORNITORE codice e stato attivo/inattivo; per altri tipi dati base. Output JSONB con sezioni per tipo ruolo, ampliabile in futuro | **Da fare** | 1.3 |
| 1.5 | Test pgTAP per `fn_search_soggetti_universale` — casi: ricerca per nome, per CF/P.IVA, filtro tipo obbligatorio, filtro comune, scope emittente, risultati vuoti, paginazione, hard cap, utility_list aggregata | **Da fare** | 1.3 |
| 1.6 | Test pgTAP per `fn_get_search_detail` — casi: dettaglio cliente (multi-istanza, multi-utility), fornitore, tipo generico | **Da fare** | 1.4 |
| 1.7 | Changeset Liquibase per estensione, indici, funzioni | **Da fare** | 1.1-1.4 |

### Fase 2 — Backend: Endpoint ricerca universale

| Step | Descrizione | Stato | Dipende da |
| --- | --- | --- | --- |
| 2.1 | Creare `SearchRepository` in `apps/core/db/search_repository.py` — `search_soggetti()` chiama `fn_search_soggetti_universale`, `get_search_detail()` chiama `fn_get_search_detail` | **Da fare** | 1.3, 1.4 |
| 2.2 | Creare `SearchUniversaleView(APIView)` in `apps/core/api/search_view.py` — `GET /api/v1/core/search/` con params: `q` (min 3), `tipo_ruolo_id` (obbligatorio), `comune_id` (opzionale), `page`, `page_size`. Il backend filtra `tipo_ruolo_id` in base ai permessi dell'utente. Applica scope emittente via `PermissionResolver`. `@extend_schema`. `is_search_endpoint = True` per throttling. Response: `{count, page, page_size, results: [...]}` | **Da fare** | 2.1 |
| 2.3 | Creare `SearchDetailView(APIView)` in `apps/core/api/search_view.py` — `GET /api/v1/core/search/<uuid:soggetto_id>/detail/?tipo_ruolo_id=N` — dettaglio per row expansion (livello 2). Verifica scope emittente e permessi tipo ruolo | **Da fare** | 2.1 |
| 2.4 | Registrare rotte in `apps/core/api/urls_v1.py` | **Da fare** | 2.2, 2.3 |
| 2.5 | Aggiungere error policies: `E_SEARCH_NO_RESULTS` (opzionale) | **Da fare** | -- |
| 2.6 | Test unitari (mock DB): ricerca success, risultati vuoti, term troppo corto, tipo ruolo obbligatorio, filtro comune, paginazione, scope emittente, dettaglio success/not_found | **Da fare** | 2.2, 2.3 |
| 2.7 | Aggiungere sezione a smoke test `smoke-test-core.sh` | **Da fare** | 2.2 |
| 2.8 | Documentazione `docs/it/backend/core/manual/api_search_universale.md` | **Da fare** | 2.2, 2.3 |

### Fase 3 — Frontend: Store contesto globale

| Step | Descrizione | Stato | Dipende da |
| --- | --- | --- | --- |
| 3.1 | Creare `stores/context.js` — Pinia store con: `tipo_ruolo_id`, `soggetto_id`, `soggetto_ruolo_id`, `label`, `meta`, computed `hasContext`, `contextLabel`, `contextIcon`, actions `setContext()`, `clearContext()`. In-memory, non persistito | **Da fare** | -- |
| 3.2 | Aggiungere chiavi i18n (`it.json`, `en.json`) per search, context, tipi ruolo, colonne | **Da fare** | -- |

### Fase 4 — Frontend: Drawer ricerca universale

| Step | Descrizione | Stato | Dipende da |
| --- | --- | --- | --- |
| 4.1 | Creare `SearchDrawer.vue` — drawer 640px con: dropdown tipo ruolo (solo abilitati per utente), input ricerca (debounce 300ms, min 3 char), AutoComplete comune, DataTable risultati livello 1 (Codice, Ragione Sociale, CF/P.IVA, Comune, Utility list), paginazione, row expansion livello 2 con componente dinamico per tipo ruolo | **Da fare** | 2.2, 3.1, 3.2 |
| 4.2 | Creare componenti dettaglio row expansion per tipo ruolo: `ClienteDetail.vue` (tabella interna multi-istanza con utility, indirizzo, stato), `FornitoreDetail.vue`, `GenericDetail.vue` (base per altri tipi) | **Da fare** | 2.3 |
| 4.3 | Creare `getDetailComponent(tipo_ruolo_codice)` — mappa tipo ruolo al componente corretto | **Da fare** | 4.2 |
| 4.4 | Aggiungere icona ricerca in `AppTopbar.vue` — click apre SearchDrawer | **Da fare** | 4.1 |
| 4.5 | Aggiungere chip contesto in `AppTopbar.vue` — visibile quando `hasContext`, mostra icona tipo + label + pulsante [x] per `clearContext()`. Colore variabile per tipo | **Da fare** | 3.1 |

### Fase 5 — Frontend: Integrazione contesto nelle liste (futuro)

| Step | Descrizione | Stato | Dipende da |
| --- | --- | --- | --- |
| 5.1 | Creare composable `useContextFilter()` — legge lo store contesto e restituisce query params per le chiamate API delle liste | **Da fare** | 3.1 |
| 5.2 | Creare `ContextFilterBanner.vue` — banner sotto toolbar: "Risultati filtrati per: X" + pulsante rimuovi filtro locale | **Da fare** | 3.1 |
| 5.3 | Integrare nelle liste (fatture, pratiche, pagamenti) quando verranno create | **Da fare** | 5.1, 5.2, liste |

---

## Sequenza di sviluppo

```text
Fase 1 (DB)  -->  Fase 2 (Backend)  -->  Fase 4 (Drawer/Topbar)
                                              |
Fase 3 (Store + i18n) ----> parallelo --------+
                                              |
                                         Fase 5 (Liste — quando esistono)
```

Fase 3 puo' partire in parallelo con Fase 1-2 (solo frontend, nessuna dipendenza DB).
Fase 5 si implementa progressivamente man mano che le liste vengono create.

---

## Decisioni prese

| # | Domanda | Decisione |
| --- | --- | --- |
| 1 | Selettore tipo: tab o dropdown? | **Dropdown** — piu' compatto e scalabile |
| 2 | Dove posizionare la ricerca? | **Drawer da topbar** — accessibile da qualsiasi schermata, non solo dalla home |
| 3 | Colonne lista (livello 1) | **Codice, Ragione Sociale, CF/P.IVA, Comune, Utility list** — niente stato nel livello 1 |
| 4 | Dettaglio riga: pop-up o inline? | **Row expansion** (inline) — l'utente resta nella lista, puo' confrontare piu' righe |
| 5 | Ricerca su quali campi | **`ragione_sociale_completa`** + **`id_fiscale_univoco_cf_piva`** (colonna unica COALESCE) |
| 6 | Filtro secondario | **Comune** — AutoComplete su `config.comuni`, parametro `comune_id` al backend |
| 7 | Tipi disponibili nel dropdown | **Solo tipi ruolo abilitati per l'utente** — filtrati in base ai permessi, no "Tutti" |
| 8 | Tipo ruolo obbligatorio | **Si'** — `p_tipo_ruolo_id` obbligatorio. La funzione cerca sempre per un tipo specifico |
| 9 | Stato nel dettaglio | **Per clienti**: `config.stati_cliente` (AT, PR, SF, SC, CH, ecc.). **Fornitori**: attivo/inattivo. **Altri**: "-" |
| 10 | Persistenza contesto | **Solo in-memory Pinia** — non persistito tra sessioni. Futuro: propagazione URL |
| 11 | Dettaglio per tipo ruolo | **Componenti dinamici per tipo ruolo** — `getDetailComponent(tipo_ruolo_codice)`, non per utility |
| 12 | Caricamento dettaglio | **Lazy** — seconda chiamata API solo quando l'utente espande la riga |
| 13 | Architettura lista | **Due livelli**: livello 1 = una riga per soggetto (nessun JOIN tabelle ruolo); livello 2 = tutte le righe specifiche per tipo ruolo (lazy) |
| 14 | Paginazione DB | **LIMIT/OFFSET + COUNT(*) OVER() + hard cap 10.000** — un solo round-trip, offset pagination |
| 15 | Strategia ricerca DB | **ILIKE + pg_trgm + indice GIN** — no tsvector (non serve ranking/stemming per nomi e CF/P.IVA) |
| 16 | ID restituiti nel livello 1 | **`soggetto_id`, `soggetto_ruolo_id`, `tipo_ruolo_id`, `comune_id`** — nessun ID specifico per tabella ruolo (cliente_id, fornitore_id, ecc.) |

---

## Decisioni aperte

| # | Domanda | Opzioni | Decisione |
| --- | --- | --- | --- |
| 1 | Tipo predefinito per ruolo utente | Mappa ruolo->tipo nel profilo / configurabile in settings | **Da decidere** |
| 2 | Ricerche recenti (history) | Salvare ultime 5-10 in localStorage / non salvare | **Da decidere** |
| 3 | Contenuto esatto dei componenti dettaglio per tipo ruolo | Quali campi mostrare per ogni tipo (ampliabile nel tempo) | **Da decidere** |

---

## File coinvolti

### DB (Liquibase)

| File | Azione |
| --- | --- |
| `db/changelog/migrations_v2/20_code/script/fn_search_soggetti_universale.yaml` | **Nuovo** |
| `db/changelog/migrations_v2/20_code/script/fn_get_search_detail.yaml` | **Nuovo** |
| `db/changelog/migrations_v2/10_indexes/anagrafiche/idx_soggetti_trgm.yaml` | **Nuovo** |
| `db/pgtap/script/test-fn-search-soggetti-universale.sql` | **Nuovo** |
| `db/pgtap/script/test-fn-get-search-detail.sql` | **Nuovo** |

### Backend (Django)

| File | Azione |
| --- | --- |
| `backend/apps/core/db/search_repository.py` | **Nuovo** |
| `backend/apps/core/api/search_view.py` | **Nuovo** |
| `backend/apps/core/api/urls_v1.py` | **Modifica** |
| `backend/apps/core/services/error_policies.py` | **Modifica** |
| `backend/apps/core/tests/api/test_search_view.py` | **Nuovo** |
| `backend/scripts/tests/smoke-test-core.sh` | **Modifica** |
| `docs/it/backend/core/manual/api_search_universale.md` | **Nuovo** |

### Frontend (Vue)

| File | Azione |
| --- | --- |
| `frontend/src/stores/context.js` | **Nuovo** |
| `frontend/src/core/components/SearchDrawer.vue` | **Nuovo** |
| `frontend/src/core/components/ContextFilterBanner.vue` | **Nuovo** |
| `frontend/src/core/components/AppTopbar.vue` | **Modifica** |
| `frontend/src/core/composables/useContextFilter.js` | **Nuovo** |
| `frontend/src/core/components/details/ClienteDetail.vue` | **Nuovo** |
| `frontend/src/core/components/details/FornitoreDetail.vue` | **Nuovo** |
| `frontend/src/core/components/details/GenericDetail.vue` | **Nuovo** |
| `frontend/src/locales/it.json` | **Modifica** |
| `frontend/src/locales/en.json` | **Modifica** |

---

## Migliorie future

| # | Miglioria | Priorita' | Note |
| --- | --- | --- | --- |
| 1 | **Full-text search con tsvector** — colonna generata + indice GIN per ranking nativo e performance su grandi volumi | Media | Alternativa a ILIKE+trigram, piu' potente ma piu' complessa |
| 2 | **Ricerche recenti** — ultime 5-10 in localStorage, mostrate all'apertura del drawer con campo vuoto | Bassa | Velocizza operatori che lavorano con stessi soggetti |
| 3 | **Contesto nell'URL** — propagare come query param `?ctx=cliente:id` per link condivisibili e persistenza al refresh | Media | Non critico in prima iterazione |
| 4 | **Cache risultati frequenti** — Redis con TTL 30s per ricerche ripetute | Bassa | Solo se emerge come bottleneck |
| 5 | **Tipo predefinito intelligente** — derivare da ruolo_sistema o area funzionale corrente | Bassa | Mappa nel profilo utente |

---

*ZeroERP — Contesto Globale e Ricerca Universale*
*Sviluppo Concentrico — anello 2/3, dipende da anagrafiche e pratiche*
