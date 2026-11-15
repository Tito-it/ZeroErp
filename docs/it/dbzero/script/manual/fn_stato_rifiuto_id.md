## 📘 Documentazione Concettuale – Funzione `script.fn_stato_rifiuto_id(regclass)`

> 👀 **Vedi anche**
>
> [script.fn_stato_accettazione_id](/dbzero/script/funzioni/fn_stato_accettazione_id) ·
> [script.fn_stato_per_colonna_id](/dbzero/script/funzioni/fn_stato_per_colonna_id) ·
> [script.fn_doc_stato_codice](/dbzero/script/funzioni/fn_doc_stato_codice) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §4

### 🎯 Scopo
(13-11-2026)

**Lo stato di rifiuto di un documento.** Preventivo e offerta si rifiutano quando il
cliente dice no. Quale stato sia il rifiuto lo dice il vocabolario degli stati, con la
colonna `rifiuto`. Questa funzione la legge, così nessuno scrive `'RIFIUTATO'` o
`'RIFIUTATA'` nel codice per dire «lo stato di rifiuto».

| Documento | Stato di rifiuto |
| --- | --- |
| Preventivo | Rifiutato |
| Offerta | Rifiutata |

### Regole

* Vuoto se il documento **non si rifiuta**: tutti tranne preventivo e offerta. Il loro
  vocabolario non ha la colonna.
* Il rifiuto non è il contrario dell'accettazione: un documento scaduto, superato o
  annullato ha anche lui un esito negativo, ma non è stato rifiutato dal cliente.
* La motivazione del rifiuto non la chiede questa colonna: la chiede la riga del
  passaggio nella matrice degli stati.
* Al massimo uno stato di rifiuto per vocabolario, ed è attivo: lo garantiscono un
  indice unico e un vincolo sulla tabella.
* Riceve la testata del documento, non il vocabolario. Una tabella fuori dalla mappa:
  `E_SCRIPT_CHIAMATA_NON_VALIDA`.

### Chi la legge

Il backend, quando registra il no del cliente, al posto del nome di stato scritto nel
service. Chi ha già in mano la riga del vocabolario legge la colonna `rifiuto`
direttamente: il guard del cambio di stato dell'offerta, che nel rifiuto scrive la data
del rifiuto.
