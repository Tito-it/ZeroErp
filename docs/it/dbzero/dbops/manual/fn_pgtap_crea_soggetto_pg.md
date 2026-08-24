## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_soggetto_pg()`

> 👀 **Vedi anche**
>
> • [script.fn_pgtap_set_contesto_operatore](/dbzero/script/funzioni/fn_pgtap_set_contesto_operatore)
> • [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Crea un **soggetto persona giuridica** completo e ne restituisce l'`uuid`.

Nasconde al test la parte noiosa: tipo soggetto, stato, partita IVA valida e libera, e i
campi che i guard di `anagrafiche.soggetti` pretendono. I parametri hanno default sensati —
al test basta passare la ragione sociale.

⚠️ Crea il **soggetto**, non i suoi ruoli: un soggetto senza ruolo non è ancora né cliente né
fornitore. Per quello serve `fn_pgtap_crea_soggetto_ruolo`, in un'istruzione **separata**.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
