{% include-markdown "it/dbzero/anagrafiche/manual/soggetti_titoli_iva.md" %}
# 📚 Tabella `soggetti_titoli_iva`

> 📝 **Descrizione**
>
> I TITOLI IVA del soggetto: il documento registrato che sostituisce l'aliquota ordinaria di una riga (D10 di brief-db-be-iva-risolutore-e-regime-cliente). ⭐ Realizza il principio di D7 — l'influenza del soggetto sull'IVA passa SEMPRE da un titolo, mai da un default. E' la ragione per cui anagrafiche.clienti.iva_id e' stata tolta e NON sostituita da un soggetti.iva_id: spostare la colonna avrebbe riprodotto lo stesso difetto un piano piu' su. 🔴 PROPRIETARIO il soggetto, DESTINATARIO l'emittente, due colonne sulla stessa riga (D10-bis): il titolo appartiene alla partita IVA, ma si presenta a un fornitore preciso, con un protocollo suo e un importo suo. Lo stesso esportatore abituale che compra da due emittenti presenta due dichiarazioni — senza la seconda colonna i due plafond si consumerebbero da un solo contatore, cioe' un errore silenzioso su precisamente il numero che l'Agenzia delle Entrate verifica. ⚠️ AMBITO: e' la condizione di applicabilita' e non un'etichetta (D12). Lo stadio B del risolutore si valuta RIGA PER RIGA, e il titolo entra solo se l'articolo di quella riga ricade nel suo ambito: dieci righe e un titolo AGEVOLATA_104 ristretto a due articoli fanno due righe agevolate e otto ordinarie. Dichiarato (TUTTO / RISTRETTO), mai dedotto da un NULL. ⛔ Un titolo RISTRETTO senza righe figlie non copre niente, ed e' voluto: il caso si costruisce in due istruzioni, quindi un vincolo lo rifiuterebbe a meta' strada — il risolutore lo legge come «nessun articolo nell'ambito» e lascia l'aliquota ordinaria, che e' la direzione sicura. ⚠️ L'anti-sovrapposizione e' un EXCLUDE vero solo per ambito=TUTTO: per i ristretti la chiave attraversa la tabella figlia e la tiene il guard trgfn_soggetti_titoli_iva_ambiti_guard. Due titoli di TIPO DIVERSO possono coesistere legittimamente — chi vince su una riga lo decide D13, articolo &gt; categoria &gt; tutto, e sta nel risolutore. ⚠️ imponibile_utilizzato e' MEMORIZZATO (P3) ma e' la SOMMA del registro anagrafiche.soggetti_titoli_iva_movimenti (D5): una colonna memorizzata e forzabile a mano diverge in silenzio da cio' che rappresenta, e su un plafond quel numero e' proprio quello che il fisco verifica. ⛔ split_payment e cliente_pa NON sono titoli e non stanno qui: non cambiano l'aliquota, cambiano chi versa l'imposta (D4) — vivono su anagrafiche.soggetti. rev 2026-08-29.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_id | uuid | NO |  |
| emittente_fiscale_id | bigint | NO |  |
| tipo_titolo_iva_id | bigint | NO |  |
| iva_id | integer | NO |  |
| ambito | character varying(16) | NO | 'TUTTO'::character varying |
| valido_dal | date | NO |  |
| valido_al | date | YES |  |
| protocollo | character varying(64) | YES |  |
| data_ricezione | date | YES |  |
| riferimento | character varying(255) | YES |  |
| plafond | numeric(15,2) | YES |  |
| imponibile_utilizzato | numeric(15,2) | NO | 0 |
| attivo | boolean | NO | true |
| note | character varying(255) | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| validita | daterange | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_soggetti_titoli_iva_ambito |  |
| CHECK | chk_soggetti_titoli_iva_finestra |  |
| CHECK | chk_soggetti_titoli_iva_plafond_pos |  |
| FOREIGN KEY | fk_soggetti_titoli_iva_emittente | emittente_fiscale_id |
| FOREIGN KEY | fk_soggetti_titoli_iva_iva | iva_id |
| FOREIGN KEY | fk_soggetti_titoli_iva_soggetto | soggetto_id |
| FOREIGN KEY | fk_soggetti_titoli_iva_tipo | tipo_titolo_iva_id |
| PRIMARY KEY | pk_soggetti_titoli_iva | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_soggetti_titoli_iva_no_overlap | `CREATE INDEX ex_soggetti_titoli_iva_no_overlap ON anagrafiche.soggetti_titoli_iva USING gist (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, validita) WHERE ((attivo IS TRUE) AND ((ambito)::text = 'TUTTO'::text))` |
| ix_soggetti_titoli_iva_soggetto_emittente | `CREATE INDEX ix_soggetti_titoli_iva_soggetto_emittente ON anagrafiche.soggetti_titoli_iva USING btree (soggetto_id, emittente_fiscale_id)` |
| pk_soggetti_titoli_iva | `CREATE UNIQUE INDEX pk_soggetti_titoli_iva ON anagrafiche.soggetti_titoli_iva USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_soggetti_titoli_iva_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_soggetti_titoli_iva_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_soggetti_titoli_iva_a10_default_emittente_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_default_emittente_fiscale('SOLLEVA')` |
| trg_soggetti_titoli_iva_a10_emittenti_fiscali_require_at_7e7ab7 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_soggetti_titoli_iva_a10_emittenti_fiscali_require_at_7e7ab7 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_soggetti_titoli_iva_a10_guard_coerenza_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_guard_coerenza()` |
| trg_soggetti_titoli_iva_a10_guard_coerenza_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_guard_coerenza()` |
| trg_soggetti_titoli_iva_a10_iva_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_soggetti_titoli_iva_a10_iva_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_soggetti_titoli_iva_a10_soggetti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id', 'id')` |
| trg_soggetti_titoli_iva_a10_soggetti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id', 'id')` |
| trg_soggetti_titoli_iva_a10_soggetti_titoli_iva_ambiti_b_1221ee | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'soggetti_titoli_iva_ambiti', 'titolo_iva_id', 'id', 'attivo')` |
| trg_soggetti_titoli_iva_a10_soggetti_titoli_iva_moviment_d128b2 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'soggetti_titoli_iva_movimenti', 'titolo_iva_id', 'id', 'attivo')` |
| trg_soggetti_titoli_iva_a10_tipi_titolo_iva_require_atti_91d686 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_titolo_iva', 'attivo', 'tipo_titolo_iva_id', 'id')` |
| trg_soggetti_titoli_iva_a10_tipi_titolo_iva_require_atti_91d686 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_titolo_iva', 'attivo', 'tipo_titolo_iva_id', 'id')` |
| trg_soggetti_titoli_iva_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_soggetti_titoli_iva_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_soggetti_titoli_iva_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_titoli_iva_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_titoli_iva_z90_guard_ambito_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_guard_ambito()` |
| trg_soggetti_titoli_iva_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('soggetti_titoli_iva_id')` |
| trg_soggetti_titoli_iva_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('soggetti_titoli_iva_id')` |

---
{% include-markdown "signature-core.md" %}
