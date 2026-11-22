# Proposta 8.2 — Audit Trail Permessi

> Specifica di implementazione per WIP `permessi-e-autorizzazioni.md`, task 8.2.
> Approccio: riutilizzare il pattern di storicizzazione generica gia' in uso su 80+ tabelle.

---

## 1. Obiettivo

Tracciare **ogni modifica** (UPDATE/DELETE) alle tabelle che definiscono profili,
override e ambito emittente degli utenti. In un sistema ERP le modifiche ai permessi
sono eventi critici: serve sapere *chi* ha cambiato *cosa*, *quando*, e qual era
il valore precedente.

---

## 2. Tabelle target (7)

| # | Schema | Tabella | PK type | Motivo |
|---|--------|---------|---------|--------|
| 1 | `config` | `profili_reparto_aree` | integer | Livello area ereditato dai reparti |
| 2 | `config` | `profili_reparto_azioni` | integer | Azioni di processo abilitate per reparto |
| 3 | `config` | `user_override_aree` | bigint | Override utente livello area |
| 4 | `config` | `user_override_oggetti` | bigint | Override utente livello model |
| 5 | `config` | `user_override_azioni` | bigint | Override utente azione processo |
| 6 | `config` | `user_emittenti_fiscali` | bigint | Whitelist emittenti per utente |
| 7 | `anagrafiche` | `risorse_umane_auth_user` | bigint | Contiene `ruolo_sistema` (ADMIN/OPERATIVO/DISABILITATO) |

**Nota su #7**: la tabella ponte `risorse_umane_auth_user` non fa parte delle sezioni 2-3
del WIP, ma contiene `ruolo_sistema` che e' il primo anello della catena di risoluzione.
Un cambio di ruolo sistema e' l'evento di permessi piu' critico (es. OPERATIVO → DISABILITATO)
e merita audit trail.

---

## 3. Approccio — Storicizzazione generica continua

### Cosa serve fare manualmente

Aggiungere **solo 2 colonne** a ciascuna delle 7 tabelle:

```sql
ALTER TABLE <schema>.<tabella>
  ADD COLUMN storicizza BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN tx_id UUID;
```

### Cosa fanno le automazioni (zero intervento manuale)

Una volta presenti le colonne, il framework di automazione DB provvede a tutto:

| Automazione | Cosa fa |
|-------------|---------|
| `STORICO_PROVISION` | Crea `storico.<tabella>` con struttura standard (FK, snapshot JSONB, valid_from/to) |
| `STORICO` | Crea trigger `trgx_z90_{table}_upd_dlt_storico` BEFORE UPDATE OR DELETE |
| `TX_ID` | Crea trigger `trg_{table}_ins_upd_gen_tx_id` BEFORE INSERT OR UPDATE |
| `proc_sync_storico_set_storicizza` | Registra le tabelle nel registry per modalita' continua |

Le tabelle permessi sono a basso volume di scritture (configurazione, non transazioni),
quindi l'overhead e' trascurabile.

---

## 4. Implementazione — Migration Liquibase

### File creati

| File | Contenuto |
|------|-----------|
| `00_schema/config/20260301-01-alter-permessi-add-storicizza-txid-mctit.yaml` | ALTER 6 tabelle config |
| `00_schema/anagrafiche/20260301-01-alter-risorse-umane-auth-user-add-storicizza-txid-mctit.yaml` | ALTER `risorse_umane_auth_user` |

### Post-deploy

Dopo `make db-migrate`, eseguire le automazioni per generare tabelle storico e trigger:

```sql
-- Dry-run per verifica
SELECT dbops.fn_run_automations('AUTO', ARRAY['config','anagrafiche'], true,
  ARRAY['STORICO_PROVISION','STORICO','TX_ID']);

-- Apply
SELECT dbops.fn_run_automations('AUTO', ARRAY['config','anagrafiche'], false,
  ARRAY['STORICO_PROVISION','STORICO','TX_ID']);
```

Il job schedulato `proc_sync_storico_set_storicizza` registrera' automaticamente
le 7 tabelle nel registry (rileva `storicizza DEFAULT true` via `pg_catalog`).

---

## 5. Query di esempio — consultare l'audit trail

### Storico di un profilo reparto area

```sql
SELECT valid_from, valid_to, tipo_operazione, user_insert, snapshot
FROM storico.profili_reparto_aree
WHERE profili_reparto_aree_id = 42
ORDER BY valid_from;
```

### Cambio ruolo sistema di un utente

```sql
SELECT valid_from, valid_to, user_insert,
       snapshot->>'ruolo_sistema' AS ruolo,
       tipo_operazione
FROM storico.risorse_umane_auth_user
WHERE (snapshot->>'auth_user_id')::int = 5
ORDER BY valid_from;
```

### Snapshot a un punto nel tempo

```sql
SELECT script.fn_get_snapshot_as_of(
  'config', 'user_override_aree', '42',
  'user_override_aree_id', '2026-02-15 10:00:00'
);
```

---

## 6. Impatto backend

- **Zero**: la storicizzazione e' trasparente a livello DB
- **Futuro**: endpoint `/api/v1/core/users/{id}/permessi-audit/` per esporre la timeline

---

## 7. Dipendenze

Tutte le dipendenze sono gia' esistenti e operative:

- `script.trgfn_storico_generic()`
- `dbops.trgfn_tx_id_managed()`
- `config.storico_set_storicizza`
- `script.fn_get_snapshot_as_of()` / `fn_get_record_id_as_of()`
- Framework automazione (`fn_run_automations`, `fn_run_automations_storico_provision`, etc.)
