## 📘 Documentazione Funzioni – Giornale Sospensioni

> 👀 **Vedi anche**
>
[pratiche.sospensioni](/dbzero/pratiche/manual/sospensioni)
> [pratiche.giornale](/dbzero/pratiche/manual/giornale)

---

### 🎯 Scopo Principale

Due trigger functions per registrare nel giornale gli eventi di sospensione e riattivazione.

---

### Funzioni

#### `pratiche.trgfn_sospensioni_giornale_ins()`

Registra `SOSPENSIONE_REGISTRATA` nel giornale su INSERT. Dettaglio JSONB: `sospensione_id`, `motivo`, `data_inizio`, `data_riattivazione_prevista`, `livello` (PRATICA/FLUSSO).

#### `pratiche.trgfn_sospensioni_giornale_riattivazione()`

Registra `SOSPENSIONE_CHIUSA` nel giornale su UPDATE OF data_fine (riattivazione). Dettaglio JSONB: `sospensione_id`, `data_inizio`, `data_fine`, `motivo`, `livello`.

---

### Trigger associati

| Nome                                              | Fase  | Evento              | Funzione                                    |
| ------------------------------------------------- | ----- | ------------------- | ------------------------------------------- |
| `trg_sospensioni_z90_giornale_ins`                | AFTER | INSERT              | `trgfn_sospensioni_giornale_ins()`          |
| `trg_sospensioni_z90_giornale_riattivazione_upd`  | AFTER | UPDATE OF data_fine | `trgfn_sospensioni_giornale_riattivazione()`|

WHEN (riattivazione): `OLD.data_fine IS NULL AND NEW.data_fine IS NOT NULL`.

---

{% include-markdown "signature-core.md" %}
