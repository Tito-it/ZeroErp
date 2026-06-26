## 📘 Documentazione Funzione – `pratiche.trgfn_sospensioni_guard_data_non_futura`

> 👀 **Vedi anche**
>
[pratiche.sospensioni](/dbzero/pratiche/manual/sospensioni)
> [pratiche.trgfn_sospensioni_set_periodo](/dbzero/pratiche/funzioni/trgfn_sospensioni_set_periodo)

---
### 🎯 Scopo Principale
Guard: vieta che una sospensione **inizi** o **finisca** nel futuro. `data_inizio` e `data_fine` non possono superare `now()` oltre una tolleranza di **2 minuti** (clock-skew tra orologio client e server). Una sospensione registra un evento già avvenuto — anche retroattivo, ma non pianificato.

`data_riattivazione_prevista` (tipo `date`) è una *previsione* e **resta libera nel futuro**: questo guard non la tocca.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_sospensioni_guard_data_non_futura()
RETURNS trigger LANGUAGE plpgsql
```

---

### Trigger associato

| Nome                                                  | Fase   | Evento                              | Tabella                |
| ----------------------------------------------------- | ------ | ----------------------------------- | ---------------------- |
| `trg_sospensioni_a10_guard_data_non_futura_ins_upd`   | BEFORE | INSERT, UPDATE OF data_inizio, data_fine | `pratiche.sospensioni` |

Fase `a10`: gira prima di `a20` (`trgfn_sospensioni_set_periodo`, derivazione di `periodo_sospensione`).

---

### Messaggi errore

| Codice                       | Messaggio                                                               | HTTP |
| ---------------------------- | ---------------------------------------------------------------------- | ---- |
| `E_SOSPENSIONE_DATA_FUTURA`  | La data indicata per la sospensione non può essere nel futuro (valore: {data}) | 422  |

---

### Note

- **Tolleranza clock-skew**: `now() + interval '2 minutes'`. Assorbe lo sfasamento tra orologio del client e del server senza falsi positivi sulla chiusura "ora"; una data realmente futura resta bloccata.
- **Difesa in profondità**: complementare al vincolo `ex_sospensioni_no_overlap` (anti-overlap) e alla validazione applicativa lato backend. Il DB resta l'autorità (DB-first).

---

{% include-markdown "signature-core.md" %}
