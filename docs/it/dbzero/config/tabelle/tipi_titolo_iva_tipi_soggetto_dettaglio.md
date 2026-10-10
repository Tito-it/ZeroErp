{% include-markdown "it/dbzero/config/manual/tipi_titolo_iva_tipi_soggetto_dettaglio.md" %}
# 📚 Tabella `tipi_titolo_iva_tipi_soggetto_dettaglio`

> 📝 **Descrizione**
>
> Matrice: quali nature di dettaglio (config.tipi_soggetto_dettaglio) possono essere titolari di quale tipo di titolo IVA (config.tipi_titolo_iva). L'intento lo presenta un soggetto IVA, mai un privato; l'agevolazione L. 104 spetta a una persona fisica. ⭐ Nessuna riga attiva per una coppia = titolo NON ammesso: un dettaglio senza righe non e' libero (D-1). Una riga si ritira con attivo = false nel CSV, mai con un DELETE (D-6), e il ritiro e' rifiutato finche' esistono titoli vigenti che la usano. La leggono anagrafiche.fn_titolo_iva_ammesso e, attraverso lei, i guard sui titoli e sul cambio di natura del soggetto. Stampo: config.forme_giuridiche_tipi_soggetto_dettaglio. Seed dal CSV 80_data/sql/config/tipi_titolo_iva_tipi_soggetto_dettaglio.csv. Brief: brief-db-dati-fiscali-e-societari-del-soggetto (Parte D).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| tipo_titolo_iva_id | bigint | NO |  |
| tipo_soggetto_dettaglio_id | bigint | NO |  |
| attivo | boolean | NO | true |
| user_insert | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | YES |  |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_tti_tsd_tipo_soggetto_dettaglio | tipo_soggetto_dettaglio_id |
| FOREIGN KEY | fk_tti_tsd_tipo_titolo_iva | tipo_titolo_iva_id |
| PRIMARY KEY | pk_tipi_titolo_iva_tipi_soggetto_dettaglio | tipo_titolo_iva_id, tipo_soggetto_dettaglio_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_titolo_iva_tipi_soggetto_dettaglio | `CREATE UNIQUE INDEX pk_tipi_titolo_iva_tipi_soggetto_dettaglio ON config.tipi_titolo_iva_tipi_soggetto_dettaglio USING btree (tipo_titolo_iva_id, tipo_soggetto_dettaglio_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_titolo_iva_tipi_soggetto_dettaglio_a10_tipi_tit_2cb381 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_titolo_iva', 'attivo', 'tipo_titolo_iva_id', 'id')` |
| trg_tipi_titolo_iva_tipi_soggetto_dettaglio_a10_tipi_tit_2cb381 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_titolo_iva', 'attivo', 'tipo_titolo_iva_id', 'id')` |
| trg_tipi_titolo_iva_tipi_soggetto_dettaglio_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_titolo_iva_tipi_soggetto_dettaglio_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_titolo_iva_tipi_soggetto_dettaglio_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_tipi_titolo_iva_tipi_soggetto_dettaglio_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_tipi_titolo_iva_tsd_a10_guard_ritiro_upd_dlt | AFTER | DELETE | `EXECUTE FUNCTION config.trgfn_tipi_titolo_iva_tipi_soggetto_dettaglio_guard_ritiro()` |
| trg_tipi_titolo_iva_tsd_a10_guard_ritiro_upd_dlt | AFTER | UPDATE | `EXECUTE FUNCTION config.trgfn_tipi_titolo_iva_tipi_soggetto_dettaglio_guard_ritiro()` |

---
{% include-markdown "signature-core.md" %}
