## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_piva_libera()`

> 👀 **Vedi anche**
>
> • [script.fn_pgtap_set_contesto_operatore](/dbzero/script/funzioni/fn_pgtap_set_contesto_operatore)
> • [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Restituisce una **partita IVA valida e non ancora usata**. Gemella di `fn_pgtap_cf_libero`,
con la stessa doppia garanzia: forma corretta — la P.IVA ha un carattere di controllo che i
guard verificano — e assenza di collisioni con i soggetti già presenti.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
