## 📘 Documentazione Concettuale – Tabella `config.user_emittenti_fiscali`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
Tabelle correlate:
>
[anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)

---

La tabella **`config.user_emittenti_fiscali`** definisce l'**ambito operativo** di un utente: su quali emittenti fiscali può operare.

Implementa una **whitelist opzionale**: se l'utente non ha righe in questa tabella, può operare su tutti gli emittenti; se ha almeno una riga, è limitato a quelli elencati.

---

### 🎯 Scopo Principale

* Limitare la **visibilità e operatività** di un utente a specifici emittenti fiscali.
* Supportare scenari **multi-azienda**: un operatore lavora solo per ACME S.r.l. e Beta S.r.l.
* Fornire il dato per il **filtering queryset** (`EmittenteFiscaleScopeMixin`) e per il **defense-in-depth** DB (`fn_check_user_emittente_scope`).

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `auth_user_id` | Utente Django (FK → `django.auth_user`) |
| `emittente_fiscale_id` | Emittente autorizzato (FK → `anagrafiche.emittenti_fiscali`) |

Il vincolo UNIQUE su `(auth_user_id, emittente_fiscale_id)` impedisce duplicati.

---

### Semantica della whitelist

| Righe per l'utente | Comportamento |
|---------------------|--------------|
| **Nessuna riga** | Accesso a **tutti** gli emittenti (nessuna restrizione) |
| **Una o più righe** | Accesso **solo** agli emittenti elencati |

Questa semantica "fail-open se vuoto" è coerente con il pattern già adottato in `config.utilities_tipi_ruolo`.

---

### Enforcement a due livelli

| Livello | Meccanismo | Dove |
|---------|-----------|------|
| **Django** | `EmittenteFiscaleScopeMixin` filtra il queryset | View DRF |
| **DB** | `script.fn_check_user_emittente_scope()` + trigger guard | Tabelle operative (fatture, ordini, pagamenti) |

Il trigger DB è un **defense-in-depth**: garantisce che nessun bypass applicativo possa inserire dati su emittenti non autorizzati.

---

> **"`config.user_emittenti_fiscali` è il pilastro dell'ambito multi-azienda: whitelist opzionale con enforcement sia Django che DB."**
