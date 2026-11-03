## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_pdp`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp) — il punto di prelievo, dato di macchina
> * [config.utilities](/dbzero/config/tabelle/utilities) — l'utility, scelta per `codice_interno`
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_crea_indirizzo_dettaglio](/dbzero/dbops/funzioni/fn_pgtap_crea_indirizzo_dettaglio) — l'indirizzo nuovo su cui il punto nasce
> * [anagrafiche.trgfn_pdp_set_default_stato](/dbzero/anagrafiche/funzioni/trgfn_pdp_set_default_stato) — lo stato iniziale, che la fixture non sceglie
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — i dati di macchina si costruiscono, non si pescano

---

### 🎯 Scopo Principale

Un punto di prelievo nuovo per un test, su un indirizzo suo, per l'utility scelta per
`codice_interno` (default `GAS`). Torna il punto, il suo codice, l'utility e l'indirizzo.

---

### ⭐ Il punto di prelievo è dato di macchina: si costruisce

`anagrafiche.pdp` su un database ricostruito è vuota: un test che ne pesca uno non trova
niente.

---

### ⭐ Un numero libero, e da lui due cose nuove

Il codice del punto è unico su tutta la tabella, e un solo punto per utility può stare su un
indirizzo. La fixture prende il primo numero libero fra i codici `PGTAPPDP` più sei cifre, e
da quel numero ricava sia il codice sia l'etichetta dell'indirizzo: entrambi nuovi, quindi
le due unicità sono rispettate per costruzione.

⚠️ L'indirizzo va nuovo apposta:
[fn_pgtap_crea_indirizzo_dettaglio](/dbzero/dbops/funzioni/fn_pgtap_crea_indirizzo_dettaglio)
torna lo stesso indirizzo per la stessa etichetta, troncata a 10 caratteri, e l'etichetta
numerata della fixture ci sta intera.

Il massimo si legge su tutta la tabella: `anagrafiche.pdp` non è sotto la sicurezza per riga.
Lo stato iniziale del punto lo mette il trigger di default.

---

### 🚫 Cosa non scrive

Il cliente e l'istanza sul punto di prelievo: sono il caso del test.

---

### Codici errore

Un'utility che non è a catalogo è un'eccezione senza codice, sollevata dalla fixture. Valgono
i guard del punto di prelievo.

---

### Test

Nessun pgTAP dedicato: la usano come fixture i test della catena istanza–punto di prelievo e
della sincronizzazione cliente–punto e del subentro in `db/pgtap/anagrafiche/`, e quello della disdetta in
`db/pgtap/script/`.

---

### Note di migrazione

* 2026-09-23 — nasce (`brief-db-fixture-che-costruiscono-giro-2`).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
