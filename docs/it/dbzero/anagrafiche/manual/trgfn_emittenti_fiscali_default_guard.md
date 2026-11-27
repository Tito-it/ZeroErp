## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_emittenti_fiscali_default_guard`

> **Ultimo aggiornamento**: 27 novembre 2026
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

La predefinita si sposta cambiando l'azienda della sua riga, e lì le predefinite restano una. La riga non si
cancella e non diventa il collegamento di un billing account (`E_BA_COLLEGAMENTO_NON_SI_TOGLIE`,
`E_BA_COLLEGAMENTO_NON_SI_SPOSTA`), quindi una predefinita che c'è non sparisce. Il controllo guarda lo stato
finale perché è un constraint trigger differito: dentro la transazione del primo emittente la predefinita
arriva dopo l'emittente. L'indice unico parziale `uq_emittenti_fiscali_ba_default` tiene «al massimo una» riga
dopo riga; questo controllo aggiunge «almeno una». Con la riga che non si cancella né si sposta, «nessuna
predefinita» la raggiunge solo una via di servizio che spegne quei rifiuti: il controllo è la rete.

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
* `db/pgtap/anagrafiche/test-emittenti-fiscali-default-singleton-v1.sql` — la predefinita tolta dalla via di
  servizio è rifiutata (`E_EMITTENTE_DEFAULT_SINGLETON`), la seconda la ferma l'indice. Gira col runner owner: la
  via di servizio spegne un trigger, e solo il proprietario può farlo.

---

{% include-markdown "signature-core.md" %}
