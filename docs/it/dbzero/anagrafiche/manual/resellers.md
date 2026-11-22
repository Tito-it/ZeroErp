## 📘 Documentazione Concettuale – Tabella `anagrafiche.resellers`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo `RE` a cui la riga si aggancia
> * [anagrafiche.resellers_billing_account](/dbzero/anagrafiche/tabelle/resellers_billing_account) — i billing account del reseller
> * [config.sistema_codici](/dbzero/config/tabelle/sistema_codici) — i generatori di codice, dove il reseller non c'è
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_resellers_guard_ruolo_reseller](/dbzero/anagrafiche/funzioni/trgfn_resellers_guard_ruolo_reseller) — il ruolo dev'essere `RE`
> * [anagrafiche.trgfn_resellers_guard_attivo](/dbzero/anagrafiche/funzioni/trgfn_resellers_guard_attivo) — lo spegnimento col reseller in uso
> * [anagrafiche.trgfn_resellers_normalize](/dbzero/anagrafiche/funzioni/trgfn_resellers_normalize) — il trigger che non fa niente
> * [vendite.fn_build_fattura_key](/dbzero/vendite/funzioni/fn_build_fattura_key) — chi legge il reseller per la fattura
>
> Guide:
>
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il modello soggetto, ruolo, specializzazione

---

### 🎯 Scopo Principale

`anagrafiche.resellers` è la specializzazione del ruolo **reseller** (`RE`): il rivenditore che intermedia la vendita,
e a cui si legano, per periodo, i billing account che ha portato.

---

### Una riga per ruolo, un codice che non cambia

La riga nomina con `soggetto_ruolo_id` il legame «questo soggetto è un reseller», uno per ruolo
(`uq_resellers_ruolo`); che il legame sia del ruolo `RE` lo controlla il guard di ruolo.

Il **codice** è obbligatorio, unico e non vuoto. Si salva in forma normalizzata (`script.trgfn_codice_maiuscolo`),
così l'unicità non distingue le maiuscole, e dopo la nascita non si modifica (`script.trgfn_lock_columns`). Il
codice lo scrive chi crea il reseller: nessun trigger lo genera, e `config.sistema_codici` non ha una riga per i
reseller.

`uid` è l'identificativo esterno, per le integrazioni; `meta` raccoglie dati liberi che il database non legge.

---

### Lo spegnimento e la cancellazione

* **Spegnere** (`attivo` a falso) è rifiutato finché il reseller ha anche un solo legame con un billing account,
  di qualunque periodo: lo dice `anagrafiche.trgfn_resellers_guard_attivo`.
* **Cancellare** passa solo dalla porta di manutenzione del migratore (`script.trgfn_delete_block_by_guc`): un
  reseller si spegne, non si toglie.

Lo storico è continuo: `storicizza` nasce vero e la tabella è fra quelle di `config.storico_set_storicizza`, che
lo tengono acceso, così ogni modifica e ogni cancellazione lasciano la versione precedente.

---

### ⚠️ Che cosa oggi non copre

* **Il codice non ha un generatore.** È obbligatorio, e chi crea il reseller deve inventarlo; il database non ha
  un verbo di creazione.
* **Il legame non punta alla tabella.** `anagrafiche.resellers_billing_account` nomina il ruolo, non la riga dei
  reseller: un legame può nascere verso un reseller spento, o verso un ruolo che non ha la riga qui (vedi la
  scheda del legame).
* **Uno spegnimento impossibile.** Il guard conta anche i legami chiusi: un reseller che ha avuto clienti si spegne
  solo cancellandone la storia.
* `anagrafiche.trgfn_resellers_normalize` scatta a ogni scrittura e non fa niente.

---

### Codici errore

* `E_SOGGETTI_RUOLI` — il ruolo non è `RE`.
* `E_RESELLER_DISATTIVAZIONE_BLOCCATA` — lo spegnimento con legami.
* `E_CODICE_NON_MODIFICABILE` — il codice cambiato dopo la nascita.
* `E_DELETE_NOT_ALLOWED` — una cancellazione fuori dalla porta di manutenzione.

---

{% include-markdown "signature-core.md" %}
