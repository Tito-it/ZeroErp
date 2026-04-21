## Documentazione Concettuale – Trigger function `anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin`

> **Vedi anche**
>
[script.fn_check_almeno_un_super_admin_attivo](/dbzero/script/funzioni/fn_check_almeno_un_super_admin_attivo)
> [config.trgfn_profili_accesso_bindings_guard_ultimo_super_admin](/dbzero/config/funzioni/trgfn_profili_accesso_bindings_guard_ultimo_super_admin)

---
### 🎯 Scopo Principale
(latest review 19-04-2026)

Guard anti-lockout simmetrico al guard su
`config.profili_accesso_bindings`, ma sul lato identità: impedisce di
disattivare un'identità che portava l'ultimo binding SUPER_ADMIN
attivo, evitando così il lockout del sistema.

Trigger associato:
```
trg_identita_digitali_a10_guard_ultimo_super_admin_upd
    AFTER UPDATE OF attivo
    FOR EACH ROW
```

### Quando scatta

Doppio short-circuit:

1. Solo transizione `attivo: true -> false`. Ogni altro UPDATE (meta,
   password, ecc.) è irrilevante.
2. Solo se l'identità disattivata portava effettivamente un binding
   SUPER_ADMIN attivo. Altrimenti il conteggio globale non può peggiorare.

Se entrambi i filtri passano, delega il check a
`script.fn_check_almeno_un_super_admin_attivo()`. Se ritorna `false`,
raise `E_PROFILO_ULTIMO_SUPER_ADMIN`.

### Perché serve un guard separato

Il guard sui bindings vede solo UPDATE/DELETE della tabella bindings.
Una disattivazione di `identita_digitali.attivo = false` rende
implicitamente invalidi tutti i suoi binding (fail-closed nel check)
ma non passa dal trigger bindings. Senza un guard dedicato sull'altra
tabella, un admin potrebbe disattivare la propria identità — o quella
altrui — rendendo inaccessibile il sistema.

### Single source of truth

Sia questo trigger sia quello sui bindings chiamano la **stessa**
funzione `script.fn_check_almeno_un_super_admin_attivo`. Evolutione
della condizione (es. aggiunta di ulteriori gate come
`bloccato_fino_a` scaduto) va fatta **solo lì** e propaga
automaticamente a entrambi i guard.

### Bypass / manutenzione

Vedi note del trigger gemello: per disabilitazioni massive in
manutenzione, `ALTER TABLE ... DISABLE TRIGGER` temporaneo.

### Codice errore

`E_PROFILO_ULTIMO_SUPER_ADMIN` (id 384). Contesto jsonb:
`op`, `identita_digitale_id`, `auth_user_id`, `ruolo_applicativo`.

### Riferimenti

* [WIP multi-face-auth §13.3.6](/dev/work-done/sviluppo-multi-face-auth)

---

{% include-markdown "signature-core.md" %}
