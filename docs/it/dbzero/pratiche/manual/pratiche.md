## 📘 Documentazione Concettuale – Tabella `pratiche.pratiche`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.tipi_prestazione](/dbzero/pratiche/tabelle/tipi_prestazione)
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale)
> * [config.stati_pratiche](/dbzero/config/tabelle/stati_pratiche)
> * [config.priorita_pratiche](/dbzero/config/tabelle/priorita_pratiche)
> * [config.canali_pratiche](/dbzero/config/tabelle/canali_pratiche)

---

### 🎯 Scopo Principale

La tabella `pratiche.pratiche` e' l'**entita' principale** del modulo gestione pratiche. Rappresenta una pratica operativa con il suo ciclo di vita completo: tipo, stato, priorita', assegnazione, tracciabilita' e gerarchia.

---

### 🧱 Ruolo nel processo

* Ogni pratica ha un **tipo_prestazione** che ne determina i template flussi disponibili.
* Lo **stato** governa le transizioni del ciclo di vita (BOZZA → APERTA → CHIUSA).
* L'**assegnazione** (risorsa umana / unita' organizzativa) definisce chi lavora la pratica.
* La **gerarchia** (`pratica_padre_id`) consente sotto-pratiche.
* La **tracciabilita' cross-pratica** (`flusso_origine_id`) collega la pratica al flusso che l'ha generata.
* Ogni evento significativo viene registrato nel **giornale**.

---

### ⚙️ Colonne specifiche

| Colonna | Note |
|---------|------|
| `emittente_fiscale_id` | BIGINT NOT NULL. FK a `anagrafiche.emittenti_fiscali` — identita' fiscale che gestisce la pratica. |
| `soggetto_id` | UUID nullable. FK a `anagrafiche.soggetti` — il soggetto interessato dalla pratica. |
| `pratica_padre_id` | BIGINT nullable. Self-reference per gerarchia. ON DELETE SET NULL. |
| `flusso_origine_id` | BIGINT nullable. FK a `pratiche.flussi` — tracciabilita' cross-pratica. Impostato dalla funzione `fn_genera_pratica_da_flusso` (DB-5). ON DELETE SET NULL. |
| `canale_origine_id` | INTEGER nullable. FK a `config.canali_pratiche` — da quale sorgente esterna e' arrivata la richiesta. NULL = creata internamente. |
| `solo_interna` | BOOLEAN DEFAULT false. Se true, la pratica non espone flussi su canali esterni. |
| `codice` | TEXT nullable. Codice pratica generato da trigger (DB-5). |
| `data_scadenza` | DATE nullable. Scadenza prevista per la pratica. |

---

### 🔗 FK principali

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

### ✅ Convenzioni

* PK BIGINT IDENTITY (tabella operativa ad alto volume).
* `storicizza = true` per tracciamento modifiche.
* Trigger standard (audit, tx_id, storico) applicati automaticamente da `dbops.fn_run_automations()`.
* Trigger business-specific (giornale, generazione codice) in DB-5.

---

{% include-markdown "signature-core.md" %}
