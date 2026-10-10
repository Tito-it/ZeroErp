## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_billing_account_require_istanza_ha_ba`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_guard_istanza_ha_ba](/dbzero/anagrafiche/manual/fn_guard_istanza_ha_ba)

---
### 🎯 Scopo Principale
(latest review 08-10-26)

Impedisce di cancellare **l'ultimo** billing account di un'istanza che resta.

---

### Contesto di Esecuzione

* **Trigger**: `trg_billing_account_z90_require_istanza_ha_ba_dlt`, constraint
  trigger `AFTER DELETE`, **differito alla conferma** dell'operazione
* **Logica**: chiama [`fn_guard_istanza_ha_ba`](/dbzero/anagrafiche/manual/fn_guard_istanza_ha_ba)
  sull'istanza del billing account cancellato

---

### Perche' alla conferma, e non subito

Cancellare un'istanza **intera**, insieme ai suoi billing account, resta
lecito. Un controllo immediato rifiuterebbe gia' la cancellazione del primo
billing account, quando l'istanza c'e' ancora; alla conferma, invece, l'istanza
non esiste piu' e non c'e' niente da controllare.

---

### Perche' esiste

Fino al 2026-10-08 l'unico controllo guardava la **nascita** dell'istanza. La
regola dice «sempre»: senza questo trigger un billing account si poteva
cancellare e lasciare l'istanza sola.
