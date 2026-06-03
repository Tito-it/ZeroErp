## 📘 Documentazione Concettuale – Vista `vendite.vw_preventivi_list`

> ⚠️ **DEPRECATA (2026-06-03)** — sostituita dalla vista canonica
> [`vendite.vw_preventivi_lista`](/dbzero/vendite/views/vw_preventivi_lista) per
> la lista preventivi configurabile (sistema liste DEF-8). La nuova vista espone
> i **nomi canonici** (`ragione_sociale_completa`, `id_fiscale_univoco_cf_piva`,
> `ba_codice`) ed è `security_invoker=on`. Questa vista resta viva solo finché il
> backend non commuta `list_preventivi` e `list_revisioni` sulla canonica; poi
> verrà droppata con un changeset di cleanup dedicato. **Non usarla per nuovo
> codice.**

---

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi)
> [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
> [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> [config.utilities](/dbzero/config/tabelle/utilities)
> [config.valute](/dbzero/config/tabelle/valute)
> [config.termini_pagamento](/dbzero/config/tabelle/termini_pagamento)
>
Approfondimento funzioni:
> [anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_soggetto_coerenza_istanza)

---

### 🎯 Scopo Principale

(latest review 15-05-2026 — rev4)

`vendite.vw_preventivi_list` e' la vista denormalizzata principale per la **lista
preventivi vendita**. Espone tutti i dati necessari al frontend (tabella lista) e
al backend (filtro permessi per scope emittente).

---

### 🆕 Cambi rev4 (15-05-2026)

| Campo | Cambio |
| --- | --- |
| `is_revision_attiva` | **Rimosso** — colonna droppata da `vendite.preventivi` |
| `is_attiva` | **Nuovo**: derivata da `vendite.vw_preventivi` (`TRUE` se non esiste rev superiore non-abortita) |
| `FROM` | Cambiato da `vendite.preventivi` a **`vendite.vw_preventivi`** per ereditare `is_attiva` |

**Motivazione**: `is_revision_attiva` era un flag persistito soggetto a drift (in particolare
dopo annullamento di una revisione il predecessore restava con `FALSE` anche se era la rev viva).
Il nuovo modello deriva l'informazione da `stati_doc_preventivi.is_abortito`, eliminando
la necessità di aggiornare manualmente il flag.

---

### 🆕 Cambi rev3 (02-05-2026)

| Campo | Cambio |
| --- | --- |
| `cliente_denominazione`, `id_fiscale`, `soggetto_id` | Lookup spostato da BA → istanza_utilities (1 join, sempre valorizzato) |
| `id_fiscale` | **Nuovo**: `s.id_fiscale_univoco_cf_piva` esposto |
| `billing_account_codice` | **Nuovo**: `ba.codice` esposto, NULL ammesso per prospect |
| `istanza_utility_codice` | **Nuovo**: `iu.codice` esposto |
| `utility_codice`, `utility_descrizione` | **Nuovi**: LEFT JOIN `config.utilities` |
| `stato_codice_interno` | **Nuovo**: `sdp.codice_interno` esposto (oggi codice == codice_interno, esposto per pulizia future-proof) |

**Motivazione del cambio root del lookup soggetto** (da BA a istanza):

* `preventivi.istanza_utility_id` e' **NOT NULL** (post brief preventivi rev2)
* `istanze_utilities.soggetto_id` e' **NOT NULL** + FK diretta a `soggetti`
* Modello dati ZeroErp: 1 cliente per istanza (manuale `istanze_utilities` §7.3 "il cliente vive dentro l'istanza")
* Conseguenza: il soggetto via istanza coincide sempre con quello via BA → uso istanza, 1 join vs 3 join, e copre anche i preventivi prospect (BA NULL)

**Coerenza BA ↔ istanza**: garantita dal nuovo guard
[`trgfn_billing_account_guard_soggetto_coerenza_istanza`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_soggetto_coerenza_istanza)
che impone `soggetti_ruoli.soggetto_id == istanze_utilities.soggetto_id` su
INSERT/UPDATE di `billing_account`.

---

### Nota sulla colonna `emittente_fiscale_id`

Dalla revisione del **01-05-2026** (rev2) la vista legge direttamente
`p.emittente_fiscale_id` (colonna persistita, popolata dal trigger
`trgfn_preventivi_default_emittente` a INSERT-time). In precedenza la
chiamata dinamica a `fn_get_emittente_fiscale_pk(billing_account_id)`
esplodeva su `BA NULL` con `E_PARAMETRO_INVALIDO`.

---

### JOIN principali

| Tabella | Dati esposti | Note |
| --- | --- | --- |
| `config.stati_doc_preventivi` | `stato_codice`, `stato_codice_interno`, `stato_descrizione` | INNER JOIN |
| `anagrafiche.istanze_utilities` → `anagrafiche.soggetti` | `soggetto_id`, `cliente_denominazione`, `id_fiscale` | LEFT (defensive: in pratica sempre match grazie a NOT NULL) |
| `anagrafiche.billing_account` | `billing_account_codice`, `ba_utility_id` | LEFT JOIN: `billing_account_id` opzionale per prospect |
| `config.utilities` | `utility_codice`, `utility_descrizione` | LEFT (defensive: in pratica sempre match) |
| `config.valute` | `valuta_codice` | LEFT |
| `config.termini_pagamento` | `termine_pagamento_descrizione` | LEFT |

---

### 📑 Campi chiave esposti

* **Identificatori**: id, uid, numero, rev, **is_attiva**, data
* **Stato**: stato_doc_preventivo_id, stato_codice, **stato_codice_interno**, stato_descrizione
* **Billing account**: billing_account_id, **billing_account_codice**, ba_utility_id
* **Soggetto (via istanza)**: soggetto_id, cliente_denominazione, **id_fiscale**
* **Permessi**: emittente_fiscale_id (colonna persistita)
* **Utility e istanza**: utility_id, **utility_codice**, **utility_descrizione**, istanza_utility_id, **istanza_utility_codice**
* **Importi**: totale_imponibile, totale_iva, totale_documento
* **Condizioni**: valuta_id, valuta_codice, termine_pagamento_id, termine_pagamento_descrizione
* **Validita'**: validita_dal, validita_al, competenza_mese
* **Flag**: fatturazione_immediata, storicizza

**Ordinamento default**: `data DESC, numero DESC, id` (tiebreaker per stabilita').

---

### Esempio d'uso

```sql
-- Lista preventivi per un emittente, filtro stato, con dati cliente
SELECT id, numero, rev, data,
       stato_codice_interno, cliente_denominazione, id_fiscale,
       billing_account_codice,
       utility_codice, istanza_utility_codice,
       totale_documento, validita_al
  FROM vendite.vw_preventivi_list
 WHERE emittente_fiscale_id = 1
   AND stato_codice_interno = 'EMESSO'
 ORDER BY data DESC;
```

```sql
-- Preventivi prospect (senza BA): la denominazione e' comunque popolata
SELECT id, numero, cliente_denominazione, id_fiscale,
       billing_account_codice IS NULL AS is_prospect
  FROM vendite.vw_preventivi_list
 WHERE billing_account_id IS NULL
 ORDER BY data DESC
 LIMIT 20;
```

---

### Note operative

* **Nessuna LEFT JOIN ridondante**: anche per i preventivi prospect (`billing_account_id IS NULL`) la riga `vw_preventivi_list` ha `cliente_denominazione` e `id_fiscale` valorizzati grazie al join via istanza.
* **Coerenza dei valori**: per preventivi con BA valorizzato, il soggetto via istanza coincide con quello via BA (garantito dal guard `trgfn_billing_account_guard_soggetto_coerenza_istanza`). Se un giorno servisse il caso "chi paga ≠ chi intesta", il modello attuale **non lo supporta** (vedi tech debt nel manuale del guard).
* **Performance**: tutti i lookup sono su PK indicizzata (`pk_istanze_utilities`, `pk_soggetti`, `pk_billing_account`, `pk_utilities`, ecc.), zero scansioni full.

---

{% include-markdown "signature-core.md" %}
