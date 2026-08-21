## 📘 Documentazione Concettuale – Tabella `magazzino.magazzini`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)
> • [magazzino.ubicazioni](/dbzero/magazzino/tabelle/ubicazioni)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Anagrafica dei magazzini e depositi.**

⭐ L'indirizzo è legato ad `anagrafiche.indirizzi_dettaglio` e **non** passa da un ruolo
anagrafico: un magazzino è un *luogo*, non un soggetto. È la differenza rispetto a clienti,
fornitori e vettori, che hanno tutti un `soggetto_ruolo_id`.

⚠️ `indirizzo_dettaglio_id` è **`NOT NULL`**: un magazzino senza indirizzo non è inseribile.
Va saputo scrivendo le fixture — serve un indirizzo esistente prima del magazzino.

---

### Il codice viene normalizzato

`magazzino.trgfn_magazzini_normalize` porta `codice` in maiuscolo e ne toglie gli spazi ai
bordi, così `mag1`, `MAG1 ` e ` Mag1` diventano lo stesso codice.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
