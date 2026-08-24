## 📘 Documentazione Concettuale – Tabella `catalogo.note_articoli`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
> • [vendite.note](/dbzero/vendite/tabelle/note)
> • [catalogo.note_articoli_componenti](/dbzero/catalogo/tabelle/note_articoli_componenti)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Partizione** delle note per `catalogo.articoli`. Non è una tabella a sé: è una delle
partizioni di `vendite.note`, partizionata per `target_tipo`.

Il documento principale del meccanismo è **[vendite.note](/dbzero/vendite/tabelle/note)** —
là stanno il modello di ancoraggio (testata/riga), il posizionamento, l'ordinamento di
rendering e le regole comuni. Qui si documenta solo ciò che è specifico degli articoli.

Contiene 59 righe al 2026-08-21: è una partizione **in uso**, non una predisposizione.

---

### Che cosa cambia rispetto alle altre partizioni

* **`target_id` è un `uuid`**, perché la chiave di `catalogo.articoli` è un UUID — mentre le
  partizioni dei documenti di vendita puntano a chiavi `bigint`. È la ragione per cui la
  partizione esiste: il tipo del bersaglio non è uniforme fra i domini.
* **Il bersaglio non è un documento ma un'anagrafica**: una nota su un articolo vale per
  *tutte* le sue apparizioni future, non per una singola riga di un singolo documento. È la
  differenza fra annotare il catalogo e annotare una vendita.

---

### ⚠️ La FK forte è nella partizione, non nel padre

Il partizionamento per `target_tipo` esiste proprio per questo: ogni partizione può avere la
propria **FK forte** verso la tabella che annota. Sul padre `vendite.note` quella FK non
potrebbe esistere, perché il bersaglio cambia natura da una partizione all'altra.

Conseguenza pratica: **le note seguono il ciclo di vita dell'articolo**. Se la FK è
`ON DELETE RESTRICT` — come nel resto del progetto — un articolo con note non si cancella
finché le note ci sono.

---

{% include-markdown "signature-core.md" %}
