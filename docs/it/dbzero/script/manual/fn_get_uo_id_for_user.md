## Documentazione Concettuale – Funzione `script.fn_get_uo_id_for_user`

> **Vedi anche**
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
>
**Tabelle correlate:**
>
[anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)

---
### 🎯 Scopo Principale
(latest review 19-04-2026)

Helper di risoluzione: dato un `auth_user_id`, ritorna l'
`unita_organizzativa_id` della risorsa umana attiva associata
all'identità OPERATORE, in una singola query.

Sostituisce catene JOIN ripetute in vari resolver / query di dominio
(lookup UO dell'operatore corrente) consolidandole in una sola fonte.
Utile anche come fondamenta per future policy RLS che filtrino per
unità organizzativa.

---

### Input / Output

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_auth_user_id` | `anagrafiche.identita_digitali.auth_user_id%TYPE` | Django `auth_user.id` dell'utente corrente. |

Ritorna `INTEGER` (nullable): l'`unita_organizzativa_id` della RU o
`NULL` in tutti i casi di fallback.

---

### Semantica (fail-soft)

| Caso | Risultato |
|------|-----------|
| `auth_user_id` inesistente | `NULL` |
| Utente senza identità OPERATORE attiva (es. `CLIENTE_PORTALE`) | `NULL` |
| Identità OPERATORE attiva ma RU inattiva | `NULL` |
| RU attiva ma `unita_organizzativa_id` NULL | `NULL` |
| RU attiva con UO assegnata | `integer` UO id |

Il "fail-soft" (ritorno `NULL` anziché raise) è voluto: la funzione è
usata in contesti di lettura dove l'assenza di UO è uno stato
legittimo (es. utente non ancora completamente configurato).

---

### Catena di risoluzione

```
auth_user_id
  → identita_digitali (ruolo_applicativo = 'OPERATORE', attivo = true)
    → soggetti_ruoli (via id.soggetto_ruolo_id)
      → risorse_umane (attivo = true, soggetto_ruolo_id = id.soggetto_ruolo_id)
        → unita_organizzativa_id
```

Il JOIN su `soggetti_ruoli` è implicito: `identita_digitali.soggetto_ruolo_id`
e `risorse_umane.soggetto_ruolo_id` referenziano la stessa colonna.

---

### Determinismo

In presenza di **più risorse umane attive** per lo stesso
`soggetto_ruolo` (caso anomalo ma storicamente possibile con
storicizzazione), la funzione ordina per `valido_dal DESC` e ritorna la
più recente:

```sql
ORDER BY ru.valido_dal DESC
LIMIT 1
```

---

### Regole implementative

* `LANGUAGE sql STABLE` — inlineable dal planner.
* `%TYPE` su firma per allineamento alla colonna sorgente.
* Singola query senza PL/pgSQL, nessun loop, nessun side-effect.

---

### Uso tipico

```sql
-- Recupero UO corrente dell'operatore in una service query
SELECT *
  FROM config.unita_organizzative
 WHERE id = script.fn_get_uo_id_for_user(
         NULLIF(current_setting('app.current_user_id', true), '')::integer);
```

Può anche essere usata in policy RLS future per scope per UO (es.
"operatore vede solo documenti della sua UO").

---

### Riferimenti

* [WIP multi-face-auth §13.3.7](/dev/work-in-progress/sviluppo-multi-face-auth)

---

{% include-markdown "signature-core.md" %}
