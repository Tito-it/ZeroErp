## 📘 Documentazione Concettuale – Funzione `script.fn_check_ddt_rendibile()`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.ddt](/dbzero/vendite/tabelle/ddt) — la bolla da cui il reso nasce
> • [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt) — gli stati della bolla
>
Approfondimento funzioni:
> • [vendite.trgfn_resi_guard_ddt_consegnato](/dbzero/vendite/funzioni/trgfn_resi_guard_ddt_consegnato) — il trigger del reso, che solleva il primo motivo
> • [script.fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt) — la capability della bolla, che ne fa `can_genera_reso`
> • [vendite.fn_ddt_causale_magazzino](/dbzero/vendite/funzioni/fn_ddt_causale_magazzino) — riconosce la bolla di trasferimento
> • [script.fn_raise_primo_motivo_se_presente](/dbzero/script/funzioni/fn_raise_primo_motivo_se_presente) — come si solleva il primo motivo

---

### 🎯 Scopo Principale

**Da questa bolla nasce un reso? E se no, perché?**

Un reso nasce da una bolla consegnata, e mai da un trasferimento fra depositi. La regola sta solo
qui. La leggono in due: il trigger del reso, che rifiuta, e la capability della bolla, che accende
o spegne «Genera reso» col motivo. Così il pulsante e il rifiuto non possono dire cose diverse, e
il frontend non deve confrontare lo stato della bolla.

| Risposta | Quando |
| --- | --- |
| `[]` | dalla bolla nasce un reso |
| un motivo | la bolla è un trasferimento, non è consegnata, o non c'è |

I motivi, nell'ordine (si esce al primo):

| `codice` | `reason` | `reason_key` | `valori` |
| --- | --- | --- | --- |
| `E_RESO_DA_DDT_TRASFERIMENTO` | `DDT_TRASFERIMENTO` | `vendite.ddt.genera_reso_reason.trasferimento` | il numero della bolla (il `%s` della frase) |
| `E_RESO_DDT_NON_CONSEGNATO` | `DDT_NON_CONSEGNATO` | `vendite.ddt.genera_reso_reason.non_consegnato` | nessuno: la frase non ha segnaposti, e i valori di un motivo sono esattamente i suoi |

* **Il trasferimento viene prima.** Una bolla di trasferimento fra depositi porta merce che è
  rimasta nostra, entrata nel magazzino di arrivo alla consegna: un reso la farebbe rientrare una
  seconda volta, con un accredito verso chi non l'ha comprata. È la risposta vera anche su una
  bolla consegnata. Si riconosce dalla causale di magazzino `TRASF_OUT` della sua causale di
  trasporto.
* **Si rende ciò che è stato consegnato.** `CONSEGNATO` è la destinazione del processo di
  consegna, e si nomina col codice, come lo nomina la matrice.
* **La bolla che non c'è** dà `E_RESO_DDT_NON_CONSEGNATO` con lo stato `NULL`: il trigger del reso
  scatta prima del guard della sorgente, e la risposta resta quella che dava prima della check.

Il `dettaglio` porta `{ddt_id}` o `{ddt_id, stato_ddt}`, che l'helper mette nel contesto
dell'errore. Parametro non valido (`NULL` o `<= 0`): `E_PARAMETRO_INVALIDO`.

### Test

* `db/pgtap/vendite/test-reso-stati-dal-vocabolario-v1.sql`: `can_genera_reso` e il trigger del
  reso rispondono uguale sulla bolla consegnata e su quella emessa; il trigger non riscrive la
  regola.
