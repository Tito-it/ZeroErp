## 📘 Documentazione Concettuale – Funzione `script.fn_articolo_riga_contesto`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — la distinta, il documento `ARTICOLO`
>
> Approfondimento funzioni:
>
> * [script.fn_check_articolo_riga](/dbzero/script/funzioni/fn_check_articolo_riga) — la firma che compone le due metà
> * [script.fn_check_articolo_riga_su_contesto](/dbzero/script/funzioni/fn_check_articolo_riga_su_contesto) — i motivi, che ricevono questo contesto
> * [catalogo.fn_articoli_ammessi](/dbzero/catalogo/funzioni/fn_articoli_ammessi) — il picker
> * [catalogo.trgfn_articoli_componenti_guard_componente](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_guard_componente) — il guard della distinta, che passa di qui a ogni composizione nuova

---

### 🎯 Scopo Principale

È **il lato documento** della regola sugli articoli di una riga: ciò che i motivi leggono e che non dipende dall'articolo. Lo legge una volta e lo restituisce come contesto `jsonb`.

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
L'obbligo è del picker.

---

### ⭐ La testata della distinta è un kit

Per la distinta (`ARTICOLO`) la «testata» è l'articolo padre, e deve essere composito: un padre
inesistente o non composito non ha una distinta, e nessun componente ci può stare
(`E_ARTICOLO_NON_COMPOSITO`, campo `prodotto_id`). È un controllo del documento, non del singolo
componente, come il padre mancante: per questo sta qui e non fra i motivi.

Ne seguono due cose:

* il guard della distinta, che chiama la check a ogni composizione nuova (un legame che nasce, che
  si riattiva, o la cui fine si allontana), rifiuta un padre non composito in tutti questi casi;
* il picker `catalogo.fn_articoli_ammessi`, su un padre non composito, solleva lo stesso codice
  invece di proporre una lista vuota.

Un padre «solo componente» non è un caso a parte: il CHECK di `catalogo.articoli` gli impedisce
di essere composito, e quindi è già un padre non composito.

---

### Il ponte verso i lettori del listino

⚠️ `doc_listino` è la grammatica `OFFERTA | CONTRATTO` dei lettori del listino; la traduzione da
`OFFERTA_COMMERCIALE` sta qui, in un punto solo, finché quei lettori non passano a
`config.tipi_entita`.

Sotto RLS (`SECURITY INVOKER`): un documento che l'operatore non vede dà un contesto senza
listino.

---

### Codici errore

* `E_DOC_TIPO_NON_GESTITO` — documento sconosciuto.
* `E_PARAMETRO_INVALIDO` — offerta o contratto senza tipo d'eccezione, distinta senza padre.
* `E_ARTICOLO_NON_COMPOSITO` — distinta con un padre inesistente o non composito.

---

### Test

* `db/pgtap/catalogo/test-distinta-storia-e-ritorni-v1.sql` — la riattivazione di un legame sotto
  un padre non più composito, e un legame nuovo su un padre non composito, sono rifiutati.
* `db/pgtap/catalogo/test-articoli-componenti-solo-componente.sql` — un solo componente come padre
  è rifiutato.
* `db/pgtap/catalogo/test-articoli-componenti-guard-attivo-composito.sql` — il padre non composito
  è rifiutato.

---

### Note di migrazione

* 2026-10-14 — nasce, come metà documento della check delle righe
  (brief-db-articoli-ammessi-per-documento, Lotto 4: R-5; il ponte è A-8, l'obbligo del picker A-1).
* 2026-11-09 — per la distinta pretende un padre composito: prima lo diceva solo un guard sul
  legame, montato sull'inserimento e sul cambio del padre, che la riattivazione non attraversava
  (brief-db-revisione-catalogo, giro 1).

---

{% include-markdown "signature-core.md" %}
