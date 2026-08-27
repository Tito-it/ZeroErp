## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_competenza_attivita`

> 👀 **Vedi anche**
>
Approfondimento tabelle e funzioni:
>
[vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)
> [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)
> [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa)
>
Famiglia due lenti:
>
[vw_dash_competenza_mensile](vw_dash_competenza_mensile.md)
> [vw_dash_competenza_errori](vw_dash_competenza_errori.md)
> [vw_dash_backlog_documenti](vw_dash_backlog_documenti.md)

---
### 🎯 Scopo Principale
(latest review 06-07-2026)
Vista di dettaglio della **Lente 1 Competenza** (cruscotti fatturazione a due
lenti, brief `brief-db-fatturazione-due-lenti` §4): una riga per **attività di
commessa computabile**, con la sua posizione nel funnel a valle
(commessa → attività fatturabile → riga fattura → stato fiscale) e la
dimensione dei **recuperi tardivi**. L'asse è la competenza **vera**
(`commesse_attivita.competenza_mese`, NOT NULL) — nessun proxy.

---

### Semantica

| Aspetto | Regola |
|---------|--------|
| **`stadio`** | `DA_APPROVARE` (BOZZA, non emessa) · `DA_EMETTERE` (approvata, non emessa) · `EMESSA_NON_FATTURATA` (riga AF con `fattura_riga_id` NULL) · `FATTURATA` (agganciata a riga fattura, con `stato_fattura_codice_interno` per il breakdown) |
| **Misura (DB-6)** | `valore = prezzo_snapshot × quantita` su **tutti** gli stadi (stessa misura del resolver commesse: funnel omogeneo); `valore_fatturato = fatture_righe.imponibile_riga` è la **riconciliazione** col fatturato reale |
| **`data_emissione` (DL-5)** | = `attivita_fatturabili.data_insert`. Validata 2026-07-06: la riga AF nasce una volta sola all'emissione, mai DELETE in produzione, il reset lotto fa solo UPDATE (la data non si sposta), nessuna re-emissione possibile |
| **`emessa_in_ritardo`** | `mese(data_emissione) > competenza_mese` — competenza M lavorata dopo M. NULL per attività non ancora emesse |
| **Perimetro (computabile)** | Esclude commesse `ANNULLATE` (testata) e attività void (predicato `20260703-61`: `stato_emissione <> 'ANNULLATA' AND (stato_approvazione <> 'RIFIUTATA' OR stato_emissione = 'EMESSA')`) |
| **Scope emittente** | In-vista via `script.fn_get_emittenti_scope_sr_ids(app.current_user_id)` da GUC: `NULL`=tutto · `'{}'`=niente · array=whitelist. `security_invoker = on` |
| `cliente_display` | Intestatario BA (`billing_account → soggetto_ruolo → soggetti`) |

---

### Esempio d'uso

```sql
-- Il mese M e' completo? Cosa manca, e cosa e' stato recuperato in ritardo.
SELECT stadio, count(*), sum(valore),
       count(*) FILTER (WHERE emessa_in_ritardo) AS recuperi_tardivi
FROM vendite.vw_dash_competenza_attivita
WHERE competenza_mese = DATE '2026-05-01'
GROUP BY stadio;
```

---

### Note operative

* **Il BE aggrega da `vw_dash_competenza_mensile`** e usa questa vista per il
  drill-down (layering come la famiglia `vw_dash_fatturazione_*`).
* ⚠️ **Caveat C1 (`data_insert`)**: il ramo UPDATE di idempotenza di
  `fn_emit_attivita_fatturabili_da_commessa` cerca la riga AF per
  `(sorgente_tipo_id, sorgente_uid)` **senza** filtrare per commessa: una
  collisione di `segment_key` fra attività diverse farebbe ereditare un
  `data_insert` **più vecchio**. Nessun percorso di produzione lo genera oggi;
  direzione benigna (il flag ritardo può solo **sotto-stimare**, mai falso
  positivo). Sentinella pgTAP sul reset in `test-vw-dash-competenza-v1.sql`.
* ⚠️ **Fail-closed dello scope**: senza GUC operatore (`app.current_user_id`)
  la vista restituisce **0 righe** (vale per superuser/psql/batch ad-hoc, il
  filtro-in-vista non è aggirato da `BYPASSRLS`). Per interrogare a mano:
  impostare la GUC. Il pgTAP la imposta esplicitamente.
* Un'attività `EMESSA` senza riga AF (solo manutenzioni fuori flusso) cade in
  `EMESSA_NON_FATTURATA` con `data_emissione` NULL: classificazione corretta,
  ritardo non calcolabile. ⭐ **Dal 2026-08-26 quel caso ha un nome**:
  `motivo_non_fatturata = 'SENZA_ATTIVITA_FATTURABILE'`, e la chiave del verbo
  resta `NULL` — vedi la sezione dedicata più in basso.
* ⚠️ **`EMESSA_NON_FATTURATA` è uno stadio RESIDUALE, non una tappa.** Pull e
  generazione righe stanno nello stesso step DRAFT: il percorso normale va da
  `DA_EMETTERE` a `FATTURATA` e questo stadio resta **vuoto** finché l'emissione
  e la fatturazione sono un gesto solo.

    > 🔴 **CORREZIONE (2026-08-26), e va letta prima di usare questa voce per
    > decidere.** Questo punto diceva due cose che oggi sono false, ed erano
    > entrambe vere quando furono scritte:
    >
    > 1. *«che azzera `fattura_riga_id` lasciando però `fatturato = t`»* — ⛔ non
    >    più possibile: dal `20260826-33` `fatturato` è una colonna **GENERATA**
    >    da `fattura_riga_id`, quindi il disaccordo fra le due **non è più
    >    rappresentabile**. È il lotto L3b del cantiere «il lavoro che non torna
    >    indietro»;
    > 2. *«chi legge un numero in questa card lo legga come una perdita
    >    silenziosa»* — ⛔ vero **solo** per una delle popolazioni. In questo
    >    stadio ne convivono più d'una, con **rimedi opposti**, ed è il motivo
    >    per cui esiste `motivo_non_fatturata`: chi emette in modo mirato ci
    >    vede passare lavoro perfettamente sano.
    >
    > 📌 Resta vero il **fatto datato** che motivò la voce: il 2026-08-26 la card
    > conteneva 5 AF di luglio (5.019 €) orfane della fattura 834 del lotto 603,
    > tutte residue. ⚠️ Ed è un fatto, non un motivo: il modello ammette le altre
    > popolazioni anche nel giorno in cui non ce n'è nessuna.
* Test: `db/pgtap/vendite/test-vw-dash-competenza-v1.sql`.

---

---

### Colonne di gruppo fatturabile (rev 2026-07-27)

Aggiunte **in coda** quattro colonne: `sorgente_tipo_id`, `sorgente_uid`,
`tipo_movimento`, `gruppo_key`.

`gruppo_key` viene da
[`fn_build_gruppo_fatturabile_key`](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key),
la **stessa** funzione usata dai filtri `p_gruppi` dell'emissione: le chiavi
mostrate sono esattamente quelle che l'emissione accetta.

Questa vista è la base di
[`vw_dash_competenza_gruppi`](/dbzero/vendite/views/vw_dash_competenza_gruppi),
che da qui eredita **scope emittente** e **coerenza dei conteggi con la card**.

⚠️ **Due vincoli su ogni futura modifica**:

1. `CREATE OR REPLACE VIEW` ammette solo l'**aggiunta di colonne in fondo**: non
   si possono rinominare, riordinare o eliminare quelle esistenti. L'ordine
   attuale è di fatto immutabile;
2. `WITH (security_invoker=on)` va **ri-specificato ogni volta**: la reloption
   non compare in `pg_get_viewdef` e PostgreSQL la azzera in silenzio,
   trasformando la vista in `security_definer` di fatto e aprendo un buco nello
   scope emittente su tutte le dashboard di competenza.

**Fail-closed senza GUC**: `script.fn_get_emittenti_scope_sr_ids(NULL)`
restituisce l'array **vuoto**, non `NULL`, quindi senza `app.current_user_id`
nessuna riga passa. Da tenere presente scrivendo test.

---

### 🆕 `commessa_stato_descrizione` (2026-08-15)

Aggiunta con `20260815-24` su richiesta del backend
([brief-db-emittibilita-visibile-e-sbloccabile](/dev/work-done/brief-db-emittibilita-visibile-e-sbloccabile)
§8.3), e propagata sui gruppi dal `20260815-25`.

La vista esponeva `commessa_stato_codice_interno` e nient'altro. A video va però
la **descrizione**: la convenzione del progetto è che le liste ricevano i campi
di display già decodificati dal DB, mai risolti lato client, e un codice interno
dentro un'interfaccia inglese — *«The job order is in state BOZZA»* — è il
sintomo che quella convenzione è stata aggirata.

Il backend si era messo un `LEFT JOIN` sul repository per cavarsela. Funzionava,
ed è la ragione per cui la richiesta era arancione e non rossa: ma quel JOIN **la
vista lo faceva già** — è da lì che arrivano `emittibile` e `codice_interno` — e
una seconda risoluzione della stessa cosa è la duplicazione che il §7.1 di quel
brief aveva già dovuto estrarre una volta, sul guard di transizione.

ℹ️ `COALESCE(descrizione, codice)` e non `descrizione` nuda: la colonna è
nullable a catalogo (il seed la valorizza su tutte e sei le righe, ma il DDL non
lo impone), e un campo di **display** che torna `NULL` produce una cella vuota,
che l'operatore legge come «non lo so» invece che come «manca il dato di
catalogo». `codice` è `NOT NULL` ed è la forma leggibile del mutabile: è il
ripiego giusto.


---

### 🆕 `emittente_ragione_sociale` *(R-4, 18-08-2026)*

Il nome dell'emittente **della commessa** arriva in coda alla proiezione.

⭐ **Il drill-down commesse può metterla nel `GROUP BY` in sicurezza**, e non è
una misura sui dati: nella vista quella colonna è `co.emittente_soggetto_ruolo_id`
dove `co` è `vendite.commesse`, e `commessa_id` è la sua **chiave primaria**.
L'emittente è un campo *della commessa*: una commessa ne ha uno solo per lo
stesso motivo per cui ha un solo codice, e non può avere attività di emittenti
diversi perché l'emittente non sta sull'attività. Non è una proprietà dei dati
che possa cambiare domani.

⚠️ **La colonna nel `GROUP BY` serve comunque.** PostgreSQL deduce da sé la
dipendenza funzionale quando si raggruppa per la chiave primaria di una
*tabella*, ma qui si raggruppa su una colonna di **vista**: la deduzione non
scatta. È innocua, non superflua.

⚠️ **Due catene distinte sulle stesse tabelle**: `sr`/`s` sono il **cliente**
(via billing account), `sr_ef`/`s_ef` l'**emittente**. Scambiarle non darebbe
nessun errore — solo un nome sbagliato a video.

⚠️ **Il flag `multi_emittente` della lista NON si accende insieme alla colonna.**
Si guadagna dopo, quando la colonna mostra un nome su dati veri (brief
perimetro-emittente §7, decisione 3). Il controllo automatico
`dbops.vw_liste_multi_emittente_non_certificate` deve restare a zero righe.

* Test: `db/pgtap/vendite/test-viste-dash-emittente-v1.sql`.

---

---

### 🆕 La chiave del verbo e la dimensione *(D-1, 26-08-2026)*

Changeset `20260826-54`, brief `brief-db-residui-competenza-dimensione-e-chiave`
(richiesta del backend). **Otto** colonne in coda.

| Colonna | Cosa | Perché
| --- | --- | --- |
| `attivita_fatturabile_id` | `attivita_fatturabili.id` | ⛔ **la chiave del verbo** |
| `lock_in_fatturazione` | `COALESCE(…, false)` | metà del discriminante |
| `stato_esecuzione` | l'altra metà | separa **l'orfana dal giro vivo** |
| `motivo_non_fatturata` | vocabolario chiuso, `NULL` fuori dallo stadio | **la dimensione** |
| `lotto_provenienza_id` · `_codice` | da `fatturazione_lotti` via `lock_batch_id` | «da dove viene questo residuo» |
| `articolo_codice` · `articolo_descrizione` | decode di `catalogo.articoli` | **che lavoro è** |

#### ⛔ Perché la chiave sta qui e non si traduce a valle

`vendite.fn_riporta_attivita_da_emettere` consuma `attivita_fatturabili.id`, e
nessuna vista lo esponeva: **il frontend non aveva la chiave del verbo**. Esiste
un `UNIQUE` 1:1 su `attivita_fatturabili(commessa_attivita_id)`, quindi il
backend *potrebbe* tradurre da sé — ma tradurre a mano un legame che il database
conosce già è una **seconda implementazione**, ed è la forma di difetto che il
cantiere precedente ha appena finito di pagare.

⚠️ `attivita_fatturabile_id` è un **identificatore**, non una colonna da
mostrare: non va a catalogo in `ui.lista_colonna`.

#### ⭐ La dimensione: lo stadio guarda una cosa sola

Il ramo `EMESSA_NON_FATTURATA` del `CASE` guarda **solo** `fattura_riga_id`, e
dentro quel valore finiscono situazioni con **rimedi opposti**:

| `motivo_non_fatturata` | Come si riconosce | Rimedio | Il verbo la tocca? |
| --- | --- | --- | --- |
| `IN_ATTESA_LOTTO` | non lucchettata | ⏳ nessuno: il prossimo giro la prende da sé | ⛔ no (`E_ATTIVITA_GIA_DA_EMETTERE`) |
| `GIRO_IN_CORSO` | lucchettata, `stato_esecuzione` ≠ `COMPLETED` | ⏳ si aspetta che il lotto finisca | ⛔ no (`E_ATTIVITA_IN_LAVORAZIONE`) |
| ⭐ `RESIDUO` | lucchettata **e** `COMPLETED`, senza riga di fattura | ✅ «Riporta da emettere» | ✅ sì |
| `SENZA_ATTIVITA_FATTURABILE` | nessuna riga in `attivita_fatturabili` | ⚠️ nessuno: non c'è niente da riportare | ⛔ no: **la chiave è `NULL`** |

⛔ **Non si spezza lo stadio in due valori.** Lo *stadio* dice **a che punto del
ciclo** è il lavoro, e queste situazioni sono allo **stesso punto**: cambia la
loro *salute*, non il loro *avanzamento*. Spezzarlo confonderebbe i due assi e
romperebbe un vocabolario consumato da whitelist BE, i18n FE e cataloghi di
lista. È lo stesso ragionamento con cui il 2026-08-20 `tipo_movimento` entrò
come **dimensione** e non come colonna `valore_rettifiche`.

#### ⛔ Le due superfici non devono poter divergere

`motivo_non_fatturata` e
[`script.fn_check_attivita_riportabile_da_emettere`](/dbzero/script/funzioni/fn_check_attivita_riportabile_da_emettere)
rispondono alla **stessa domanda** da due lati. Scritte due volte, divergono — e
la divergenza sarebbe **silenziosa**: la lista proporrebbe il verbo su una riga
che la mutazione rifiuta, oppure lo nasconderebbe su una che accetta.

Il presidio è `db/pgtap/vendite/test-motivo-non-fatturata-v1.sql`, con una
fixture **costruita** per ciascun caso: un test che itera su ciò che c'è
passerebbe a vuoto su un database ricostruito da zero, cioè in CI.

⛔ **`IS DISTINCT FROM 'COMPLETED'`, mai `<>`.** `stato_esecuzione` è
**nullable** e il `CHECK` ammette anche `ERRORE`: con un `<>` un lucchetto a
`NULL` darebbe `NULL`, il `CASE` cadrebbe sul ramo successivo e la vista direbbe
`RESIDUO` dove la funzione risponde `E_ATTIVITA_IN_LAVORAZIONE`. `ERRORE`
finisce perciò in `GIRO_IN_CORSO`, e il rimedio — aspettare che il lotto si
chiuda — è lo stesso.

⛔ **E `fatturato` non entra nel discriminante.** Dal `20260826-33` è generata da
`fattura_riga_id`: dentro `EMESSA_NON_FATTURATA` è **sempre falsa**, quindi non
distingue niente.

#### ⭐ Lo stadio si calcola una volta sola

`motivo_non_fatturata` è definito **sopra** lo stadio («`NULL` fuori da
`EMESSA_NON_FATTURATA`»), e in SQL un alias di `SELECT` non è riferibile da
un'altra espressione della stessa `SELECT`. Ricopiare la condizione avrebbe
messo la definizione dello stadio in **due posti della stessa vista**: la
`CROSS JOIN LATERAL … st` la calcola una volta e la serve a entrambe le colonne.
Valore, nome e tipo della colonna `stadio` non cambiano.

#### ⚠️ Il lotto di provenienza non è `lotto_id`

`lotto_id` arriva dalla catena della **fattura** (`fatture_righe → fatture →
fatturazione_lotti_fatture`): su un residuo la fattura **non c'è**, quindi è
`NULL` proprio sulle righe per cui la domanda si pone. `lotto_provenienza_*`
arriva invece da `attivita_fatturabili.lock_batch_id`, il timbro del giro che
l'ha lucchettata.

* il `LEFT JOIN` è lecito perché `fatturazione_lotti.lock_batch_id` ha un
  **`UNIQUE`**: non può moltiplicare le righe di una vista che ne alimenta altre
  quattro. Il vincolo è verificato in `preCondition` e ha un test suo;
* ⚠️ `LEFT` e non `INNER` perché `fatturazione_lotti` ha la **RLS**: un lotto
  fuori perimetro deve lasciare le colonne a `NULL`, non far sparire il residuo;
* ⚠️ `lotto_provenienza_codice` viene da `codice`, colonna **mutabile**: è
  display (§6c) e nessuna logica può appoggiarcisi.

#### ℹ️ I due JOIN nuovi non li paga chi non li usa

La ragione è **strutturale, non una misura**: entrambi sono `LEFT JOIN` su
chiavi con indice `UNIQUE`, quindi PostgreSQL può *provare* che non moltiplicano
le righe e li **elimina dal piano** quando nessuna delle loro colonne è
selezionata (*left join removal*).

📌 Fatto datato, e non è il motivo: il 2026-08-26 nei piani di
`vw_dash_competenza_gruppi` e della vista stessa interrogata senza le colonne
nuove non compare nessuna scansione di `fatturazione_lotti` né di
`catalogo.articoli`. ⚠️ **La condizione che regge tutto è il `UNIQUE`**:
togliendolo, l'eliminazione smetterebbe di essere lecita e la vista comincerebbe
a contare doppio in silenzio.

* Test: `db/pgtap/vendite/test-motivo-non-fatturata-v1.sql` (17 asserzioni).
* Lista a catalogo: `ui.lista_definizione` **49** —
  `vendite.dash_competenza_residui`.

---

{% include-markdown "signature-core.md" %}
