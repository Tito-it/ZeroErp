## 📘 Documentazione Concettuale – Tabella `dbops.ai_query_log`

> **Ultimo aggiornamento**: 4 novembre 2026
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
INSERT diretto: nessuna funzione del database la scrive o la aggiorna. Il registro è
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

### ⚠️ Contiene testo dell'utente, e oggi non scade

`input_text` è testo digitato dall'utente e `response_text` è la risposta del modello: la tabella
può contenere dati sensibili, e la scadenza delle righe fa parte del suo disegno, non è un
dettaglio operativo. Per questo c'è `cleanup_at`, la data dalla quale la riga può essere rimossa.

⛔ Oggi la colonna **non la valorizza nessuno**: la tabella non sta nello scope delle automazioni
e non ha una regola di scadenza, quindi né il job di scadenza né un trigger alla nascita la
riempiono, e il job di pulizia non cancella mai una riga. Le righe restano per sempre, finché la
tabella non entra nello scope con la sua regola, come i quattro registri di `dbops` che già
scadono.

---

### Note di migrazione

* 2026-03-31 — nasce con l'assistente AI, con `cleanup_at` previsto per la scadenza.

---

{% include-markdown "signature-core.md" %}
