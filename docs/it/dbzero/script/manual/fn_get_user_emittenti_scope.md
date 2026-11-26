## 📘 Documentazione Concettuale – Funzione `script.fn_get_user_emittenti_scope`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali) — la riga che dà a un operatore la sua azienda
>
> Approfondimento funzioni:
>
> * [script.fn_change_user_emittenti_scope](/dbzero/script/funzioni/fn_change_user_emittenti_scope) — il verbo che cambia l'assegnazione
> * [script.fn_applica_user_emittenti_scope](/dbzero/script/funzioni/fn_applica_user_emittenti_scope) — le regole dello spostamento
> * [script.fn_is_super_admin_account](/dbzero/script/funzioni/fn_is_super_admin_account) — se l'utente è SUPER_ADMIN
> * [script.fn_check_ultimo_super_admin_attivo](/dbzero/script/funzioni/fn_check_ultimo_super_admin_attivo) — il blocco dell'ultimo SUPER_ADMIN
>
> Guide:
>
> * [Gli emittenti fiscali](/guide/emittenti-fiscali) — Parte 2, il super admin assegna gli operatori
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — l'assegnazione dal drawer dell'operatore

---

### 🎯 Scopo Principale

Dice al drawer dell'operatore **com'è assegnato un utente** e **che cosa gli si può scegliere**. Ritorna sempre una
riga, anche per un utente senza assegnazione. Il drawer non deduce niente da sé: spegne le scelte e il Salva da
questa risposta.

---

### Firma

```sql
script.fn_get_user_emittenti_scope(
    p_auth_user_id config.user_emittenti_fiscali.auth_user_id%TYPE
) RETURNS TABLE (...)
```

| Colonna | Tipo | Che cosa dice |
| --- | --- | --- |
| `auth_user_id` | `config.user_emittenti_fiscali.auth_user_id%TYPE` | l'utente chiesto |
| `scope_mode` | `text` | `SINGLE` o `GLOBAL` (vedi sotto) |
| `emittente_id` | `config.user_emittenti_fiscali.emittente_fiscale_id%TYPE` | l'azienda della riga, `NULL` senza riga |
| `emittente_descrizione` | `anagrafiche.soggetti.ragione_sociale_completa%TYPE` | la ragione sociale del soggetto dell'azienda |
| `allowed_scope_modes` | `text[]` | le modalità che il drawer può offrire |
| `can_change_scope` | `boolean` | se l'assegnazione si può cambiare |
| `change_scope_reason` | `text` | perché no, in chiaro; `NULL` se si può |

Le quattro colonne `text`/`boolean` non sono il riflesso di una colonna: sono la forma della risposta.

---

### ⭐ `scope_mode` e `allowed_scope_modes`

| Utente | Riga | `scope_mode` | `emittente_id` | `allowed_scope_modes` |
| --- | --- | --- | --- | --- |
| Operatore | sì | `SINGLE` | la sua azienda | `['SINGLE']` |
| Operatore | no | `SINGLE` | `NULL` (da scegliere) | `['SINGLE']` |
| SUPER_ADMIN | sì | `SINGLE` | la sua azienda | `['GLOBAL','SINGLE']` |
| SUPER_ADMIN | no | `GLOBAL` | `NULL` | `['GLOBAL','SINGLE']` |

⛔ **Un operatore non è mai «globale».** Senza la riga non vede niente (fail-closed), e il verbo rifiuta di togliergli
l'azienda (`E_OPERATORE_SCOPE_GLOBALE_SOLO_SUPER_ADMIN`). Per questo un operatore appena creato è `SINGLE` con
l'azienda da scegliere, e non `GLOBAL`: il drawer gli mostra «Un solo emittente» con l'elenco vuoto, e tiene spento il
Salva finché non si sceglie.

La domanda «è SUPER_ADMIN?» è [script.fn_is_super_admin_account](/dbzero/script/funzioni/fn_is_super_admin_account)
sull'utente chiesto, la stessa della primitiva: non dipende dalla veste di chi guarda.

La `UNIQUE (auth_user_id)` della tabella tiene al massimo una riga: un operatore su più aziende non esiste, e
`allowed_scope_modes` resta un array perché la firma non lo vincola.

---

### `can_change_scope`

`NOT script.fn_check_ultimo_super_admin_attivo(p_auth_user_id)`: l'ultimo SUPER_ADMIN attivo non si sposta, perché
assegnarlo a un'azienda gli toglierebbe la vista sulle altre. `change_scope_reason` lo dice in chiaro.

---

### Caratteristiche

* `LANGUAGE sql STABLE`, `SECURITY INVOKER`: sola lettura.
* La base `(VALUES (p_auth_user_id))` e i `LEFT JOIN` danno la riga anche senza assegnazione.
* Nessun filtro sulla veste `OPERATORE`: il drawer chiede solo operatori, e un utente tecnico chiesto per diagnostica
  riceve comunque la sua riga.

Test: `db/pgtap/script/test-fn-get-user-emittenti-scope.sql`.

---

### Esempio

```sql
-- Operatore appena creato, senza azienda
SELECT scope_mode, emittente_id, allowed_scope_modes
  FROM script.fn_get_user_emittenti_scope(42);
-- 'SINGLE', NULL, {SINGLE}

-- SUPER_ADMIN senza azienda
SELECT scope_mode, allowed_scope_modes
  FROM script.fn_get_user_emittenti_scope(7);
-- 'GLOBAL', {GLOBAL,SINGLE}
```
