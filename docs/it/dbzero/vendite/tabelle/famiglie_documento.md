{% include-markdown "it/dbzero/vendite/manual/famiglie_documento.md" %}
# 📚 Tabella `famiglie_documento`

> 📝 **Descrizione**
>
> Catalogo delle famiglie di documento che si numerano su un registro. ⭐ Non e' un vocabolario che decora un CHECK: e' la sede da cui si DERIVA il presidio del cambio emittente del billing account. La regola — «lo spostamento di un BA si blocca quando anche un solo documento del BA e' gia' NUMERATO su un registro» — scritta come elenco di sub-select ha un difetto noto: il SESTO documento che un domani entra nei registri e che nessuno aggiunge al conteggio. Derivata da qui, quel documento entra nella regola il giorno in cui si registra la sua famiglia, e non esiste nessun elenco parallelo che possa restare indietro. ⭐ E' la stessa forma che config.sistema_codici usa per dire dove vive un codice (schema_tabella/nome_tabella/nome_colonna), ed e' lo stesso principio della primitiva di pulizia che scopre le figlie da pg_constraint: si condivide la funzione, non una copia della sua logica. ⚠️ colonna_numero e colonna_billing_account non sono ridondanti: il numero si chiama `numero` su fatture, ddt, ordini e resi ma `codice` sulla commessa, e il billing account e' NOT NULL su fatture e commesse mentre e' NULLABLE su ddt, ordini e resi — il predicato derivato deve saperlo e non puo' dedurlo. ⛔ Non c'e' nessun flag `conta_come_storia`: la regola decisa il 2026-08-30 e' CATEGORICA, e un flag che nessuno mettesse a false sarebbe una voce dichiarata e non implementata — la stessa specie di NESSUNA/MENSILE, tolte da chk_registri_fatturazione_reset il 2026-08-25. ⚠️ Chi aggiunge una famiglia deve anche darle un registro per emittente, o i documenti di quella famiglia non nascono. Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, C2-0.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice_interno | character varying(50) | NO |  |
| descrizione | character varying(120) | NO |  |
| colonna_numero | text | NO |  |
| colonna_billing_account | text | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| presidia_data_documento | boolean | NO | true |
| prefisso_default | character varying(8) | YES |  |
| lunghezza_default | integer | NO | 7 |
| colonna_serie | text | YES |  |
| ammette_regole_fiscali | boolean | NO | false |
| anno_nel_numero_default | boolean | NO | false |
| codice | character varying(50) | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_famiglie_documento_codice_nonvuoto |  |
| CHECK | chk_famiglie_documento_regole_fiscali_solo_fattura |  |
| FOREIGN KEY | fk_famiglie_documento_sorgenti | codice_interno |
| PRIMARY KEY | pk_famiglie_documento | id |
| UNIQUE | uq_famiglie_documento_codice | codice |
| UNIQUE | uq_famiglie_documento_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_famiglie_documento | `CREATE UNIQUE INDEX pk_famiglie_documento ON vendite.famiglie_documento USING btree (id)` |
| uq_famiglie_documento_codice | `CREATE UNIQUE INDEX uq_famiglie_documento_codice ON vendite.famiglie_documento USING btree (codice)` |
| uq_famiglie_documento_codice_interno | `CREATE UNIQUE INDEX uq_famiglie_documento_codice_interno ON vendite.famiglie_documento USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_famiglie_documento_a10_default_codice_ins | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_famiglie_documento_default_codice()` |
| trg_famiglie_documento_a10_guard_chiave_struttura_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_famiglie_documento_guard_struttura()` |
| trg_famiglie_documento_a10_guard_disattivazione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_famiglie_documento_guard_disattivazione()` |
| trg_famiglie_documento_a10_guard_riferimenti_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_famiglie_documento_guard_riferimenti()` |
| trg_famiglie_documento_a10_guard_riferimenti_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_famiglie_documento_guard_riferimenti()` |
| trg_famiglie_documento_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_famiglie_documento_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_famiglie_documento_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_famiglie_documento_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_famiglie_documento_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
