## 📘 Documentazione Concettuale – Tabella `dbops.ai_query_log`

### 🎯 Scopo Principale

(rev 2026-08-21)

Log delle **interazioni con l'assistente AI**: testo dell'utente, strumenti invocati, risposta
del modello, metriche di token e durata, provider e modello usati.

Serve a tre cose diverse: capire **come** viene usato l'assistente, misurarne il **costo** (i
token sono la valuta), e poter ricostruire una risposta sbagliata.

---

### Append-only, con retention

Le righe non si aggiornano. La pulizia passa da `cleanup_at`: è la data a partire dalla quale
la riga può essere rimossa, invece di una cancellazione decisa altrove.

⚠️ **Contiene testo inserito dall'utente** (`input_text`) e la risposta del modello: è quindi
una tabella con potenziale contenuto sensibile, e la retention non è un dettaglio operativo ma
parte del suo disegno.

⚠️ `user_id` è `NOT NULL`: ogni interazione è attribuita. Non esiste un uso anonimo
dell'assistente.

---

{% include-markdown "signature-core.md" %}
