## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_clienti_guard_stato_date`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — la tabella su cui scatta
> * [config.stati_cliente](/dbzero/config/tabelle/stati_cliente) — gli stati del cliente
> * [config.transizioni_stati_cliente](/dbzero/config/tabelle/transizioni_stati_cliente) — il percorso ammesso fra gli stati
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_clienti_set_periodo](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_periodo) — il periodo calcolato dalle stesse date
> * [script.fn_disdetta_cliente](/dbzero/script/funzioni/fn_disdetta_cliente) — la chiusura del cliente
>
> Guide:
>
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility) — gli stati del cliente e le loro date

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_clienti_guard_stato_date` tiene in regola lo stato del cliente e le date che lo
accompagnano, a ogni nascita e a ogni modifica: il percorso degli stati, la data di chiusura che non cambia,
la data che ogni stato pretende.

---

### Le regole

| Regola | Codice |
| --- | --- |
| lo stato cambia solo lungo il percorso di `config.transizioni_stati_cliente` (le transizioni attive) | `E_CLIENTE_STATO_TRANSIZIONE_INVALIDA` |
| un cliente chiuso, in qualunque forma, non cambia più la data di chiusura, nemmeno quando diventa «chiuso e fatturato» | `E_CLIENTE_DATA_CHIUSURA_IMMUTABILE` |
| ogni stato pretende la sua data | `E_CLIENTE_STATO_SENZA_DATA` |
| la chiusura non precede l'attivazione (l'annullato escluso: il periodo gli toglie le date) | `E_DATA_CHIUSURA` |

Le date che ogni stato pretende:

| Stato | Date |
| --- | --- |
| attivo, richiesta di sospensione | attivazione |
| sospeso (fatturabile o no) | attivazione, sospensione |
| chiuso (`CH`, `CM`, `CW`, `CF`) | attivazione, chiusura |
| attivo dopo una sospensione | anche la riattivazione |
| pre-contrattuale, annullato, aggregante | nessuna |

Il percorso vale per i **cambi** di stato. Un cliente nasce in qualunque stato, purché abbia le date che lo
stato pretende. Quando mancano più date, il rifiuto nomina la prima nell'ordine in cui la vita del cliente le
scrive.

Il messaggio riconosce il cliente dal codice del suo billing account, quello che l'operatore conosce.

---

### ⭐ Un cliente chiuso non si riapre

Dal chiuso si va solo a «chiuso e fatturato», che è finale come l'annullato. Chi torna dopo una chiusura apre
una fornitura nuova (istanza, billing account e cliente), collegata alla precedente. Il cliente chiuso resta
com'è, perché la sua data di chiusura dice fino a quando ha occupato la fornitura: è la misura del periodo, del
vincolo sul PDP e della chiave del cliente manuale.

---

### Codici errore

* `E_CLIENTE_STATO_TRANSIZIONE_INVALIDA` — un cambio di stato fuori percorso. Campo `stato_cliente_id`.
* `E_CLIENTE_DATA_CHIUSURA_IMMUTABILE` — la data di chiusura di un cliente chiuso cambia. Campo `data_chiusura`.
* `E_CLIENTE_STATO_SENZA_DATA` — manca la data che lo stato pretende. Il campo è la data mancante.
* `E_DATA_CHIUSURA` — la chiusura precede l'attivazione. Campo `data_chiusura`.

---

### Test

* `db/pgtap/anagrafiche/test-cliente-manuale-chiave-unica-v1.sql` — le date pretese da sospeso, riattivato e
  chiuso, il chiuso che non torna attivo, la data di chiusura che non cambia, il passaggio a «chiuso e
  fatturato» e il ritorno indietro rifiutato, la disdetta di un sospeso.

---

### Note di migrazione

* 2026-10-14 — nasce, e raccoglie per tutti gli stati i controlli che stavano nel calcolo del periodo (l'attivo
  senza attivazione, il chiuso con la chiusura prima dell'attivazione). Prima la disdetta accettava solo un
  cliente attivo.

---

{% include-markdown "signature-core.md" %}
