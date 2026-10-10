## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_efba_guard_istanza_emittente`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_guard_istanza_ba_emittente](/dbzero/anagrafiche/manual/fn_guard_istanza_ba_emittente)
>
[anagrafiche.fn_guard_istanza_ba_gestore_globale](/dbzero/anagrafiche/manual/fn_guard_istanza_ba_gestore_globale)
>
[anagrafiche.trgfn_efba_guard_albero_emittente](/dbzero/anagrafiche/manual/trgfn_efba_guard_albero_emittente) — il gemello sull'albero

---
### 🎯 Scopo Principale
(latest review 08-10-26)

Fa scattare il controllo «un'istanza, un'azienda» quando cambia l'azienda a cui
un billing account e' collegato.

---

### I movimenti

Sono gli stessi che controlla il gemello sull'albero:

| # | Cosa succede | Effetto |
| --- | --- | --- |
| 1 | si **crea** il collegamento (anche alla nascita del billing account) | il billing account prende un'azienda |
| 2 | si **modifica** il collegamento | il billing account cambia azienda |
| 3 | si **cancella** il collegamento | ricade sull'azienda predefinita, senza che nessuno abbia scritto un'azienda |
| 4 | si sposta l'**azienda predefinita** | cambiano insieme tutti i billing account senza collegamento |

Per 1-3 controlla il billing account toccato; per 4 chiama
[`fn_guard_istanza_ba_gestore_globale`](/dbzero/anagrafiche/manual/fn_guard_istanza_ba_gestore_globale).

---

### Contesto di Esecuzione

* **Trigger**: `trg_emittenti_fiscali_ba_z95_guard_istanza_ef_ins_upd_dlt`,
  `AFTER INSERT OR UPDATE OR DELETE`
* Deve girare **dopo** la scrittura: il controllo rilegge il collegamento per
  risolvere l'azienda.
* Lo spostamento di un collegamento resta sotto il cancello della storia
  ([`trgfn_efba_guard_storia_emittente`](/dbzero/anagrafiche/manual/trgfn_efba_guard_storia_emittente)):
  i due controlli si sommano.
