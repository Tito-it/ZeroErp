## Documentazione Concettuale – Trigger function `config.trgfn_profili_accesso_bindings_guard_ultimo_super_admin`

> **Vedi anche**
>
[script.fn_check_almeno_un_super_admin_attivo](/dbzero/script/funzioni/fn_check_almeno_un_super_admin_attivo)
> [anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_ultimo_super_admin)

---
### 🎯 Scopo Principale
(latest review 19-04-2026)

Guard anti-lockout sulla tabella `config.profili_accesso_bindings`:
impedisce che un UPDATE o DELETE di un binding SUPER_ADMIN attivo
lasci il sistema privo di amministratori raggiungibili.

Trigger associato:
```
trg_profili_accesso_bindings_a10_guard_ultimo_super_admin_upd_dlt
    AFTER UPDATE OR DELETE
    FOR EACH ROW
```

### Quando scatta

Short-circuit interno: la funzione ritorna immediatamente se `OLD.attivo
= false` oppure `OLD.profilo_accesso_id` non corrisponde a un profilo
di codice `SUPER_ADMIN`. In tutti gli altri casi il trigger verifica se
la transizione è "a rischio":

| Transizione | A rischio? |
|---|---|
| `DELETE` di binding SUPER_ADMIN attivo | Sì |
| `UPDATE attivo: true -> false` | Sì |
| `UPDATE profilo_accesso_id: SUPER_ADMIN -> altro` | Sì |
| `UPDATE identita_digitale_id` | Sì (nuova identità potrebbe non essere attiva) |
| `UPDATE meta / altri campi` senza cambi rilevanti | No — skip |

Se a rischio, chiama `script.fn_check_almeno_un_super_admin_attivo()`.
Se ritorna `false`, solleva `E_PROFILO_ULTIMO_SUPER_ADMIN` e la
transazione fallisce.

### Perché `AFTER` e non `BEFORE`

`AFTER` consente di verificare lo stato **post-modifica** della
tabella, inclusi eventuali effetti di cascata. Un `BEFORE` dovrebbe
simulare lo stato futuro (più complesso e duplicato rispetto al check
standard).

Impatto performance: trascurabile perché il check è un singolo EXISTS
inlineato, eseguito solo sui binding SUPER_ADMIN effettivamente
modificati.

### Bypass / manutenzione

Non esistono bypass documentati: se in manutenzione serve davvero
azzerare tutti i SUPER_ADMIN (es. bootstrap ambiente), occorre
disabilitare temporaneamente il trigger con `ALTER TABLE ... DISABLE
TRIGGER`, eseguire l'operazione, riabilitarlo. Solo utenti con
privilegio sulla tabella possono farlo.

### Codice errore

`E_PROFILO_ULTIMO_SUPER_ADMIN` (id 384). Contesto jsonb:
`op`, `old_binding_id`, `old_profilo_accesso_id`, `old_identita_digitale_id`.

### Riferimenti

* [WIP multi-face-auth §13.3.6](/dev/work-done/sviluppo-multi-face-auth)

---

{% include-markdown "signature-core.md" %}
