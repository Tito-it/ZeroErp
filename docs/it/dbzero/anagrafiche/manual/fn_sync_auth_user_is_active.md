## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_sync_auth_user_is_active()`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
>
**Approfondimento tabelle:**
>
[anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
>
**Approfondimento funzioni:**
>
[anagrafiche.fn_sync_auth_user_expired](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_expired)

---
### 🎯 Scopo Principale
(latest review 20-04-2026 — semantica OR multi-veste)

La funzione **`anagrafiche.fn_sync_auth_user_is_active()`** allinea il campo
`django.auth_user.is_active` allo stato effettivo delle identita digitali
dell'utente.

Post 20-04-2026 (modello SSO multi-veste) la funzione ha una logica **OR
su N identita**: `auth_user.is_active = true` se e solo se esiste almeno
un'identita utilizzabile per l'utente (cioe' attiva, con ruolo applicativo
diverso da DISABILITATO, in finestra temporale, con soggetto parent attivo).

---

### Parametri di input

| Parametro        | Tipo      | Descrizione                           |
| ---------------- | --------- | ------------------------------------- |
| `p_auth_user_id` | `integer` | ID dell'utente Django. NOT NULL, > 0. |

Il parametro è dichiarato con `%TYPE` della colonna
`anagrafiche.identita_digitali.auth_user_id`.

---

### Output

`boolean` — `true` solo se la funzione ha **effettivamente modificato** la
riga `django.auth_user` (UPDATE applicato perché il valore è cambiato).
`false` in tutti gli altri casi (utente orfano, nessun cambio, schema django
assente).

---

### Algoritmo (OR multi-veste post 20-04-2026)

1. **Guard parametro** — `p_auth_user_id IS NULL OR <= 0` → `E_PARAMETRO_INVALIDO`.
2. **Calcolo OR** — singola query `EXISTS (...)` sulle N identita
   digitali dell'utente. `is_active = true` se esiste almeno un'identita
   che soddisfa tutti i criteri:
   * `id.attivo = true`
   * `id.ruolo_applicativo <> 'DISABILITATO'` (fail-closed per convenzione)
   * `CURRENT_DATE BETWEEN id.valido_dal AND COALESCE(id.valido_al, CURRENT_DATE)`
   * Soggetto parent attivo (via `soggetti_ruoli` → `soggetti.attivo = true`)
3. **No-op ambiente CI** — se schema Django assente, `RETURN false`
   silente (CI senza Django non ha auth_user da sincronizzare).
4. **UPDATE** — `auth_user.is_active = <OR>` solo se diverso dal valore
   corrente. Se l'auth_user non esiste (orfano), `RETURN false`.

**Motivazione OR:** Django `is_active` e' il flag globale di autorizzazione
al login. Se l'utente ha 3 vesti e ne vengono disattivate 2, deve
comunque poter loggare con la terza. Il blocco della singola veste
disattivata e' applicato dalla policy RLS + permission class namespace,
non dal flag `is_active`.

**Rimossi rispetto a versioni pre-20-04:**

* Fallback legacy su `risorse_umane_auth_user` (ora vista post cutover
  19-04-2026, gia' rimosso in migration 20260419-92).
* Doppia verifica per OPERATORE su `risorse_umane.attivo` (vincolo legacy
  transitorio gia' rimosso in 20260419-92).
* Assunzione 1:1 user→identita (sostituita da query aggregata sul set
  delle identita).

---

### Fix bug latente §3.2.b (verifica 2026-04-18)

La firma precedente accettava `p_risorsa_umana_id bigint`, ma 3 metodi di
`AmmSoftwareRepository` (`update_operatore`, `disabilita_operatore`,
`riattiva_operatore`) la invocavano passando invece un `auth_user_id`.
Il bug era coperto dai trigger AFTER su `risorse_umane_auth_user` che
chiamavano la funzione con il parametro corretto, ma lasciava un rischio
di comportamento non deterministico in caso di collisione di id tra
`auth_user` e `risorse_umane`.

La nuova firma `(p_auth_user_id)` rende **automaticamente corretti** i 3
metodi Python senza toccare il codice chiamante.

---

### Regole implementative

* Variabili locali e parametro tipizzati con `%TYPE` (policy ZeroErp).
* `LANGUAGE plpgsql` (non `sql`): la funzione ha flusso condizionale
  complesso + EXECUTE dinamico per dialog con `django.auth_user`.
* `EXECUTE` dinamico su `django.auth_user`: evita dipendenza statica dallo
  schema `django` (compatibilità CI).
* Codici errore: `E_PARAMETRO_INVALIDO` (già in `messaggi_errore`).

---

### Chiamanti

#### Trigger DB

* `anagrafiche.trgfn_risorse_umane_sync_auth_user_active` — risolve
  l'`auth_user_id` dalle identità collegate alla risorsa prima di chiamare.
* `anagrafiche.trgfn_identita_digitali_sync_auth_user_active` — passa
  `NEW.auth_user_id`.

#### Funzione batch

* `anagrafiche.fn_sync_auth_user_expired` — loop daily via pgAgent con
  `DISTINCT auth_user_id` su UNION di risorse_umane scadute + identità scadute.

#### Service Python

* `AmmSoftwareRepository.update_operatore / disabilita_operatore /
  riattiva_operatore` — passano `auth_user_id` (ora corretto grazie alla
  nuova firma; fix implicito del bug latente §3.2.b).

---

{% include-markdown "signature-core.md" %}
