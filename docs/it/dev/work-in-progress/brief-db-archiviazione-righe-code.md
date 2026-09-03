# Brief DB — archiviare una riga di coda senza toccarne lo stato

> **Chi scrive:** BE/FE (`dev/backend-tid`), 2026-09-03.
> **A chi:** team DB.
> **Da dove nasce:** richiesta di Tid sulle due liste «Code di lavoro»
> (`CodaLavoriTab`, `CodaStampaTab`): poter togliere righe dall'elenco **senza**
> cancellarle né annullarle, perché i conteggi del pannello **Esiti
> fatturazione** devono restare fermi.
> **Decisioni di Tid (2026-09-03):** si archiviano **solo righe in stato
> terminale**; l'archiviazione ha un **interruttore «mostra archiviate» + il
> conteggio**; vale **per tutti**, non per operatore.
> **Stato:** 🔴 in attesa del prerequisito DB. BE e FE **non partono** finché le
> colonne non ci sono.

---

## 1. Il fatto, verificato

Nessuna delle due code ha oggi un flag di visibilità.

| Tabella (lista) | Stati ammessi | Flag | Verbo «annulla» |
| --- | --- | --- | --- |
| `dbops.coda_lavori` | PENDING · IN_CORSO · FATTO · ERRORE · ANNULLATO | ❌ | sì, **solo** su PENDING |
| `vendite.fatture_stampa_coda` | PENDING · IN_CORSO · FATTO · ERRORE | ❌ | **non esiste** |

⚠️ **E le due strade che l'operatore ha oggi spostano i numeri**, che è la
ragione della richiesta. I conteggi del pannello Esiti vengono da
`VenditePipelineRepository.count_coda_stampa_per_stato` — un `GROUP BY c.stato`
su `fatture_stampa_coda`, ristretto al mese via `lotto_id`, **senza alcun filtro
di visibilità**:

* un `DELETE` fa **calare** il numero;
* un ANNULLA — che sulla coda stampa non esiste, ma che sarebbe la mossa ovvia
  da aggiungere — **sposterebbe** la riga da FATTO/ERRORE a ANNULLATO, cioè
  cambierebbe la ripartizione che l'operatore sta leggendo.

⇒ Serve un flag che la **lista** legge e che **nessun altro** legge.

---

## 2. La richiesta

### 2.1 Due colonne, simmetriche

```sql
ALTER TABLE dbops.coda_lavori
  ADD COLUMN archiviato boolean NOT NULL DEFAULT false;

ALTER TABLE vendite.fatture_stampa_coda
  ADD COLUMN archiviato boolean NOT NULL DEFAULT false;
```

⭐ **Simmetriche dal primo giorno**, non «prima una poi l'altra»: le due code
sono gemelle, hanno lo stesso scheletro di lista (`CodaTabBase`) e la stessa
domanda. Un'asimmetria qui si paga al primo che tocca solo una delle due.

### 2.2 ⛔ Sul NOME — perché non `disabilitato` né `attivo`

In `vendite` la stessa idea esiste già e si chiama **`disabilitato`**
(`fatturazione_lotti_log`, `fatture_log`), con la disciplina già rodata
(nascoste di default + `ritirate_count` che dichiara quante). Riusare quel nome
sarebbe la scelta di default, e **qui è quella sbagliata**:

* là le righe sono **segnali passivi** — `disabilitato` significa «ritirato,
  non lo si mostra più», e non c'è nient'altro che quella riga possa fare;
* qui le righe sono **lavoro** — `disabilitato` su una riga di coda si legge
  come *«non eseguirlo»*, che è l'opposto di ciò che deve fare. Stesso problema
  con `attivo`, che per giunta collide con la famiglia
  `trgfn_prevent_deactivate_if_children`.

**`archiviato`** dice *messo via dall'elenco*, non *spento*. ⚠️ Il nome qui non è
cosmetica: è l'unica cosa che impedisce al prossimo che legge la colonna di
aggiungerla al `WHERE` del claim «per coerenza».

### 2.3 Il guard — solo stati terminali

Trigger `BEFORE UPDATE OF archiviato`, fase `_a10_` (guard):

| Tabella | Terminali (archiviabili) | Vivi (rifiutati) |
| --- | --- | --- |
| `dbops.coda_lavori` | FATTO · ERRORE · ANNULLATO | PENDING · IN_CORSO |
| `vendite.fatture_stampa_coda` | FATTO · ERRORE | PENDING · IN_CORSO |

Nomi proposti (convenzione `linee-guida-trigger`):
`trg_coda_lavori_a10_guard_archiviazione_upd` /
`trg_fatture_stampa_coda_a10_guard_archiviazione_upd`.

**Perché il perimetro è questo, e non è prudenza.** Il badge in topbar conta i
«vivi» (`PENDING|IN_CORSO`, sede unica `STATI_CODA_VIVI`). Archiviare una riga
viva la lascerebbe **nel conteggio** e fuori dall'**elenco**: l'operatore legge
«2 lavori vivi» e apre una lista dove non c'è niente, senza nessun modo di
arrivarci per rimetterla a posto. Sulle terminali il problema non esiste **per
costruzione**: non sono vive, non sono reclamabili, e l'indice unico parziale
`uq_fatture_stampa_coda_vivo` non le vede — quindi ri-accodamento e ristampa
restano intatti.

### 2.4 ⭐ Il pezzo che si scopre solo guardando i verbi vicini: **requeue**

`CodaLavoriRepository.requeue` riporta una riga da IN_CORSO/ERRORE a **PENDING**.
Una riga **archiviata e poi rimessa in coda** sarebbe viva e invisibile — cioè
esattamente il difetto che il §2.3 evita, rientrato dalla porta di servizio.

⇒ Lo stesso trigger, su `UPDATE OF stato`: **se il nuovo stato non è terminale,
`archiviato` torna `false`**. Non un rifiuto — una riga che torna al lavoro deve
tornare nell'elenco, ed è la regola «chi alza la bandiera la abbassa» applicata
qui.

⚠️ È la ragione per cui questo è un brief e non una riga di richiesta: le due
colonne da sole passerebbero ogni verifica e lascerebbero il buco aperto.

### 2.5 Quando l'archiviazione è avvenuta

```sql
ADD COLUMN archiviato_il timestamptz NULL
```

⛔ **`data_update` non è un sostituto affidabile**, e sembra esserlo: è l'istante
dell'**ultimo** update qualunque esso sia. Oggi sulle terminali nessuno scrive
più, quindi coinciderebbe — ma è una coincidenza che regge finché nessuno tocca
il drainer, non una garanzia. Serve alla lista «mostra archiviate» per dire
*quando* è stata messa via.

⚠️ Chi l'ha archiviata resta su `user_update`: lì la coincidenza regge davvero,
perché la scrittura è la stessa.

### 2.6 Codice errore

Il guard del §2.3 deve sollevare un codice **registrato a catalogo con la sua
classe** (`config.codici_errore`), non un `E_GENERICO`:

| Codice | Classe | Perché |
| --- | --- | --- |
| `E_CODA_ARCHIVIAZIONE_NON_AMMESSA` | `CONFLITTO_STATO` (409) | non è un dato sbagliato: è la riga che in questo momento è ancora viva |

Con la sua `soluzione` a catalogo («attendi che il lavoro finisca, oppure
annullalo prima di archiviarlo»): è la frase che arriva all'operatore come
`hint`. Il messaggio nomina **lo stato**, non il nome della colonna.

⚠️ Lato BE, dopo il seed: `./manage-env.sh genera_error_policies` più la voce in
`error_messages_fallback.py`. Lo facciamo noi, ma solo dopo il vostro apply.

---

## 3. Chi legge il flag — e chi NON deve leggerlo

⛔ **Un solo lettore: la lista.** Se lo leggessero anche claim, drainer o reaper,
archiviare diventerebbe **un annullamento silenzioso** — cioè peggio della
cancellazione che questa richiesta esiste per evitare.

| Lettore | Legge `archiviato`? |
| --- | --- |
| `elenca` / `elenca_coda_stampa` (le due liste) | ✅ sì, `= false` di default |
| `count_coda_stampa_per_stato` (**Esiti fatturazione**) | ⛔ **NO** — è il punto della richiesta |
| `count_per_stato` / `get_stato` (badge topbar) | ⛔ NO (e per il §2.3 è indifferente) |
| claim · `reap_stale` · `mark_done` · `mark_error` · drainer | ⛔ **NO, mai** |
| `uq_fatture_stampa_coda_vivo` | ⛔ NO (parziale su PENDING/IN_CORSO) |

⚠️ **Nessun indice nuovo per ora**: entrambe le liste filtrano già per `stato` e
per intervallo di date, e l'archiviazione si somma a quelli. Lo si valuta se e
quando le code cresceranno — un indice adesso sarebbe una previsione, non una
misura.

---

## 4. Quello che resta a noi (dopo il vostro apply)

* filtro `archiviato = false` di default nelle due `elenca`, con parametro per
  chiederle;
* **`archiviate_count`** nell'envelope della lista: senza quel numero «coda
  pulita» e «tre righe messe via» si leggono uguali — è la stessa lezione di
  `ritirate_count` sul giornale della fattura;
* verbo «Archivia» / «Ripristina» nel kebab di riga (`RowActionsMenu`), gated
  come gli altri due verbi di coda (`code_manage`), con `disabled` + `tooltip`
  che porta il motivo quando la riga è ancora viva;
* interruttore «mostra archiviate» nella toolbar di `CodaTabBase` — una sola
  volta, le due schede lo ereditano.

---

## 5. ⚠️ Nota a margine, fuori richiesta ma di vostra competenza

`docs/it/dbzero/vendite/manual/fatture_stampa_coda.md` dice, a proposito della
RLS: *«in G1 la coda non ha superficie di lettura → nessuna policy»*.

**Quella premessa non è più vera**: la coda stampa ha una lista a video dal
brief gestione-code (`elenca_coda_stampa`, scheda «Coda stampa» di Strumenti).
Lo scope oggi è **applicativo** — `add_emittente_scope_condition` sulla fattura
collegata — quindi non c'è un buco aperto adesso; ma la frase che decide se
serve una policy descrive un mondo che non c'è più, ed è il genere di riga che
resta vera in archivio e falsa nel prodotto.
