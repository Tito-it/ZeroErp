## 📘 Documentazione Concettuale – Funzione `catalogo.fn_get_uom_base`

> **Ultimo aggiornamento**: 11 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — la colonna `uom_id` che la funzione legge
> * [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — l'unità restituita
>
> Approfondimento funzioni:
>
> * [catalogo.fn_get_uom_factor](/dbzero/catalogo/funzioni/fn_get_uom_factor) — la chiama come primo passo del fattore
> * [script.trgfn_qta_from_operativa](/dbzero/script/funzioni/trgfn_qta_from_operativa) — la chiama quando la riga non dice l'unità

---

### 🎯 Scopo Principale

Restituisce l'unità di misura base di un articolo, cioè il suo `articoli.uom_id`. Se
l'articolo non esiste restituisce NULL, e il chiamante decide se è un errore.

---

### NULL vuol dire «articolo che non c'è»

`articoli.uom_id` è obbligatorio, quindi un articolo che esiste ha sempre un'unità base: la
funzione restituisce NULL solo quando l'id non corrisponde a nessun articolo (o l'articolo
non è visibile a chi la chiama).

L'unità base di un articolo non cambia dopo la creazione: `articoli.uom_id` è bloccato.

---

### Chi la usa

Nel database la chiamano `fn_get_uom_factor`, come primo passo, e il calcolo della quantità
sulle righe di vendita (`script.trgfn_qta_from_operativa`), quando la riga non dice l'unità.
Fuori dal database la chiama solo un metodo del repository del backend, che a sua volta non ha
chiamanti.

---

### Test

* `db/pgtap/catalogo/test-fn-get-uom.sql` — restituisce l'unità base di due articoli
  costruiti dal test.

---

### Note di migrazione

* 2025-11-03 — nasce insieme a `fn_get_uom_factor`.
* 2026-11-09 — la chiama anche il calcolo della quantità sulle righe di vendita
  (brief-db-revisione-catalogo, giro 2).
* 2026-11-11 — la firma è ancorata con `%TYPE`; via il `LIMIT 1` su chiave primaria e la
  frase sull'articolo «senza UoM» (brief-db-revisione-catalogo, giro 5).

---

{% include-markdown "signature-core.md" %}
