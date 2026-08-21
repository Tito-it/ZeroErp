## 📘 Documentazione Concettuale – Funzione `script.fn_pgtap_set_contesto_operatore()`

> 👀 **Vedi anche**
>
> • [script.fn_pgtap_set_contesto_operatore](/dbzero/script/funzioni/fn_pgtap_set_contesto_operatore)
> • [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Dà alla sessione di test **lo stesso contesto che il backend imposta** per un operatore:
ruolo applicativo, utente corrente, perimetro emittente.

🔴 **È la riga più importante del preambolo pgTAP**, e la sua assenza non produce un errore:
produce un test **verde per sottrazione**. Senza veste dichiarata le policy RLS sono
fail-closed, le `SELECT` della fixture leggono zero righe, e le asserzioni finiscono nei rami
`skip` — che non verificano niente.

⚠️ Un test che ha bisogno di una veste **diversa** (per esempio `CLIENTE_PORTALE`) chiama
comunque prima questa — la fixture deve *vedere* per costruire — e cambia veste solo dopo,
impostando `app.ruolo_applicativo` e `app.current_identita_id`.

⚠️ E svuotare `app.current_user_id` **non** è un modo per testare il fail-closed: il cancello
vero è `app.ruolo_applicativo`.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
