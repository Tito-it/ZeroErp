## 📘 Documentazione Concettuale – Funzione `script.fn_doc_colonna_modificabile()`

> 👀 **Vedi anche**
>
> • [script.fn_doc_lock_montaggi](/dbzero/script/funzioni/fn_doc_lock_montaggi) — il lettore del montaggio, dove sta il quadro intero
> • [script.fn_check_ordine_data_consegna_confermata](/dbzero/script/funzioni/fn_check_ordine_data_consegna_confermata) — la prima check che la usa

---

### 🎯 Scopo Principale

(nata il 2026-10-10, brief `brief-db-testata-dopo-emissione`, fase 1)

**La domanda di una capability**: con il documento in questo stato, una modifica che cambia
**solo** questa colonna passa i lock «si tocca solo in bozza» della tabella?

Legge il montaggio della tabella e decide con la stessa funzione del lock: non contiene
nessuna regola sua. Una tabella senza lock risponde sì, come farebbe il database.

Lo stato lo passa chi chiede, per `codice_interno`. Per una tabella *nipote* (componenti,
prelievi, rientri) è lo stato della testata del documento.

Oggi la usa la promessa di consegna delle righe d'ordine. È pensata anche per l'ubicazione
d'arrivo dei prelievi della bolla e per le colonne di testata della fase 2 del brief.
