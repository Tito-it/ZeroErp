# Brief DB — magazzino, Lotto 2-bis: ciò che il BE/FE del motore chiede al DB

> **Destinatario:** team DB (`dev/db-tid`). **Chi scrive:** BE/FE, 2026-09-18.
> **Origine:** [piano-be-fe-magazzino-lotto-2-motore.md](piano-be-fe-magazzino-lotto-2-motore.md)
> §7 — scrivendo il piano del drawer e delle righe sono emerse **tre** cose che
> il BE non può fare da sé senza riscrivere una regola del DB, più **due**
> difese opzionali. Nessuna ridiscute il Lotto 2: ogni riga cita la decisione
> da cui discende (D-L2-* del [brief del motore](brief-db-magazzino-lotto-2-motore.md)).
> **Stato:** ✅ **LE TRE BLOCCANTI SONO FATTE, APPLICATE E VERDI — 2026-09-22.**
> Sei changeSet `EXECUTED` su dbdev (i cinque del disegno alle 19:06, la rev
> della vista del presidio C1 in serata), i quattro seed a catalogo, i pgTAP
> rilanciati da Tid: verdi.
> R-1 (la capability, in quattro changeSet), R-2 (il codice del `UNIQUE`) e R-3
> (l'azione di processo) sono nel repo: cinque changeSet `20260922-18 … -22`,
> tre righe di catalogo nei CSV, un pgTAP nuovo da 14 asserzioni, la doc. Ogni
> passo provato con l'**SQL estratto** in transazione annullata su dbdev — i
> quindici pgTAP del Lotto 2 toccati restano verdi, i due presidi trasversali
> pure. ⚠️ **L'apply ha fatto emergere una ricaduta**, ed è una cosa buona: il
> presidio C1 «stati mai scritti» ha smesso di essere verde per coincidenza — e
> si è scoperto anche **lento**: rimedio nel CSV delle dichiarazioni più due
> interventi di costo (§Consegna). ✅ **Tutto applicato e verde la sera del
> 22-09** (sei changeSet `-18 … -23`, i quattro seed, pgTAP rilanciati da Tid).
> ✅ **E le quattro «opzionali» R-4 … R-7 sono state decise da Tid la stessa
> sera**, una alla volta (§Il secondo giro): nessuna è un changeSet — tre sono
> righe nei CSV di catalogo, una è lavoro del backend. ✅ **Anche il secondo
> giro è applicato**: migrate delle 00:05 del 23-09, mirror `20260614-08` e
> `20260110-15` `RERAN`, i tre codici (msg 1114-1116) e le due righe di lock a
> catalogo — letti sul catalogo vivo, non dedotti dai file.
> ✅ **E il lucchetto di R-4 è ARMATO** dal 23-09: i due trigger
> `trg_inventari_a10_lock_columns_upd` e `trg_rettifiche_a10_lock_columns_upd`
> esistono e portano `magazzino_id → E_MAG_DOCUMENTO_MAGAZZINO_IMMUTABILE`
> (letti su `pg_trigger`). ⇒ Il **test 17 del guard non fa più `skip`**: adesso
> misura davvero. A generarli è stata l'automazione chiamata da
> `90_end/20260923-02`, il changeSet di un cantiere nato da una riga di questo
> brief — [brief-db-codici-ritirati-negli-argomenti-dei-trigger.md](brief-db-codici-ritirati-negli-argomenti-dei-trigger.md).
> ✅ **pgTAP rilanciati da Tid, nessuna regressione; commit fatto** (`7d67d6d9d`).
> ⇒ **Sul DB non resta niente di questo brief.**
>
> # ✅ CHIUSO il 2026-09-23 — anche la metà BE/FE
>
> **Consegnato**: il drawer monta la barra dalla capability (le tre transizioni
> e «Registra», spento col motivo), il `23505` del duplicato di posizione esce
> come codice registrato col campo da accendere, il gate `registra_magazzino` è
> dichiarato sui due `registra/`, il codice di validazione del dominio ha preso
> il posto del generico, la riga di un altro documento ha un 404 suo, e il
> picker di riga propone i soli articoli gestiti a magazzino. Dettaglio e
> presidi in coda, §«A BE/FE, quando il DB è applicato».
> ⏳ **Resta il collaudo a video** (passo 7 del piano), che è di Tid: il
> frontend non è stato provato in-app. Il copione è
> [collaudo-in-app-magazzino-inventario-e-rettifica.md](../work-in-progress/collaudo-in-app-magazzino-inventario-e-rettifica.md).
> 📦 **Archiviato in `work-done/` il 2026-09-25**: il brief non ha più niente
> da consegnare; il collaudo vive nel suo documento.
> ✅ Le cinque domande del piano (Q-1 … Q-5) erano decise da Tid il 2026-09-18:
> lato BE/FE non restava niente in sospeso. Bloccavano parti **diverse** del
> piano: R-1 il drawer (Pezzo 3), R-2 le righe (Pezzo 2), R-3 il gate di
> «Registra» — ⛔ e il passo 7 del piano era fermo lì: senza queste funzioni il
> drawer non ha la barra delle azioni, e il BE non finge le capability.
>
> **In una riga.** Il Lotto 2 ha messo la matrice degli stati **dentro il
> guard** e nessuna funzione la espone: il drawer, che deve disegnare i pulsanti
> come in tutti gli altri domini (`fn_available_actions_*`), non ha da dove
> leggerla — e il BE non la copia. Poi un `UNIQUE` senza codice, un'azione di
> processo per il verbo irreversibile, e due lucchetti.

---

## R-1 ✅ FATTA (22-09) — la capability dei documenti interni (D-L2-h; linee-guida-sql §12)

**Il fatto.** `trgfn_documento_interno_guard_transizione` porta la matrice in
un `CASE v_old …` nel corpo. Il frontend monta le azioni di stato **solo** da
`available_actions` (`mapAvailableActionsToDrawerActions`, frontend-standards
§Azioni Drawer: *«niente loop manuale»*, *«un `v-if` su `stato_codice` nel
drawer sarebbe la stessa regola scritta due volte»*), e il backend **trasporta,
non deduce** (api.md §Capability). Senza una funzione, le uscite sono due e
sono entrambe una seconda sede della matrice: un `dict` in Python o un
`v-if` in Vue. Il brief del motore lo aveva previsto: *«se un giorno servirà,
la matrice esce dal guard: cambia dove sta, non chi la fa rispettare»*. Il
giorno è il primo drawer.

**Che cosa si chiede.**

1. **La matrice in una sede sola**, letta dal guard e dalla capability:
   `magazzino.fn_documento_interno_transizioni(p_stato_da text) RETURNS text[]`
   (`IMMUTABLE`, `SECURITY INVOKER`) — `DRAFT → {CONFIRM, CANCEL}`, `CONFIRM →
   {POSTED, CANCEL, DRAFT}`, `POSTED`/`CANCEL → {}`. Il guard fa `v_new = ANY(…)`
   al posto del `CASE`; `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA` e la porta
   `POSTED` restano dove sono. ⚠️ Non una tabella seed: gli stati non hanno
   attributi (D-L2-h, «matrice nel guard, non tabella»); una funzione è la sede
   più piccola che due lettori possono condividere.
2. **Due capability con lo stampo di `fn_available_actions_ordine`**, in
   `script`, `STABLE SECURITY INVOKER` (sotto RLS: fuori perimetro `{}`, il 404
   lo dà il BE sulla testata): `script.fn_available_actions_inventario(p_id)`
   e `script.fn_available_actions_rettifica(p_id)`. ⭐ Se il corpo è uno
   (`_documento_interno(p_tabella, p_col_stato, p_id)`) le due sono involucri:
   scelta vostra. Il blob:

   | Chiave | Che cosa |
   | --- | --- |
   | `stato_codice` | lo stato |
   | `available_actions[]` | una voce per **transizione richiedibile** dalla matrice (mai `POSTED`, che si chiede con `registra`): `key` (`conferma` / `annulla` / `riapri`), `target_state`, `label_key`, `icon`, `severity`, `requires_confirm` (`true` su `CANCEL`), `enabled`, `reason`, `reason_key`, `manuale = true` |
   | `can_edit_testata`, `can_edit_righe` | `stato = 'DRAFT'` — **lo stesso predicato** del guard delle righe (§12.2: «il predicato è lo STESSO del guard») |
   | `can_delete` | `stato = 'DRAFT'` (C3) |
   | `can_registra`, `can_registra_reason`, `can_registra_reason_key` | la terna di **`registra`** (famiglia 1 di api.md §Capability, come `can_push_commessa`): `enabled` sse `stato = 'CONFIRM'` **e** almeno una riga **e** (solo inventario) nessuna riga `NON_POSTABILE` nel piano — sono le tre condizioni con cui `fn_posta_*` rifiuta (`E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA`, `E_MAG_DOCUMENTO_SENZA_RIGHE`, il primo motivo di `fn_check_riga_magazzino`). Precedenza: stato > righe > postabilità. ⭐ Se preferite che `fn_posta_*` chiami una `script.fn_check_documento_interno_registrabile` e la capability la stessa (§12.5.2, «la madre chiama la check»), è la forma di casa — decidete voi |
   | `stato_info_key` | `POSTED` → `magazzino.documenti_interni.stato_info.posted` («Registrato: i movimenti sono sul registro. Per correggere, una rettifica»); `CANCEL` → `….cancel`; `NULL` altrove (il campo è sempre presente, brief vie d'uscita R3) |

3. **Le chiavi i18n**, da dichiarare qui perché il FE le semini **nello stesso
   giro** (`check_i18n_keys.py` controllo 4 le cerca nella doc auto-gen):
   `label_key` `magazzino.documenti_interni.azione.{conferma, annulla, riapri}`;
   `reason_key` `magazzino.documenti_interni.registra_reason.{non_confermato,
   senza_righe, righe_non_postabili}`; le due `stato_info_key` sopra.

**pgTAP** (stampo dei test delle otto capability): la matrice della funzione
coincide con ciò che il guard ammette e rifiuta (**costruendo** le sei
transizioni, non leggendo dati); `can_registra` spento con la `reason` giusta
nei tre casi e acceso sul caso buono; fuori perimetro `{}`.

---

## R-2 ✅ FATTA (22-09) — `E_MAG_INVENTARIO_RIGA_POSIZIONE_DUPLICATA` (C14)

`uq_mag_inventari_righe_posizione` (UNIQUE NULLS NOT DISTINCT su
`(inventario, articolo, ubicazione, lotto, asset)`) rifiuta con un `23505` —
e un `23505` il BE lo traduce con `map_integrity_error` in un codice **che
deve essere a catalogo** (guardrail dei codici; oggi nessun `E_MAG_*` lo
nomina). Chi rimedia è chi compila la riga ⇒ `DATO_ERRATO`, `campo =
articolo_id`. Messaggio proposto: *«L'articolo %s è già contato in questa
posizione dell'inventario (%s).»* (codice articolo, posizione: ubicazione ·
lotto · seriale, «—» dove vuota); soluzione: *«Modifica la riga esistente
invece di aggiungerne una seconda.»* ⚠️ Lo solleva **solo il BE** (nessuna
funzione lo nomina): il rubinetto B-7 non lo vede, il registro del terzo lato
lo trova a catalogo con la sua classe. Le rettifiche non lo prendono (C14: due
delta dati non sono due letture).

---

## R-3 ✅ FATTA (22-09) — l'azione di processo `registra_magazzino`

Una riga in `config/azioni_processo.csv`: area **6** (`magazzino`),
`permission_codename = registra_magazzino`, *«Registra inventario o rettifica
di magazzino (crea i movimenti: irreversibile)»*, `pericolosa = t`, `attivo = t`
— lo stampo è `registra_distinta` (id 32). Un'azione per la famiglia, non due:
il verbo è lo stesso e la matrice è la stessa. Il BE la dichiara su
`POST inventari/<id>/registra/` e `rettifiche/<id>/registra/`
(`post_permission`), fail-closed finché un profilo non la porta.

---

## R-4 ✅ DECISA (22-09) — `magazzino_id` si sceglie alla nascita

> ✅ **Tid, 2026-09-22: si mette il lucchetto su `magazzino_id`, in ogni stato.**
> Il documento appartiene a quel magazzino da quando nasce. ⛔ **La `data` NO**:
> resta la Q-2 del piano, cioè com'è — il DB non congela la testata, e il BE non
> aggiunge una regola che il DB non ha. Da fare: `script.trgfn_lock_columns` su
> `inventari` e `rettifiche` (stampo `trg_ubicazioni_a10_lock_columns_upd`) e il
> pgTAP del caso costruito.
> ✅ **Fatto e a catalogo dal 23-09**: due righe in `automation_lock_columns`,
> il codice `E_MAG_DOCUMENTO_MAGAZZINO_IMMUTABILE` (msg 1114), il pgTAP a 17
> asserzioni, e la regola scritta in `manual/inventari.md`, `manual/rettifiche.md`
> e `_dominio-magazzino.md`. 🔴 **Manca solo l'automazione che genera i due
> trigger**: finché non gira, la regola è dichiarata e non in vigore.
> ⚠️ Letto sul catalogo vivo il 22-09, ed è il motivo per cui serve: sulla
> testata oggi sorvegliano solo `sorgente_*` (guard tipizzato), lo stato
> (matrice + porta) e l'esistenza del magazzino attivo — nessuno impedisce di
> **spostare** il documento su un altro magazzino, nemmeno dopo la
> registrazione, e le righe resterebbero a nominare ubicazioni di un magazzino
> che non è più il suo.

Il documento è ancorato a **un** magazzino (RLS, ubicazioni delle righe,
`qta_sistema` del piano). Il BE lo esclude dal `PATCH`; la difesa a DB è
`script.trgfn_lock_columns('magazzino_id', …)` su `inventari` e `rettifiche`
(stampo `trg_ubicazioni_a10_lock_columns_upd`). Senza, un `UPDATE` diretto
sposta un conteggio su un altro magazzino con le ubicazioni di quello vecchio
— e la primitiva se ne accorgerebbe **solo** al posting
(`E_MAG_UBICAZIONE_DI_ALTRO_MAGAZZINO`). Un lucchetto piccolo che dice la
regola dove sta.

⚠️ **Nota, dalla Q-2 del piano (decisa il 18-09):** il guard di famiglia
copre righe e stato, **non** `data`/`descrizione` della testata, e il BE **non
aggiunge** una regola che il DB non ha (a video il form è readonly fuori da
`DRAFT`; via API un `PATCH` di `data` su un `POSTED` passa). `data` decide
`data_mov` al posting: dopo, una `data` cambiata e i `data_mov` a registro
dicono due cose. Se per voi è un difetto del modello, il congelamento della
testata fuori da `DRAFT`/`CONFIRM` è un lucchetto vostro, nello stesso giro di
R-4; se no, resta com'è.

## R-5 ✅ DECISA (22-09) — `fn_lookup_articoli`: filtro `p_gestito_a_magazzino`

> ✅ **Tid, 2026-09-22: si aggiunge il filtro.** Il ragionamento che l'ha
> decisa: un errore che non si può proprio fare è meglio di un errore spiegato
> dopo.
>
> 🔴 **Ma la premessa di questa richiesta è falsa, e il lavoro non è del DB.**
> `fn_lookup_articoli` **non esiste**: cercata in `pg_proc` il 22-09, zero
> funzioni con quel nome. Il picker degli articoli è SQL costruito in Python —
> `catalogo/db/catalogo_repository.py::lookup_articoli` — che legge
> `catalogo.vw_articoli_dettaglio` e monta le condizioni `WHERE` dai parametri
> ricevuti. ⭐ E quella vista **espone già `gestito_a_magazzino`**: il repository
> lo seleziona persino (ce l'ha messo il Lotto 2, per lotto e seriale nel form
> di riga). ⇒ Il filtro è **una condizione in più nel BE** e un parametro che il
> FE passa dal picker del magazzino: **zero changeSet**. La richiesta si sposta
> in §A BE/FE.

Il picker della riga di inventario propone oggi **tutti** gli articoli; uno non
gestito diventa `NON_POSTABILE` al piano. Un filtro `boolean DEFAULT NULL`
(`NULL` = nessun filtro, come `is_solo_componente`) lascia al FE la scelta di
proporre solo i gestiti. Non blocca niente: senza, l'anteprima dei motivi nel
form (`fn_check_riga_magazzino`) lo dice comunque.

---

## R-6 ✅ DECISA (22-09) — `E_MAGAZZINO_VALIDATION`

> ✅ **Tid, 2026-09-22: si conia.** Gemello di `E_PAGAMENTI_VALIDATION`: il
> magazzino dice il proprio nome quando rifiuta un payload, e nel registro degli
> errori i suoi si contano. Una riga a catalogo + la frase; al BE una riga
> (`magazzino_service.E_VALIDAZIONE`).
> ⚠️ La frase è **senza segnaposto**, come quella dei diciotto fratelli
> `*_VALIDATION`: nessuna funzione PL/pgSQL solleva questo codice, quindi un
> `%s` non lo riempirebbe nessuno (§Il secondo giro, rilettura del 22-09).

Il codice di validazione del payload del dominio (`DATO_ERRATO`), gemello di
`E_PAGAMENTI_VALIDATION`: oggi il BE usa il generico `E_VALIDATION_INPUT`, ed è
**una riga** da cambiare (`magazzino_service.E_VALIDAZIONE`). Il BE non conia.

## R-7 ✅ DECISA (22-09) — `E_MAG_DOCUMENTO_RIGA_NON_TROVATA`

> ✅ **Tid, 2026-09-22: si conia.** La risposta a chi guarda non cambia (404,
> nessuna informazione in più: resta la convenzione no-leak), ma il codice smette
> di dire «documento» mentre la frase dice «riga» — e quella frase torna al
> catalogo, invece di essere scritta nel backend.

La coppia (documento, riga) è la risorsa dell'URL
(`inventari/<id>/righe/<rid>/`): una riga di un altro documento «non c'è», e
oggi risponde `E_MAG_DOCUMENTO_NON_TROVATO` con la frase del BE («Riga non
trovata nel documento»). Un codice suo (`NON_TROVATO`) dice *quale* delle due
manca; è un candidato allo split, non un difetto.

---

## Ai team, per chiudere

- 🔵 DB: R-1 (con le chiavi i18n dichiarate), R-2, R-3; R-4/R-5/R-6/R-7 a discrezione.
  In `_dominio-magazzino.md` §«Che cosa manca» la riga di `requires_lotto`
  esce quando il Pezzo 0 del piano è mergiato.
- 🔵 BE/FE: le chiavi di R-1 nei locales **prima** che la doc auto-gen delle
  capability entri nel repo; `genera_error_policies` + ripiego per R-2.

---

## Consegna del 2026-09-22 — che cosa c'è, che cosa resta

> Scritto dal team DB rispondendo alla contestazione del BE sul **passo 7**: le
> tre righe che chiedeva — le due `fn_available_actions_*`, il codice del
> `UNIQUE`, l'azione `registra_magazzino` — erano **zero** sul database, e
> aveva ragione: non erano del Lotto 2 (chiuso e consegnato), erano di questo
> brief, che dal 18-09 stava in `work-in-progress` con stato «da decidere».

### I changeSet — cinque, `runOnChange: false`, `failOnError: true`, con rollback

| # | Fase | Che cosa |
| --- | --- | --- |
| `20260922-18` | `20_code/magazzino` | `fn_documento_interno_transizioni(p_stato_da)`: la **matrice** esce dal guard e diventa una sede con due lettori. `IMMUTABLE`, plpgsql (non `LANGUAGE sql`: resterebbe fuori dal presidio dei riferimenti morti) |
| `-19` | `20_code/magazzino` | rev di `trgfn_documento_interno_guard_transizione`: il `CASE` diventa `v_new = ANY (…)`. ⛔ Nient'altro cambia — DELETE solo in bozza, porta `POSTED`, codici e VARIADIC identici |
| `-20` | `20_code/script` | `fn_check_documento_interno_registrabile(p_famiglia, p_documento_id)`: i **tre** motivi che impediscono di registrare, nell'ordine che è il contratto |
| `-21` | `20_code/magazzino` | rev di `fn_posta_inventario` e `fn_posta_rettifica`: chiamano la check invece di ripeterla. Il `FOR UPDATE` resta primo (è il lock, e la check è `STABLE`) |
| `-22` | `20_code/script` | `fn_available_actions_documento_interno` + i due involucri `_inventario` e `_rettifica` |

**In place** (non changeSet): `80_data/sql/config/codici_errore.csv` +
`messaggi_errore.csv` (R-2, messaggio id 1113) e `azioni_processo.csv` (R-3,
id 36, area 6 `magazzino`). ⚠️ L'id 36 in coda a un CSV di seed **scade
subito** se un'altra sessione ne prende uno: va riguardato prima del migrate.
La sequenza la riallinea `90_end/20260818-72`, che è `runAlways` e dinamica.

### Le scelte che il brief lasciava al DB

* **un corpo e due involucri** (R-1 lo lasciava aperto): la regola è la stessa
  per le due famiglie, e due corpi gemelli sarebbero due posti dove cambiarla —
  cioè il difetto che R-1 viene a chiudere;
* **la madre chiama la check** (R-1 lo proponeva come alternativa): è la forma
  di casa (§12.5.2, e la domanda di AGENTS.md «questa regola deve anche
  accendere un pulsante?»). Il prezzo è la rev delle due madri; il guadagno è
  che il rifiuto e il tooltip **non possono** divergere.

### ⚠️ Due `reason_key` in più di quelle che R-1 elencava

R-1 ne chiedeva tre; ne escono **cinque**, e la ragione è un difetto trovato
provando la funzione: su un documento `POSTED` il motivo era
`DOCUMENTO_NON_CONFERMATO`, cioè una frase **falsa** nel tooltip del pulsante.
Il codice dell'errore resta uno solo (`E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA`:
la frase per l'operatore è la stessa), ma il `reason` no.

**Le chiavi i18n da seminare — al FE, nello stesso giro** (senza,
`scripts/check_i18n_keys.py` controllo 4 fallisce appena la doc auto-gen entra
nel repo, e il tooltip è vuoto):

| Chiave | Dove compare |
| --- | --- |
| `magazzino.documenti_interni.azione.conferma` · `.riapri` · `.annulla` | le etichette dei tre pulsanti |
| `magazzino.documenti_interni.registra_reason.non_confermato` | «Registra» spento su una bozza |
| `magazzino.documenti_interni.registra_reason.gia_registrato` | …su un documento già registrato |
| `magazzino.documenti_interni.registra_reason.annullato` | …su uno annullato |
| `magazzino.documenti_interni.registra_reason.senza_righe` | …su un documento vuoto |
| `magazzino.documenti_interni.registra_reason.righe_non_postabili` | …quando una riga non si può registrare |
| `magazzino.documenti_interni.stato_info.posted` · `.cancel` | la nota sugli stati chiusi (testi proposti in R-1) |

#### ⛔ Il guard delle chiavi è ROSSO, e ne nomina **due su otto**

Entrata la doc auto-gen nel repo, `scripts/check_i18n_keys.py` fallisce — come
previsto. ⚠️ **Ma il suo rosso non è l'elenco del lavoro**: misurato il 22-09 a
fine serata, nomina solo
`magazzino.documenti_interni.registra_reason.senza_righe` e
`….righe_non_postabili`. Le altre **sei** le legge nessuno, e la causa è la
**forma** in cui la chiave è scritta nel corpo, non la chiave:

| Chiavi | Perché il guard non le vede |
| --- | --- |
| `registra_reason.{gia_registrato, annullato, non_confermato}` | stanno dentro un `CASE v_stato`, e il regex `RE_DB_KEY` pretende `'reason_key', '<letterale>'` **sulla stessa riga** |
| `azione.{conferma, riapri, annulla}` | stanno in una tupla `VALUES`, dove la chiave non è preceduta dal nome della proprietà |
| `stato_info.{posted, cancel}` | `stato_info_key` **non è** fra i nomi che il guard cerca (`_PROP_KEY` = `label_key\|reason_key\|nessuna_azione_key`) |

⇒ Chi semina «quello che il guard dice» ne mette due e lascia **sei tooltip
vuoti**, con il guard verde a dirgli che è finita — la forma classica del verde
per sottrazione. **La lista buona è la tabella qui sopra**, che è anche quella
che il `COMMENT` di `fn_available_actions_documento_interno` dichiara per esteso.

🔵 **Candidato a un cantiere `dbops`, non di questo brief**: il guard è cieco per
forma, e la terza riga è la più facile da chiudere (`stato_info_key` nell'elenco
delle proprietà). Le prime due vogliono un criterio diverso — leggere le chiavi
dal `COMMENT`, che il progetto già obbliga a dichiararle — e quello cambia il
perimetro di un presidio trasversale: si decide, non si allarga di straforo.

### Il pgTAP

`db/pgtap/magazzino/test-capability-documenti-interni-v1.sql` — **14
asserzioni**. ⭐ Il test 3 è quello che conta: costruisce **tutte e dodici** le
transizioni fra i quattro stati e confronta, una per una, ciò che la matrice
ammette con ciò che il guard lascia davvero passare (tenendo aperta la porta
`POSTED` con la GUC, perché quello è un cancello a parte e va misurato da solo).
Un elenco scritto a mano nel test sarebbe stato una **terza** copia della
matrice.

⚠️ `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql` test 5 passa da **20 a
21**: `fn_posta_rettifica` è un sito nuovo nato sull'helper (la nota datata è
nel file). È il presidio trasversale che ogni cantiere che aggiunge funzioni
deve rilanciare.

### Come è stato provato, e che cosa questo NON prova

SQL **estratto** dai cinque changeSet, in `BEGIN … ROLLBACK` su dbdev: i cinque
compilano; il comportamento è quello disegnato (matrice, azioni nei quattro
stati, terna di «Registra», posting delle due famiglie); `plpgsql_check` via
`dbops.fn_check_funzioni_riferimenti_morti` non ha niente da dire sulle otto
funzioni toccate; sette guardrail statici verdi; e i pgTAP esistenti toccati
restano verdi nello stesso harness — `test-fn-posta-inventario-v1` 17/17,
`test-fn-posta-rettifica-v1` 6/6, `test-documenti-interni-guard-v1` 15/15,
`test-rubinetto-primo-motivo-v1` 7/7, `test-punti-canale-campo-v1` 14/14.

⛔ **Non prova** che regga da zero: su `zeroerp_ci` non è stato applicato niente,
e la CI di GitHub dal 21-09 sera non parte (billing). Non prova nemmeno il
comportamento **come applicazione**: l'harness gira da owner, quindi la RLS non
è esercitata — il 404 no-leak del test 14 vale davvero solo col runner come app.

### ⚠️ La ricaduta trovata dall'apply: il presidio C1 e un verde per coincidenza

Applicati i cinque changeSet (19:06 del 22-09), il presidio **«stati mai
scritti»** (`dbops/test-stati-check-scrittori-v1`, test 2) è diventato rosso su
due righe:

```
magazzino.inventari.stato_mag_inventario = CONFIRM
magazzino.rettifiche.stato_mag_rettifiche = CONFIRM
```

⭐ **E ha ragione lui.** A DB `CONFIRM` non lo scrive nessuno, e non lo ha mai
scritto: lo scrive il **backend** (`magazzino_service.py`, `STATI_RICHIEDIBILI`
— la conferma è un gesto dell'operatore dal drawer), esattamente come `CANCEL`,
che infatti era già dichiarato `APPLICAZIONE` nel registro il 21-09.

Fino al 22-09 quel valore risultava «scritto» per una **coincidenza testuale**:
il criterio del presidio chiama scrittore una funzione che *scrive la tabella* e
*nomina il letterale*, e `fn_posta_inventario` faceva tutte e due le cose —
scriveva `POSTED` e **leggeva** `'CONFIRM'` in un `IF`. Spostando quel letterale
nella check condivisa, la coincidenza è caduta e il presidio ha visto il buco
che c'era da sempre. ⚠️ È la **trappola 1** che quel presidio pinna nel proprio
test 6 (*«nominare non è scrivere»*), vista dall'altra parte: qui il criterio non
aveva prodotto un falso rosso, ne aveva nascosto uno vero.

**Rimedio** (`80_data/sql/dbops/stati_check_dichiarazioni.csv`, mirror
`runOnChange` + `ANY`: basta il CSV, si carica al prossimo migrate):

* **due righe nuove** — `inventari` e `rettifiche`, valore `CONFIRM`, canale
  `APPLICAZIONE`, con la ragione che nomina il file del BE e dice che a DB la
  check lo **legge** come precondizione del posting;
* **due righe corrette**: le dichiarazioni di `CANCEL` del 21-09 affermavano
  *«A DB fn_posta_inventario scrive CONFIRM/POSTED»* — una frase **falsa**, nata
  dalla stessa coincidenza. Ora dicono che scrive solo `POSTED`.

Provato in transazione annullata con le righe caricate: `vw_stati_check_da_sanare`
torna a **zero** e il presidio fa **14/14**.

✅ **Caricato da Tid il 22-09 alle 23:00** (il mirror `20260921-19` `RERAN`): le
due dichiarazioni sono a catalogo e la vista da sanare è a zero.

#### …e il presidio era anche LENTO: 8,3 s, e quasi tutto in una riga sola

Rilanciandolo, Tid ha detto la seconda cosa: *«il test funziona, solo che è
lento»*. Misurato il 22-09 su dbdev: **8,3 s**, di cui praticamente tutto in
`dbops.vw_stati_check_scrittori` — **535 ms a chiamata**, e il file la
interrogava **diciassette** volte.

Due rimedi, indipendenti l'uno dall'altro:

| Dove | Che cosa | Effetto |
| --- | --- | --- |
| `20260922-23`, rev della vista (✅ applicata il 22-09 sera) | i due CTE erano **prodotti cartesiani con un test testuale per coppia** (29 tabelle × 2250 funzioni, poi 242 × 2250). Ora si **estrae una volta e si confronta per uguaglianza**: i nomi qualificati che ogni funzione scrive, e in un passaggio solo le funzioni che citano un letterale di stato | 535 → **230 ms** a chiamata; il test 8,3 → **3,7 s** |
| il pgTAP | **due fotografie** in `TEMP TABLE` invece di diciassette interrogazioni: il file ha due soli momenti — prima dei casi costruiti e dopo — e fra le asserzioni di uno stesso momento non cambia niente | 3,7 → **1,2 s** (2,3 s con la vista vecchia) |

⛔ **Quello che NON si è fatto, ed era la tentazione**: riscrivere nel test il
filtro di `vw_stati_check_da_sanare` per fotografare una query sola. Sarebbe una
seconda copia del criterio — cioè il difetto che questo presidio esiste per
trovare. Si fotografano **tutte e due** le viste, com'erano.

**Prove**: la vista nuova e la vecchia confrontate con `EXCEPT` nei due versi sul
catalogo vivo, **zero righe di differenza** (114 per parte); il pgTAP **14/14**;
e una **prova per mutazione** — tolte le dichiarazioni dentro la transazione, il
test 2 torna rosso e nomina le righe giuste: la fotografia non lo ha reso cieco.

### Che cosa resta a Tid — ✅ sul DB non resta niente

1. ✅ **Migrate**: i cinque changeSet `20260922-18 … -22` `EXECUTED` alle 19:06
   del 22-09, i **seed** alle 23:00 (mirror `20260921-19` `RERAN`: le
   dichiarazioni del presidio C1; e i tre CSV di `config` —
   `E_MAG_INVENTARIO_RIGA_POSIZIONE_DUPLICATA` con la sua frase e l'azione
   `registra_magazzino` — verificati a catalogo), e **`20260922-23`** (la rev
   della vista del presidio C1) applicato in serata. ⇒ Del **primo** giro sul
   database non resta niente.
2. ✅ **pgTAP**: rilanciati da Tid il 22-09 sera e di nuovo il 23-09 dopo il
   lucchetto, **verdi, nessuna regressione**.
3. ✅ **commit** fatto (`ce91eb2d1` + `7d67d6d9d`): i sei changeSet (`-18 … -23`), i **cinque** CSV
   (`codici_errore`, `messaggi_errore`, `azioni_processo`,
   `stati_check_dichiarazioni`, `automation_lock_columns`), il pgTAP nuovo
   `magazzino/test-capability-documenti-interni-v1`, i due toccati
   (`script/test-rubinetto-primo-motivo-v1` a 21,
   `dbops/test-stati-check-scrittori-v1` con le due fotografie), le sei pagine
   `manual/` nuove e le **cinque** aggiornate — fra queste `inventari.md` e
   `rettifiche.md`, dove il lucchetto di R-4 mancava —, `_dominio-magazzino.md`
   e questo brief.
4. ✅ **Le quattro decisioni R-4 … R-7 sono prese da Tid il 22-09 sera**, una
   alla volta, e **già scritte** (§Il secondo giro): lucchetto su
   `magazzino_id` (e **non** sulla `data`), filtro sugli articoli gestiti — che
   si scopre essere lavoro del **BE**, non del DB —, e i due codici nuovi.
   ✅ **Migrate del secondo giro fatto** (23-09, 00:05): mirror `20260614-08`
   (codici + messaggi) e `20260110-15` (registro dei lock) `RERAN`. Letto sul
   catalogo vivo: i quattro codici ci sono con la loro classe
   (`E_MAG_INVENTARIO_RIGA_POSIZIONE_DUPLICATA` e `E_MAGAZZINO_VALIDATION`
   `DATO_ERRATO`, `E_MAG_DOCUMENTO_MAGAZZINO_IMMUTABILE` `CONFLITTO_STATO`,
   `E_MAG_DOCUMENTO_RIGA_NON_TROVATA` `NON_TROVATO`), i messaggi **1113-1116**
   pure — e il 1115 è entrato nella forma **corretta**, *«Richiesta di
   magazzino non valida.»*, senza il segnaposto che nessuno avrebbe riempito —,
   e `dbops.automation_lock_columns` ha le **due** righe nuove, `enabled`.

5. ✅ **Il lucchetto è ARMATO** (23-09). Su `magazzino.inventari` e
   `magazzino.rettifiche` ci sono `trg_inventari_a10_lock_columns_upd` e
   `trg_rettifiche_a10_lock_columns_upd`, entrambi con
   `magazzino_id → E_MAG_DOCUMENTO_MAGAZZINO_IMMUTABILE`. ⇒ Il **test 17 del
   guard non fa più `skip`**: il 17/17 adesso vale.
   ⭐ **Non l'ha armato una chiamata a mano**, ed è la parte che vale la pena
   leggere: l'automazione è stata richiamata da `90_end/20260923-02`, il
   changeSet di un cantiere nato da una riga di questo brief — la nota di R-4
   *«non si è riusato `CODICE_NON_MODIFICABILE`: è obsoleto»*. Guardando il
   registro dei lock per quella riga si è scoperto che **26 righe su 38**
   nominavano un codice ritirato o inesistente e che **69 trigger vivi** lo
   sollevavano con il presidio verde. La bonifica ha chiamato l'automazione una
   volta, e nello stesso gesto ha armato anche questi due:
   [brief-db-codici-ritirati-negli-argomenti-dei-trigger.md](brief-db-codici-ritirati-negli-argomenti-dei-trigger.md).
6. ✅ **pgTAP e commit**: rilanciati da Tid il 23-09, **nessuna regressione**;
   commit `7d67d6d9d`. ⇒ Sul database non resta niente di questo brief.

### Il secondo giro — le quattro decisioni, scritte (22-09 sera)

Decise una alla volta da Tid e messe a terra subito. ⚠️ **Nessuna è un
changeSet**, ed è il fatto che vale la pena leggere: tre stanno nei CSV di
catalogo e una è del backend.

| | Che cosa è entrato | Dove |
| --- | --- | --- |
| **R-4** | il magazzino della testata diventa **immutabile**, per le due famiglie | due righe in `80_data/sql/dbops/automation_lock_columns.csv` + il codice `E_MAG_DOCUMENTO_MAGAZZINO_IMMUTABILE` (`CONFLITTO_STATO`, msg 1114) |
| **R-5** | il filtro sugli articoli gestiti a magazzino | 🔵 **al BE**: non c'è nessuna funzione da cambiare (vedi R-1 qui sopra) |
| **R-6** | `E_MAGAZZINO_VALIDATION` (`DATO_ERRATO`, msg 1115) | `codici_errore.csv` + `messaggi_errore.csv` |
| **R-7** | `E_MAG_DOCUMENTO_RIGA_NON_TROVATA` (`NON_TROVATO`, msg 1116) | idem |

✅ **Applicato il 23-09 alle 00:05** (mirror `20260614-08` per codici e messaggi,
`20260110-15` per il registro dei lock, entrambi `RERAN`): i tre codici, i tre
messaggi e le due righe di lock sono a catalogo, verificati sul catalogo vivo.
🔴 **Ma i trigger del lock NON ci sono ancora**: il registro li dichiara, e li
scrive l'automazione — vedi il punto 5 di §Che cosa resta.

⭐ **Il lucchetto non si scrive a mano**, ed è la cosa che si sbaglia: il
trigger lo **genera l'automazione** dalla riga nel CSV (su dev
`CALL maintenance.proc_automations_lock_columns_job()`, in CI `ci_apply`). Un
`CREATE TRIGGER` scritto a mano con la stessa funzione sarebbe un oggetto che
*sembra* governato dall'automazione e non lo è — è già successo una volta, e se
ne è accorto solo un pgTAP.
⛔ E non si è riusato `CODICE_NON_MODIFICABILE`: è `obsoleto_dal 2026-08-05`.
⭐ **Da quella riga è nato un cantiere**: guardando il registro dei lock si è visto
che 26 righe su 38 nominavano quel codice ritirato o uno inesistente, e che **69
trigger vivi** lo sollevavano ancora con il presidio verde — il codice viaggia come
argomento del trigger, e il controllo guardava i corpi delle funzioni.
[brief-db-codici-ritirati-negli-argomenti-dei-trigger.md](brief-db-codici-ritirati-negli-argomenti-dei-trigger.md).
⚠️ Quella bonifica arma **anche** i due lock di R-4: è l'automazione, chiamata una volta.

⚠️ **La `data` resta modificabile**, per decisione esplicita nella stessa
risposta: il DB non congela la testata oltre il magazzino, e il BE non aggiunge
una regola che il DB non ha (Q-2 del piano, confermata).

**Presidio**: `magazzino/test-documenti-interni-guard-v1` passa da 15 a **17**
asserzioni — la dichiarazione nel registro dei lock e il rifiuto del lock
generato, quest'ultimo con `skip` finché l'automazione non l'ha scritto (stampo
di `test-ubicazioni-guard-parent-v1`). ⚠️ Lo skip è stato **provato**: montando
a mano il trigger nella transazione di prova, il test 17 diventa verde e la
frase combacia — cioè lo skip non sta nascondendo un messaggio sbagliato.
✅ **Dal 23-09 il test 17 NON è più in skip**: l'automazione ha generato i due
trigger e l'asserzione misura davvero. ⭐ Vale la pena tenerlo a mente come
forma: fino a quel momento il file dava **17/17 con una asserzione che non
aveva misurato niente** — uno `skip` motivato è onesto, ma non è una prova, e
il numero verde da solo non distingue i due casi.

#### ⚠️ Rilettura del 22-09 a fine serata: la frase di R-6 era l'unica col `%s`

`E_MAGAZZINO_VALIDATION` era nato con la frase *«Richiesta di magazzino non
valida: %s.»*, e quel segnaposto **non lo riempie nessuno**: a riempirlo è
`script.fn_log_and_raise_error`, e un codice che nessuna funzione PL/pgSQL
solleva da lì non ci passa mai — a video sarebbe uscito un `%s` grezzo.

⭐ **Il difetto si vede dalla famiglia, non dalla riga**: dei diciannove codici
`*_VALIDATION` a catalogo, i diciotto fratelli — a partire dal gemello
dichiarato `E_PAGAMENTI_VALIDATION`, *«Parametri non validi.»* — hanno tutti una
frase **senza argomenti**, ed è una proprietà del *chi solleva*, non uno stile:
li solleva il backend, che la propria frase se la compone e manda il campo da
accendere nel `context.field` e nel `detail` del `ServiceError`. La frase a
catalogo è quella che si legge quando quegli argomenti non ci sono.

⇒ Corretta in `messaggi_errore.csv` (*«Richiesta di magazzino non valida.»*), e
il **perché** è finito nella nota del codice in `codici_errore.csv`, così la
prossima persona non la ri-arricchisce. ✅ **Ed è entrata così**: al migrate del
23-09 il messaggio 1115 a catalogo è la frase chiusa — la correzione ha fatto in
tempo, il `%s` non è mai arrivato sul database. ⚠️ Gli altri tre codici del giro il `%s`
lo tengono, ed è giusto: `E_MAG_DOCUMENTO_MAGAZZINO_IMMUTABILE` lo riempie il
lock (la colonna), e i due `NON_TROVATO` seguono la forma dei fratelli del
21-09 (`E_MAG_UBICAZIONE_NON_TROVATA`, `E_MAG_LOTTO_NON_TROVATO`), dove
l'identificativo lo mette chi solleva.

#### La doc del lucchetto — il debito che R-4 aveva lasciato aperto

Il gemello del 21-09 la regola la **dice** nella sua pagina
(`manual/ubicazioni.md`: *«`magazzino_id` non si cambia dopo la creazione»*);
inventari e rettifiche no — la riga nel CSV e il pgTAP c'erano, la frase per chi
legge il dominio mancava. Chiusa in tre posti: `manual/inventari.md` e
`manual/rettifiche.md` (una sezione *«Il magazzino si sceglie alla nascita»*,
con l'errore, il `E_MAG_UBICAZIONE_DI_ALTRO_MAGAZZINO` che si prenderebbe al
posting senza il lucchetto, e la nota che la `data` invece resta modificabile) e
`_dominio-magazzino.md`, nel capoverso dei documenti interni.

### ✅ A BE/FE — fatto il 2026-09-23

Tutto consegnato nello stesso giro. Che cosa è entrato, e dove:

| | Che cosa | Dove |
| --- | --- | --- |
| **R-1** | il dettaglio porta `capabilities` e `stato_info_key` dal blob, **trasportati intatti**; il drawer monta le tre transizioni con `mapAvailableActionsToDrawerActions` e «Registra» dalla terna `can_registra*` | `famiglie.py` (`fn_capability`, l'involucro della famiglia), `magazzino_repository.get_capabilities`, `magazzino_service.get_documento`, `DocumentoInternoDrawer.vue` |
| **R-2** | `_UNIQUE_CONSTRAINTS` traduce il `23505` di `uq_mag_inventari_righe_posizione` nel codice registrato, `field = articolo_id` | `magazzino_service.py` |
| **R-3** | `post_permission = registra_magazzino` (era già dichiarato, fail-closed); il FE nasconde il pulsante a chi non ha l'azione (`AZIONE_REGISTRA_MAGAZZINO`) | `api/views.py`, `vocabolari.js` |
| **R-5** | `gestito_a_magazzino: bool \| None` sul repository, sul service e sull'endpoint di lookup; il picker di riga passa `gestitiAMagazzino: 'solo'` col meccanismo tri-stato che `ArticoloLookup` aveva già | `catalogo_repository.py`, `catalogo_service.py`, `catalogo/api/views.py`, `ArticoloLookup.vue`, `DocumentoInternoRigaForm.vue` |
| **R-6** | `E_VALIDAZIONE` passa a `E_MAGAZZINO_VALIDATION` — una riga, più i test e lo smoke che pinnavano il generico | `services/_helpers.py` |
| **R-7** | `E_MAG_DOCUMENTO_RIGA_NON_TROVATA` sul 404 della riga; la frase la porta il catalogo, qui resta l'etichetta tecnica del log (stampo dei tre 404 del 21-09) | `magazzino_service.py` |
| codici | `genera_error_policies` rigenerato (**quattro** voci nuove, zero classi mosse) e i **quattro ripieghi** senza segnaposto, in ordine di catalogo | `error_policies_generated.py`, `error_messages_fallback.py` |
| i18n | le **dieci** chiavi emesse dal DB (`azione.*`, `registra_reason.*` ×5, `stato_info.*`) più quelle del verbo («Registra», conferma, esito) e della conferma di transizione, it/en | `locales/{it,en}.json` |

⭐ **Le chiavi erano dieci, non otto**: la check emette anche `gia_registrato` e
`annullato` — i due tooltip che lo stesso codice di transizione prende secondo
lo stato. Il brief ne dichiarava otto perché contava tre `reason_key`.
⚠️ E `check_i18n_keys.py` ne nominava **due**: le altre otto sono il punto
cieco già dichiarato più sopra. Ora il guard è verde perché ci sono tutte, non
perché le abbia viste.

**Presidi** — verdi il 2026-09-23:

* BE: `apps.magazzino.tests` + `apps.catalogo.tests` + `apps.core.tests`, e la
  suite intera (**5202** test). Tre prove nuove **sul DB vero**
  (`tests/db/test_documento_interno_db.py`): la capability segue la matrice del
  guard costruendo le sei transizioni, «Registra» è spento col motivo giusto
  nei **tre** casi con cui le madri rifiutano, il duplicato di posizione esce
  col suo codice — e la rettifica **non** lo prende. Più il pinning dei **nomi**
  del blob: un campo rinominato a DB non spegnerebbe niente a video, lascerebbe
  un pulsante grigio che sembra una regola.
* FE: `vitest` 251, `npm run lint`, `npm run guards` (incluso `guard:filtri`,
  registri invariati), `check_i18n_keys` pulito, `vite build`.
* Smoke `smoke-magazzino-inventario-primo-carico.py`: **12/12**, rollback.

🔴 **Un limite dichiarato, non un rinvio**: la barra del drawer **non ha un
presidio automatico lato FE**. Nel progetto nessuno spec monta un componente —
`@vue/test-utils` non è fra le dipendenze, e non se ne aggiungono senza il via
libera di Tid. Ciò che regge è il presidio del **contratto** (i nomi del blob,
pinnati lato BE) e il collaudo a video. ⇒ La forma di guasto che resta scoperta
è quella che api.md §Capability descrive: *un campo letto col nome sbagliato non
fa fallire niente*.

⚠️ **Una ricaduta trovata strada facendo, e non è di questo brief**: il test BE
`test_il_codice_del_magazzino_e_lockato_e_il_duplicato_dice_il_campo` era rosso
prima di toccare qualunque cosa. Il changeSet `90_end/20260923-02` (cantiere
[codici ritirati negli argomenti dei trigger](brief-db-codici-ritirati-negli-argomenti-dei-trigger.md))
ha rigenerato i lock coi codici vivi, e `CODICE_NON_MODIFICABILE` — obsoleto dal
2026-08-05 — è diventato `E_CODICE_NON_MODIFICABILE`: il test pinnava il vecchio.
Allineato qui perché senza, la suite del dominio resta rossa. ⭐ Vale la pena
notarlo come forma: **un codice ritirato a DB lascia indietro i test del backend
che lo nominano**, e nessun cancello li lega.
