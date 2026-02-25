## 📘 Documentazione Concettuale – Funzione `vendite.fn_resolve_commessa_prezzi`

> 👀 **Vedi anche**
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_resolve_prezzo_listino](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino)  
>
> **Approfondimento tabelle:**
>
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [vendite.attivita_fatturabili_lotti](/dbzero/vendite/tabelle/attivita_fatturabili_lotti)  
> • [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe)  
>
---

### 🎯 Scopo Principale

La funzione `vendite.fn_resolve_commessa_prezzi` analizza le righe di
`attivita_fatturabili` appartenenti a un lotto e confronta `prezzo_unitario`
con il prezzo risolto via listino.

Nello stato attuale (pre-DB-L3 commesse), opera come equivalente operativo su lotto
attivita e restituisce esito diagnostico per ogni riga.

---

### ✅ Regole principali

* `p_lotto_id` obbligatorio e `> 0`.
* Il lotto deve esistere.
* Per ogni riga del lotto:
  * risolve contesto BA/utility/emittente,
  * richiama `fn_resolve_prezzo_listino(...)`,
  * confronta prezzo attuale vs prezzo risolto.
* La funzione non interrompe l'analisi alla prima anomalia:
  * ritorna un esito riga-per-riga (`OK`, `PRICE_STALE`, `PREZZO_ASSENTE`, `UOM_ASSENTE`, `ERRORE_RESOLVER`).

---

### 🧩 Output

Ritorna, per ogni riga attività del lotto:

* identificativo attività,
* prezzo attuale,
* prezzo risolto,
* delta prezzo,
* flag `stale`,
* metadati del match (`listino_versione_id`, `listino_riga_id`, `match_level`),
* `esito` e `dettaglio`.

---

{% include-markdown "signature-core.md" %}
