## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_valuta`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.valute](/dbzero/config/tabelle/valute) — il catalogo da cui la prende
>
> Approfondimento funzioni:
>
> * [vendite.fn_get_valuta_id](/dbzero/vendite/funzioni/fn_get_valuta_id) — la catena del dominio, di cui questa dà le radici
> * [dbops.fn_pgtap_crea_cliente_ba](/dbzero/dbops/funzioni/fn_pgtap_crea_cliente_ba) — il conto di fatturazione, prima radice
> * [dbops.fn_pgtap_crea_emittente](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente) — l'azienda, seconda radice
> * [dbops.fn_pgtap_crea_gestore](/dbzero/dbops/funzioni/fn_pgtap_crea_gestore) — il gestore, ultima radice
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — le fixture che costruiscono

---

### 🎯 Scopo Principale

Restituisce la **valuta di una fixture che non ha una catena da cui risolverla**: la prima di
`config.valute` per id. È una sede sola per una scelta che prima stava ricopiata in sette
fixture.

---

### ⭐ Chi la usa e chi no

La valuta di un documento il dominio la risolve lungo una catena
([vendite.fn_get_valuta_id](/dbzero/vendite/funzioni/fn_get_valuta_id)): quella del conto di
fatturazione, poi quella dell'azienda, poi quella del gestore. Su un database ricostruito
nessuno dei tre ce l'ha, quindi qualcuno deve dargliela:

* **la usano le radici della catena**: il conto di fatturazione, l'azienda e il gestore delle
  fixture nascono con questa valuta;
* **non la usano i documenti**: le fixture di bolla, ordine, preventivo e fattura chiedono la
  valuta alla catena, come i trigger di default, e così il documento prende quella del suo
  cliente.

Il catalogo delle valute è seed: la scelta non cambia fra un'esecuzione e l'altra.

---

### Codici errore

Un catalogo vuoto è un'eccezione senza codice: è un seed che manca, non un dato di macchina.
Non scrive niente.

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-valuta-v1.sql` — restituisce la prima valuta per id, e nessun'altra
  fixture di `dbops` legge il catalogo delle valute da sé.
* I presidi dell'ordine e della fattura controllano che il documento prenda la valuta del suo
  conto di fatturazione.

---

### Note di migrazione

* 2026-11-08 — nasce, per ritirare le sette copie della «prima valuta del catalogo» nelle
  fixture.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
