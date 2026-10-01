## 📘 Documentazione Concettuale – Funzione `script.fn_esigibilita_iva()`

> 👀 **Vedi anche**
>
> [config.regimi_fiscali](/dbzero/config/tabelle/regimi_fiscali)
> [script.fn_esigibilita_iva_documento](/dbzero/script/funzioni/fn_esigibilita_iva_documento)
> [vendite.fn_esigibilita_iva_fattura](/dbzero/vendite/funzioni/fn_esigibilita_iva_fattura)
> [vendite.trgfn_fatture_righe_guard_normalize](/dbzero/vendite/funzioni/trgfn_fatture_righe_guard_normalize)
> [vendite.fn_resolve_iva_riga_it](/dbzero/vendite/funzioni/fn_resolve_iva_riga_it)

### 🎯 Scopo

(01-10-2026 — brief `brief-db-esigibilita-iva-per-cassa-emittente`)

**La regola unica dell'esigibilità IVA** di una riga: `I` immediata, `D` differita,
`S` scissione dei pagamenti, insieme al flag `split_payment`. Prima del 2026-10-01
la regola stava in due copie (il trigger di riga della fattura e il risolutore IVA),
che coincidevano solo perché guardavano il solo cliente. Con il regime
dell'emittente la decisione dipende da tre cose, e due copie divergerebbero.

### Firma

| Parametro | Tipo | Significato |
|---|---|---|
| `p_iva_per_cassa` | `config.regimi_fiscali.iva_per_cassa%TYPE` | il regime dell'emittente, come **attributo** (mai il codice RF) |
| `p_cliente_split_payment` | `anagrafiche.soggetti.split_payment%TYPE` | la scissione del cliente; `NULL` = cliente non noto |
| `p_cliente_partita_iva` | `anagrafiche.soggetti.partita_iva%TYPE` | la partita IVA del cliente (D-2) |
| `p_iva_id` | `config.iva.id%TYPE` | il codice IVA della riga |
| **Ritorno** | `TABLE(esigibilita, split_payment)` | **sempre una riga** |

`STABLE`, `SECURITY INVOKER`: legge il solo codice IVA, per sapere se la riga ha
un'imposta (nessuna Natura e aliquota maggiore di zero).

### L'ordine delle domande

| # | Caso | Risultato |
|---|---|---|
| 1 | cliente non noto | `NULL` / `NULL` («non lo so», D32) |
| 2 | cliente in scissione | `S` / `true` (prevale su tutto) |
| 3 | regime non noto | `NULL` / `false` |
| 4 | regime non per cassa | `I` / `false` |
| 5 | per cassa, cliente senza partita IVA (o fatta di spazi) | `I` / `false` |
| 6 | per cassa, codice IVA assente o inesistente | `NULL` / `false` (non si sa se c'è imposta) |
| 7 | per cassa, codice con una **Natura** (N1-N7, inversione contabile compresa) o aliquota zero | `I` / `false` |
| 8 | per cassa, riga **con imposta** | `D` / `false` |

⭐ **D-12 (Tid, 2026-10-01, changeSet `20261001-40`)**: `D` solo sulle righe con
imposta. Qualsiasi Natura, dalla N1 alla N7, va a `I`: non c'è imposta da
differire. Fino al `-40` la regola mandava a `I` la sola inversione contabile.

⭐ **Derivazione pura (D-7)**: chi la usa riscrive sempre il valore. Non esiste un
ramo «lascia quello che c'era»: una differita scelta a mano, se mai servirà, avrà
una colonna sua.

⚠️ **Fuori dal modello, dichiarati**: i regimi speciali esclusi dal 32-bis
(brief, sezione 7).

### Chi la chiama

| Chi | Come risolve le parti |
|---|---|
| [vendite.fn_esigibilita_iva_fattura](/dbzero/vendite/funzioni/fn_esigibilita_iva_fattura) (trigger di riga, ricalcolo del riepilogo) | regime dello snapshot della fattura, o vivo |
| [script.fn_esigibilita_iva_documento](/dbzero/script/funzioni/fn_esigibilita_iva_documento) (riepiloghi di preventivi, ordini, DDT) | emittente e billing account di testata |
| [vendite.fn_resolve_iva_riga_it](/dbzero/vendite/funzioni/fn_resolve_iva_riga_it) | emittente e soggetto passati al risolutore, per parte |

### Test

`db/pgtap/vendite/test-esigibilita-iva-per-cassa-v1.sql` (casi 2-10 e 9-bis: la matrice).

---

{% include-markdown "signature-core.md" %}
