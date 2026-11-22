## 📘 Documentazione Concettuale – Tabella `anagrafiche.istanze_dati_precontrattuali`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza dei dati
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — la coppia (istanza, utility) che i dati richiedono
> * [config.classi_utenze](/dbzero/config/tabelle/classi_utenze) — la classe d'utenza, da cui viene il tipo
> * [config.tipi_utenze](/dbzero/config/tabelle/tipi_utenze) — il tipo d'utenza, letto attraverso la classe
> * [vendite.contratti_utilities](/dbzero/vendite/tabelle/contratti_utilities) — il contratto che congela i dati
> * [storico.istanze_dati_precontrattuali](/dbzero/storico/tabelle/istanze_dati_precontrattuali) — le versioni di prima
>
> Approfondimento viste:
>
> * [anagrafiche.vw_istanze_dati_precontrattuali_dettaglio](/dbzero/anagrafiche/views/vw_istanze_dati_precontrattuali_dettaglio) — i dati con l'istanza e le decodifiche
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_istanze_dati_precontrattuali_protect_update](/dbzero/anagrafiche/funzioni/trgfn_istanze_dati_precontrattuali_protect_update) — il blocco dopo il contratto
> * [script.fn_get_ba_id_da_coppia](/dbzero/script/funzioni/fn_get_ba_id_da_coppia) — il BA della coppia, per la policy
>
> Guide:
>
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility) — l'istanza e i suoi billing account

---

### 🎯 Scopo Principale

`anagrafiche.istanze_dati_precontrattuali` raccoglie i dati tecnici di una fornitura per una sua utility:
la classe d'utenza, due parametri di uso comune e le estensioni proprie della utility. Il contratto li
legge e, da quel momento, non si cambiano più.

---

### Una riga per coppia (istanza, utility), e solo col suo billing account

La chiave è la coppia (`uq_istanze_dati_precontrattuali_id_utility_id`): una fornitura ha al più una riga di
dati per ogni utility. La coppia deve essere quella di un billing account (`fk_idp_billing_account_coppia`):
i dati precontrattuali sono dati, non dichiarano la utility dell'istanza, e senza il BA di quella utility
non esistono.

---

### I campi

* `classe_utenza_id` — la classe d'utenza; il tipo d'utenza non sta sulla riga, si legge dalla classe.
* `param_1_num` e `param_2_txt` — due parametri di uso comune, per esempio la potenza impegnata e la
  tensione o la pressione. Il numero è finito (`chk_istanze_dati_precontrattuali_param_1_num_finito`).
* `meta` — le estensioni proprie della utility, in JSONB.

---

### ⛔ Dopo il contratto non si toccano

Quando un contratto utility ha letto la riga (`vendite.contratti_utilities` la nomina), la riga non si
modifica e non si cancella (`E_COLONNA_NON_MODIFICABILE`): il contratto resta coerente con i dati su cui è
nato, e una correzione passa da un contratto nuovo. Finché nessun contratto la nomina, si modifica e si
cancella; ogni versione di prima va nello storico, quando `storicizza` è acceso.

---

### Visibilità per azienda

La tabella ha la RLS: la vede e la scrive solo un operatore, quando l'azienda emittente del billing account
della coppia è nel suo perimetro (`rls_istanze_dati_precontrattuali_ef_whitelist`). Il perimetro si calcola
una volta per istruzione; il BA della coppia lo trova `script.fn_get_ba_id_da_coppia`, che non dipende dalla
RLS del BA. Chi non ha la veste di operatore non vede niente. La vista di dettaglio è `security_invoker`, e
non scavalca la regola.

---

### ⚠️ Che cosa oggi non copre

* **Il blocco guarda solo i contratti.** Anche un'offerta commerciale nomina la riga
  (`vendite.offerte_commerciali_utilities`): la cancellazione la ferma la chiave esterna, la modifica passa,
  e l'offerta si ritrova dati diversi da quelli su cui è nata.
* **Il rifiuto non nomina un campo.** Il blocco risponde con il codice di una colonna non modificabile anche
  per una cancellazione, e senza il campo da evidenziare nel form.

---

### Codici errore

* `E_COLONNA_NON_MODIFICABILE` — modifica o cancellazione di una riga che un contratto nomina.

---

### Test

* `db/pgtap/anagrafiche/test-istanze-dati-precontrattuali.sql` — le chiavi esterne verso istanza, utility e
  classe.
* `db/pgtap/anagrafiche/test-istanza-nasce-col-ba-v1.sql` — la chiave esterna verso la coppia del BA.
* `db/pgtap/vendite/test-contratti-utilities-snapshot.sql` — il contratto che legge la riga, e la modifica
  bloccata dopo.
* `db/pgtap/rls/test-rls-istanze-dati-precontrattuali-v1.sql` — la policy, la vista che non scavalca, la
  scrittura sulla coppia di un'altra azienda rifiutata, chi non ha veste che non vede niente.

---

### Note di migrazione

* 2026-10-08 — nascono la chiave esterna verso la coppia del BA e la RLS; prima una riga di dati bastava a
  far nascere un'istanza senza billing account.
* 2026-10-21 — la policy trova il BA con `script.fn_get_ba_id_da_coppia` e calcola il perimetro una volta per
  istruzione.

---

{% include-markdown "signature-core.md" %}
