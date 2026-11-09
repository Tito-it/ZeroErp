## 📘 Documentazione Concettuale – Funzione `catalogo.fn_get_uom_factor`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa) — il fattore dell'articolo, la prima fonte
> * [catalogo.unita_misura_conversioni](/dbzero/catalogo/tabelle/unita_misura_conversioni) — le conversioni generali, il ripiego
>
> Approfondimento funzioni:
>
> * [catalogo.fn_get_uom_base](/dbzero/catalogo/funzioni/fn_get_uom_base) — l'unità base dell'articolo, il primo passo
> * [catalogo.fn_uom_operativa_alla_data](/dbzero/catalogo/funzioni/fn_uom_operativa_alla_data) — la mappatura dell'articolo a una data
> * [script.trgfn_qta_from_operativa](/dbzero/script/funzioni/trgfn_qta_from_operativa) — il calcolo della quantità sulle righe di vendita, che la chiama

---

### 🎯 Scopo Principale

Restituisce il fattore che porta una quantità espressa in un'unità di misura all'unità base
di un articolo, a una data: quante unità base vale una unità richiesta quel giorno. Se non
trova un fattore restituisce NULL.

---

### I gradini

1. **La data.** Senza data non c'è fattore: la funzione restituisce NULL. La data non si
   sottintende; chi vuole il fattore di oggi passa il giorno aziendale.
2. **L'unità base.** La legge con `fn_get_uom_base`; se l'articolo non esiste, restituisce
   NULL.
3. **La base stessa.** Se l'unità richiesta è la base, il fattore è 1, a ogni data.
4. **La mappatura dell'articolo** alla data, letta da `fn_uom_operativa_alla_data`: la riga
   attiva di `articoli_uom_operativa` la cui validità contiene quel giorno.
5. **La conversione generale** fra le due unità, attiva e in vigore quel giorno. Ce n'è al più
   una per coppia di unità, in un verso o nell'altro: se è scritta dall'unità richiesta verso
   la base vale il suo fattore, se è scritta al contrario il suo reciproco.
6. **Niente**: NULL.

Le conversioni generali valgono solo fra unità della stessa tipologia: lo garantisce la
tabella stessa, e la funzione non lo ricontrolla.

---

### ⭐ Una sede per il fattore

La chiama il trigger della quantità delle righe di vendita, alla data del documento. Quando
la funzione risponde NULL il trigger rifiuta la riga: una quantità base inventata è peggio di
nessuna.

---

### ⚠️ Che cosa oggi non copre

* Un NULL non dice perché manca il fattore (articolo inesistente, data mancante o nessuna
  conversione). Il trigger della quantità lo spiega da sé nell'errore.
* Fuori dal database la chiamano due metodi del repository del backend, scritti per la firma
  senza data e senza chiamanti: con la firma nuova non funzionano più, e vanno ritirati.

---

### Test

* `db/pgtap/catalogo/test-fn-get-uom.sql` — i rami uno per uno, su un mondo costruito dal
  test: fattore 1 sulla base, fattore dalla mappatura, conversione diretta, conversione
  inversa, NULL senza conversioni; con la mappatura spenta, la funzione ricade sulla
  conversione generale.
* `db/pgtap/catalogo/test-uom-fattore-e-regole-v1.sql` — la mappatura versionata letta a due
  date, la conversione nei due versi, il NULL senza conversione.

---

### Note di migrazione

* 2025-11-03 — nasce, con la sola mappatura dell'articolo.
* 2026-01-13 — aggiunge il ripiego sulle conversioni globali, diretta e inversa.
* 2026-10-09 — «oggi» diventa la data nel fuso dell'azienda invece della data della sessione.
* 2026-11-09 — prende la data in coda alla firma e la chiama il trigger della quantità; la
  conversione generale è una per coppia (brief-db-revisione-catalogo, giro 2).

---

{% include-markdown "signature-core.md" %}
