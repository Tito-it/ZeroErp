## 📘 Documentazione Concettuale – Funzione `script.fn_check_sorgente_chiudibile`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — le righe di commessa che conta
>
> Approfondimento funzioni:
>
> * [vendite.fn_ritira_commessa_attivita_da_sorgente](/dbzero/vendite/funzioni/fn_ritira_commessa_attivita_da_sorgente) — l'altra metà della regola: il ritiro delle righe non emesse
> * [vendite.trgfn_doc_guard_chiusura_sorgente](/dbzero/vendite/funzioni/trgfn_doc_guard_chiusura_sorgente) — il guard che ne solleva il primo motivo
> * [vendite.fn_riporta_attivita_da_emettere](/dbzero/vendite/funzioni/fn_riporta_attivita_da_emettere) — la via d'uscita che il messaggio nomina
> * [script.fn_check_ordine_annullabile](/dbzero/script/funzioni/fn_check_ordine_annullabile) — una delle due capability che le delegano
> * [script.fn_check_preventivo_annullabile](/dbzero/script/funzioni/fn_check_preventivo_annullabile) — l'altra
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza: tipo, documento, riga

---

### 🎯 Scopo Principale

Elenca i **motivi che impediscono di chiudere** (annullare) un documento che ha spinto righe in
commessa. Funzione **pura**: non scrive e non solleva errori di dominio; ritorna un elenco vuoto
quando il documento si può chiudere.

⭐ **Il motivo è uno**: ci sono righe di commessa già `EMESSA`. Sono in volo verso una fattura, non si
ritirano, e finché ci sono la testata non si chiude.

---

### La regola, divisa per stato

Quando un documento si chiude, ciò che aveva spinto in commessa segue due strade, secondo dove è
arrivato:

| Stato della riga | Che cosa succede | Chi lo fa |
| --- | --- | --- |
| `NON_EMESSA` | ⭐ il documento la ritira (`ANNULLATA`) | `vendite.fn_ritira_commessa_attivita_da_sorgente` |
| `EMESSA` | ⛔ la testata non si chiude | questa funzione, sollevata dal guard |
| `ANNULLATA` | non si tocca | — |

---

### ⭐ Il rifiuto ha una via d'uscita

Il messaggio nomina la sequenza: «Riporta da emettere» riporta la riga a `NON_EMESSA`, poi si chiude
il documento, e il ritiro la prende insieme alle altre. Senza quel verbo il rifiuto sarebbe un vicolo
cieco.

---

### Il documento si passa con le colonne del modello

Il documento si indica con il tipo (`config.sorgenti`), `sorgente_id` e `sorgente_uid`, e le righe di
commessa si cercano sulla loro provenienza con la **regola d'incontro**: una riga conta se il suo
`sorgente_id` è quello passato oppure il suo `sorgente_uid` è quello passato. Chi ha il documento
passa il suo id e il suo uid, e la regola trova le righe qualunque sia la chiave del tipo.

⛔ **Una chiave sbagliata non produce un errore: produce zero motivi**, cioè un freno che lascia
passare tutto. Per questo i chiamanti passano tutte e due le chiavi del documento che hanno in mano.

---

### Una primitiva sola, non una per documento

La provenienza è la stessa per tutti i tipi, e una copia per documento divergerebbe.

⭐ **Una implementazione, più superfici.** La stessa funzione serve il guard
`vendite.trgfn_doc_guard_chiusura_sorgente` (montato su ordini, contratti e bolle), che ferma la
scrittura; le capability `script.fn_check_ordine_annullabile` e `script.fn_check_preventivo_annullabile`,
che accendono o spengono il pulsante; il verbo `vendite.fn_documento_ritira_legami`.

⚠️ Il preventivo **rietichetta** il motivo con il proprio codice (`E_PREV_ANNULLA_COMMESSA_EMESSA`): la
regola resta una, cambia il nome con cui esce. Ed è il motivo per cui sui preventivi il guard generico
non è montato: uscirebbero due codici per lo stesso rifiuto.

---

### ℹ️ Che cosa non guarda

* le righe già `ANNULLATA`: sono uscite di proposito;
* le `NON_EMESSA`: sono proprio quelle che il ritiro porta via;
* ⚠️ le righe senza documento d'origine (`ONERE`, `RETTIFICA`): non hanno provenienza, quindi nessun
  documento le raggiunge. È corretto, e va detto invece che lasciato dedurre.

⚠️ **Gira sotto la RLS di chi chiede**: `commesse_attivita` ha il perimetro per emittente, e chi non
vede le righe non viene fermato. Qui non c'è una FK a fare da rete; il caso resta stretto perché la
commessa eredita l'emittente dal documento.

⭐ Il valore nel messaggio è il **conteggio** delle righe, non i loro id: dice all'operatore quanto
lavoro deve recuperare. La `reason_key` è `vendite.sorgenti.azione_reason.righe_commessa_emesse`.

---

### Codici errore

* `E_SORGENTE_CON_RIGHE_EMESSE` — il motivo restituito (non sollevato qui): righe di commessa già
  `EMESSA`, con il conteggio.
* `E_RITIRO_SORGENTE_PARAMETRO_MANCANTE` — il solo errore sollevato: il tipo è vuoto o non positivo,
  oppure manca la chiave del documento, oppure l'id non è positivo.

---

### Test

* `db/pgtap/vendite/test-ritiro-commessa-attivita-da-sorgente-v1.sql` e
  `db/pgtap/vendite/test-ritiro-alla-chiusura-documento-v1.sql` — il motivo sulle righe emesse, il
  ritiro delle non emesse.
* `db/pgtap/vendite/test-sorgente-commesse-attivita-v1.sql` — la ricerca sulle colonne del modello.
* `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql` — il primo motivo, sollevato dal guard.

---

### Note di migrazione

* 2026-08-26 — nasce come primitiva unica del freno sulle righe emesse; le capability di ordine e
  preventivo le delegano (`brief-db-lavoro-che-non-torna-indietro`).
* 2026-11-07 — il documento si passa con tipo, `sorgente_id` e `sorgente_uid` al posto della chiave in
  testo, come `vendite.commesse_attivita` porta ora la provenienza (`brief-db-sorgente-documento-e-riga`).

---
{% include-markdown "signature-core.md" %}
