## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_contratti_guard_transizione_stato()`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti)
> [config.transizioni_stati_contratti](/dbzero/config/tabelle/transizioni_stati_contratti)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni:
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> [script.fn_available_actions_contratto](/dbzero/script/funzioni/fn_available_actions_contratto) — spegne «Attiva» con gli stessi motivi
> [vendite.trgfn_contratti_freeze_listino_versione](/dbzero/vendite/funzioni/trgfn_contratti_freeze_listino_versione) — il listino all'attivazione
> [vendite.fn_cessa_contratto](/dbzero/vendite/funzioni/fn_cessa_contratto) — il verbo della cessazione, che scrive la data di fine
>
Linee guida:
> [Linee guida SQL §7c — Ciclo stato + finestra di validita'](/linee-guida-sql)

### 🎯 Scopo Principale

La trigger function **`vendite.trgfn_contratti_guard_transizione_stato()`** giudica ogni cambio di
stato del contratto. La monta `trg_contratti_a10_guard_transizione_stato_upd` (`BEFORE UPDATE`
dello stato), dopo la porta: lo stato lo scrivono solo i verbi del contratto, e qui si decide se il
passaggio si può fare.

Il grafo lo legge dalla matrice `config.transizioni_stati_contratti`, e il **significato** degli
stati dal vocabolario `config.stati_doc_contratti`: lo stato di emissione (`emissione`,
l'attivazione) e lo stato di cessazione (`cessazione`). Nessun codice di stato è scritto nel corpo:
i codici vanno solo nel contesto degli errori. Le regole sono le stesse, nello stesso ordine, con
cui [`script.fn_available_actions_contratto`](/dbzero/script/funzioni/fn_available_actions_contratto)
spegne i pulsanti.

---

### Le regole

| Quando | Regola | Errore |
| --- | --- | --- |
| sempre | il passaggio esiste attivo nella matrice | `E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA` |
| verso lo stato di cessazione | in più, la data di fine c'è ed è arrivata: `valido_al <= script.fn_data_operativa()` | `E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA` |
| verso lo stato di emissione | il primo motivo, in quest'ordine: `script.fn_check_prezzi_autorizzati` (righe e componenti BoM attivi col prezzo in attesa o rifiutato), `script.fn_check_indirizzi_documento_cliente` (un indirizzo d'anagrafica che non è del cliente), `script.fn_check_righe_documento` (una riga che la regola intera non ammette più), `script.fn_check_contratto_sovrapposto` (un contratto vincolante sovrapposto sulla quintupla dell'EXCLUDE) | `E_DOC_PREZZO_PENDENTE`, `E_DOC_PREZZO_RIFIUTATO`, `E_INDIRIZZO_DOC_NON_DEL_CLIENTE`, `E_DOC_RIGA_NON_AMMESSA`, `E_CONTRATTO_OVERLAP_ESISTENTE` |

Col vocabolario di oggi lo stato di emissione è `ATTIVO`, quello di cessazione `CESSATO`.

⚠️ **Una data futura è una cessazione programmata.** La scrive il verbo della cessazione
([`vendite.fn_cessa_contratto`](/dbzero/vendite/funzioni/fn_cessa_contratto)), che rifiuta una data
passata; lo stato lo porta il job delle scadenze quando la data arriva. Il guard chiede la data
arrivata a chiunque scriva lo stato.

⚠️ **Il sovrapposto si giudica sui valori di `NEW`:** un `UPDATE` che porta il contratto in
emissione cambiando le date nella stessa istruzione si giudica sulle date nuove (la riga salvata è
ancora quella di prima). Il vincolo `ex_contratti_no_overlap` resta la difesa dura; il codice
parlante arriva da qui.

---

### La matrice (seed)

| Da | A | Manuale |
| --- | --- | --- |
| DRAFT | ATTIVO | sì (attiva) |
| DRAFT | ANNULLATO | sì (annulla) |
| ATTIVO | CESSATO | sì (cessa, con la data) |

---

### Codici errore

| Codice | id | Quando |
| --- | --- | --- |
| `E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA` | 392 | il passaggio non è nella matrice, o va nello stato di cessazione senza una data di fine arrivata |
| `E_DOC_PREZZO_PENDENTE` | 1119 | verso lo stato di emissione, un prezzo in attesa |
| `E_DOC_PREZZO_RIFIUTATO` | 1120 | verso lo stato di emissione, un prezzo rifiutato |

Gli altri motivi sono quelli delle check citate nella tabella delle regole.

---

### Test

* `db/pgtap/vendite/test-contratto-stati-dal-vocabolario-v1.sql` — con `cessazione` spostata, la
  condizione sulla data segue la marca;
* `db/pgtap/vendite/test-contratto-attiva-spento-se-sovrapposto-v1.sql` — il sovrapposto, nel
  guard e nella capability.
