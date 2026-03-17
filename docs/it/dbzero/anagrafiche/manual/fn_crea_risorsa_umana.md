## Documentazione Concettuale -- Funzione `anagrafiche.fn_crea_risorsa_umana()`

> **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> [anagrafiche.risorse_umane_auth_user](/dbzero/anagrafiche/tabelle/risorse_umane_auth_user)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
>
**Approfondimento funzioni:**
>
[script.fn_get_or_create_soggetto_ruolo](/dbzero/script/funzioni/fn_get_or_create_soggetto_ruolo)
> [anagrafiche.fn_crea_operatore](/dbzero/anagrafiche/manual/fn_crea_operatore)
> [anagrafiche.fn_crea_auth_user](/dbzero/anagrafiche/manual/fn_crea_auth_user)
>
**Guide:**
>
[Risorse umane e accessi](/guide/risorse-umane-e-accessi)

---

### 🎯 Scopo Principale

(latest review 13-03-2026)
Building block atomico per la creazione di una risorsa umana con bridge
`auth_user` opzionale.

Crea/recupera automaticamente il ruolo `RIS_UMANA` tramite
`script.fn_get_or_create_soggetto_ruolo`. Se viene fornito `p_auth_user_id`,
crea anche il bridge `risorse_umane_auth_user` che abilita l'accesso al software.

---

### Parametri

| Parametro                  | Tipo                            | Obbligatorio | Default        | Note                                               |
| -------------------------- | ------------------------------- | :----------: | -------------- | -------------------------------------------------- |
| `p_soggetto_id`            | `soggetti.id%TYPE`              |      Si      | `NULL`         | UUID soggetto (deve esistere). Guard nel body.     |
| `p_qualifica_id`           | `qualifiche.id%TYPE`            |      Si      | `NULL`         | Deve essere attiva. Guard nel body.                |
| `p_unita_organizzativa_id` | `unita_organizzative.id%TYPE`   |      No      | `NULL`         | Se fornita, deve essere attiva.                    |
| `p_valido_dal`             | `risorse_umane.valido_dal%TYPE` |      No      | `CURRENT_DATE` | Inizio validita'.                                  |
| `p_valido_al`              | `risorse_umane.valido_al%TYPE`  |      No      | `NULL`         | Fine validita' (NULL = illimitata).                |
| `p_auth_user_id`           | `integer`                       |      No      | `NULL`         | Se fornito, crea bridge auth_user.                 |
| `p_ruolo_sistema`          | `config.ruolo_sistema`          |      No      | `'OPERATIVO'`  | Ruolo nel bridge (ADMIN, OPERATIVO, DISABILITATO). |

---

### Valore di ritorno

`anagrafiche.risorse_umane.id%TYPE` (bigint) -- ID della risorsa umana creata.

---

### Regole applicate

* **Qualifica attiva:** verifica esistenza e `attivo = true` in
  `config.qualifiche`. Errore: `E_ADMIN_VALIDAZIONE`.
* **UO attiva (se fornita):** verifica esistenza e `attivo = true` in
  `config.unita_organizzative`. Errore: `E_ADMIN_UO_NON_TROVATA`.
* **Auth user esistente (se fornito):** verifica esistenza in `auth_user`.
  Errore: `E_ADMIN_VALIDAZIONE`.
* **Creazione ruolo:** chiama `fn_get_or_create_soggetto_ruolo(p_soggetto_id, 'RIS_UMANA')`.
  Gestisce concorrenza (race condition).
* **INSERT risorse_umane:** con `attivo = true`.
* **Bridge opzionale:** se `p_auth_user_id IS NOT NULL`, inserisce in
  `risorse_umane_auth_user` con `attivo = true` e `ruolo_sistema`.

---

### Trigger coinvolti

| Trigger                                              | Fase          | Effetto                                                |
| ---------------------------------------------------- | ------------- | ------------------------------------------------------ |
| `trgfn_risorse_umane_guard_ruolo`                    | BEFORE INSERT | Verifica coerenza `soggetto_ruolo_id` / tipo RIS_UMANA |
| `trgfn_risorse_umane_auth_user_guard_persona_fisica` | BEFORE INSERT | Verifica CF NOT NULL e PIVA IS NULL (solo bridge)      |
| `trgfn_risorse_umane_auth_user_sync_active`          | AFTER INSERT  | Sincronizza `auth_user.is_active` (solo bridge)        |
| `trgfn_child_requires_active_parent`                 | AFTER INSERT  | Verifica soggetto attivo, qualifica attiva             |

---

### Riusabilita'

| Orchestratore                 | Uso                                            |
| ----------------------------- | ---------------------------------------------- |
| `fn_crea_operatore`           | Crea RU + bridge per operatore                 |
| (futuro) `fn_crea_admin`      | Crea RU + bridge con `ruolo_sistema = 'ADMIN'` |
| (futuro) creazione dipendente | Crea RU senza bridge (`p_auth_user_id = NULL`) |

---

{% include-markdown "signature-core.md" %}
