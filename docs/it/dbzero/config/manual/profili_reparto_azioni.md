## 📘 Documentazione Concettuale – Tabella `config.profili_reparto_azioni`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
Tabelle correlate:
>
[config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative)
> [config.azioni_processo](/dbzero/config/tabelle/azioni_processo)
> [config.user_override_azioni](/dbzero/config/tabelle/user_override_azioni)

---

La tabella **`config.profili_reparto_azioni`** definisce le **azioni di processo abilitate** a livello di reparto.

Come per le aree, l'ereditarietà è automatica: tutti gli operatori del reparto ereditano le abilitazioni configurate.

---

### 🎯 Scopo Principale

* Definire quali **azioni di processo** sono abilitate per ogni reparto.
* Consentire la gestione centralizzata delle abilitazioni critiche.
* Le eccezioni individuali sono gestite in `config.user_override_azioni`.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `unita_organizzativa_id` | Reparto (FK → `config.unita_organizzative`) |
| `azione_id` | Azione di processo (FK → `config.azioni_processo`) |
| `abilitata` | Azione concessa (`true`) o negata (`false`) per il reparto |

---

### ⚠️ Default

Se un'azione non ha riga per il reparto, è **negata** (default sicuro). Il campo `abilitata` con default `false` consente anche di creare righe esplicitamente negate per documentare la scelta.

---

> **"`config.profili_reparto_azioni` controlla le operazioni critiche a livello di reparto, con override individuali possibili tramite `user_override_azioni`."**
