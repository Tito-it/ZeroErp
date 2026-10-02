## 📘 Documentazione Concettuale – Funzione `vendite.fn_regime_fiscale_fattura()`

> 👀 **Vedi anche**
>
> [script.fn_regime_fiscale_documento](/dbzero/script/funzioni/fn_regime_fiscale_documento) (la regola)
> [vendite.fn_esigibilita_iva_fattura](/dbzero/vendite/funzioni/fn_esigibilita_iva_fattura)
> [vendite.fn_annotazioni_fattura](/dbzero/vendite/funzioni/fn_annotazioni_fattura)

### 🎯 Scopo

(02-10-2026 — brief `brief-db-esigibilita-iva-per-cassa-emittente`, R-DB-3, D-8)

**Il regime fiscale di una fattura.** Legge dalla testata il regime congelato
nello snapshot dell'intestazione (`emittente_snapshot ->> 'regime_fiscale_rf'`) e
l'emittente (`emittente_soggetto_ruolo_id` → `emittenti_fiscali`: la fattura non
ha `emittente_fiscale_id`), e chiede a
[script.fn_regime_fiscale_documento](/dbzero/script/funzioni/fn_regime_fiscale_documento)
quale vale: lo snapshot se c'è, altrimenti il regime vivo.

⭐ **Una sede per due lettori.** L'esigibilità delle righe e le annotazioni in
stampa leggono il regime da qui. Così l'annotazione non può guardare un regime
diverso da quello con cui le righe sono state calcolate.

### Firma

| Parametro | Tipo | Significato |
|---|---|---|
| `p_fattura_id` | `vendite.fatture.id%TYPE` | la fattura |
| **Ritorno** | `emittenti_fiscali.regime_fiscale_rf%TYPE` | il codice RF della fattura; `NULL` = non noto |

Fattura inesistente o fuori dal perimetro di chi legge: `NULL`. Nessun guard che
sollevi: la chiama anche il trigger di riga, attraverso
`fn_esigibilita_iva_fattura`, con l'id di una FK. Il guard di parametro sta sul
punto d'ingresso del backend, `fn_annotazioni_fattura`.

`STABLE`, `SECURITY INVOKER`.

### Chi la chiama

* [vendite.fn_esigibilita_iva_fattura](/dbzero/vendite/funzioni/fn_esigibilita_iva_fattura)
  (trigger di riga e ricalcolo del riepilogo);
* [vendite.fn_annotazioni_fattura](/dbzero/vendite/funzioni/fn_annotazioni_fattura).

### Test

`db/pgtap/vendite/test-annotazioni-fattura-v1.sql` (casi 10-11).

---

{% include-markdown "signature-core.md" %}
