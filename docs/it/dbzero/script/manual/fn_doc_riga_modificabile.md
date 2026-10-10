## 📘 Documentazione Concettuale – Funzione `script.fn_doc_riga_modificabile()`

> 👀 **Vedi anche**
>
> • [script.fn_doc_lock_montaggi](/dbzero/script/funzioni/fn_doc_lock_montaggi) — il lettore del montaggio, dove sta il quadro intero
> • [script.fn_doc_colonna_modificabile](/dbzero/script/funzioni/fn_doc_colonna_modificabile) — la sorella, per una colonna sola

---

### 🎯 Scopo Principale

(nata il 2026-10-11, brief `brief-db-testata-dopo-emissione`, §11, R-DB-3)

**La domanda di una capability**: con il documento in questo stato, una riga **intera** di
questa tabella si aggiunge, si modifica e si toglie, oppure i lock «si tocca solo in bozza» la
fermano?

Legge il montaggio della tabella e decide con la stessa funzione del lock, sulla riga intera
(come un inserimento o una cancellazione). Non contiene nessuna regola sua. Una tabella senza
lock risponde sì, come farebbe il database.

La usano le capability per i **satelliti** del documento: `can_edit_indirizzi` di ordine,
DDT, preventivo, offerta e contratto, e `can_edit_utility` di offerta e contratto. Gli
indirizzi e la fornitura si scrivono solo in bozza: lo dice il lock montato su di loro, e la
capability lo legge da lì.
