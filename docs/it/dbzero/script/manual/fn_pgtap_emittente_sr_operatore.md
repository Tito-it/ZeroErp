## 📘 Documentazione Concettuale – Funzione `script.fn_pgtap_emittente_sr_operatore()`

> 👀 **Vedi anche**
>
> • [script.fn_pgtap_set_contesto_operatore](/dbzero/script/funzioni/fn_pgtap_set_contesto_operatore)
> • [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Restituisce il **`soggetto_ruolo_id`** dell'emittente dell'operatore, non la sua chiave
primaria.

⭐ Le due cose non sono intercambiabili, ed è la ragione per cui esistono due funzioni: alcune
tabelle referenziano l'emittente per `id` (`emittente_fiscale_id`), altre per ruolo
(`emittente_soggetto_ruolo_id`), e le policy di scope leggono l'uno o l'altro a seconda del
dominio.

⚠️ `vendite.commesse` è il caso da ricordare: la policy `rls_commesse_ef_whitelist` respinge
un `soggetto_ruolo_id` nullo, fail-closed. Ometterlo in una fixture non dà «riga senza
emittente», dà **nessuna riga**.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
