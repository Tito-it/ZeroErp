## 📘 Documentazione Concettuale – Funzione `script.fn_articolo_riga_contesto`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> [script.fn_check_articolo_riga](/dbzero/script/manual/fn_check_articolo_riga) — la firma che compone le due metà
> [script.fn_check_articolo_riga_su_contesto](/dbzero/script/manual/fn_check_articolo_riga_su_contesto) — i motivi, che ricevono questo contesto
> [catalogo.fn_articoli_ammessi](/dbzero/catalogo/funzioni/fn_articoli_ammessi) — il picker

### 🎯 Scopo Principale

(nasce 2026-10-14, brief-db-articoli-ammessi-per-documento, Lotto 4: R-5)

È **il lato documento** della regola sugli articoli di una riga: ciò che i motivi leggono e che
non dipende dall'articolo. Lo legge una volta e lo restituisce come contesto `jsonb`.

Serve perché la stessa regola ha due chiamanti diversi. Il guard giudica una riga, cioè un
articolo. Il picker giudica tutti gli articoli che la ricerca trova, sullo stesso documento:
senza questa metà rileggerebbe il listino (e la sua versione espansa coi bundle) una volta per
articolo.

---

### Il contesto

| Documento | Chiavi in più |
| --- | --- |
| tutti | `documento`, `documento_id`, `tipo_eccezione`, `articolo_padre_id` |
| `LISTINO_VERSIONE` | `listino_tipologia_id` |
| `ARTICOLO` (la distinta) | `padre_codice`, `padre_iva_id`, `padre_aliquota` |
| `OFFERTA_COMMERCIALE`, `CONTRATTO` | `doc_listino`, `listino_id`, `listino_versione_id`, `etichetta`, `articoli_listino` |

`articoli_listino` è l'elenco degli articoli della versione operativa **espansa**
(`vendite.fn_espandi_listino_versione`: righe semplici e bundle), cioè «nel listino» come lo
intende il drawer delle eccezioni. Senza versione è vuoto.

Preventivo, ordine, bolla e promo non leggono il documento: il contesto ha solo le chiavi comuni.

---

### Validazione

Le validazioni dei parametri stanno qui, perché è la porta d'ingresso di entrambi i chiamanti:

* documento sconosciuto: `E_DOC_TIPO_NON_GESTITO`;
* offerta e contratto senza tipo d'eccezione, distinta senza padre: `E_PARAMETRO_INVALIDO`.

L'id del documento **non** è obbligatorio qui: preventivo, ordine e bolla non lo leggono.
L'obbligo (A-1) è del picker.

⚠️ **Ponte A-8.** `doc_listino` è la grammatica `OFFERTA | CONTRATTO` dei lettori del listino;
la traduzione da `OFFERTA_COMMERCIALE` sta qui, in un punto solo, finché quei lettori non passano
a `config.tipi_entita` (giro BE/FE).

Sotto RLS (`SECURITY INVOKER`): un documento che l'operatore non vede dà un contesto senza
listino.

---
{% include-markdown "signature-core.md" %}
