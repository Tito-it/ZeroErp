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

## Proposte automazione sviluppo DB

> Strumenti e script per accelerare lo sviluppo e ridurre errori manuali.

### Alta priorita` — risparmio quotidiano

#### 1. Script scaffolding changelog YAML

Generatore di boilerplate per nuovi changelog:

```bash
./scripts/new_changelog.sh --schema vendite --tipo create-fn --nome fn_mia_funzione
```

Genera file con naming corretto (`YYYYMMDD-NN-...`), SPDX header, `logicalFilePath`,
struttura changeSet. Elimina errori di naming e copia/incolla.

#### 2. Script scaffolding pgTAP

Dato un nome tabella/funzione, genera lo scheletro test:

```bash
./scripts/new_test.sh --schema vendite --tabella commesse
```

Genera automaticamente: test tabella esiste, test FK presenti, test trigger presenti,
test colonne audit, test constraint CHECK. Si aggiungono poi solo i test funzionali.

#### 3. Generatore loadUpdateData YAML da CSV

Legge il CSV header + ispeziona `information_schema.columns` e genera il YAML con
tipi corretti:

```bash
./scripts/gen_load_data.sh --csv 80_data/sql/vendite/stati_commessa.csv
```

Evita il mapping manuale colonne/tipi che oggi e` fonte di errori.

### Media priorita` — qualita` e sicurezza

#### 4. Linter %TYPE

Scansiona i YAML in `20_code/` e verifica che:

- Parametri funzione usino `%TYPE` dove esiste colonna corrispondente
- `RETURNS TABLE` usi `%TYPE` per colonne da tabella
- `DECLARE` usi `%TYPE`
- Segnala tipi espliciti come warning (non errore — calcolati come `bigint` per COUNT sono legittimi)

#### 5. Funzione DB `dbops.fn_setup_standard_table`

Applica l'intero pattern standard in un colpo:

```sql
SELECT dbops.fn_setup_standard_table(
  'vendite', 'nuova_tabella',
  p_audit => true,            -- trigger audit
  p_storico => true,          -- tabella storico + trigger
  p_tx_id => true,            -- trigger tx_id
  p_fk_index_policy => true   -- applica policy indici FK
);
```

Oggi servono 4-5 changeset separati per ogni nuova tabella. Ridurrebbe a 1 chiamata
piu` i changeset specifici (CHECK, trigger custom).

#### 6. Validatore pre-deploy

Script che prima di `liquibase update` verifica:

- CSV seed matchano le colonne della tabella (header vs `information_schema`)
- Nessun changelog modificato dopo push (confronto hash con `origin/main`)
- `processi` JSON in pipeline referenziano `task_code` validi
- FK referenziano tabelle esistenti

### Bassa priorita` — nice to have

#### 7. Generatore diff signature funzioni

Confronta la signature attuale (da `pg_proc`) con quella nel changelog nuovo e
avvisa se serve DROP:

```bash
./scripts/check_fn_signature.sh vendite.fn_list_commesse_emittibili
# Output: SIGNATURE CHANGED - DROP required (params: 4 -> 5)
```

#### 8. Report trigger per tabella

Genera un report delle tabelle con piu` trigger, utile per il consolidamento:

```bash
./scripts/trigger_report.sh
# vendite.clienti: 18 trigger (WARNING: >15)
# vendite.commesse: 12 trigger
# ...
```

#### 9. Template Liquibase per pattern ricorrenti

Template YAML parametrizzati per i pattern piu` comuni:

- `add-fk-with-guard.yaml.tpl` — FK + `trgfn_child_requires_active_parent` + `trgfn_prevent_deactivate`
- `add-lookup-table.yaml.tpl` — tabella lookup + seed + lock `codice_interno`
- `add-storico.yaml.tpl` — tabella storico + trigger storicizzazione

### Ordine consigliato di implementazione

| Prio | Script | Motivo |
|------|--------|--------|
| 1 | Scaffolding changelog YAML | Usato piu` volte al giorno, fonte di errori frequenti |
| 2 | Generatore loadUpdateData | Mapping manuale colonne/tipi e` tedioso e error-prone |
| 3 | Linter %TYPE | Previene inconsistenze viste in questa sessione |
| 4 | `fn_setup_standard_table` | ROI alto a lungo termine, riduce changeset ripetitivi |
| 5 | Validatore pre-deploy | Safety net prima di ogni deploy |
| 6 | Scaffolding pgTAP | Accelera la copertura test (gap critico) |

---

*Documento generato da valutazione qualitativa DB — febbraio 2026*
