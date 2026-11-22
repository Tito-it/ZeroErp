## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_clienti_sync_pdp`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — la tabella di cui scrive `pdp_id`
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza da cui il PDP si copia
> * [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp) — il punto di prelievo
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_clienti_sync_utility_from_ba](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_utility_from_ba) — il PDP obbligatorio e della stessa utility
> * [anagrafiche.trgfn_clienti_sync_stato_pdp](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_stato_pdp) — lo stato del PDP, che segue i clienti

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_clienti_sync_pdp` scrive sul cliente il PDP della sua istanza, a ogni nascita e a ogni
modifica. Il PDP del cliente è una copia: un valore passato da chi scrive è sostituito.

---

### ⭐ Una copia, perché i vincoli la leggano

Il PDP sta sull'istanza. Il cliente lo ripete perché le regole che lo riguardano sono regole **del cliente**:
un PDP ha un solo cliente alla volta (`ex_clienti_no_overlap_stesso_pdp`, sul periodo del cliente), il PDP è
obbligatorio per le utility che lo richiedono e dev'essere della stessa utility. Un vincolo di esclusione legge
solo le colonne della sua riga: senza la copia non si potrebbe scrivere.

Il trigger non giudica niente. Un'istanza senza PDP lascia il cliente senza PDP, e se la utility lo richiede il
rifiuto arriva da `anagrafiche.trgfn_clienti_sync_utility_from_ba`, che per nome viene dopo e quindi legge già la
copia. Un'istanza che non esiste lascia il PDP vuoto, e risponde la chiave esterna verso l'istanza.

L'istanza del cliente non cambia dopo la nascita: la copia si rifà a ogni scrittura per seguire il PDP
dell'istanza, non un'istanza diversa.

---

### ⚠️ Che cosa oggi non copre

* **Un cambio di PDP dell'istanza arriva al cliente solo alla sua prossima scrittura.** Fino ad allora il
  cliente tiene il PDP di prima, e con lui il vincolo di esclusione e la catena delle istanze.
* **Quando la copia cambia, lo stato dei due PDP può non ricalcolarsi.** Il riallineamento dello stato del PDP
  (`anagrafiche.trgfn_clienti_sync_stato_pdp`) scatta solo sulle modifiche che nominano lo stato, il PDP o le
  date fra le colonne scritte: una modifica che tocca, per esempio, il solo termine di pagamento porta sul
  cliente il PDP nuovo e lascia i due PDP nello stato di prima.

---

### Test

* `db/pgtap/anagrafiche/test-clienti-sync-utility-pdp-policy.sql` — il cliente col PDP dell'istanza e il
  cliente senza PDP.
* `db/pgtap/anagrafiche/test-fn-crea-cliente-v1.sql` — il cliente creato su un'istanza senza PDP.

---

{% include-markdown "signature-core.md" %}
