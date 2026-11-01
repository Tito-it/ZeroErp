## 📘 Documentazione Concettuale – Funzione `vendite.fn_documento_righe_preview`

> **Ultimo aggiornamento**: 1 novembre 2026

> 👀 **Vedi anche**
>
> **Gli ingressi per documento:** [vendite.fn_contratto_righe_preview](/dbzero/vendite/funzioni/fn_contratto_righe_preview) ·
> [vendite.fn_offerta_righe_preview](/dbzero/vendite/funzioni/fn_offerta_righe_preview)
>
> **Da cui legge:** [vendite.fn_documento_listino_operativo](/dbzero/vendite/funzioni/fn_documento_listino_operativo) ·
> [vendite.fn_espandi_listino_versione](/dbzero/vendite/funzioni/fn_espandi_listino_versione) ·
> [vendite.fn_documento_righe_eccezione](/dbzero/vendite/funzioni/fn_documento_righe_eccezione) ·
> [script.fn_check_esclusione_articolo_documento](/dbzero/script/funzioni/fn_check_esclusione_articolo_documento)
>
> **Verifica:** `db/pgtap/vendite/test-contratto-righe-lista-v1.sql` (contratto) ·
> `db/pgtap/vendite/test-righe-esclusione-solo-non-si-vende-v1.sql` (offerta, e il confronto fra i due ingressi)

---

### 🎯 Scopo Principale

(funzione nata il 2026-10-04, `20261004-71`, dal corpo di
`fn_contratto_righe_preview`)

**Le righe di un contratto o di un'offerta come le vede il drawer, con i
verbi che il database ammette.** È il corpo comune delle due liste: il
contratto e l'offerta la chiamano con il loro documento, e il frontend rende
quello che riceve senza dedurre niente.

Ogni riga dice da dove viene (`origine`) e che cosa ci si può fare (`azioni`):

| Origine | Che cos'è | Azioni |
| --- | --- | --- |
| `DA_LISTINO` | un articolo del listino, senza eccezione | forza il prezzo, escludi, aderisci |
| `OVERRIDE` | un articolo del listino a un prezzo forzato | modifica, ripristina il prezzo del listino |
| `ADESIONE` | un articolo del listino che il documento prende (quantità, periodicità) | modifica, rimuovi l'adesione |
| `ESCLUSIONE` | un articolo del listino che il documento non vende | ripristina l'articolo (e basta: un'esclusione non si modifica) |
| `AGGIUNTA` | un articolo fuori listino | modifica, rimuovi |

«Escludi» può essere spento: `escludi_blocco_codice` porta il motivo (oggi uno
solo, il componente di un bundle), lo stesso con cui il guard rifiuterebbe.

---

### Da dove vengono le righe

1. **Il listino**: la versione che vale per il documento
   ([`fn_documento_listino_operativo`](/dbzero/vendite/funzioni/fn_documento_listino_operativo)),
   espansa in articoli singoli e bundle, con sopra i prezzi forzati e le
   esclusioni del documento. Senza listino questa parte non c'è.
2. **Le aggiunte**: gli articoli fuori listino, singoli e bundle, ciascuno
   nell'unità di misura della sua riga (o in quella dell'articolo, se la riga
   non la dice), coi componenti del bundle presi dalla tabella del documento.

Ogni riga ha una chiave (`riga_key`): `L:<articolo>:<unità>` per le righe del
listino, `A:<id>` per le aggiunte. In coda, `ordine` e `uom_operativa_id` della
riga eccezione, che il form di modifica rimanda al salvataggio, poi `periodicita` e
`generazione_canone` (26 colonne):

* sulla riga con un'eccezione, quelle della riga: il form in modifica le rimanda come
  sono scritte, e non le cancella;
* sulla riga `DA_LISTINO`, la periodicità del listino
  ([`fn_listino_periodicita_articolo`](/dbzero/vendite/manual/fn_listino_periodicita_articolo),
  il kit compreso), che è la proposta di «Aderisci»; nessuna generazione, che allora è
  quella della testata.

⚠️ Il blocco «documento fuori bozza» non è qui: è una regola del documento, non
della riga.

---

### Forma

- Primo argomento: il documento (`CONTRATTO`, `OFFERTA`).
- `STABLE`, `SECURITY INVOKER`: legge sotto la sicurezza per riga di chi chiede;
  documento assente o fuori perimetro = nessuna riga.
- La storia delle regole (verbi per origine, unità di misura della riga,
  esposizione dei componenti, esclusione senza «modifica») è nella pagina di
  [`fn_contratto_righe_preview`](/dbzero/vendite/funzioni/fn_contratto_righe_preview),
  dove sono nate.

---

{% include-markdown "signature-core.md" %}
