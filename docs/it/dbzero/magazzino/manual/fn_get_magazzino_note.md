## 📘 Documentazione Concettuale – Funzione `magazzino.fn_get_magazzino_note()`

> 👀 **Vedi anche**
>
> • [script.fn_get_note](/dbzero/script/funzioni/fn_get_note)
> • [magazzino.note](/dbzero/magazzino/tabelle/note)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Wrapper** su `script.fn_get_note` per la tabella `magazzino.note`: estrae le note di un
documento di magazzino con la stessa firma usata dagli altri domini.

Non contiene logica propria — filtri, ancoraggio e ordinamento vivono nella funzione generica.
Esiste per non far passare a ogni chiamante il `regclass` della partizione giusta.

⭐ È il gemello esatto di `acquisti.fn_get_acquisti_note` e degli altri wrapper per dominio: la
stessa funzione parametrizzata sulla tabella. Chi ne aggiunge uno per un dominio nuovo copia
questa forma.

---

### I parametri che contano

`_include_doc` e `_include_righe` decidono se raccogliere le note di testata, quelle di riga o
entrambe; `_only_visible` filtra quelle non visibili. I default (`true`, `true`, `true`) danno
il comportamento di stampa: tutto ciò che l'utente deve vedere.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
