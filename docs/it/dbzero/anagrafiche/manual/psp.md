## 📘 Documentazione Concettuale – Tabella `anagrafiche.psp`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo `PSP` a cui la riga si aggancia
> * [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso) — i canali d'incasso, che chiedono un PSP censito e attivo
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_psp_guard_ruolo_psp](/dbzero/anagrafiche/funzioni/trgfn_psp_guard_ruolo_psp) — il ruolo dev'essere `PSP`
> * [pagamenti.trgfn_enti_incasso_guard_psp](/dbzero/pagamenti/funzioni/trgfn_enti_incasso_guard_psp) — l'unico che legge la tabella
>
> Guide:
>
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — dove il PSP entra negli incassi

---

### 🎯 Scopo Principale

`anagrafiche.psp` è la specializzazione del ruolo **PSP** (`PSP`): il prestatore di servizi di pagamento, il
gateway o processore esterno da cui arriva un flusso d'incasso.

---

### Una riga per ruolo, con un codice

La riga nomina con `soggetto_ruolo_id` il legame «questo soggetto è un PSP», uno per ruolo (`uq_psp_ruolo`); che
il legame sia del ruolo `PSP` lo controlla il guard di ruolo. Il **codice** è obbligatorio, unico e non vuoto, e
si salva in forma normalizzata (`script.trgfn_codice_maiuscolo`), così l'unicità non distingue le maiuscole. Non
ha un generatore: lo scrive chi crea il PSP. `uid` è l'identificativo esterno; `meta` raccoglie dati liberi che il
database non legge.

Lo storico è continuo: `storicizza` nasce vero e la tabella è fra quelle di `config.storico_set_storicizza`, che
lo tengono acceso.

---

### ⭐ Il PSP serve agli enti d'incasso

Un ente d'incasso di tipo PSP, in `pagamenti.enti_incasso`, nomina un ruolo `PSP`, e nasce o si modifica solo se
quel ruolo ha qui una riga **attiva**: lo controlla `pagamenti.trgfn_enti_incasso_guard_psp`. È l'unico oggetto
del database che legga la tabella, e il solo punto in cui `attivo` conta.

Anche qui l'ente nomina il ruolo, non la riga dei PSP: nessuna chiave esterna punta alla tabella, e l'automazione
dello spegnimento non monta niente.

---

### ⚠️ Che cosa oggi non copre

* **Lo spegnimento e la cancellazione sono liberi.** A differenza delle altre specializzazioni, la cancellazione
  non passa dalla porta di manutenzione, e nessun controllo guarda gli enti d'incasso: un PSP spento, o
  cancellato, lascia attivi gli enti che lo nominano, che restano validi finché non si riscrivono. La filiale
  bancaria, l'altra controparte di un ente d'incasso, ha invece la chiave esterna, e non si spegne con enti
  attivi.
* **Il codice si può cambiare.** Non ha il lucchetto di colonna che hanno i codici delle sorelle.

---

### Codici errore

* `E_SOGGETTI_RUOLI` — il ruolo non è `PSP`.

---

### Test

* `db/pgtap/pagamenti/test-enti-incasso-psp.sql` — la nascita di un PSP, e l'ente d'incasso rifiutato quando il
  ruolo non ha una riga qui.

---

{% include-markdown "signature-core.md" %}
