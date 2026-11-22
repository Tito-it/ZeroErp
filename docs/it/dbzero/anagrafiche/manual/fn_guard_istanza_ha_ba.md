## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_istanza_ha_ba`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza controllata
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — i billing account che deve avere
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata](/dbzero/anagrafiche/funzioni/trgfn_istanze_utilities_require_utility_dichiarata) — la chiama alla nascita dell'istanza
> * [anagrafiche.trgfn_billing_account_require_istanza_ha_ba](/dbzero/anagrafiche/funzioni/trgfn_billing_account_require_istanza_ha_ba) — la chiama alla cancellazione di un billing account
>
> Guide:
>
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility#ogni-istanza-nasce-col-suo-billing-account) — ogni istanza nasce col suo billing account

---

### 🎯 Scopo Principale

`anagrafiche.fn_guard_istanza_ha_ba` rifiuta un'istanza utility che esiste e non ha nessun billing account.

---

### ⭐ La regola: istanza e billing account nascono insieme

Un'istanza senza billing account non è una fase del ciclo di vita (non c'è una «fase prospect» con la sola
istanza): è un dato fuori regola. La regola si può rompere in due momenti, e questa funzione è il controllo di
tutti e due:

* nasce un'istanza senza billing account — la chiama, al commit, il trigger della nascita dell'istanza;
* si cancella l'ultimo billing account di un'istanza che resta — la chiama, al commit, il trigger della
  cancellazione del billing account.

Un terzo modo, spostare il billing account su un'altra istanza, non passa da qui: lo chiude il blocco di
colonna (`E_BA_ISTANZA_IMMUTABILE`).

I due chiamanti sono differiti al commit: dentro la stessa transazione l'istanza può essere scritta prima del
suo billing account, e un'istanza può andarsene insieme ai suoi billing account. Un'istanza che non esiste più,
o un parametro vuoto, non hanno niente da presidiare.

---

### Perché è privilegiata

La funzione legge `billing_account`, che ha la RLS. Con i permessi di chi scrive un billing account fuori dal
suo perimetro sarebbe invisibile, e il controllo rifiuterebbe un'istanza che il suo billing account ce l'ha.
Gira quindi coi privilegi del proprietario, con un `search_path` fissato.

---

### Codici errore

* `E_ISTANZA_SENZA_BA` — l'istanza esiste e non ha billing account; il messaggio porta il codice dell'istanza.

---

### Test

* `db/pgtap/anagrafiche/test-istanza-nasce-col-ba-v1.sql` — l'istanza senza billing account non arriva al
  commit, l'ultimo billing account non si cancella, istanza e billing account se ne vanno insieme.
* `db/pgtap/anagrafiche/test-trgfn-istanze-utilities-require-utility-dichiarata.sql` — la nascita dell'istanza.

---

### Note di migrazione

* 2026-10-08 — nasce con la regola «istanza e billing account nascono insieme, sempre».

---

{% include-markdown "signature-core.md" %}
