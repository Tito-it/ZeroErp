## 📘 Documentazione Concettuale – Funzione `vendite.fn_resi_da_accreditare(p_ddt_ids, p_ordine_ids)`

> 👀 **Vedi anche**
>
> [vendite.vw_resi_da_accreditare](/dbzero/vendite/views/vw_resi_da_accreditare) — la stessa cosa, senza filtro
> [vendite.fn_partite_merce](/dbzero/vendite/funzioni/fn_partite_merce) — la partita da cui parte
> [vendite.fn_accredita_riga_reso](/dbzero/vendite/funzioni/fn_accredita_riga_reso) · [vendite.fn_resi_riga_tetti_accredito](/dbzero/vendite/funzioni/fn_resi_riga_tetti_accredito) — i due verbi che la leggono per riga
> Brief: `docs/it/dev/work-done/brief-db-partita-merce-per-documento.md` (giro 2, D3)

---
### 🎯 Scopo Principale
(latest review 2026-09-21)

`vendite.fn_resi_da_accreditare` è **la coda accrediti** — le righe di reso per
cui il conto della merce dichiara un accredito ancora dovuto, lo stesso insieme
di [`vw_resi_da_accreditare`](vw_resi_da_accreditare.md), che ne è la
proiezione senza filtro — calcolata **per i documenti che si chiedono**.

Chi la leggeva per **una** riga sola pagava la coda di **tutti**: il verbo
«accredita» ([`fn_accredita_riga_reso`](fn_accredita_riga_reso.md)) e il guard
del ponte ([`fn_resi_riga_tetti_accredito`](fn_resi_riga_tetti_accredito.md),
chiamato a ogni riga scritta su `resi_righe_accrediti`) — e con loro il
backend, quando mostra la coda di un DDT o di un ordine. La vista somma le
partite di tutti, valuta i resi di tutti, e per **ogni** riga di reso confermata
del database chiama `fn_resi_riga_accreditato_partita`.

---

### I semi

Gli stessi due, **nello stesso ordine**, di `fn_partite_merce`:

| Parametro | Cosa semina — l'insieme **S** delle righe di DDT |
|---|---|
| `p_ddt_ids` | le righe di DDT dei DDT chiesti (la colonna `ddt_id`) |
| `p_ordine_ids` | le righe di DDT con un **fulfillment** verso una riga di quegli ordini |

* **Entrambi `NULL` = tutta la coda.** È il modo in cui la vista chiama la
  funzione.
* **Un array vuoto semina zero righe.**
* Con entrambi valorizzati l'uscita è l'**unione**.
* **L'uscita è `ddt_riga_id ∈ S`**, per costruzione.

⭐ **S è lo stesso predicato del building block del backend**
`_coda_documento_filtro.filtro_coda_per_documento`, riga per riga: la coda ha
`ddt_id` ma **non ha** `ordine_id`, e il legame all'ordine passa dal
fulfillment — la stessa fonte da cui la partita deriva la propria origine.

⛔ **Non è l'uscita per ordine di `fn_partite_merce`.** Là il filtro è sulla
colonna proiettata `ordine_id` = la riga d'ordine **minima**, quindi una riga di
DDT che evade due ordini esce sotto uno solo. Qui la stessa riga sta nella coda
di **entrambi**, come il backend la filtra oggi. Le due semantiche «per ordine»
sono diverse perché le due letture lo sono; il presidio costruisce la riga
`MULTIPLA` per distinguerle.

---

### Perché il numero è giusto anche leggendo poco

| Pezzo | Con un seme legge |
|---|---|
| le partite in negativo (`acc`) | `fn_partite_merce(<i DDT di S>, NULL)`: tutte le partite di quei DDT, un soprainsieme di S che il `JOIN` riporta a S |
| le righe di reso effettive (`eff`) | quelle con `ddt_riga_id ∈ S` — cioè **tutte le sorelle** della stessa riga di DDT |
| `fn_resi_riga_accreditato_partita` | solo su quelle |
| la greedy per `resi_riga_id` (`dist`) | la finestra `PARTITION BY ddt_riga_id ORDER BY resi_riga_id` è **intera**, perché le sorelle ci sono tutte |

Le sorelle sono il pezzo che conta: la capienza della partita si ripartisce fra
le righe di reso in ordine di id, e una riga chiesta **senza** le sorelle che la
precedono si prenderebbe una quota già presa. Il presidio lo costruisce: partita
da 10 fatturata 6, due resi a credito (4, poi 3) — la prima prende i 3 di
capienza, la seconda resta fuori; e il guard del ponte, attraverso la funzione,
dice 3 alla prima e 0 alla seconda.

---

### ⚠️ Due scelte di forma che non sono stile

**Il corpo è `BEGIN ATOMIC`**, come `fn_partite_merce`: dipendenze in
`pg_depend`, catena RLS leggibile dal presidio `security_invoker` attraverso le
due funzioni. Una colonna nuova nel `RETURNS TABLE` è un `DROP FUNCTION` a
cascata sulla vista **e** su `vw_dash_backlog_documenti`, che la legge.

**I due modi sono rami in `UNION ALL`**, mai `p IS NULL OR …`. Sulla partita il
ramo «tutte» chiama `fn_partite_merce(NULL, NULL)` con due letterali (inlinata:
le stesse tabelle e lo stesso numero di accessi della vista di prima); il ramo
ristretto passa il seme **calcolato** (`array_agg` dei DDT di S), che il planner
non inlina — un `Function Scan` che regge in piano generico.
`COALESCE(array_agg(…), '{}')`: un seme che non trova righe non deve diventare
«tutte».

**Dentro `fn_resi_riga_tetti_accredito`**, che è `SECURITY DEFINER`, la funzione
— `INVOKER` — gira come l'owner: **sopra la RLS**, esattamente com'era la vista
letta da lì. Il tetto non cambia natura.

---

### Chi la chiama

| Lettore | Come |
|---|---|
| `vw_resi_da_accreditare` | `fn_resi_da_accreditare(NULL, NULL)` — tutta la coda |
| `fn_accredita_riga_reso(p_resi_riga_id)` | `ARRAY[ddt della riga resa]` nel primo seme, poi `WHERE resi_riga_id = p` |
| `fn_resi_riga_tetti_accredito(p_resi_riga_id, …)` | idem, con `COALESCE(…, '{}')` se la riga non c'è (zero righe, non «tutta») |
| BE `list_situazione_merce_accrediti` e `ResiRepository.list_da_accreditare` con `ddt_id`/`ordine_id` | ⏳ richiesta BE nel brief: `(ARRAY[%s], NULL)` / `(NULL, ARRAY[%s])` **senza** il predicato del BB, che la funzione incorpora; oggi leggono la vista, che risponde giusto ma paga tutto |
| la lista configurabile `vendite.resi_da_accreditare`, `vw_dash_backlog_documenti` | la vista: leggono **tutta** la coda, ed è giusto così |

---

### Esempio d'uso

```sql
-- La coda accrediti di una spedizione.
SELECT resi_riga_id, reso_numero, accredito_dovuto, etichetta, blocco_codice
  FROM vendite.fn_resi_da_accreditare(ARRAY[15854], NULL);

-- Quella di un ordine (una riga di DDT che evade due ordini esce per entrambi).
SELECT resi_riga_id, ddt_numero, accredito_dovuto
  FROM vendite.fn_resi_da_accreditare(NULL, ARRAY[18586]);
```

---

### Presidio

`db/pgtap/vendite/test-fn-resi-da-accreditare-chiusura-v1.sql` (12 test). I
casi che contano sono costruiti, non letti dai dati:

* **le sorelle**: due resi a credito sulla stessa partita con capienza
  parziale — una riga in coda (3), l'altra fuori; e il guard del ponte,
  attraverso la funzione, dice 3 e 0;
* la riga **`MULTIPLA`**: nella coda dell'ordine B (predicato del backend)
  anche se la partita per B non esce da `fn_partite_merce`;
* **il verbo** attraverso la funzione: accredita per 3, e — emessa la rettifica
  — la coda del DDT è vuota;
* `FACOLTATIVA` su un reso per ri-consegna con residuo aperto; zero righe su una
  partita non fatturata;
* più i pin di forma (la vista nomina la funzione e nessuna tabella; 27 colonne
  coi cinque `varchar` che tengono il typmod; `security_invoker`), il vuoto che
  non è «tutta», lo scope.

---

{% include-markdown "signature-core.md" %}
