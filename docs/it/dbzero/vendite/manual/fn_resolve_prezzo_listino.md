## 📘 Documentazione Concettuale – Funzione `vendite.fn_resolve_prezzo_listino`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.listini](/dbzero/vendite/tabelle/listini)  
> • [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)  
> • [vendite.listini_associazioni](/dbzero/vendite/tabelle/listini_associazioni)  
> • [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe)  
>
---

### 🎯 Scopo Principale

La funzione `vendite.fn_resolve_prezzo_listino` risolve in modo deterministico il
prezzo da applicare per `articolo + uom + data_riferimento`, considerando contesto
BA/utility/emittente e priorita` multi-listino.

---

### ✅ Regole principali

* `p_data_riferimento` e` obbligatoria.
* Input ID numerici validi solo se `> 0`.
* La risoluzione usa solo record `attivo=true` e versioni `stato='ATTIVA'`.
* Precedenze implementate:
  * BA+utility+emittente
  * BA+utility
  * BA+emittente (non-utility)
  * BA (non-utility)
  * utility+emittente
  * utility
  * fallback articolo+uom
* Tie-break:
  * `listini_associazioni.priorita`
  * `listini_versioni.priorita`
  * validita` piu` recente/specifica
* Se nessun match: errore esplicito `PRICE_NOT_FOUND`.
* Se pareggio totale: errore esplicito `AMBIGUOUS_PRICE_MATCH`.

---

### 🧩 Output

Ritorna una riga con:

* listino selezionato,
* versione selezionata,
* riga prezzo selezionata,
* associazione usata,
* prezzo,
* livello di match (`match_level`).

---

{% include-markdown "signature-core.md" %}
