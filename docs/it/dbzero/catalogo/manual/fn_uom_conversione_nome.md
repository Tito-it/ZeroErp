## 📘 Documentazione Concettuale – Funzione `catalogo.fn_uom_conversione_nome`

> **Ultimo aggiornamento**: 10 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_uom_guard_storia](/dbzero/catalogo/funzioni/trgfn_uom_guard_storia) — il guard della storia, che la legge
> * [catalogo.trgfn_uom_guard_listini_attivi](/dbzero/catalogo/funzioni/trgfn_uom_guard_listini_attivi) — il guard dei listini attivi, che la legge

---

### 🎯 Scopo Principale

Dà il nome di una conversione nei valori dei messaggi d'errore, nella forma delle unità: «CRT → PZ
(ART-1)» per la mappatura di un articolo, «KG → G» per una conversione generale.

---

### Perché qui

Due guard nominano la stessa cosa allo stesso modo. La forma è quella delle unità, non una frase:
la lingua sta nel messaggio. Se l'articolo o un'unità non c'è più risponde vuoto, e i guard lo
leggono come «la riga se ne va con lui».

---

### Test

* `db/pgtap/catalogo/test-uom-storia-v1.sql`
* `db/pgtap/vendite/test-listino-uom-periodo-v1.sql`

---

### Note di migrazione

* 2026-11-10 — nasce (brief-db-revisione-catalogo, giro 2-bis).

---

{% include-markdown "signature-core.md" %}
