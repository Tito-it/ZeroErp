{% include-markdown "it/dbzero/dbops/manual/presidi_testi.md" %}
# 📚 Tabella `presidi_testi`

> 📝 **Descrizione**
>
> Il testo di un presidio per CHI DEVE AGIRE, per lingua: `significato` (cosa vuol dire una riga) e `azione` (cosa fare per spegnerlo). ⛔ Non sostituisce il COMMENT della vista ne' la `nota` di dbops.presidi: quelli sono scritti per chi MANTIENE il presidio e restano com'erano. Chi lo spegne e' un dato del presidio, non del testo: dbops.presidi.chi_agisce. Lo leggono il pannello dei processi automatici e il digest (che va per email, senza i locali del frontend: per questo il testo sta a DB, come config.messaggi_errore). La completezza — ogni presidio attivo, non obsoleto e non INVENTARIO ha la riga `it` — la garantisce il pgTAP dbops/test-presidi-testi-v1, perche' un CHECK non guarda un'altra tabella. Seed: 80_data/sql/dbops/presidi_testi.csv. Brief: brief-db-presidi-cosa-significa-cosa-fare §4.1.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| vista | text | NO |  |
| lingua | text | NO |  |
| significato | text | NO |  |
| azione | text | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_presidi_testi_azione_non_vuota |  |
| CHECK | chk_presidi_testi_significato_non_vuoto |  |
| FOREIGN KEY | fk_presidi_testi_lingue | lingua |
| FOREIGN KEY | fk_presidi_testi_presidi | vista |
| PRIMARY KEY | pk_presidi_testi | id |
| UNIQUE | uq_presidi_testi_vista_lingua | vista, lingua |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_presidi_testi | `CREATE UNIQUE INDEX pk_presidi_testi ON dbops.presidi_testi USING btree (id)` |
| uq_presidi_testi_vista_lingua | `CREATE UNIQUE INDEX uq_presidi_testi_vista_lingua ON dbops.presidi_testi USING btree (vista, lingua)` |

---
{% include-markdown "signature-core.md" %}
