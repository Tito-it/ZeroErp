## 📘 Documentazione Concettuale – Funzione `dbops.fn_idempotency_soglia_secondi`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.parameters](/dbzero/config/tabelle/parameters) — dove sta `SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI`
> * [dbops.idempotency_keys](/dbzero/dbops/tabelle/idempotency_keys) — le key a cui la soglia si applica
>
> Approfondimento funzioni:
>
> * [dbops.fn_idempotency_prenota](/dbzero/dbops/funzioni/fn_idempotency_prenota) — la usa per decidere la ripresa di una key in corso
> * [script.fn_intero_positivo_da_testo](/dbzero/script/funzioni/fn_intero_positivo_da_testo) — valida il valore letto
>
> Guide:
>
> * [Le operazioni che non si ripetono](/guide/operazioni-che-non-si-ripetono) — quando una chiave si riprende

---

### 🎯 Scopo Principale

La soglia, in secondi, oltre cui una Idempotency-Key rimasta `in_progress` conta come abbandonata
e si può riprendere: il valore di `SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI`, validato come intero
positivo.

---

### ⭐ Una sede sola per la lettura

La soglia la usano in due: `dbops.fn_idempotency_prenota`, quando decide se riprendere una key, e il
backend all'avvio, che rifiuta di partire se la soglia non supera il timeout del server web (una
key si riprenderebbe mentre la richiesta che la tiene è ancora viva). Entrambi la chiedono a questa
funzione: prima il backend ricopiava la regola di validazione, e una copia aveva già divergito.

---

### Il default nudo, e niente ripieghi

Si legge il valore di default del parametro, senza override per azienda o per utente: la soglia è
una proprietà del sistema. Il valore passa da `script.fn_intero_positivo_da_testo`: parametro
assente, vuoto o non intero positivo è `E_CONFIG_MANCANTE`, mai un numero di ripiego.

---

### Codici errore

* `E_CONFIG_MANCANTE` — `SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI` manca, è vuoto o non è un intero
  positivo.

---

### Test

* `db/pgtap/script/test-intero-positivo-da-testo-v1.sql` — la funzione esiste, `SECURITY INVOKER`,
  `STABLE`, e restituisce il default del seed; la regola delle forme ammesse sta nel solo building
  block, e la prenotazione lo usa.

---

### Note di migrazione

* 2026-10-24 — nasce, togliendo dal backend la copia della validazione
  (`brief-be-verifica-documentazione-api`).

---

{% include-markdown "signature-core.md" %}
