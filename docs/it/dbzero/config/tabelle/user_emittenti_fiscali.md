{% include-markdown "it/dbzero/config/manual/user_emittenti_fiscali.md" %}
# 📚 Tabella `user_emittenti_fiscali`

> 📝 **Descrizione**
>
> Scope operativo: l'emittente fiscale su cui l'utente puo' operare. Modello 1-a-1, presidiato da UNIQUE(auth_user_id): al massimo una riga per utente, quindi al massimo un emittente. FAIL-CLOSED dal 2026-08-18 (P-2a): un operatore SENZA riga non vede NESSUN emittente. La riga mancante e' un errore di configurazione, non un permesso — prima di questa data valeva il contrario (vedeva tutti gli emittenti ed era indistinguibile da un super admin), ed era il difetto che P-2a ha chiuso. L'unico attore legittimamente multi-emittente e' il SUPER_ADMIN, che passa da fn_is_super_admin e non da questa tabella. Per restringersi a un singolo emittente il super admin usa la GUC app.current_emittente_id (solo restringente, mai allargante). Chi e' senza riga si vede con dbops.vw_operatori_senza_emittente. Catena: script.fn_get_emittenti_scope_pk_ids (canonica) -&gt; _sr_ids -&gt; fn_scope_ef_whitelist_via_*. Brief perimetro-emittente §2.5.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| auth_user_id | integer | NO |  |
| emittente_fiscale_id | bigint | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_config_user_emittenti_fiscali_auth_user | auth_user_id |
| FOREIGN KEY | fk_user_emittenti_fiscali_emittente | emittente_fiscale_id |
| PRIMARY KEY | pk_user_emittenti_fiscali | id |
| UNIQUE | uq_user_emittenti_fiscali_auth_user | auth_user_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_user_emittenti_fiscali_emittente_id | `CREATE INDEX ix_user_emittenti_fiscali_emittente_id ON config.user_emittenti_fiscali USING btree (emittente_fiscale_id)` |
| pk_user_emittenti_fiscali | `CREATE UNIQUE INDEX pk_user_emittenti_fiscali ON config.user_emittenti_fiscali USING btree (id)` |
| uq_user_emittenti_fiscali_auth_user | `CREATE UNIQUE INDEX uq_user_emittenti_fiscali_auth_user ON config.user_emittenti_fiscali USING btree (auth_user_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_user_emittenti_fiscali_a10_emittenti_fiscali_require_4dae7e | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_user_emittenti_fiscali_a10_emittenti_fiscali_require_4dae7e | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_user_emittenti_fiscali_a10_guard_delete_dlt | BEFORE | DELETE | `EXECUTE FUNCTION config.trgfn_user_emittenti_fiscali_guard_delete()` |
| trg_user_emittenti_fiscali_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('emittente_fiscale_id', 'E_CODICE_NON_MODIFICABILE')` |
| trg_user_emittenti_fiscali_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_user_emittenti_fiscali_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_user_emittenti_fiscali_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_user_emittenti_fiscali_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_user_emittenti_fiscali_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('user_emittenti_fiscali_id')` |
| trg_user_emittenti_fiscali_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('user_emittenti_fiscali_id')` |

---
{% include-markdown "signature-core.md" %}
