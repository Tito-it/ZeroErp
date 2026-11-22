## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_billing_account_require_istanza_ha_ba`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — la tabella su cui è montata
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_istanza_ha_ba](/dbzero/anagrafiche/funzioni/fn_guard_istanza_ha_ba) — il controllo a cui delega
> * [anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata](/dbzero/anagrafiche/funzioni/trgfn_istanze_utilities_require_utility_dichiarata) — lo stesso controllo, alla nascita dell'istanza
>
> Guide:
>
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility#ogni-istanza-nasce-col-suo-billing-account) — ogni istanza nasce col suo billing account

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_billing_account_require_istanza_ha_ba` impedisce di cancellare l'ultimo billing account di
un'istanza che resta.

---

### Al commit, non subito

È un constraint trigger dopo la cancellazione, differito al commit: a quel punto chiede a
`fn_guard_istanza_ha_ba` se l'istanza del billing account cancellato ha ancora un billing account, e se non ce
l'ha l'operazione è rifiutata con `E_ISTANZA_SENZA_BA`.

Al commit, perché cancellare un'istanza intera insieme ai suoi billing account resta lecito: un controllo
immediato rifiuterebbe già il primo billing account cancellato, quando l'istanza c'è ancora; al commit
l'istanza non esiste più e non c'è niente da controllare.

È la seconda metà della regola «istanza e billing account vivono insieme»: la prima, alla nascita dell'istanza,
la tiene il trigger dell'istanza con lo stesso controllo; lo spostamento di un billing account su un'altra
istanza lo chiude il blocco di colonna.

---

### Codici errore

* `E_ISTANZA_SENZA_BA` — da `fn_guard_istanza_ha_ba`, al commit.

---

### Test

* `db/pgtap/anagrafiche/test-istanza-nasce-col-ba-v1.sql` — l'ultimo billing account di un'istanza che resta
  non si cancella; istanza e billing account se ne vanno insieme.

---

### Note di migrazione

* 2026-10-08 — nasce: fino ad allora la regola si guardava solo alla nascita dell'istanza, e un billing account
  si poteva cancellare lasciando l'istanza sola.

---

{% include-markdown "signature-core.md" %}
