## 📘 Documentazione Concettuale – Tabella `pratiche.pratiche`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.tipi_prestazione](/dbzero/pratiche/tabelle/tipi_prestazione)
> [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)
> [pratiche.giornale](/dbzero/pratiche/tabelle/giornale)
> [config.stati_pratiche](/dbzero/config/tabelle/stati_pratiche)
> [config.priorita_pratiche](/dbzero/config/tabelle/priorita_pratiche)
> [config.canali_pratiche](/dbzero/config/tabelle/canali_pratiche)

---
### 🎯 Scopo Principale
La tabella `pratiche.pratiche` e' l'**entita' principale** del modulo gestione pratiche. Rappresenta una pratica operativa con il suo ciclo di vita completo: tipo, stato, priorita', assegnazione, tracciabilita' e gerarchia.

---

### Ruolo nel processo

* Ogni pratica ha un **tipo_prestazione** che ne determina i template flussi disponibili.
* Lo **stato** governa le transizioni del ciclo di vita (BOZZA → APERTA → CHIUSA). La transizione a **CHIUSA** e' inoltre vincolata ai flussi obbligatori percorribili non completati (guard `trg_pratiche_a10_guard_chiusura_flussi_upd`, D4 — il ramo morto di un bivio non blocca).
* Il **contesto anagrafico** a due rami (`soggetto_id` → `soggetto_ruolo_id` **oppure** `soggetto_id` → `istanza_utility_id`) classifica la pratica nelle lenti canoniche D1: RUOLO / ISTANZA / SOGGETTO / INTERNA (tutti NULL). Lettura canonica: [fn_lista_pratiche_per_contesto](/dbzero/pratiche/funzioni/fn_lista_pratiche_per_contesto); coerenza garantita da `trgfn_pratiche_guard_contesto`.
* L'**assegnazione** (risorsa umana / unita' organizzativa) definisce chi lavora la pratica — ortogonale al contesto cliente (le pratiche interne sono "contesto vuoto + assegnazione", D2).
* La **genealogia cross-pratica** (`pratica_padre_id` + `flusso_origine_id`) collega la pratica generata alla pratica e al flusso che l'hanno generata — entrambe valorizzate da `fn_genera_pratica_da_flusso`.
* Ogni evento significativo viene registrato nel **giornale**.

---

### Colonne specifiche

| Colonna | Note |
|---------|------|
| `emittente_fiscale_id` | BIGINT NOT NULL. FK a `anagrafiche.emittenti_fiscali` — identita' fiscale che gestisce la pratica. |
| `soggetto_id` | UUID nullable. FK a `anagrafiche.soggetti` — il soggetto interessato dalla pratica. NULL = pratica interna. |
| `soggetto_ruolo_id` | BIGINT nullable. FK a `anagrafiche.soggetti_ruoli` — contesto ruolo (ramo 1). Richiede `soggetto_id` coerente (guard contesto). |
| `istanza_utility_id` | BIGINT nullable. FK a `anagrafiche.istanze_utilities` — contesto istanza/utility (ramo 2, indipendente dal ruolo: prospect puro ammesso). Richiede `soggetto_id` coerente. |
| `pratica_padre_id` | BIGINT nullable. Self-reference per gerarchia/genealogia. Valorizzata da `fn_genera_pratica_da_flusso` per le pratiche generate (rev 2026-06-11). ON DELETE SET NULL. |
| `flusso_origine_id` | BIGINT nullable. FK a `pratiche.flussi` — il flusso che ha generato la pratica. Impostato da `fn_genera_pratica_da_flusso`. ON DELETE SET NULL. |
| `canale_origine_id` | INTEGER nullable. FK a `config.canali_pratiche` — da quale sorgente esterna e' arrivata la richiesta. NULL = creata internamente. |
| `codice` | TEXT nullable. Codice pratica generato da trigger. |
| `data_scadenza` | DATE nullable. Scadenza prevista per la pratica. |

---

### Indici notevoli

| Indice | Note |
|--------|------|
| `uq_pratiche_flusso_origine_tipo` | UNIQUE parziale su `(flusso_origine_id, tipo_prestazione_id)` WHERE `flusso_origine_id IS NOT NULL` — anti doppio-figlio della generazione cross-pratica. |
| `ix_pratiche_soggetto_ruolo_id`, `ix_pratiche_istanza_utility_id` | Parziali (NOT NULL), via `dbops.fk_index_policy` — supporto alle lenti per contesto. |

---

### FK principali

| FK | Target | onDelete |
|----|--------|----------|
| `fk_pratiche_emittente_fiscale` | `anagrafiche.emittenti_fiscali(id)` | NO ACTION |
| `fk_pratiche_tipo_prestazione` | `pratiche.tipi_prestazione(id)` | NO ACTION |
| `fk_pratiche_soggetto` | `anagrafiche.soggetti(id)` | NO ACTION |
| `fk_pratiche_stato` | `config.stati_pratiche(id)` | NO ACTION |
| `fk_pratiche_priorita` | `config.priorita_pratiche(id)` | NO ACTION |
| `fk_pratiche_risorsa_umana` | `anagrafiche.risorse_umane(id)` | NO ACTION |
| `fk_pratiche_unita_organizzativa` | `config.unita_organizzative(id)` | NO ACTION |
| `fk_pratiche_pratica_padre` | `pratiche.pratiche(id)` | SET NULL |
| `fk_pratiche_flusso_origine` | `pratiche.flussi(id)` | SET NULL |
| `fk_pratiche_canale_origine` | `config.canali_pratiche(id)` | NO ACTION |

---

### Convenzioni

* PK BIGINT IDENTITY (tabella operativa ad alto volume).
* `storicizza = true` per tracciamento modifiche.
* Trigger standard (audit, tx_id, storico) applicati automaticamente da `dbops.fn_run_automations()`.
* Trigger business-specific (giornale, generazione codice) in DB-5.

---

{% include-markdown "signature-core.md" %}
