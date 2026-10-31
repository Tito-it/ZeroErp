## Documentazione Concettuale – Funzione `vendite.fn_contratti_addebiti_maturati(...)`

> **Ultimo aggiornamento**: 31 ottobre 2026

> **Vedi anche**
>
[vendite.fn_list_contratti_da_pushare](/dbzero/vendite/manual/fn_list_contratti_da_pushare) — il push: tiene le righe senza scarto
> [vendite.vw_dash_fatturazione_contratti](/dbzero/vendite/manual/vw_dash_fatturazione_contratti) — la dashboard: le conta tutte e due
> [vendite.fn_canone_periodi](/dbzero/vendite/funzioni/fn_canone_periodi) — i periodi del canone
> [Guida dei contratti §4-bis](/guide/gestione-contratti#4-bis-come-il-contratto-si-addebita-una-tantum-e-canoni) — la stessa regola, per chi non sviluppa

---
### 🎯 Scopo Principale

Gli **addebiti maturati** dei contratti ATTIVO e CESSATO a questo giro e non ancora in commessa,
**con gli scartati** e il motivo (`scarto`). È la **sede unica** della regola del push dei
contratti (dal 2026-10-31, `20261031-02`), letta da due posti:

* il push ([`fn_list_contratti_da_pushare`](/dbzero/vendite/manual/fn_list_contratti_da_pushare)),
  che tiene le righe con `scarto` NULL;
* la dashboard ([`vw_dash_fatturazione_contratti`](/dbzero/vendite/manual/vw_dash_fatturazione_contratti)),
  che conta le une e le altre: «c'è da mandare» e «c'è qualcosa che non può partire».

Il corpo era quello del lister: è diventato una funzione a sé perché la dashboard non ne
scrivesse una copia.

---

### Parametri

| Parametro | Default | Effetto |
| --- | --- | --- |
| `p_competenza_mese` | NULL | il giro di quel mese: la data del giro è la sua fine; NULL = oggi aziendale |
| `p_billing_account_id` | NULL | solo i contratti di quel billing account |
| `p_contratto_id` | NULL | un contratto solo; `<= 0` → `E_PUSH_SORGENTE_ID_INVALIDO` |

Gli stati letti sono quelli di emissione e di cessazione del vocabolario
([`script.fn_stato_emissione_id`](/dbzero/script/funzioni/fn_stato_emissione_id),
[`script.fn_stato_cessazione_id`](/dbzero/script/funzioni/fn_stato_cessazione_id); oggi `ATTIVO` e
`CESSATO`). Se il vocabolario non ne marca uno → `E_CONFIG_MANCANTE` (fino al 31-10-2026 `E_CODICE`).

---

### Chi si addebita (le fonti)

| Fonte | Ramo | Note |
| --- | --- | --- |
| riga ADESIONE o AGGIUNTA una tantum | 0 | contratti ATTIVO, una volta, competenza = `valido_dal` |
| riga ADESIONE o AGGIUNTA a canone | 1 | |
| riga OVERRIDE a canone **su una quota fissa** | 1 | prende il posto della quota; altrove l'OVERRIDE è solo il prezzo del cliente e non si addebita |
| quota fissa del listino | 1 | articolo di tipologia `e_quota_fissa`, erogazione di default CANONE, **nessuna** riga del contratto sullo stesso articolo (un'eccezione la sostituisce, l'ESCLUSIONE la toglie). Quantità 1, periodicità della riga di listino |

L'ESCLUSIONE non si addebita mai. ORARIO e CONSUMO non escono: aspettano le loro sorgenti.

---

### I periodi del canone

* I pezzi li calcola [`vendite.fn_canone_periodi`](/dbzero/vendite/funzioni/fn_canone_periodi): mese
  di partenza della testata, periodi dal giorno 1, il periodo incompleto in proporzione (i mesi
  interi a mesi, il mese a metà a giorni), spezzatura al 31/12.
* **Anticipato o normale:** `coalesce(generazione_canone della riga, della testata)`.
  `INIZIO_PERIODO` = il pezzo esce appena comincia; `FINE_PERIODO` = appena finisce, rispetto alla
  data del giro.
* **Il «da»:** il giorno dopo l'ultimo pezzo addebitato **di quella fonte** (righe positive,
  NORMALE, non annullate, senza `#STO`). Gli arretrati si recuperano; un giro rifatto non rimanda
  niente.
* **Quantità:** a quantità fissa `round(quantità × frazione, 6)`; a durata i giorni del pezzo
  (`GIORNO`) o i mesi (`MESE`: frazione × mesi del periodo).
* **Prezzo:** della riga (OVERRIDE, AGGIUNTA: `prezzo_bloccato`), o del listino del contratto
  all'inizio del pezzo con la variazione globale (ADESIONE, quota fissa:
  `vendite.fn_resolve_prezzo_listino_v2_esito`, versione operativa del contratto).
* **Competenza:** `competenza_mese` = mese del giro; `competenza_dal/al` = il pezzo;
  `data_attivita` = il suo inizio.

---

### Gli storni

Un pezzo addebitato che va oltre `valido_al` si storna per la parte non goduta, al prezzo
addebitato, una riga per ogni riga addebitata (anche i componenti di un kit). La fine si può
spostare finché il contratto è ATTIVO, quindi lo storno è la **differenza**:

```text
round(addebitato × rapporto, 6) − addebitato − già stornato
```

Il rapporto è giorni (o frazione) con la fine di oggi su quelli senza fine. Il risultato è negativo
se la fine arretra, positivo se avanza o sparisce (si riaddebita). Ogni rettifica ha la sua
chiave: `<base>#STO` la prima, `#STO:2`, `#STO:3` … le successive, prima dell'eventuale `#CMP`.
Le rettifiche già scritte si riconoscono da `#STO` e da `meta.storno_di_attivita_id`. Quelle
annullate non contano nella somma ma contano nel numero, perché la chiave resta occupata nella
commessa.

---

### Gli scartati (`scarto`)

| `scarto` | Ramo | Quando | Colonne |
| --- | --- | --- | --- |
| `SENZA_PERIODICITA` | 3 | una fonte a canone senza periodicità (riga, o quota fissa del listino) | una riga per fonte, senza pezzo: competenza, chiave e quantità NULL |
| `DURATA_SENZA_CALENDARIO` | 3 | una fonte a durata su un'unità senza `conta_dal_calendario` | come sopra |
| `SENZA_PREZZO` | 0, 1 | il pezzo (o la una tantum) senza prezzo alla data | il pezzo intero, prezzo NULL |

Fra due righe di listino sullo stesso articolo vince quella con la periodicità.

---

### Che cosa non esce

* le righe già inviate: `script.fn_get_stato_push_segment(segment_key) <> 'LIBERA'` (vede anche i
  componenti `#CMP`);
* le quantità a zero.

Gli scartati del ramo 3 escono sempre.

---

### Sicurezza

`SECURITY INVOKER`: la vista della dashboard è `security_invoker` e la legge l'app. EXECUTE a
`zeroerp_app`, tolto a PUBLIC.

Brief: `brief-db-contratto-righe-periodiche-in-commessa` (§6.12, §6.13). Test:
`db/pgtap/vendite/test-push-contratto-canoni-v1.sql`,
`test-vw-dash-contratti-giudizio-v1.sql`.

{% include-markdown "signature-core.md" %}
