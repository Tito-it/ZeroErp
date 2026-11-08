## 📘 Documentazione Concettuale – Funzione `catalogo.fn_get_uom_factor`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa) — il fattore dell'articolo, la prima fonte
> * [catalogo.unita_misura_conversioni](/dbzero/catalogo/tabelle/unita_misura_conversioni) — le conversioni globali, il ripiego
>
> Approfondimento funzioni:
>
> * [catalogo.fn_get_uom_base](/dbzero/catalogo/funzioni/fn_get_uom_base) — l'unità base dell'articolo, il primo passo
> * [script.trgfn_qta_from_operativa](/dbzero/script/funzioni/trgfn_qta_from_operativa) — il calcolo reale della quantità sulle righe di vendita, che non chiama questa funzione
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — la data a cui si cercano mappature e conversioni in vigore

---

### 🎯 Scopo Principale

Restituisce il fattore che porta una quantità espressa in un'unità di misura all'unità base
di un articolo: quante unità base vale una unità richiesta. Se non trova un fattore
restituisce NULL.

---

### I gradini

1. **L'unità base.** La legge con `fn_get_uom_base`; se l'articolo non esiste, restituisce
   NULL.
2. **La base stessa.** Se l'unità richiesta è la base, il fattore è 1, senza guardare la
   mappatura.
3. **La mappatura dell'articolo.** La riga di `articoli_uom_operativa` attiva per l'articolo e
   l'unità, in vigore oggi.
4. **La conversione globale diretta**, dall'unità richiesta alla base, attiva e in vigore.
5. **La conversione globale inversa**, dalla base all'unità richiesta: il fattore è il suo
   reciproco.
6. **Niente**: NULL.

«In vigore oggi» vuol dire alla data operativa dell'azienda (`script.fn_data_operativa`),
non alla data di un documento: la funzione non prende una data.

Le conversioni globali sono già limitate a unità della stessa famiglia dalla tabella stessa:
la funzione non lo ricontrolla.

---

### ⚠️ Che cosa oggi non copre

* **Nessuna funzione del database la chiama.** Il calcolo della quantità sulle righe di
  vendita lo fa `script.trgfn_qta_from_operativa`, che ripete solo il gradino della mappatura
  e, se non la trova, usa il fattore 1 senza errore. Le due regole sono già in disaccordo: qui
  un'unità senza mappatura trova la conversione globale o restituisce NULL, là vale 1.
  Fuori dal database la chiama solo un metodo del repository del backend, che a sua volta
  non ha chiamanti.
* **Fra due conversioni che si contraddicono sceglie la diretta in silenzio.** Per la stessa
  coppia possono essere attive insieme A → B e B → A con fattori incoerenti: vince la diretta.
* Un NULL non dice perché manca il fattore (articolo inesistente o nessuna conversione).

---

### Test

* `db/pgtap/catalogo/test-fn-get-uom.sql` — i rami uno per uno, su un mondo costruito dal
  test: fattore 1 sulla base, fattore dalla mappatura, conversione diretta, conversione
  inversa, NULL senza conversioni; con la mappatura spenta, la funzione ricade sulla
  conversione globale.

---

### Note di migrazione

* 2025-11-03 — nasce, con la sola mappatura dell'articolo.
* 2026-01-13 — aggiunge il ripiego sulle conversioni globali, diretta e inversa.
* 2026-10-09 — «oggi» diventa la data nel fuso dell'azienda invece della data della sessione.

---

{% include-markdown "signature-core.md" %}
