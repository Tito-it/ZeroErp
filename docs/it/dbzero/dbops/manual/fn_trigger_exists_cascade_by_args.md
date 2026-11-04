## 📘 Documentazione Concettuale – Funzione `dbops.fn_trigger_exists_cascade_by_args`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_trigger_exists_block_by_args](/dbzero/dbops/funzioni/fn_trigger_exists_block_by_args) — la gemella viva, per il block della regola ATTIVO
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — il motore ATTIVO di oggi, che non la chiama
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.2: la regola ATTIVO non ha cascata

---

### 🎯 Scopo Principale

Residuo della vecchia regola ATTIVO con cascata: diceva se sulla tabella padre c'era un trigger di
spegnimento a cascata (`dbops.trgfn_soft_delete_cascade`) con gli argomenti dati. ⛔ Oggi non ha
chiamanti e cerca una funzione che non esiste più: è candidata al ritiro.

---

### Perché non serve più

La regola ATTIVO di oggi non spegne i figli da sé: blocca il padre finché ha figli attivi, e
nient'altro. `dbops.trgfn_soft_delete_cascade` è stata ritirata insieme alle funzioni trigger
legacy, e il motore `dbops.fn_run_automations_attivo` non chiama più questo controllo.

Su un database di oggi restituisce sempre falso: non può esserci un trigger di una funzione che
non c'è. Anche se ci fosse, il confronto sul testo della definizione cerca gli argomenti separati
da una virgola senza spazio, mentre PostgreSQL li scrive con virgola e spazio.

---

### Note di migrazione

* 2026-01-01 — `dbops.trgfn_soft_delete_cascade` viene ritirata con gli oggetti ATTIVO legacy;
  questa funzione resta, senza più chiamanti.

---

{% include-markdown "signature-core.md" %}
