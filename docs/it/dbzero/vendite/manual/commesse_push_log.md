## 📘 Documentazione Concettuale – Tabella `vendite.commesse_push_log`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse](/dbzero/vendite/tabelle/commesse)  
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
>
**Le due funzioni che ci scrivono:**
>
• [vendite.fn_start_commessa_push_run](/dbzero/vendite/funzioni/fn_start_commessa_push_run)  
> • [vendite.fn_close_commessa_push_run](/dbzero/vendite/funzioni/fn_close_commessa_push_run)  
>
### 🎯 Scopo Principale
`vendite.commesse_push_log` tiene il registro dei **giri** dell'orchestratore che
spinge le sorgenti verso commesse e attività: uno per corsa, non uno per riga.

---

### ⭐ Dal 2026-08-22 il giro si apre e si chiude

Prima la riga veniva scritta **alla fine** della corsa, quando l'esito era già
noto. Sembra la cosa naturale — si registra ciò che è successo — e portava con sé
due difetti che nessuno collegava al registro:

1. **all'avvio non c'era niente da citare.** L'evento di partenza scriveva
   `entity_id = 0`, che non era un segnaposto ma un identificativo *che non
   esisteva ancora*;
2. **un giro interrotto non lasciava traccia.** Se la corsa moriva a metà, non si
   scriveva nessuna riga: nessuno poteva sapere che era stata tentata.

Adesso la riga nasce **in testa**, in stato `IN_ESECUZIONE`, e la chiusura le
mette sopra il proprio esito. ⭐ La riga rimasta `IN_ESECUZIONE` è l'unica prova
che qualcosa è partito e non è tornato.

> ⚠️ **Il guadagno vale sul batch, non sul push singolo.** Il push lanciato dal
> drawer avvolge tutta la corsa in una transazione unica: se fallisce, viene
> annullata anche la riga d'apertura. Il batch gira in autocommit, e lì la traccia
> resta.

---

### Campi chiave (semantica)

* **Il giro**: `run_at` (quando è partito), `dry_run`, `source_types` (gli handler
  dichiarati all'avvio).
* **Esito**: `stato` — `IN_ESECUZIONE` finché la corsa è aperta, poi
  `COMPLETATO | PARZIALE | ERRORE` — e `durata_ms`.
* **Dettaglio**: `risultato` (`jsonb` per handler: created/updated/skipped/errors).
* **I due fili**: `correlation_id` è l'identità del **giro**, condivisa con gli
  eventi e con i tentativi dei task; `tx_id` è l'identità della **transazione**.
  Rispondono a due domande diverse — «in quale corsa» e «nella stessa scrittura» —
  e per questo servono entrambi.
* **Audit**: `data_insert`, `user_insert`, `data_update`, `user_update` (l'utente
  vero arriva dal JWT).

---

### Regole principali

* Una riga per **giro**, non per riga sorgente.
* ⚠️ **Non è più append-only**: la chiusura è un aggiornamento della stessa riga,
  e nessun veto lo impedisce. Ciò che non si fa è *riscrivere un esito già
  registrato* — la seconda chiusura viene rifiutata dalla funzione.
* `stato` vincolato ai quattro valori sopra. ⚠️ `IN_ESECUZIONE` **non è un esito**:
  chi conta i giri deve decidere cosa farne, o leggerà come aperto per sempre un
  giro che nessuno chiuderà.
* `durata_ms` opzionale ma non negativa.
* Indice su `run_at` per la consultazione recente, e uno su `correlation_id` per
  ricucire il giro con gli altri registri.

---

### Concorrenza

La concorrenza fra corse è gestita con `pg_try_advisory_lock`: non esistono
tabelle di lock applicative. ⚠️ Lo stato `IN_ESECUZIONE` **non è un lock** e non
va usato come tale — dice che quel giro è stato aperto, non che nessun altro
possa partire.

---

### Utilizzo previsto

* verificare l'esito dei giri schedulati,
* diagnosticare gli errori per handler e sorgente,
* ⭐ accorgersi dei giri **rimasti aperti**, che sono la traccia di una corsa
  interrotta,
* ricucire, tramite `correlation_id`, ciò che di quella corsa è finito negli altri
  registri.

---

{% include-markdown "signature-core.md" %}
