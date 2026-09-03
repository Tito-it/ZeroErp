## 📘 Documentazione Concettuale – Funzione Trigger `vendite.trgfn_listini_righe_guard_stato`

> 👀 **Vedi anche**
>
Tabelle:
>
[vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe)
> [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)
>
Funzioni:
>
[vendite.fn_resolve_prezzo_listino](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2)

---
### 🎯 Scopo Principale

Guard N6 — terzo livello di protezione: impedisce la modifica o cancellazione di righe listino
quando lo stato della versione padre non lo consente o quando la riga e` gia` stata propagata
a valle (commesse, attivita` fatturabili).

---

### Contesto di Esecuzione

* **Tipo**: `BEFORE UPDATE OR DELETE` trigger su `vendite.listini_righe`
* **Nome trigger**: `trg_listini_righe_a10_guard_stato_upd_dlt`
* **Fase**: `_a10_` (guard/block — prima linea di difesa)
* **Non si applica a INSERT**: l'aggiunta di righe a una versione ATTIVA e` ammessa come rettifica controllata

---

### Logica Operativa

Il trigger recupera lo `stato` della versione padre (`vendite.listini_versioni`) tramite `OLD.listino_versione_id` e applica le seguenti regole:

| Stato versione | Comportamento |
| --- | --- |
| `BOZZA` | Passa sempre — modifica libera |
| `ATTIVA` | Verifica propagazione: se la riga e` referenziata in almeno una tabella a valle → blocca con `E_RIGA_LISTINO_PROPAGATA`. Se non propagata → passa (rettifica controllata ammessa) |
| `CHIUSA` | Blocca sempre con `E_RIGA_LISTINO_VERSIONE_CHIUSA` |

---

### Tabelle controllate per propagazione

Il check di propagazione verifica se `OLD.id` e` referenziato come `listino_riga_id` in:

1. `vendite.commesse_attivita` — riga listino che ha generato il `prezzo_snapshot`
2. `vendite.attivita_fatturabili` — propagato dalla commessa, usato per guard e tracciamento pipeline

Per aggiungere nuove tabelle al controllo: aggiungere `UNION ALL` nel corpo della funzione (espansione concentrica).

---

### Codici errore

| Codice | Condizione | Messaggio atteso |
| --- | --- | --- |
| `E_RIGA_LISTINO_VERSIONE_CHIUSA` | UPDATE/DELETE su riga di versione CHIUSA | Operazione non ammessa su versione chiusa |
| `E_RIGA_LISTINO_PROPAGATA` | UPDATE/DELETE su riga ATTIVA gia` propagata a valle | Riga gia` propagata, modifica non ammessa |

---

### Relazione con i livelli di protezione N6

Questo trigger e` il **terzo livello** della protezione N6 (espansione concentrica):

1. **Primo livello**: vincoli EXCLUDE GIST su `listini_versioni` e `listini_associazioni` — impediscono overlap temporali
2. **Secondo livello**: logica service Python — validazione business prima della persistenza
3. **Terzo livello** (questo trigger): guard DB che impedisce modifica/cancellazione di righe gia` consumate a valle

---

{% include-markdown "signature-core.md" %}
