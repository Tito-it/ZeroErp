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
> [script.fn_check_ultimo_super_admin_attivo](/dbzero/script/funzioni/fn_check_ultimo_super_admin_attivo)

---
### 🎯 Scopo Principale
(latest review 20-04-2026 — filtro OPERATORE)

La funzione **`script.fn_is_super_admin`** verifica se un utente ha il
privilegio di **bypass totale dei permessi**. Sostituisce
semanticamente l'enum legacy `config.ruolo_sistema` (valori
`ADMIN`/`OPERATIVO`/`DISABILITATO`) droppato in Fase 7 cleanup
(2026-04-29) — il check `is_super_admin = true` corrisponde al vecchio
`ruolo_sistema = 'ADMIN'`.

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
   * **`ruolo_applicativo = 'OPERATORE'`** (post 20-04-2026 — filtro esplicito)
   * In finestra temporale (`valido_dal <= today <= valido_al`)
2. Un binding attivo su quella identità (`profili_accesso_bindings.attivo = true`)
3. Il profilo bindato è attivo (`profili_accesso.attivo = true`) e ha
   `tipo = 'SUPER_ADMIN'`

Fail-closed: se una sola condizione non è verificata, ritorna `false`.

---

### Filtro OPERATORE (post 20-04-2026)

Post modello SSO multi-veste, la fn filtra esplicitamente
`ruolo_applicativo = 'OPERATORE'`. Motivazione:

* Un `auth_user` puo' avere contemporaneamente identita OPERATORE+SUPER_ADMIN
  e identita CLIENTE_PORTALE. Senza filtro, la fn restituirebbe `true` anche
  quando l'utente e' loggato in contesto portale → bypass permessi
  indesiderato.
* SUPER_ADMIN e' privilege di **operatore interno** per design: un cliente
  B2B che ha anche credenziali amministrative entra da `/api/admin/*` con
  la veste OPERATORE, non dal portale con la veste CLIENTE_PORTALE.
* Il caso `CLIENTE_ADMIN_PORTALE` (admin di portale B2B multi-utente) sara'
  gestito in Fase 2 con una chiamata dedicata (es. `fn_is_cliente_admin`)
  con semantica propria, non estendendo `fn_is_super_admin`.

Un binding SUPER_ADMIN patologico su identita non-OPERATORE (caso che
tecnicamente il modello ammette ma non e' intenzionale) viene **ignorato**
dalla fn.

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

Il wrapper `fn_get_ruolo_sistema` esisteva come retrocompat fino a
Fase 7 cleanup (2026-04-29), quando e' stato droppato insieme alla
colonna `ruolo_sistema` della vista `risorse_umane_auth_user` e al
type `config.ruolo_sistema`. Ogni consumer che voleva il vecchio
`'ADMIN'` ora usa direttamente questa funzione (`fn_is_super_admin`).

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

### Storico evoluzione

* **§4.6.B (apr-19)**: introdotta come sostituto del check
  `ruolo_sistema = 'ADMIN'` legacy.
* **PR-B (21-04-2026)**: GUC-aware (fail-closed in contesti non-OPERATORE).
* **Cutover §13.3.2 (19-04-2026)**: bridge legacy
  `risorse_umane_auth_user` rinominato `_legacy_...` e sostituito da
  vista. La vista esponeva ancora una colonna `ruolo_sistema`
  CASE-calcolata via LEFT JOIN pre-aggregato (per non chiamare questa
  fn N+1 volte).
* **Fase 7 (29-04-2026)**: rimossa la colonna `ruolo_sistema` dalla
  vista (e la subquery LEFT JOIN che la alimentava). Droppato il
  wrapper `fn_get_ruolo_sistema` e il type `config.ruolo_sistema`.
  Da qui in avanti `fn_is_super_admin` e' l'**unico** entry point
  per il check "bypass totale".
* **29-09-2026** (`20260929-10`, `-11`, regola del 2): la seconda delle
  due domande — «la credenziale ha un binding SUPER_ADMIN attivo?» — passa
  in [fn_is_super_admin_account](/dbzero/script/funzioni/fn_is_super_admin_account),
  perche' la chiede anche l'obbligo del secondo fattore, che vale su tutte
  le porte. Qui resta il cancello della veste; risultato invariato. Brief:
  brief-db-secondo-fattore-totp.

---

{% include-markdown "signature-core.md" %}
