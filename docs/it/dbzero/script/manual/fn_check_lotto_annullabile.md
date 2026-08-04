## 📘 Documentazione Concettuale – Funzione `script.fn_check_lotto_annullabile`
### 🎯 Scopo Principale
(latest review 04-08-2026)
Elenca i **motivi che impediscono l'annullamento** di un lotto di fatturazione. Funzione
**pura** (`fn_check_*`): non solleva errori di dominio e non scrive. Ritorna `[]` quando
l'annullamento è lecito.

È la **sede unica** della regola, con due consumatori:

1. `vendite.fn_annulla_lotto_da_draft` — solleva il codice del **primo** motivo;
2. `script.fn_available_actions_lotto` — espone l'azione `annulla` con
   `enabled = false` e i `reasons` a tooltip.

---

### Perché esiste

Il 2026-07-31 il pulsante «Annulla lotto» risultava visibile da EMESSA in poi, dove la
funzione rifiuta: un vicolo cieco trovato in-app. Fu tappato aggiungendo un `v-if` in Vue —
cioè ricopiando in JavaScript una precondizione che vive in PL/pgSQL. Questa funzione
chiude quel modo di lavorare: la precondizione è una, e la UI la legge.

---

### I motivi, nell'ordine

| # | `reason` | Codice | Quando |
| --- | --- | --- | --- |
| 1 | `STATO_NON_DRAFT` | `E_LOTTO_NON_ANNULLABILE` (798) | Il lotto non è in bozza |
| 2 | `FATTURE_NON_PRE_FISCALI` | `E_LOTTO_FATTURE_NON_PRE_FISCALI` (799) | Almeno una fattura oltre il pre-fiscale |

Il motivo 1 esiste perché `ANNULLATA` **chiude** il lotto e non si riapre: l'annullamento
si concede solo finché il lotto non ha prodotto nulla oltre la bozza. Da EMESSA la via
d'uscita è un'altra, e non è distruttiva del lotto: `fn_riporta_lotto_a_draft`.

Il motivo 2 è **delegato** a `script.fn_check_lotto_fatture_pre_fiscali`, che è la sede
unica della definizione di «pre-fiscale».

**Non** è un motivo il tipo di lotto: dal 2026-08-02 (D-L pt.2 + D-T) l'annullamento vale
per `MASSIVO` **e** `GIORNALIERO`.

---

### Errori sollevati (non di dominio)

* `E_PARAMETRO_INVALIDO` — `lotto_id` assente o `<= 0`: è un errore di programmazione.
* `E_LOTTO_NON_TROVATO` — il lotto non esiste.

---

### Output (jsonb)

Array (eventualmente vuoto) di `{ codice, reason, reason_key, dettaglio }`.

---

{% include-markdown "signature-core.md" %}
