## Documentazione Concettuale – Funzione `script.fn_check_almeno_un_super_admin_attivo`

> **Vedi anche**
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
>
**Tabelle correlate:**
>
[config.profili_accesso](/dbzero/config/tabelle/profili_accesso)
> [config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings)
> [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
>
**Trigger guard che la consumano:**
>
[config.trgfn_profili_accesso_bindings_guard_ultimo_super_admin](/dbzero/config/funzioni/trgfn_profili_accesso_bindings_guard_ultimo_super_admin)
> [anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_ultimo_super_admin)

---
### 🎯 Scopo Principale
(latest review 19-04-2026)

Helper puro di check (non solleva mai errori): ritorna `true` se nel
sistema esiste almeno **un'identità attiva** con **un binding attivo**
verso un `profili_accesso` di codice `SUPER_ADMIN`.

È la fonte di verità unica della condizione "il sistema ha un
amministratore raggiungibile" per:

1. `config.trgfn_profili_accesso_bindings_guard_ultimo_super_admin` (su
   UPDATE/DELETE di `profili_accesso_bindings`);
2. `anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin` (su
   UPDATE `attivo` di `identita_digitali`).

Entrambi i trigger chiamano questa funzione post-transizione: se
ritorna `false`, l'operazione viene abortita con
`E_PROFILO_ULTIMO_SUPER_ADMIN`.

---

### Input / Output

Nessun parametro. Ritorna `BOOLEAN`.

| Stato rilevato | Risultato |
|---|---|
| Esiste `identita_digitali.attivo=true` con `profili_accesso_bindings.attivo=true` verso `profili_accesso.codice='SUPER_ADMIN'` | `true` |
| Nessuna combinazione valida (sistema in lockout) | `false` |

---

### Condizione di "SUPER_ADMIN raggiungibile"

Tre livelli AND obbligatori:

```sql
profili_accesso.codice          = 'SUPER_ADMIN'
AND profili_accesso.attivo      = true
AND profili_accesso_bindings.attivo = true
AND identita_digitali.attivo    = true
```

Il binding deve essere di tipo **AD_HOC** (col `identita_digitale_id`
valorizzata): le altre forme (REPARTO/PORTALE) non portano SUPER_ADMIN
per convenzione (il profilo SUPER_ADMIN ha `tipo = 'SUPER_ADMIN'` che
è compatibile solo con binding AD_HOC — vedi guard di coerenza).

---

### Regole implementative

* `LANGUAGE sql STABLE` — read-only, inlineable.
* Single `EXISTS` short-circuit: appena trovato un admin valido ritorna
  `true` senza scansionare oltre.
* Nessun parametro: lo stato è globale, non "per utente".
* **Non solleva errori** — la raise è responsabilità dei trigger caller.

---

### Riferimenti

* [WIP multi-face-auth §13.3.6](/dev/work-in-progress/sviluppo-multi-face-auth)
* Codice errore `E_PROFILO_ULTIMO_SUPER_ADMIN` (id 384) in
  `config.messaggi_errore`.

---

{% include-markdown "signature-core.md" %}
