## 📘 Documentazione Concettuale – Tabella `anagrafiche.fornitori`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo `FO` di cui la riga è la specializzazione
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — l'identità del fornitore, lo split payment
> * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari) — l'instradamento della fatturazione elettronica
> * [config.stati_fornitore](/dbzero/config/tabelle/stati_fornitore) — lo stato, e se blocca gli ordini
> * [config.termini_pagamento](/dbzero/config/tabelle/termini_pagamento) — giorni, fine mese e rate del pagamento
> * [config.regimi_fiscali](/dbzero/config/tabelle/regimi_fiscali) — il catalogo dei regimi RF
> * [anagrafiche.soggetti_ruoli_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari) — i conti bancari del ruolo
>
> Approfondimento viste:
>
> * [anagrafiche.vw_fornitori_dettaglio](/dbzero/anagrafiche/views/vw_fornitori_dettaglio) — il fornitore in una riga, sorgente della lista
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_fornitore](/dbzero/anagrafiche/funzioni/fn_crea_fornitore) — la porta che fa di un soggetto un fornitore
> * [anagrafiche.trgfn_fornitori_guard_ruolo_fornitore](/dbzero/anagrafiche/funzioni/trgfn_fornitori_guard_ruolo_fornitore) — il ruolo dev'essere `FO`
> * [anagrafiche.trgfn_fornitori_guard_normalize](/dbzero/anagrafiche/funzioni/trgfn_fornitori_guard_normalize) — la coerenza della ritenuta d'acconto
> * [anagrafiche.trgfn_fornitori_gen_codice](/dbzero/anagrafiche/funzioni/trgfn_fornitori_gen_codice) — il codice, quando non è passato
> * [anagrafiche.fn_guard_fornitore_attivo](/dbzero/anagrafiche/funzioni/fn_guard_fornitore_attivo) — il fornitore utilizzabile, con rifiuto
> * [anagrafiche.fn_check_fornitore_attivo](/dbzero/anagrafiche/funzioni/fn_check_fornitore_attivo) — la stessa domanda, senza rifiuto
>
> Guide:
>
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il soggetto, i ruoli e le loro specializzazioni
> * [Termini di pagamento](/guide/termini-di-pagamento) — il termine che il fornitore condivide col cliente

---

### 🎯 Scopo Principale

`anagrafiche.fornitori` è la specializzazione del **ruolo fornitore** (`FO`): per ogni ruolo, le impostazioni con
cui l'azienda compra da quel soggetto (pagamento, ritenuta, regime fiscale), lo stato del fornitore e la sua
qualifica.

---

### Una riga per ruolo, non per soggetto

La riga punta al ruolo (`soggetto_ruolo_id`), non al soggetto, e un ruolo ha al più un fornitore
(`uq_fornitori_soggetto_ruolo_id`). L'identità sta sul soggetto, i dati del rapporto qui: lo stesso soggetto può
essere cliente e fornitore senza che niente si scriva due volte. Che il ruolo sia proprio `FO` lo garantisce
`anagrafiche.trgfn_fornitori_guard_ruolo_fornitore`.

Si nasce fornitore da `anagrafiche.fn_crea_fornitore`, che crea il ruolo se manca, scrive la riga nello stato «in
verifica» (`VE`) e porta con sé il contatto e gli indirizzi del ruolo.

---

### Che cosa sta qui e che cosa no

* **Il pagamento**: valuta, modalità e termine. È la stessa base del cliente; giorni, fine mese, rate e intervallo
  sono del termine, non del fornitore.
* **La ritenuta d'acconto**: con la ritenuta serve un'aliquota maggiore di zero, e senza ritenuta l'aliquota si
  azzera (`anagrafiche.trgfn_fornitori_guard_normalize`).
* **Il regime fiscale** (`regime_fiscale_rf`): il codice RF del tracciato FatturaPA, nella stessa forma
  dell'emittente. È facoltativo, perché un privato non ne ha.
* **La qualifica**: `rating`, un punteggio da 0 a 100 (`chk_fornitori_rating`), e `qualifica_scadenza`, la data
  in cui la qualifica va rinnovata. Il database le conserva e non le usa.
* **Non stanno qui**, perché sono del soggetto e valgono per ogni suo ruolo: lo split payment
  (`anagrafiche.soggetti`) e l'instradamento della fatturazione elettronica (codice destinatario, PEC:
  `anagrafiche.dati_societari`). Neanche i conti bancari: si legano al ruolo in
  `anagrafiche.soggetti_ruoli_conti_bancari`, o al soggetto.

---

### Lo stato e l'abilitazione

`attivo` dice se il fornitore è abilitato; lo **stato** (`stato_fornitore_id`) dice a che punto è il rapporto, e lo
stato porta il flag `blocca_ordini`. Un fornitore si può usare quando è attivo e il suo stato non blocca gli ordini:
è la domanda di `anagrafiche.fn_guard_fornitore_attivo` (che rifiuta) e di `anagrafiche.fn_check_fornitore_attivo`
(che risponde sì o no).

---

### ⭐ Un riferimento spento non si assegna a un fornitore acceso

Lo stato, il termine di pagamento e il regime fiscale hanno un `attivo` loro, e la coppia ATTIVO del framework li
lega al fornitore: un fornitore acceso non riceve un riferimento spento (`E_ATTIVO_PADRE_NON_ATTIVO`, col campo nel
contesto), e un riferimento che un fornitore acceso usa non si spegne (`E_ATTIVO_BLOCK_CHILDREN_ACTIVE`). Un
fornitore spento tiene il suo riferimento anche se si spegne, ma per riaccenderlo gliene serve uno acceso. Il
controllo è differito alla conferma. Per il regime la coppia lega la chiave esterna anche se la colonna non finisce
in `_id`.

---

### Il codice

Il codice è obbligatorio e unico (`uq_fornitori_codice`). Chi scrive può passarlo; se non lo passa, lo genera
`anagrafiche.trgfn_fornitori_gen_codice` dalla riga `fornitori` di `config.sistema_codici`, nella forma
`FORN0000001`. Si salva in maiuscolo, e dopo la nascita non cambia più (`E_CODICE_NON_MODIFICABILE`).

---

### Un fornitore non si cancella: si disattiva

La cancellazione è bloccata (`trg_fornitori_a10_delete_block_dlt`): si apre solo dalla porta di manutenzione dei
ruoli. Ogni modifica e ogni cancellazione lasciano la versione precedente nello storico, quando `storicizza` è
acceso.

---

### ⚠️ Che cosa oggi non copre

* **Il ruolo del fornitore si può cambiare.** `soggetto_ruolo_id` non è bloccato: una riga si può spostare sul
  ruolo `FO` di un altro soggetto, e porta con sé codice, stato e storia.
* **Il COMMENT di `rating` dice «0-100 o 1-5».** La scala è una sola, da 0 a 100, ed è quella del vincolo.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-fornitore-v1.sql` — la nascita: ruolo nuovo o riusato, stato `VE`, codice
  generato, campi estranei rifiutati, il secondo fornitore sullo stesso ruolo rifiutato dal vincolo unico.
* `db/pgtap/anagrafiche/test-fornitore-privato-indirizzi-v1.sql` — il fornitore privato e i suoi indirizzi.
* `db/pgtap/ui/test-lista-fornitori-seed.sql` — la lista configurabile sulla vista di dettaglio.

---

### Note di migrazione

* 2026-11-21 — escono dalla tabella i campi che doppiavano il soggetto (lo split payment e l'instradamento della
  fatturazione elettronica), e il regime fiscale prende il nome `regime_fiscale_rf`, legato al catalogo dei regimi.

---

{% include-markdown "signature-core.md" %}
