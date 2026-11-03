## 📘 Documentazione Concettuale – Funzione `dbops.fn_list_indices`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy) — la policy degli indici sulle chiavi esterne
>
> Approfondimento viste:
>
> * [dbops.vw_duplicate_indexes](/dbzero/dbops/views/vw_duplicate_indexes) — gli indici duplicati esatti
> * [dbops.vw_indici_ridondanti_prefisso](/dbzero/dbops/views/vw_indici_ridondanti_prefisso) — gli indici ridondanti per prefisso

---

### 🎯 Scopo Principale

Elenca gli indici di uno schema, o di una sola tabella, con nome, unicità, chiave primaria e
definizione completa. È un attrezzo di ispezione da lanciare a mano: evita di riscrivere ogni volta
la congiunzione sui cataloghi degli indici. Nessun oggetto del database la chiama.

---

### ⚠️ Non è un presidio

Non confronta con nessuna regola e non segnala niente: elenca. Le domande con una risposta giusta
hanno le loro viste — i duplicati esatti, la ridondanza per prefisso, le chiavi esterne senza
indice — e la policy delle chiavi esterne decide quali indici devono esistere.

L'elenco comprende ogni indice dello schema, anche quelli che non stanno su tabelle (per esempio
sulle viste materializzate), ordinati per tabella e nome.

---

{% include-markdown "signature-core.md" %}
