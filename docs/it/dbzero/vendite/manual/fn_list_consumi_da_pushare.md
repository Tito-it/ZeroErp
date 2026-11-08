## 📘 Documentazione Concettuale – Funzione `vendite.fn_list_consumi_da_pushare`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.attivita_consumi](/dbzero/vendite/tabelle/attivita_consumi) — i consumi da mandare in commessa
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il conto di fatturazione
>
> Approfondimento funzioni:
>
> * [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa) — la commessa del push
> * [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita) — la madre che scrive le righe, e traduce la chiave del documento
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

`vendite.fn_list_consumi_da_pushare(...)` seleziona i consumi utility
pronti per il push verso `commesse_attivita`, restituendo un payload di base
per l'handler di calcolo componenti.

A differenza delle sorgenti commerciali (preventivi, ordini) dove il mapping
e 1 riga → 1 `commesse_attivita`, un consumo genera **N componenti fatturabili**
(consumo per fascia, canoni fissi, oneri, accise, ecc.).
Il fan-out 1→N e responsabilita dell'handler, non di questa funzione.

---

### Regole principali

* considera consumi con `stato_calcolo = 'OK'` (esclusi WARNING/ERRORE);
* esclude consumi gia fatturati sul percorso legacy (`fattura_id IS NULL`);
* esclude consumi con segment_key gia EMESSA in `commesse_attivita` (idempotenza batch);
* costruisce `segment_key` base con `script.fn_segment_key` (`ATTIVITA_CONSUMI:{uid}`); l'handler
  espande in `ATTIVITA_CONSUMI:{uid}:COMP:{componente}` per ogni componente;
* restituisce `articolo_id = NULL` e `valuta_id = NULL`:
  l'handler deve risolverli da configurazione;
* `prezzo_bloccato = FALSE`: i consumi sono sempre ricalcolabili da listino;
* sorgente tipo: `ATTIVITA_CONSUMI`, letto da `config.sorgenti` per `codice_interno` (solo
  se attivo; altrimenti `E_CODICE`);
* supporta filtri opzionali:
  * `p_competenza_mese`
  * `p_billing_account_id`
  * `p_limit`
  * `p_consumo_id` — vedi sezione dedicata

---

### Push singolo consumo (estensione coordinata)

Il parametro `p_consumo_id` (tipo `vendite.attivita_consumi.id%TYPE`, default `NULL`) consente
di restringere il risultato a un singolo consumo.

| Valore  | Comportamento                                                |
|---------|--------------------------------------------------------------|
| `NULL`  | Lista globale — comportamento batch invariato                |
| `> 0`   | Filtra al consumo specificato; tutti gli altri filtri in AND |
| `<= 0`  | Guard: solleva `E_PUSH_SORGENTE_ID_INVALIDO`                 |

Estensione coordinata con le altre 4 `fn_list_*_da_pushare` per uniformare
la signature al client Python `CommesseRepository.fetch_pushable_rows` (4 args posizionali).

---

### 📦 Output (alto livello)

Restituisce per ogni consumo candidato:
* contesto consumo (`consumo_id`, `consumo_uid`),
* dati commessa/competenza (`billing_account_id`, `utility_id`, `emittente`, `competenza_dal/al`),
* dati economici (`prezzo_snapshot = NULL`, `prezzo_bloccato = FALSE`, `pricing_mode = FIXED`),
* provenienza (`sorgente_tipo_id`, `sorgente_chiave`, `segment_key`): `sorgente_chiave` è l'uid
  del consumo in testo, e la madre `fn_upsert_commessa_attivita` la traduce con
  `script.fn_sorgente_chiave` nella colonna del `key_selector` del tipo (`sorgente_id`, perché il
  consumo si riconosce dall'id). Un consumo non ha righe: la provenienza è il documento intero, e
  non c'è `riga_id`,
* quantita grezza (`consumo_totale` come `quantita` e `qta_operativa`),
* `meta` tecnico con periodo, stato_calcolo, tipo_commessa/policy.

---

### Flusso nel contesto pipeline

```text
attivita_consumi (stato_calcolo = OK)
    |
    v
fn_list_consumi_da_pushare (questa funzione — 1 riga per consumo)
    |
    v
Handler utility-specific (gas_v1, energia_v1, idrico_v1):
    fan-out 1 consumo → N componenti fatturabili
    |
    v
fn_get_or_create_commessa (AUTO) + fn_upsert_commessa_attivita x N
    |
    v
fn_emit_attivita_fatturabili_da_commessa → attivita_fatturabili x N
```

---

### Perché qui `fatturazione_immediata` resta la costante `FALSE`

Le altre `fn_list_*_da_pushare` (ordini, contratti, DDT) proiettano su `fatturazione_immediata`
la colonna reale del documento. **Questa no, ed è voluto**: un consumo è una **misura** — una lettura di
contatore — non un accordo commerciale. La scelta «questo cliente si fattura
subito» appartiene al **contratto** che governa la fornitura, non alla singola
lettura. Un flag anche qui significherebbe lo stesso interruttore in **due
posti**, con la possibilità concreta che dicano cose opposte (contratto
differito + consumo immediato) e nessuna regola che stabilisca chi vince.

I consumi seguono quindi **sempre la corsia differita**; la corsia immediata si
ottiene, dove serve, marcando il contratto.

`vendite.attivita_consumi` **non ha** la colonna, e non ha il guard di
immutabilità. Un pgTAP (`test-fatturazione-immediata-simmetria-sorgenti-v1.sql`,
caso 11) verifica che continui a non averla: se qualcuno la aggiungesse «per
simmetria», il test obbliga a ridiscutere la decisione invece di subirla.

> Reversibile a costo basso: se un domani servisse davvero, la colonna si
> aggiunge come sugli altri documenti e questa funzione la legge come le altre.

⚠️ **Nota**: la funzione proietta **due** costanti `FALSE`. La seconda è
`prezzo_bloccato`, e vale per suo conto: un consumo non porta prezzo dalla
sorgente (`prezzo_snapshot` è `NULL`), quindi non c'è nulla da bloccare — il
prezzo lo risolve il pricing a valle. Le due costanti non sono correlate.

---

### Note di migrazione

* 2026-05-10 — arriva `p_consumo_id`, in coordinamento con le altre `fn_list_*_da_pushare`.
* 2026-07-27 — le altre `fn_list_*_da_pushare` proiettano la colonna reale di
  `fatturazione_immediata`; i consumi restano sulla costante `FALSE` (decisione D-6,
  brief-db-emissione-fattura-per-documento-sorgente).
* 2026-10-20 — la `segment_key` la compone `script.fn_segment_key` col codice del tipo, al posto
  del prefisso `CONS:` (brief-db-grammatica-unica-documenti).
* 2026-11-08 — la colonna d'uscita `sorgente_uid` diventa `sorgente_chiave`, la chiave del
  documento in testo che la madre traduce (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
