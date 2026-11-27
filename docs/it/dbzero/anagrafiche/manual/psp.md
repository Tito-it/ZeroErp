## 📘 Documentazione Concettuale – Tabella `anagrafiche.psp`

> **Ultimo aggiornamento**: 27 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo `PSP` a cui la riga si aggancia
> * [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso) — i canali d'incasso, che chiedono un PSP censito, e acceso se il canale è acceso
> * [config.sistema_codici](/dbzero/config/tabelle/sistema_codici) — il catalogo dei formati, da cui nasce il codice
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_psp_guard_ruolo_psp](/dbzero/anagrafiche/funzioni/trgfn_psp_guard_ruolo_psp) — il ruolo dev'essere `PSP`
> * [anagrafiche.trgfn_psp_guard_enti_incasso_attivi](/dbzero/anagrafiche/funzioni/trgfn_psp_guard_enti_incasso_attivi) — il PSP con canali accesi non si spegne
> * [pagamenti.trgfn_enti_incasso_guard_psp](/dbzero/pagamenti/funzioni/trgfn_enti_incasso_guard_psp) — il canale acceso vuole il PSP acceso
>
> Guide:
>
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — dove il PSP entra negli incassi
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — le specializzazioni, col ruolo che non si sposta
> * [Numerazione dei documenti e dei codici](/guide/numerazione-documenti-e-codici) — il catalogo dei formati

---

### 🎯 Scopo Principale

`anagrafiche.psp` è la specializzazione del ruolo **PSP** (`PSP`): il prestatore di servizi di pagamento, il
gateway o processore esterno da cui arriva un flusso d'incasso.

---

### Una riga per ruolo, con un codice

La riga nomina con `soggetto_ruolo_id` il legame «questo soggetto è un PSP», uno per ruolo (`uq_psp_ruolo`); che
il legame sia del ruolo `PSP` lo controlla il guard di ruolo. Il ruolo **non si cambia**
(`E_SPECIALIZZAZIONE_SOGGETTO_IMMUTABILE`): un PSP creato sul soggetto sbagliato si spegne e se ne crea uno giusto.

Il **codice** lo genera il database quando manca, dal catalogo dei formati: `PSP-` e sette cifre. È unico, si salva
in forma normalizzata (`script.trgfn_codice_maiuscolo`) e **non si cambia** (`E_CODICE_NON_MODIFICABILE`). `uid`
è l'identificativo esterno; `meta` raccoglie dati liberi che il database non legge.

Il PSP **non si cancella** (`E_DELETE_NOT_ALLOWED`): si spegne. Lo storico è continuo: `storicizza` nasce vero e la
tabella è fra quelle di `config.storico_set_storicizza`, che lo tengono acceso.

---

### ⭐ Il PSP e i suoi canali d'incasso

Un canale d'incasso di tipo PSP, in `pagamenti.enti_incasso`, nomina un ruolo `PSP`. I due versi:

* **il canale acceso vuole il PSP acceso**: un canale nasce, si riaccende o cambia ruolo solo su un PSP censito e
  acceso (`pagamenti.trgfn_enti_incasso_guard_psp`). Un canale spento si modifica anche col PSP spento;
* **il PSP con canali accesi non si spegne** (`E_PSP_ENTI_INCASSO_ATTIVI`): prima si spengono i canali, poi il PSP.
  Il controllo conta i canali di ogni azienda, anche quelli che chi agisce non vede.

Il canale nomina il ruolo, non la riga dei PSP: nessuna chiave esterna punta alla tabella, perché il ruolo del
canale è polimorfo. Per questo i due versi li tengono due guard scritti a mano, e non l'automazione dello
spegnimento.

---

### Codici errore

* `E_SOGGETTI_RUOLI` — il ruolo non è `PSP`.
* `E_SPECIALIZZAZIONE_SOGGETTO_IMMUTABILE` — si cerca di cambiare il ruolo.
* `E_CODICE_NON_MODIFICABILE` — si cerca di cambiare il codice.
* `E_DELETE_NOT_ALLOWED` — si cerca di cancellarlo.
* `E_PSP_ENTI_INCASSO_ATTIVI` — si cerca di spegnerlo con canali accesi.

---

### Test

* `db/pgtap/anagrafiche/test-ruoli-impresa-psp-vettore-gestore-v1.sql` — il codice generato e bloccato, il ruolo
  bloccato, la cancellazione rifiutata, i due versi coi canali d'incasso.
* `db/pgtap/pagamenti/test-enti-incasso-psp.sql` — la nascita di un PSP, e il canale rifiutato quando il ruolo non
  ha una riga qui.

---

{% include-markdown "signature-core.md" %}
