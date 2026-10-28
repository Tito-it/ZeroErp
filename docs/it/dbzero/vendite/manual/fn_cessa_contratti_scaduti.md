## 📘 Documentazione Concettuale – Funzione `vendite.fn_cessa_contratti_scaduti()`

> 👀 **Vedi anche**
>
> [dbops.fn_apply_chiusura_scadenze](/dbzero/dbops/funzioni/fn_apply_chiusura_scadenze) ·
> [dbops.automazione_chiusura_scadenze](/dbzero/dbops/tabelle/automazione_chiusura_scadenze) ·
> [vendite.fn_cessa_contratto](/dbzero/vendite/funzioni/fn_cessa_contratto) ·
> [Linee guida SQL §7c](/linee-guida-sql)

### 🎯 Scopo
(26-10-2026 — brief `brief-modello-documento-vendita` §11, decisione Y-2)

**La cessazione automatica dei contratti scaduti.** I contratti attivi la cui data di fine
è passata diventano `CESSATO`, uno per uno, dalla scrittura comune del modello del
documento. La chiama la chiusura per scadenza
([`dbops.fn_apply_chiusura_scadenze`](/dbzero/dbops/funzioni/fn_apply_chiusura_scadenze)),
che per una testata sotto la porta non può più usare il suo aggiornamento diretto.

### Regole

* **Solo i contratti scaduti**: nello stato di emissione (`ATTIVO`) e con la data di fine
  prima di oggi. Un contratto che scade oggi resta attivo fino a domani.
* **Il perimetro** è quello dell'utente della sessione: nel drenatore della coda, l'utente
  tecnico dell'azienda. Senza utente non cessa niente.
* **Nessun parametro**: chiunque la chiami cessa solo ciò che la chiusura per scadenza
  cesserebbe. Non chiede azioni: la causa è la data, non l'operatore.
* Ritorna quanti contratti ha cessato.
