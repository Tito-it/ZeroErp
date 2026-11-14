## 📘 Documentazione Concettuale – Funzione `script.fn_check_ordine_evadibile()`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini) — da dove legge lo stato di emissione
>
Approfondimento funzioni:
> • [vendite.fn_genera_ddt_da_ordine](/dbzero/vendite/funzioni/fn_genera_ddt_da_ordine) — la bolla dall'ordine, che solleva il primo motivo
> • [script.fn_available_actions_ordine](/dbzero/script/funzioni/fn_available_actions_ordine) — la capability, che ne fa `can_genera_ddt`
> • [script.fn_raise_primo_motivo_se_presente](/dbzero/script/funzioni/fn_raise_primo_motivo_se_presente) — come si solleva il primo motivo

---

### 🎯 Scopo Principale

**Da quest'ordine si genera una bolla di evasione? E se no, perché?**

L'ordine si evade da due stati:

* lo **stato di emissione**, cioè quello che il vocabolario marca con la colonna `emissione` di
  `config.stati_doc_ordini` (oggi `CONFERMATO`);
* **`PARZIALMENTE_EVASO`**, la destinazione del processo di evasione. Questo stato non ha una
  colonna e si nomina col codice, come lo nomina la matrice.

La regola sta solo qui. La leggono in due: la bolla dall'ordine, che rifiuta, e la capability,
che accende o spegne «Genera bolla» col motivo. Così il pulsante e il rifiuto non possono dire
cose diverse, e il frontend non deve tenere una sua lista di stati.

| Risposta | Quando |
| --- | --- |
| `[]` | l'ordine si evade; e anche quando l'ordine non c'è (decide il chiamante) |
| un motivo | l'ordine è in uno stato da cui non si evade |

Il motivo ha la forma delle altre check:

| Campo | Valore |
| --- | --- |
| `codice` | `E_DDT_ORDINE_STATO_NON_EVADIBILE`, quello che la bolla solleva |
| `reason` | `ORDINE_NON_EVADIBILE` |
| `reason_key` | `vendite.ordini.genera_ddt_reason.stato_non_evadibile` |
| `dettaglio` | `{stato}`: il codice dello stato, che l'helper mette nel contesto dell'errore |
| `valori` | il numero dell'ordine e il codice dello stato, i due `%s` della frase |

Parametro non valido (`NULL` o `<= 0`): `E_PARAMETRO_INVALIDO`.

### Test

* `db/pgtap/vendite/test-ordine-stati-dal-vocabolario-v1.sql`: la bolla e `can_genera_ddt`
  rispondono uguale col seed, e seguono la marca `emissione` spostata.
