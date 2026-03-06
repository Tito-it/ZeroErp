## 📘 Documentazione Concettuale – Tabella `pratiche.calcoli_tempo`

> 👀 **Vedi anche**
>
> Tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)
> * [pratiche.formule_tempo](/dbzero/pratiche/manual/formule_tempo)
> * [pratiche.sospensioni](/dbzero/pratiche/manual/sospensioni)
>
> Funzioni:
>
> * [fn_calcola_tempo_netto_da_a](/dbzero/pratiche/manual/fn_calcola_tempo_netto_da_a)
> * [fn_valuta_tempo_esecuzione_da_a](/dbzero/pratiche/manual/fn_valuta_tempo_esecuzione_da_a)
> * [trgfn_flussi_calcolo_tempo_completamento](/dbzero/pratiche/manual/trgfn_flussi_calcolo_tempo_completamento)

---

### 🎯 Scopo Principale

Tabella di calcolo persistente: misura il tempo impiegato per transitare dal completamento di `flusso_da` al completamento di `flusso_a`. Alimentata automaticamente dal trigger `trgfn_flussi_calcolo_tempo_completamento` a due fasi (avvio + chiusura).

---

### 🧱 Campi chiave (semantica)

| Colonna               | Note                                                                  |
| --------------------- | --------------------------------------------------------------------- |
| `flusso_da_id`        | FK a `pratiche.flussi` — flusso di partenza — **immutabile**.         |
| `flusso_a_id`         | FK a `pratiche.flussi` — flusso di arrivo — **immutabile**.           |
| `formula_tempo_id`    | FK a `pratiche.formule_tempo` — snapshot formula — **immutabile**.    |
| `data_inizio_calcolo` | `data_fine` del flusso_da — **immutabile**.                           |
| `data_fine_calcolo`   | `data_fine` del flusso_a. NULL = calcolo in corso.                    |
| `giorni_lordi`        | Giorni calendario totali. NULL mentre in corso.                       |
| `giorni_sospensione`  | Giorni di sospensione nel periodo. NULL mentre in corso.              |
| `giorni_netti`        | `giorni_lordi - giorni_sospensione`. NULL mentre in corso.            |
| `giorni_formula`      | Snapshot di `formule_tempo.giorni_esecuzione` — **immutabile**.       |
| `sforato`             | `true` se `giorni_netti > giorni_formula`. NULL mentre in corso.      |

---

### 🔒 Vincoli e immutabilita'

* **UNIQUE** su `(pratica_id, flusso_da_id, flusso_a_id, formula_tempo_id)`.
* **CHECK** `data_fine_calcolo IS NULL OR data_fine_calcolo > data_inizio_calcolo`.
* **CHECK** `giorni_formula > 0`, `flusso_da_id <> flusso_a_id`.
* **Guard immutabilita'**: trigger `trg_calcoli_tempo_a10_guard_immutabili_upd` blocca UPDATE su `pratica_id`, `flusso_da_id`, `flusso_a_id`, `formula_tempo_id`, `giorni_formula`, `data_inizio_calcolo`.

Campi aggiornabili: `data_fine_calcolo`, `giorni_lordi`, `giorni_sospensione`, `giorni_netti`, `sforato`, `tx_id`, audit.

---

### ⚙️ Ciclo di vita

1. **Avvio**: flusso_da va COMPLETATO → INSERT con `data_inizio_calcolo`, `giorni_formula`.
2. **Chiusura**: flusso_a va COMPLETATO → UPDATE con `data_fine_calcolo`, calcolo giorni.
3. **Ordine invertito**: se flusso_a completa prima di flusso_da, quando flusso_da completa il trigger fa INSERT + UPDATE immediato.

---

{% include-markdown "signature-core.md" %}
