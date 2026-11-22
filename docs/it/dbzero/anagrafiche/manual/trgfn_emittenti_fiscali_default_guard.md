## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_emittenti_fiscali_default_guard`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — la tabella su cui scatta, con la riga della predefinita
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — le aziende dell'installazione
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_emittenti_fiscali_default_bootstrap](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_default_bootstrap) — scrive la predefinita al primo emittente

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_emittenti_fiscali_default_guard` controlla al COMMIT che l'installazione abbia una e una sola
azienda predefinita, appena ha un emittente. Scatta su ogni scrittura dei collegamenti fra billing account e
azienda, e solleva `E_EMITTENTE_DEFAULT_SINGLETON` col numero di predefinite trovate.

---

### ⭐ Perché al COMMIT

Il modo naturale di spostare la predefinita è cambiare l'azienda della sua riga, e lì le predefinite restano una.
Chi invece toglie la riga e ne scrive un'altra passa, a metà transazione, da zero predefinite: il trigger è un
constraint trigger differito, e guarda solo lo stato finale. L'indice unico parziale
`uq_emittenti_fiscali_ba_default` tiene «al massimo una» riga dopo riga; questo controllo aggiunge «almeno una».

---

### L'installazione vuota

Un'installazione senza emittenti e senza predefinita passa: è lo stato prima del primo emittente, che porta con
sé la predefinita (`anagrafiche.trgfn_emittenti_fiscali_default_bootstrap`). Appena esiste un emittente, acceso o
spento, la predefinita è obbligatoria.

---

### Codici errore

* `E_EMITTENTE_DEFAULT_SINGLETON` — al COMMIT le predefinite non sono una; il segnaposto è quante sono.

---

### Test

* `db/pgtap/anagrafiche/test-emittenti-fiscali.sql` — dopo il primo emittente esiste una sola predefinita.

Il rifiuto al COMMIT non è provato da un test proprio.

---

{% include-markdown "signature-core.md" %}
