## 📘 Documentazione Funzioni – Giornale Sospensioni

> 👀 **Vedi anche**
>
> **Tabelle:**
>
> • [pratiche.sospensioni](/dbzero/pratiche/manual/sospensioni) — la tabella sorvegliata
> • [pratiche.giornale](/dbzero/pratiche/manual/giornale) — dove finiscono gli eventi
>
> **Le due funzioni vive descritte qui:**
>
> • [pratiche.trgfn_sospensioni_giornale_ins](/dbzero/pratiche/funzioni/trgfn_sospensioni_giornale_ins)
> • [pratiche.trgfn_sospensioni_giornale_riattivazione](/dbzero/pratiche/funzioni/trgfn_sospensioni_giornale_riattivazione)

---
### 🎯 Scopo Principale
Due trigger functions per registrare nel giornale gli eventi di sospensione e riattivazione.

> ℹ️ **Questa pagina copre una coppia, non un oggetto singolo.** Nel database non
> esiste una funzione `trgfn_sospensioni_giornale`: il nome del file è il **prefisso
> di famiglia** delle due funzioni reali, `_ins` e `_riattivazione`. Sono documentate
> insieme perché sono i due lati dello stesso fatto — una sospensione che si apre e
> la stessa sospensione che si chiude — e leggerne una sola non spiega il giornale.
> Le rispettive schede auto-generate sono linkate qui sopra.

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
