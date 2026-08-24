## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_cf_libero()`

> 👀 **Vedi anche**
>
> • [script.fn_pgtap_set_contesto_operatore](/dbzero/script/funzioni/fn_pgtap_set_contesto_operatore)
> • [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Restituisce un **codice fiscale valido e non ancora usato**, pronto per una fixture.

⭐ Le due proprietà servono entrambe e per ragioni diverse: *valido* perché i guard di dominio
verificano la forma del CF e rifiuterebbero una stringa inventata; *libero* perché su
`anagrafiche.soggetti` l'unicità del codice fiscale è imposta, e riusare quello di un soggetto
esistente farebbe fallire il test con un errore di unicità che non c'entra con ciò che
verifica.

⚠️ È il motivo per cui non si scrivono CF a mano nei test: due file che usassero la stessa
costante si romperebbero a vicenda, e solo quando girano insieme.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
