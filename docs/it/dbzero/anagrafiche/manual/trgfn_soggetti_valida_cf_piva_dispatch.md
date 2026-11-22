## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la tabella che il controllo presidia
> * [config.stati](/dbzero/config/tabelle/stati) — lo stato del soggetto, che sceglie il validatore
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — la natura, che dice il formato atteso
>
> Approfondimento funzioni:
>
> * [script.fn_validate_cf_piva_it](/dbzero/script/funzioni/fn_validate_cf_piva_it) — il validatore italiano
> * [script.fn_valida_codice_fiscale](/dbzero/script/funzioni/fn_valida_codice_fiscale) — il codice fiscale di una persona
> * [script.fn_valida_partita_iva](/dbzero/script/funzioni/fn_valida_partita_iva) — la partita IVA, e il codice fiscale numerico
> * [anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_cf_piva_obbligatori) — la presenza di CF e P.IVA

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch` controlla il formato del codice fiscale e della partita IVA
di un soggetto, col validatore del suo stato. Oggi esiste solo quello italiano: per gli altri stati non controlla
niente.

---

### Lo stato sceglie il validatore, la natura il formato

Il trigger legge il codice ISO2 dello stato del soggetto e, per l'Italia, passa a `script.fn_validate_cf_piva_it`
la natura e i tre campi fiscali. Il validatore italiano:

* **la partita IVA** e quella del **gruppo d'acquisto**, se scritte e se la natura prevede una partita IVA, le
  controlla con la cifra di controllo;
* **il codice fiscale**, se scritto e se la natura lo prevede, lo controlla secondo il formato della natura: a
  sedici caratteri per una persona fisica, a undici cifre (come una partita IVA) per una società o un ente. Un
  formato per cui non c'è un algoritmo si accetta.

Che i campi ci siano non è affar suo: lo dice `anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori`. Senza
natura il controllo non ha un formato da applicare, e tace.

Il trigger viene, per nome, dopo quello che dà lo stato proposto: un soggetto scritto senza stato si controlla
già con lo stato che riceve.

---

### ⚠️ Che cosa oggi non copre

* **Uno stato senza validatore passa in silenzio.** Non c'è un ramo per gli altri paesi, né un errore che dica
  che il controllo non è stato fatto.
* **Ricontrolla a ogni modifica**, anche quando CF e P.IVA non cambiano. Un soggetto il cui codice scritto il
  validatore non accetta più non si modifica in niente finché il codice non si corregge, e il codice scritto lo
  corregge solo il SUPER_ADMIN.
* **Una natura che non esiste** dà un errore tecnico del validatore (nessuna riga trovata) prima che parli la
  chiave esterna.
* **Forma**: il trigger non ha la fascia nel nome (`trg_soggetti_valida_cf_piva_dispatch_ins_upd`), e la
  variabile dello stato non è ancorata al tipo della colonna `config.stati.codice_iso2`.

---

### Codici errore

Dal validatore italiano:

* `E_PIVA_NON_VALIDA` — partita IVA, o partita IVA del gruppo d'acquisto, con la cifra di controllo sbagliata.
  Il campo dell'errore è quello sbagliato.
* `E_CF_NON_VALIDO` — codice fiscale che non rispetta il formato della natura. Il campo dell'errore è
  `codice_fiscale`.

---

{% include-markdown "signature-core.md" %}
