## 📘 Documentazione Concettuale – Funzione `catalogo.fn_get_uom_factor`

> **Ultimo aggiornamento**: 10 novembre 2026
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
> * [catalogo.fn_uom_fonti_conversione](/dbzero/catalogo/funzioni/fn_uom_fonti_conversione) — le fonti della conversione, col loro periodo
> * [script.fn_fattore_uom_alla_data](/dbzero/script/funzioni/fn_fattore_uom_alla_data) — il fattore alla data o il rifiuto, che la chiama

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
4. **La prima fonte in vigore quel giorno** fra quelle di `fn_uom_fonti_conversione`: prima la
   mappatura dell'articolo (la riga attiva di `articoli_uom_operativa` la cui validità contiene
   quel giorno), poi la conversione generale fra le due unità, attiva e in vigore. Di conversioni
   ce n'è al più una per coppia di unità, in un verso o nell'altro: se è scritta dall'unità
   richiesta verso la base vale il suo fattore, se è scritta al contrario il suo reciproco.
5. **Niente**: NULL.

Le conversioni generali valgono solo fra unità della stessa tipologia: lo garantisce la
tabella stessa, e la funzione non lo ricontrolla.

---

### ⭐ Una sede per il fattore

La chiama `script.fn_fattore_uom_alla_data`, per le righe di vendita (alla data del documento) e
per le attività di commessa (alla data dell'attività). Quando la funzione risponde NULL la riga si
rifiuta: una quantità base inventata è peggio di nessuna. Da dove si converte lo dicono le fonti
(`fn_uom_fonti_conversione`), che leggono anche la regola dei listini sui periodi.

---

### ⚠️ Che cosa oggi non copre

* Un NULL non dice perché manca il fattore (articolo inesistente, data mancante o nessuna
  conversione). Lo spiega nell'errore `fn_fattore_uom_alla_data`.

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
* 2026-11-10 — legge le fonti di `fn_uom_fonti_conversione` (brief-db-revisione-catalogo,
  giro 2-bis).

---

{% include-markdown "signature-core.md" %}
