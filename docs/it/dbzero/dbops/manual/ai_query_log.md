## 📘 Documentazione Concettuale – Tabella `dbops.ai_query_log`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.request_log](/dbzero/dbops/tabelle/request_log) — la chiamata HTTP della stessa richiesta, legata dal `request_id`
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — lo scope delle automazioni, da cui dipende la pulizia di `cleanup_at`
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole di scadenza dei registri
>
> Guide:
>
> * [Audit e tracciabilità](/guide/audit-e-tracciabilita) — i registri del sistema e come scadono

---

### 🎯 Scopo Principale

Il registro delle **interazioni con l'assistente AI**: il testo dell'utente, gli strumenti
invocati, la risposta del modello, i token consumati, la durata, il provider e il modello usati.

Serve a tre cose diverse: capire **come** viene usato l'assistente, misurarne il **costo** (i
token sono la valuta) e poter ricostruire una risposta sbagliata.

---

### Lo scrive il backend, una riga per interazione

La riga la scrive il repository dell'assistente nel backend, a interazione conclusa, con un
INSERT diretto: nessuna funzione del database la scrive o la aggiorna (il trigger alla nascita
riempie solo `cleanup_at`). Il registro è
**append-only** per disegno: le righe non si correggono.

La scrittura è **di miglior sforzo**: se fallisce, la risposta all'utente parte lo stesso. Per le
operazioni delicate (scritture confermate, canale di supporto) il backend segnala il fallimento
come errore, perché lì la riga mancante è un'anomalia da guardare.

`request_id` è l'identificativo della richiesta HTTP che il middleware assegna: lo stesso che sta
in `dbops.request_log`, ed è il filo per passare dall'interazione alla chiamata. La tabella non
lo pretende univoco.

⚠️ `user_id` è obbligatorio: ogni interazione è attribuita, non esiste un uso anonimo
dell'assistente. È l'id dell'utente Django, ma **senza** vincolo di chiave esterna: la tabella
degli utenti sta nello schema dell'applicazione.

---

### ⭐ Contiene testo dell'utente, e scade a novanta giorni

`input_text` è testo digitato dall'utente e `response_text` è la risposta del modello: la tabella
può contenere dati sensibili, e la scadenza delle righe fa parte del suo disegno, non è un
dettaglio operativo. Le righe si tengono **novanta giorni**, lo stesso termine degli altri
registri di `dbops` (le richieste, gli errori, i giri delle automazioni).

La scadenza è fatta degli stessi pezzi degli altri registri che scadono:

* la tabella sta nello **scope delle automazioni**, con una riga sua: è ciò che fa vedere al job
  di pulizia le righe scadute;
* la **regola di scadenza** sta in `dbops.automation_rules_tbl`: novanta giorni da `data_insert`,
  l'unico orario della riga. È la sede del termine: lo leggono il trigger e il job;
* `cleanup_at` **nasce con la riga**: lo scrive all'inserimento il trigger
  `trg_ai_query_log_m50_cleanup_at_ins`, con `dbops.trgfn_cleanup_at_alla_nascita`, e il valore
  passato da chi scrive non conta. Il job delle scadenze riempie solo le righe nate prima del
  trigger, con la stessa regola;
* nessun guard sul `DELETE` da aprire: la tabella non ne ha.

⚠️ Il termine si congela alla nascita: accorciare la regola vale per le righe nuove, non per quelle
che hanno già la loro data.

---

### Note di migrazione

* 2026-03-31 — nasce con l'assistente AI, con `cleanup_at` previsto per la scadenza.
* 2026-11-07 — la scadenza diventa vera: la tabella entra nello scope delle automazioni, con la
  regola dei novanta giorni e il trigger alla nascita. Fino a quel giorno nessuno valorizzava
  `cleanup_at` e le righe restavano per sempre.

---

{% include-markdown "signature-core.md" %}
