## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_titoli_iva_non_ammessi_conta`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — i titoli che conta, di tutti gli emittenti
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_titoli_iva_non_ammessi](/dbzero/anagrafiche/funzioni/fn_titoli_iva_non_ammessi) — il predicato che conta
> * [anagrafiche.fn_check_cambio_natura_soggetto](/dbzero/anagrafiche/funzioni/fn_check_cambio_natura_soggetto) — chi la legge

---

### 🎯 Scopo Principale

`anagrafiche.fn_titoli_iva_non_ammessi_conta` conta, fra tutti gli emittenti, i titoli IVA in vigore di un soggetto
che una natura di dettaglio non ammette. Risponde solo il numero, e gira sopra la RLS dei titoli.

---

### Un numero, non un elenco

Gira coi privilegi del proprietario e conta le righe di `anagrafiche.fn_titoli_iva_non_ammessi`, che così vede
anche i titoli presentati agli emittenti fuori dal perimetro di chi agisce. Non restituisce identificativi né
dati dei titoli: il cambio di natura confronta questo numero con quanti titoli vede chi agisce, e la differenza
diventa il rifiuto `E_CAMBIO_NATURA_TITOLI_ALTRI_EMITTENTI`, che dice quanti sono e non quali.

Con la natura assente conta ogni titolo in vigore: il cambio di natura la usa così quando la natura si toglie, e
un solo titolo, visibile o no, basta a fermarlo.

---

{% include-markdown "it/dbzero/anagrafiche/_titolo-iva-per-natura.md" %}

---

{% include-markdown "signature-core.md" %}
