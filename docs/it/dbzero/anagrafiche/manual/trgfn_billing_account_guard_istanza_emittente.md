## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_billing_account_guard_istanza_emittente`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_guard_istanza_ba_emittente](/dbzero/anagrafiche/manual/fn_guard_istanza_ba_emittente)
>
[anagrafiche.trgfn_efba_guard_istanza_emittente](/dbzero/anagrafiche/manual/trgfn_efba_guard_istanza_emittente)

---
### 🎯 Scopo Principale
(latest review 08-10-26)

Quando nasce un billing account, verifica che appartenga alla stessa azienda
emittente degli altri billing account della sua istanza.

---

### Contesto di Esecuzione

* **Trigger**: `trg_billing_account_z95_guard_istanza_emittente_ins`, `AFTER INSERT`
* **Dopo** il collegamento all'azienda: l'azienda del billing account nuovo
  nasce dal collegamento creato da `trg_billing_account_z90_link_ef_ins`, che
  scatta prima (z90 < z95). Prima di lui, il controllo leggerebbe l'azienda
  predefinita al posto di quella vera.

---

### Perche' solo alla nascita

Istanza e utility di un billing account non cambiano dopo la nascita (blocco di
colonna): un billing account non cambia fratelli. La sua azienda cambia solo dal
collegamento, controllato da
[`trgfn_efba_guard_istanza_emittente`](/dbzero/anagrafiche/manual/trgfn_efba_guard_istanza_emittente).
