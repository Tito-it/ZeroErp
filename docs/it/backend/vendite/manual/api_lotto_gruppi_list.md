# API list_lotto_gruppi (Django)

## Scopo

Esporre via HTTP i **documenti che un lotto ha preso in carico**, con l'esito di
ciascuno — **compresi quelli che una fattura non sono mai diventati**.

## Contesto

`GET /api/v1/vendite/lotti/<id>/gruppi/` (+ `/export/?formato=csv|xlsx`).
Sola lettura su `vendite.fatturazione_lotti_gruppi`, con l'identità di ogni
gruppo risolta da `vendite.vw_dash_competenza_gruppi` sul **mese del lotto**.

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

Brief di riferimento: `docs/it/dev/work-in-progress/brief-db-esito-gruppo-lotto.md`.

## Input

| Parametro | Tipo | Note |
|---|---|---|
| `lotto_id` | path | obbligatorio |
| `stato_esecuzione` | query | `PENDING` \| `RUNNING` \| `COMPLETED` \| `ERRORE`. Assente = tutti, **compresi i mai tentati** (esito `NULL`) |
| `order_by` | query | whitelist `LOTTO_GRUPPI_SORT_COLUMNS`: `riferimento`, `tipo_gruppo`, `stato_esecuzione`, `errore_codice`, `errore_quando`, `commessa_codice` |
| `order_dir` | query | `asc` \| `desc`. ⚠️ Da mandare **solo insieme** a `order_by`: da solo annullerebbe il default |
| `page` / `page_size` | query | 1 / 50 (max 200). L'export salta la paginazione |

⭐ **L'ordine di default non è alfabetico**: `(stato_esecuzione = 'ERRORE') DESC`,
poi `riferimento`. È la domanda con cui questa scheda si apre — *«quale documento
non è passato?»* — e l'ordine alfabetico dello stato metterebbe `ERRORE` **dopo**
`COMPLETED`. Il tiebreak è `gruppo_key`, perché `riferimento` può non risolversi.

## Output

Envelope lista standard (`count`, `page`, `page_size`, `total_pages`, `results`)
**più `perimetro_dichiarato`**.

| Campo di riga | Cosa |
|---|---|
| `gruppo_key` | la chiave di dominio, `<sorgente>:<uid>` oppure `MAN:<commessa>`. È anche il **ripiego** a video quando l'identità non si risolve più |
| `stato_esecuzione` | vocabolario chiuso, **identico** a quello delle fatture del lotto (D-2). ⚠️ `null` = «nessuno l'ha detto», **non** «è andata bene» |
| `errore_codice` · `errore_messaggio` · `errore_quando` | il perché, dalla riga di **questo** lotto |
| `riferimento` · `tipo_gruppo` · `area_documento` · `documento_id` | l'identità del documento, risolta dalla vista di competenza |
| `commessa_id` · `commessa_codice` · `commesse_n` | la **commessa da correggere** — vedi sotto |
| `perimetro_dichiarato` (payload, non riga) | vedi «Zero ha due significati» |

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

### L'esito si legge dalla tabella, non dalle colonne `ultimo_*` della vista

Quelle dicono com'è andato l'**ultimo** tentativo su quel gruppo, che può essere
di un **altro** lotto. Qui la domanda è «come è andata in *questo* lotto», e la
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

### Zero ha due significati, e `perimetro_dichiarato` li separa

Un giro **di massa** non scrive nessun gruppo: nessuna riga = **nessuna
restrizione**, che è la convenzione portante di `fatturazione_lotti_gruppi`
(garanzia G1). Quel lotto qui non ha niente da mostrare — e non perché non abbia
lavorato. Senza il flag, «non ha lavorato niente» e «non dichiara un perimetro»
si leggerebbero uguali, e il frontend affermerebbe la cosa sbagliata proprio sui
lotti più numerosi.

⛔ Il flag **non si deriva dalle righe della pagina**: sarebbe un'eco. Si chiede
al perimetro intero (`lotto_ha_perimetro_gruppi`, un `EXISTS`) e solo quando la
pagina è vuota.

## Dipendenze DB

* `vendite.fatturazione_lotti_gruppi` (colonne esito dal changeSet `20260906-10`)
* `vendite.fatturazione_lotti` — **il cancello di scope**
* `vendite.vw_dash_competenza_gruppi` — l'identità del gruppo
* `vendite.fn_segna_esito_gruppo_lotto` — chi **scrive** l'esito (dal
  `pipeline_step_executor`, non da qui)

🔒 **Il cancello è la testata**: `fatturazione_lotti_gruppi` **non ha RLS**,
`fatturazione_lotti` sì. Leggere la figlia da sola sarebbe fail-open, e vale
anche per il **conteggio** — un totale senza cancello direbbe «3 documenti»
mostrandone zero. Allo scope RLS si affianca il filtro emittente esplicito
(`_add_scope_emittente`), come su `/fatture/`.

## Note di migrazione

⚠️ **Le colonne dell'esito nascono vuote.** Le scrive
`vendite.fn_segna_esito_gruppo_lotto`, che il backend chiama dal
`_handle_pull_attivita_da_commessa_task`: finché non passa un giro di
fatturazione, ogni riga risponde `stato_esecuzione = null`. Non è un difetto —
è che il primo giro deve ancora avvenire.

🔴 **Limite dichiarato (brief §11).** Nel ramo «tutte le commesse fallite» la
marcatura **non sopravvive**: `run_pipeline` tiene un `transaction.atomic()`
attorno all'intero ciclo degli step, e il `raise` di
`E_PULL_COMMESSA_ALL_FAILED` fa rollback portandosi via i segni. I due rami che
non sollevano — tutto riuscito e **parziale** — funzionano, e il parziale è il
caso per cui il cantiere è nato. Serve una scrittura che sopravviva al rollback,
ed è del team DB.

🔴 **E un lotto di massa non ha dove essere marcato.** Un giro schedulato non
scrive righe in `fatturazione_lotti_gruppi`, quindi
`fn_segna_esito_gruppo_lotto` non trova nessun gruppo e torna `0` (con il
warning previsto). L'esito per giro esiste oggi **solo** sui lotti nati da
emissione mirata.
