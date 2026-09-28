## 📘 Documentazione Concettuale – Tabella `config.aree_funzionali`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
Tabelle correlate:
>
[config.azioni_processo](/dbzero/config/tabelle/azioni_processo)
> [config.profili_accesso_aree](/dbzero/config/tabelle/profili_accesso_aree)
> [config.user_override_aree](/dbzero/config/tabelle/user_override_aree)
> [config.area_model_overrides](/dbzero/config/tabelle/area_model_overrides)

---

La tabella **`config.aree_funzionali`** è il **catalogo delle aree funzionali** del sistema permessi.

Ogni area corrisponde a uno **schema PostgreSQL** (es. `vendite`, `anagrafiche`, `catalogo`). Il mapping è automatico: Django risolve l'area dal `db_table` del model, senza configurazione manuale.

---
### 🎯 Scopo Principale
* Definire il **perimetro funzionale** su cui si applicano i livelli di accesso (TUTTO / LETTURA / BLOCCATO).
* Fornire il **mapping area → schema DB** per la risoluzione automatica dei permessi in Django.
* Gestire l'**ordine di visualizzazione** nell'interfaccia di configurazione profili reparto.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `codice` | Identificativo univoco dell'area, usato nelle query e nell'API |
| `codice_interno` | Codice immutabile per mapping applicativo |
| `schema_db` | Nome dello schema PostgreSQL associato (chiave del mapping automatico) |
| `ordinamento` | Ordine di visualizzazione nella UI gestione profili |

**Nota:** `codice` e `schema_db` sono separati per consentire la rinomina della label dell'area senza impatto sullo schema fisico (es. `codice='finanza'`, `schema_db='contabilita'`).

---

### Relazioni

`config.aree_funzionali` è referenziata da:

| Tabella | Campo | Scopo |
|---------|-------|-------|
| `config.azioni_processo` | `area_id` | Raggruppa le azioni per area |
| `config.profili_accesso_aree` | `area_id` | Livello accesso del profilo per area |
| `config.user_override_aree` | `area_id` | Override individuale per area |
| `config.area_model_overrides` | `area_id` | Riassegnazione model a area diversa |

---

### Chi la scrive

**Solo il CSV** `80_data/sql/config/aree_funzionali.csv`. Il nome dell'area (`descrizione`) e l'ordine (`ordinamento`) si cambiano lì, e il migrate successivo li porta ovunque. L'applicazione la legge e basta: non è nel pannello di configurazione e non ha una schermata di modifica. Un'area nuova è un modulo nuovo, quindi nasce nel CSV con il suo schema.

---

### Seed iniziale

| codice | schema_db | ordinamento | introdotta |
|--------|-----------|-------------|------------|
| anagrafiche | anagrafiche | 10 | seed iniziale |
| vendite | vendite | 20 | seed iniziale |
| acquisti | acquisti | 30 | seed iniziale |
| catalogo | catalogo | 40 | seed iniziale |
| contabilita | contabilita | 50 | seed iniziale |
| magazzino | magazzino | 60 | seed iniziale |
| pagamenti | pagamenti | 70 | seed iniziale |
| storico | storico | 80 | seed iniziale |
| config | config | 90 | seed iniziale |
| core | core | 100 | seed iniziale |
| pratiche | pratiche | 110 | 2026-04-10 |
| documenti | documenti | 120 | 2026-05-03 (modelli documenti — gestione template/asset) |
| strumenti | strumenti | 130 | 2026-07-21 (superfici operative self-service — code di lavoro/stampa; area *virtuale*, accesso dichiarato esplicitamente su `DomainAPIView`, non da mapping model→schema) |

---

> **"`config.aree_funzionali` è il pilastro del sistema permessi: collega ogni schema DB a un'area funzionale, consentendo la risoluzione automatica dei permessi senza configurazione manuale."**
