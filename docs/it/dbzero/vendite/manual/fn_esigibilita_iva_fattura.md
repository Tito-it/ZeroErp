## 📘 Documentazione Concettuale – Funzione `vendite.fn_esigibilita_iva_fattura()`

> 👀 **Vedi anche**
>
> [script.fn_esigibilita_iva](/dbzero/script/funzioni/fn_esigibilita_iva) (la regola)
> [script.fn_esigibilita_iva_documento](/dbzero/script/funzioni/fn_esigibilita_iva_documento)
> [vendite.trgfn_fatture_righe_guard_normalize](/dbzero/vendite/funzioni/trgfn_fatture_righe_guard_normalize)
> [vendite.fn_ricalcola_riepilogo_iva_fattura](/dbzero/vendite/funzioni/fn_ricalcola_riepilogo_iva_fattura)
> [vendite.fn_regime_fiscale_fattura](/dbzero/vendite/funzioni/fn_regime_fiscale_fattura) (il regime della fattura)

### 🎯 Scopo

(01-10-2026 — brief `brief-db-esigibilita-iva-per-cassa-emittente`, D-7, D-8)

**La coppia (`esigibilita`, `split_payment`) di una riga di fattura.** Prende dalla
testata l'emittente (`emittente_soggetto_ruolo_id` → `emittenti_fiscali`), il
cliente (`billing_account_id`) e il **regime congelato** nello snapshot
dell'intestazione (`emittente_snapshot ->> 'regime_fiscale_rf'`), e passa tutto a
[script.fn_esigibilita_iva_documento](/dbzero/script/funzioni/fn_esigibilita_iva_documento).

⭐ **Perché il regime dello snapshot (D-8).** La testata stampa il regime che lo
snapshot ha congelato. Se le righe leggessero quello vivo dell'emittente, un cambio
di regime con la fattura in bozza farebbe dire alla testata RF01 e alle righe `D`.
Da quando lo snapshot c'è, le righe seguono la testata; prima, il regime vivo.

⭐ **Il regime lo dà [vendite.fn_regime_fiscale_fattura](/dbzero/vendite/funzioni/fn_regime_fiscale_fattura)**
(dal 02-10-2026, `20261002-06`), la stessa funzione che leggono le annotazioni in
stampa ([vendite.fn_annotazioni_fattura](/dbzero/vendite/funzioni/fn_annotazioni_fattura)):
l'annotazione non può guardare un regime diverso da quello con cui le righe sono
state calcolate.

### Firma

| Parametro | Tipo | Significato |
|---|---|---|
| `p_fattura_id` | `vendite.fatture.id%TYPE` | la fattura |
| `p_iva_id` | `config.iva.id%TYPE` | il codice IVA della riga |
| **Ritorno** | `TABLE(esigibilita, split_payment)` | una riga |

`STABLE`, `SECURITY INVOKER`.

### Chi la chiama

* il trigger di riga `vendite.trgfn_fatture_righe_guard_normalize`, a ogni scrittura;
* `vendite.fn_ricalcola_riepilogo_iva_fattura`, che riallinea le righe prima di
  aggregarle.

### Test

`db/pgtap/vendite/test-esigibilita-iva-per-cassa-v1.sql` (casi 11-17).

---

{% include-markdown "signature-core.md" %}
