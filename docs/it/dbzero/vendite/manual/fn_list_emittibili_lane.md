## Documentazione Concettuale – Funzione `vendite.fn_list_emittibili_lane`

> **Vedi anche**
>
**Tabelle correlate:**
>
[vendite.commesse](/dbzero/vendite/tabelle/commesse),
[vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita),
[vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)
>
**Funzioni correlate:**
>
[vendite.fn_list_commesse_emittibili](/dbzero/vendite/funzioni/fn_list_commesse_emittibili),
[vendite.fn_select_attivita_fatturabili](/dbzero/vendite/funzioni/fn_select_attivita_fatturabili),
[vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa)

---
### 🎯 Scopo Principale
(latest review 19-06-2026 — discovery corsie per il driver batch; grana estesa a `utility_id`)

La funzione **`vendite.fn_list_emittibili_lane`** è la **discovery delle corsie** per il
driver batch di fatturazione. Risponde a:

> «Per questa corsia/perimetro, quali **terne distinte
> `(emittente_soggetto_ruolo_id, tipo_doc_fiscale_id, utility_id)`** hanno lavoro pronto da
> fatturare, e **fino a quale `competenza_mese`** creare il lotto?»

Serve perché un **lotto** è segregato per `(emittente, tipo_doc_fiscale, utility, competenza_mese)`:
oltre a emittente e tipo_doc, `fn_create_fatturazione_lotto` **pretende `utility_id` NOT NULL**
e `fn_select_attivita_fatturabili` **filtra le AF per `ba.utility_id`** (gas/ee/idrico →
documenti distinti). Il driver deve aprire **un lotto per ogni terna** presente, altrimenti
le righe delle altre utility/tipo_doc — pullate ma non catturate — resterebbero orfane
(fatturato perso in silenzio). È **separata** da `fn_list_commesse_emittibili` (che resta
la discovery per-commessa dello step di pull): qui si raggruppa per corsia, non per commessa.

> **Coerenza grana ↔ select (perché la terna è sicura).** La discovery raggruppa per
> `c.utility_id` (`vendite.commesse`), mentre la select a valle filtra per `ba.utility_id`
> (`anagrafiche.billing_account`). I due **coincidono per costruzione**: `fn_get_or_create_commessa`
> impone `commessa.utility_id = billing_account.utility_id` (altrimenti
> `E_CLIENTE_UTILITY_MISMATCH_BA`). Quindi una terna scoperta qui non potrà mai essere
> scartata dalla select per disallineamento di utility — per questo non serve alcun guard
> aggiuntivo su questo asse.

---

### Parametri di input

| Parametro                       | Tipo                                                     | Default | Descrizione                                                        |
| ------------------------------- | -------------------------------------------------------- | ------- | ------------------------------------------------------------------ |
| `p_competenza_mese`             | `vendite.commesse_attivita.competenza_mese%TYPE`         | `NULL`  | **Limite superiore** della competenza (cumulativo, vedi sotto). NULL = nessun limite. |
| `p_billing_account_id`          | `vendite.commesse.billing_account_id%TYPE`               | `NULL`  | Filtro perimetro BA.                                               |
| `p_utility_id`                  | `vendite.commesse.utility_id%TYPE`                        | `NULL`  | Filtro perimetro utility (opzionale).                             |
| `p_emittente_soggetto_ruolo_id` | `vendite.commesse.emittente_soggetto_ruolo_id%TYPE`      | `NULL`  | Filtro perimetro emittente.                                       |
| `p_fatturazione_immediata`      | `vendite.commesse.fatturazione_immediata%TYPE`           | `NULL`  | Corsia: true=immediata / false=differita / NULL=indifferente.     |
| `p_limit`                       | `integer`                                                | `1000`  | Normalizzato (default 1000, max 10000); si applica alle **terne**. |
| `p_gruppi`                      | `text[]`                                                 | `NULL`  | **Emissione mirata**: restringe alle terne dei GRUPPI FATTURABILI richiesti. NULL = nessuna restrizione. ⚠️ `text[]` esplicito — PostgreSQL non supporta `colonna%TYPE[]`. |

---

### Output

`RETURNS TABLE(emittente_soggetto_ruolo_id, tipo_doc_fiscale_id, utility_id, competenza_mese, total_candidate, gruppi_coperti)`:

* **`utility_id`** = utility della terna. **Mai NULL** (`commesse.utility_id` è NOT NULL a
  monte): nessuna terna da escludere su questo asse.
* **`competenza_mese`** = `max(competenza_mese)` fra le righe candidate della terna → la
  competenza con cui il driver crea il lotto.
* **`total_candidate`** = numero di righe candidate (per dry-run/diagnostica).
* **`gruppi_coperti`** `text[]` *(dal 2026-08-15, `20260815-02`)* = **quali gruppi
  fatturabili** questa terna ha effettivamente coperto, in ordine **deterministico**.

#### A cosa serve `gruppi_coperti`, e perché non c'era

Risponde a una domanda che prima non aveva risposta: **l'operatore chiede tre gruppi e
ne escono due fatture — quale è rimasto fuori?**

L'informazione si perdeva **per costruzione**, non per dimenticanza: questa funzione
aggrega per terna, e in quel `GROUP BY` i gruppi di partenza smettono di esistere. A
valle nessuno poteva più ricostruirli. È come versare tre sacchetti della spesa in un
carrello: il totale è giusto, la provenienza no.

⚠️ Ed era il caso **peggiore** dei tre esiti possibili, perché l'unico silenzioso:
«zero fatture» è un errore parlante dal 2026-08-04, e comunque insospettisce; «2 su 3»
sembra un successo, e il lavoro non fatturato resta fermo senza che nessuno lo cerchi.
Il gruppo non servito si ricava ora per **differenza** fra i richiesti e i coperti.

Tre cose da sapere se ci si mette mano:

* la chiave arriva da `vendite.fn_build_gruppo_fatturabile_key`, **unica fonte di
  verità** — la stessa che filtra nel `WHERE` e che alimenta `vw_dash_competenza_gruppi`.
  Non è ricostruita qui e non deve esserlo: sarebbe una seconda copia della regola;
* l'ordine è **deterministico** (`ORDER BY` dentro l'aggregato): senza, due chiamate
  identiche darebbero array diversi e chi li confronta vedrebbe differenze inesistenti;
* si calcola **sempre**, anche nel giro di massa. Costa una chiamata `STABLE` per riga
  candidata; l'alternativa — solo con `p_gruppi NOT NULL`, altrimenti `NULL` — è stata
  scartata perché produrrebbe un campo che a volte vale `NULL` per «non calcolato» e a
  volte per «nessun gruppo`. Quell'ambiguità si paga dopo, in silenzio.

> ℹ️ **Per chi consuma la funzione**: il campo è **opt-in**. I chiamanti nominano le
> colonne una per una, quindi la sesta non li tocca finché non la aggiungono alla
> propria `SELECT`.

---

### Criteri di inclusione (allineati alla pull e alla select)

1. Commessa in stato **emittibile** (`stati_commessa.emittibile = true`).
2. Righe `commesse_attivita` **`stato_approvazione = 'APPROVATA'` AND `stato_emissione =
   'NON_EMESSA'`** — allineato alla pull (`fn_emit_attivita_fatturabili_da_commessa` con
   `p_only_approved = true`). *Differenza* con `fn_list_commesse_emittibili`, che non filtra
   l'approvazione.
3. **`tipo_doc_fiscale_id IS NOT NULL`** (il lotto lo richiede NOT NULL; le righe con
   tipo_doc NULL sono escluse — il default si risolve all'upsert, non qui).
4. **Competenza cumulativa**: `competenza_mese <= p_competenza_mese` — coerente con
   `fn_select_attivita_fatturabili` (che filtra `<= v_competenza`). Così la discovery
   include gli **arretrati** (mesi precedenti) che la select poi cattura: nessun fatturato
   arretrato perso.
5. Filtri perimetro BA/utility/emittente; corsia `fatturazione_immediata`.

La grana di raggruppamento è **`(emittente, tipo_doc_fiscale, utility)`** con
`competenza_mese = max(...)`: lo stesso emittente con lavoro su più utility (es. gas + ee)
produce **terne distinte**, una per utility, ciascuna destinata a un lotto separato.

---

### Regole principali

* Funzione **STABLE** (read-only, nessun effetto collaterale).
* `LIMIT` sulle **terne** (non sulle commesse).
* `utility_id` in output **mai NULL** (`commesse.utility_id` è NOT NULL a monte).
* `fn_list_commesse_emittibili` resta separata e **invariata** (approccio A3).

---

### Esempio d'uso

```sql
-- corsia immediata, competenza fino a luglio 2026, un emittente specifico
SELECT * FROM vendite.fn_list_emittibili_lane(
  p_competenza_mese => DATE '2026-07-01',
  p_emittente_soggetto_ruolo_id => 55,
  p_fatturazione_immediata => true
);
-- -> (emittente, tipo_doc, utility, competenza_mese=max, total_candidate) per ogni terna
```

---

---

### Emissione mirata: `p_gruppi` (rev 2026-07-27)

Parametro `text[]`, default `NULL`. La discovery restituisce **solo le terne dei
gruppi richiesti**.

**Perché serve anche qui.** Il driver crea **un lotto per terna** restituita.
Senza il filtro, un'emissione mirata su un solo preventivo farebbe comunque
nascere un lotto per ogni terna con lavoro pronto nel perimetro: quei lotti
girerebbero pull e select (entrambi filtrati), non troverebbero nulla e
resterebbero lì. Non un errore di correttezza — la fattura sarebbe giusta — ma
lotti vuoti, task run, log e segnalazioni per lavoro che nessuno ha chiesto.

**Un gruppo può restare su più terne**, ed è corretto: `tipo_doc_fiscale_id` sta
sulla **riga** (`commesse_attivita`), non sulla testata del documento, quindi un
gruppo con righe di tipo diverso produce N lotti. La funzione le restituisce
tutte — ed è il motivo per cui l'esito verso il backend è una **lista** di
`lotto_id`, non uno solo.

---

### ⚠️ `gruppi_coperti` è una previsione, non un consuntivo (rev 2026-08-15)

Dice quali gruppi la discovery **si aspetta** di coprire. Fra quel momento e
l'esecuzione della pipeline le righe di un gruppo possono essere prese da un
altro giro: la pipeline esce senza errore e senza lotto, e l'esito legge pieno
successo mentre quel gruppo non è stato fatturato.

Per sapere cosa un giro ha fatturato **davvero** c'è
[`fn_esito_gruppi_giro(lotti)`](/dbzero/vendite/funzioni/fn_esito_gruppi_giro),
che misura a consuntivo. Le due cose convivono: questa serve *prima*, quella
serve *dopo*.

⚠️ Il campo si calcola **sempre**, anche nel giro di massa. Costo misurato: la
chiave vale ~5 µs a chiamata, cioè ~0,5 s ogni 100.000 righe candidate. E la
mitigazione «ovvia» — calcolare la chiave una volta sola in una `LATERAL` invece
che due volte fra argomento e `ORDER BY` — **non esiste**: il parser deduplica
già le due espressioni quando sono identiche, e le due forme misurano uguale.
Scritto perché è controintuitivo e qualcuno la riproverà.

---

### ⚠️ Il tetto `p_limit`, e le due risposte opposte (rev 2026-08-15)

`p_limit` (default 1000, massimo 10000) limita le **corsie**, non le righe. Se
ne taglia una, i gruppi che stavano dentro spariscono dal risultato — e a valle,
dove il non servito si ricava per differenza, diventerebbero *«questo gruppo non
è fatturabile»*: una diagnosi falsa su un gruppo che era solo oltre il taglio.

Il rimedio è **asimmetrico**, ed è il punto:

| | tetto toccato |
|---|---|
| giro di **massa** (`p_gruppi` `NULL`) | tronca in silenzio — lì è una valvola di sicurezza, e «cosa c'è da fare» ammette una risposta parziale |
| giro **mirato** (`p_gruppi` valorizzato) | **solleva** `E_FATTURAZIONE_MIRATA_TRONCATA` — il perimetro è nominale, e troncarlo significa non aver risposto |

È la stessa distinzione che il backend applica dal 2026-08 a «zero lotti su N
gruppi chiesti». ⚠️ Sollevando, il chiamante non riceve **nessuna** riga: non
esiste lo stato «mezza risposta più un errore».

{% include-markdown "signature-core.md" %}
