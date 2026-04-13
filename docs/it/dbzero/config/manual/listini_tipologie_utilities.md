## 📘 Documentazione Concettuale – Tabella `config.listini_tipologie_utilities`

> 👀 **Vedi anche**
>
Tabelle:
>
[config.listini_tipologie](/dbzero/config/manual/listini_tipologie)
> [config.utilities](/dbzero/config/tabelle/utilities)
> [vendite.listini](/dbzero/vendite/tabelle/listini)
>
Funzioni:
>
[trgfn_listini_guard_tipologia_utility](/dbzero/vendite/manual/trgfn_listini_guard_tipologia_utility)

---
### 🎯 Scopo Principale

Matrice di ammissibilita` N:M tra utility e tipologie listino. Definisce quali combinazioni `(utility_id, tipologia_id)` sono valide per la creazione di listini. Impedisce combinazioni incoerenti (es. un listino Gas con tipologia PRODOTTI).

---

### Campi chiave (semantica)

| Colonna | Note |
| --- | --- |
| `utility_id` | FK a `config.utilities` |
| `tipologia_id` | FK a `config.listini_tipologie` |
| `attivo` | Se `false` la combinazione e` disabilitata senza cancellare la riga |

---

### Vincoli

* **`uq_listini_tipologie_utilities`**: UNIQUE su `(utility_id, tipologia_id)` — una sola riga per coppia.

---

### Pattern

Analogo a `config.utilities_tipi_ruolo` — matrice N:M con flag `attivo`. La validazione e` imposta da un trigger guard su `vendite.listini` (`trgfn_listini_guard_tipologia_utility`) che verifica la coppia ad ogni INSERT/UPDATE.

---

### Seed iniziale

| Utility | Tipologie ammesse |
| --- | --- |
| Gas (1) | CONSUMO, QUOTA_FISSA, IMPOSTA, ONERE_SISTEMA |
| Energia (2) | CONSUMO, QUOTA_FISSA, IMPOSTA, ONERE_SISTEMA |
| Idrico (3) | CONSUMO, QUOTA_FISSA, IMPOSTA |
| Teleriscaldamento (4) | CONSUMO, QUOTA_FISSA, IMPOSTA |
| Base (5) | PRODOTTI, SERVIZI |

Per aggiungere una nuova combinazione basta un INSERT nella matrice — nessuna migration DDL necessaria.

---

{% include-markdown "signature-core.md" %}
