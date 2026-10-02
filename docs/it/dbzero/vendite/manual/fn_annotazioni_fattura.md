## 📘 Documentazione Concettuale – Funzione `vendite.fn_annotazioni_fattura()`

> 👀 **Vedi anche**
>
> [vendite.fn_regime_fiscale_fattura](/dbzero/vendite/funzioni/fn_regime_fiscale_fattura) (il regime della fattura)
> [config.regimi_fiscali](/dbzero/config/tabelle/regimi_fiscali) (il testo)
> [vendite.fn_esigibilita_iva_fattura](/dbzero/vendite/funzioni/fn_esigibilita_iva_fattura)

### 🎯 Scopo

(02-10-2026 — brief `brief-db-esigibilita-iva-per-cassa-emittente`, R-DB-3, AN-1)

**Le annotazioni di legge che una fattura deve stampare**, come lista: una riga
per voce, nell'ordine di stampa. Nessuna voce = nessuna riga, mai una riga a
`NULL`.

La legge il builder della fattura (forma 4 del contesto): la copia in
`annotazioni` come lista di `{codice, testo}`, e il template (v6) la stampa
sotto i totali.

⭐ **Perché una lista decisa dal database.** Fino alla v4 il template non
stampava nessuna annotazione di legge. Un campo per ogni annotazione vorrebbe una
forma nuova del contesto e una versione nuova del template a ogni aggiunta. Con la
lista, le voci future (scissione dei pagamenti, inversione contabile, bollo
virtuale…) sono **righe nuove di questa funzione**, e template e builder non
cambiano.

### Le voci

| `codice` | Quando esce | `testo` | `ordine` |
|---|---|---|---|
| `ESIGIBILITA_DIFFERITA` | il regime **della fattura** è per cassa (`iva_per_cassa`) **e** almeno una riga ha `esigibilita = 'D'` | `config.regimi_fiscali.annotazione_documento` del regime (per RF17 l'annotazione art. 32-bis) | 10 |

* **La condizione guarda le righe**, non solo il regime: una fattura RF17 verso
  un privato, o con sole righe con Natura, è tutta immediata, e l'annotazione
  sarebbe falsa (sezione 8.7 del brief).
* **Il regime è quello della fattura**
  ([vendite.fn_regime_fiscale_fattura](/dbzero/vendite/funzioni/fn_regime_fiscale_fattura)):
  lo snapshot se c'è, altrimenti il regime vivo. È lo stesso con cui le righe
  sono state calcolate.
* **Il testo c'è sempre**: un regime per cassa senza annotazione non può
  esistere (CHECK `chk_regimi_fiscali_per_cassa_annotazione`).
* ⚠️ La voce chiede `iva_per_cassa`, non solo un testo nel catalogo: un regime
  con una dicitura sua che non dipende dalle righe (il forfettario) avrà una voce
  sua, con la sua condizione.

### Firma

| Parametro | Tipo | Significato |
|---|---|---|
| `p_fattura_id` | `vendite.fatture.id%TYPE` | la fattura |
| **Ritorno** | `TABLE(codice text, testo text, ordine integer)` | una riga per voce |

`testo` è ancorato a `annotazione_documento`. `codice` e `ordine` non hanno una
colonna di cui siano il riflesso: sono il vocabolario delle voci e la posizione di
stampa.

* `p_fattura_id` nullo o non positivo: `E_VENDITE_CHIAMATA_NON_VALIDA` (TECNICO,
  è rotto il chiamante). Per questo la funzione è `VOLATILE` e non `STABLE`:
  solleva e scrive il log degli errori.
* Fattura inesistente o fuori dal perimetro di chi legge: nessuna riga.

`SECURITY INVOKER`: sotto RLS contano solo le righe che chi legge vede.

### Test

`db/pgtap/vendite/test-annotazioni-fattura-v1.sql` (casi 6-9, 11-13).

---

{% include-markdown "signature-core.md" %}
