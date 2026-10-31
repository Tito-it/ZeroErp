## 📘 Documentazione Concettuale – Funzione `vendite.fn_chiudi_preventivi_scaduti()`

> 👀 **Vedi anche**
>
> [dbops.fn_apply_chiusura_scadenze](/dbzero/dbops/funzioni/fn_apply_chiusura_scadenze) ·
> [dbops.automazione_chiusura_scadenze](/dbzero/dbops/tabelle/automazione_chiusura_scadenze) ·
> [script.fn_stato_scadenza_id](/dbzero/script/funzioni/fn_stato_scadenza_id) ·
> [vendite.fn_cessa_contratti_scaduti](/dbzero/vendite/funzioni/fn_cessa_contratti_scaduti) ·
> guida [Gestione preventivi](/guide/gestione-preventivi) §3.1 ·
> [Linee guida SQL §7c](/linee-guida-sql)

### 🎯 Scopo
(31-10-2026 — brief `brief-db-scadenza-preventivi` §8, decisione E-1 (a) di Tid)

**La scadenza automatica dei preventivi.** Un preventivo emesso a cui il cliente non ha
risposto entro la sua validità diventa `SCADUTO`, uno per uno, dalla scrittura comune del
modello del documento. La chiama la chiusura per scadenza
([`dbops.fn_apply_chiusura_scadenze`](/dbzero/dbops/funzioni/fn_apply_chiusura_scadenze)),
che la trova dichiarata nella riga del preventivo del registro delle chiusure: il
preventivo è sotto la porta, e lo stato lo scrive solo un verbo.

È la gemella di
[`vendite.fn_cessa_contratti_scaduti`](/dbzero/vendite/funzioni/fn_cessa_contratti_scaduti)
e di
[`vendite.fn_chiudi_versioni_listino_scadute`](/dbzero/vendite/funzioni/fn_chiudi_versioni_listino_scadute).

### Regole

* **Solo i preventivi scaduti**: nello stato di emissione (`EMESSO`) e con «Valido al» prima
  di oggi. «Valido al» è l'ultimo giorno valido: un preventivo che scade oggi resta emesso
  fino a domani.
* **Senza «Valido al» non scade mai.**
* **Lo stato di arrivo** è quello che il vocabolario dichiara di scadenza (colonna
  `scadenza`, oggi `SCADUTO`), non un codice scritto nel corpo.
* **Il perimetro** è quello dell'utente della sessione: nel drenatore della coda, l'utente
  tecnico dell'azienda. Senza utente non chiude niente.
* **Nessun parametro**: chiunque la chiami chiude solo ciò che la chiusura per scadenza
  chiuderebbe. Non chiede azioni: la causa è la data, non l'operatore.
* Ritorna quanti preventivi ha portato allo stato di scadenza.

### Prima del passaggio del job

Fra la fine della validità e la corsa del job il preventivo è ancora `EMESSO`, ma non si
accetta lo stesso: lo rifiuta il guard di transizione con `E_PREV_VALIDITA_SCADUTA`
([`script.fn_check_preventivo_accettabile`](/dbzero/script/funzioni/fn_check_preventivo_accettabile)).
La regola non dipende dall'ora del job.
