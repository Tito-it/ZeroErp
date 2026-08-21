## 📘 Documentazione Concettuale – Funzione `pratiche.trgfn_calcoli_tempo_set_periodo()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [pratiche.calcoli_tempo](/dbzero/pratiche/tabelle/calcoli_tempo)
>
Approfondimento funzioni:
> • [pratiche.trgfn_sospensioni_set_periodo](/dbzero/pratiche/funzioni/trgfn_sospensioni_set_periodo)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Mantiene `periodo_calcolo` (`tstzrange`) come **proiezione derivata** di
`data_inizio_calcolo` / `data_fine_calcolo`. È il gemello di
`trgfn_sospensioni_set_periodo`: stesso schema, stessa convenzione di bounds, stessa
divisione dei ruoli fra date (sorgente di verità) e range (superficie su cui PostgreSQL
sa ragionare per contenimento e sovrapposizione).

Serve a rispondere in modo diretto alla domanda ricorrente del dominio pratiche —
*quanto tempo è passato fra due fasi, al netto delle sospensioni* — che con due colonne
separate richiederebbe confronti a mano a ogni query.

---

### Aggancio

Trigger `trg_calcoli_tempo_a20_set_periodo_ins_upd` — fase `_a20_`,
`BEFORE INSERT OR UPDATE OF data_inizio_calcolo, data_fine_calcolo`
su `pratiche.calcoli_tempo`.

---

### Regole applicate

```sql
NEW.periodo_calcolo := tstzrange(
    NEW.data_inizio_calcolo,
    COALESCE(NEW.data_fine_calcolo, 'infinity'::timestamptz),
    '[)'
);
```

* `data_inizio_calcolo` è `NOT NULL`: l'estremo inferiore c'è sempre.
* `data_fine_calcolo` nulla = **calcolo ancora in corso** → estremo superiore `infinity`.
* Bounds `'[)'`, come per le sospensioni.

Il valore passato dal chiamante in `periodo_calcolo` viene sempre sovrascritto.

---

### ⚠️ Differenza dal gemello: qui non c'è anti-overlap

Su `pratiche.sospensioni` il range alimenta il vincolo `ex_sospensioni_no_overlap`. Su
`calcoli_tempo` **non esiste** un vincolo analogo: l'unicità è garantita per chiave
logica, da `uq_calcoli_tempo_pratica_da_a_formula`
(`pratica_id, flusso_da_id, flusso_a_id, formula_tempo_id`).

Vale la pena saperlo prima di dare per scontata una simmetria che non c'è: due calcoli
sulla stessa pratica **possono** avere periodi sovrapposti, purché differiscano per
coppia di flussi o per formula.

---

### ⚠️ Date incoerenti: parla il trigger, non il CHECK

Come per le sospensioni, il `BEFORE` gira prima dei CHECK di tabella:

| Caso | Chi parla | Errore |
|------|-----------|--------|
| `data_fine_calcolo < data_inizio_calcolo` | **il trigger** | SQLSTATE `22000` da `tstzrange` |
| `data_fine_calcolo = data_inizio_calcolo` | il CHECK | `chk_calcoli_tempo_data_fine` (confronto stretto) |

Nel primo caso il messaggio è quello interno di PostgreSQL sui range: non nomina il calcolo
né le date, e non porta a `chk_calcoli_tempo_data_fine`, che pure sembrerebbe il colpevole
naturale.

---

### ⚠️ L'`UPDATE` della sola colonna derivata non risincronizza

L'aggancio è `UPDATE OF data_inizio_calcolo, data_fine_calcolo`: scrivere direttamente
`periodo_calcolo` lo lascia divergere dalle date, in silenzio. In bonifica si aggiornano
**le date**.

---

### Codici errore

Nessuno di dominio: la funzione non chiama `script.fn_log_and_raise_error`.

---

{% include-markdown "signature-core.md" %}
