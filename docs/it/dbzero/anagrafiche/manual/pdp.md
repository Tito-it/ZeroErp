## 📘 Documentazione Concettuale – Tabella `anagrafiche.pdp`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — il luogo a cui il PDP è ancorato
> * [config.utilities](/dbzero/config/tabelle/utilities) — la utility del punto
> * [config.stati_pdp](/dbzero/config/tabelle/stati_pdp) — gli stati tecnici
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — le forniture che si legano al punto
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — i clienti del punto, per periodo
> * [storico.pdp](/dbzero/storico/tabelle/pdp) — le versioni di prima
>
> Approfondimento viste:
>
> * [anagrafiche.vw_pdp](/dbzero/anagrafiche/views/vw_pdp) — il PDP con utility, stato e indirizzo
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_pdp_set_default_stato](/dbzero/anagrafiche/funzioni/trgfn_pdp_set_default_stato) — lo stato di nascita
> * [anagrafiche.trgfn_pdp_a10_guard](/dbzero/anagrafiche/funzioni/trgfn_pdp_a10_guard) — codice e indirizzo non cambiano
> * [anagrafiche.trgfn_clienti_sync_stato_pdp](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_stato_pdp) — lo stato segue l'occupazione
> * [anagrafiche.fn_check_pdp_occupato](/dbzero/anagrafiche/funzioni/fn_check_pdp_occupato) — il PDP è occupato in una data?
>
> Guide:
>
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility) — istanze e PDP

---

### 🎯 Scopo Principale

`anagrafiche.pdp` registra i punti di prelievo: punti fisici ancorati a un indirizzo, con un codice univoco
globale (POD, PDR o altro), una utility e uno stato tecnico. Il PDP esiste prima dei clienti e dopo di loro.

---

### Un punto fisico non si sposta e non cambia nome

Il codice `pdp` è unico in tutto il database (`uq_pdp_codice`) e non si modifica; l'indirizzo non si
modifica: un punto in un altro luogo è un altro PDP. Un luogo ha al più un PDP per utility
(`uq_pdp_addr_utility`), e la chiave unica (`id`, `indirizzo_dettaglio_id`) serve la chiave esterna composta
con cui l'istanza si lega solo a un PDP del suo indirizzo.

L'indirizzo e lo stato devono essere attivi, controllati al COMMIT. Un PDP non si disattiva finché un
cliente lo nomina, di qualunque stato e periodo (`E_ATTIVO_BLOCK_CHILDREN_EXIST`): `clienti` non ha la
colonna `attivo`, e il rimedio sarebbe togliere i clienti.

---

### Lo stato tecnico segue l'occupazione

Lo stato tecnico è distinto dallo stato commerciale del cliente: un punto può essere staccato con il
cliente ancora attivo, o disponibile con il cliente chiuso.

| Stato | Significato |
| --- | --- |
| `DISP` | Disponibile: presente e utilizzabile, senza cliente attivo |
| `ATT` | Attivo: in servizio con almeno un cliente |
| `DTEC` | Disattivo tecnico: lavori, sospensione, stacco |
| `DISM` | Dismesso: il punto non è più utilizzabile |

Un PDP nasce `DISP` quando chi lo crea non dice altro. Poi lo muove la scrittura dei clienti: quando nasce o
cambia un cliente del PDP (stato, PDP, date), lo stato diventa `ATT` se il PDP è occupato oggi (un cliente
il cui periodo contiene la data operativa) e torna `DISP` se non lo è più. Il calcolo vale anche per il PDP
che il cliente ha lasciato. `DTEC` e `DISM` non li tocca nessuno: sono stati che pone chi gestisce la rete.

---

### Il cliente del punto lo dice il periodo dei clienti

Chi occupa un PDP in una data lo dicono le righe di `clienti` con quel PDP e il loro periodo; due clienti
sullo stesso PDP non si sovrappongono (`ex_clienti_no_overlap_stesso_pdp`). Il PDP sulla riga del cliente è
la copia di quello della sua istanza.

---

### Storico

Ogni modifica e cancellazione lascia la versione di prima in `storico.pdp`, quando `storicizza` è acceso.
`meta` è un oggetto JSONB libero, sempre presente.

---

### ⚠️ Che cosa oggi non copre

* **`cliente_id` non lo scrive nessuno.** Il COMMENT e `vw_pdp` la presentano come «cliente corrente», ma
  nessun oggetto del database la valorizza: la scrittura dei clienti aggiorna lo stato del PDP, non questa
  colonna. Chi la legge trova il valore che vi ha scritto qualcun altro, o niente.
* **Lo stato non si ricalcola al passare dei giorni.** Si ricalcola solo quando si scrive un cliente del
  PDP: un cliente con l'attivazione futura lascia il PDP `DISP` anche dopo quella data, un cliente chiuso
  nel futuro lo lascia `ATT` anche dopo la chiusura, finché un cliente del PDP non si riscrive.
* **Due presìdi per la stessa immutabilità del codice.** Sul cambio di `pdp` scattano il guard della tabella
  e il blocco di colonna, in quest'ordine: risponde sempre il guard (`E_COLONNA_NON_MODIFICABILE`), e il
  blocco di colonna, che avrebbe `E_CODICE_NON_MODIFICABILE` e la porta di manutenzione, non parla mai.
* **Un PDP che ha avuto un cliente non si disattiva più.** Il blocco conta anche i clienti chiusi e
  annullati, che restano sulla tabella.
* **Una dismissione non chiude niente.** `DISM` non impedisce a un'istanza di legarsi al PDP né a un cliente
  di nascervi.

---

### Codici errore

* `E_COLONNA_NON_MODIFICABILE` — cambio del codice o dell'indirizzo.
* `E_ATTIVO_BLOCK_CHILDREN_EXIST` — disattivazione di un PDP che un cliente nomina.
* `E_CODICE` — alla nascita senza stato, manca lo stato `DISP` nel catalogo.

---

### Test

* `db/pgtap/anagrafiche/test-create-pdp.sql` — i PDP nascono `DISP`.
* `db/pgtap/anagrafiche/test-trgfn-pdp-a10-guard.sql` — codice e indirizzo non si cambiano.
* `db/pgtap/dbops/test-trgfn-prevent-deactivate-if-children-pdp.sql` — lo stato tecnico disattivato con PDP
  attivi.

---

### Note di migrazione

* 2026-10-14 — lo stato del PDP segue l'occupazione per periodo; prima seguiva lo stato del cliente (attivo
  o chiuso).
* Il NOT NULL di `meta` porta ancora il nome della colonna di prima, `extra_info` (`pdp_extra_info_not_null`).

---

{% include-markdown "signature-core.md" %}
