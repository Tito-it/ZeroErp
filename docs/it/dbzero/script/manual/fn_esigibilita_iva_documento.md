## 📘 Documentazione Concettuale – Funzione `script.fn_esigibilita_iva_documento()`

> 👀 **Vedi anche**
>
> [script.fn_esigibilita_iva](/dbzero/script/funzioni/fn_esigibilita_iva) (la regola)
> [vendite.fn_esigibilita_iva_fattura](/dbzero/vendite/funzioni/fn_esigibilita_iva_fattura)

### 🎯 Scopo

(01-10-2026 — brief `brief-db-esigibilita-iva-per-cassa-emittente`, D-4, D-6, D-8)

**Le parti di un documento di vendita** per la regola dell'esigibilità: dal
`p_emittente_fiscale_id` il regime per cassa, dal `p_billing_account_id` la
scissione e la partita IVA del cliente. Poi chiama
[script.fn_esigibilita_iva](/dbzero/script/funzioni/fn_esigibilita_iva).

Fattura, preventivi, ordini e DDT fanno la stessa domanda con le stesse chiavi di
testata: la catena dei join sta qui una volta sola (regola del 2).

### Firma

| Parametro | Tipo | Significato |
|---|---|---|
| `p_emittente_fiscale_id` | `emittenti_fiscali.id%TYPE` | l'emittente del documento |
| `p_billing_account_id` | `billing_account.id%TYPE` | il cliente; `NULL` = non noto |
| `p_iva_id` | `config.iva.id%TYPE` | il codice IVA |
| `p_regime_fiscale_rf` | `emittenti_fiscali.regime_fiscale_rf%TYPE`, `DEFAULT NULL` | il regime **congelato** del documento, se c'è |
| **Ritorno** | `TABLE(esigibilita, split_payment)` | una riga |

⭐ `p_regime_fiscale_rf` è una **fonte di valore**, non un filtro: la fattura passa
il regime del suo snapshot dell'intestazione, così righe e testata dicono lo stesso
regime (D-8). I documenti senza snapshot non lo passano, e vale il regime vivo.

`SECURITY INVOKER`: un cliente che chi chiama non vede diventa «non noto», e la
coppia esce `NULL`/`NULL`.

### Chi la chiama

`vendite.fn_ricalcola_riepilogo_iva_preventivo`, le viste
`vendite.vw_ordini_riepilogo_iva_dettaglio` e `vendite.vw_ddt_riepilogo_iva_dettaglio`
(per codice IVA, `LEFT JOIN LATERAL ... ON true`), e
`vendite.fn_esigibilita_iva_fattura`.

---

{% include-markdown "signature-core.md" %}
