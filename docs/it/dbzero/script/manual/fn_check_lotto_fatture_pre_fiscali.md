## 📘 Documentazione Concettuale – Funzione `script.fn_check_lotto_fatture_pre_fiscali`
### 🎯 Scopo Principale
(latest review 04-08-2026)
Dice se le fatture di un lotto sono ancora **demolibili**, cioè se nessuna ha superato lo
stato pre-fiscale. Funzione **pura** (`fn_check_*`): non solleva errori di dominio e non
scrive. Ritorna `[]` quando tutte le fatture del lotto sono pre-fiscali.

È la **sede unica** della definizione di «pre-fiscale» per le fatture di un lotto. La
usano `script.fn_check_lotto_annullabile` e `script.fn_check_lotto_riportabile_a_draft`, e
per loro tramite le due funzioni di mutazione e le capability.

---

### Cos'è «pre-fiscale»

`DRAFT` o `EMESSA`. A `EMESSA` la fattura **non è ancora numerata** (C-19): il documento
non è fiscalmente nato e si può ancora disfare. Da `DEFINITIVA` in poi no.

---

### ⚠️ Perché `IS DISTINCT FROM` e non un `NOT IN` sui codici

La condizione confronta lo `stato_doc_fiscale_id` della fattura con i due id risolti, con
`IS DISTINCT FROM`. Così una fattura con `stato_doc_fiscale_id` **NULL** conta come **non**
pre-fiscale — fail-closed. Un `NOT IN` scritto via `JOIN` sui codici la perderebbe per
strada, e il verdetto risulterebbe «demolibile» proprio sulla riga di cui non si sa niente.

---

### Perché esiste come funzione a sé

La stessa `SELECT count(*)` era scritta due volte — in `fn_annulla_lotto_da_draft` e in
`fn_riporta_lotto_a_draft` — e stava per diventare tre con le capability. È il **fatto**
condiviso dai due verbi distruttivi del lotto: entrambi cancellano fatture, ed entrambi
possono farlo solo finché il documento non è fiscalmente nato.

---

### Errori sollevati (non di dominio)

* `E_PARAMETRO_INVALIDO` — `lotto_id` assente o `<= 0`.
* `E_CONFIG_MANCANTE` — stato `DRAFT` o `EMESSA` non configurato (installazione rotta,
  non condizione di dominio).

---

### Output (jsonb)

Array vuoto, oppure un solo elemento:
`{ codice: 'E_LOTTO_FATTURE_NON_PRE_FISCALI', reason: 'FATTURE_NON_PRE_FISCALI', reason_key, dettaglio: <conteggio> }`.

---

{% include-markdown "signature-core.md" %}
