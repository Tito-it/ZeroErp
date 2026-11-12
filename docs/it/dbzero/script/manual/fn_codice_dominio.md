## 📘 Documentazione Concettuale – Funzione `script.fn_codice_dominio`

> **Ultimo aggiornamento**: 12 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — chi scrive il codice nel canale `CONSTRAINT`
> * [vendite.fn_batch_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_batch_upsert_commessa_attivita) — la legge per ogni errore raccolto
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — la legge per il codice della corsa fallita
>
> Guide:
>
> * [Messaggi di Errore e Generazione Log](/guide/Messaggi-di-Errore-e-Generazione-Log) — i canali dell'eccezione

---

### 🎯 Scopo Principale

Dice se un errore **catturato** è un errore di dominio, e qual è il suo codice. Riceve lo
SQLSTATE e il canale `CONSTRAINT` della diagnostica (`GET STACKED DIAGNOSTICS … RETURNED_SQLSTATE,
CONSTRAINT_NAME`) e risponde:

* il **codice** (`E_…`), quando lo SQLSTATE è `P0001` e il canale non è vuoto: è il contratto con
  cui `script.fn_log_and_raise_error` solleva;
* **`NULL`** in ogni altro caso.

⚠️ Il canale da solo non basta: per una violazione di unicità (`23505`) o di un `CHECK` (`23514`)
porta il **nome del vincolo**, che non è un codice del catalogo dei messaggi.

---

### Chi la chiama

Le funzioni che catturano un errore **senza rilanciarlo al backend**, e devono comunque dirgli
quale codice è stato: il backend legge il codice dal driver solo quando l'eccezione gli arriva.

| Lettore | Che cosa ne fa |
| --- | --- |
| `vendite.fn_batch_upsert_commessa_attivita` | mette `codice` (e `campo`) nell'errore della riga, solo quando c'è |
| `maintenance.fn_run_and_log` | scrive `error_code` della corsa, e senza codice ci mette lo SQLSTATE |

Il ripiego quando il codice non c'è **non** è della funzione: ogni lettore decide il suo. I wrapper
di lotto (`vendite.fn_snapshot_fattura_lotto`, `vendite.fn_genera_scadenze_lotto`) catturano solo
`raise_exception`, e per loro la regola vale per costruzione.

---

### Test

* `db/pgtap/script/test-fn-codice-dominio-v1.sql` — la regola sui valori, sulla diagnostica vera di
  un errore di dominio e di un `CHECK`, e i due lettori che la chiamano senza una copia del
  confronto.

---

### Note di migrazione

* 2026-11-12 — nasce, alla seconda lettura della regola (brief-db-revisione-catalogo, giro 5-bis).

---

{% include-markdown "signature-core.md" %}
