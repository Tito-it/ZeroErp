## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_attivita_fatturabili_guard_fatturato`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — la tabella che protegge
>
> Approfondimento funzioni:
>
> * [vendite.fn_porta_reset_lotto_aperta](/dbzero/vendite/funzioni/fn_porta_reset_lotto_aperta) — la porta del reset del lotto: la GUC e il proprietario
> * [vendite.fn_cleanup_fatture_by_ids](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids) — la pulizia del lotto, l'unica che apre la porta
> * [vendite.trgfn_attivita_fatturabili_normalize](/dbzero/vendite/funzioni/trgfn_attivita_fatturabili_normalize)
> * [vendite.trgfn_attivita_fatturabili_guard_quantita_immutabile](/dbzero/vendite/funzioni/trgfn_attivita_fatturabili_guard_quantita_immutabile)

---

### 🎯 Scopo Principale

La funzione **`vendite.trgfn_attivita_fatturabili_guard_fatturato()`** blocca
modifiche o cancellazioni di righe di `vendite.attivita_fatturabili` che
risultano gia` agganciate a una riga di fattura.

La scrittura passa solo dentro la pulizia di un lotto, dalla porta del reset
(sezione qui sotto).

---

### Regola applicata

* Trigger **BEFORE UPDATE/DELETE** su `vendite.attivita_fatturabili`.
* Se `fattura_riga_id` e` valorizzato, l’operazione e` bloccata con
  `script.fn_log_and_raise_error('E_RIGA_GIA_FATTURATA')`.
* In caso di `DELETE`, la funzione ritorna **OLD** (evita errori su RETURN NEW).

---

### Ruolo nel processo

Questa guard tutela l’integrita` del processo di fatturazione:

* evita modifiche dopo l’aggancio a una riga di fattura;
* preserva la coerenza tra attivita` fatturabili e fatture.

---

### La porta del reset del lotto

Il guard lascia passare la scrittura quando la **porta del reset del lotto** è aperta. La legge
[`vendite.fn_porta_reset_lotto_aperta`](/dbzero/vendite/funzioni/fn_porta_reset_lotto_aperta), che
risponde sì solo se la GUC `zeroerp.maintenance_reset_lotto_draft` è accesa **e** chi scrive è il
proprietario della tabella.

La GUC la accende solo la pulizia del lotto,
[`vendite.fn_cleanup_fatture_by_ids`](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids), riservata
al proprietario, e la spegne prima di uscire: la porta è aperta solo mentre la pulizia lavora. ⛔ Per
l'applicazione la porta è sempre chiusa: accendere la GUC da sé e scrivere diretta non apre niente.

---

### Test

* `db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` — con la GUC accesa dall'applicazione
  la porta resta chiusa.

---

### Note di migrazione

* 2026-11-25 — la porta del reset si legge da `vendite.fn_porta_reset_lotto_aperta` e chiede anche
  il proprietario; prima bastava la GUC, che l'applicazione poteva accendere da sé
  (brief-db-porte-aperte-dalla-sola-guc, giro 1-7).

---

{% include-markdown "signature-core.md" %}
