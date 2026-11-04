{% include-markdown "it/dbzero/vendite/manual/registri_fatturazione.md" %}
# 📚 Tabella `registri_fatturazione`

> 📝 **Descrizione**
>
> Registri (sezionali) di NUMERAZIONE dei documenti di vendita, uno per emittente fiscale e per famiglia di documento: serie, politica della data, regole di reset e contatore in vendite.registri_fatturazione_progressivi. ⛔ IL NOME DICE MENO DI QUELLO CHE LA TABELLA FA, ED E' UN DEBITO DICHIARATO. Fino al 2026-08-30 qui vivevano i soli sezionali fiscali; dal 2026-08-31 la colonna famiglia_documento distingue FATTURA, DDT, ORDINE, COMMESSA e RESO, e il motore di numerazione e' lo stesso per tutti — la fattura compare ormai solo nel ramo d'errore di vendite.fn_get_next_progressivo. La descrizione precedente («registri/serie di numerazione per FATTURE DI VENDITA, per emittente/brand») non era incompleta: era falsa per quattro quinti del contenuto. ⚠️ Ne discende anche una correzione al COMMENT di famiglia_documento (changeSet 20260830-15, applicato e quindi non riscrivibile), che sosteneva «la descrizione della tabella dice gia' registri/serie di NUMERAZIONE, era il nome dell'oggetto a essere rimasto indietro»: meta' vero — diceva numerazione, ma diceva anche «per fatture di vendita» — e rimandava a un §12.5-bis del brief che non esiste, mentre il debito e' scritto al §3.8. ⭐ PERCHE' IL NOME RESTA: rinominare questa tabella significa rinominare vendite.registri_fatturazione_progressivi, i trigger, le funzioni che la interrogano, le viste, i vincoli e le colonne registro_id sparse su cinque tabelle di documento. E' un cantiere suo, e soprattutto un cantiere che non cambia NESSUN comportamento — cioe' esattamente il genere di lavoro che non si infila dentro uno che ne cambia molti, dove un errore di rename si confonderebbe con un errore di trasloco. Un debito dichiarato in quattro sedi (questo COMMENT, il COMMENT di famiglia_documento, la doc manuale, il brief §3.8) costa una frase; un rename fatto di fretta costa a chi verra' dopo. ⚠️ CHI LEGGE QUESTA TABELLA NON DEVE DEDURRE «fattura» DAL NOME: la famiglia si chiede a famiglia_documento, e vendite.fn_get_registro_documento RIFIUTA la famiglia FATTURA proprio perche' quella ha una strada sua (tipo documento + natura, via vendite.tipi_doc_fiscale_registri). ⚠️ Un registro non e' una categoria libera: e' la chiave del contatore, quindi due emittenti non condividono un registro (vendite.trgfn_fatture_guard_registro_emittente lo impedisce sulle fatture, e emittente_soggetto_ruolo_id e' NOT NULL dal 2026-08-30) e cambiare il serie_default di un registro vivo SPOSTA il sezionale. Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, C2-1 e C2-15.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| codice | character varying(80) | NO |  |
| descrizione | character varying(120) | NO |  |
| emittente_soggetto_ruolo_id | bigint | NO |  |
| serie_default | character varying(8) | YES |  |
| reset_policy | character varying(8) | NO | 'ANNUALE'::character varying |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| utility_id | integer | YES |  |
| politica_data_documento | character varying(32) | NO | 'OGGI'::character varying |
| limite_emissione_giorni | smallint | YES |  |
| limite_emissione_giorno_mese | smallint | YES |  |
| famiglia_documento | character varying(50) | NO | 'FATTURA'::character varying |
| prefisso | character varying(4) | YES |  |
| suffisso | character varying(4) | YES |  |
| lunghezza_numero | integer | NO | 7 |
| anno_nel_numero | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_registri_fatturazione_famiglia_regole_fattura |  |
| CHECK | chk_registri_fatturazione_limite_coerenza |  |
| CHECK | chk_registri_fatturazione_limite_giorni |  |
| CHECK | chk_registri_fatturazione_limite_giorno_mese |  |
| CHECK | chk_registri_fatturazione_politica_data |  |
| CHECK | chk_registri_fatturazione_reset |  |
| FOREIGN KEY | fk_registri_fatturazione_emitt | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_registri_fatturazione_famiglia | famiglia_documento |
| FOREIGN KEY | fk_registri_fatturazione_utility | utility_id |
| PRIMARY KEY | pk_regfatt | id |
| UNIQUE | uq_registri_fatturazione_codice | codice |
| UNIQUE | uq_registri_fatturazione_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_regfatt | `CREATE UNIQUE INDEX pk_regfatt ON vendite.registri_fatturazione USING btree (id)` |
| uq_registri_fatturazione_codice | `CREATE UNIQUE INDEX uq_registri_fatturazione_codice ON vendite.registri_fatturazione USING btree (codice)` |
| uq_registri_fatturazione_famiglia_emittente_utility | `CREATE UNIQUE INDEX uq_registri_fatturazione_famiglia_emittente_utility ON vendite.registri_fatturazione USING btree (famiglia_documento, emittente_soggetto_ruolo_id, utility_id) NULLS NOT DISTINCT WHERE ((famiglia_documento)::text <> 'FATTURA'::text)` |
| uq_registri_fatturazione_prefisso_suffisso | `CREATE UNIQUE INDEX uq_registri_fatturazione_prefisso_suffisso ON vendite.registri_fatturazione USING btree (emittente_soggetto_ruolo_id, prefisso, suffisso) NULLS NOT DISTINCT WHERE (((COALESCE(prefisso, ''::character varying))::text <> ''::text) OR ((COALESCE(suffisso, ''::character varying))::text <> ''::text))` |
| uq_registri_fatturazione_uid | `CREATE UNIQUE INDEX uq_registri_fatturazione_uid ON vendite.registri_fatturazione USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_registri_fatturazione_a10_commesse_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'commesse', 'registro_id', 'id', 'attivo')` |
| trg_registri_fatturazione_a10_ddt_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt', 'registro_id', 'id', 'attivo')` |
| trg_registri_fatturazione_a10_fatture_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture', 'registro_id', 'id', 'attivo')` |
| trg_registri_fatturazione_a10_guard_coppia_unica_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_registri_fatturazione_guard_coppia_unica()` |
| trg_registri_fatturazione_a10_guard_forma_numero_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_registri_fatturazione_guard_forma_numero()` |
| trg_registri_fatturazione_a10_guard_serie_ammessa_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_registri_fatturazione_guard_serie_ammessa()` |
| trg_registri_fatturazione_a10_guard_serie_ammessa_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_registri_fatturazione_guard_serie_ammessa()` |
| trg_registri_fatturazione_a10_ordini_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini', 'registro_id', 'id', 'attivo')` |
| trg_registri_fatturazione_a10_registri_fatturazione_prog_17cdc5 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'registri_fatturazione_progressivi', 'registro_id', 'id', 'attivo')` |
| trg_registri_fatturazione_a10_resi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'resi', 'registro_id', 'id', 'attivo')` |
| trg_registri_fatturazione_a10_set_anno_nel_numero_ins | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_registri_fatturazione_set_anno_nel_numero()` |
| trg_registri_fatturazione_a10_tipi_doc_fiscale_registri__d1c865 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'tipi_doc_fiscale_registri', 'registro_id', 'id', 'attivo')` |
| trg_registri_fatturazione_a10_vendite_contabili_block_de_3e2bbe | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pagamenti', 'vendite_contabili', 'registro_id', 'id', 'attivo')` |
| trg_registri_fatturazione_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_registri_fatturazione_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_registri_fatturazione_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_registri_fatturazione_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_registri_fatturazione_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_registri_fatturazione_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_registri_fatturazione_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('registri_fatturazione_id')` |
| trg_registri_fatturazione_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('registri_fatturazione_id')` |

---
{% include-markdown "signature-core.md" %}
