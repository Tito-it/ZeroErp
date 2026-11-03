## 📘 Documentazione Concettuale – Procedura `maintenance.proc_bump_indirizzi_dettaglio`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — le righe che la procedura rinormalizza
> * [config.stradario](/dbzero/config/tabelle/stradario) — la via a cui puntano, quella che è cambiata
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_indirizzi_dettaglio_protect_update](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_dettaglio_protect_update) — il guard su `stradario_id`, che questa procedura non deve aprire
> * [anagrafiche.trgfn_indirizzi_dettaglio_normalize](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_dettaglio_normalize) — il trigger che ricalcola i campi normalizzati
> * [anagrafiche.fn_build_indirizzo_normalizzato](/dbzero/anagrafiche/funzioni/fn_build_indirizzo_normalizzato) — la regola della normalizzazione, in una sede sola
> * [anagrafiche.trgfn_indirizzi_dettaglio_guard_chiave](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_dettaglio_guard_chiave) — la chiave dell'indirizzo, giudicata dopo la normalizzazione
> * [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic) — lo storico, sulle righe che lo chiedono
>
> Guide:
>
> * [Riclassificazione vie e toponomastica](/guide/riclassificazione-vie) — la procedura operativa in cui si inserisce

---

### 🎯 Scopo Principale

Rinormalizza tutti gli indirizzi di dettaglio che puntano a una via (`stradario_id`) dopo che
la via è cambiata, con un aggiornamento neutro che fa ripartire i trigger di normalizzazione.

Il nome della via di un indirizzo non sta sull'indirizzo: `via_norm` e `indirizzo_normalizzato`
si calcolano dallo stradario quando la riga viene scritta. Se lo stradario cambia — per esempio
la via passa a un altro nome dello stradario generale — gli indirizzi che ci puntano restano con
il testo vecchio, perché nessuno li ha riscritti. Questa procedura li riscrive.

---

### Un aggiornamento che non cambia niente, perché i trigger ricalcolino tutto

La procedura riscrive su ogni riga di `anagrafiche.indirizzi_dettaglio` con lo `stradario_id`
indicato lo stesso `stradario_id` che già c'è. Il valore non cambia, ma l'aggiornamento c'è: i
trigger `BEFORE UPDATE` della tabella girano, e il trigger di normalizzazione ricalcola dallo
stradario di oggi la via normalizzata, il civico normalizzato e l'indirizzo completo, oltre a
ripulire estensione, palazzina, scala, piano e interno.

⚠️ La normalizzazione può cambiare anche le colonne della chiave dell'indirizzo, se una riga
vecchia non era ancora nella forma di oggi. In quel caso il guard della chiave giudica la riga
come un aggiornamento qualsiasi, e un doppione fa fallire la procedura intera.

Una via senza indirizzi, o un `p_stradario_id` nullo, non aggiornano niente e non sollevano
errori.

---

### ⛔ Non apre la porta di manutenzione, perché non la attraversa

Il guard dell'aggiornamento su `anagrafiche.indirizzi_dettaglio` blocca un solo gesto: il
**cambio** di `stradario_id`, cioè spostare un indirizzo su un'altra via. L'aggiornamento di
questa procedura riscrive lo stesso `stradario_id`, quindi il guard non scatta, e la procedura
non accende il flag `zeroerp.maintenance_indirizzi_dettaglio` che lo aprirebbe. Una porta aperta
che nessuno attraversa sarebbe solo un'apertura in più: il flag vale per la transazione, e
lasciato acceso farebbe passare senza guard ogni spostamento successivo nella stessa
transazione.

Il guard continua a riconoscere il flag: è la porta pronta per il verbo che sposterà gli
indirizzi su un'altra via, quando nascerà. Oggi quel verbo non c'è, e questa procedura non lo fa.

---

### Lo storico registra solo le righe che lo chiedono

L'aggiornamento attraversa anche il trigger di storico della tabella, che però scrive solo per
le righe con `storicizza = true`: il default di `anagrafiche.indirizzi_dettaglio` è `false`. Su
una riga che non lo chiede, la rinormalizzazione non lascia traccia in `storico`.

---

### Gira coi diritti di chi la chiama

La procedura è `SECURITY INVOKER`: aggiorna solo le righe che chi la chiama vede e può scrivere.
Non ha un job pgAgent. Si lancia a mano, come passo della riclassificazione di una via, dopo aver
aggiornato lo stradario; e la chiama `maintenance.proc_bump_toponomastica`, una volta per ogni via
il cui nome di strada usa il toponimo corretto, nella stessa transazione.

---

### Test

`db/pgtap/config/test-stradario-riclassificazione-unico.sql` — il cambio di nome completo di una
via: aggiorna lo stradario, chiama la procedura, e verifica che `via_norm` e
`indirizzo_normalizzato` degli indirizzi coinvolti tornino coerenti con lo stradario nuovo. Poi
prova che, **dopo** la procedura e nella stessa transazione, il cambio a mano di `stradario_id`
è ancora rifiutato dal guard. Chiude con lo storico dello stradario.

`db/pgtap/maintenance/test-bump-toponomastica-v1.sql` — prova che, dopo la procedura, il flag
degli indirizzi non è acceso nella stessa transazione, e che la cascata di
`maintenance.proc_bump_toponomastica` porta la descrizione nuova del toponimo in `via_norm` e in
`indirizzo_normalizzato` di un indirizzo di dettaglio.

---

### Note di migrazione

* 2026-01-02 — nasce, insieme al guard su `stradario_id`.
* 2026-08-06 — il flag torna a `off` prima di uscire, anche in errore. Prima restava acceso fino
  alla fine della transazione, e la cosa reggeva solo perché la procedura veniva chiamata da sola,
  in autocommit; l'ha trovata il passaggio dei pgTAP in transazione
  (`brief-db-pgtap-runner-rls-baseline` §18.2).
* 2026-11-03 — la procedura non accende più il flag: il suo aggiornamento non cambia lo
  `stradario_id`, e il guard non lo avrebbe bloccato comunque. Il verbo che sposta gli indirizzi
  su un'altra via, a cui il flag serve, non si costruisce ora (`brief-db-revisione-maintenance`
  D8).
* 2026-11-03 — la chiama anche `maintenance.proc_bump_toponomastica`, per ogni via del toponimo
  corretto (`brief-db-revisione-maintenance` D9).

---

{% include-markdown "signature-core.md" %}
