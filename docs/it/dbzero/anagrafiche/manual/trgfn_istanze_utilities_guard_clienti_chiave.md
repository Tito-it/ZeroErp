## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_istanze_utilities_guard_clienti_chiave`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — la tabella su cui è montata, e la sua colonna `fittizia`
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_clienti_chiave_unica_di](/dbzero/anagrafiche/funzioni/fn_guard_clienti_chiave_unica_di) — il controllo dei clienti dell'istanza, a cui delega

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_istanze_utilities_guard_clienti_chiave` è la strada dell'istanza: quando un'istanza
diventa fittizia, o smette di esserlo, controlla alla conferma dell'operazione i clienti di quell'istanza.

---

### Solo quando `fittizia` cambia, nei due versi

La regola vale soltanto per i clienti delle istanze fittizie, quindi l'unico dato dell'istanza che conta è
`fittizia`: il trigger scatta solo quando quella colonna cambia, in un verso o nell'altro, e non per le
altre modifiche dell'istanza.

* Un'istanza che **diventa** fittizia porta i suoi clienti dentro la regola: il controllo li confronta con
  gli altri clienti manuali della stessa chiave, ed è il caso che può rifiutare.
* Un'istanza che **smette** di essere fittizia porta i suoi clienti fuori dalla regola: il controllo li
  guarda lo stesso, e passano, perché non occupano più nessuna chiave.

---

### Note di migrazione

* 2026-10-14 — nasce con la regola del cliente manuale.

---

{% include-markdown "it/dbzero/anagrafiche/_chiave-unica-cliente.md" %}

---

{% include-markdown "signature-core.md" %}
