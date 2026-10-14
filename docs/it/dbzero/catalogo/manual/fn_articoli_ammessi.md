## 📘 Documentazione Concettuale – Funzione `catalogo.fn_articoli_ammessi`

> 👀 **Vedi anche**
>
> [script.fn_check_articolo_riga](/dbzero/script/manual/fn_check_articolo_riga) — la regola, documento per documento
> [script.trgfn_righe_guard_articolo_ammesso](/dbzero/script/manual/trgfn_righe_guard_articolo_ammesso) — il guard che rifiuta con lo stesso motivo
> [vendite.fn_listini_selezionabili](/dbzero/vendite/funzioni/fn_listini_selezionabili) — il precedente, per il listino del documento

### 🎯 Scopo Principale

(nasce 2026-10-14, brief-db-articoli-ammessi-per-documento, Lotto 4: R-2, R-4, R-5; A-1, A-2, A-7)

È la **sede unica del picker** degli articoli di una riga. Dato il documento e il testo cercato,
restituisce gli articoli che la ricerca trova, ciascuno col **primo motivo** per cui il documento
non lo ammette. `motivo` vuoto (`NULL`) vuol dire ammesso. Prima vengono gli ammessi, poi gli
esclusi, ciascun gruppo per codice.

Il motivo è quello che il guard di tabella solleverebbe scrivendo la riga, perché viene dalla
**stessa regola** ([script.fn_check_articolo_riga](/dbzero/script/manual/fn_check_articolo_riga)).
Il picker non propone un articolo che poi viene rifiutato, e non nasconde un articolo che il
database accetterebbe.

Un articolo escluso **resta nell'elenco**, col suo motivo: chi cerca un codice preciso e non lo
vede fra gli ammessi sa perché. Come mostrarlo (grigio con la spiegazione, oppure solo quando la
ricerca non trova ammessi) lo decide l'interfaccia.

---

### Documenti

| `p_documento` | Il documento | Che cosa serve |
| --- | --- | --- |
| `PREVENTIVO`, `ORDINE_VENDITA`, `DDT_VENDITA` | le righe del documento | l'id della testata |
| `OFFERTA_COMMERCIALE`, `CONTRATTO` | le righe d'eccezione al listino | l'id e il tipo d'eccezione (`AGGIUNTA`, `OVERRIDE`, `ESCLUSIONE`) |
| `LISTINO_VERSIONE` | le righe di una versione di listino | l'id della versione |
| `ARTICOLO` | i componenti di una distinta | il padre (`p_articolo_padre_id`) |
| `PROMO_ARTICOLO` | l'articolo di una promo | niente: la regola dipende solo dall'articolo |

Le righe ricevono **l'id del documento salvato**, non i valori del form (A-1): il guard giudica
la riga contro la testata salvata, e il picker deve fare la stessa domanda. La testata nasce
sempre prima delle righe, quindi l'id c'è sempre.

---

### Che cosa propone

* Solo gli articoli **attivi**: ogni riga pretende un articolo attivo, e uno spento non si
  propone.
* La ricerca è un «contiene», senza distinzione fra maiuscole e minuscole, sul codice o sulla
  descrizione. Il testo è letterale: `%` o `_` non fanno da jolly. Testo vuoto: tutti.
* Il tetto (`p_limit`) lo sceglie il chiamante; si applica **dopo** aver giudicato tutti gli
  articoli trovati, perché «prima gli ammessi» non si può decidere sui soli primi.
* `ordine` è la posizione nell'elenco: chi unisce altre colonne dell'articolo (per esempio da
  `catalogo.vw_articoli_dettaglio`) ordina su questa.
* Nella **versione di listino** un composito esce col motivo `COMPOSITO_COME_BUNDLE`: come riga
  semplice è rifiutato, ma nella versione entra come bundle, coi prezzi dei componenti.
  L'interfaccia lo propone per quella strada.

---

### Come lavora

La regola è divisa in due metà:

1. [script.fn_articolo_riga_contesto](/dbzero/script/manual/fn_articolo_riga_contesto) legge
   **una volta** il lato documento (il listino operativo e la sua versione espansa, la tipologia
   del listino, il padre della distinta) e valida i parametri;
2. [script.fn_check_articolo_riga_su_contesto](/dbzero/script/manual/fn_check_articolo_riga_su_contesto)
   giudica **ogni articolo** trovato su quel contesto.

Il guard usa le stesse due metà attraverso la firma di sempre. Leggere il documento una volta
sola è ciò che rende il picker abbastanza veloce da girare a ogni tasto premuto.

---

### Firma

```sql
catalogo.fn_articoli_ammessi(
    p_documento         text,     -- codice di config.tipi_entita
    p_documento_id      bigint,   -- la testata (o la versione di listino)
    p_search            text    DEFAULT NULL,
    p_limit             integer DEFAULT 50,
    p_tipo_eccezione    vendite.tipo_eccezione_contratto DEFAULT NULL,
    p_articolo_padre_id uuid    DEFAULT NULL)
RETURNS TABLE(articolo_id uuid, codice varchar, descrizione varchar, motivo jsonb, ordine integer)
```

* `motivo`: `{codice, reason, reason_key, dettaglio, valori}`, il primo dell'array della check.
* Errori: id mancante per un documento con testata, o `p_limit` minore di 1:
  `E_PARAMETRO_INVALIDO`; documento sconosciuto: `E_DOC_TIPO_NON_GESTITO`; tipo d'eccezione
  mancante per offerta e contratto, o padre mancante per la distinta: `E_PARAMETRO_INVALIDO`.
* Sotto RLS (`SECURITY INVOKER`): il documento si legge con i permessi dell'operatore, come lo
  legge il guard.

---
{% include-markdown "signature-core.md" %}
