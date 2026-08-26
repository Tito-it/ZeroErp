# Brief DB — i residui di competenza: la chiave che manca e la dimensione che manca

> **Destinatario:** team DB (`dev/db-tid`). BE e FE **attendono**
> ([[feedback_be_fe_attende_prerequisiti_db]]).
>
> **Origine.** 2026-08-26, scrivendo il piano applicativo di
> [brief-be-fe-lavoro-che-non-torna-indietro.md](brief-be-fe-lavoro-che-non-torna-indietro.md),
> cioè la metà BE/FE del cantiere che il team DB ha appena chiuso
> ([brief-db-lavoro-che-non-torna-indietro.md](brief-db-lavoro-che-non-torna-indietro.md)).
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

`ui.lista_definizione` (prossimo id libero, **44**) + le righe di
`ui.lista_colonna`, sul modello delle tre sorelle già a catalogo:

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

*Scritto il 2026-08-26 — Tid / Claude. Piano applicativo che ne dipende:
[brief-be-fe-lavoro-che-non-torna-indietro.md](brief-be-fe-lavoro-che-non-torna-indietro.md) §6.*
