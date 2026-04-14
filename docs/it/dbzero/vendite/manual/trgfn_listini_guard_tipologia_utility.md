## 📘 Documentazione Concettuale – Funzione Trigger `vendite.trgfn_listini_guard_tipologia_utility`

> 👀 **Vedi anche**
>
Tabelle:
>
[vendite.listini](/dbzero/vendite/tabelle/listini)
> [config.listini_tipologie_utilities](/dbzero/config/manual/listini_tipologie_utilities)
> [config.listini_tipologie](/dbzero/config/manual/listini_tipologie)

---
### 🎯 Scopo Principale

Guard defense-in-depth: verifica che la coppia `(utility_id, tipologia_id)` su `vendite.listini` sia ammessa dalla matrice `config.listini_tipologie_utilities` con `attivo = true`.

---

### Contesto di Esecuzione

* **Tipo**: `BEFORE INSERT OR UPDATE OF utility_id, tipologia_id` su `vendite.listini`
* **Nome trigger**: `trg_listini_a10_guard_tipologia_utility_ins_upd`
* **Fase**: `_a10_` (guard/block)
* Scatta **solo** quando cambiano `utility_id` o `tipologia_id`, non su ogni UPDATE

---

### Logica Operativa

1. Verifica se la coppia `(NEW.utility_id, NEW.tipologia_id)` esiste in `config.listini_tipologie_utilities` con `attivo = true`
2. Se non esiste → errore `E_LISTINO_TIPOLOGIA_UTILITY`
3. Se esiste → passa

---

### Codici errore

| Codice | Condizione | Messaggio |
| --- | --- | --- |
| `E_LISTINO_TIPOLOGIA_UTILITY` | Coppia utility/tipologia non ammessa o non attiva nella matrice | Combinazione utility %s / tipologia %s non ammessa per questo listino |

---

### Note operative

* La matrice e` gestita come seed (`config.listini_tipologie_utilities`) — nuove combinazioni si aggiungono con INSERT, non con DDL.
* Il trigger e` il terzo livello di validazione (dopo UI e service Python) — defense-in-depth.
* Per disabilitare una combinazione senza cancellarla: `UPDATE config.listini_tipologie_utilities SET attivo = false WHERE ...`. I listini gia` creati con quella coppia restano validi, ma nuovi listini o modifiche vengono bloccati.

---

{% include-markdown "signature-core.md" %}
