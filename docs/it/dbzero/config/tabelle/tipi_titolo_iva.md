{% include-markdown "it/dbzero/config/manual/tipi_titolo_iva.md" %}
# 📚 Tabella `tipi_titolo_iva`

> 📝 **Descrizione**
>
> Vocabolario dei TITOLI che sostituiscono l'aliquota ordinaria di una riga (D10 di brief-db-be-iva-risolutore-e-regime-cliente). ⭐ Non e' la tabella della dichiarazione d'intento: e' la FAMIGLIA di cui l'intento e' il primo caso. I quattro noti al 2026-08-29 sono INTENTO, USO_INDUSTRIALE, AGEVOLATA_104, COOPERATIVA, e rispondono tutti allo stesso schema: chi x per cosa vale x da quando a quando x con quale prova -&gt; quale codice IVA prende il posto di quello ordinario. Nascere col nome soggetti_intento avrebbe scambiato il caso particolare per la regola. ⚠️ ha_plafond e' la sola proprieta' che distingue le due specie: solo l'intento ha un contatore che si consuma, quindi il plafond NON e' la colonna portante della tabella dei titoli — e' una proprieta' di un TIPO. La riga di titolo porta il valore del tetto, il tipo dice se il tetto esiste; a tenerle insieme e' il guard anagrafiche.trgfn_soggetti_titoli_iva_guard_coerenza, perche' un CHECK di colonna non puo' leggere un'altra tabella. ⛔ Nessun flag richiede_protocollo: tutti e quattro hanno una prova documentale, ma di natura diversa, e una colonna che nessuna regola legge e' esattamente il difetto che questo cantiere sta chiudendo. Mono-lingua: la descrizione e' il label (stampo config.tipi_reso). Seed dal CSV 80_data/sql/config/tipi_titolo_iva.csv. rev 2026-08-29.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(64) | NO |  |
| codice | character varying(64) | NO |  |
| descrizione | character varying(160) | NO |  |
| ha_plafond | boolean | NO |  |
| attivo | boolean | NO | true |
| ordine | smallint | NO | 0 |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_titolo_iva | id |
| UNIQUE | uq_tipi_titolo_iva_codice | codice |
| UNIQUE | uq_tipi_titolo_iva_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_titolo_iva_attivo | `CREATE INDEX ix_tipi_titolo_iva_attivo ON config.tipi_titolo_iva USING btree (attivo)` |
| ix_tipi_titolo_iva_ordine | `CREATE INDEX ix_tipi_titolo_iva_ordine ON config.tipi_titolo_iva USING btree (ordine)` |
| pk_tipi_titolo_iva | `CREATE UNIQUE INDEX pk_tipi_titolo_iva ON config.tipi_titolo_iva USING btree (id)` |
| uq_tipi_titolo_iva_codice | `CREATE UNIQUE INDEX uq_tipi_titolo_iva_codice ON config.tipi_titolo_iva USING btree (codice)` |
| uq_tipi_titolo_iva_codice_interno | `CREATE UNIQUE INDEX uq_tipi_titolo_iva_codice_interno ON config.tipi_titolo_iva USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_titolo_iva_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_tipi_titolo_iva_a10_soggetti_titoli_iva_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'soggetti_titoli_iva', 'tipo_titolo_iva_id', 'id', 'attivo')` |
| trg_tipi_titolo_iva_a10_tipi_titolo_iva_tipi_soggetto_de_8953f3 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'tipi_titolo_iva_tipi_soggetto_dettaglio', 'tipo_titolo_iva_id', 'id', 'attivo')` |
| trg_tipi_titolo_iva_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_titolo_iva_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_titolo_iva_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_titolo_iva_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
