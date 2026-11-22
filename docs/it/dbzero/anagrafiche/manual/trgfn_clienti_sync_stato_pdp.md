## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_clienti_sync_stato_pdp`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — la tabella su cui scatta
> * [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp) — il punto di prelievo di cui aggiorna lo stato
> * [config.stati_pdp](/dbzero/config/tabelle/stati_pdp) — gli stati tecnici del PDP
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_pdp_occupato](/dbzero/anagrafiche/funzioni/fn_check_pdp_occupato) — la domanda «il PDP è occupato in questo giorno?»
> * [anagrafiche.trgfn_clienti_set_periodo](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_periodo) — il periodo del cliente, la misura dell'occupazione
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — il giorno operativo

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_clienti_sync_stato_pdp` porta lo stato tecnico del PDP dietro ai suoi clienti: un PDP
disponibile che ha un cliente nel giorno operativo diventa attivo, un PDP attivo che non ne ha più torna
disponibile.

---

### ⭐ Lo stato segue l'occupazione, non lo stato del cliente

La domanda è una sola: nel giorno operativo un cliente occupa il PDP, cioè il suo periodo contiene quel giorno?
La risponde `anagrafiche.fn_check_pdp_occupato`, con la stessa misura del vincolo per cui un PDP ha un solo
cliente alla volta. Così un sospeso tiene il PDP attivo, un cliente chiuso lo libera dal giorno della chiusura,
un annullato (che non ha periodo) lo libera subito.

La lettura conta i clienti di tutte le aziende: lo stato del PDP è uno solo, anche se chi scrive vede solo i
suoi clienti.

---

### Che cosa tocca

* **Solo i passaggi fra disponibile e attivo** (`DISP` e `ATT`). Un PDP tecnicamente staccato (`DTEC`) o
  dismesso (`DISM`) resta com'è: quello stato lo decide chi gestisce la rete, non i clienti.
* **Due PDP, quando il cliente cambia PDP**: quello nuovo e quello lasciato, ognuno ricalcolato per conto suo.

Scatta dopo la nascita del cliente e dopo le modifiche che nominano lo stato, il PDP, l'attivazione o la
chiusura. Un cliente senza PDP, prima e dopo, non fa niente.

---

### ⚠️ Che cosa oggi non copre

* **Lo stato segue il giorno della scrittura, non il calendario.** Un cliente con l'attivazione o la chiusura in
  un giorno futuro cambia lo stato del PDP alla prima scrittura dopo quel giorno, non quel giorno: nessun job
  ricalcola gli stati quando le date arrivano.
* **Un PDP cambiato dalla copia dell'istanza** non sempre lo ricalcola: la copia avviene in ogni scrittura del
  cliente, ma questo trigger scatta solo se la scrittura nomina una delle sue quattro colonne.

---

### Codici errore

* `E_CODICE` — gli stati `ATT` o `DISP` non sono nel catalogo degli stati del PDP.

---

### Test

* `db/pgtap/script/test-fn-disdetta-cliente.sql` — il PDP che torna disponibile dopo la disdetta.

Il passaggio da disponibile ad attivo, il cambio di PDP e i due stati che il trigger non tocca non hanno un
pgTAP che li provi.

---

### Note di migrazione

* 2026-10-14 — lo stato del PDP segue il periodo dei clienti, con `anagrafiche.fn_check_pdp_occupato`. Prima
  seguiva lo stato del cliente (attivo → PDP attivo, chiuso → PDP disponibile, senza guardare gli altri
  clienti), e leggeva sotto la RLS di chi scriveva.

---

{% include-markdown "signature-core.md" %}
