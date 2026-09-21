## Documentazione Concettuale – Funzione `vendite.fn_list_ddt_da_pushare(...)`

> **Vedi anche**
>
[vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)
> [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)
> [vendite.fn_list_ordini_da_pushare](/dbzero/vendite/funzioni/fn_list_ordini_da_pushare)
> [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa)
> [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)
> [vendite.fn_partite_merce](/dbzero/vendite/funzioni/fn_partite_merce) — la partita, per documento (rev 2026-09-21)

---
### 🎯 Scopo Principale
`vendite.fn_list_ddt_da_pushare(...)` seleziona le righe DDT pronte per
il push verso `commesse_attivita`, restituendo un payload completo per
l'handler di acquisizione.

Supporta **due modalita`**:
- **DDT da ordine**: fatturazione delegata dall'ordine via `fatturazione_trigger`
- **DDT autonomo**: DDT con billing_account proprio, senza ordine sorgente

---

### Regole principali

**Caso A — DDT da ordine (fulfillment esiste):**

* l'ordine sorgente ha `fatturazione_trigger IN ('SPEDITO','CONSEGNATO')`;
* lo stato DDT deve corrispondere al trigger dell'ordine;
* prezzo: `COALESCE(ddt_righe.prezzo_unitario, ordini_righe.prezzo_unitario)`;
* billing_account: `COALESCE(ddt.billing_account_id, ordini.billing_account_id)`.

**Caso B — DDT autonomo (nessun fulfillment):**

* `ddt.billing_account_id IS NOT NULL` (obbligatorio);
* stato DDT IN (`SPEDITO`, `CONSEGNATO`);
* prezzo da `ddt_righe.prezzo_unitario` (puo` essere NULL; handler risolve).

**Regole comuni:**

* riga attiva (`attivo = TRUE`);
* esclude segmenti gia` emessi in `commesse_attivita` (idempotenza batch);
* costruisce `segment_key` deterministica (`DDT:{uid}:R:{riga_id}`);
* `prezzo_bloccato = TRUE` se prezzo_snapshot presente;
* sorgente tipo: `DDT_VENDITA` da `config.sorgenti` (id=8);
* supporta filtri opzionali:
  * `p_competenza_mese`
  * `p_billing_account_id`
  * `p_limit`
  * `p_ddt_id` *(2026-05)* — vedi sezione dedicata

---

### Push singolo DDT (estensione coordinata)

> **Aggiunto:** 2026-05 — migration `20260510-04`

Il parametro `p_ddt_id` (tipo `vendite.ddt.id%TYPE`, default `NULL`) consente
di restringere il risultato a un singolo DDT.

| Valore  | Comportamento                                            |
|---------|----------------------------------------------------------|
| `NULL`  | Lista globale — comportamento batch invariato            |
| `> 0`   | Filtra al DDT specificato; tutti gli altri filtri in AND |
| `<= 0`  | Guard: solleva `E_PUSH_SORGENTE_ID_INVALIDO` (id 433)    |

Estensione coordinata con le altre 4 `fn_list_*_da_pushare` per uniformare
la signature al client Python `CommesseRepository.fetch_pushable_rows` (4 args posizionali).

---

### Relazione con fn_list_ordini_da_pushare

Le due funzioni sono **mutuamente esclusive** per design:

| fatturazione_trigger | Chi pusha | Funzione |
|---------------------|-----------|----------|
| `CONFERMATO` | Ordine | `fn_list_ordini_da_pushare` |
| `SPEDITO` | DDT alla spedizione | `fn_list_ddt_da_pushare` |
| `CONSEGNATO` | DDT alla consegna | `fn_list_ddt_da_pushare` |

Il campo `fatturazione_trigger` su `vendite.ordini` (default da
`anagrafiche.billing_account.fatturazione_ordini`) determina quale
funzione gestisce il push a commessa.

---

### Output (alto livello)

Restituisce per ogni riga candidata:
* contesto documento (`ddt_id`, `ddt_uid`, `riga_id`),
* dati commessa/competenza (risolti da DDT o ordine sorgente),
* dati economici (`prezzo_snapshot`, `prezzo_bloccato`, `pricing_mode`),
* sorgente (`sorgente_tipo_id`, `sorgente_uid`, `segment_key`),
* `meta` tecnico con riferimento ordine sorgente (se presente).

---

### Esempi d'uso

**Batch globale (orchestrator):**

```sql
SELECT *
FROM vendite.fn_list_ddt_da_pushare(
  p_competenza_mese => DATE '2026-03-01',
  p_billing_account_id => NULL,
  p_limit => 500
);
```

**Push singolo DDT:**

```sql
SELECT *
FROM vendite.fn_list_ddt_da_pushare(
  p_ddt_id => 12345
);
```

---

---

### `fatturazione_immediata`: dalla costante alla colonna (rev 2026-07-27)

Fino al 2026-07-27 questa funzione proiettava la **costante `FALSE`** nello slot
`fatturazione_immediata`: il contratto della `RETURNS TABLE` era simmetrico a
quello dei preventivi, ma il **dato** no. Conseguenza pratica: un DDT non
poteva mai finire sulla corsia immediata.

Dal changeset `20260727-06` il valore è letto dalla **colonna reale**
`vendite.ddt.fatturazione_immediata` (aggiunta da `20260727-03`). Il valore proiettato qui viaggia fino a
`fn_get_or_create_commessa`, dove è **parte della chiave di dedup**: è così che
il flag separa fisicamente le due corsie (commesse distinte → lotti distinti →
`GIORNALIERO` che numera da solo *vs* `MASSIVO` che si ferma a `EMESSA`).

⚠️ **`prezzo_bloccato` NON è stato toccato** e non va toccato: qui vale
`(COALESCE(dr.prezzo, src.prezzo) IS NOT NULL)`, indipendente dal flag. L'accoppiamento
`prezzo_bloccato = COALESCE(fatturazione_immediata, false)` esiste **solo** in
`fn_list_preventivi_da_pushare`. Copiare qui quella riga cambierebbe in silenzio
il comportamento di pricing.

Presidio a valle: dopo il push il flag non è più modificabile sul documento
([`trgfn_guard_fatturazione_immediata_immutabile`](/dbzero/vendite/funzioni/trgfn_guard_fatturazione_immediata_immutabile)).

Brief: `brief-db-emissione-fattura-per-documento-sorgente` PARTE B (step B3).

---

### 🔄 rev 2026-09-21 — la partita si legge per documento (D14, quarta leva)

ChangeSet `20260921-23`. Il lister leggeva `vw_partite_merce` in `JOIN`, e la
vista calcola le partite di **tutti** i DDT anche quando `p_ddt_id` ne chiede
uno — cioè a ogni apertura del drawer, dalla capability. Ora legge
[`fn_partite_merce`](/dbzero/vendite/funzioni/fn_partite_merce) con il DDT
chiesto come seme (`ARRAY[p_ddt_id]`): la **chiusura** del documento. Con
`p_ddt_id NULL` (la lista del push, il cockpit) il seme è `NULL` = tutte,
com'era. Stessi predicati, stesso contratto verso la pipeline, stessi numeri: la
vista è la proiezione della stessa funzione.

⚠️ Il seme è un `CASE` senza colonne: in piano custom si piega a un letterale,
in piano generico (dalla sesta esecuzione plpgsql) la funzione lo riceve come
parametro e i suoi rami in `UNION ALL` lo trattano da *One-Time Filter* — mai
una scansione intera (brief `brief-db-partita-merce-per-documento` §2-bis.2).
{% include-markdown "signature-core.md" %}
