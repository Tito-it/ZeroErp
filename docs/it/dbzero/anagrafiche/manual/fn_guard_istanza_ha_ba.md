## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_istanza_ha_ba`

> **Ultimo aggiornamento**: 26 novembre 2026
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
> * [script.trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic) — il rifiuto della cancellazione di un billing account, che chiude l'altra strada
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
istanza): è un dato fuori regola. Le strade per arrivarci sono tre, e ognuna ha il suo presidio:

* **nasce un'istanza senza billing account** — è la strada di questa funzione: la chiama, al commit, il
  trigger della nascita dell'istanza (`anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata`);
* **si cancella l'ultimo billing account di un'istanza** — non può succedere: il billing account non si
  cancella mai (`E_BA_NON_SI_CANCELLA`, il primo trigger sulla cancellazione), e un cliente che non si vuole
  più si annulla;
* **si sposta il billing account su un'altra istanza** — lo chiude il blocco di colonna
  (`E_BA_ISTANZA_IMMUTABILE`).

Il chiamante è differito al commit: dentro la stessa transazione l'istanza può essere scritta prima del suo
billing account. Un'istanza che non esiste più, o un parametro vuoto, non hanno niente da presidiare.

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
  commit; il billing account non si cancella, né da solo né insieme alla sua istanza.
* `db/pgtap/anagrafiche/test-trgfn-istanze-utilities-require-utility-dichiarata.sql` — la nascita dell'istanza.

---

### Note di migrazione

* 2026-10-08 — nasce con la regola «istanza e billing account nascono insieme, sempre». La chiamava anche un
  constraint trigger differito sulla cancellazione di un billing account, che rifiutava l'ultimo di un'istanza
  rimasta e ammetteva istanza e billing account cancellati insieme.
* 2026-11-26 — quel trigger e la sua funzione sono ritirati: il billing account non si cancella più, e la
  strada della cancellazione è chiusa del tutto. La funzione resta per la nascita dell'istanza.

---

{% include-markdown "signature-core.md" %}
