## 📘 Documentazione Concettuale – Funzione `catalogo.fn_uom_fonti_conversione`

> **Ultimo aggiornamento**: 10 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa) — la mappatura dell'articolo, la fonte di priorità 1
> * [catalogo.unita_misura_conversioni](/dbzero/catalogo/tabelle/unita_misura_conversioni) — la conversione generale, la fonte di priorità 2
>
> Approfondimento funzioni:
>
> * [catalogo.fn_get_uom_factor](/dbzero/catalogo/funzioni/fn_get_uom_factor) — il fattore a una data, che la legge
> * [catalogo.fn_uom_operativa_alla_data](/dbzero/catalogo/funzioni/fn_uom_operativa_alla_data) — la mappatura a una data, che la legge
> * [catalogo.fn_uom_primo_giorno_non_convertibile](/dbzero/catalogo/funzioni/fn_uom_primo_giorno_non_convertibile) — la copertura di un periodo, che la legge

---

### 🎯 Scopo Principale

Dice **da dove** un'unità si converte nell'unità base di un articolo, e per quali giorni. Una riga
per fonte, col fattore (quante unità base vale un'unità) e il periodo:

| Priorità | Fonte | Periodo |
| --- | --- | --- |
| 0 | l'unità base stessa, fattore 1 | sempre |
| 1 | la mappatura dell'articolo (`articoli_uom_operativa`, attiva) | il suo |
| 2 | la conversione generale fra le due unità (attiva), nel verso scritto o nell'inverso | il suo |

---

### ⭐ Un predicato, una sede

«Quali righe convertono un'unità per un articolo» stava scritto due volte: nella lettura della
mappatura alla data e nella lettura della conversione generale dentro `fn_get_uom_factor`. Il giro
2-bis ne chiedeva una terza, sui periodi, per la regola dei listini. Il predicato si è estratto qui,
e le tre letture lo usano.

---

### Come è fatta

`LANGUAGE sql`, `STABLE`. Il fattore è `numeric` senza scala: l'inversa di una conversione non sta
nella scala della colonna. Le mappature di un'unità non si sovrappongono, né le conversioni di una
coppia: a una data c'è al più una fonte per priorità.

---

### Test

* `db/pgtap/catalogo/test-uom-storia-v1.sql` — il fattore di ieri e di oggi dopo «chiudi e inserisci».
* `db/pgtap/vendite/test-listino-uom-periodo-v1.sql` — la copertura dei periodi, attraverso i suoi lettori.

---

### Note di migrazione

* 2026-11-10 — nasce (brief-db-revisione-catalogo, giro 2-bis).

---

{% include-markdown "signature-core.md" %}
