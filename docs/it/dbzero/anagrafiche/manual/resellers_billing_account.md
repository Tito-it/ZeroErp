## 📘 Documentazione Concettuale – Tabella `anagrafiche.resellers_billing_account`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.resellers](/dbzero/anagrafiche/tabelle/resellers) — il reseller
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il billing account portato
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_resellers_guard_attivo](/dbzero/anagrafiche/funzioni/trgfn_resellers_guard_attivo) — il reseller con legami non si spegne
> * [script.trgfn_guard_date_validita](/dbzero/script/funzioni/trgfn_guard_date_validita) — la fine non precede l'inizio
> * [vendite.fn_build_fattura_key](/dbzero/vendite/funzioni/fn_build_fattura_key) — chi mette il reseller sulla fattura

---

### 🎯 Scopo Principale

`anagrafiche.resellers_billing_account` lega un billing account al reseller che l'ha portato, per un periodo. Il
legame è sempre esplicito: un billing account senza riga qui non ha reseller, e non esiste un reseller di
ripiego.

---

### Il legame nomina il ruolo, e ha un periodo

* `reseller_soggetto_ruolo_id` nomina il **ruolo** del reseller in `anagrafiche.soggetti_ruoli`, non la riga di
  `anagrafiche.resellers`.
* `valido_dal` e `valido_al` sono il periodo, con **tutti e due i giorni inclusi**; senza fine il legame è aperto.
  L'inizio, se non passato, è il giorno operativo (`script.fn_data_operativa`). Che la fine non preceda l'inizio
  lo dice `script.trgfn_guard_date_validita` con un codice proprio, prima che il calcolo di `validita` risponda
  con un errore tecnico.
* `validita` è il periodo come intervallo, calcolato dalle due date.
* `meta` raccoglie dati liberi che il database non legge.

Il legame si cancella liberamente e non ha storico.

---

### Chi lo legge

Nel database la leggono in due:

* `vendite.fn_build_fattura_key`, che mette sulla fattura il reseller del billing account;
* `anagrafiche.trgfn_resellers_guard_attivo`, che rifiuta lo spegnimento del reseller finché ne esiste un legame,
  di qualunque periodo.

---

### ⚠️ Che cosa oggi non copre

* **Il periodo non vincola e non si legge.** Nessuna unicità né esclusione sui periodi: due reseller sullo stesso
  billing account negli stessi giorni sono ammessi, e `validita` non è usata da nessun vincolo. La fattura prende
  il primo legame per ordine di nascita, senza guardare il periodo: un legame chiuso vale come uno aperto, e di
  due legami vale il più vecchio.
* **Il ruolo non è controllato.** Nessun guard dice che il ruolo nominato sia un reseller: la chiave esterna
  accetta un ruolo di qualunque tipo, anche senza la riga in `anagrafiche.resellers`.
* **Il reseller spento.** Lo spegnimento con legami è rifiutato, ma un legame nuovo verso un reseller già spento
  nasce.

---

### Codici errore

* `E_DATA_AL_MINORE_DAL` — la fine del periodo precede l'inizio.

---

{% include-markdown "signature-core.md" %}
