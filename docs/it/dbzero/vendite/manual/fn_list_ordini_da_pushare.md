## 📘 Documentazione Concettuale – Funzione `vendite.fn_list_ordini_da_pushare`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> * [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
>
> Approfondimento funzioni:
>
> * [vendite.fn_list_ddt_da_pushare](/dbzero/vendite/funzioni/fn_list_ddt_da_pushare) — funzione complementare per DDT
> * [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa)
> * [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)

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

* **stato documento libero sull'asse spedizione**: esclusi solo
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
* costruisce `segment_key` deterministica con `script.fn_segment_key` (`ORDINE_VENDITA:{uid}:R:{riga_id}`);
* forza `prezzo_bloccato = TRUE` (ordine confermato);
* supporta filtri opzionali:
  * `p_competenza_mese`
  * `p_billing_account_id`
  * `p_limit`
  * `p_ordine_id` — vedi sezione dedicata

---

### Push singolo ordine (estensione coordinata)

Il parametro `p_ordine_id` (tipo `vendite.ordini.id%TYPE`, default `NULL`) consente
di restringere il risultato a un singolo ordine.

| Valore  | Comportamento                                                |
|---------|--------------------------------------------------------------|
| `NULL`  | Lista globale — comportamento batch invariato                |
| `> 0`   | Filtra all'ordine specificato; tutti gli altri filtri in AND |
| `<= 0`  | Guard: solleva `E_PUSH_SORGENTE_ID_INVALIDO`                 |

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

### La riga-onere va in commessa come ONERE

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
* provenienza (`sorgente_tipo_id`, `sorgente_chiave`, `segment_key`): `sorgente_chiave` è l'uid
  dell'ordine in testo, e la madre `fn_upsert_commessa_attivita` la traduce con
  `script.fn_sorgente_chiave` nella colonna del `key_selector` del tipo (`sorgente_id`, perché
  l'ordine si riconosce dall'id); `riga_id` arriva in commessa come la riga della provenienza (`sorgente_riga`),
* `meta` tecnico per il push.

---

### `fatturazione_immediata`: dalla costante alla colonna

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

---

### Note di migrazione

* 2026-05-10 — arriva `p_ordine_id`, in coordinamento con le altre `fn_list_*_da_pushare`.
* 2026-10-20 — la `segment_key` la compone `script.fn_segment_key` col codice del tipo, al posto
  del prefisso `ORD:` (brief-db-grammatica-unica-documenti).
* 2026-11-07 — `riga_id` arriva in commessa come `sorgente_riga` (brief-db-sorgente-documento-e-riga).
* 2026-11-08 — la colonna d'uscita `sorgente_uid` diventa `sorgente_chiave`, la chiave del
  documento in testo che la madre traduce (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
