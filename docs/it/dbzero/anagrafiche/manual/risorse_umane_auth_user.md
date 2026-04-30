## 📘 Documentazione Concettuale – Vista `anagrafiche.risorse_umane_auth_user`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
>
**Tabelle correlate:**
>
[anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> [config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings)
> [config.profili_accesso](/dbzero/config/tabelle/profili_accesso)
>
**Funzioni correlate:**
>
[script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin) (concettualmente equivalente, non usata dalla vista per ragioni di performance)

---
### 🎯 Scopo Principale
(latest review 29-04-2026, post-Fase 7 cleanup)

**Attenzione:** dal 19-04-2026 `risorse_umane_auth_user` è una **vista**,
non più una tabella. La tabella originale è stata rinominata in
`anagrafiche._legacy_risorse_umane_auth_user` e archiviata.

**Update Fase 7 (29-04-2026):** la colonna `ruolo_sistema` è stata
**rimossa** dalla vista insieme alla relativa subquery `sa` su
`profili_accesso_bindings`. `config.ruolo_sistema` (enum legacy) è
stato droppato in chiusura di Fase 7. Per il check "is super admin"
usare direttamente
[`script.fn_is_super_admin(auth_user_id)`](/dbzero/script/funzioni/fn_is_super_admin).

La vista oggi è una proiezione liscia di `anagrafiche.identita_digitali`
filtrata su `ruolo_applicativo = 'OPERATORE'`, con `LEFT JOIN`
opzionale su `risorse_umane` per il campo legacy `risorsa_umana_id`.

Creata con `WITH (security_invoker = true)` per compatibilità con
Row Level Security (§4.9).

---

### Read-only

La vista è **letta** (nessuna regola INSTEAD OF). Tutti i writer
scrivono ora direttamente su `identita_digitali`:

* `fn_registra_tentativo_login`, `fn_check_blocco_login` (PR1 DB)
* `auth_repository`, `amm_software_repository` (PR-A backend)
* `fn_crea_risorsa_umana` (post-cutover: scrive `identita_digitali` +
  eventuale binding SUPER_ADMIN direttamente)

Un tentativo di `INSERT`/`UPDATE`/`DELETE` sulla vista fallisce con
errore PostgreSQL standard (no rule/trigger INSTEAD OF).

---

### Layout di output (post-Fase 7)

| Campo | Origine | Note |
|-------|---------|------|
| `id` | `identita_digitali.id` | PK surrogata |
| `risorsa_umana_id` | LEFT JOIN `risorse_umane.id` via `soggetto_ruolo_id` | Compat legacy |
| `auth_user_id` | `identita_digitali.auth_user_id` | |
| `attivo` | `identita_digitali.attivo` | |
| `meta` | `identita_digitali.meta` | |
| `data_insert` / `user_insert` / `data_update` / `user_update` | `identita_digitali.*` | Audit standard |
| `storicizza` | `identita_digitali.storicizza` | |
| `tx_id` | `identita_digitali.tx_id` | |
| `tentativi_falliti` | `identita_digitali.tentativi_falliti` | |
| `bloccato_fino_a` | `identita_digitali.bloccato_fino_a` | |
| `deve_cambiare_password` | `identita_digitali.deve_cambiare_password` | |
| `invito_inviato_at` | `identita_digitali.invito_inviato_at` | |
| `totp_obbligatorio` | `identita_digitali.totp_obbligatorio` | |

> ⚠️ **Rimossa in Fase 7 (2026-04-29):** colonna `ruolo_sistema`. Per
> ricostruirne la semantica legacy lato consumer:
>
> * `'ADMIN'` ↔ `script.fn_is_super_admin(auth_user_id)`
> * `'DISABILITATO'` ↔ `NOT script.fn_has_identita_attiva(auth_user_id, 'OPERATORE')`
> * `'OPERATIVO'` ↔ composizione delle due (`fn_has_identita_attiva` AND NOT `fn_is_super_admin`)

---

### Filtro `ruolo_applicativo = 'OPERATORE'`

La vista espone **solo** le identità operatore, coerentemente con la
semantica del bridge legacy. Le identità portale/shop/fornitore
**non** compaiono.

---

### Tabella `_legacy_risorse_umane_auth_user`

Contiene i dati pre-cutover (righe scritte dal backend legacy + dal
trigger-ponte durante PR1 DB). Archivio: **non scrivere**. Tutti gli
altri trigger framework (audit, storico, tx_id, guard persona fisica)
sono rimasti agganciati alla tabella legacy ma sono inerti perché non
ci sono più writer.

**Update Fase 7 (2026-04-29):** anche su questa tabella la colonna
`ruolo_sistema` è stata droppata (`ALTER TABLE ... DROP COLUMN`,
migration `90_end/20260429-19a`) per liberare la dipendenza dal type
`config.ruolo_sistema` prima del `DROP TYPE` finale. Le altre colonne
storiche (`id`, `risorsa_umana_id`, `auth_user_id`, `attivo`, audit)
restano intatte come backup forensico.

---

{% include-markdown "signature-core.md" %}
