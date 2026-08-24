## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_listini_righe_guard_tipologia()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe)
> • [vendite.listini](/dbzero/vendite/tabelle/listini)
> • [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
>
Approfondimento funzioni:
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale

(rev 2026-08-21 — pricing v5)

**Un articolo entra solo in un listino della sua tipologia.** Il guard impone che
`catalogo.articoli.listino_tipologia_id` coincida con `vendite.listini.tipologia_id` del
listino a cui la riga appartiene.

La tipologia è ciò che rende confrontabili i prezzi dentro un listino: mescolare articoli di
tipologie diverse produce un listino che non risponde più alla domanda per cui esiste — qual
è il prezzo di questa famiglia di prodotti per questo contesto. Il guard tiene il listino
omogeneo all'ingresso, invece di lasciare che l'incoerenza emerga in fase di pricing.

---

### Aggancio

Trigger `trg_listini_righe_a10_guard_tipologia_ins_upd` — fase `_a10_`,
`BEFORE INSERT OR UPDATE` su `vendite.listini_righe`, `FOR EACH ROW`.

---

### Regole applicate

Una sola query risale la catena `listini_righe → listini_versioni → listini` e legge in
parallelo la tipologia dell'articolo:

1. **Articolo non classificato** — `articoli.listino_tipologia_id IS NULL` →
   `E_ARTICOLO_TIPOLOGIA_MANCANTE`. Un articolo senza tipologia non entra in **nessun**
   listino tipizzato: non c'è modo di dire se ci appartiene.
2. **Tipologie diverse** — `articolo.tipologia IS DISTINCT FROM listino.tipologia` →
   `E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE`.

I due controlli sono separati apposta: dicono cose diverse a chi legge l'errore — *classifica
l'articolo* contro *hai scelto il listino sbagliato* — e portano a due azioni diverse.

---

### ⚠️ Se la catena non risolve, il primo errore mente

`v_articolo_tipologia_id` e `v_listino_tipologia_id` arrivano dallo **stesso** `SELECT INTO`,
che unisce articolo, versione e listino con dei `JOIN` interni. Se una qualunque delle tre
righe manca — articolo inesistente, `listino_versione_id` orfano — la query non restituisce
righe ed **entrambe** le variabili restano `NULL`.

Il primo controllo scatta e solleva `E_ARTICOLO_TIPOLOGIA_MANCANTE`, cioè *«questo articolo
non è classificato»* — quando la causa vera può essere che la **versione di listino** non
esiste. L'errore è fail-closed, quindi il dato resta protetto, ma il messaggio indirizza
verso l'oggetto sbagliato.

Indizio per riconoscerlo nel log: nel context, `listino_tipologia_id` è `null` insieme a
tutto il resto. Se il listino esistesse davvero, quel campo sarebbe valorizzato.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_ARTICOLO_TIPOLOGIA_MANCANTE` | L'articolo non ha `listino_tipologia_id` (o la catena articolo/versione/listino non risolve) |
| `E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE` | Tipologia dell'articolo diversa da quella del listino |

Entrambi via `script.fn_log_and_raise_error`, area `vendite`.

---

{% include-markdown "signature-core.md" %}
