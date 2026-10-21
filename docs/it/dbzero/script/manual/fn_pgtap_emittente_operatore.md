## 📘 Documentazione Concettuale – Funzione `script.fn_pgtap_emittente_operatore()`

> 👀 **Vedi anche**
>
> • [script.fn_pgtap_set_contesto_operatore](/dbzero/script/funzioni/fn_pgtap_set_contesto_operatore)
> • [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Restituisce l'**emittente fiscale su cui l'operatore di test opera**.

⭐ Serve a una regola precisa del template pgTAP: **l'emittente non si pesca, si deriva**. Un
documento appartiene all'emittente di chi agisce, e le policy `ef_whitelist` lo pretendono.

⭐ **Con un contesto aperto risponde la regola di produzione** (rev 2026-10-21):
`script.fn_resolve_emittente_for_user` — l'azienda scelta in alto (`app.current_emittente_id`)
se l'utente la può usare, altrimenti quella assegnata. È la stessa risposta del trigger che lega
il cliente all'azienda di chi agisce: per un super admin che ha scelto l'azienda le due non
divergono più. Senza contesto, o senza un'azienda risolta, ripiega su quella di un operatore
reale scelto con un ordinamento stabile.

⚠️ Scriverlo con `SELECT id FROM emittenti_fiscali ORDER BY id LIMIT 1` funziona **finché c'è
un solo emittente con documenti** — e smette di funzionare senza preavviso quando ne nasce un
secondo. È successo davvero: tre fixture pescavano invece di derivare, e il difetto era
invisibile perché i due valori coincidevano per caso.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
