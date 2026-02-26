# Migliorie generali da test valutazione

> Valutazione qualitativa del layer DB ZeroErp — febbraio 2026.
> Voto complessivo: **8.9/10** — design production-ready.

---

## Punti di forza

### 1. Trigger riusabili (9.5/10)

8 trigger generici in `dbops`/`script` riusati 470+ volte:

- `trgfn_child_requires_active_parent` — pattern padre/figlio universale
- `trgfn_prevent_deactivate_if_children` — protezione disattivazione
- `trgfn_storico_generic` — storicizzazione automatica
- `trgfn_audit_data_user_generic` — audit trail zero-effort
- `trgfn_tx_id_managed` — transaction ID centralizzato
- `trgfn_lock_columns` — protezione colonne immutabili

Livello di riuso raro anche in progetti enterprise.

### 2. Error handling centralizzato (9.5/10)

`script.fn_log_and_raise_error` con:

- Context JSONB strutturato
- `tx_id` per tracciabilita` cross-tabella
- Lookup messaggi in `config.messaggi_errore` (multi-lingua)
- Pattern consistente in tutte le funzioni

### 3. Audit/storico (9.5/10)

Automatico, snapshot-based, transaction-linked. Zero sforzo manuale.
Colonne standard: `data_insert`, `user_insert`, `data_update`, `user_update`, `tx_id`, `storicizza`.

### 4. FK index policy (9.5/10)

Approccio centralizzato in `dbops.fk_index_policy` invece di creare indici a mano.
Evita indici ridondanti, riduce overhead INSERT/UPDATE, centralizza le decisioni.

### 5. Liquibase workflow (9.5/10)

Separazione per fasi (schema -> code -> data), naming rigoroso,
regola "mai modificare changelog pushati" rispettata.

- 711 changeset totali
- 287 file in `00_schema`, 424 in `20_code`
- 128 migration con `runOnChange: true` (funzioni/trigger idempotenti)

### 6. Naming conventions (9.0/10)

94% aderenza: `pk_`, `fk_`, `ix_`, `uq_`, `chk_`, `trg_<fase>_`, `fn_`/`trgfn_`.

---

## Aree di miglioramento

### 1. Test coverage (7.0/10) — PRIORITA` ALTA

| Schema | Test | Note |
|--------|------|------|
| vendite | 46 | Ben coperto |
| anagrafiche | 27 | Buono |
| catalogo | 6 | Sufficiente |
| config | 5 | Da ampliare |
| dbops | 5 | Trigger generici meritano piu` edge-case |
| pagamenti | 4 | Minimo |
| script | 1 | Insufficiente |
| **contabilita** | **0** | **Critico — dominio business-critical** |
| **acquisti** | **0** | **Critico — specchia vendite** |
| **magazzino** | **0** | **Da coprire** |

**Totale**: ~94 test. Target consigliato: 200+ per copertura adeguata.

### 2. Documentazione manuale (8.5/10)

509 pagine manuali totali, ma gap su:

- `contabilita`: 0 pagine (gap critico)
- `magazzino`: 1 pagina
- `acquisti`: 3 pagine
- Viste: poca doc manuale (32 pagine vs 190+ per funzioni)

### 3. Complessita` trigger per tabella

Alcune tabelle hanno 15-18 trigger (es. `clienti` con 18 trigger).
Valutare consolidamento in trigger multi-step dove possibile.

### 4. Enum handling — guida mancante

Mix di due pattern senza regola documentata:

- **VARCHAR + CHECK**: `tipo_commessa`, `policy_fatturazione`, `priorita_operativa`
- **Lookup table + FK**: `stati_doc_fiscale`, `stati_commessa`

Serve una guida che chiarisca quando usare quale:

| Pattern | Quando usare |
|---------|-------------|
| VARCHAR + CHECK | Valori fissi, 2-5 opzioni, nessun flag operativo |
| Lookup table + FK | Valori con flag, configurabili, potenzialmente estensibili |

### 5. Test storico assenti

Il pattern `trgfn_storico_generic` non ha test pgTAP dedicati che verifichino:

- Correttezza snapshot JSONB
- Tipo operazione (U/D)
- Consistenza `valid_from`/`valid_to`

---

## Checklist migliorie

### Priorita` alta
- [ ] Aggiungere test contabilita (dominio business-critical, 0 test)
- [ ] Aggiungere test acquisti (specchia vendite, 0 test)
- [ ] Aggiungere test magazzino (0 test)
- [ ] Documentare contabilita (0 pagine manuali)

### Priorita` media
- [ ] Test storico: verificare snapshot JSONB, tipo operazione, valid_from/to
- [ ] Test dbops: edge-case su trigger generici (parent inattivo, deactivate con figli)
- [ ] Guida enum vs lookup table in `docs/it/linee-guida-sql.md`
- [ ] Ampliare doc viste (32 pagine attuali)
- [ ] Ampliare doc acquisti e magazzino

### Priorita` bassa
- [ ] Revisione trigger clienti — valutare consolidamento (18 trigger)
- [ ] Standardizzare lunghezza nomi trigger (alcuni >70 caratteri)
- [ ] Runbook deployment Liquibase
- [ ] Esempi test integrazione backend-DB

---

## Scorecard

| Area | Voto | Stato |
|------|------|-------|
| Schema organization | 9.5/10 | Eccellente |
| Naming conventions | 9.0/10 | Molto buono |
| Trigger patterns | 9.5/10 | Eccellente |
| Function patterns | 9.0/10 | Molto buono |
| Error handling | 9.5/10 | Eccellente |
| Audit/storico | 9.5/10 | Eccellente |
| FK index policy | 9.5/10 | Eccellente |
| Data integrity | 8.5/10 | Molto buono |
| Liquibase organization | 9.5/10 | Eccellente |
| Test coverage | 7.0/10 | Buono (gap critici) |
| Documentation | 8.5/10 | Molto buono (gap su 3 schemi) |
| **Media** | **8.9/10** | **Molto alto** |

---

*Documento generato da valutazione qualitativa DB — febbraio 2026*
