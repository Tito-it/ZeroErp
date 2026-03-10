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

L'utente seleziona un'entita' (soggetto, cliente, fornitore) e questa diventa il
**contesto attivo** per tutta la sessione di navigazione. Ogni schermata che ha una
relazione con quell'entita' si filtra automaticamente. Il contesto rimane attivo finche'
l'utente non lo rimuove esplicitamente.

Il contesto e' uno stato globale gestito da uno store Pinia dedicato (`stores/context.js`).

---

## Struttura del contesto

Il contesto attivo contiene:

| Campo   | Descrizione                                                        |
| ------- | ------------------------------------------------------------------ |
| `type`  | Tipo di entita': `soggetto`, `cliente`, `fornitore`                |
| `id`    | `soggetto_ruolo_id` — identificativo univoco nel database          |
| `label` | Nome visualizzabile (es. "Mario Rossi", "Comune di Bergamo")       |
| `meta`  | Informazioni aggiuntive opzionali (es. codice, utility, CF/P.IVA)  |

Un solo contesto attivo alla volta. Non e' possibile avere due entita' in focus
contemporaneamente.

---

## Ricerca Universale — Drawer in Topbar

Il punto di ingresso per impostare il contesto e' la **ricerca universale**, accessibile
da un'icona nella topbar in ogni schermata. Si apre come drawer da destra (640px).

### Schema visivo

```
+----------------------------------------------------------------+
| [Tutti v]   [  Cerca per nome, CF/P.IVA, codice...     ] [x]  |   <- fisso
| Comune: [                                          v]          |   <- filtro secondario
+----------------------------------------------------------------+
| Codice   | Ragione Sociale    | CF / P.IVA      | Indirizzo           | Utility | Stato    |
|----------+--------------------+-----------------+---------------------+---------+----------|
| CLI-0042 | Rossi Mario        | RSSMRA80A01F205X| Bergamo, Via Roma 12| GAS     | . Attivo |
| CLI-0108 | Bianchi Laura      | BNCLRA85B42F205Y| Milano, C.so Mag. 5 | EE      | o In corso|
| FOR-0015 | Eni Gas e Luce SpA | 00484960588     | Roma, P.le ENI 1    | --      | . Attivo |
+----------+--------------------+-----------------+---------------------+---------+----------+
|  v Dettaglio (row expansion al click)                                                      |
|  Telefono: 035 123456         Email: rossi@email.it                                        |
|  PDR: 01234567890123          Contratto: CTR-2026-0042                                     |
|  Ultimo pagamento: 15/02/2026  Saldo: EUR 125,00                                          |
|  [Imposta contesto ->]        [Apri scheda completa ->]                                    |
+--------------------------------------------------------------------------------------------+
|                          [Paginazione]                                                     |
+--------------------------------------------------------------------------------------------+
```

### Componenti del drawer

- **Selettore tipo** — dropdown: Tutti, Clienti, Fornitori, Soggetti.
  Il tipo predefinito dipende dal ruolo/area dell'utente connesso.
- **Campo di ricerca** — cerca su `ragione_sociale_completa` e `id_fiscale_univoco_cf_piva`.
  La ricerca parte dopo almeno 3 caratteri. Debounce 300ms.
- **Filtro comune** — AutoComplete su `config.comuni`. Appare come filtro secondario
  per ridurre risultati con cognomi comuni. Parametro `comune_id` inviato al backend.
- **Tabella risultati** — DataTable PrimeVue con colonne:
  - Codice (codice cliente/fornitore/soggetto)
  - Ragione Sociale (`ragione_sociale_completa`)
  - CF / P.IVA (`id_fiscale_univoco_cf_piva`)
  - Indirizzo (formato: "Comune, indirizzo completo")
  - Utility (`config.utility` — GAS, EE, ACQUA, ecc. — solo per clienti, "--" per altri)
  - Stato (derivato — vedi sezione stati)
- **Row expansion** — click su riga espande dettaglio inline (non pop-up).
  Il contenuto varia per tipo/utility tramite componenti dinamici.
  Dati caricati lazy (seconda chiamata API solo quando si espande).
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

## Stati soggetto

Lo stato visualizzato nella lista e' derivato dalla logica di business:

| Stato visualizzato | Logica DB                                                  | Tipi     |
| ------------------ | ---------------------------------------------------------- | -------- |
| **Attivo**         | Ha ruolo attivo                                            | Tutti    |
| **In corso**       | Ha istanza utility ma nessun ruolo cliente attivo          | Clienti  |
| **Sospeso**        | Ruolo cliente/fornitore sospeso                            | Cli/For  |
| **Chiuso**         | Ruolo cliente/fornitore chiuso                             | Cli/For  |

Lo stato "In corso" e' specifico dei clienti utility: rappresenta soggetti con una
`istanza_utility` attiva ma che non hanno ancora completato l'attivazione come clienti.
Non sono ne' aperti, ne' chiusi, ne' sospesi — sono in fase di attivazione.

---

## Dettaglio riga — Row Expansion

Il click su una riga espande un pannello inline sotto la riga stessa (pattern subfile
con dettaglio). Il contenuto varia per tipo di entita' e utility.

### Architettura componenti dettaglio

```
SearchDrawer.vue
  +-- DataTable (expandedRows)
        +-- <template #expansion="{ data }">
              <component :is="getDetailComponent(data.tipo_ruolo, data.utility)" :row="data" />
```

Mappa componenti:

| tipo_ruolo | utility | Componente              | Dati specifici                        |
| ---------- | ------- | ----------------------- | ------------------------------------- |
| cliente    | GAS     | `ClienteGasDetail.vue`  | PDR, contratto gas, letture, saldo    |
| cliente    | EE      | `ClienteEEDetail.vue`   | POD, contratto EE, letture, saldo     |
| cliente    | ACQUA   | `ClienteAcquaDetail.vue`| PDM, contratto acqua, letture, saldo  |
| fornitore  | --      | `FornitoreDetail.vue`   | Ordini attivi, pagamenti, scadenze    |
| soggetto   | --      | `SoggettoDetail.vue`    | Contatti, indirizzi, ruoli associati  |

Vantaggi row expansion vs pop-up:
- L'utente resta nella lista, vede la riga sopra e sotto
- Puo' espandere piu' righe e confrontare
- Nessun overlay — fluidita' operativa
- PrimeVue DataTable supporta `expandedRows` nativamente

I dati di dettaglio vengono da una **chiamata API lazy** separata — solo quando
l'utente espande la riga. La lista iniziale resta veloce.

---

## Chip contesto nella Topbar

Quando un contesto e' attivo, la topbar mostra una chip permanente:

```
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

| Metodo                              | Descrizione                        |
| ----------------------------------- | ---------------------------------- |
| `setContext(type, id, label, meta)` | Imposta il contesto attivo         |
| `clearContext()`                    | Rimuove il contesto attivo         |
| `hasContext`                        | `true` se un contesto e' attivo    |
| `contextLabel`                      | Stringa visualizzabile per la chip |

Il contesto non viene persistito tra sessioni — ogni login parte senza contesto attivo.
In futuro si potra' propagare nell'URL (`?ctx=cliente:id`) per link condivisibili.

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
|---|---|---|
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
|---|---|---|---|
| 1.1 | Verificare/abilitare estensione `pg_trgm` su PostgreSQL | **Da fare** | -- |
| 1.2 | Creare indice GIN trigram su `soggetti.ragione_sociale_completa` e `soggetti.id_fiscale_univoco_cf_piva` per performance ILIKE | **Da fare** | 1.1 |
| 1.3 | Creare `script.fn_search_soggetti_universale(p_search_term, p_tipo_ruolo, p_comune_id, p_emittente_scope, p_limit, p_offset)` — cerca su `ragione_sociale_completa` e `id_fiscale_univoco_cf_piva` con ILIKE. Filtra per tipo ruolo, comune, scope emittente. Ritorna: `soggetto_ruolo_id`, `codice`, `ragione_sociale_completa`, `id_fiscale_univoco_cf_piva`, `comune_descrizione`, `indirizzo_completo`, `utility_codice`, `stato_derivato`. LEFT JOIN su `istanze_utilities` per stato "in corso" clienti | **Da fare** | 1.1, 1.2 |
| 1.4 | Creare `script.fn_get_search_detail(p_soggetto_ruolo_id)` — dettaglio per row expansion: contatti, contratti attivi, ultimo pagamento, saldo. Output JSONB con sezioni variabili per tipo/utility | **Da fare** | 1.3 |
| 1.5 | Test pgTAP per `fn_search_soggetti_universale` — casi: ricerca per nome, per CF/P.IVA, filtro tipo, filtro comune, scope emittente, risultati vuoti, paginazione, stato "in corso" | **Da fare** | 1.3 |
| 1.6 | Test pgTAP per `fn_get_search_detail` — casi: dettaglio cliente GAS/EE/ACQUA, fornitore, soggetto | **Da fare** | 1.4 |
| 1.7 | Changeset Liquibase per estensione, indici, funzioni | **Da fare** | 1.1-1.4 |

### Fase 2 — Backend: Endpoint ricerca universale

| Step | Descrizione | Stato | Dipende da |
|---|---|---|---|
| 2.1 | Creare `SearchRepository` in `apps/core/db/search_repository.py` — `search_soggetti()` chiama `fn_search_soggetti_universale`, `get_search_detail()` chiama `fn_get_search_detail` | **Da fare** | 1.3, 1.4 |
| 2.2 | Creare `SearchUniversaleView(APIView)` in `apps/core/api/search_view.py` — `GET /api/v1/core/search/` con params: `q` (min 3), `type` (opzionale: cliente/fornitore/soggetto), `comune_id` (opzionale), `page`, `page_size`. Applica scope emittente via `PermissionResolver`. `@extend_schema`. `is_search_endpoint = True` per throttling | **Da fare** | 2.1 |
| 2.3 | Creare `SearchDetailView(APIView)` in `apps/core/api/search_view.py` — `GET /api/v1/core/search/<int:soggetto_ruolo_id>/detail/` — dettaglio per row expansion. Verifica scope emittente | **Da fare** | 2.1 |
| 2.4 | Registrare rotte in `apps/core/api/urls_v1.py` | **Da fare** | 2.2, 2.3 |
| 2.5 | Aggiungere error policies: `E_SEARCH_NO_RESULTS` (opzionale) | **Da fare** | -- |
| 2.6 | Test unitari (mock DB): ricerca success, risultati vuoti, term troppo corto, filtro tipo, filtro comune, paginazione, scope emittente, dettaglio success/not_found | **Da fare** | 2.2, 2.3 |
| 2.7 | Aggiungere sezione a smoke test `smoke-test-core.sh` | **Da fare** | 2.2 |
| 2.8 | Documentazione `docs/it/backend/core/manual/api_search_universale.md` | **Da fare** | 2.2, 2.3 |

### Fase 3 — Frontend: Store contesto globale

| Step | Descrizione | Stato | Dipende da |
|---|---|---|---|
| 3.1 | Creare `stores/context.js` — Pinia store con: `type`, `id`, `label`, `meta`, computed `hasContext`, `contextLabel`, `contextIcon`, actions `setContext()`, `clearContext()`. In-memory, non persistito | **Da fare** | -- |
| 3.2 | Aggiungere chiavi i18n (`it.json`, `en.json`) per search, context, tipi entita', stati, colonne | **Da fare** | -- |

### Fase 4 — Frontend: Drawer ricerca universale

| Step | Descrizione | Stato | Dipende da |
|---|---|---|---|
| 4.1 | Creare `SearchDrawer.vue` — drawer 640px con: dropdown tipo (Tutti/Clienti/Fornitori/Soggetti), input ricerca (debounce 300ms, min 3 char), AutoComplete comune, DataTable risultati con colonne (Codice, Ragione Sociale, CF/P.IVA, Indirizzo, Utility, Stato), paginazione, row expansion con componente dinamico | **Da fare** | 2.2, 3.1, 3.2 |
| 4.2 | Creare componenti dettaglio row expansion: `SoggettoDetail.vue` (base), `FornitoreDetail.vue`, `ClienteGasDetail.vue`, `ClienteEEDetail.vue`, `ClienteAcquaDetail.vue` | **Da fare** | 2.3 |
| 4.3 | Creare `getDetailComponent(tipo_ruolo, utility)` — mappa tipo/utility al componente corretto | **Da fare** | 4.2 |
| 4.4 | Aggiungere icona ricerca in `AppTopbar.vue` — click apre SearchDrawer | **Da fare** | 4.1 |
| 4.5 | Aggiungere chip contesto in `AppTopbar.vue` — visibile quando `hasContext`, mostra icona tipo + label + pulsante [x] per `clearContext()`. Colore variabile per tipo | **Da fare** | 3.1 |

### Fase 5 — Frontend: Integrazione contesto nelle liste (futuro)

| Step | Descrizione | Stato | Dipende da |
|---|---|---|---|
| 5.1 | Creare composable `useContextFilter()` — legge lo store contesto e restituisce query params per le chiamate API delle liste | **Da fare** | 3.1 |
| 5.2 | Creare `ContextFilterBanner.vue` — banner sotto toolbar: "Risultati filtrati per: X" + pulsante rimuovi filtro locale | **Da fare** | 3.1 |
| 5.3 | Integrare nelle liste (fatture, pratiche, pagamenti) quando verranno create | **Da fare** | 5.1, 5.2, liste |

---

## Sequenza di sviluppo

```
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
|---|---|---|
| 1 | Selettore tipo: tab o dropdown? | **Dropdown** — piu' compatto e scalabile |
| 2 | Dove posizionare la ricerca? | **Drawer da topbar** — accessibile da qualsiasi schermata, non solo dalla home |
| 3 | Colonne lista risultati | **Codice, Ragione Sociale, CF/P.IVA, Indirizzo (comune+via), Utility, Stato** |
| 4 | Dettaglio riga: pop-up o inline? | **Row expansion** (inline) — l'utente resta nella lista, puo' confrontare piu' righe |
| 5 | Ricerca su quali campi | **`ragione_sociale_completa`** + **`id_fiscale_univoco_cf_piva`** (colonna unica COALESCE) |
| 6 | Filtro secondario | **Comune** — AutoComplete su `config.comuni`, parametro `comune_id` al backend |
| 7 | Tipi disponibili | **Tutti, Clienti, Fornitori, Soggetti** — no PDR/POD/PDM come tipi separati |
| 8 | Stato "in corso" | **Specifico clienti** — ha istanza utility ma nessun ruolo cliente attivo |
| 9 | Persistenza contesto | **Solo in-memory Pinia** — non persistito tra sessioni. Futuro: propagazione URL |
| 10 | Dettaglio per tipo/utility | **Componenti dinamici** — mappa `getDetailComponent(tipo_ruolo, utility)` |
| 11 | Caricamento dettaglio | **Lazy** — seconda chiamata API solo quando l'utente espande la riga |

---

## Decisioni aperte

| # | Domanda | Opzioni | Decisione |
|---|---|---|---|
| 1 | Tipo predefinito per ruolo utente | Mappa ruolo->tipo nel profilo / configurabile in settings | **Da decidere** |
| 2 | Ricerche recenti (history) | Salvare ultime 5-10 in localStorage / non salvare | **Da decidere** |
| 3 | Full-text search PostgreSQL | ILIKE con trigram (semplice) vs tsvector (ranking nativo) | **Da decidere** |
| 4 | Contenuto esatto dei componenti dettaglio per tipo/utility | Quali campi mostrare per ogni combinazione | **Da decidere** |

---

## File coinvolti

### DB (Liquibase)

| File | Azione |
|---|---|
| `db/changelog/migrations_v2/20_code/script/fn_search_soggetti_universale.yaml` | **Nuovo** |
| `db/changelog/migrations_v2/20_code/script/fn_get_search_detail.yaml` | **Nuovo** |
| `db/changelog/migrations_v2/10_indexes/anagrafiche/idx_soggetti_trgm.yaml` | **Nuovo** |
| `db/pgtap/script/test-fn-search-soggetti-universale.sql` | **Nuovo** |
| `db/pgtap/script/test-fn-get-search-detail.sql` | **Nuovo** |

### Backend (Django)

| File | Azione |
|---|---|
| `backend/apps/core/db/search_repository.py` | **Nuovo** |
| `backend/apps/core/api/search_view.py` | **Nuovo** |
| `backend/apps/core/api/urls_v1.py` | **Modifica** |
| `backend/apps/core/services/error_policies.py` | **Modifica** |
| `backend/apps/core/tests/api/test_search_view.py` | **Nuovo** |
| `backend/scripts/tests/smoke-test-core.sh` | **Modifica** |
| `docs/it/backend/core/manual/api_search_universale.md` | **Nuovo** |

### Frontend (Vue)

| File | Azione |
|---|---|
| `frontend/src/stores/context.js` | **Nuovo** |
| `frontend/src/core/components/SearchDrawer.vue` | **Nuovo** |
| `frontend/src/core/components/ContextFilterBanner.vue` | **Nuovo** |
| `frontend/src/core/components/AppTopbar.vue` | **Modifica** |
| `frontend/src/core/composables/useContextFilter.js` | **Nuovo** |
| `frontend/src/core/components/details/SoggettoDetail.vue` | **Nuovo** |
| `frontend/src/core/components/details/FornitoreDetail.vue` | **Nuovo** |
| `frontend/src/core/components/details/ClienteGasDetail.vue` | **Nuovo** |
| `frontend/src/core/components/details/ClienteEEDetail.vue` | **Nuovo** |
| `frontend/src/core/components/details/ClienteAcquaDetail.vue` | **Nuovo** |
| `frontend/src/locales/it.json` | **Modifica** |
| `frontend/src/locales/en.json` | **Modifica** |

---

## Migliorie future

| # | Miglioria | Priorita' | Note |
|---|---|---|---|
| 1 | **Full-text search con tsvector** — colonna generata + indice GIN per ranking nativo e performance su grandi volumi | Media | Alternativa a ILIKE+trigram, piu' potente ma piu' complessa |
| 2 | **Ricerche recenti** — ultime 5-10 in localStorage, mostrate all'apertura del drawer con campo vuoto | Bassa | Velocizza operatori che lavorano con stessi soggetti |
| 3 | **Contesto nell'URL** — propagare come query param `?ctx=cliente:id` per link condivisibili e persistenza al refresh | Media | Non critico in prima iterazione |
| 4 | **Cache risultati frequenti** — Redis con TTL 30s per ricerche ripetute | Bassa | Solo se emerge come bottleneck |
| 5 | **Tipo predefinito intelligente** — derivare da ruolo_sistema o area funzionale corrente | Bassa | Mappa nel profilo utente |

---

*ZeroERP — Contesto Globale e Ricerca Universale*
*Sviluppo Concentrico — anello 2/3, dipende da anagrafiche e pratiche*
