## Documentazione Concettuale -- Funzione `anagrafiche.fn_crea_operatore()`

> **Vedi anche**
>
**Building block chiamati:**
>
[anagrafiche.fn_crea_auth_user](/dbzero/anagrafiche/manual/fn_crea_auth_user)
> [anagrafiche.fn_crea_soggetto_pf](/dbzero/anagrafiche/manual/fn_crea_soggetto_pf)
> [anagrafiche.fn_crea_risorsa_umana](/dbzero/anagrafiche/manual/fn_crea_risorsa_umana)
> [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/manual/fn_crea_indirizzo_soggetto)
> [anagrafiche.fn_get_or_create_indirizzo_dettaglio](/dbzero/anagrafiche/manual/fn_get_or_create_indirizzo_dettaglio)
> [script.fn_get_or_create_soggetto_ruolo](/dbzero/script/funzioni/fn_get_or_create_soggetto_ruolo)
>
**Guide:**
>
[Risorse umane e accessi](/guide/risorse-umane-e-accessi)
> [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici)

---
### 🎯 Scopo Principale
(latest review 13-03-2026)
Orchestratore transazionale per la creazione completa di un operatore.
Chiama i building block in sequenza all'interno di una singola transazione:

```text
fn_crea_auth_user              --> auth_user (Django)
fn_crea_soggetto_pf            --> soggetto PF (PR) + contatto default (con comune_nascita_id)
fn_crea_risorsa_umana          --> ruolo RIS_UMANA + risorsa_umana + bridge auth_user
fn_crea_indirizzo_soggetto x2  --> RESID + DOMFISC (se p_indirizzo_resid_dettaglio_id fornito)
```

L'orchestratore **non contiene logica duplicata**: validazione unicita',
lookup config, INSERT sono delegati ai building block. L'orchestratore
valida solo la coerenza dei parametri e la sequenza delle chiamate.

In caso di errore in qualsiasi step, il rollback e' automatico
(singola transazione PostgreSQL).

---

### Parametri

| Parametro                  | Tipo                            | Obbligatorio | Default        | Note                                    |
| -------------------------- | ------------------------------- | :----------: | -------------- | --------------------------------------- |
| `p_cognome`                | `soggetti.cognome%TYPE`         |      Si      | `NULL`         | Guard nel body.                         |
| `p_nome`                   | `soggetti.nome%TYPE`            |      Si      | `NULL`         | Guard nel body.                         |
| `p_codice_fiscale`         | `soggetti.codice_fiscale%TYPE`  |      Si      | `NULL`         | Richiesto da guard PF.                  |
| `p_username`               | `text`                          |      Si      | `NULL`         | Username univoco auth_user.             |
| `p_email`                  | `text`                          |      Si      | `NULL`         | Email univoca (anche contatto default). |
| `p_password_hash`          | `text`                          |      Si      | `NULL`         | Hash password formato Django.           |
| `p_qualifica_id`           | `qualifiche.id%TYPE`            |      Si      | `NULL`         | Qualifica risorsa umana.                |
| `p_unita_organizzativa_id` | `unita_organizzative.id%TYPE`   |      No      | `NULL`         | UO di appartenenza.                     |
| `p_data_nascita`           | `soggetti.data_nascita%TYPE`    |      No      | `NULL`         |                                         |
| `p_sesso`                  | `soggetti.sesso%TYPE`           |      No      | `'M'`          |                                         |
| `p_ruolo_sistema`          | `config.ruolo_sistema`          |      No      | `'OPERATIVO'`  |                                         |
| `p_valido_dal`             | `risorse_umane.valido_dal%TYPE` |      No      | `CURRENT_DATE` |                                         |
| `p_valido_al`              | `risorse_umane.valido_al%TYPE`  |      No      | `NULL`         |                                         |
| `p_comune_nascita_id`      | `soggetti.comune_id%TYPE`       |      No      | `NULL`         | Comune di nascita (FK comuni). Sprint 3.|
| `p_indirizzo_resid_dettaglio_id` | `indirizzi_dettaglio.id%TYPE` | No      | `NULL`         | Indirizzo residenza normalizzato. Sprint 3.|
| `p_indirizzo_domfisc_dettaglio_id` | `indirizzi_dettaglio.id%TYPE` | No    | `NULL`         | Domicilio fiscale. Se NULL e RESID fornito, usa RESID. Sprint 3.|

**Firma flessibile:** tutti i parametri hanno `DEFAULT NULL` per consentire
chiamate con parametri named. La validazione avviene nel body.

---

### Valore di ritorno

`integer` -- `auth_user.id` dell'utente creato.

---

### Sequenza operazioni

```text
1. Validazione coerenza parametri orchestratore
2. fn_crea_auth_user(username, email, password_hash, nome, cognome)
   --> v_auth_user_id
3. fn_crea_soggetto_pf(cognome, nome, cf, email, data_nascita, sesso, comune_nascita_id)
   --> v_soggetto_id
4. fn_crea_risorsa_umana(soggetto_id, qualifica_id, uo_id,
     valido_dal, valido_al, auth_user_id, ruolo_sistema)
   --> v_ru_id  (internamente chiama fn_get_or_create_soggetto_ruolo)
5. Se p_indirizzo_resid_dettaglio_id IS NOT NULL:
     fn_crea_indirizzo_soggetto(soggetto_id, 'RESID', dettaglio_id)
     fn_crea_indirizzo_soggetto(soggetto_id, 'DOMFISC', COALESCE(domfisc, resid))
6. RETURN v_auth_user_id
```

---

### Nota indirizzo (aggiornata Sprint 3)

L'orchestratore ora supporta la creazione di indirizzi RESID e DOMFISC
tramite `p_indirizzo_resid_dettaglio_id` e `p_indirizzo_domfisc_dettaglio_id`.

Se `p_indirizzo_resid_dettaglio_id` e' fornito:

* Crea RESID con `fn_crea_indirizzo_soggetto`
* Crea DOMFISC (se `p_indirizzo_domfisc_dettaglio_id` IS NULL, usa stesso di RESID)

Se **non** fornito: nessun indirizzo creato. Il trigger DEFERRED
`trgfn_soggetti_guard_indirizzi_required` puo' bloccare al COMMIT se la
matrice richiede indirizzi obbligatori per PR.

---

### Trigger coinvolti (catena completa)

| Trigger                                              | Tabella                 | Fase          | Effetto                    |
| ---------------------------------------------------- | ----------------------- | ------------- | -------------------------- |
| `trgfn_soggetti_gen_codice`                          | soggetti                | BEFORE INSERT | Genera codice soggetto     |
| `trgfn_soggetti_normalize`                           | soggetti                | BEFORE INSERT | `ragione_sociale_completa` |
| `trgfn_soggetti_guard_cf_piva_obbligatori`           | soggetti                | BEFORE INSERT | Valida CF/PIVA per natura  |
| `trgfn_soggetti_valida_cf_piva_dispatch`             | soggetti                | BEFORE INSERT | Formato CF 16 char         |
| `trgfn_soggetti_guard_soggetto_contatti`             | soggetti                | DEFERRED      | Almeno 1 contatto          |
| `trgfn_soggetti_guard_indirizzi_required`            | soggetti                | DEFERRED      | Indirizzi obbligatori      |
| `trgfn_contatti_set_default_contatto`                | contatti                | BEFORE INSERT | Auto-default               |
| `trgfn_soggetti_ruoli_guard_natura_ammessa`          | soggetti_ruoli          | BEFORE INSERT | Natura/ruolo compatibili   |
| `trgfn_risorse_umane_guard_ruolo`                    | risorse_umane           | BEFORE INSERT | Verifica tipo RIS_UMANA    |
| `trgfn_risorse_umane_auth_user_guard_persona_fisica` | risorse_umane_auth_user | BEFORE INSERT | CF NOT NULL, PIVA IS NULL  |
| `trgfn_risorse_umane_auth_user_sync_active`          | risorse_umane_auth_user | AFTER INSERT  | Sync `auth_user.is_active` |

---

{% include-markdown "signature-core.md" %}
