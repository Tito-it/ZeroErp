## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_titolo_iva_vigente`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — i titoli di cui dice se sono in vigore
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_soggetti_titoli_iva_guard_tipo_soggetto](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_guard_tipo_soggetto) — il guard sul titolo, che la chiama
> * [anagrafiche.fn_titoli_iva_non_ammessi](/dbzero/anagrafiche/funzioni/fn_titoli_iva_non_ammessi) — il lettore del cambio di natura
> * [anagrafiche.fn_titolo_iva_vigente_su_natura_esiste](/dbzero/anagrafiche/funzioni/fn_titolo_iva_vigente_su_natura_esiste) — il lettore del ritiro di matrice
> * [script.fn_giorno_operativo](/dbzero/script/funzioni/fn_giorno_operativo) — il «oggi» che le passano

---

### 🎯 Scopo Principale

`anagrafiche.fn_titolo_iva_vigente` dice se un titolo IVA è in vigore: attivo, e con la data di fine assente o
non ancora passata. È la sede unica della definizione, letta da tutti i controlli della natura ammessa.

---

### Lavora sui valori, non sulla riga

Riceve `attivo`, `valido_al` e il giorno di riferimento, e non legge nessuna tabella. Il giorno lo passa chi chiama:
tutti i chiamanti di oggi passano il giorno operativo (`script.fn_giorno_operativo` sull'istante della
transazione). Così la risposta non dipende dal fuso della sessione, e la funzione è dichiarata immutabile.

Una data di fine assente vuol dire «senza scadenza», non «nessuna risposta»: la funzione non è `STRICT`, e un
`attivo` assente vale spento.

---

{% include-markdown "it/dbzero/anagrafiche/_titolo-iva-per-natura.md" %}

---

{% include-markdown "signature-core.md" %}
