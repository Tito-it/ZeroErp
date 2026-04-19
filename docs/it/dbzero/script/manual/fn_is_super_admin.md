## Documentazione Concettuale – Funzione `script.fn_is_super_admin`

> **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
**Tabelle correlate:**
>
[anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [config.profili_accesso](/dbzero/config/tabelle/profili_accesso)
> [config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings)
>
**Funzioni correlate:**
>
[script.fn_has_identita_attiva](/dbzero/script/funzioni/fn_has_identita_attiva)
> [script.fn_get_ruolo_sistema](/dbzero/script/funzioni/fn_get_ruolo_sistema)

---
### 🎯 Scopo Principale
(latest review 19-04-2026)

La funzione **`script.fn_is_super_admin`** verifica se un utente ha il
privilegio di **bypass totale dei permessi** (equivalente al vecchio
`ruolo_sistema = 'ADMIN'` sul bridge legacy `risorse_umane_auth_user`).

Nel nuovo modello (§4.6 WIP multi-face-auth, decisione 2026-04-19 "ADMIN
come profilo") il bypass non è più una colonna speciale ma un **binding
attivo verso un profilo di tipo `SUPER_ADMIN`** (profilo seed `id = 9100`).

---

### Parametri di input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_auth_user_id` | `integer` | ID utente Django. Fail-closed su `NULL`. |

---

### Output

`BOOLEAN` — `true` se l'utente è super admin, `false` altrimenti.

---

### Condizioni verificate

Ritorna `true` se e solo se esiste (JOIN su 3 tabelle):

1. Un'identità `anagrafiche.identita_digitali` con:
   * `auth_user_id = p_auth_user_id`
   * `attivo = true`
   * `ruolo_applicativo <> 'DISABILITATO'`
   * In finestra temporale (`valido_dal <= today <= valido_al`)
2. Un binding attivo su quella identità (`profili_accesso_bindings.attivo = true`)
3. Il profilo bindato è attivo (`profili_accesso.attivo = true`) e ha
   `tipo = 'SUPER_ADMIN'`

Fail-closed: se una sola condizione non è verificata, ritorna `false`.

---

### Cross-ruolo by design

Il check non restringe `ruolo_applicativo = 'OPERATORE'`: un binding
SUPER_ADMIN su un'identità `CLIENTE_PORTALE` viene riconosciuto e
restituisce `true`. Questo è **intenzionale**: in Fase 2 post-MVP il
modello supporterà `CLIENTE_ADMIN_PORTALE` come binding SUPER_ADMIN su
identità `CLIENTE_PORTALE` (o variante limitata al solo portale) **senza
refactor** di questa funzione.

Il solo filtro su `ruolo_applicativo` è `<> 'DISABILITATO'` per
coerenza fail-closed: un'identità disattivata (anche se con binding
attivo residuo) non deve bypassare i permessi.

---

### Filtro tramite tipo, non tramite id

La query filtra per `pa.tipo = 'SUPER_ADMIN'` anziché hardcoded sul seed
`pa.id = 9100`. Scelta di flessibilità: permette in futuro di avere
**più profili SUPER_ADMIN differenziati** (es. `SUPER_ADMIN_TECH` per
DBA e `SUPER_ADMIN_DATI` per referenti dati) semplicemente seedando
profili aggiuntivi con `tipo = 'SUPER_ADMIN'`, senza toccare questa
funzione.

---

### Regole implementative

* `LANGUAGE sql`, `STABLE`: inlineable dal planner, cache-friendly.
* Unica query `SELECT EXISTS (...)` con JOIN su FK indicizzate.
* Fail-closed implicito su `NULL`: l'`EXISTS` restituisce `false` senza
  richiedere un check esplicito.

---

### Sostituisce il check legacy

Il pattern sostituito nel refactor §4.6.B:

```sql
-- PRIMA (legacy): colonna diretta sul bridge
SELECT rau.ruolo_sistema = 'ADMIN'
  FROM anagrafiche.risorse_umane_auth_user rau
 WHERE rau.auth_user_id = p_auth_user_id;

-- DOPO (nuovo modello): check binding attivo
SELECT script.fn_is_super_admin(p_auth_user_id);
```

Il wrapper `fn_get_ruolo_sistema` (deprecato) usa internamente questa
funzione per ricostruire la stringa `'ADMIN'` / `'OPERATIVO'` /
`'DISABILITATO'` a beneficio dei chiamanti legacy non ancora migrati
(rimossi in PR2 backend).

---

### Esempio d'uso

```sql
-- Bypass totale in fn_resolve_livello_area:
IF script.fn_is_super_admin(p_auth_user_id) THEN
    RETURN 'TUTTO'::config.livello_accesso;
END IF;

-- In una policy RLS (futuro §4.9):
CREATE POLICY rls_fatture_bypass_admin ON vendite.fatture
    FOR SELECT
    USING (
        script.fn_is_super_admin(
            NULLIF(current_setting('app.jwt_user', true), '')::int
        )
    );
```

---

### Evoluzione attesa

Quando il backend (PR2) e il frontend (PR2) verranno migrati, l'esperienza
di "concedere ADMIN" passerà dal radio `ruolo_sistema` nel drawer
operatore a un toggle "Concedi accesso SUPER ADMIN" che crea/rimuove un
binding verso il profilo 9100. Al cutover §4.6.H il bridge legacy
`risorse_umane_auth_user` verrà sostituito dalla vista
`vw_risorse_umane_auth_user`, che usa questa funzione (via LEFT JOIN
pre-aggregato) per ricostruire il campo `ruolo_sistema` output.

---

{% include-markdown "signature-core.md" %}
