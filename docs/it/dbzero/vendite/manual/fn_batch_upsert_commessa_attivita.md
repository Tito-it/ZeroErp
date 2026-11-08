## 📘 Documentazione Concettuale – Funzione `vendite.fn_batch_upsert_commessa_attivita`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — le righe scritte
> * [vendite.commesse](/dbzero/vendite/tabelle/commesse) — la commessa
>
> Approfondimento funzioni:
>
> * [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita) — la madre chiamata per ogni riga
> * [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) — il resolver da cui viene lo snapshot pricing
> * [script.fn_sorgente_chiave](/dbzero/script/funzioni/fn_sorgente_chiave) — il BB che, nella madre, traduce la chiave del documento
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

Batch wrapper su [`vendite.fn_upsert_commessa_attivita`](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita): accetta un **array jsonb** di righe e per ciascuna chiama il single-upsert, riducendo N round-trip Python→DB a **1**. Gli errori sono raccolti in modalità collect-all (non bloccano le righe successive) e contatori `inserted`/`updated` sono distinti tramite il flag `is_new` restituito dal single-upsert.

Usato principalmente dalla pipeline "push commessa" del backend per materializzare in un colpo solo le attività di una commessa/ordine.

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

`qta_operativa`, `uom_operativa_id`, `factor_to_base`, `posticipa_al`, `tipo_doc_fiscale_id`, `valuta_id`, `area_geografica_id`, `listino_versione_id`, `listino_riga_id`, `prezzo_bloccato`, `pricing_mode`, `prezzo_da_riallineare`, `stato_approvazione`, `stato_emissione`, `sorgente_tipo_id`, `sorgente_chiave`, `sorgente_riga`, `tipo_movimento`, `causale_onere_id`, `meta`. Una chiave che il wrapper non conosce (per esempio `tipo_consumo`, o la vecchia `sorgente_uid`) si ignora.

#### La provenienza della riga: tipo, chiave, riga

* `sorgente_tipo_id` — il tipo del documento d'origine (`config.sorgenti`).
* `sorgente_chiave` — la chiave del documento in testo, **id o uid indifferentemente**: la madre
  la traduce con `script.fn_sorgente_chiave` nella colonna giusta (`sorgente_id` o `sorgente_uid`)
  secondo il `key_selector` del tipo. Il push la prende dal lister del documento.
* `sorgente_riga` — la riga del documento (la `riga_id` del lister); assente o `null` quando il
  documento non ha righe o la provenienza è il documento intero.

#### La causale dell'onere

`causale_onere_id` arriva a `p_causale_onere_id` della madre. Il push di ordini e bolle passa da
qui, e gli oneri del documento arrivano come `tipo_movimento = 'ONERE'`: la madre vuole ONERE ⇔
causale, quindi una riga-onere senza la chiave è rifiutata (errore raccolto in `errors`). Assente o
`null` = nessuna causale, come per la merce.

Se la chiave manca o è `null` JSON, il wrapper propaga `NULL` al single-upsert che applica il proprio `DEFAULT` sul parametro (es. `pricing_mode` → `'FIXED'`, `prezzo_bloccato` → `false`).

---

### Che cosa restituisce

Un record di aggregato: le righe processate, quante hanno prodotto un INSERT (`is_new` del
single-upsert), quante un UPDATE, e l'elenco degli errori (posizione, `segment_key`, messaggio)
delle righe fallite. Le righe processate sono sempre la somma degli altri tre.

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

### Note di migrazione

* 2026-04-15 — il payload porta le otto chiavi dello snapshot pricing v5; la firma del wrapper non
  cambia.
* 2026-10-09 — arriva la chiave `listino_riga_id` (brief-db-riga-listino-propagata-dalla-commessa).
* 2026-10-13 — la chiave `tipo_consumo` si ritira.
* 2026-11-03 — arriva la chiave `causale_onere_id`: senza, ogni riga-onere del push di ordini e bolle
  era rifiutata.
* 2026-11-07 — arriva la chiave `sorgente_riga`, e la chiave del documento passa da `sorgente_uid` a
  `sorgente_chiave`, che la madre traduce nella colonna tipizzata giusta
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
