## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_titoli_iva_non_ammessi`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — i titoli che legge
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_cambio_natura_soggetto](/dbzero/anagrafiche/funzioni/fn_check_cambio_natura_soggetto) — chi la legge
> * [anagrafiche.fn_titoli_iva_non_ammessi_conta](/dbzero/anagrafiche/funzioni/fn_titoli_iva_non_ammessi_conta) — la stessa domanda, contata sopra la RLS

---

### 🎯 Scopo Principale

`anagrafiche.fn_titoli_iva_non_ammessi` elenca i titoli IVA in vigore di un soggetto che una natura di dettaglio
non ammette. È la sede del predicato del cambio di natura: «se il soggetto diventasse questa natura, quali titoli
resterebbero in vigore senza essere ammessi».

---

### Vede quello che vede chi chiama

Gira coi permessi di chi la chiama, sotto la RLS dei titoli: un operatore ottiene i titoli presentati agli
emittenti del suo perimetro. Per ogni titolo dà il tipo e il suo ordine; l'ordine è stabile (ordine del tipo, poi
gli identificativi), perché il rifiuto del cambio di natura nomina il tipo del primo.

Con la natura assente ogni titolo in vigore è non ammesso: è la domanda che serve quando la natura si toglie.

`anagrafiche.fn_titoli_iva_non_ammessi_conta` la chiama coi privilegi del proprietario, e allora la stessa
funzione vede tutti i titoli: il predicato resta scritto una volta sola.

---

{% include-markdown "it/dbzero/anagrafiche/_titolo-iva-per-natura.md" %}

---

{% include-markdown "signature-core.md" %}
