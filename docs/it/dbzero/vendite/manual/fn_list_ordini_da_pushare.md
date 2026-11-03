## Documentazione Concettuale – Funzione `vendite.fn_list_ordini_da_pushare(...)`

> **Ultimo aggiornamento**: 3 novembre 2026

> **Vedi anche**
>
[vendite.ordini](/dbzero/vendite/tabelle/ordini)
> [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
> [vendite.fn_list_ddt_da_pushare](/dbzero/vendite/funzioni/fn_list_ddt_da_pushare) — funzione complementare per DDT
> [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa)
> [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)

---
### 🎯 Scopo Principale
`vendite.fn_list_ordini_da_pushare(...)` seleziona le righe ordine
pronte per il push verso `commesse_attivita`, restituendo un payload completo
per l’handler di acquisizione.

**Solo ordini con `fatturazione_trigger = ‘CONFERMATO’`** sono gestiti
da questa funzione. Ordini con trigger `SPEDITO` o `CONSEGNATO` sono
delegati a `fn_list_ddt_da_pushare`.

---

### Regole principali

* **stato documento libero sull'asse spedizione** *(rev 2026-07-10)*: esclusi solo
  `DRAFT`, `ANNULLATO` (documento commercialmente inesistente) e `FATTURATO`
  (cintura). Un ordine `PARZIALMENTE_EVASO`/`EVASO` resta eleggibile: per il
  trigger CONFERMATO la fatturazione è ortogonale alla spedizione (fix «orfano
  da push», piano `piano-db-fix-orfano-push-ordine-confermato.md`);
* **`fatturazione_trigger = ‘CONFERMATO’`** (esclusione reciproca con DDT);
* nessun filtro sul billing account: `vendite.ordini.billing_account_id` è
  `NOT NULL` (il filtro `IS NOT NULL` è stato ritirato il 2026-10-10, D-1 di
  `brief-db-istanza-nasce-col-ba-residui`). ⚠️ Se il BA dell'ordine tornasse
  nullable, il filtro tornerebbe necessario;
* include solo righe attive con quantita` e prezzo validi;
* esclude segmenti gia` emessi in `commesse_attivita` (idempotenza batch);
* costruisce `segment_key` deterministica (`ORD:{uid}:R:{riga_id}`);
* forza `prezzo_bloccato = TRUE` (ordine confermato);
* supporta filtri opzionali:
  * `p_competenza_mese`
  * `p_billing_account_id`
  * `p_limit`
  * `p_ordine_id` *(2026-05)* — vedi sezione dedicata

---

### Push singolo ordine (estensione coordinata)

> **Aggiunto:** 2026-05 — migration `20260510-02`

Il parametro `p_ordine_id` (tipo `vendite.ordini.id%TYPE`, default `NULL`) consente
di restringere il risultato a un singolo ordine.

| Valore  | Comportamento                                                |
|---------|--------------------------------------------------------------|
| `NULL`  | Lista globale — comportamento batch invariato                |
| `> 0`   | Filtra all'ordine specificato; tutti gli altri filtri in AND |
| `<= 0`  | Guard: solleva `E_PUSH_SORGENTE_ID_INVALIDO` (id 433)        |

Estensione coordinata con le altre 4 `fn_list_*_da_pushare` per uniformare
la signature al client Python `CommesseRepository.fetch_pushable_rows` (4 args posizionali).

---

### Esclusione reciproca con DDT

| `fatturazione_trigger` | Chi pusha | Funzione |
|------------------------|-----------|----------|
| `CONFERMATO` | Ordine alla conferma | `fn_list_ordini_da_pushare` |
| `SPEDITO` | DDT alla spedizione | `fn_list_ddt_da_pushare` |
| `CONSEGNATO` | DDT alla consegna | `fn_list_ddt_da_pushare` |

Il valore di `fatturazione_trigger` e` ereditato da
`billing_account.fatturazione_ordini` al momento dell’inserimento ordine
(via `trgfn_ordini_normalize`).

---

### La riga-onere va in commessa come ONERE (rev 2026-11-03)

Dal `20261103-38` (brief-db-addebito-trasporto-ordine §8.1, K-1) la riga-onere dell'ordine
(`script.fn_natura_e_merce` falso sulla natura congelata) esce con `tipo_movimento = 'ONERE'` e con la
causale dell'articolo nella colonna **nuova** `causale_onere_id`, in coda (NULL sulla merce). La
sorgente è l'ordine, come per le altre righe. Il RETURNS TABLE è cambiato (DROP + CREATE).

⚠️ La madre `vendite.fn_upsert_commessa_attivita` vuole `ONERE` ⇔ causale: il backend deve passare
`causale_onere_id` (`p_causale_onere_id`), o la riga ONERE si rifiuta (`E_PARAMETRO_INVALIDO`).

---

### 📦 Output (alto livello)

Restituisce per ogni riga candidata:
* contesto documento (`ordine_id`, `ordine_uid`, `riga_id`),
* dati commessa/competenza,
* dati economici (`prezzo_snapshot`, `prezzo_bloccato`, `pricing_mode`),
* sorgente (`sorgente_tipo_id`, `sorgente_uid`, `segment_key`),
* `meta` tecnico per il push.

---

### Esempi d’uso

**Batch globale (orchestrator):**

```sql
SELECT *
FROM vendite.fn_list_ordini_da_pushare(
  p_competenza_mese => DATE ‘2026-02-01’,
  p_billing_account_id => NULL,
  p_limit => 500
);
```

**Push singolo ordine:**

```sql
SELECT *
FROM vendite.fn_list_ordini_da_pushare(
  p_ordine_id => 12345
);
```

---

---

### `fatturazione_immediata`: dalla costante alla colonna (rev 2026-07-27)

Fino al 2026-07-27 questa funzione proiettava la **costante `FALSE`** nello slot
`fatturazione_immediata`: il contratto della `RETURNS TABLE` era simmetrico a
quello dei preventivi, ma il **dato** no. Conseguenza pratica: un ordine non
poteva mai finire sulla corsia immediata.

Dal changeset `20260727-04` il valore è letto dalla **colonna reale**
`vendite.ordini.fatturazione_immediata` (aggiunta da `20260727-01`). Il valore proiettato qui viaggia fino a
`fn_get_or_create_commessa`, dove è **parte della chiave di dedup**: è così che
il flag separa fisicamente le due corsie (commesse distinte → lotti distinti →
`GIORNALIERO` che numera da solo *vs* `MASSIVO` che si ferma a `EMESSA`).

⚠️ **`prezzo_bloccato` NON è stato toccato** e non va toccato: qui vale
la costante `TRUE`, indipendente dal flag. L'accoppiamento
`prezzo_bloccato = COALESCE(fatturazione_immediata, false)` esiste **solo** in
`fn_list_preventivi_da_pushare`. Copiare qui quella riga cambierebbe in silenzio
il comportamento di pricing.

Presidio a valle: dopo il push il flag non è più modificabile sul documento
([`trgfn_guard_fatturazione_immediata_immutabile`](/dbzero/vendite/funzioni/trgfn_guard_fatturazione_immediata_immutabile)).

Brief: `brief-db-emissione-fattura-per-documento-sorgente` PARTE B (step B3).

{% include-markdown "signature-core.md" %}
