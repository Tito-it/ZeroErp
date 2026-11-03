## 📘 Documentazione Concettuale – Funzione `vendite.fn_batch_upsert_commessa_attivita`

> **Ultimo aggiornamento**: 3 novembre 2026

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> • [vendite.commesse](/dbzero/vendite/tabelle/commesse)
>
**Approfondimento funzioni:**
>
• [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)
> • [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2)

---

### 🎯 Scopo Principale
(latest review 15-04-2026)

Batch wrapper su [`vendite.fn_upsert_commessa_attivita`](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita): accetta un **array jsonb** di righe e per ciascuna chiama il single-upsert, riducendo N round-trip Python→DB a **1**. Gli errori sono raccolti in modalità collect-all (non bloccano le righe successive) e contatori `inserted`/`updated` sono distinti tramite il flag `is_new` restituito dal single-upsert.

Usato principalmente dalla pipeline "push commessa" del backend per materializzare in un colpo solo le attività di una commessa/ordine.

---

### Firma

```sql
vendite.fn_batch_upsert_commessa_attivita(
    p_rows jsonb
)
RETURNS TABLE (
    total_rows integer,
    inserted   integer,
    updated    integer,
    errors     jsonb
)
```

La firma del wrapper **non cambia** con pricing v5: 1 parametro jsonb in input, 1 record di aggregato in output. Quello che cambia è la forma del **payload** atteso per ogni elemento dell'array (vedi sotto).

---

### Payload atteso per elemento

Ogni elemento di `p_rows` è un oggetto jsonb con chiavi che corrispondono 1:1 ai parametri `p_*` del single-upsert. Le chiavi **core** e le chiavi **snapshot pricing v5** sono obbligatorie lato contratto BE↔DB (il wrapper non solleva errore sulla mancanza perché usa `->>` NULL-safe, ma il payload deve essere generato correttamente per non perdere lo snapshot).

#### Chiavi core

`commessa_id`, `segment_key`, `articolo_id`, `istanza_utility_id`, `data_attivita`, `uom_id`, `quantita`, `competenza_mese`, `competenza_dal`, `competenza_al`, `prezzo_snapshot`.

#### Chiavi snapshot pricing v5 (obbligatorie nel payload)

| Chiave | Tipo JSON | Cast interno |
| --- | --- | --- |
| `prezzo_base_snapshot` | number / null | `numeric` |
| `origine_prezzo` | string / null | `varchar` |
| `tipo_variazione_applicata` | string / null | `varchar` |
| `valore_variazione_applicata` | number / null | `numeric` |
| `promo_id` | number / null | `bigint` |
| `contratto_id` | number / null | `bigint` |
| `categoria_cliente_id_snapshot` | number / null | `smallint` |
| `classe_utenza_id_snapshot` | number / null | `integer` |

Passare `null` JSON quando la dimensione non è applicabile (es. `classe_utenza_id_snapshot` su utility commercio, `promo_id` se origine ≠ `PROMO`).

#### Chiavi opzionali

`qta_operativa`, `uom_operativa_id`, `factor_to_base`, `posticipa_al`, `tipo_doc_fiscale_id`, `valuta_id`, `area_geografica_id`, `listino_versione_id`, `prezzo_bloccato`, `pricing_mode`, `prezzo_da_riallineare`, `stato_approvazione`, `stato_emissione`, `sorgente_tipo_id`, `sorgente_uid`, `tipo_movimento`, `meta`. Una chiave `tipo_consumo` (ritirata il 2026-10-13) si ignora.

Se la chiave manca o è `null` JSON, il wrapper propaga `NULL` al single-upsert che applica il proprio `DEFAULT` sul parametro (es. `pricing_mode` → `'FIXED'`, `prezzo_bloccato` → `false`).

---

### Output

| Campo | Tipo | Semantica |
| --- | --- | --- |
| `total_rows` | integer | Numero totale di righe processate (= `jsonb_array_length(p_rows)`) |
| `inserted` | integer | Righe che hanno prodotto INSERT (single-upsert `is_new = true`) |
| `updated` | integer | Righe che hanno prodotto UPDATE (`is_new = false`) |
| `errors` | jsonb | Array di oggetti `{index, segment_key, error}` per le righe fallite |

Vale: `total_rows = inserted + updated + jsonb_array_length(errors)`.

---

### Gestione errori

Per ogni riga il wrapper esegue il single-upsert dentro un `BEGIN ... EXCEPTION WHEN others ... END` **per-riga**:

* **Success** → contatore `inserted`/`updated` incrementato.
* **Errore** → oggetto JSON aggiunto ad `errors` con:
    * `index`: posizione (0-based) nell'array di input
    * `segment_key`: valore della chiave per identificare la riga
    * `error`: `SQLERRM` (messaggio testuale dell'errore)

Il loop **continua** sulla riga successiva. Il wrapper non solleva eccezioni: la responsabilità di decidere cosa fare in caso di errori parziali è lasciata al caller (es. rollback lato BE se `errors` non vuoto).

Casi degenerati:

* `p_rows IS NULL` oppure `jsonb_typeof(p_rows) <> 'array'` → ritorna `(0, 0, 0, '[]')` senza errore.
* `p_rows` array vuoto → idem.

---

### Dipendenze DB

* Funzioni: [`vendite.fn_upsert_commessa_attivita`](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita) (chiamata N volte).
* Nessuna lettura/scrittura diretta su tabelle: tutto passa dal single-upsert.

---

### Esempio d'uso (con snapshot pricing v5)

```sql
SELECT *
  FROM vendite.fn_batch_upsert_commessa_attivita(
    jsonb_build_array(
      jsonb_build_object(
        'commessa_id',                   12345,
        'segment_key',                   'ORD-1001-RIGA-1',
        'articolo_id',                   '8c5ce3a9-8f52-4d07-ae36-884c5f8d4a1f',
        'istanza_utility_id',            10,
        'data_attivita',                 '2026-06-01',
        'uom_id',                        1,
        'quantita',                      1,
        'competenza_mese',               '2026-06-01',
        'competenza_dal',                '2026-06-01',
        'competenza_al',                 '2026-06-30',
        'prezzo_snapshot',               90,
        'prezzo_base_snapshot',          100,
        'origine_prezzo',                'CATEGORIA',
        'tipo_variazione_applicata',     'PERCENTUALE',
        'valore_variazione_applicata',   -10,
        'promo_id',                      NULL,
        'contratto_id',                  NULL,
        'categoria_cliente_id_snapshot', 3,
        'classe_utenza_id_snapshot',     NULL
      ),
      jsonb_build_object(
        'commessa_id',                   12345,
        'segment_key',                   'ORD-1001-RIGA-2',
        'articolo_id',                   '8c5ce3a9-8f52-4d07-ae36-884c5f8d4a1f',
        'istanza_utility_id',            10,
        'data_attivita',                 '2026-06-01',
        'uom_id',                        1,
        'quantita',                      1,
        'competenza_mese',               '2026-06-01',
        'competenza_dal',                '2026-06-01',
        'competenza_al',                 '2026-06-30',
        'prezzo_snapshot',               42,
        'prezzo_base_snapshot',          42,
        'origine_prezzo',                'CONTRATTO_OVERRIDE',
        'tipo_variazione_applicata',     'NESSUNA',
        'valore_variazione_applicata',   NULL,
        'promo_id',                      NULL,
        'contratto_id',                  789,
        'categoria_cliente_id_snapshot', 3,
        'classe_utenza_id_snapshot',     NULL
      )
    )
  );
```

Output:

```text
 total_rows | inserted | updated | errors
------------+----------+---------+--------
          2 |        2 |       0 | []
```

---

{% include-markdown "signature-core.md" %}

### La causale dell'onere (rev 2026-11-03)

Dal `20261103-49` il payload porta la chiave facoltativa `causale_onere_id`, passata a
`p_causale_onere_id` della madre. Il push di ordini e bolle passa da qui, e gli oneri del documento
arrivano come `tipo_movimento = 'ONERE'`: la madre vuole ONERE ⇔ causale, quindi senza la chiave
ogni riga-onere era rifiutata (errore raccolto in `errors`). Assente o `null` = nessuna causale, come
per la merce.
