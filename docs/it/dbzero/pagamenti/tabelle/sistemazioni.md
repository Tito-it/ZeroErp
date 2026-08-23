{% include-markdown "it/dbzero/pagamenti/manual/sistemazioni.md" %}
# 📚 Tabella `sistemazioni`

> 📝 **Descrizione**
>
> Il REGISTRO delle sistemazioni: che cosa e' stato deciso di fare di un'eccedenza, e che cosa ne e' venuto fuori. ⭐ Tre destinazioni — RIPORTO su un'altra fattura, RIMBORSO con bonifico, COMPENSAZIONE fra due documenti — e nessuna macchina nuova sotto: il riporto e' un fondo fattura con origine MANUALE, il rimborso e' una contabile a importi negativi, la compensazione e' una contabile sul centro dedicato (D15-a). ⭐ Si accoppia con vw_eccedenze_da_sistemare: la vista dice CHE COSA C'E' DA FARE, questa tabella CHE COSA E' STATO FATTO. ⚠️ Si chiamava `compensazioni` fino al 2026-08-22: il nome copriva una sola delle tre azioni, e chiamare «compensazione» un bonifico di rimborso sarebbe stato falso. ⛔ Scartato `regolazioni`, che in contabilita' sarebbe la parola piu' esatta: in un ERP per le utilities «regolazione» vuol dire un'altra cosa.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| data_esecuzione | timestamp with time zone | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| destinazione | character varying | NO |  |
| stato | character varying | NO | 'BOZZA'::character varying |
| importo | numeric | NO |  |
| motivo | text | YES |  |
| cliente_soggetto_ruolo_id | bigint | NO |  |
| emittente_soggetto_ruolo_id | bigint | NO |  |
| fattura_origine_id | bigint | NO |  |
| fattura_destinazione_id | bigint | YES |  |
| contabile_id | bigint | YES |  |
| fondo_source_id | bigint | YES |  |
| user_esecuzione | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_sistemazioni_destinazione |  |
| CHECK | chk_sistemazioni_documenti |  |
| CHECK | chk_sistemazioni_eseguita |  |
| CHECK | chk_sistemazioni_esito |  |
| CHECK | chk_sistemazioni_importo_non_zero |  |
| CHECK | chk_sistemazioni_motivo_obbligatorio |  |
| CHECK | chk_sistemazioni_stato |  |
| FOREIGN KEY | fk_sistemazioni_cliente | cliente_soggetto_ruolo_id |
| FOREIGN KEY | fk_sistemazioni_contabile | contabile_id |
| FOREIGN KEY | fk_sistemazioni_emittente | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_sistemazioni_fattura_destinazione | fattura_destinazione_id |
| FOREIGN KEY | fk_sistemazioni_fattura_origine | fattura_origine_id |
| FOREIGN KEY | fk_sistemazioni_fondo_source | fondo_source_id |
| PRIMARY KEY | pk_sistemazioni | id |
| UNIQUE | uq_sistemazioni_contabile | contabile_id |
| UNIQUE | uq_sistemazioni_fondo_source | fondo_source_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_sistemazioni_fattura_origine_id | `CREATE INDEX ix_sistemazioni_fattura_origine_id ON pagamenti.sistemazioni USING btree (fattura_origine_id)` |
| pk_sistemazioni | `CREATE UNIQUE INDEX pk_sistemazioni ON pagamenti.sistemazioni USING btree (id)` |
| uq_sistemazioni_contabile | `CREATE UNIQUE INDEX uq_sistemazioni_contabile ON pagamenti.sistemazioni USING btree (contabile_id)` |
| uq_sistemazioni_fondo_source | `CREATE UNIQUE INDEX uq_sistemazioni_fondo_source ON pagamenti.sistemazioni USING btree (fondo_source_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_sistemazioni_a10_fatture_fondi_fattura_source_requir_4dd4fb | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'fatture_fondi_fattura_source', 'attivo', 'fondo_source_id', 'id')` |
| trg_sistemazioni_a10_fatture_fondi_fattura_source_requir_4dd4fb | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'fatture_fondi_fattura_source', 'attivo', 'fondo_source_id', 'id')` |
| trg_sistemazioni_a10_guard_scope_dest_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fattura', 'fattura_destinazione_id')` |
| trg_sistemazioni_a10_guard_scope_dest_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fattura', 'fattura_destinazione_id')` |
| trg_sistemazioni_a10_guard_scope_origine_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fattura', 'fattura_origine_id')` |
| trg_sistemazioni_a10_guard_scope_origine_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fattura', 'fattura_origine_id')` |
| trg_sistemazioni_a15_guard_transizione_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_sistemazioni_guard_transizione()` |
| trg_sistemazioni_a15_guard_transizione_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pagamenti.trgfn_sistemazioni_guard_transizione()` |
| trg_sistemazioni_a20_guard_dati_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_sistemazioni_guard_dati()` |
| trg_sistemazioni_a20_guard_dati_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pagamenti.trgfn_sistemazioni_guard_dati()` |
| trg_sistemazioni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_sistemazioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_sistemazioni_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_sistemazioni_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
