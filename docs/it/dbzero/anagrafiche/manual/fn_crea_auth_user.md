## Documentazione Concettuale -- Funzione `anagrafiche.fn_crea_auth_user()`

> **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
>
**Approfondimento funzioni:**
>
[anagrafiche.fn_crea_operatore_v2](/dbzero/anagrafiche/funzioni/fn_crea_operatore_v2)
> [anagrafiche.fn_crea_risorsa_umana_v2](/dbzero/anagrafiche/funzioni/fn_crea_risorsa_umana_v2)

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
| `p_email`         | `text` |      Si      | `NULL`  | Email univoca senza distinguere maiuscole e minuscole. Guard nel body. |
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
  con la stessa `email` **a meno delle maiuscole** (D-9: l'email e' la chiave
  d'ingresso di portale e shop). Non confronta da se': chiede a
  [`script.fn_get_auth_user_id_for_email`](/dbzero/script/funzioni/fn_get_auth_user_id_for_email),
  la sede unica della regola (dal 2026-09-25, `20260925-41`; prima era
  `email = TRIM(p_email)` e `Mario@x.it` passava accanto a `mario@x.it`).
  Errore: `E_ADMIN_EMAIL_DUPLICATA`. Sotto, come rete, l'indice unico
  `ix_auth_user_email_lower_unique` su `django.auth_user` (dove c'e': in CI no,
  nasce dopo Django); senza il guard la collisione sarebbe un `23505` anonimo.
* **Valori fissi INSERT:** `is_active = true`, `is_staff = false`,
  `is_superuser = false`, `date_joined = NOW()`.
* I campi `first_name` e `last_name` vengono impostati a stringa vuota
  se non forniti (Django li richiede NOT NULL).

---

### Riusabilita'

| Orchestratore             | Uso                                         |
| ------------------------- | ------------------------------------------- |
| `fn_crea_operatore_v2`    | Crea auth_user per operatore **solo se l'email non ha gia' una credenziale** (altrimenti la riusa, D-6) |
| (futuro) `fn_crea_admin`  | Crea auth_user per amministratore           |
| (futuro) qualsiasi flusso | Crea utente Django senza logica anagrafiche |

---

{% include-markdown "signature-core.md" %}
