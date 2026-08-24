## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_contratti_righe_guard_esclusione_figlio_bundle()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe)
> • [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> • [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)
> • [vendite.listini_righe_componenti](/dbzero/vendite/tabelle/listini_righe_componenti)
>
Approfondimento funzioni:
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale

(rev 2026-08-21 — §6.1, 2026-05-16)

**Un bundle si vende come unità: non se ne può escludere un pezzo.**

Il guard blocca le righe di contratto con `tipo_eccezione = 'ESCLUSIONE'` quando l'articolo
escluso è un **componente figlio** di un bundle presente nel listino del contratto.
L'esclusione resta legittima su un articolo standalone o sul **padre** del bundle — mai sul
singolo figlio.

La ragione è che il prezzo del bundle è il prezzo dell'insieme: togliere un componente e
tenere il prezzo del padre significherebbe fatturare qualcosa che non si consegna, e
ricalcolare il padre significherebbe disfare il bundle. La soluzione non è a metà: o si
esclude tutto il bundle, o non si esclude niente.

---

### Aggancio

Trigger `trg_contratti_righe_a10_guard_esclusione_figlio_bundle_ins_upd` — fase `_a10_`,
`BEFORE INSERT OR UPDATE` su `vendite.contratti_righe`, `FOR EACH ROW`,
`WHEN (NEW.tipo_eccezione = 'ESCLUSIONE')`.

⭐ Il filtro sul tipo di eccezione sta nel `WHEN`, non nel corpo: la funzione non viene
neppure invocata sulle righe normali. Chi la riaggancia altrove deve riportare anche il
`WHEN`, o pagherà due query per ogni riga di contratto.

---

### Le tre strade, secondo lo stato del contratto

Il guard deve sapere **quale versione di listino** guardare, e la risposta dipende da dove si
trova il contratto:

**Branch 1 — nessun listino** (`contratti.listino_id IS NULL`): non c'è alcun bundle da cui
escludere. Passa.

**Branch 2 — contratto in preparazione** (`listino_versione_id IS NULL`): la versione non è
ancora fissata, quindi si guarda quella **operativa oggi** — `attivo = TRUE`,
`stato IN ('ATTIVA','CHIUSA')`, `validita @> CURRENT_DATE`.

**Branch 3 — contratto attivo** (`listino_versione_id IS NOT NULL`): si guarda esattamente
la versione **fissata all'attivazione**, senza rivalutare quale sia quella corrente.

La distinzione è il punto delicato dell'intera funzione: usare la versione corrente su un
contratto attivo lo esporrebbe a cambi di listino successivi alla firma.

---

### ⚠️ `articolo_figlio_id`, non `articolo_componente_id`

In `listini_righe_componenti` convivono due colonne che si somigliano:

* `articolo_figlio_id` → **UUID dell'articolo** — è questa che va confrontata con
  `contratti_righe.articolo_id`;
* `articolo_componente_id` → referenzia `catalogo.articoli_componenti.id`, cioè la riga di
  distinta, **non** l'articolo.

Usare la seconda produrrebbe un `EXISTS` sempre falso — un guard che non blocca mai, e che
non fallisce nessun test perché non solleva. È il tipo di errore che si scopre in
produzione, ed è annotato nel corpo proprio per questo.

---

### ⚠️ `CURRENT_DATE` compare anche nel branch 3

Anche sulla versione fissata, la riga di componente deve essere valida **oggi**
(`lrc.attivo = TRUE AND lrc.validita @> CURRENT_DATE`). Il guard è quindi
**dipendente dalla data di esecuzione**: un componente uscito di validità smette di essere
protetto, e da quel momento la sua esclusione passa.

Da tenere presente scrivendo i test — un pgTAP che usi righe con `validita` fuori dal
presente verifica il ramo sbagliato — e valutando il comportamento su contratti storici.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA` (455) | Riga `ESCLUSIONE` su articolo che è componente figlio di un bundle nel listino del contratto |

Sollevato via `script.fn_log_and_raise_error`, area `vendite`, con `NEW.tx_id` propagato:
l'errore resta correlabile alla transazione applicativa.

---

{% include-markdown "signature-core.md" %}
