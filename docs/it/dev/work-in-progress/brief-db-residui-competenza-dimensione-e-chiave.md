# Brief DB — i residui di competenza: la chiave che manca e la dimensione che manca

> **Destinatario:** team DB (`dev/db-tid`). BE e FE **attendono**
> ([[feedback_be_fe_attende_prerequisiti_db]]).
>
> **Origine.** 2026-08-26, scrivendo il piano applicativo di
> [brief-be-fe-lavoro-che-non-torna-indietro.md](brief-be-fe-lavoro-che-non-torna-indietro.md),
> cioè la metà BE/FE del cantiere che il team DB ha appena chiuso
> ([brief-db-lavoro-che-non-torna-indietro.md](../work-done/brief-db-lavoro-che-non-torna-indietro.md)).
> Il verbo **«Riporta da emettere»** è applicato, collaudato sulle 5 righe vere e
> documentato. ⛔ **A video non può esistere**: la sua chiave non esce da nessuna
> vista, e la card su cui dovrebbe vivere conta due popolazioni con **rimedi
> opposti**.
>
> ⭐ **La richiesta è piccola, ed è diventata piccola guardando come sono fatte
> le liste sorelle**: non serve una vista nuova. Servono **quattro colonne in
> coda a una vista che esiste** e **una dimensione in più in un `GROUP BY`**.
>
> ⛔ **Nessun file scritto, nessuna migrazione applicata**
> ([[feedback_db_actions_passaggio_team]], [[feedback_mai_applicare_migrazioni_db]]).
>
> 🔴 **Quella riga vale per la RICHIESTA, non per lo stato di oggi.** Il lato DB
> è **scritto e APPLICATO** (migrate di Tid, 2026-08-27 08:20): vedi §6. Restano
> aperte le due consegne BE/FE del §7, e la prima è un **cancello CI rosso**.

---

## 1. Il fatto, in tre righe

`vendite.fn_riporta_attivita_da_emettere(p_attivita_fatturabili_ids bigint[])`
consuma **`vendite.attivita_fatturabili.id`**.

`vendite.vw_dash_competenza_attivita` — l'unica vista che alimenta la Lente 1 —
espone `commessa_attivita_id`, `fattura_riga_id`, `af.sospesa`, `af.posticipa_al`,
`af.data_insert`… **e mai `af.id`**. La vista tocca già `attivita_fatturabili`
con l'alias `af`: la colonna non manca per un limite, manca perché finora non
serviva a nessuno.

⇒ **Il frontend non ha la chiave del verbo.**

⚠️ Esiste un `UNIQUE` 1:1 su `attivita_fatturabili(commessa_attivita_id)`, quindi
il backend *potrebbe* tradurre `commessa_attivita_id → af.id` con una query sua.
⛔ **Non lo faccio, ed è una scelta di merito**: tradurre a mano una chiave che il
database conosce già è una **seconda implementazione di un legame**, ed è
esattamente la forma di difetto che questo cantiere ha appena finito di pagare —
due dati autonomi che descrivono lo stesso fatto e prima o poi divergono.

---

## 2. La seconda cosa, ed è di modello: la card conta due popolazioni

`vw_dash_competenza_attivita` assegna lo stadio così:

```sql
WHEN ca.stato_emissione <> 'EMESSA' AND ca.stato_approvazione <> 'APPROVATA' THEN 'DA_APPROVARE'
WHEN ca.stato_emissione <> 'EMESSA'                                          THEN 'DA_EMETTERE'
WHEN af.fattura_riga_id IS NULL                                              THEN 'EMESSA_NON_FATTURATA'
ELSE 'FATTURATA'
```

Il terzo ramo guarda **solo** il legame con la riga di fattura. Dentro
`EMESSA_NON_FATTURATA` finiscono quindi **tre** situazioni, e il perimetro del
verbo ne è **una sola** — sono le stesse tre che
`script.fn_check_attivita_riportabile_da_emettere` distingue:

| Situazione | Come si riconosce | Rimedio | Il verbo la tocca? |
| --- | --- | --- | --- |
| **in attesa del suo lotto** | `lock_in_fatturazione` falso | ⏳ nessuno: il prossimo giro la prende da sé | ⛔ no (`E_ATTIVITA_GIA_DA_EMETTERE`) |
| **dentro un giro vivo** | lucchettata, `stato_esecuzione` ≠ `COMPLETED` | ⏳ si aspetta che il lotto finisca | ⛔ no (`E_ATTIVITA_IN_LAVORAZIONE`) |
| ⭐ **residuo** | lucchettata **e** `COMPLETED`, senza riga di fattura | ✅ «Riporta da emettere» | ✅ sì |

⛔ **Due delle tre non chiedono nessuna azione, la terza sì.** Un numero solo per
rimedi opposti è la stessa ambiguità che il cantiere ha appena chiuso un livello
più in giù, e a video produce il difetto peggiore: la guida operativa §3.1 dice
oggi *«se in quella casella c'è un numero, qualcosa si è rotto»* — che è vero
**solo** per la terza riga della tabella.

📌 **Fatto datato — e non è un motivo.** Il 2026-08-26, con contesto operatore
impostato (`app.ruolo_applicativo = 'OPERATORE'` **e** `app.current_user_id`, la
vista è `security_invoker` **e** fail-closed: senza entrambe risponde **zero**, e
lo zero sembra un dato — [[feedback_rls_conteggio_zero_non_e_un_dato]]), la card
contiene **5 righe su 5 residue** e nessuna delle altre due specie.

⛔ **La misura non decide niente qui.** Il modello **ammette** le altre due — si
legge dal `CASE` della vista, che è **struttura**, non popolazione — e una lista
costruita sui dati di oggi si romperebbe il primo giorno in cui il caso capita,
in silenzio, disfacendo emissioni corrette. Zero occorrenze non significa che il
caso non esiste.

---

## 3. Le richieste

### D-1 — quattro colonne in coda a `vw_dash_competenza_attivita`

| Colonna | Cosa | Perché |
| --- | --- | --- |
| `attivita_fatturabile_id` | `af.id` | ⛔ **la chiave del verbo**, oggi irraggiungibile (§1) |
| `lock_in_fatturazione` | `COALESCE(af.lock_in_fatturazione, false)` | è metà del discriminante |
| `stato_esecuzione` | `af.stato_esecuzione` | è l'altra metà — ⭐ ed è ciò che separa **l'orfana dal giro vivo** |
| ⭐ `motivo_non_fatturata` | vocabolario chiuso, `NULL` fuori da `EMESSA_NON_FATTURATA` | la **dimensione** del §2 |

**Vocabolario proposto** per `motivo_non_fatturata` — tre valori, uno per riga
della tabella del §2:

```text
IN_ATTESA_LOTTO   -- non lucchettata: il prossimo giro la prende
GIRO_IN_CORSO     -- lucchettata, stato_esecuzione <> 'COMPLETED'
RESIDUO           -- lucchettata e COMPLETED, senza riga di fattura
```

> 🔴 **I valori applicati sono QUATTRO, e il terzo confronto non è `<>`.** Vedi
> §6.2: il modello ammette una quarta situazione che questo elenco non prevede,
> e `stato_esecuzione` è **nullable**.

⚠️ **Perché una colonna e non tre booleani sparsi**: il consumatore deve poter
dire *quale* delle tre, non ricomporla — e l'export della lista, che condivide la
stessa proiezione, deve poterla scrivere in chiaro.

⛔ **E NON si aggiunge `fatturato`.** Dal `20260826-33` è una colonna generata da
`fattura_riga_id`, quindi dentro `EMESSA_NON_FATTURATA` è **sempre falsa**: come
discriminante non distingue niente. È la stessa trappola già evitata nel §9.5.0
del brief precedente.

### D-2 — la dimensione entra nel `GROUP BY` di `vw_dash_competenza_mensile`

Perché la card possa mostrare **due numeri** invece di uno (decisione di Tid,
2026-08-26: *la card si spezza in due*), `motivo_non_fatturata` deve entrare fra
le dimensioni dell'aggregata, accanto a `stadio`, `stato_fattura_codice_interno`
e `tipo_movimento`.

⭐ **C'è un precedente esatto, sulla stessa vista, con la stessa forma e la stessa
ragione**: la rev del 2026-08-20 che ha aggiunto `tipo_movimento` al
raggruppamento. Il `COMMENT` di quella revisione dice *«la compensazione NASCONDE
LAVORO»* e conclude che *«si aggiunge la DIMENSIONE e non una colonna
`valore_rettifiche`, che avrebbe messo i valori dell'enum dentro la vista»*.
**Qui vale identico**: non una colonna `n_residui`, una dimensione.

⚠️ **E porta con sé la stessa conseguenza dichiarata allora**: cambia la
**cardinalità** dell'aggregata. I totali del consumatore reggono perché il pivot
accumula, ma **il breakdown elenca una voce per riga**: senza adeguamento il
frontend mostrerebbe `EMESSA_NON_FATTURATA` due volte. È lavoro BE/FE, sta nel
brief applicativo, e va fatto **nello stesso giro**.

### D-3 — ⭐ il presidio: la vista e la `fn_check_*` non devono poter divergere

`motivo_non_fatturata` e `script.fn_check_attivita_riportabile_da_emettere`
rispondono alla **stessa domanda** da due superfici. Scritte due volte,
divergono — e la divergenza sarebbe **silenziosa**: la lista proporrebbe il verbo
su una riga che la mutazione rifiuta, oppure lo nasconderebbe su una che lo
accetta.

Chiedo un **pgTAP che le lega**, sul modello del *«test che vale»* già usato per
`fn_elimina_fattura_da_lotto`: costruita una fixture per **ciascuno** dei tre
casi, il `motivo_non_fatturata` della vista e il `codice` che la `fn_check_*`
compone devono corrispondere. ⚠️ Fixture **costruite**, non scelte: un test che
itera su ciò che c'è passa a vuoto su un database ricostruito da zero, cioè in CI.

### D-4 — il seed della lista dei residui

`ui.lista_definizione` + le righe di `ui.lista_colonna`, sul modello delle tre
sorelle già a catalogo:

> 🔴 **CORREZIONE (2026-08-26, team DB): l'id libero non è 44, è 49.** Il 44 è
> già `vendite.fondi_fattura_da_decidere` (2026-08-15) e il catalogo è arrivato
> a **48**. ⚠️ Il numero qui sopra era una **fotografia** del catalogo, presa
> quando è stato scritto il brief: è la ragione per cui un id libero non si
> dichiara in un documento — si legge dal CSV nel momento in cui si semina.


```text
41  vendite.dash_competenza_errori     Competenza — errori vivi
42  vendite.dash_competenza_gruppi     Competenza — gruppi fatturabili
43  vendite.dash_competenza_commesse   Competenza — drill-down commesse
44  vendite.dash_competenza_residui    Competenza — residui da riportare   ← nuova
```

⭐ **`vista_sql` può restare `NULL`**, come nelle tre sorelle: la query la compone
il backend leggendo `vw_dash_competenza_attivita`. È il motivo per cui questa
richiesta **non contiene una vista nuova**.

Colonne suggerite: commessa (codice), cliente, articolo, competenza, valore,
data attività, **lotto di provenienza** (⭐ è l'informazione che risponde a *«da
dove viene questo residuo»*, e oggi non si vede da nessuna parte) e il
`motivo_non_fatturata`. ⚠️ `attivita_fatturabile_id` serve al verbo, non
all'occhio: identificatore, non colonna da mostrare.

### D-5 · D-6 — due messaggi a catalogo che mandano dalla parte sbagliata

Non bloccano niente, ma dicono il falso a chi legge:

| # | Codice | Cosa dice oggi | Cosa dovrebbe dire |
| --- | --- | --- | --- |
| **D-5** | `E_PREV_ANNULLA_COMMESSA_EMESSA` | la `soluzione` indica *«nota di credito o storno delle attività già emesse»*, cioè **la strada di prima** | il §9.7.4 del brief precedente dichiarava che *«il suo testo guadagna il rimedio»*: la via d'uscita adesso esiste e si chiama **«Riporta da emettere»** |
| **D-6** | `E_RIGA_COMMESSA_NON_MANUALE` (guard 4 di `fn_annulla_commessa_attivita`) | *«il rimedio è SEMPRE a monte, sul documento»* | ⭐ **da L7b quella frase è vera**: il messaggio può **nominare** il documento invece di lasciarlo cercare (già registrato come «cosa resta di L7», §14.9) |

---

## 4. Cosa NON sto chiedendo, e perché

| Non chiesto | Perché |
| --- | --- |
| una vista nuova `vw_dash_competenza_residui` | le tre liste sorelle della stessa Lente hanno `vista_sql = NULL` e la query la compone il backend. Una vista in più sarebbe un oggetto da mantenere per un `WHERE` |
| di **spezzare il valore** `EMESSA_NON_FATTURATA` in due stadi | ⛔ lo **stadio** dice *a che punto del ciclo* è il lavoro, e le tre situazioni sono allo **stesso punto**: cambia la loro *salute*, non il loro avanzamento. Spezzarlo confonderebbe i due assi, e romperebbe un vocabolario consumato da whitelist BE, i18n FE e cataloghi di lista. La dimensione dice la cosa giusta e non tocca lo stadio |
| che il verbo diventi asincrono / passi da `dbops.coda_lavori` | è **sincrono** per progetto (§11.2 del brief precedente): due scritture, una transazione. La coda porterebbe la dedup, che qui non serve |
| di bonificare le 5 righe residue | ⛔ **sono il banco di prova**, e il recupero vero è il primo gesto del frontend. Se il verbo non le prende, non ha fallito la bonifica: **ha fallito il perimetro** |

---

## 5. Trappole

1. ⚠️ **`vendite.attivita_fatturabili` non ha RLS, `vendite.commesse_attivita` sì.**
   Qualunque lettura che parta dalla prima è **fail-open sullo scope**. La vista
   parte già da `commesse` → `commesse_attivita`, quindi il cancello c'è: va solo
   **non aggirato** aggiungendo le colonne nuove.
2. ⚠️ **`security_invoker=on` non è visibile in `pg_get_viewdef`** e va
   **ri-specificata** a ogni `CREATE OR REPLACE VIEW`, su **entrambe** le viste:
   altrimenti PostgreSQL la azzera in silenzio e lo scope emittente sparisce.
   È già scritto nel `COMMENT` di tutte e due, ed è il tipo di cosa che si perde
   proprio quando si tocca la vista per un motivo diverso.
3. ⚠️ **La vista chiama già due funzioni per riga** (`fn_resolve_registro_documento`,
   `fn_calcola_data_documento`) e ne alimenta altre quattro: il costo è
   dichiarato nel suo `COMMENT`. Le quattro colonne nuove sono lettura diretta di
   `af`, che è già nel `FROM` — non aggiungono un `JOIN`.
4. ⚠️ **Il corpo si prende dalla doc auto-gen, non dagli YAML**: su questa vista
   ci sono già più revisioni (2026-08-18 emittente, 2026-08-26 registro e data
   prevista), e partire da uno YAML le **regredirebbe in silenzio**.
5. ⚠️ **Cambiare il `GROUP BY` dell'aggregata rende rossi i test che ne contano
   le righe.** Cercarli **dal codice**, non dalla direzione del cambio: la
   lezione della regressione di L7b è che un guard allargato rompe i test come
   uno ristretto, al contrario.

---

---

## 6. Risposta del team DB — ✅ **APPLICATO** (migrate di Tid, 2026-08-27 08:20)

> ✅ **I tre changeSet sono `EXECUTED`**, e non lo dice questo brief: lo dice
> `databasechangelog` ([[feedback_stato_apply_si_legge_dal_databasechangelog]]).
>
> ```text
> 20260826-54-update-vw-dash-competenza-attivita-motivo-non-fatturata   EXECUTED
> 20260826-55-update-vw-dash-competenza-mensile-motivo-non-fatturata    EXECUTED
> 20260826-56-update-fn-annulla-commessa-attivita-nomina-documento      EXECUTED
> ```
>
> I tre mirror `runOnChange` dei seed risultano **`RERAN`** nello stesso
> migrate (`20260507-06` liste, `20260806-15` colonne, `20260614-08` messaggi):
> è la conferma che i CSV sono entrati **dalla loro sede** e non da un `UPDATE`
> a parte.
>
> **Verificato sugli oggetti vivi**: 8/8 colonne nuove sul dettaglio,
> `security_invoker=on` su **entrambe** le viste (la reloption che un `REPLACE`
> azzera in silenzio), lista `49` con 11 colonne, le due `soluzione` riscritte,
> e il guard 4 che chiama davvero il resolver.
>
> ⛔ **Nessun commit** ([[feedback_no_commit_autonomo]]).

### 6.0 ⭐ Cosa la prova pre-apply NON poteva dire — e adesso è detto

⚠️ I pgTAP provati **prima** del migrate girano per forza da **owner**
([[reference_pgtap_pre_apply_gira_solo_da_owner]]), e l'owner **non è soggetto
alla RLS**: quella corsa verde non aveva esercitato nessuna policy. Le due viste
sono `security_invoker` e il perimetro del verbo *è* la RLS su
`vendite.commesse_attivita`, quindi era il pezzo che contava di più.

Rigirati **come applicazione** (`PGTAP_RUNNER=app`) a migrate fatto:

| File | Esito |
| --- | --- |
| `vendite/test-motivo-non-fatturata-v1` | ✅ **17/17** |
| `vendite/test-annulla-commessa-attivita-v1` | ✅ **28/28** (incluso il 18-bis di D-6) |
| `vendite/test-fn-list-commessa-attivita-provenienza-v1` | ✅ **28/28** (incluso il 22, la grana) |

E `scripts/pgtap-baseline.sh vendite` (Tid): **nessuna regressione**.

⚠️ La doc auto-generata è stata rigenerata dal migrate e riflette gli oggetti
vivi — comprese le due viste e `fn_annulla_commessa_attivita`, che adesso mostra
la chiamata al resolver.

### 6.1 Cosa c'è

| # | File | Cosa |
| --- | --- | --- |
| **54** | `20_code/vendite/…-update-vw-dash-competenza-attivita-motivo-non-fatturata-mctit.yaml` | D-1 — **otto** colonne in coda al dettaglio |
| **55** | `20_code/vendite/…-update-vw-dash-competenza-mensile-motivo-non-fatturata-mctit.yaml` | D-2 — la dimensione entra nel `GROUP BY` |
| **56** | `20_code/vendite/…-update-fn-annulla-commessa-attivita-nomina-documento-mctit.yaml` | D-6 — il guard 4 **nomina** il documento |
| — | `80_data/sql/ui/lista_definizione.csv` · `lista_colonna.csv` | D-4 — lista **49** + 11 colonne (555…565) |
| — | `80_data/sql/config/messaggi_errore.csv` | D-5 e D-6 — le due `soluzione` riscritte |
| — | `db/pgtap/vendite/test-motivo-non-fatturata-v1.sql` | D-3 — **nuovo**, 17 asserzioni |
| — | `db/pgtap/vendite/test-fn-list-commessa-attivita-provenienza-v1.sql` | test 22 portato sulla grana nuova |
| — | `db/pgtap/vendite/test-annulla-commessa-attivita-v1.sql` | 18-bis: il presidio della **frase** di D-6 |
| — | 3 schede in `dbzero/vendite/manual/` + `guide/cruscotti-fatturazione.md` §3.1 | la doc, con **due affermazioni corrette** |

### 6.2 ⭐ Tre cose che il brief non prevedeva, e perché sono entrate

Tutte e tre nascono dalla stessa domanda — *«il modello lo ammette?»* — e non da
una misura sui dati.

#### 1. ⛔ `IS DISTINCT FROM 'COMPLETED'`, non `<>`

`attivita_fatturabili.stato_esecuzione` è **nullable** dal `20260222-01-02` e il
`CHECK` ammette anche `ERRORE`. Con il `<>` del vocabolario proposto, un
lucchetto a `NULL` darebbe `NULL`, il `CASE` cadrebbe sul ramo successivo e la
vista direbbe **`RESIDUO` su una riga che la mutazione RIFIUTA** — cioè
esattamente la divergenza silenziosa che il D-3 esiste per impedire.
`fn_check_attivita_riportabile_da_emettere` usa `IS DISTINCT FROM`, e la vista
adesso usa lo stesso.

ℹ️ Conseguenza dichiarata: **`ERRORE` finisce in `GIRO_IN_CORSO`**. Il nome dice
«il giro non ha finito», che è vero, e il rimedio è identico.

#### 2. ⭐ Un **quarto** valore: `SENZA_ATTIVITA_FATTURABILE`

Il `LEFT JOIN` ammette una riga di commessa a `EMESSA` **senza nessuna riga in
`attivita_fatturabili`**, e il guard di `DELETE` su quella tabella ammette per
progetto la cancellazione di una riga non ancora fatturata.

⛔ Senza un ramo suo cadrebbe su `IN_ATTESA_LOTTO` per via del `COALESCE`, cioè
*«il prossimo giro la prende»* — **falso**: la pull filtra su `stato_emissione` e
non la riprende mai più. E `attivita_fatturabile_id` sarebbe `NULL`, quindi il
verbo non avrebbe nemmeno la chiave: la lista lo proporrebbe su una riga senza
bersaglio.

⚠️ **Nessun percorso scritto oggi la produce** — cercato: in tutto il repo non
c'è un solo `DELETE FROM vendite.attivita_fatturabili`. Non è una ragione per
non trattarla: *zero occorrenze non significa che il caso non esiste*, e la
fixture del pgTAP se lo **costruisce**.

➡️ **Per il BE**: la whitelist del vocabolario ha **quattro** valori, non tre.

#### 3. ⭐ Quattro colonne in più delle quattro chieste

Il D-4 elenca fra le colonne suggerite il **«lotto di provenienza»** e
l'**«articolo»**, e nessuna delle due era raggiungibile dalla vista:

| Colonna | Perché non bastava quello che c'era |
| --- | --- |
| `lotto_provenienza_id` · `_codice` | ⛔ `lotto_id` nasce dalla catena della **fattura**, e su un residuo la fattura **non c'è**: era `NULL` proprio sulle righe della lista nuova. Il legame vero è `af.lock_batch_id`, che ha un **`UNIQUE`** gemello su `fatturazione_lotti` |
| `articolo_codice` · `_descrizione` | ⛔ la vista esponeva il solo `articolo_id`, che è un **UUID**: una lista su cui si deve *agire* e che non dice quale lavoro sta chiedendo l'azione non è azionabile. Il decode è lo **stesso** di `fn_list_commessa_attivita`, un livello sopra sulla stessa colonna |

⚠️ **Il brief diceva «non aggiungono un `JOIN`» (Trappola 3), e queste due coppie
ne aggiungono due.** La ragione per cui è sostenibile è **strutturale, non una
misura**: sono `LEFT JOIN` su chiavi con indice `UNIQUE`, quindi PostgreSQL può
*provare* che non moltiplicano le righe e li **elimina dal piano** quando nessuna
delle loro colonne è selezionata (*left join removal*).

📌 **Fatto datato, e non è il motivo.** Il 2026-08-26, con contesto operatore, nei
piani di `vw_dash_competenza_gruppi` e della vista stessa interrogata senza le
colonne nuove **non compare nessuna scansione** di `fatturazione_lotti` né di
`catalogo.articoli`; compaiono solo interrogando la lista dei residui.
⚠️ La condizione che regge tutto è il `UNIQUE`: è verificato in `preCondition` e
ha un'asserzione sua (test 13).

### 6.3 ⭐ Una scelta di forma: lo stadio si calcola una volta sola

`motivo_non_fatturata` è definito **sopra** lo stadio («`NULL` fuori da
`EMESSA_NON_FATTURATA`»), e in SQL un alias di `SELECT` non è riferibile da
un'altra espressione della stessa `SELECT`. Ricopiare la condizione avrebbe messo
la definizione dello stadio in **due posti della stessa vista**, dove divergere
non produce nessun errore — cioè avrebbe ricreato in piccolo il difetto che
questo cantiere serve a chiudere.

Lo stadio vive ora in una `CROSS JOIN LATERAL` e serve entrambe le colonne.
⚠️ Verificato sul vivo: la colonna `stadio` resta **attnum 12**, tipo
`character varying`, valore identico. Nessun consumatore la vede cambiare.

### 6.4 Le prove PRE-APPLY — e i presidi visti **rossi prima**

> ℹ️ Questa sezione racconta la verifica fatta **prima** del migrate, quando
> ancora si poteva scegliere. Resta perché è il momento in cui i presidi sono
> stati messi alla prova; l'esito **come applicazione** sta nella §6.0.

⭐ *Un presidio che non si è mai visto fallire non è un presidio: è una speranza.*
I tre che contano sono stati mutati apposta:

| Mutazione applicata alla vista | Cosa è diventato rosso |
| --- | --- |
| `IS DISTINCT FROM` → `<>` | test **7** (il caso costruito) **e test 11** (il giro generale) |
| tolto il ramo `SENZA_ATTIVITA_FATTURABILE` | test **8** |
| mensile ri-aggregata a valle con `min(…)` | test **14** |
| changeSet 56 non applicato | test **18-bis** di `test-annulla-commessa-attivita-v1` |

**Esiti** (i pgTAP girano da *owner*, perché provati **prima** del migrate —
[[reference_pgtap_pre_apply_gira_solo_da_owner]]):

* `test-motivo-non-fatturata-v1` → **17/17**;
* **caccia ai consumatori, dal codice e non dalla direzione del cambio**: gli
  **11** file pgTAP che nominano le due viste e i **3** che nominano
  `fn_annulla_commessa_attivita` o i due codici, eseguiti *prima* e *dopo* i
  changeSet: **zero regressioni**. L'unico rosso-prima/verde-dopo è dei presidi
  nuovi;
* cancelli statici: letterali SQL, `runOnChange`, preambolo pgTAP,
  `gen_master_autogen --strict` (nessuna collisione su 54/55/56), test 5 del
  catalogo messaggi (**arità dei segnaposto invariata**) → **verdi**;
* `codici-errore-baseline.sh` → nessun allargamento. ⚠️ Resta il **rientrato**
  `E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO`, che è il rosso preesistente già
  dichiarato in `brief-db-lavoro-che-non-torna-indietro` §14.9 e **non è di
  questo cantiere**.

📌 **Fatto datato — e non decide niente.** Con contesto operatore, sul dato del
2026-08-26 la card contiene **5 righe su 5** classificate `RESIDUO`, e per tutte
e cinque `fn_check_*` non ha motivi, cioè il verbo le accetta. ⚠️ È un
controesempio mancato, non una prova: la prova sono le fixture **costruite**.

### 6.5 ⛔ Cosa NON è stato fatto, e perché

| Non fatto | Perché |
| --- | --- |
| il **bersaglio** («apri il documento») sul messaggio di D-6 | servirebbe un codice di `config.tipi_entita`, e la sorgente lì è **polimorfa**: dedurlo da `config.sorgenti.codice_interno` per simmetria di nomi sarebbe una scommessa, e `api.md` è esplicito — un bersaglio che punta a qualcosa che non si apre è **un pulsante in un vicolo cieco**. Se serve, è un cantiere suo con la mappa dichiarata |
| bonificare le 5 righe residue | ⛔ **sono il banco di prova**, come dice il §4 di questo brief |
| toccare `backend/` o `frontend/` | [[feedback_perimetro_db_no_modifiche_be]]: le richieste si scrivono qui |

---

## 7. ⛔ Le richieste a BE/FE — e la prima è un cancello CI

### 7.1 🔴 **BLOCCANTE** — le quattro chiavi i18n

Il catalogo delle liste dichiara la chiave, e
`scripts/check_i18n_keys.py` (CI) **confronta il CSV coi locales**: verificato,
prima del seed usciva `exit=0`, dopo esce **`exit=1`** con queste quattro:

```text
vendite.dashboard_competenza.col_competenza              →  "Competenza"
vendite.dashboard_competenza.col_articolo_descrizione    →  "Descrizione"
vendite.dashboard_competenza.col_lotto_provenienza       →  "Lotto di provenienza"
vendite.dashboard_competenza.col_motivo_non_fatturata    →  "Motivo"
```

In `frontend/src/locales/it.json` **e** `en.json` (la parità è presidiata).
⚠️ Non è un incidente: è lo stesso schema del `20260826-18`, dove il DB seminò
`col_registro`/`col_data_prevista` e il FE le aggiunse **lo stesso giorno**. Le
due metà vanno concordate insieme; finché non arrivano, quel cancello è rosso.

### 7.2 🔴 Il breakdown della mensile elenca **una voce per riga**

`vw_dash_competenza_mensile` ha una dimensione in più, quindi un bucket
`EMESSA_NON_FATTURATA` che contiene più situazioni **si spezza in una riga per
situazione**. I totali reggono (il pivot accumula), il breakdown no: senza
adeguamento il frontend mostrerebbe **`EMESSA_NON_FATTURATA` due volte**.
⚠️ È la stessa conseguenza dichiarata il 2026-08-20 per `tipo_movimento`, e va
fatta **nello stesso giro**.

### 7.3 Il vocabolario da mettere in whitelist — **quattro** valori

| Valore | Chiede un'azione? | Il codice che la mutazione solleva |
| --- | --- | --- |
| `IN_ATTESA_LOTTO` | ⛔ no | `E_ATTIVITA_GIA_DA_EMETTERE` |
| `GIRO_IN_CORSO` | ⛔ no | `E_ATTIVITA_IN_LAVORAZIONE` |
| ⭐ `RESIDUO` | ✅ **sì** | — (nessun motivo: il verbo accetta) |
| `SENZA_ATTIVITA_FATTURABILE` | ⛔ no | — (**la chiave è `NULL`**: il verbo non è proponibile) |

⚠️ **La card si spezza in due sul discriminante `RESIDUO` / non-`RESIDUO`**, non
su quattro numeri: gli altri tre sono «niente da fare», e distinguerli serve al
*drill-down*, non al contatore.

### 7.4 La lista dei residui

`ui.lista_definizione` id **49**, codice `vendite.dash_competenza_residui`,
`vista_sql = NULL` come le tre sorelle: **la query la compone il backend**
leggendo `vw_dash_competenza_attivita` con
`WHERE motivo_non_fatturata = 'RESIDUO'`.

⚠️ `attivita_fatturabile_id` **non è a catalogo** ed è deliberato: serve al verbo,
non all'occhio. Il backend lo proietta comunque — è la chiave che passa a
`vendite.fn_riporta_attivita_da_emettere`.

### 7.5 Il pulsante

Il verbo è collaudato lato DB dal cantiere precedente; **manca il gesto a
video**. Le 5 righe vere sono il banco di prova, e il recupero è il primo gesto
del frontend.

---

---

## 8. Segnalazioni BE del 2026-08-27 — esito

### 8.1 ✅ Mancava il preset di default della lista 49 — **è un buco mio**

Ho seminato `lista_definizione` e `lista_colonna` e **non** `lista_preset`.
Seminare una lista sono **tre** tabelle: le prime due si notano subito, la terza
no — e non produce nessun errore, perché il resolver **ripiega sul catalogo**.
La lista si vedeva, e partiva senza una configurazione dichiarata.

📌 Misurato il 2026-08-27: la **49 era l'unica** lista attiva senza preset di
default. Le altre 48 ce l'hanno.

**Seminato** — `ui/lista_preset.csv` id **49** (`id = lista_id`, come tutte e 48
le righe esistenti) + **11** righe in `ui/lista_preset_colonna.csv`. Entrambi i
loader sono `runOnChange`, quindi basta il CSV.

| Scelta | Perché |
| --- | --- |
| **preset = catalogo** (11 colonne su 11), non 10 | ⛔ Il «modello della 43» che il BE suggerisce è **drift, non convenzione**: la 41 e la 43 hanno il preset più corto del catalogo perché la colonna emittente fu aggiunta il 2026-08-18 e i preset non furono aggiornati. Le liste nate dopo (**44, 45, 47, 48**) hanno preset = catalogo. Ho seguito quelle |
| `emittente_fiscale` con **`visibile = f`**, non omessa | ⚠️ Omessa diventerebbe «colonna nuova» per il banner DEF-2: una scelta **dichiarata** si travestirebbe da dimenticanza, e la lista nascerebbe col banner già acceso |
| `pagina_dimensione = 25` | come le sorelle 42 e 43 |
| `ordinamento_default` = `competenza_mese asc` | ⭐ Le sorelle ordinano per **valore desc**, ma questa non è una lista di grandezze: è una **coda di recupero**. Un residuo che invecchia si avvicina al limite di emissione, quindi il più vecchio è il più a rischio — stessa logica del backlog (`anzianita_giorni desc`), non dei gruppi. ℹ️ `competenza_mese` è sia `codice` sia `campo_sorgente`, quindi risolve con entrambe le convenzioni (vedi §8.3) |

### 8.2 ⭐ E ci ho messo un presidio, perché il BE l'ha trovato **a mano**

`db/pgtap/ui/test-liste-preset-default-v1.sql` — 5 asserzioni. Il difetto è stato
scoperto contando le righe delle liste sorelle: è esattamente il genere di
controllo che va spostato dalla disciplina alla **struttura**.

| # | Cosa | Visto rosso? |
| --- | --- | --- |
| 1 | il **denominatore** non è zero | — (è il guard degli altri due: un `count(*) = 0` su una popolazione vuota passa *smettendo di verificare*) |
| 2 | ⛔ ogni lista attiva ha **esattamente un** preset di sistema di default | ✅ rosso senza il seed |
| 3 | ⛔ una colonna di preset appartiene alla **stessa lista** del preset | ✅ rosso infilando una colonna altrui |
| 4 | la 49 ha il preset dichiarato **per intero** (11 colonne, 10 accese, 1 fissata) | ✅ rosso senza il seed |
| 5 | la 49 non nasce col **banner DEF-2** acceso | ✅ rosso senza il seed |

⭐ Il **3** merita una riga: `ui.lista_preset_colonna` ha **due FK separate** —
una al preset, una alla colonna — e **niente** obbliga la colonna ad appartenere
alla stessa lista del preset. Il modello lo ammette, e l'effetto sarebbe una
lista che mostra la colonna di un'altra **senza nessun errore di vincolo**. Oggi
zero occorrenze: è il momento giusto per il cancello, perché *un presidio nato
verde costa niente e uno nato rosso non nasce*.

### 8.3 ⚠️ Una cosa trovata e **non** chiusa: due convenzioni per `ordinamento_default`

Cercando un quinto controllo ho misurato che `clienti_default` e
`emittenti_fiscali_default` ordinano per **`campo_sorgente`**
(`ragione_sociale_completa`), mentre tutti gli altri ordinano per **`codice`**.

⛔ **Non l'ho messo nel presidio, ed è deliberato**: decidere qui quale delle due
è «giusta» sarebbe stabilire una convenzione dentro un test invece che nel
cantiere che possiede le liste. È scritto anche in testa al file pgTAP.
➡️ Per chi possiede lo schema `ui`: o si sceglie una convenzione e si bonifica,
o si dichiara che valgono entrambe.

### 8.4 ✅ Il codice errore «rientrato» — concordo, e resta di chi lo possiede

`E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO`. **Nessuna azione da parte mia**, ed
è la stessa conclusione che era già scritta nella §6.4: stringere la baseline
qui nasconderebbe la storia di un altro lavoro dentro questo cantiere.
⚠️ Ma il BE ha ragione sul fatto che sia **urgente**: finché la baseline non è
stretta quel presidio è un cancello **mezzo spento**, e non è uno stato in cui
lasciarlo a lungo. È già registrato in `brief-db-lavoro-che-non-torna-indietro`
§14.9 come rosso preesistente.

### 8.5 ⛔ Stato: seminato, **non ancora applicato**

Il preset è nei CSV e **provato in rollback**; i tre mirror `runOnChange`
(`20260507-08`, `20260507-09` e il loro gemello) lo caricheranno **al prossimo
migrate**. Fino ad allora `ui.lista_preset` non ha la riga, e il presidio 8.2
è **rosso** — correttamente.

---

*Scritto il 2026-08-26 — Tid / Claude. Piano applicativo che ne dipende:
[brief-be-fe-lavoro-che-non-torna-indietro.md](brief-be-fe-lavoro-che-non-torna-indietro.md) §6.*
