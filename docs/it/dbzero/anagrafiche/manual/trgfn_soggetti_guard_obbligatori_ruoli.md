## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_guard_obbligatori_ruoli`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la tabella su cui è montato
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — i ruoli che controlla
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — gli indirizzi dei ruoli
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_guard_indirizzi_obbligatori_ruolo) — il controllo di un ruolo
> * [anagrafiche.fn_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_ruolo) — il requisito, che dipende dalla natura
> * [anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required](/dbzero/anagrafiche/funzioni/trgfn_soggetti_ruoli_guard_indirizzi_required) — lo stesso controllo quando si scrive il ruolo
> * [anagrafiche.trgfn_soggetti_guard_indirizzi_required](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_indirizzi_required) — il gemello per gli indirizzi del soggetto

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_guard_obbligatori_ruoli` controlla, quando la natura di un soggetto cambia, che
ognuno dei suoi ruoli abbia gli indirizzi obbligatori che il requisito chiede sulla natura nuova. Il
controllo avviene alla conferma della transazione.

---

### ⭐ Il requisito di un ruolo dipende dalla natura

Che indirizzi deve avere un ruolo lo dice il suo tipo, ma sulla natura del soggetto: una riga del requisito
chiede il suo tipo se la natura lo ammette, il ripiego se ammette solo quello, niente se non ammette nessuno
dei due (`anagrafiche.fn_indirizzi_obbligatori_ruolo`). Lo stesso ruolo, su un privato e su una ditta, può
quindi chiedere indirizzi diversi, e un cambio di natura può lasciarlo incompleto senza che nessun
indirizzo sia stato toccato. Gli altri guard del requisito scattano quando si scrive il ruolo o un suo
indirizzo; questo copre la strada che resta, il cambio della natura.

Gli indirizzi che la natura nuova **vieta** non li guarda: quelli sono un motivo della regola del cambio, e lo
fermano prima.

---

### Come controlla

* Scatta dopo un UPDATE di `anagrafiche.soggetti` in cui la natura cambia davvero, come constraint trigger
  **differito**: si giudica lo stato alla conferma, e dentro la transazione si possono aggiungere gli
  indirizzi che la natura nuova chiede prima o dopo averla cambiata.
* Guarda ogni ruolo del soggetto, in ordine di id, con `anagrafiche.fn_guard_indirizzi_obbligatori_ruolo`, la
  sede unica del controllo del ruolo: al primo indirizzo mancante del primo ruolo incompleto rifiuta.
* Un ruolo cancellato nella stessa transazione non si guarda.

---

{% include-markdown "it/dbzero/anagrafiche/_cambio-di-natura.md" %}

---

### ⚠️ Che cosa oggi non copre

* **Il nome del trigger dice immediato.** Il trigger è differito, ma il suo nome porta la fascia dei guard
  immediati (`a10`) invece di quella dei differiti, che hanno gli altri constraint trigger della tabella.

---

### Codici errore

* `E_INDIRIZZO_OBBLIGATORIO_MANCANTE` — un ruolo non ha un indirizzo che il requisito chiede sulla natura
  nuova; la frase nomina il ruolo e il tipo richiesto col suo ripiego. Lo solleva
  `anagrafiche.fn_guard_indirizzi_obbligatori_ruolo`.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-ripiego-e-cancellazione-v1.sql` — il trigger differito sugli
  eventi giusti; su un requisito costruito (la consegna obbligatoria per il fornitore e vietata al privato):
  il privato che non ha niente da dare, il passaggio a ditta senza la consegna sul ruolo rifiutato con la
  frase che nomina ruolo e indirizzo, e lo stesso passaggio con la consegna scritta nella stessa transazione,
  che passa.

---

### Note di migrazione

* 2026-11-17 — nasce nel giro che porta il requisito del ruolo sulla natura del soggetto («vale il
  ripiego») in una sede sola, insieme ai controlli alla cancellazione di un indirizzo e al cambio del suo tipo
  (`brief-db-fornitore-privato-indirizzi`).

---

{% include-markdown "signature-core.md" %}
