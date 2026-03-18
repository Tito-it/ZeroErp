## Documentazione Concettuale -- Funzione `anagrafiche.fn_crea_auth_user()`

> **Vedi anche**
>
**Approfondimento tabelle:**
>
[auth_user (Django)](/dbzero/anagrafiche/tabelle/risorse_umane_auth_user)
>
**Approfondimento funzioni:**
>
[anagrafiche.fn_crea_operatore](/dbzero/anagrafiche/manual/fn_crea_operatore)
> [anagrafiche.fn_crea_risorsa_umana](/dbzero/anagrafiche/manual/fn_crea_risorsa_umana)

---
### 🎯 Scopo Principale
(latest review 13-03-2026)
Building block atomico per la creazione di un record `auth_user` (Django).
Gestisce la validazione dei parametri e i guard di unicita' su username e email.

Non crea soggetto, contatto, risorsa umana ne' bridge: e' responsabilita'
dell'orchestratore (es. `fn_crea_operatore`) comporre i building block.

---

### Parametri

| Parametro         | Tipo   | Obbligatorio | Default | Note                                  |
| ----------------- | ------ | :----------: | ------- | ------------------------------------- |
| `p_username`      | `text` |      Si      | `NULL`  | Username univoco. Guard nel body.     |
| `p_email`         | `text` |      Si      | `NULL`  | Email univoca. Guard nel body.        |
| `p_password_hash` | `text` |      Si      | `NULL`  | Hash password formato Django.         |
| `p_first_name`    | `text` |      No      | `NULL`  | Nome. Se NULL viene inserito `''`.    |
| `p_last_name`     | `text` |      No      | `NULL`  | Cognome. Se NULL viene inserito `''`. |

**Firma flessibile:** tutti i parametri hanno `DEFAULT NULL` per consentire
chiamate con parametri named. La validazione avviene nel body con guard espliciti.

---

### Valore di ritorno

`integer` -- `auth_user.id` dell'utente creato.

---

### Regole applicate

* **Guard unicita' username:** verifica che non esista gia' un `auth_user`
  con lo stesso `username`. Errore: `E_ADMIN_USERNAME_DUPLICATO`.
* **Guard unicita' email:** verifica che non esista gia' un `auth_user`
  con la stessa `email`. Errore: `E_ADMIN_EMAIL_DUPLICATA`.
* **Valori fissi INSERT:** `is_active = true`, `is_staff = false`,
  `is_superuser = false`, `date_joined = NOW()`.
* I campi `first_name` e `last_name` vengono impostati a stringa vuota
  se non forniti (Django li richiede NOT NULL).

---

### Riusabilita'

| Orchestratore             | Uso                                         |
| ------------------------- | ------------------------------------------- |
| `fn_crea_operatore`       | Crea auth_user per operatore                |
| (futuro) `fn_crea_admin`  | Crea auth_user per amministratore           |
| (futuro) qualsiasi flusso | Crea utente Django senza logica anagrafiche |

---

{% include-markdown "signature-core.md" %}
