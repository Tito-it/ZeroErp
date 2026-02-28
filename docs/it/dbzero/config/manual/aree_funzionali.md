## 📘 Documentazione Concettuale – Tabella `config.aree_funzionali`

> 👀 **Vedi anche**
>
> Architettura di riferimento:
>
> * [Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
> Tabelle correlate:
>
> * [config.azioni_processo](/dbzero/config/tabelle/azioni_processo)
> * [config.profili_reparto_aree](/dbzero/config/tabelle/profili_reparto_aree)
> * [config.user_override_aree](/dbzero/config/tabelle/user_override_aree)
> * [config.area_model_overrides](/dbzero/config/tabelle/area_model_overrides)

---

La tabella **`config.aree_funzionali`** è il **catalogo delle aree funzionali** del sistema permessi.

Ogni area corrisponde a uno **schema PostgreSQL** (es. `vendite`, `anagrafiche`, `catalogo`). Il mapping è automatico: Django risolve l'area dal `db_table` del model, senza configurazione manuale.

---

### 🎯 Scopo Principale

* Definire il **perimetro funzionale** su cui si applicano i livelli di accesso (TUTTO / LETTURA / BLOCCATO).
* Fornire il **mapping area → schema DB** per la risoluzione automatica dei permessi in Django.
* Gestire l'**ordine di visualizzazione** nell'interfaccia di configurazione profili reparto.

---

### 🔑 Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `codice` | Identificativo univoco dell'area, usato nelle query e nell'API |
| `codice_interno` | Codice immutabile per mapping applicativo |
| `schema_db` | Nome dello schema PostgreSQL associato (chiave del mapping automatico) |
| `ordinamento` | Ordine di visualizzazione nella UI gestione profili |

**Nota:** `codice` e `schema_db` sono separati per consentire la rinomina della label dell'area senza impatto sullo schema fisico (es. `codice='finanza'`, `schema_db='contabilita'`).

---

### 🔗 Relazioni

`config.aree_funzionali` è referenziata da:

| Tabella | Campo | Scopo |
|---------|-------|-------|
| `config.azioni_processo` | `area_id` | Raggruppa le azioni per area |
| `config.profili_reparto_aree` | `area_id` | Livello accesso del reparto per area |
| `config.user_override_aree` | `area_id` | Override individuale per area |
| `config.area_model_overrides` | `area_id` | Riassegnazione model a area diversa |

---

### 📋 Seed iniziale (10 aree)

| codice | schema_db | ordinamento |
|--------|-----------|-------------|
| anagrafiche | anagrafiche | 10 |
| vendite | vendite | 20 |
| acquisti | acquisti | 30 |
| catalogo | catalogo | 40 |
| contabilita | contabilita | 50 |
| magazzino | magazzino | 60 |
| pagamenti | pagamenti | 70 |
| storico | storico | 80 |
| config | config | 90 |
| core | core | 100 |

---

> 🧠 **"`config.aree_funzionali` è il pilastro del sistema permessi: collega ogni schema DB a un'area funzionale, consentendo la risoluzione automatica dei permessi senza configurazione manuale."**
