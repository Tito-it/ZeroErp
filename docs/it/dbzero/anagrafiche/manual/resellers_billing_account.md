## 📘 Documentazione Concettuale – Tabella `anagrafiche.resellers_billing_account`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [anagrafiche.resellers](/dbzero/anagrafiche/tabelle/resellers)  
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  
>
🎯 Scopo Principale

(latest review 26-01-2026)
La tabella **`anagrafiche.resellers_billing_account`** gestisce l’associazione tra
**billing_account** e **reseller** (ruolo), con validita` temporale. Non prevede
un emittente “di default”: il legame e` sempre esplicito.

---

### Campi chiave

* `billing_account_id` → riferimento al cliente operativo.
* `reseller_soggetto_ruolo_id` → ruolo reseller collegato.
* `valido_dal` / `valido_al` → periodo di validita` del legame.

---

### Regole principali

* nessun **fallback** automatico: il reseller va sempre associato in modo esplicito;
* `valido_al` (se presente) deve essere ≥ `valido_dal`.

---

{% include-markdown "signature-core.md" %}
