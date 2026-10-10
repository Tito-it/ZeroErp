## 📘 Documentazione Concettuale – Funzione `script.fn_regime_fiscale_documento()`

> 👀 **Vedi anche**
>
> [script.fn_esigibilita_iva_documento](/dbzero/script/funzioni/fn_esigibilita_iva_documento)
> [vendite.fn_regime_fiscale_fattura](/dbzero/vendite/funzioni/fn_regime_fiscale_fattura)
> [config.regimi_fiscali](/dbzero/config/tabelle/regimi_fiscali)

### 🎯 Scopo

(02-10-2026 — brief `brief-db-esigibilita-iva-per-cassa-emittente`, R-DB-3, D-8)

**Quale regime fiscale vale per un documento.** Il regime **congelato** che il
chiamante passa, se non è vuoto; altrimenti quello **vivo** dell'emittente;
`NULL` se non c'è né l'uno né l'altro («regime non noto»).

⭐ **Perché è un building block.** La regola stava dentro
[script.fn_esigibilita_iva_documento](/dbzero/script/funzioni/fn_esigibilita_iva_documento).
Le annotazioni della fattura hanno bisogno della stessa risposta: se leggessero
il solo snapshot, una fattura senza snapshot con righe `D` (calcolate col regime
vivo) non stamperebbe l'annotazione. Alla seconda occorrenza la regola si è
estratta, e la copia è stata ritirata nello stesso giro (`20261002-04`).

Sta in `script` perché la domanda vale per ogni documento che congela un regime,
non solo per la fattura: domani anche per il passivo di `acquisti`.

### Firma

| Parametro | Tipo | Significato |
|---|---|---|
| `p_emittente_fiscale_id` | `emittenti_fiscali.id%TYPE` | l'emittente del documento; `NULL` = non noto |
| `p_regime_fiscale_rf` | `emittenti_fiscali.regime_fiscale_rf%TYPE`, `DEFAULT NULL` | il regime congelato del documento, se c'è |
| **Ritorno** | `emittenti_fiscali.regime_fiscale_rf%TYPE` | il codice RF che vale |

* Un congelato fatto di spazi non è un regime: vale quello vivo.
* ⚠️ Un congelato **fuori catalogo** esce com'è: lo snapshot è un testo, e la
  funzione dice **quale** regime, non che cosa significa. Chi legge
  `config.regimi_fiscali` lo tratta come «non noto».

`STABLE`, `SECURITY INVOKER`: un emittente che chi chiama non vede dà `NULL`.

### Chi la chiama

* [script.fn_esigibilita_iva_documento](/dbzero/script/funzioni/fn_esigibilita_iva_documento)
  (fattura, preventivi, ordini, DDT);
* [vendite.fn_regime_fiscale_fattura](/dbzero/vendite/funzioni/fn_regime_fiscale_fattura).

### Test

`db/pgtap/vendite/test-annotazioni-fattura-v1.sql` (casi 3-5).

---

{% include-markdown "signature-core.md" %}
