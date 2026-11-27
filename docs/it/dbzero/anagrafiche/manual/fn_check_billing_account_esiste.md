## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_check_billing_account_esiste`

> **Ultimo aggiornamento**: 27 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — i billing account, sotto row level security
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_get_emittente_fiscale_id](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_id) e [anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk) — i chiamanti: rifiutano un id che non è un billing account
> * [script.fn_get_ba_emittente_sr_id](/dbzero/script/funzioni/fn_get_ba_emittente_sr_id) — il lettore dell'azienda di un billing account, che non solleva

---

### 🎯 Scopo Principale

`anagrafiche.fn_check_billing_account_esiste` dice se un id è un billing account: `true` o `false`, e `NULL` su
un id `NULL`. Non solleva: che cosa vuol dire «nessun billing account», e che cosa fare di un id che non lo è,
lo decide chi la chiama.

---

### ⭐ Guarda tutti i billing account

La funzione è `SECURITY DEFINER`: legge `anagrafiche.billing_account` come il proprietario, senza la row level
security di chi chiama. La domanda è se l'id esiste, non se chi chiama lo vede. I due risolutori dell'azienda di
un billing account la chiamano da guard di documento, normalizzatori, funzioni di insieme e job senza sessione:
letto da invocante, un billing account di un'altra azienda risulterebbe inesistente, e un id giusto sarebbe
rifiutato. Risponde solo il booleano: nessuna colonna del billing account esce.

---

### Chi la usa

* `anagrafiche.fn_get_emittente_fiscale_id` e `anagrafiche.fn_get_emittente_fiscale_pk`: su `false` sollevano
  `E_BILLING_ACCOUNT_NOT_FOUND`. Senza il controllo, i livelli di riserva del lettore (l'azienda di chi agisce,
  la predefinita) davano un'azienda a un id sbagliato.

---

### Test

* `db/pgtap/anagrafiche/test-fn-get-emittente-fiscale-pk.sql` (test 6, 7, 11) e
  `db/pgtap/anagrafiche/test-fn-get-emittente-fiscale-id-v1.sql` (test 4, 5, 7): l'id che non è un billing
  account, in sessione e senza, e il billing account fuori dal perimetro di chi chiama.

---

### Note di migrazione

* 2026-11-27 — nasce, per i due risolutori dell'azienda di un billing account.

---

{% include-markdown "signature-core.md" %}
