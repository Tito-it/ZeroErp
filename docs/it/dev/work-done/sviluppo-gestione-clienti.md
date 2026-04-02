# Sviluppo Gestione Clienti — Completato

> Stato: **COMPLETATO**
>
> Data inizio: 23 marzo 2026 | Completato: marzo 2026
>
> Continuazione: [sviluppo-gestione-clienti-v2.md](../work-in-progress/sviluppo-gestione-clienti-v2.md) — funzionalita' avanzate (subentro, disdetta, billing account parent/child)

---

## Decisioni architetturali

### Discriminante `richiede_pdp`

Il flag `config.utilities.richiede_pdp` e' l'**unico discriminante** per stabilire se la creazione manuale di un cliente e' ammessa:

| `richiede_pdp` | Creazione manuale | Istanza | Indirizzo | Workflow |
|:-:|:-:|:-:|:-:|:-:|
| `false` | Ammessa | Sempre fittizia | Facoltativo | Non richiesto |
| `true` | Bloccata | Reale (con PDP) | Obbligatorio | Solo via pratiche |

**Rischio noto**: se in futuro servira' un'utility senza PDP che richiede comunque il workflow pratiche, bastera' aggiungere un boolean `solo_pratica` su `config.utilities`.

### ClienteService riusabile

`ClienteService.crea_cliente()` accetta parametri opzionali per istanza e billing account:

| Chiamante | `istanza_utility_id` | `billing_account_id` | Scenario |
| --- | --- | --- | --- |
| Creazione manuale | `NULL` — genera | `NULL` — genera | Utility con `richiede_pdp = false` |
| Motore pratiche | Valorizzato | Valorizzato o NULL | Utility con `richiede_pdp = true` |
| Subentro (futuro) | `NULL` — genera nuova | `NULL` — genera nuovo | Chiude il precedente, crea nuovo ciclo |

---

## Implementazione completata

### Backend

| Componente | File | Stato |
| --- | --- | --- |
| Repository | `apps/anagrafiche/db/clienti_repository.py` | 12 metodi (CRUD + lookup + validazione) |
| Service | `apps/anagrafiche/services/clienti_service.py` | Orchestrator riusabile con transazione atomica |
| API views | `apps/anagrafiche/api/views_clienti.py` | 3 view (list/create, detail/update, utility lookup) |
| URL routing | `apps/anagrafiche/api/urls.py` | 3 rotte clienti |
| Test service | `apps/anagrafiche/tests/services/test_clienti_service.py` | 29 test case |
| Test API | `apps/anagrafiche/tests/api/test_clienti_api.py` | Test PATCH |

**Endpoint API:**

| Metodo | Path | Scopo |
| --- | --- | --- |
| GET | `/api/v1/anagrafiche/clienti/` | Lista paginata con search e filtri |
| POST | `/api/v1/anagrafiche/clienti/` | Crea cliente (catena completa) |
| GET | `/api/v1/anagrafiche/clienti/{id}/` | Dettaglio con dati istanza + BA + soggetto |
| PATCH | `/api/v1/anagrafiche/clienti/{id}/` | Aggiorna campi editabili |
| GET | `/api/v1/anagrafiche/utilities/manual-lookup/` | Utility con richiede_pdp=false |

### Frontend

| Componente | File | Note |
| --- | --- | --- |
| Store Pinia | `anagrafiche/stores/clienti.js` | fetchList, fetchDetail, create, update |
| API functions | `anagrafiche/api/anagrafiche.js` | 5 funzioni (list, get, create, update, lookupUtilities) |
| ClientiSearchTable | `anagrafiche/components/ClientiSearchTable.vue` | Filtri: search, utility, stato. Colonne: codice, ragione sociale, CF, utility, stato, data |
| ClienteDrawer | `anagrafiche/components/ClienteDrawer.vue` | Create/edit con: soggetto, utility, indirizzo, pagamenti, PA, CIG/CUP, garanzia, contatto inline |
| ClientiView | `anagrafiche/views/ClientiView.vue` | Pagina completa con sub-drawer contatti/indirizzi/conti |
| Routing | `router/index.js` | Rotta `anagrafiche-clienti` |
| i18n | `locales/it.json` | Chiavi `clienti.*` |

### Contatti, indirizzi e conti bancari a due livelli

Implementato nel ClienteDrawer:

- **Livello soggetto** (ereditati, sola lettura): indirizzi e conti del soggetto, non modificabili dal contesto cliente
- **Livello ruolo/cliente** (specifici, modificabili): collegati al `soggetto_ruolo_id`

### Billing account

- Creazione automatica in trasparenza (codice generato da trigger)
- Supporto `parent_account_id` nel modello DB e nel repository
- Sezione BA visibile nel drawer in modalita' edit

---

## Building block riutilizzati

Consultare il [Catalogo Building Block Frontend](../frontend/catalogo-building-block-frontend.md) e il [Catalogo Building Block Backend](../backend/catalogo-building-block-backend.md) per l'elenco completo dei componenti riutilizzabili.

---

*Sviluppo Gestione Clienti — ZeroERP (marzo 2026)*
