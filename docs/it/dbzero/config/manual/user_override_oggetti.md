## 📘 Documentazione Concettuale – Tabella `config.user_override_oggetti`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
Tabelle correlate:
>
[config.user_override_aree](/dbzero/config/tabelle/user_override_aree)
> [config.area_model_overrides](/dbzero/config/tabelle/area_model_overrides)

---

La tabella **`config.user_override_oggetti`** consente di sovrascrivere il livello di accesso per un **singolo model Django** per un utente specifico.

È il livello più granulare della catena di risoluzione: sovrascrive sia il profilo reparto che l'override area.

---
### 🎯 Scopo Principale
* Consentire **granularità a livello di singola entità** (model Django).
* Esempio: un utente ha TUTTO su Anagrafiche ma solo LETTURA su `anagrafiche.clienti`.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `auth_user_id` | Utente Django (FK → `django.auth_user`) |
| `app_label` | Label app Django (es. `anagrafiche`) |
| `model_name` | Nome model Django (es. `clienti`) |
| `livello` | `config.livello_accesso`: TUTTO / LETTURA / BLOCCATO |
| `motivo` | Motivazione dell'override |
| `valido_dal` / `valido_al` | Finestra temporale di validità |

Il vincolo UNIQUE su `(auth_user_id, app_label, model_name)` garantisce un solo override per utente/model.

⛔ **Solo oggetti a catalogo e non riservati.** La FK composita
`fk_user_override_oggetti_catalogo` punta `(app_label, model_name, riservato)`
di [config.area_model_overrides](/dbzero/config/tabelle/area_model_overrides);
qui `riservato` è una colonna **generata**, sempre `false`, che non si scrive.
Un override su un oggetto fuori catalogo, o riservato, è rifiutato dal database
qualunque sia il percorso di scrittura.

---

### ⚠️ Priorità nella catena

Questo override è al **primo livello** della catena di risoluzione (massima priorità):

```
1. Override utente su SINGOLO OGGETTO ← questa tabella
2. Override utente su AREA
3. Profilo reparto
4. Default → BLOCCATO
```

---

### Uso consigliato

Questa tabella è pensata per **eccezioni rare e puntuali**. Se molti utenti hanno override sullo stesso model, probabilmente serve una riorganizzazione dei profili reparto o una separazione dell'area funzionale.

---

> **"`config.user_override_oggetti` è il livello più granulare del sistema permessi: usare con parsimonia per eccezioni puntuali."**
