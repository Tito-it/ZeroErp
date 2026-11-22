## 📘 Documentazione Concettuale – Tabella `anagrafiche.gestori_utilities`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.gestori](/dbzero/anagrafiche/tabelle/gestori) — il gestore
> * [config.utilities](/dbzero/config/tabelle/utilities) — il catalogo dei servizi
> * [anagrafiche.emittenti_fiscali_utilities](/dbzero/anagrafiche/tabelle/emittenti_fiscali_utilities) — la tabella gemella dell'emittente, che porta i parametri per servizio

---

### 🎯 Scopo Principale

`anagrafiche.gestori_utilities` dice quali servizi (le utility di `config.utilities`) il gestore del sistema
gestisce: una riga per coppia gestore e servizio.

---

### Una coppia, una volta

La coppia gestore e servizio è unica (`uq_gestore_utility`). Il ruolo non compare: il gestore è già un ruolo, e
la riga lo nomina attraverso la sua specializzazione. Il commento della tabella parla ancora di un «ruolo
funzionale» e la chiave primaria si chiama `pk_gestori_utilities_ruoli`: sono nomi di un modello di prima, e
nessuna colonna li porta.

`meta` raccoglie i parametri della coppia in forma libera; il database non ne legge niente.

---

### Che cosa la tabella non regge

La tabella ha due chiavi esterne e l'audit, e nessun trigger di dominio:

* la cancellazione di una riga è libera; quella di un servizio usato si ferma sulla chiave esterna, come quella
  del gestore (che però è già bloccata a monte);* non ha storico.

---

### ⚠️ Che cosa oggi non copre

* **Nessun oggetto del database legge la tabella.** Il perimetro dei servizi del gestore non limita niente: un
  cliente, un'istanza, un listino di un servizio che il gestore non dichiara nascono lo stesso.

---

{% include-markdown "signature-core.md" %}
