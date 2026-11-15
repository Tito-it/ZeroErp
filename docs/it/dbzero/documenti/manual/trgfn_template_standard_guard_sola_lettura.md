## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_template_standard_guard_sola_lettura`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) — il modello standard
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — le sue versioni
>
> Approfondimento funzioni:
>
> * [script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella) — chi scrive è il proprietario della tabella?
> * [documenti.fn_personalizza_template_standard](/dbzero/documenti/funzioni/fn_personalizza_template_standard) — la strada per un modello diverso
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — la registrazione dell'errore
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — il modello standard e «personalizza»

---

### 🎯 Scopo Principale

Tiene il **modello standard e le sue versioni in sola lettura per l'applicazione**: li scrive solo il
proprietario della tabella, cioè il seed e i changeSet. È montata
`BEFORE INSERT OR UPDATE OR DELETE` su `documenti.template_documenti` e su
`documenti.template_documenti_versioni`, nella fase `a05`, prima degli altri guard e del default
dell'azienda.

---

### ⭐ Lo standard evolve in un posto solo

Lo standard vale per ogni azienda che non ha un modello suo: se l'applicazione potesse cambiarlo,
un'azienda cambierebbe la stampa di tutte le altre. Le evoluzioni le portano gli aggiornamenti del
sistema, che scrivono sullo standard e non sulle copie. Chi vuole un modello diverso lo personalizza
per la sua azienda.

---

### Quando una riga è dello standard

* **Sul modello**: conta la riga di prima (UPDATE, DELETE) e quella di dopo (INSERT, UPDATE). Così
  l'applicazione non crea uno standard, non modifica né cancella uno standard, e non trasforma un suo
  modello in standard.
* **Su una versione**: conta il modello a cui appartiene, prima e dopo. Così l'applicazione non
  aggiunge, modifica o cancella versioni di uno standard, e non sposta una sua versione sotto uno
  standard.

Se la riga è dello standard e chi scrive non è il proprietario della tabella, la scrittura è
rifiutata. I modelli delle aziende e le loro versioni non li tocca.

Parlando per primo, il rifiuto dice la cosa giusta anche quando un altro vincolo fermerebbe comunque
la scrittura (il CHECK dell'azienda, il lock di `standard`).

---

### Codici errore

* `E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA` — scrittura dall'applicazione su uno standard o su una
  sua versione. Il messaggio porta il codice del modello; il contesto l'operazione, la tabella e il
  ruolo.

---

### Test

* `db/pgtap/documenti/test-documenti-template-standard-app-v1.sql` — come applicazione: non crea uno
  standard, non trasforma un suo modello in standard, non modifica, non cancella e non aggiunge
  versioni a uno standard; risolve lo standard e scrive i modelli della sua azienda come prima.

---

### Note di migrazione

* 2026-10-20 — nasce con il modello standard.

---

{% include-markdown "signature-core.md" %}
