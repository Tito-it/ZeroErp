## 📘 Documentazione Concettuale – Tabella `anagrafiche.vettori`

> **Ultimo aggiornamento**: 27 novembre 2026
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
> * [vendite.trgfn_ddt_guard_vettore_attivo](/dbzero/vendite/funzioni/trgfn_ddt_guard_vettore_attivo) — la bolla sceglie un vettore acceso
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
 Il ruolo **non si cambia** (`E_SPECIALIZZAZIONE_SOGGETTO_IMMUTABILE`): un vettore creato sul
soggetto sbagliato si spegne e se ne crea uno giusto.

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

Il documento di trasporto nomina il vettore col ruolo (`vendite.ddt.vettore_soggetto_ruolo_id`), con una chiave
esterna verso questa tabella (`soggetto_ruolo_id`): il vettore di una bolla è un vettore, non un ruolo qualunque.
Quando la bolla lo sceglie o lo cambia deve essere acceso (`E_DDT_VETTORE_NON_ATTIVO`,
`vendite.trgfn_ddt_guard_vettore_attivo`). La bolla di riconsegna eredita il vettore della bolla d'origine solo se è
acceso: spento, nasce in bozza col vettore vuoto (`vendite.fn_genera_ddt_riconsegna`).

⭐ **La bolla è storia.** Un vettore spento dopo resta sulle bolle che lo hanno già, e quelle bolle si modificano
come prima. Per questo la chiave esterna è un'eccezione dell'automazione dello spegnimento
(`dbops.automazione_attivo_eccezioni`): senza, un vettore che ha portato anche una sola bolla non si spegnerebbe
più.

---

### ⚠️ Che cosa oggi non copre

* **Un trigger che non fa niente.** `trg_vettori_norm_ins_upd` scatta a ogni scrittura e non cambia la riga.

---

### Test

* `db/pgtap/anagrafiche/test-vettori-gen-codice.sql` — la riga di configurazione, la sequenza, la funzione e il
  trigger del codice; il codice generato nella forma attesa e poi non modificabile.
* `db/pgtap/anagrafiche/test-ruoli-impresa-psp-vettore-gestore-v1.sql` — il ruolo bloccato, la chiave esterna della
  bolla, il vettore spento che una bolla non sceglie e che si spegne anche se ha portato bolle.

---

### Note di migrazione

* 2026-08-21 — nasce la riga `vettori` di `config.sistema_codici`, e con essa il codice generato. Prima il codice
  era obbligatorio ma nessuno lo generava: un inserimento senza codice cadeva sul `NOT NULL`.

---

{% include-markdown "signature-core.md" %}
