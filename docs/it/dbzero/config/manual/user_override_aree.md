## 📘 Documentazione Concettuale – Tabella `config.user_override_aree`

> **Ultimo aggiornamento**: 27 novembre 2026

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
Tabelle correlate:
>
[config.aree_funzionali](/dbzero/config/tabelle/aree_funzionali)
> [config.profili_accesso_aree](/dbzero/config/tabelle/profili_accesso_aree)
> [config.user_override_oggetti](/dbzero/config/tabelle/user_override_oggetti)

---

La tabella **`config.user_override_aree`** consente di **sovrascrivere il profilo del reparto** per un singolo utente su un'area funzionale.

---
### 🎯 Scopo Principale
* Gestire **eccezioni individuali** al profilo ereditato dal reparto.
* Supportare **deleghe temporanee** tramite validità temporale (`valido_dal` / `valido_al`).
* Documentare la **motivazione** dell'override per audit e governance.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `auth_user_id` | Utente Django (FK → `django.auth_user`) |
| `area_id` | Area funzionale (FK → `config.aree_funzionali`) |
| `livello` | `config.livello_accesso`: TUTTO / LETTURA / BLOCCATO |
| `motivo` | Testo libero: perché è stato concesso l'override |
| `valido_dal` / `valido_al` | Finestra temporale di validità (NULL = indeterminato) |

---

### Casi d'uso tipici

* **Delega temporanea**: un operatore del reparto Tecnico ha bisogno di LETTURA su Vendite per 2 settimane → override con `valido_al`.
* **Restrizione puntuale**: un operatore non deve vedere Contabilità nonostante il profilo del suo reparto lo consenta → override BLOCCATO.
* **Promozione individuale**: un operatore senior ha TUTTO su un'area che per il reparto è LETTURA.

---

### ⛔ Chi la scrive

Solo il **SUPER_ADMIN**, dal verbo [`config.fn_imposta_override_aree`](/dbzero/config/funzioni/fn_imposta_override_aree), che
sostituisce l'elenco delle eccezioni di un utente. Per l'applicazione la tabella è in sola lettura:
un'eccezione dà un potere che il profilo non dà, e un operatore che potesse scriverne una per sé si
alzerebbe il livello da solo (brief-db-porte-aperte-dalla-sola-guc, giro 10-quater, 2026-11-27).

---

### ⚠️ Priorità nella catena

Questo override ha **priorità sul profilo reparto** ma è sovrascritto da un override oggetto (`config.user_override_oggetti`).

Il CHECK `chk_user_override_aree_validita` garantisce la coerenza delle date: `valido_al >= valido_dal`.

---

> **"`config.user_override_aree` permette eccezioni individuali senza modificare il profilo del reparto, con tracciabilità e scadenza automatica."**
