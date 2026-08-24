## 📘 Documentazione Concettuale – Tabella `storico.comune_trasformazioni`

> 📄 **La tabella di origine `config.comune_trasformazioni` non esiste più** nel database.

{% include-markdown "it/dbzero/storico/_tabelle-storico.md" %}

---

### ⚠️ Storico orfano e vuoto

La tabella viva `config.comune_trasformazioni` è stata rimossa, e questo archivio è **vuoto** (0 righe al
2026-08-21): non ha mai raccolto nulla, o il suo contenuto è stato smaltito insieme alla fonte.

Resta in piedi perché lo schema `storico` non viene potato quando una tabella sparisce. Non è un
difetto attivo — è una struttura senza più né sorgente né contenuto, e come tale è candidata a
essere rimossa se un giorno si farà pulizia dello schema.

---

{% include-markdown "signature-core.md" %}
