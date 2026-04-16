## 📘 Documentazione Concettuale – Funzione `vendite.fn_upsert_commessa_attivita`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> • [vendite.commesse](/dbzero/vendite/tabelle/commesse)
> • [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa)
> • [vendite.promo_articoli](/dbzero/vendite/tabelle/promo_articoli)
> • [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> • [anagrafiche.categorie_clienti](/dbzero/anagrafiche/tabelle/categorie_clienti)
> • [config.classi_utenze](/dbzero/config/tabelle/classi_utenze)
>
**Approfondimento funzioni:**
>
• [vendite.fn_batch_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_batch_upsert_commessa_attivita)
> • [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2)
> • [vendite.fn_get_commessa_stato](/dbzero/vendite/funzioni/fn_get_commessa_stato)
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---

### 🎯 Scopo Principale
(latest review 15-04-2026)

Upsert idempotente di una riga `vendite.commesse_attivita` sulla chiave `(commessa_id, segment_key)`, con **snapshot pricing v5** obbligatorio in firma. Restituisce `(attivita_id, is_new)` per distinguere INSERT da UPDATE (via `xmax = 0` nel RETURNING).

Tre gruppi di validazione applicativa (`E_PARAMETRO_INVALIDO`) + tre guard di coerenza con lo stato commessa:

| Gruppo | Fail-fast |
| --- | --- |
| Parametri core | Null/≤0 su ID, segment_key vuota o > 128 char, quantità = 0, prezzo_snapshot NULL |
| Dominio enum snapshot v5 | `origine_prezzo` ∈ {PROMO, CONTRATTO_OVERRIDE, CONTRATTO_LISTINO, CATEGORIA, MANUALE}; `tipo_variazione_applicata` ∈ {PERCENTUALE, VALORE_FISSO, PREZZO_FISSO, NESSUNA} |
| Classificazione operativa | `tipo_movimento` ∈ {NORMALE, RETTIFICA}; `tipo_consumo` ∈ {ACCONTO, CONGUAGLIO, STORNO} |

---

### Parametri

#### Core (obbligatori, posizionali)

| Parametro              | Tipo     | Note                                                             |
| ---------------------- | -------- | ---------------------------------------------------------------- |
| `p_commessa_id`        | bigint   | >0; lookup su `vendite.commesse`                                 |
| `p_segment_key`        | varchar  | Trimmed, non vuoto, ≤ 128 char                                   |
| `p_articolo_id`        | uuid     | FK `catalogo.articoli`                                           |
| `p_istanza_utility_id` | bigint   | >0; FK `anagrafiche.istanze_utilities`                           |
| `p_data_attivita`      | date     | Data dell'attività erogata                                       |
| `p_uom_id`             | bigint   | >0; FK `catalogo.unita_misura`                                   |
| `p_quantita`           | numeric  | ≠ 0 (negativi ammessi per rettifiche/utility)                    |
| `p_competenza_mese`    | date     | Normalizzato al primo giorno del mese via `date_trunc('month')`  |
| `p_competenza_dal`     | date     | Inizio competenza                                                |
| `p_competenza_al`      | date     | Fine competenza                                                  |
| `p_prezzo_snapshot`    | numeric  | Obbligatorio; negativi ammessi (storni)                          |

#### Snapshot pricing v5 (obbligatori, posizionali dopo `p_prezzo_snapshot`)

Tutti obbligatori in firma. Passare `NULL` esplicito quando la dimensione non si applica (es. `p_classe_utenza_id_snapshot` per utility commercio, `p_promo_id` se origine ≠ PROMO).

| Parametro | Tipo | Valore tipico |
| --- | --- | --- |
| `p_prezzo_base_snapshot` | numeric(22,10) | Prezzo base pre-variazione (ritornato da `fn_resolve_prezzo_listino_v2.prezzo_base_snapshot`) |
| `p_origine_prezzo` | varchar(32) | Enum: `PROMO` \| `CONTRATTO_OVERRIDE` \| `CONTRATTO_LISTINO` \| `CATEGORIA` \| `MANUALE` |
| `p_tipo_variazione_applicata` | varchar(16) | Enum: `PERCENTUALE` \| `VALORE_FISSO` \| `PREZZO_FISSO` \| `NESSUNA` |
| `p_valore_variazione_applicata` | numeric(10,4) | Valore effettivo della variazione applicata |
| `p_promo_id` | bigint | FK `vendite.promo_articoli`; NOT NULL solo se origine = PROMO |
| `p_contratto_id` | bigint | FK `vendite.contratti`; NOT NULL se origine CONTRATTO_* |
| `p_categoria_cliente_id_snapshot` | smallint | FK `anagrafiche.categorie_clienti`; congela la categoria |
| `p_classe_utenza_id_snapshot` | integer | FK `config.classi_utenze`; NULL per utility senza dimensione |

#### Opzionali (con DEFAULT, dopo lo snapshot)

`p_qta_operativa`, `p_uom_operativa_id`, `p_factor_to_base` (default 1), `p_posticipa_al`, `p_tipo_doc_fiscale_id`, `p_valuta_id`, `p_area_geografica_id`, `p_listino_versione_id`, `p_prezzo_bloccato` (default false), `p_pricing_mode` (default `FIXED`), `p_prezzo_da_riallineare` (default false), `p_stato_approvazione` (default `BOZZA`), `p_stato_emissione` (default `NON_EMESSA`), `p_sorgente_tipo_id`, `p_sorgente_uid`, `p_tipo_movimento` (default `NORMALE`), `p_tipo_consumo` (default `CONGUAGLIO`), `p_meta` (default `'{}'::jsonb`).

---

### Output

```sql
RETURNS TABLE (
    attivita_id bigint,
    is_new      boolean
)
```

| Campo | Semantica |
| --- | --- |
| `attivita_id` | `id` della riga `commesse_attivita` inserita o aggiornata |
| `is_new` | `true` se INSERT, `false` se UPDATE (determinato da `xmax = 0` nel RETURNING) |

---

### Regole UPDATE (ON CONFLICT)

* Tutte le colonne **sovrascritte** da EXCLUDED tranne `meta`: il `meta` esistente viene **mergeato** con quello in input (`COALESCE(meta, '{}') || COALESCE(EXCLUDED.meta, '{}')`). Chi usa `tipo_movimento`/`tipo_consumo` in meta li vede aggiornati.
* Snapshot pricing v5: **sovrascrive sempre** (rappresenta lo snapshot del calcolo corrente; se il resolver è stato rieseguito, il nuovo risultato vince).
* Guard: se la riga esistente ha `stato_emissione ≠ NON_EMESSA`, update bloccato con `E_COMMESSA_ATTIVITA_GIA_EMESSA`.

---

### Errori sollevati

Via `script.fn_log_and_raise_error` (`SQLSTATE 'P0001'`).

| Codice | Quando |
| --- | --- |
| `E_PARAMETRO_INVALIDO` | ID NULL/≤0, segment_key invalida, quantità = 0, prezzo_snapshot NULL, enum fuori dominio, tipo_movimento/consumo invalidi |
| `E_COMMESSA_NON_TROVATA` | `commessa_id` non esiste in `vendite.commesse` |
| `E_COMMESSA_NON_MODIFICABILE` | `stati_commessa.modificabile = false` per lo stato corrente |
| `E_COMMESSA_ATTIVITA_GIA_EMESSA` | Riga esistente con `stato_emissione ≠ NON_EMESSA` |

---

### Dipendenze DB

* Tabelle: `vendite.commesse_attivita`, `vendite.commesse`, `vendite.stati_commessa`.
* Funzioni: `script.fn_log_and_raise_error`.
* Trigger/CHECK DB: `chk_commesse_attivita_origine_prezzo`, `chk_commesse_attivita_tipo_variazione_applicata` garantiscono i domini enum anche se il guard applicativo è bypassato.

---

### Esempio d'uso (con snapshot pricing v5)

```sql
SELECT *
  FROM vendite.fn_upsert_commessa_attivita(
    p_commessa_id                   => 12345,
    p_segment_key                   => 'ORD-1001-RIGA-1',
    p_articolo_id                   => '8c5ce3a9-8f52-4d07-ae36-884c5f8d4a1f',
    p_istanza_utility_id            => 10,
    p_data_attivita                 => DATE '2026-06-01',
    p_uom_id                        => 1,
    p_quantita                      => 1,
    p_competenza_mese               => DATE '2026-06-01',
    p_competenza_dal                => DATE '2026-06-01',
    p_competenza_al                 => DATE '2026-06-30',
    p_prezzo_snapshot               => 90,
    -- Snapshot pricing v5 (risultato di fn_resolve_prezzo_listino_v2)
    p_prezzo_base_snapshot          => 100,
    p_origine_prezzo                => 'CATEGORIA',
    p_tipo_variazione_applicata     => 'PERCENTUALE',
    p_valore_variazione_applicata   => -10,
    p_promo_id                      => NULL,
    p_contratto_id                  => NULL,
    p_categoria_cliente_id_snapshot => 3,       -- es. SILVER
    p_classe_utenza_id_snapshot     => NULL     -- utility commercio
  );
```

Output:

```text
 attivita_id | is_new
-------------+--------
    7890123  | t
```

---

{% include-markdown "signature-core.md" %}
