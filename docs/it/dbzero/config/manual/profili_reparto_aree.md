## 📘 Documentazione Concettuale – Tabella `config.profili_reparto_aree`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
Tabelle correlate:
>
[config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative)
> [config.aree_funzionali](/dbzero/config/tabelle/aree_funzionali)
> [config.profili_reparto_azioni](/dbzero/config/tabelle/profili_reparto_azioni)
> [config.user_override_aree](/dbzero/config/tabelle/user_override_aree)

---

La tabella **`config.profili_reparto_aree`** è il **cuore dell'ereditarietà** del sistema permessi.

Definisce il livello di accesso di default che ogni reparto ha su ogni area funzionale. Tutti gli operatori del reparto ereditano automaticamente questi livelli.

---

### 🎯 Scopo Principale

* Definire il **profilo di accesso ereditato**: una matrice (reparto × area) → livello.
* Consentire la configurazione centralizzata: un cambio di policy si applica a tutti gli operatori del reparto.
* Garantire il **default sicuro**: se un reparto non ha profilo per un'area, l'accesso è BLOCCATO.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `unita_organizzativa_id` | Reparto (FK → `config.unita_organizzative`) |
| `area_id` | Area funzionale (FK → `config.aree_funzionali`) |
| `livello` | `config.livello_accesso`: TUTTO / LETTURA / BLOCCATO (default BLOCCATO) |

---

### ⚠️ Impatto delle modifiche

Modificare il profilo di un reparto ha **impatto immediato** su tutti gli operatori associati. L'interfaccia di gestione deve sempre mostrare il numero di operatori impattati prima di confermare.

---

### Catena di risoluzione (livello area)

```
1. Override utente su SINGOLO OGGETTO? → SI: applica → NO: continua ↓
2. Override utente su AREA?            → SI: applica → NO: continua ↓
3. Profilo reparto per quell'area?     → SI: applica → NO: BLOCCATO
```

Questa tabella interviene al **punto 3** della catena.

---

> **"`config.profili_reparto_aree` è il motore dell'ereditarietà: configura una volta il reparto, tutti gli operatori sono allineati."**
