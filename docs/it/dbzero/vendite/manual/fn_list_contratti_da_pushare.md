## Documentazione Concettuale – Funzione `vendite.fn_list_contratti_da_pushare(...)`

> **Vedi anche**
>
[vendite.contratti](/dbzero/vendite/tabelle/contratti)
> [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe)
> [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa)
> [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)

---
### 🎯 Scopo Principale
`vendite.fn_list_contratti_da_pushare(...)` seleziona le righe contratto
pronte per il push verso `commesse_attivita`, restituendo un payload completo
per l'handler di acquisizione.

A differenza di preventivi e ordini (una tantum), un contratto puo` avere
righe ricorrenti (canoni, quote fisse mensili). Per garantire idempotenza
su piu` periodi il `segment_key` include il mese di competenza.

---

### Regole principali

* considera contratti in stato documento `ATTIVO`. Se lo stato non si trova nel
  catalogo (riga assente o spenta) la funzione solleva `E_CODICE`, come per la
  sorgente: non lista mai contratti in uno stato qualunque (fino al 2026-10-10 il
  filtro era `IS NULL OR` e in quel caso cadeva). Nessun filtro sul billing
  account: la colonna è `NOT NULL` (D-1 e D-2 di
  `brief-db-istanza-nasce-col-ba-residui`);
* contratto in validita` (`valido_al IS NULL` o `>= competenza_mese/oggi`);
* include solo righe attive con articolo valido;
* esclude segmenti gia` emessi in `commesse_attivita` (idempotenza batch);
* costruisce `segment_key` deterministica (`CONTR:{uid}:R:{riga_id}:M:{YYYY-MM}`);
* `prezzo_bloccato = TRUE` se `prezzo_unitario` presente nel contratto;
* sorgente tipo: `CONTRATTO` da `config.sorgenti` (id=4);
* supporta filtri opzionali:
  * `p_competenza_mese`
  * `p_billing_account_id`
  * `p_limit`
  * `p_contratto_id` *(2026-05)* — vedi sezione dedicata

---

### Push singolo contratto (estensione coordinata)

> **Aggiunto:** 2026-05 — migration `20260510-03`

Il parametro `p_contratto_id` (tipo `vendite.contratti.id%TYPE`, default `NULL`) consente
di restringere il risultato a un singolo contratto.

| Valore  | Comportamento                                                  |
|---------|----------------------------------------------------------------|
| `NULL`  | Lista globale — comportamento batch invariato                  |
| `> 0`   | Filtra al contratto specificato; tutti gli altri filtri in AND |
| `<= 0`  | Guard: solleva `E_PUSH_SORGENTE_ID_INVALIDO` (id 433)          |

Estensione coordinata con le altre 4 `fn_list_*_da_pushare` per uniformare
la signature al client Python `CommesseRepository.fetch_pushable_rows` (4 args posizionali).

---

### Output (alto livello)

Restituisce per ogni riga candidata:
* contesto documento (`contratto_id`, `contratto_uid`, `riga_id`),
* dati commessa/competenza (`billing_account_id`, `utility_id`, `emittente`, `competenza_dal/al`),
* dati economici (`prezzo_snapshot`, `prezzo_bloccato`, `pricing_mode`),
* sorgente (`sorgente_tipo_id`, `sorgente_uid`, `segment_key`),
* `meta` tecnico per il push (include `periodicita`, `generazione_canone`, `tipo_erogazione`).

---

### Differenze rispetto a preventivi/ordini

| Aspetto | Preventivi/Ordini | Contratti |
|---------|------------------|-----------|
| **segment_key** | `PREV/ORD:<uid>:R:<id>` | `CONTR:<uid>:R:<id>:M:<YYYY-MM>` |
| **Ricorrenza** | Una tantum | Potenzialmente ricorrente |
| **quantita** | Dalla riga sorgente | `quantita_fissa` (puo` essere NULL) |
| **prezzo** | Dalla riga sorgente | `prezzo_unitario` (puo` essere NULL) |
| **valuta_id** | Dalla testata | NULL (handler deve risolvere) |
| **uom_id** | NULL (handler risolve) | NULL (handler risolve) |

---

### Esempi d'uso

**Batch globale (orchestrator):**

```sql
SELECT *
FROM vendite.fn_list_contratti_da_pushare(
  p_competenza_mese => DATE '2026-03-01',
  p_billing_account_id => NULL,
  p_limit => 500
);
```

**Push singolo contratto:**

```sql
SELECT *
FROM vendite.fn_list_contratti_da_pushare(
  p_contratto_id => 12345
);
```

---

---

### `fatturazione_immediata`: dalla costante alla colonna (rev 2026-07-27)

Fino al 2026-07-27 questa funzione proiettava la **costante `FALSE`** nello slot
`fatturazione_immediata`: il contratto della `RETURNS TABLE` era simmetrico a
quello dei preventivi, ma il **dato** no. Conseguenza pratica: un contratto non
poteva mai finire sulla corsia immediata.

Dal changeset `20260727-05` il valore è letto dalla **colonna reale**
`vendite.contratti.fatturazione_immediata` (aggiunta da `20260727-02`). Il valore proiettato qui viaggia fino a
`fn_get_or_create_commessa`, dove è **parte della chiave di dedup**: è così che
il flag separa fisicamente le due corsie (commesse distinte → lotti distinti →
`GIORNALIERO` che numera da solo *vs* `MASSIVO` che si ferma a `EMESSA`).

⚠️ **`prezzo_bloccato` NON è stato toccato** e non va toccato: qui vale
`(cr.prezzo_unitario IS NOT NULL)`, indipendente dal flag. L'accoppiamento
`prezzo_bloccato = COALESCE(fatturazione_immediata, false)` esiste **solo** in
`fn_list_preventivi_da_pushare`. Copiare qui quella riga cambierebbe in silenzio
il comportamento di pricing.

Presidio a valle: dopo il push il flag non è più modificabile sul documento
([`trgfn_guard_fatturazione_immediata_immutabile`](/dbzero/vendite/funzioni/trgfn_guard_fatturazione_immediata_immutabile)).

Brief: `brief-db-emissione-fattura-per-documento-sorgente` PARTE B (step B3).

### Le esclusioni non si fatturano, e l'erogazione non si indovina (rev 2026-10-04)

Dal changeSet `20261004-33`:

* le righe `ESCLUSIONE` **non si listano**. Un'esclusione dice che il contratto
  non vende quell'articolo: non è una riga da fatturare. Prima arrivava in
  commessa senza prezzo, e per quell'articolo il calcolo del prezzo risponde
  `E_ARTICOLO_ESCLUSO_DA_CONTRATTO`;
* l'erogazione della riga, **senza ripiego** su `CANONE`, andava nella colonna
  `tipo_consumo`; dal `20261013-19` quella colonna non c'è più (la madre la
  rifiutava, e nessun contratto arrivava in commessa) e l'erogazione viaggia
  in `meta.tipo_erogazione`.

Dal changeSet `20261013-24` (D-1 e D-2 di Tid, 2026-10-13):

* si listano **solo le righe `UNA_TANTUM`**. `CANONE`, `ORARIO` e `CONSUMO` partivano una volta sola,
  con la quantità fissa del contratto e la competenza di tutto il contratto: un canone diventava un
  addebito unico. Aspettano la loro generazione:
  [brief-db-contratto-righe-periodiche-in-commessa](../../../dev/work-in-progress/brief-db-contratto-righe-periodiche-in-commessa.md);
* la competenza della riga è il **giorno di attivazione** (`valido_dal`) in tutte e due le colonne,
  come per ordini e DDT. Prima era `valido_dal`…`valido_al`, e con un contratto senza scadenza
  `competenza_al` usciva NULL e la madre la rifiutava.
  L'erogazione è obbligatoria su ogni riga che non è un'esclusione (vedi
  [`trgfn_righe_guard_erogazione_obbligatoria`](/dbzero/script/funzioni/trgfn_righe_guard_erogazione_obbligatoria)),
  quindi su ogni riga che questa funzione restituisce.

Brief: `brief-db-erogazione-obbligatoria-righe-fatturate` (R4).

{% include-markdown "signature-core.md" %}
