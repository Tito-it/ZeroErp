## 📘 Documentazione Concettuale – Tabella `anagrafiche.vettori`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo `VT` di cui la riga è la specializzazione
> * [config.sistema_codici](/dbzero/config/tabelle/sistema_codici) — la forma del codice del vettore
> * [vendite.ddt](/dbzero/vendite/tabelle/ddt) — il documento di trasporto, che nomina il vettore
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_vettori_guard_ruolo_vettore](/dbzero/anagrafiche/funzioni/trgfn_vettori_guard_ruolo_vettore) — il ruolo dev'essere `VT`
> * [anagrafiche.trgfn_vettori_gen_codice](/dbzero/anagrafiche/funzioni/trgfn_vettori_gen_codice) — il codice, quando non è passato
> * [anagrafiche.trgfn_vettori_normalize](/dbzero/anagrafiche/funzioni/trgfn_vettori_normalize) — agganciato, non fa niente
>
> Guide:
>
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il soggetto, i ruoli e le loro specializzazioni
> * [Gestione DDT](/guide/gestione-ddt) — il documento su cui compare il vettore

---

### 🎯 Scopo Principale

`anagrafiche.vettori` è la specializzazione del **ruolo vettore** (`VT`): chi trasporta la merce. Ogni riga è il
vettore di un ruolo, col suo codice, la descrizione e lo stato di abilitazione.

---

### Una riga per ruolo, non per soggetto

La riga punta al ruolo (`soggetto_ruolo_id`), non al soggetto, e un ruolo ha al più un vettore
(`uq_vettori_ruolo`). Lo stesso soggetto può essere cliente, fornitore e vettore: tre ruoli, ognuno con la sua
specializzazione. Che il ruolo sia proprio `VT` lo garantisce `anagrafiche.trgfn_vettori_guard_ruolo_vettore`.

---

### Il codice

Il codice è obbligatorio, unico e non vuoto (`uq_vettori_codice`, `chk_vettori_codice_non_vuoto`). Chi scrive può
passarlo; se non lo passa, lo genera `anagrafiche.trgfn_vettori_gen_codice` dalla riga `vettori` di
`config.sistema_codici`, nella forma `VET-0000001`. Si salva in maiuscolo (`script.trgfn_codice_maiuscolo`), e dopo
la nascita non cambia più: il lock della colonna risponde `E_CODICE_NON_MODIFICABILE`.

---

### Un vettore non si cancella: si disattiva

La cancellazione è bloccata (`trg_vettori_a10_delete_block_dlt`): si apre solo dalla porta di manutenzione dei
ruoli. Un vettore che non si usa più si spegne con `attivo`. Ogni modifica e ogni cancellazione lasciano la versione
precedente nello storico, quando `storicizza` è acceso.

---

### Il vettore del DDT

Il documento di trasporto nomina il vettore col **ruolo** (`vendite.ddt.vettore_soggetto_ruolo_id`), non con la
riga di questa tabella: la chiave esterna va a `anagrafiche.soggetti_ruoli`.

---

### ⚠️ Che cosa oggi non copre

* **Il vettore del DDT non è controllato come vettore.** La colonna del DDT accetta qualunque ruolo: nessun
  controllo chiede che sia di tipo `VT`, che abbia una riga in questa tabella o che quella riga sia attiva. Un
  vettore spento resta indicabile su un DDT nuovo.
* **Il COMMENT di `soggetto_ruolo_id` dice «ruolo atteso: RES».** Il ruolo atteso è `VT`, ed è quello che il guard
  controlla.
* **Un trigger che non fa niente.** `trg_vettori_norm_ins_upd` scatta a ogni scrittura e non cambia la riga.

---

### Test

* `db/pgtap/anagrafiche/test-vettori-gen-codice.sql` — la riga di configurazione, la sequenza, la funzione e il
  trigger del codice; il codice generato nella forma attesa e poi non modificabile.

---

### Note di migrazione

* 2026-08-21 — nasce la riga `vettori` di `config.sistema_codici`, e con essa il codice generato. Prima il codice
  era obbligatorio ma nessuno lo generava: un inserimento senza codice cadeva sul `NOT NULL`.

---

{% include-markdown "signature-core.md" %}
