{% include-markdown "it/dbzero/magazzino/manual/trasferimenti.md" %}
# 📚 Tabella `trasferimenti`

> 📝 **Descrizione**
>
> Il trasferimento INTERNO di merce (D-L2-g): dentro lo stesso magazzino, fra due ubicazioni, oppure fra due magazzini dello stesso emittente, senza trasporto. Il trasferimento con trasporto e' la bolla con causale TRASFERIMENTO (vendite.ddt). Stessa famiglia di inventari e rettifiche: DRAFT -&gt; CONFIRM -&gt; POSTED, CANCEL; POSTED lo scrive solo magazzino.fn_posta_trasferimento. Dal 2026-09-28 lo stesso magazzino in partenza e in arrivo e' ammesso (via chk_mag_trasferimenti_da_a_distinti): allora ogni riga deve andare da un'ubicazione a un'altra, motivo della check di registrazione.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| data | date | NO | script.fn_data_operativa() |
| stato_trasferimento | character varying(16) | NO | 'DRAFT'::character varying |
| magazzino_id_from | bigint | NO |  |
| magazzino_id_to | bigint | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| sorgente_riga | bigint | YES |  |
| sorgente_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_trasferimenti_sorgente_chiave |  |
| CHECK | chk_mag_trasferimenti_stato |  |
| FOREIGN KEY | fk_mag_trasf_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_mag_trasferimenti_magazzino_from | magazzino_id_from |
| FOREIGN KEY | fk_mag_trasferimenti_magazzino_to | magazzino_id_to |
| PRIMARY KEY | pk_mag_trasferimenti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_trasferimenti_data | `CREATE INDEX ix_mag_trasferimenti_data ON magazzino.trasferimenti USING btree (data)` |
| ix_mag_trasferimenti_from_to | `CREATE INDEX ix_mag_trasferimenti_from_to ON magazzino.trasferimenti USING btree (magazzino_id_from, magazzino_id_to)` |
| ix_mag_trasferimenti_stato | `CREATE INDEX ix_mag_trasferimenti_stato ON magazzino.trasferimenti USING btree (stato_trasferimento)` |
| pk_mag_trasferimenti | `CREATE UNIQUE INDEX pk_mag_trasferimenti ON magazzino.trasferimenti USING btree (id)` |
| uq_mag_trasf_sorgente_fk | `CREATE UNIQUE INDEX uq_mag_trasf_sorgente_fk ON magazzino.trasferimenti USING btree (sorgente_tipo_id, sorgente_uid) WHERE (sorgente_tipo_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_trasferimenti_a10_guard_sorgente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_sorgente_polimorfa_tipizzata()` |
| trg_trasferimenti_a10_guard_sorgente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_sorgente_polimorfa_tipizzata()` |
| trg_trasferimenti_a10_guard_stesso_emittente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION magazzino.trgfn_trasferimenti_guard_stesso_emittente()` |
| trg_trasferimenti_a10_guard_stesso_emittente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION magazzino.trgfn_trasferimenti_guard_stesso_emittente()` |
| trg_trasferimenti_a10_guard_transizione_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION magazzino.trgfn_documento_interno_guard_transizione('stato_trasferimento', 'zeroerp.magazzino_posting_trasferimento')` |
| trg_trasferimenti_a10_guard_transizione_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION magazzino.trgfn_documento_interno_guard_transizione('stato_trasferimento', 'zeroerp.magazzino_posting_trasferimento')` |
| trg_trasferimenti_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_trasferimenti_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_trasferimenti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_trasferimenti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_trasferimenti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_trasferimenti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_trasferimenti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('trasferimenti_id')` |
| trg_trasferimenti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('trasferimenti_id')` |

---
{% include-markdown "signature-core.md" %}
