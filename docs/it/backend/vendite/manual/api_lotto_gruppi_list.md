# API list_lotto_gruppi (Django)

## Scopo

Esporre via HTTP i **documenti che un lotto ha preso in carico**, con l'esito di
ciascuno — **compresi quelli che una fattura non sono mai diventati**.

## Contesto

`GET /api/v1/vendite/lotti/<id>/gruppi/` (+ `/export/?formato=csv|xlsx`).
Sola lettura sull'**unione di due fatti** — il perimetro
(`vendite.fatturazione_lotti_gruppi`) e l'esito
(`vendite.fatturazione_lotti_esiti`) — con l'identità di ogni documento risolta
da `vendite.vw_dash_competenza_gruppi` sul **mese del lotto**.

⭐ **Perché non basta `/fatture/`**, ed è tutta la ragione per cui questo
endpoint esiste. Quella lista si aggancia a `fattura_id`: descrive i documenti
che una fattura l'hanno prodotta. Un documento che cade **prima** — al pull
delle attività dalla commessa — non ha nessuna fattura a cui appendersi e
spariva dal racconto. Sul lotto `LTF-0009578` (2026-09-06) se ne vedevano
**due su tre**, e il terzo era nominato solo da una segnalazione, per giunta
con l'identificativo della **commessa**: sembrava una segnalazione sbagliata,
ed era l'unica cosa vera in giro.

⚠️ **Le due liste non sono in corrispondenza 1:1 nemmeno a giro riuscito**:
`fn_build_fattura_key` può raccogliere più gruppi nello stesso documento. Sono
due domande diverse, non due viste della stessa — per questo è una scheda in più
e non una colonna.

Brief di riferimento: `docs/it/dev/work-done/brief-db-esito-gruppo-lotto.md`.

## Input

| Parametro | Tipo | Note |
|---|---|---|
| `lotto_id` | path | obbligatorio |
| `stato_esecuzione` | query | `PENDING` \| `RUNNING` \| `COMPLETED` \| `ERRORE` \| `ESCLUSO` (`STATI_ESECUZIONE_DOCUMENTO`: il vocabolario comune più `ESCLUSO`, documento tolto dal giro). Fuori vocabolario → `400 E_VENDITE_VALIDATION`. Assente = tutti, **compresi i mai tentati** (esito `NULL`) |
| `order_by` | query | whitelist `LOTTO_GRUPPI_SORT_COLUMNS`: `riferimento`, `tipo_gruppo`, `stato_esecuzione`, `errore_codice`, `errore_quando`, `commessa_codice` |
| `order_dir` | query | `asc` \| `desc`. ⚠️ Da mandare **solo insieme** a `order_by`: da solo annullerebbe il default |
| `limit` / `offset` | query | `limit` default 25, max 200; `offset` default 0. Non interi, `limit` fuori da 1..200 o `offset` negativo → `400 E_VALIDATION_INPUT`. ⛔ `page`/`page_size` sono un `400 E_VALIDATION_INPUT` dal 2026-10-21 (prima erano il contratto di questa lista). L'export salta la paginazione |

⭐ **L'ordine di default non è alfabetico**: `(stato_esecuzione = 'ERRORE') DESC`,
poi `riferimento`. È la domanda con cui questa scheda si apre — *«quale documento
non è passato?»* — e l'ordine alfabetico dello stato metterebbe `ERRORE` **dopo**
`COMPLETED`. Il tiebreak è `gruppo_key`, perché `riferimento` può non risolversi.

## Output

Envelope lista standard (`count`, `page`, `page_size`, `total_pages`,
`results`), e **nient'altro** — vedi «L'unione di due fatti» più sotto.

| Campo di riga | Cosa |
|---|---|
| `gruppo_key` | la chiave di dominio, `<sorgente>:<uid>` oppure `MAN:<commessa>`. È anche il **ripiego** a video quando l'identità non si risolve più, e la **chiave di riga**: ⛔ non c'è un `id`, perché la riga non è una riga di tabella ma l'unione di due fatti |
| `stato_esecuzione` | vocabolario chiuso: quello delle fatture del lotto (D-2) più `ESCLUSO`, che una fattura non può avere. ⚠️ `null` = «nessuno l'ha detto», **non** «è andata bene» |
| `errore_codice` · `errore_messaggio` · `errore_quando` | il perché, dalla riga di **questo** lotto |
| `riferimento` · `tipo_gruppo` · `area_documento` · `documento_id` | l'identità del documento, risolta dalla vista di competenza |
| `commessa_id` · `commessa_codice` · `commesse_n` | la **commessa da correggere** — vedi sotto |

Errori: `400 E_VENDITE_VALIDATION` (filtro, ordinamento o paginazione fuori
limiti; un intero non leggibile → `E_VALIDATION_INPUT`); `404
E_LOTTO_NON_TROVATO` su lotto inesistente o fuori perimetro — vale anche per
l'export. ⚠️ 2026-10-20: prima rispondeva `200` con zero righe.

## Regole

### L'identità del gruppo non si ricostruisce nel backend

Una `gruppo_key` è `<sorgente>:<uid>`: per scriverla a video serve la
derivazione che `vendite.fn_build_gruppo_fatturabile_key` e
`vw_dash_competenza_gruppi` **già fanno**. Si legge da lì invece di spezzare la
chiave in Python — che sarebbe la seconda sede della stessa regola, e il giorno
in cui la chiave cambia forma le due dissentirebbero in silenzio.

⚠️ Il legame è **(gruppo, mese del lotto)**, lo stesso della vista. La vista ha
grana `(competenza, gruppo_key, …, stadio)`: le colonne di identità si
collassano con `min()` in una riga per gruppo — è un collasso di valori
identici, non una scelta fra alternative, perché discendono dalla chiave.
Senza il collasso lo **stesso** documento comparirebbe due volte quando parte
del suo lavoro è già fatturato e parte no.

### L'esito si legge da `fatturazione_lotti_esiti`, non dalle `ultimo_*` della vista

Quelle dicono com'è andato l'**ultimo** tentativo su quel documento, che può
essere di un **altro** lotto. Qui la domanda è «come è andata in *questo* lotto», e la
risposta è la riga di questo lotto.

### La commessa esce solo quando ce n'è una

La chiave di un gruppo-documento **non contiene la commessa**, quindi due
commesse sullo stesso documento sono ammesse per costruzione. `commesse_n` dice
quante sono; `commessa_id`/`commessa_codice` restano `null` quando sono più
d'una — offrirne una a caso sarebbe una scommessa travestita da regola. È la
stessa forma con cui la lista dei gruppi in competenza tratta già il sezionale
multiplo (`registri_n`).

⭐ **È il campo che decide se il lavoro è servito**: nel caso reale la causa non
era un difetto del programma ma un dato mancante sulla commessa 34137. Se il
rosso non porta lì, l'operatore sa di avere un problema e non sa che farci.

### L'unione di due fatti, e perché nessuno dei due basta

| | risponde a | esiste su |
| --- | --- | --- |
| `fatturazione_lotti_gruppi` | *«quali documenti devo lavorare»* — il **perimetro** | i soli giri **mirati** |
| `fatturazione_lotti_esiti` | *«com'è andato ciascuno»* — l'**esito** | **entrambi** i tipi di giro |

⛔ Il solo perimetro lascia muto ogni giro di massa — il difetto chiuso dal
database il 2026-09-07. I soli esiti perdono i documenti di un lotto mirato che
non è ancora arrivato al passo del pull: **dichiarati e non ancora tentati**.

⭐ **`perimetro_dichiarato` non esiste più**, ed è il segno che il problema è
stato risolto invece che spostato. Serviva a distinguere «non ha lavorato
niente» da «non dichiara un perimetro», perché la lista leggeva il solo
perimetro. Con l'unione, zero righe ha **un significato solo**: di questo lotto
non risulta nessun documento — non ha ancora lavorato, oppure è anteriore al
tracciamento. ⚠️ Tolto e non lasciato «per compatibilità»: un campo che non
discrimina più niente è peggio di un campo assente, perché chi lo legge crede
che discrimini.

## Dipendenze DB

* `vendite.fatturazione_lotti_gruppi` — il perimetro
* `vendite.fatturazione_lotti_esiti` — l'esito (changeSet `20260907-12`)
* `vendite.fatturazione_lotti` — **il cancello di scope**
* `vendite.vw_dash_competenza_gruppi` — l'identità del gruppo
* `vendite.fn_segna_esito_gruppo_lotto` — chi **scrive** l'esito (dal
  `pipeline_step_executor`, non da qui)

🔒 **Il cancello è la testata**: né `fatturazione_lotti_gruppi` né
`fatturazione_lotti_esiti` hanno **RLS**, `fatturazione_lotti` sì. Leggere la figlia da sola sarebbe fail-open, e vale
anche per il **conteggio** — un totale senza cancello direbbe «3 documenti»
mostrandone zero. Allo scope RLS si affianca il filtro emittente esplicito
(`_add_scope_emittente`), come su `/fatture/`. La testata si legge **prima**
dell'elenco (`lotto_visibile`): lotto non visibile → `404`, non elenco vuoto.

## Note di migrazione

- 2026-10-21: la finestra passa da `page`/`page_size` a `limit`/`offset`
  (`pagina_da_query`); `page`/`page_size` in query diventano un 400. Envelope
  di risposta invariato.

⚠️ **L'esito nasce assente.** Lo scrive `vendite.fn_segna_esito_gruppo_lotto`,
che il backend chiama dal `_handle_pull_attivita_da_commessa_task`: finché non
passa un giro di fatturazione la riga di esito non esiste, e la lista mostra il
solo perimetro con `stato_esecuzione = null`. Non è un difetto — è che il primo
giro deve ancora avvenire.

✅ **I due limiti dichiarati il 2026-09-06 sono chiusi**, e da parti diverse.

* *«la marcatura non sopravvive nel ramo tutte-fallite»*: quel ramo **non
  solleva più** (P-5, decisione di Tid). Non serviva una scrittura durevole —
  serviva togliere ciò che annullava la scrittura. Fermarsi e strappare gli
  appunti erano due cose che faceva lo stesso gesto: ora si ferma **tenendo**, e
  a fermare la catena ci pensa il blocco per segnalazioni critiche al giro
  successivo.
* *«un lotto di massa non ha dove essere marcato»*: la riga adesso si **crea**
  in `fatturazione_lotti_esiti`, che il perimetro non lo richiede. La stessa
  identica chiamata del backend ha cominciato a funzionare.

⭐ Il presidio è `apps/vendite/tests/db/test_pull_tutte_fallite_scrittura_reale.py`
(opt-in DB, acceso in CI): esercita il ramo con il repository **vero** e legge
la riga scritta — non che la chiamata sia avvenuta. È la metà che mancava ai
test del 06-09, ed è stato verificato che si accende rimettendo il `raise`.
