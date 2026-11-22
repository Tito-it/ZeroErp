## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_resellers_guard_attivo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.resellers](/dbzero/anagrafiche/tabelle/resellers) — la tabella su cui scatta
> * [anagrafiche.resellers_billing_account](/dbzero/anagrafiche/tabelle/resellers_billing_account) — i legami che contano
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — l'automazione dello spegnimento, che qui non monta niente

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_resellers_guard_attivo` rifiuta lo spegnimento di un reseller che ha legami con dei billing
account.

---

### ⭐ Scritto a mano, perché il legame non punta alla tabella

Il legame dei billing account nomina il **ruolo** del reseller, non la riga di `anagrafiche.resellers`: nessuna
chiave esterna lega le due tabelle, e l'automazione dello spegnimento (`dbops.fn_run_automations_attivo`), che
monta i suoi controlli seguendo le chiavi esterne verso un padre con `attivo`, qui non monta niente. Il guard fa a
mano la metà «il padre non si spegne»: c'è un legame verso questo ruolo?

---

### Quando scatta e che cosa conta

* Solo quando `attivo` passa da vero a falso. La riaccensione e le modifiche delle altre colonne passano.
* Basta **un** legame, di qualunque periodo: anche uno chiuso da anni ferma lo spegnimento.

---

### ⚠️ Che cosa oggi non copre

* **Il verso opposto.** L'altra metà dell'automazione, «il figlio nasce solo con il padre acceso», non ha il suo
  equivalente a mano: un legame nuovo verso un reseller già spento nasce, perché sulla tabella dei legami nessun
  trigger guarda il reseller.
* **Il legame chiuso.** Contando anche i legami finiti, un reseller che ha avuto clienti non si spegne se non
  cancellandone i legami, cioè la storia.

---

### Codici errore

* `E_RESELLER_DISATTIVAZIONE_BLOCCATA` — lo spegnimento con legami.

---

{% include-markdown "signature-core.md" %}
