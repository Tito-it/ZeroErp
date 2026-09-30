## 📘 Documentazione Concettuale – Funzione `documenti.fn_guard_versione_contesto()`

> 👀 **Vedi anche**
>
> [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) (§ «Il patto con la forma dei dati»)
> [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati)
> [documenti.fn_pubblica_template_documento_versione](/dbzero/documenti/funzioni/fn_pubblica_template_documento_versione)
> [documenti.trgfn_documenti_generati_guard_versione_contesto](/dbzero/documenti/funzioni/trgfn_documenti_generati_guard_versione_contesto)

### 🎯 Scopo

(30-09-2026 — brief `brief-db-documenti-versione-contesto-template`)

Il **patto fra una versione di template e la forma dei dati che legge**, in un posto solo.
Risponde a una domanda: *la versione `p_template_versione_id` legge i dati nella forma
`p_versione_contesto`?* Se no, solleva, e nessun PDF nasce.

`p_versione_contesto` è la forma che i dati **hanno**: il `_meta.context_version` del contesto
(per una stampa) o la costante del builder (prima del render, alla pubblicazione). La forma che
il builder produce è un fatto del **codice**: il DB non la conosce e la riceve dal chiamante.

### Firma

| Parametro | Tipo | Significato |
|---|---|---|
| `p_template_versione_id` | `template_documenti_versioni.id%TYPE` | la versione di template che renderizza |
| `p_versione_contesto` | `template_documenti_versioni.versione_contesto%TYPE` | la forma dei dati da renderizzare |
| **Ritorno** | `void` | — |

`SECURITY INVOKER`: legge la versione nel perimetro di chi chiama.

### I tre chiamanti

| Chi | Quando | Con quale forma |
|---|---|---|
| backend | prima del render (niente PDF da buttare) | la costante del builder |
| trigger `trg_documenti_generati_a10_guard_versione_contesto_ins` | INSERT di una stampa | `_meta.context_version` del contesto congelato |
| `fn_pubblica_template_documento_versione` | pubblicazione di una BOZZA | `p_versione_contesto`, la costante del builder |

### Errori

| Codice | Classe | Quando |
|---|---|---|
| `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA` | `CONFLITTO_STATO` (409) | le due forme non coincidono. Frase: versione, nome del template, forma del template, forma dei dati. Rimedia chi amministra i template, pubblicando una versione che legga la forma di oggi |
| `E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE` | `TECNICO` (500) | manca la versione (NULL/≤ 0) o la forma dei dati (NULL). Solo un chiamante rotto lo produce |
| `E_DOCUMENTI_VERSIONE_NOT_FOUND` | `NON_TROVATO` | la versione non c'è, o non è nel perimetro di chi legge |

Nessun bersaglio: un template non è fra i tipi di `config.tipi_entita`.

### Perché `guard` e non `check`

Solleva, quindi è un guard (linee-guida-sql §5). Non c'è un pulsante da accendere o spegnere
a DB: la forma del builder non è un dato del database, e una capability non si potrebbe comporre.

### Test

`db/pgtap/documenti/test-documenti-versione-contesto-v1.sql` (guard e trigger),
`test-fn-pubblica-template-documento-versione-v1.sql` (test 8-11, la pubblicazione),
`test-documenti-template-versioni.sql` (test 10-11, immutabilità da PUBBLICATA e bozza libera).

---

{% include-markdown "signature-core.md" %}
