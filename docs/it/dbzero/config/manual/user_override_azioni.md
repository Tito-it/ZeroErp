## 📘 Documentazione Concettuale – Tabella `config.user_override_azioni`

> **Ultimo aggiornamento**: 27 ottobre 2026

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
Tabelle correlate:
>
[config.azioni_processo](/dbzero/config/tabelle/azioni_processo)
> [config.profili_accesso_azioni](/dbzero/config/tabelle/profili_accesso_azioni)

---

La tabella **`config.user_override_azioni`** consente di **sovrascrivere l'abilitazione di un'azione di processo** ereditata dal reparto, per un singolo utente.

---
### 🎯 Scopo Principale
* Concedere un'azione negata a livello reparto (**GRANT** individuale).
* Revocare un'azione concessa a livello reparto (**DENY** individuale).
* Supportare **validità temporale** e **motivazione** per governance.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `auth_user_id` | Utente Django (FK → `django.auth_user`) |
| `azione_id` | Azione di processo (FK → `config.azioni_processo`) |
| `abilitata` | `true` = concessa, `false` = negata (sovrascrive il reparto) |
| `motivo` | Motivazione dell'override |
| `valido_dal` / `valido_al` | Finestra temporale di validità |

---

### Casi d'uso tipici

* **GRANT individuale**: il reparto Tecnico non ha `approva_attivita_commessa`, ma il responsabile sì → override `abilitata = true`.
* **DENY individuale**: il reparto Amministrazione ha `genera_fatture_lotti`, ma un operatore junior no → override `abilitata = false`.
* **Delega temporanea**: un operatore sostituisce un collega per 2 settimane e riceve temporaneamente `numera_fatture_lotti`.

---

### ⚠️ Catena di risoluzione azioni

```
1. Override utente sull'azione? ← questa tabella
   → SI: applica abilitata (true/false)
   → NO: continua ↓

2. Azione abilitata nel profilo reparto?
   → SI: concessa
   → NO: negata
```

---

> **"`config.user_override_azioni` gestisce le eccezioni individuali sulle azioni di processo, con tracciabilità e scadenza automatica."**
