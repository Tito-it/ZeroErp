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
> [anagrafiche.risorse_umane_auth_user](/dbzero/anagrafiche/tabelle/risorse_umane_auth_user)
> [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
>
**Approfondimento funzioni:**
>
[anagrafiche.fn_sync_auth_user_expired](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_expired)

---
### 🎯 Scopo Principale
(latest review 18-04-2026)

La funzione **`anagrafiche.fn_sync_auth_user_is_active()`** allinea il campo
`django.auth_user.is_active` allo stato effettivo del bridge auth associato.

Con la generalizzazione §4.5 del modello multi-face auth la funzione ha
cambiato firma: parte da `auth_user_id` invece che da `risorsa_umana_id`,
risolve internamente il bridge (nuovo o legacy) e gestisce tutti i ruoli
applicativi (operatore, portale clienti, portale fornitori, shop customer,
api_client, disabilitato).

---

### Parametri di input

| Parametro        | Tipo      | Descrizione                            |
|------------------|-----------|----------------------------------------|
| `p_auth_user_id` | `integer` | ID dell'utente Django. NOT NULL, > 0.  |

Il parametro è dichiarato con `%TYPE` della colonna
`anagrafiche.identita_digitali.auth_user_id`.

---

### Output

`boolean` — `true` solo se la funzione ha **effettivamente modificato** la
riga `django.auth_user` (UPDATE applicato perché il valore è cambiato).
`false` in tutti gli altri casi (utente orfano, nessun cambio, schema django
assente).

---

### Algoritmo (expand-align-contract)

1. **Guard parametro** — `p_auth_user_id IS NULL OR <= 0` → `E_PARAMETRO_INVALIDO`.
2. **Priorità: nuovo bridge** — cerca identità attiva in
   `anagrafiche.identita_digitali` per `auth_user_id`. Se trovata, procede al
   calcolo basato su `identita_digitali`.
3. **Fallback legacy** — se nessuna identità, cerca bridge in
   `risorse_umane_auth_user`. Necessario durante la transizione §4.5 → §4.6
   quando `identita_digitali` è ancora vuota. Post cutover §4.6 il ramo
   legacy diventa dead code.
4. **Calcolo `is_active` atteso**:
   * `DISABILITATO` → `false`
   * altri ruoli → AND di: identità attiva, finestra `[valido_dal, valido_al]`
     valida, `soggetti.attivo = true`
   * **OPERATORE in più**: AND con `risorse_umane.attivo` + finestra RU
     (vincolo legacy mantenuto durante transizione, rimuovibile post §4.6)
5. **UPDATE auth_user.is_active** solo se il valore cambia (short-circuit
   se lo stato è già corretto). Gestione difensiva dell'assenza schema Django
   (ambienti CI senza Django: no-op silente).

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

* `anagrafiche.trgfn_risorse_umane_auth_user_sync_active` — passa
  `NEW.auth_user_id` (aggiornato in §4.5 F2).
* `anagrafiche.trgfn_risorse_umane_sync_auth_user_active` — risolve
  `auth_user_id` dal bridge RUA prima di chiamare (aggiornato in §4.5 F2).
* `anagrafiche.trgfn_identita_digitali_sync_auth_user_active` — nuovo:
  passa `NEW.auth_user_id` (§4.5 F4).

#### Funzione batch

* `anagrafiche.fn_sync_auth_user_expired` — loop daily via pgAgent con
  `DISTINCT auth_user_id` su UNION di risorse_umane scadute + identità scadute.

#### Service Python

* `AmmSoftwareRepository.update_operatore / disabilita_operatore /
  riattiva_operatore` — passano `auth_user_id` (ora corretto grazie alla
  nuova firma; fix implicito del bug latente §3.2.b).

---

{% include-markdown "signature-core.md" %}
