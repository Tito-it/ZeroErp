## Documentazione Concettuale – Trigger function `anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin`

> **Vedi anche**
>
[script.fn_check_almeno_un_super_admin_attivo](/dbzero/script/funzioni/fn_check_almeno_un_super_admin_attivo)
> [config.trgfn_profili_accesso_bindings_guard_ultimo_super_admin](/dbzero/config/funzioni/trgfn_profili_accesso_bindings_guard_ultimo_super_admin)

---
### 🎯 Scopo Principale
(latest review 19-04-2026)

Guard anti-lockout simmetrico al guard su
`config.profili_accesso_bindings`, ma sul lato identità: impedisce le
scritture su un'identità SUPER_ADMIN che lascerebbero il sistema senza
**nessun SUPER_ADMIN senza scadenza**, evitando così il lockout, subito
o col calendario.

Trigger associato (dal 07-10-2026, `20261007-19`):
```
trg_identita_digitali_a10_guard_ultimo_super_admin_upd
    AFTER UPDATE
    FOR EACH ROW
    WHEN (attivo, valido_dal o valido_al cambiano)
```

⭐ **Dal 07-10-2026** (brief `brief-db-veste-utilizzabile`, decisione di Tid):
guarda anche le **date**. Una data che passa non scrive niente, e nessun guard
può fermare il calendario: se l'ultimo amministratore ha una data di fine, il
giorno dopo il sistema resta senza. Per questo la garanzia si chiede sulla
scrittura che **mette** la data, finché resta almeno un amministratore che non
scade ([fn_identita_super_admin_senza_scadenza](/dbzero/script/funzioni/fn_identita_super_admin_senza_scadenza)).
Il gemello sul rapporto è
[trgfn_risorse_umane_guard_ultimo_super_admin](/dbzero/anagrafiche/funzioni/trgfn_risorse_umane_guard_ultimo_super_admin).

### Quando scatta

Doppio short-circuit:

1. Solo le scritture che **riducono** la garanzia: spegnere la veste
   (`attivo: true -> false`), darle una data di fine (`valido_al` da vuoto a
   valorizzato), spostarne l'inizio nel futuro. Togliere una data di fine o
   riaccendere passano sempre, anche su un sistema già scoperto.
2. Solo se l'identità porta effettivamente un binding SUPER_ADMIN attivo.
   Altrimenti la garanzia non può peggiorare.

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
funzione `script.fn_check_almeno_un_super_admin_attivo`. Evoluzione
della condizione va fatta **solo lì** e propaga automaticamente a
tutti i guard. ⭐ È successo il 2026-09-25: la funzione ha imparato che
un SUPER_ADMIN la cui credenziale è **bloccata dall'amministratore**
([config.credenziali](/dbzero/config/tabelle/credenziali)) non è
raggiungibile, e un terzo guard — sul blocco stesso,
[config.trgfn_credenziali_guard_ultimo_super_admin](/dbzero/config/funzioni/trgfn_credenziali_guard_ultimo_super_admin)
— chiede alla stessa funzione.

### Bypass / manutenzione

Vedi note del trigger gemello: per disabilitazioni massive in
manutenzione, `ALTER TABLE ... DISABLE TRIGGER` temporaneo.

### Codice errore

`E_PROFILO_ULTIMO_SUPER_ADMIN` (id 384). Contesto jsonb:
`op`, `identita_digitale_id`, `auth_user_id`, `ruolo_applicativo`, e dal
07-10-2026 `attivo`, `valido_dal`, `valido_al` della riga nuova.

### Riferimenti

* [WIP multi-face-auth §13.3.6](/dev/work-done/sviluppo-multi-face-auth)

---

{% include-markdown "signature-core.md" %}
