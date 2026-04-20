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
(latest review 19-04-2026, post-cutover §13.3.2)

**Attenzione:** dal 19-04-2026 `risorse_umane_auth_user` è una **vista**,
non più una tabella. La tabella originale è stata rinominata in
`anagrafiche._legacy_risorse_umane_auth_user` e archiviata. La vista
mantiene il nome canonico per compatibilità con i reader esistenti
(grep su backend e test ha confermato zero writer Python residui prima
del cutover).

La vista riproduce il **layout** della ex tabella bridge leggendo dal
nuovo modello `anagrafiche.identita_digitali` filtrato su
`ruolo_applicativo = 'OPERATORE'`, con `ruolo_sistema` ricostruito
dinamicamente.

Creata con `WITH (security_invoker = true)` per compatibilità con
Row Level Security future (§4.9).

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

### Layout di output

La vista espone **esattamente** le colonne del bridge legacy:

| Campo | Origine | Note |
|-------|---------|------|
| `id` | `identita_digitali.id` | PK surrogata |
| `risorsa_umana_id` | JOIN `risorse_umane.id` via `soggetto_ruolo_id` | Compat legacy |
| `auth_user_id` | `identita_digitali.auth_user_id` | |
| `attivo` | `identita_digitali.attivo` | |
| `meta` | `identita_digitali.meta` | |
| `data_insert` / `user_insert` / `data_update` / `user_update` | `identita_digitali.*` | Audit standard |
| **`ruolo_sistema`** | **Calcolato (CASE)** | Vedi sotto |
| `storicizza` | `identita_digitali.storicizza` | |
| `tx_id` | `identita_digitali.tx_id` | |
| `tentativi_falliti` | `identita_digitali.tentativi_falliti` | |
| `bloccato_fino_a` | `identita_digitali.bloccato_fino_a` | |
| `deve_cambiare_password` | `identita_digitali.deve_cambiare_password` | |
| `invito_inviato_at` | `identita_digitali.invito_inviato_at` | |
| `totp_obbligatorio` | `identita_digitali.totp_obbligatorio` | |

---

### Ricostruzione `ruolo_sistema`

Il campo legacy `ruolo_sistema` (enum `ADMIN`/`OPERATIVO`/`DISABILITATO`)
è ricostruito dinamicamente:

```sql
CASE
    WHEN NOT id.attivo
      OR id.ruolo_applicativo = 'DISABILITATO'
      OR valido_dal > CURRENT_DATE
      OR valido_al  < CURRENT_DATE
        THEN 'DISABILITATO'
    WHEN sa.identita_digitale_id IS NOT NULL
        THEN 'ADMIN'
    ELSE 'OPERATIVO'
END
```

Dove `sa` è una sub-query `LEFT JOIN` pre-aggregata sui binding
`SUPER_ADMIN` attivi.

---

### Performance: LEFT JOIN vs chiamata funzione

La vista **non** chiama `fn_is_super_admin(id.auth_user_id)` per
ogni riga (pattern N+1 evitato). Usa invece un **LEFT JOIN** a una
sub-query pre-aggregata:

```sql
LEFT JOIN (
    SELECT pab.identita_digitale_id
      FROM config.profili_accesso_bindings pab
      JOIN config.profili_accesso pa
        ON pa.id = pab.profilo_accesso_id
     WHERE pab.attivo = true
       AND pa.attivo  = true
       AND pa.tipo    = 'SUPER_ADMIN'
       AND pab.identita_digitale_id IS NOT NULL
) sa ON sa.identita_digitale_id = id.id
```

L'indice parziale UNIQUE `uq_profili_accesso_bindings_identita`
garantisce al più una riga per identità, quindi non serve `DISTINCT`.
Un solo piano di query, indici FK sfruttati.

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

---

{% include-markdown "signature-core.md" %}
