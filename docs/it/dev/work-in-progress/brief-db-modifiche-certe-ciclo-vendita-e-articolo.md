# Brief DB — le modifiche certe: le date di consegna, il modo di approvvigionamento, la commessa leggibile

> **Destinatario:** team DB (`dev/db-tid`) per l'esecuzione, **e team BE/FE come
> lettori** — ⭐ **questo documento è l'unica comunicazione che BE e FE
> riceveranno su questo lavoro.** Decisione di Tid, 2026-09-01: *«non faremo
> documentazione BE/FE, manderemo solo questo nuovo brief con tutta l'attività
> fatta»*. Quindi la §5 non è un'appendice: è la parte che va letta dall'altro
> lato, e deve bastare da sola.
>
> **Origine.** Le due analisi del 2026-09-01 su commessa e magazzino. Tid:
> *«da questi dobbiamo estrarre quali potrebbero essere le modifiche necessarie,
> quelle che sicuramente servono, tenendo fuori quelle collegate a decisioni da
> prendere»*.
>
> ⭐ **Terza origine, aggiunta il 2026-09-01 a sera**:
> [analisi-simmetria-ordini-acquisto.md](analisi-simmetria-ordini-acquisto.md),
> scritta lo stesso giorno. Ha prodotto **tre** voci che passano lo stesso filtro
> (§3-bis, §7, §8) e ha allargato la motivazione del Blocco B — vedi §1.
>
> **Stato:** 🔵 **APERTO — piano scritto, nulla applicato.** Nessun changeSet
> ancora creato. ⛔ Niente si applica senza autorizzazione esplicita di Tid.
>
> 🔴 **Verificato il 2026-09-12 contro il DB vivo (doc auto-gen) e contro ciò che
> è entrato in esercizio fra il 01-09 e il 12-09.** I tre blocchi reggono —
> nessuna colonna, nullabilità o vista cambia — ma **le premesse operative sono
> cambiate in dodici punti**, due dei quali avrebbero fatto fallire il migrate
> (P-2) o lasciato tre colonne vuote a video senza nessun rosso (lista articoli
> e pannello situazione merce). ⭐ **Da leggere per
> primo: §10**, che li elenca; le sezioni toccate portano ciascuna la propria
> correzione datata. Le **tre decisioni** che ne uscivano sono state prese da
> Tid lo stesso giorno (§10.3): **il brief è eseguibile, il piano è la §6.**
>
> ⚠️ **Perimetro:** solo ciò che **nessuna decisione aperta può cambiare**. Il
> criterio è dichiarato in §1 ed è l'unica ragione per cui una voce sta qui.

---

## 1. Il filtro, ed è tutto il valore di questo documento

Le due analisi contengono molto più di quanto sta qui. La domanda che ha separato
le voci è **una sola**:

> **Se le decisioni aperte venissero prese in un modo o nell'altro, questa voce
> cambierebbe?** Se sì, non è in questo brief.

Le decisioni aperte sono le **D-1 → D-9** dell'[analisi
magazzino](analisi-db-magazzino-aggancio-documento-e-produzione.md) §8 (*fino al
2026-09-12 qui c'era scritto «D-8»: è lo stesso off-by-one che la revisione
incrociata del 02-09 aveva corretto negli altri tre documenti e non in questo*)
e la **§7**
dell'[analisi commessa](analisi-db-commessa-e-produzione-predisposizione.md) —
cioè: se l'ODL è una sorgente o un anello proprio, se il ledger di magazzino usa
il catalogo delle sorgenti o il riferimento testuale, e se la commessa di
produzione è `vendite.commesse` o un'entità sua.

⚠️ **Il filtro NON è «serve anche se la produzione non si farà mai».** La
produzione non è una delle decisioni aperte: Tid l'ha data per assunta — *«siamo
vicini a iniziare lo sviluppo, e anche se ora non c'è dobbiamo prevederlo»*. È
aperta la sua **forma**, non la sua esistenza.

### ⭐ Il risultato del filtro, ed è la cosa più utile che è emersa

**Tutte le voci certe stanno su `vendite` e `catalogo`. Tutte le decisioni aperte
stanno su `magazzino` e sulla forma dell'ODL.**

Le due analisi sembravano contigue e in realtà **non si bloccano a vicenda**: il
lavoro di questo brief si può fare adesso, sulle tabelle in esercizio, mentre
`magazzino` aspetta le sue decisioni. Non c'è un ordine da rispettare fra i due.

> ⚠️ **Aggiornamento del 2026-09-12: un ordine adesso C'È, ed è questo brief per
> primo.** Due fatti nuovi: (1) `acquisti` e `magazzino` sono **il prossimo
> cantiere** (decisione di Tid dell'11-09, in `.codex/PROJECT_CONTEXT.md`);
> (2) l'[analisi carico e scarico](analisi-db-magazzino-carico-e-scarico.md) ha
> **chiuso** M-1, M-2, M-3, M-4, M-5, M-6, M-8 e M-9 fra il 02-09 e il 04-09, e
> tre di quelle decisioni **leggono colonne che nascono qui**: la primitiva di
> scrittura (M-2) è guidata da `catalogo.articoli.gestito_a_magazzino`; la vista
> «effettiva / impegnata / in arrivo» (§7-bis) legge
> `acquisti.ordini_righe.data_consegna_confermata_fornitore` e
> `vendite.ordini_righe.data_consegna_confermata`; e M-5 aggiunge
> `catalogo.articoli.requires_lotto` accanto alle tre colonne del Blocco B (§8).
> ⇒ Il filtro della §1 non cambia — nessuna di quelle decisioni **modifica** una
> voce di qui — ma il brief smette di essere «parallelo e indipendente»: è il
> **prerequisito** del cantiere che viene dopo, e la sua priorità sale.

### ⭐ E il Blocco B serve a due cantieri, non a uno (2026-09-01)

Il Blocco B è motivato qui dalla **produzione** — «questa riga richiede
produzione?». L'analisi acquisto mostra che risponde anche a una seconda domanda,
che nessuna decisione aperta tocca: **«questo articolo si compra?»**. Il valore
`ACQUISTO` è il default del vocabolario, ed è il perno da cui parte qualunque
proposta d'acquisto.

⇒ Non cambia una riga del blocco: ne **rinforza la certezza**. Un blocco che
serve a due cantieri indipendenti non dipende dalla forma di nessuno dei due.

---

## 2. Blocco A — Le date di consegna

### 2.1 Che cosa manca, e perché è la prima

⛔ **Non esiste alcuna data di consegna in tutto il database.** Cercata su
`vendite`, `acquisti` e `magazzino` il 2026-09-01: l'unica data di previsione
dell'intero modello è `magazzino.reservations.data_prevista` (dal 2026-09-02 decisa come `magazzino.movimenti_attesi`), in uno schema che
non è in esercizio.

⚠️ **Nessuna delle date esistenti serve, e vanno nominate per non farsele
proporre di nuovo:**

| Colonna | Perché non è quella |
| --- | --- |
| `vendite.ordini.data` | è la **data documento**, e governa numerazione, anno e pavimenti |
| `commesse.competenza_dal/al` | è **competenza fiscale**: riusarla farebbe dissentire due domande sulla stessa colonna |
| `data_insert` | è quando la riga è stata scritta, non quando la merce è attesa |

⭐ **E serve anche senza produzione**: senza una data di consegna non esiste la
nozione di **ritardo**. `vw_situazione_merce_ordine` sa dire *quanto* resta da
spedire e non saprà mai dire *se è tardi*. Nessun sollecito, nessuna priorità di
evasione, nessun indicatore di puntualità.

### 2.2 Le colonne

| Tabella | Colonna | Tipo | Null |
| --- | --- | --- | --- |
| `vendite.ordini_righe` | `data_consegna_richiesta_cliente` | `date` | sì |
| `vendite.ordini_righe` | `data_consegna_confermata` | `date` | sì |
| `vendite.preventivi_righe` | `data_consegna_richiesta_cliente` | `date` | sì |
| `acquisti.ordini_righe` | `data_consegna_richiesta` | `date` | sì |
| `acquisti.ordini_righe` | `data_consegna_confermata_fornitore` | `date` | sì |

**Le due date sono due cose diverse** e la differenza fra loro *è* la promessa:
la prima è quando il cliente la vuole, la seconda quando ci si impegna a darla.
Sull'ordine d'acquisto lo stesso, ribaltato: quando la si chiede al fornitore e
quando lui conferma — ed è l'informazione che oggi manca per sapere se la merce
arriverà in tempo per una consegna già promessa.

⛔ **Sulla RIGA, non sulla testata**, e non è un dettaglio: una riga può essere
pronta e un'altra no. È esattamente il caso «questa riga richiede produzione», ed
è anche il caso banale «il pezzo grosso arriva a marzo, il resto subito».

⛔ **Niente colonna di testata.** La data della testata è
`min(data_consegna_richiesta_cliente)` sulle righe attive: una colonna sarebbe una
**seconda sorgente di verità** che va fuori sincrono al primo cambio di riga.
Dove serve come dato — la lista ordini — si espone dalla vista (§5.2), non dalla
tabella.

⚠️ **`vendite.preventivi_righe` ha solo la richiesta**, non la confermata: su un
preventivo non c'è ancora niente da confermare.

⛔ **`vendite.offerte_commerciali` NON entra**: non ha righe articolo (ha
utilities ed eccezioni), quindi non c'è la riga a cui la data apparterrebbe.

> ✅ **I NOMI seguono la convenzione D-12 — DECISO da Tid il 2026-09-02.**
> `data_consegna_confermata` sarebbe nata **su due tabelle con l'attore invertito**: su
> vendite la promessa è **nostra**, su acquisti è del **fornitore**. E la proprietà è
> pure **incrociata**, perché la data *richiesta* su vendite la esprime il **cliente**
> mentre su acquisti la esprimiamo **noi**.
>
> ⛔ Il posto dove il difetto sarebbe morso è la vista di [carico e scarico
> §7-bis](analisi-db-magazzino-carico-e-scarico.md), che legge **entrambe** per comporre
> impegnato e in-arrivo: lì il nome della tabella sparisce e restano due omonime che
> promettono cose di soggetti diversi.
>
> **Regola applicata** — *non marcato = nostro, marcato = della controparte*, la stessa
> di `numero` / `numero_fornitore`:
>
> | Tabella | Nostra | Della controparte |
> | --- | --- | --- |
> | `vendite.ordini_righe` | `data_consegna_confermata` | `data_consegna_richiesta_cliente` |
> | `vendite.preventivi_righe` | — | `data_consegna_richiesta_cliente` |
> | `acquisti.ordini_righe` | `data_consegna_richiesta` | `data_consegna_confermata_fornitore` |
>
> ⚠️ **Ricadono anche i nomi derivati**: la colonna di testata della vista diventa
> `data_consegna_richiesta_cliente_min`, e con lei la chiave i18n (§5.2, §5.4). ⭐ È
> lunga, ed è il prezzo giusto: dice **di chi è la data** senza che si debba risalire
> alla tabella.
>
> ⭐ **Decisa prima di P-3**, cioè quando nessuna delle colonne esisteva: dopo sarebbero
> state quattro colonne in esercizio, due viste e una comunicazione già partita verso
> BE/FE. Origine: [analisi acquisti §6, D-12 e D-16](analisi-simmetria-ordini-acquisto.md).

### 2.3 ⛔ Nessun CHECK fra le due date, ed è una scelta

La tentazione è `data_consegna_confermata >= data_consegna_richiesta_cliente`. **È
falsa**: si può confermare *prima* di quanto chiesto, ed è una buona notizia, non
un errore.

E nemmeno un CHECK contro `ordini.data`: la **retrodatazione è un caso d'uso
vivo** in questo progetto — è la lezione già pagata dal cantiere numerazione, dove
un cancello sulla data era stato motivato con «la sceglie una persona» mentre è
proprio per questo che va lasciata scegliere.

⭐ La regola applicata: *un vincolo si mette dove il modello lo richiede, non
dove sembra ordinato.*

### 2.4 Il passaggio preventivo → ordine

`vendite.fn_push_preventivo_a_ordine` deve **portare avanti** la data richiesta,
altrimenti si perde nel punto in cui il documento cambia natura, ed è il punto in
cui gli utenti smetteranno di fidarsene.

⚠️ Toccando quella funzione si incontra un residuo già noto: nel corpo cita in un
commento `trgfn_ordini_gen_codice`, funzione che non esiste più. ⭐ È dichiarato
nel brief archiviato del prefisso sul registro (§6.3) come *«si fa alla prossima
occasione in cui la si tocca»*: **questa è quell'occasione**, e costa una riga.

---

## 3. Blocco B — Da dove arriva un articolo

### 3.1 Il buco, e le tre risposte sbagliate

⛔ **Oggi niente, in nessuna tabella, sa rispondere a «questa riga richiede
produzione?»** — e neppure a «questo articolo movimenta giacenza?», che serve a
`magazzino` a prescindere dall'ODL.

⚠️ **Le tre colonne che sembrano rispondere già, e non rispondono** — vanno
nominate perché sono la scorciatoia che qualcuno proporrà:

| Colonna | A che domanda risponde davvero |
| --- | --- |
| `articoli.is_composito` | *l'articolo ha componenti da esporre in fattura* (pricing v5, `esposto_in_fattura`). Un assemblato può essere comprato finito |
| `articoli.natura_vendita_id` | *dove va la riga venduta* (`destinazione_tipo`: ORDINE / COMMESSA / CONTRATTO). Dice la destinazione, non la provenienza |
| `nature_vendita.e_cessione_beni` | è **fiscale**: lo consuma `fn_resolve_iva_riga_guscio`. Riusarlo farebbe rispondere a un dato due domande in AND |

### 3.2 Il vocabolario `config.modi_approvvigionamento` (tabella nuova)

Colonne, sulla forma già usata da `config.nature_vendita`:

| Colonna | Note |
| --- | --- |
| `id` | identity |
| `codice_interno` | UNIQUE, **immutabile** (lock column) — è ciò su cui il codice confronta |
| `codice`, `descrizione` | mutabili, per l'operatore |
| `attivo`, `ordine`, `meta` | come tutti i vocabolari |

Seed: `ACQUISTO`, `PRODUZIONE`, `STOCK`, `NON_APPLICABILE`.

⭐ **Perché una tabella e non un CHECK su varchar**, ed è una scelta fatta qui
(revocabile, ma motivata): il modo di approvvigionamento è una **dimensione
dell'articolo** come la natura di vendita, e la natura di vendita è una tabella.
Il FE ha bisogno di una **select con etichetta** e la lista di un valore
**decodificabile**; un CHECK non dà né l'una né l'altro, e ogni consumatore
finirebbe per riscriversi le quattro stringhe a mano. ⚠️ E il giorno in cui la
produzione esiste, quel vocabolario avrà **attributi** (per esempio «richiede
ODL»): un CHECK non li può portare.

⚠️ **Tabella nuova = ciclo delle automazioni.** Audit, `tx_id` e storico non
esistono finché non gira `ci_apply`. E serve la riga in
`dbops.fk_index_policy` per la FK che nasce (⚠️ `dll_command` **sempre
valorizzato**, anche a `consentito = false`).

> 🔴 **Corretto il 2026-09-12 — verificato su `dbops.fn_run_automations_lock_columns`.**
> Fino a quel giorno questo paragrafo diceva che il lock su `codice_interno`
> *«va seminato in `dbops.automation_lock_columns` … DROP + rigenera»*. ⛔ **È
> falso, e avrebbe fatto seminare una riga che non serve**: il lock su
> `codice_interno` è **implicito** — la funzione lo monta per la sola presenza
> della colonna (*«codice_interno e' implicito: non si configura nella tabella di
> setup»*, riga 41 del corpo), ed è la regola già scritta in
> [linee-guida-sql §6b](../../linee-guida-sql.md). Prova: `config.nature_vendita`,
> il modello dichiarato di questa tabella, **non ha** nessuna riga in
> `automation_lock_columns.csv` e il lock ce l'ha. Il «DROP + rigenera» vale per
> le colonne **extra** (`natura_vendita_id` su `preventivi_righe` è il
> precedente), non per questa.
>
> ⭐ **E l'automazione che invece NASCE davvero, e nessuno l'aveva scritta**: il
> vocabolario ha `attivo`, quindi la FK da `catalogo.articoli` fa generare a
> `ci_apply` la coppia ATTIVO — sul **padre**
> `trg_modi_approvvigionamento_a10_articoli_block_deact_upd` (BEFORE UPDATE OF
> attivo: non si spegne un modo usato da articoli attivi) e sul **figlio**
> `trg_articoli_a10_modi_approvvigionamento_require_attivo_ins_upd` (constraint
> trigger AFTER, DEFERRABLE: un articolo non punta a un modo spento). ⚠️ È
> **questo** trigger a rendere vera l'asserzione «un articolo non può puntare a
> una riga spenta» del pgTAP di §7 — e nasce a `ci_apply`, non da un changeSet:
> su un `--fresh` senza `--ci-apply` quel test è rosso per assenza, non per
> difetto (memoria `pgtap verde su dbdev non dice niente sulla CI`).

### 3.3 Le colonne su `catalogo.articoli`

| Colonna | Tipo | Null | Default |
| --- | --- | --- | --- |
| `modo_approvvigionamento_id` | `bigint` FK → `config.modi_approvvigionamento` | **no** | `ACQUISTO` |
| `gestito_a_magazzino` | `boolean` | **no** | `false` |
| `lead_time_giorni` | `integer` (CHECK `>= 0`) | **sì** | — |

⭐ **Perché queste nullabilità e non altre**, applicando la regola del progetto
(*un `NOT NULL` va dove il dato si può fornire*):

* **`modo_approvvigionamento_id` NOT NULL**: il valore si può sempre dare, e un
  NULL significherebbe «non lo so» — cioè esattamente lo stato che questa colonna
  esiste per abolire. Il default `ACQUISTO` è il caso comune e non inventa niente.
* **`gestito_a_magazzino` NOT NULL DEFAULT `false`**: il default è **fail-safe** —
  nessun articolo comincia a movimentare giacenza per distrazione. ⚠️ Ne discende
  che al rilascio *tutti* sono `false` e la merce va marcata: è un lavoro di dato,
  ed è il momento giusto per farlo, perché `magazzino` non è in esercizio.
* **`lead_time_giorni` NULLABLE**: per una prestazione non significa niente, e
  `0` non è «non si applica». Qui il NULL è un'informazione.

⚠️ **`gestito_a_magazzino` non si deriva da `natura_vendita = MERCE`**: una merce
può essere venduta senza passare da giacenza (consegna diretta dal fornitore).
Sono due domande, e vanno tenute separate anche quando oggi le risposte
coincidono.

> 🔴 **Il `NOT NULL DEFAULT ACQUISTO` NON si scrive in un changeSet solo, e non
> per prudenza sui dati — per la TIMELINE delle fasi (2026-09-12).** Il default
> è l'`id` di una riga che nasce dal seed CSV di `80_data` (P-1), e `80_data`
> gira **dopo** tutto `00_schema`. Quindi un `ADD COLUMN … NOT NULL DEFAULT <id>`
> con la sua FK, scritto in `00_schema`:
>
> * su **dev** muore subito: `catalogo.articoli` ha righe, la FK si valida
>   all'`ADD CONSTRAINT`, e `config.modi_approvvigionamento` a quel punto è
>   ancora **vuota**;
> * in **CI** muore poco dopo: il mirror `articoli.csv` è ancorato a
>   `20260114-06`, cioè a gennaio, e in `80_data` inserisce gli articoli
>   **prima** del seed del vocabolario (numerato settembre) — con il default a
>   un id che non esiste ancora.
>
> ⭐ **La forma è già scritta, sulla stessa tabella**: `natura_vendita_id` è
> nata così — `20260608-43` (`00_schema`: colonna **nullable** + FK),
> `20260608-42` (`80_data`: seed), `20260609-04` (`80_data`, numerato **dopo** il
> seed: risolve l'id di `MERCE` **per `codice_interno` a runtime**, backfill,
> `SET DEFAULT`, `SET NOT NULL`). Si ricalca quella, non si inventa. ⛔ E il
> `DEFAULT` finale resta un id letterale come su `natura_vendita_id`: è
> l'eccezione ammessa da §6b (*FK fisica reale*), da motivare nel changeSet.
>
> ⚠️ **E l'header di `articoli.csv` non prende le colonne nuove**: quel mirror
> è di gennaio, e una colonna con FK aggiunta a un mirror vecchio lo manda a
> scrivere prima del bersaglio (memoria `colonna FK su mirror vecchio`). Se un
> giorno servirà seminarle, `type: SKIP` sul vecchio + mirror ri-ancorato.
>
> Le altre due colonne — `gestito_a_magazzino` e `lead_time_giorni` — non hanno
> FK e stanno in un passo solo, in `00_schema`. Vedi §4-bis, corretta di
> conseguenza.

---

## 3-bis. Blocco B-bis — `famiglie_documento`: la colonna del billing account

> ⚠️ **Voce da confermare, ed è l'unica di questo brief che non si autogiustifica.**
> Passa il filtro della §1 — nessuna decisione aperta la cambia — ma **non è
> richiesta da nulla che stia qui dentro**: la chiede il cantiere acquisto. Sta in
> questo brief per una ragione sola, di costo, ed è Tid a decidere se accettarla.

`vendite.famiglie_documento` è l'elenco dei tipi di documento che prendono il
numero da un registro. Dichiara, per ognuno, **dove vive**: schema, tabella, e il
nome di tre colonne — `colonna_numero`, `colonna_serie`, `colonna_billing_account`.

⛔ **`colonna_billing_account` è `NOT NULL`**, e il guard
`trgfn_famiglie_documento_guard_riferimenti` verifica su `pg_attribute` che la
colonna nominata **esista davvero** sulla tabella. È corretto oggi: tutte e cinque
le famiglie in servizio un billing account ce l'hanno.

Diventa sbagliato al **primo documento che non ce l'ha** — e il primo è l'ordine
di acquisto, la cui controparte è un `soggetto_ruolo`, non un BA. Registrare
quella famiglia, oggi, fallisce con
`E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE`.

⭐ **La correzione non è da inventare: sta già nella stessa tabella.**
`colonna_serie` è **nullable**, e il vuoto non è un dato mancante — è la
dichiarazione che *quella famiglia una serie non ce l'ha* (reso e commessa). Stessa
forma per il billing account:

| Oggetto | Cosa |
| --- | --- |
| `famiglie_documento.colonna_billing_account` | da `NOT NULL` a **nullable**: `NULL` = «questa famiglia non ha un billing account» |
| `trgfn_famiglie_documento_guard_riferimenti` | salta il controllo `pg_attribute` quando è `NULL` |
| `anagrafiche.fn_ba_ha_storia_emittente` · `fn_get_storia_emittente_ba` | **saltano** le famiglie con colonna `NULL` — corretto per costruzione: un documento senza BA non può contribuire alla storia di nessun BA |

⚠️ **Il dettaglio che decide se funziona**: le due funzioni compongono SQL dinamico
con `%I`, e il salto va scritto nella query che **sceglie** le famiglie, non dentro
la composizione.

> 🔴 **I lettori sono più di tre — censimento del 2026-09-12** (memoria
> *cancellare una fonte = censire i lettori*). La tabella qui sopra fotografa il
> 01-09 mattina; lo stesso giorno il cantiere CRUD delle famiglie
> (`20260901-15/-17/-19/-20`) e poi l'08-09 (`20260908-24/-25`) hanno aggiunto
> **quattro** lettori DB e due applicativi, e P-9 li deve toccare tutti o resta a
> metà:
>
> | Lettore | Che cosa fa oggi con la colonna | Che cosa cambia |
> | --- | --- | --- |
> | `vendite.fn_crea_famiglia_documento` | ⛔ **la pretende non vuota** (riga 56: `COALESCE(btrim(p_colonna_billing_account), '') = ''` → rifiuto) | diventa opzionale come `p_colonna_serie` |
> | `vendite.trgfn_famiglie_documento_guard_struttura` + `script.fn_check_famiglia_documento_struttura_modificabile` | la contano fra le cinque colonne **immutabili** a registri vivi (`IS DISTINCT FROM`) | nulla: `NULL ↔ valore` è comunque un cambio, e va rifiutato |
> | `vendite.vw_famiglie_documento_lista` | la espone | nulla |
> | `backend/apps/vendite/services/famiglie_service.py` | ⛔ `_OBBLIGATORI_CREATE`: *«La colonna che porta il cliente è obbligatoria»* | esce dall'elenco, come `colonna_serie` che già non c'è |
> | il form FE delle famiglie | campo obbligatorio | opzionale |
> | `db/pgtap/vendite/test-famiglie-documento-crud-v1.sql` · `test-famiglie-documento-guard-riferimenti.sql` | fixture con la colonna sempre valorizzata | un caso in più: famiglia senza BA |
>
> ⇒ La riga «cinque righe» della tabella qui sotto **non è più vera**: sono
> quattro oggetti DB, un service, un form e due pgTAP. Resta piccolo, ma non è
> più *«nessun consumatore»* — ed è un'altra ragione per cui la voce va decisa e
> non fatta di straforo.

🔴 **Correzione del 2026-09-02, verificata sul database.** La prima stesura
motivava la regola dicendo che *«un `NULL` passato a `format('%I')` non solleva un
errore parlante»*. **È falso**: `%I` con `NULL` solleva eccome —
`i valori vuoti non possono essere formattati come un identificativo SQL`.
⭐ La regola resta la stessa e il motivo diventa **migliore**: comporre e poi
fallire significa che un operatore vede un errore **di PostgreSQL** — nessun codice
di dominio, nessun `context`, nessun campo da accendere — al posto di una funzione
che semplicemente non considera quella famiglia. Si salta *prima* per non arrivarci.
⚠️ **E il pericolo del silenzio esiste, ma vive su `%s`**: `format('%s', NULL)`
produce **stringa vuota** senza fiatare. Se in quelle due funzioni una parte del
comando si compone con `%s`, il ramo muto è lì, non su `%I`.

### Perché proporla adesso, e perché potresti dire di no

| Per farla ora | Per rimandarla |
| --- | --- |
| è il momento di **costo minimo**: cinque righe, nessun consumatore acquisto, nessun registro vivo di acquisto | non serve a **niente** di ciò che sta in questo brief |
| dopo si tocca una tabella con registri in esercizio e il guard in servizio | il cantiere acquisto ha i suoi lotti, e questa è roba sua |
| la forma è **certa** e ha il precedente identico accanto | ⚠️ farla ora significa una colonna nullable che per mesi non ha nessun `NULL` — e questo brief altrove **contesta** proprio le strutture senza funzione |

⛔ **Non la decido io.** La riga di destra è un argomento vero, ed è lo stesso che
in §8 tiene fuori altre voci. ⇒ **P-9 è marcata come opzionale** in §6: si esegue
solo se Tid la conferma.

⚠️ E comunque **il trasloco del motore fuori da `vendite` NON è di questo brief**:
l'analisi acquisto lo ha rimandato di proposito al giorno in cui il primo ordine
d'acquisto prende davvero un numero — la regola del 2 non si applica a un secondo
consumatore che non esiste ancora.

---

## 4. Blocco C — La commessa leggibile

⛔ Oggi `vendite.commesse` ha `codice` e **nient'altro di parlante**: in una lista
non si capisce che cosa sia.

| Colonna | Tipo | Null | Note |
| --- | --- | --- | --- |
| `descrizione` | `varchar(255)` | sì | l'oggetto della commessa, in parole |
| `data_apertura` | `date` | **no**, default `script.fn_data_operativa()` | ⛔ **mai `now()` nudo**: è la convenzione del progetto |
| `responsabile_risorsa_umana_id` | `bigint` FK → `anagrafiche.risorse_umane` | sì | chi la governa. ✅ **DECISO da Tid il 2026-09-12 (D-A)**: era `responsabile_soggetto_ruolo_id → soggetti_ruoli`; la convenzione di casa per una persona interna è `risorsa_umana_id` (le tre tabelle di `pratiche`) — riquadro sotto |

⭐ **Perché sono certe**: servono alla commessa **così com'è oggi**, cioè al
contenitore di fatturazione. Valgono identiche in tutti e due gli esiti della §7 —
se domani la commessa diventasse anche la testata di produzione, queste tre
resterebbero e se ne aggiungerebbero altre.

> 🔴 **Il paragrafo che seguiva è stato RITIRATO il 2026-09-12: poggiava su una
> premessa falsa, verificata sulla doc auto-gen.** Diceva: *«la FK nuova genera
> un trigger BEFORE ROW di parent attivo … su commesse ce ne sono già tre a mano
> … va verificato che il generato non oscuri uno di quelli»*. Tre cose non
> tornano:
>
> 1. `anagrafiche.soggetti_ruoli` **non ha la colonna `attivo`** ⇒
>    `dbops.fn_run_automations_attivo` salta la coppia (`PARENT_NO_ATTIVO`) e
>    **non genera niente** per questa FK — come già non genera niente per
>    `emittente_soggetto_ruolo_id`, che punta alla stessa tabella;
> 2. anche dove genera, il trigger sul **figlio** (`…_require_attivo_ins_upd`) è
>    un constraint trigger **AFTER**, non `BEFORE ROW`: non può oscurare nessun
>    guard di riga. L'ordine alfabetico morde sul **padre**, fra
>    `prevent_deactivate_if_children` generati e guard a mano — è il caso della
>    memoria, ed è un altro caso;
> 3. i `BEFORE ROW` a mano su `commesse` sono **quattro**, non tre: c'è anche
>    `trg_commesse_a10_default_emittente_ins`.
>
> ✅ **Quello che invece serve, e mancava**: la riga in `dbops.fk_index_policy`
> per la FK nuova (`consentito` deciso e `dll_command` valorizzato — è la stessa
> regola di P-1, e P-4 non la nominava).
>
> ⚠️ **E una domanda di modello che il brief aveva chiuso senza porla —
> decisione per Tid (§10.3, D-A).** Il progetto ha già una convenzione per «una
> persona interna che governa o è assegnata»: `risorsa_umana_id → anagrafiche.risorse_umane`
> (`pratiche.pratiche`, `pratiche.flussi`, `pratiche.competenze_flussi` — tutte e
> tre; e `risorse_umane` ha `attivo` e la finestra di validità). Un FK verso
> `soggetti_ruoli` ammette come responsabile **qualunque ruolo**, un cliente o un
> fornitore compresi. Le due forme costano diverso:
>
> | | `responsabile_soggetto_ruolo_id → soggetti_ruoli` | `responsabile_risorsa_umana_id → risorse_umane` |
> | --- | --- | --- |
> | coerenza col progetto | ⛔ una quarta forma per lo stesso concetto | ✅ la convenzione di `pratiche` |
> | chi può essere responsabile | chiunque abbia un ruolo | solo una risorsa umana |
> | automazione ATTIVO | nessuna (il padre non ha `attivo`) | ⚠️ **nasce**: il blocco sul padre impedirebbe di disattivare una persona finché è responsabile di **qualunque** commessa — anche chiusa, perché `commesse` non ha `attivo` e il generato conta *tutti* i figli (memoria *cancello su stato persistente = blocca per sempre*). ⛔ E **non si esclude per coppia**: lo scope dell'automazione è per tabella. ⭐ Ma è esattamente la situazione in cui `risorse_umane` **già vive**: porta tre block identici da `pratiche`, `flussi` e `competenze_flussi`, e nessuna delle tre figlie ha `attivo`. Il quarto non cambia la natura del cancello |
>
> ✅ **DECISO (Tid, 2026-09-12): la seconda — `responsabile_risorsa_umana_id →
> anagrafiche.risorse_umane`.** Ne discende, e va scritto nel changeSet di P-4:
>
> * a `ci_apply` nascono **due** trigger che nessun changeSet scrive —
>   `trg_risorse_umane_a10_commesse_block_deact_upd` sul padre (BEFORE UPDATE OF
>   `attivo`) e `trg_commesse_a10_risorse_umane_require_attivo_ins_upd` sul figlio
>   (AFTER, DEFERRABLE). ⛔ Niente DDL né `preCondition` su quei nomi
>   (linee-guida §11.5); l'esistenza si asserisce nel pgTAP di §7, che gira a
>   `ci_apply` avvenuto;
> * il block sul padre è il **quarto** della sua specie su `risorse_umane`
>   (`pratiche`, `flussi`, `competenze_flussi`): una persona responsabile di una
>   commessa — anche chiusa — non si disattiva finché lo è. Dichiarato, non
>   corretto: è la postura che quella tabella ha già;
> * `fk_index_policy`: riga per `fk_commesse_risorse_umane`, `consentito = false`
>   con `dll_command` valorizzato — nessuna query dell'applicazione entra oggi
>   da quella colonna (§8.7 delle linee guida: si decide sulla query, non sulla
>   FK).

---

## 4-bis. I default che AFFERMANO — e perché resta una domanda di modello

> 🔴 **Riscritta il 2026-09-02.** La prima stesura trattava questo come un problema
> di **migrazione dati**: backfill obbligatorio, sequenza in tre passi per non
> scrivere mai il valore falso. ⛔ **Era cerimonia da produzione, e produzione non
> ce n'è.** Tid: *«i dati sono solo di test, possiamo fare quello che vogliamo»* —
> è la regola già in vigore nel progetto (breaking secchi ammessi, nessun fallback
> transitorio), e qui non l'avevo applicata.
>
> ⭐ **Ma la domanda che resta non è sui dati: è sul modello.** Ed è per questo che
> la sezione non sparisce, si accorcia.

### Quel che cade

⛔ Niente sequenza `nullable → backfill → SET NOT NULL`, niente `UPDATE` di
bonifica obbligatorio, niente precauzioni sull'ordine dei changeSet. Con dati
usa-e-getta si scrive la forma finale e, se le righe di prova danno fastidio, si
rifanno. **Non è un rischio: è una comodità che abbiamo.**

> 🔴 **Corretto il 2026-09-12: il paragrafo qui sopra vale per DUE colonne su
> tre, e sulla terza avrebbe fatto morire il migrate.** La sequenza
> `nullable → seed → backfill → SET NOT NULL` era stata tolta perché letta come
> cautela sui *dati*. Su `modo_approvvigionamento_id` **non è quella la ragione
> per cui esiste**: il `DEFAULT` è l'id di una riga di `80_data`, e `00_schema`
> gira prima — su dev la FK non si valida, in CI il mirror di gennaio degli
> articoli inserisce prima del seed (§3.3, riquadro). ⇒ **La sequenza resta,
> nella forma del precedente `natura_vendita_id`** (`20260608-43` → `-42` →
> `20260609-04`). ⭐ La regola generale è la memoria *«il NOT NULL va dopo tutto
> `80_data`»*: non è cerimonia da produzione, è l'ordine in cui Liquibase legge
> le cartelle.
>
> Restano vere le due righe sotto: `gestito_a_magazzino` (nessuna FK) e
> `data_apertura` (default da funzione, che esiste già) stanno in un passo solo.
> ⚠️ Su `data_apertura` l'`UPDATE` di comodo da `data_insert` attraversa i
> trigger di `commesse` — audit, `tx_id` e **storico**: ogni commessa esistente
> riceve una versione shadow. Su dati di test è indifferente, ma va saputo
> leggendo `storico.commesse` dopo l'apply.

### Quel che resta, ed è la parte che i dati non risolvono

`NOT NULL` è un'**affermazione strutturale**: *«ogni riga di questa tabella ha
questo dato, e lo sappiamo»*. Se esiste un caso in cui la risposta onesta è «non lo
so», allora `NOT NULL` è la scelta sbagliata **sul modello** — e resta sbagliata
anche con zero righe, perché il caso si ripresenta il giorno in cui arriva un
import, un percorso di creazione che non valorizza la colonna, o una commessa
generata da un flusso che quella data non ce l'ha.

⇒ Le tre `NOT NULL` con default vanno guardate **una per una**, e non sono la
stessa cosa:

| Colonna | Che cosa afferma il default | Verdetto sul modello |
| --- | --- | --- |
| `articoli.gestito_a_magazzino = false` | «non movimenta giacenza» | ✅ **fail-safe**: dice *nel dubbio non fare*, ed è sempre una risposta legittima. `NOT NULL` è corretto. ⚠️ Resta il registro del §7, che non è una bonifica ma un **presidio**: la colonna a `false` ovunque è indistinguibile da «nessuno l'ha ancora marcata» |
| `articoli.modo_approvvigionamento_id = ACQUISTO` | «questo articolo si compra» | ✅ **DECISO `ACQUISTO`** (Tid, 2026-09-02). Afferma un fatto positivo, e per una prestazione è falso — ma il vocabolario è **modificabile dall'operatore** e la marcatura è un lavoro di dato che si fa comunque (come per `gestito_a_magazzino`). `NON_APPLICABILE` non avrebbe mentito, ma avrebbe reso *obbligatoria* la marcatura di ogni articolo prima di poterlo comprare |
| `commesse.data_apertura` | «questa commessa è stata aperta oggi» | ✅ **DECISO: `NOT NULL`, con valore iniziale da `data_insert`** (Tid, 2026-09-02) — non da «oggi». ⭐ La colonna nasce per essere letta in lista, e un `NULL` lì sarebbe una cella vuota per sempre; `data_insert` non è la data di apertura *reale* ma è **un fatto**, non un'invenzione |

✅ **Entrambe decise il 2026-09-02.** Su `data_apertura` il valore iniziale si prende
da `commesse.data_insert`, che esiste ed è `NOT NULL` per convenzione. ⚠️ È un `UPDATE`
di **comodo**, non una bonifica: si fa perché «quando la riga è stata scritta» è più
utile di «oggi», non perché ci siano dati da salvare — quelli sono di test.

⚠️ **E il `DEFAULT fn_data_operativa()` resta**, perché serve alle commesse **future**,
dove è la risposta giusta. Quello che non doveva fare è rispondere anche per il passato.

## 5. ⭐ La predisposizione BE/FE — la parte che va letta dall'altro lato

> ⛔ **Non ci sarà altra documentazione.** Questa sezione è la richiesta a BE e FE,
> e dichiara **tutto ciò che il DB consegna già pronto**, così che dall'altro lato
> non serva nessun lavoro di scoperta.

### 5.1 Che cosa il DB consegna, in una riga

**Le colonne nuove escono già dalle viste canoniche e sono già configurate come
colonne di lista.** BE e FE non devono aggiungere una vista, né una riga di
configurazione: devono **consumare** e, sul FE, tradurre le chiavi i18n.

### 5.2 Le viste che cambiano

| Vista | Colonne aggiunte | A cosa serve |
| --- | --- | --- |
| `vendite.vw_ordini_lista` | `data_consegna_richiesta_cliente_min` | ⭐ è la vista **canonica lista *e* dettaglio** degli ordini: la stessa colonna serve la lista e il drawer di testata |
| `vendite.vw_situazione_merce_ordine` | `data_consegna_richiesta_cliente`, `data_consegna_confermata`, `giorni_ritardo` | è la vista **per riga** che già tiene ordinato / consegnato / `da_spedire` con la soglia dell'impegno |
| `catalogo.vw_articoli_dettaglio` | `modo_approvvigionamento_id`, `modo_approvvigionamento_codice_interno`, `modo_approvvigionamento_descrizione`, `gestito_a_magazzino`, `lead_time_giorni` | è la vista della lista **e** del drawer articolo (lista `catalogo.articoli`, id 26) |
| 🔴 `vendite.vw_preventivi_righe_smistabili_ordine` *(aggiunta il 2026-09-12)* | `data_consegna_richiesta_cliente` | ⛔ **è la vista da cui `fn_push_preventivo_a_ordine` legge le righe** (cursore `FOR v_riga IN … FROM vendite.vw_preventivi_righe_smistabili_ordine`), con proiezione **esplicita** di 12 colonne: senza questa colonna P-5 non ha da dove copiare la data. Un `JOIN` sulla tabella dentro la funzione sarebbe una seconda sede della stessa lista di righe |

⭐ **`giorni_ritardo` sta lì e non altrove**, ed è la scelta che evita un difetto:
il ritardo non è «oggi > data richiesta», è «oggi > data richiesta **e** resta
merce da spedire». Il residuo e la soglia dell'impegno vivono in
`vw_situazione_merce_ordine`, che li calcola già; metterlo altrove significherebbe
ricalcolarli, cioè creare una seconda verità sul residuo. ⛔ **NULL quando
`da_spedire` è NULL o zero**: «non è in ritardo» e «non c'è niente da spedire»
sono due cose diverse, e quella vista ha già la disciplina di non confonderle.

⚠️ **Due trappole tecniche su queste viste, entrambe verificate:**

1. **`CREATE OR REPLACE VIEW` può solo APPENDERE**: le colonne nuove finiscono
   **in ultima posizione**. Non è disordine da sistemare, ed è già dichiarato nel
   commento di `vw_ordini_lista`. Chi consuma per posizione si romperebbe: si
   consuma per nome.
2. **`security_invoker=on` va RI-SPECIFICATA** in ogni `CREATE OR REPLACE VIEW`,
   altrimenti PostgreSQL la azzera e la vista smette di rispettare l'RLS di chi
   la legge. È la reloption di tutte e tre.

   > 🔴 **Corretto il 2026-09-12: NON è la reloption di tutte e tre.**
   > `catalogo.vw_articoli_dettaglio` **non ce l'ha** (verificato sulla doc
   > auto-gen), e non deve prenderla per imitazione: `catalogo.articoli` non ha
   > RLS e la vista non tocca dati protetti. Dal 07-09 il criterio è presidiato
   > sul **merito** e non sui nomi — `db/pgtap/rls/test-rls-viste-security-invoker.sql`
   > fa rosso su qualunque vista che attraversa una tabella protetta senza
   > l'interruttore, anche attraverso altre viste
   > ([brief-db-viste-security-invoker-criterio](../work-done/brief-db-viste-security-invoker-criterio.md)).
   > ⇒ La trappola resta vera per le **tre** viste di `vendite` (le due della
   > tabella più la smistabili), e adesso ha una rete: dimenticarla è un rosso,
   > non un buco silenzioso.
   >
   > ⚠️ **E dal 09-09 le righe sono sotto RLS.** `vendite.ordini_righe` e
   > `vendite.preventivi_righe` (con i loro satelliti) hanno le policy armate da
   > `20260909-30` e `-35` (`brief-db-perimetro-emittente-righe-documento`):
   > per le viste non cambia niente — erano già `security_invoker` — ma per i
   > pgTAP di §7 sì, vedi là.

⛔ **E un nome che il guardrail CI respinge**: `codice_interno AS *_codice` è
**vietato** (`linee-guida-sql` §6c, presidiato da
`scripts/sql/check_naming_stato_codice.sql`). Per questo la colonna decodificata
si chiama `modo_approvvigionamento_codice_interno` e **non** `..._codice`: quel
valore viene dalla colonna immutabile, e un consumatore che confronta contro un
`*_codice` si aspetta invece quella mutabile.

### 5.3 Le colonne di lista — sono **dato**, non DDL

La configurazione delle liste è una riga in `ui.lista_colonna` per colonna,
appesa al CSV `db/changelog/migrations_v2/80_data/sql/ui/lista_colonna.csv`.

| Lista | `lista_id` | Colonne nuove |
| --- | --- | --- |
| `vendite.ordini` | **7** | `data_consegna_richiesta_cliente_min` |
| `catalogo.articoli` | **26** | `modo_approvvigionamento`, `gestito_a_magazzino`, `lead_time_giorni` |

Per ogni riga vanno dati: `codice`, `etichetta`, `campo_sorgente` (il nome della
colonna **nella vista**), `tipo_colonna = informazione`, `tipo_dato`
(`date` / `boolean` / `numero`), `formato` (`date_short` per le date),
`larghezza_default`, `ordine_default`, `allineamento`, `gruppo`,
`filtrabile` / `ordinabile` / `esportabile`, `etichetta_i18n_key`, `priorita`.

⛔ **`sensibile` resta `f`.** Non è un'etichetta: è un **cancello** — a `t`, senza
il grant corrispondente, la colonna diventa **invisibile** e nessuno capisce
perché.

⚠️ **Il CSV si appende a mano.** `csv.writer` di Python pianta un CRLF e ri-quota
tutto il file: dopo l'append, `git diff --numstat` deve dare **`1 1`** e non un
rewrite di centinaia di righe.

⭐ **Non c'è niente da aspettare, sul FE.** Le liste si montano già con
`<ListaConfigurabile>`: una colonna nuova **compare come dato**, senza toccare un
componente. L'unica cosa che serve dall'altro lato sono le **traduzioni**.

> 🔴 **Vero per la lista 7, FALSO per la lista 26 — verificato sui repository il
> 2026-09-12.** `ordini_repository` fa `SELECT v.* FROM vendite.vw_ordini_lista`
> (lista **e** dettaglio): lì la colonna arriva da sola. `catalogo_repository`
> invece proietta una **lista esplicita** (`ARTICOLI_DETAIL_COLUMNS`) da
> `vw_articoli_dettaglio`: le tre colonne nuove **non escono** finché il BE non
> le aggiunge. ⛔ E il difetto è **muto due volte**: il trigger DB
> `ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente` è verde (la colonna
> nella vista c'è), e il cancello Django `test_lista_proiezione_campo_sorgente`
> **salta le liste che hanno una vista** — è nato per le 39 senza. Cella vuota,
> export con l'intestazione e niente dentro, colonna accendibile in
> «Personalizza» che non mostra niente.
> ⇒ Le tre righe della lista 26 si seminano **`attivo = f`** e le accende il BE
> nello stesso commit in cui estende la proiezione (memoria *colonna con
> `campo_sorgente`: `attivo=f` fino al BE*). La riga della lista 7 nasce attiva.
>
> ⚠️ **`ordinabile = t` è una modifica in due file.** La whitelist di ordinamento
> vive nel repository (`_ORDER_COLS_ORDINI`, `ARTICOLI_ORDER_COLUMNS`) e
> `scripts/gen_seed_lista.py --verifica-ordinamento <codice>` confronta le due
> sedi: una colonna `ordinabile=t` fuori whitelist è *una freccia che non
> ordina*. Chi semina `t` lo scrive nella §5.5 come voce BE, o semina `f`.

### 5.4 Le chiavi i18n dichiarate qui

Le chiavi seguono la convenzione già in uso (`vendite.contratti.col_data`,
`vendite.ordini.col_data`). Sono queste, e il FE deve solo aggiungere il testo:

```text
vendite.ordini.col_data_consegna_richiesta_cliente_min
vendite.ordini_righe.col_data_consegna_richiesta_cliente
vendite.ordini_righe.col_data_consegna_confermata
catalogo.articoli.col_modo_approvvigionamento
catalogo.articoli.col_gestito_a_magazzino
catalogo.articoli.col_lead_time_giorni
config.modi_approvvigionamento.acquisto
config.modi_approvvigionamento.produzione
config.modi_approvvigionamento.stock
config.modi_approvvigionamento.non_applicabile
```

> 🔴 **Sette chiavi su dieci non seguono i VICINI — verificato in `it.json` il
> 2026-09-12.** L'elenco sopra era scritto a regola (`<area>.<entità>.*`) senza
> guardare come sono già battezzate le colonne **della stessa lista** e dello
> stesso form:
>
> | Chiave proposta | Che cosa c'è già accanto | Forma coerente |
> | --- | --- | --- |
> | `catalogo.articoli.col_*` | la lista 26 usa `catalogo.col_codice`, `catalogo.col_uom`, `catalogo.col_composito`… — `catalogo` è **piatto**, non esiste `catalogo.articoli` | `catalogo.col_modo_approvvigionamento`, `catalogo.col_gestito_a_magazzino`, `catalogo.col_lead_time_giorni` |
> | `vendite.ordini_righe.col_*` | non esiste il ramo `ordini_righe`: i campi di riga vivono in `vendite.ordini.riga_articolo`, `riga_quantita`, `riga_prezzo`… | `vendite.ordini.riga_data_consegna_richiesta_cliente`, `vendite.ordini.riga_data_consegna_confermata` (e i gemelli in `vendite.preventivi.riga_*`) |
> | `config.modi_approvvigionamento.*` | ⛔ **non servono**: `config.nature_vendita` — il modello dichiarato — non ha nessuna chiave; la select mostra la `descrizione` del DB via `LookupSelect rel="config.nature_vendita"`, e la colonna di lista espone `modo_approvvigionamento_descrizione` | nessuna |
> | `vendite.ordini.col_data_consegna_richiesta_cliente_min` | ✅ coerente con `vendite.ordini.col_data` | invariata |
> | *(mancava)* `giorni_ritardo` sul pannello | il pannello ha il suo ramo, `vendite.situazione_merce.*` | `vendite.situazione_merce.col_giorni_ritardo` + le due date |
>
> ⚠️ È una decisione di **forma** e non di sostanza (D-C in §10.3): la regola di
> `frontend-standards` ammette entrambe — «l'indirizzo parte dall'area» — e il
> presidio `scripts/check_i18n_keys.py` passa in tutti e due i casi. Il criterio
> che consiglio è quello dei vicini: **una lista con due grammatiche di chiave
> è la forma in cui la terza nasce sbagliata**.
>
> ✅ **DECISO (Tid, 2026-09-12): i vicini.** L'elenco che il FE deve tradurre,
> e che sostituisce quello in cima alla sezione, è:
>
> ```text
> vendite.ordini.col_data_consegna_richiesta_cliente_min
> vendite.ordini.riga_data_consegna_richiesta_cliente
> vendite.ordini.riga_data_consegna_confermata
> vendite.preventivi.riga_data_consegna_richiesta_cliente
> vendite.situazione_merce.col_data_consegna_richiesta_cliente
> vendite.situazione_merce.col_data_consegna_confermata
> vendite.situazione_merce.col_giorni_ritardo
> catalogo.col_modo_approvvigionamento
> catalogo.col_gestito_a_magazzino
> catalogo.col_lead_time_giorni
> vendite.commesse.field_descrizione
> vendite.commesse.field_data_apertura
> vendite.commesse.field_responsabile
> ```
>
> ⚠️ Le tre di `vendite.commesse.*` non c'erano nell'elenco originale: il drawer
> commessa ha tre campi nuovi e le sue chiavi vivono in quel ramo, che esiste.
> Le due di `acquisti` (`riga_data_consegna_richiesta`,
> `riga_data_consegna_confermata_fornitore`) arrivano con il cantiere acquisto,
> che oggi non ha un form di riga. `etichetta_i18n_key` in `lista_colonna.csv`
> porta le chiavi `col_*` di questo elenco.

### 5.5 Che cosa deve fare il BE

1. **Righe d'ordine — scrittura**: gli endpoint di creazione/aggiornamento riga
   (vendite e acquisti) devono accettare e persistere le due date. Sono
   nullable: ometterle resta legittimo.
2. **Drawer articolo — scrittura**: i tre campi nuovi nel payload del drawer, con
   il modo di approvvigionamento come **lookup** sul vocabolario.
3. **Lookup nuovo**: `config.modi_approvvigionamento` va esposto come le altre
   decodifiche (attivi, ordinati per `ordine`).
4. **Drawer commessa**: `descrizione` e `responsabile` in scrittura,
   `data_apertura` in sola lettura (la scrive il default).
5. **Niente da fare per la lista**: le colonne arrivano dalla configurazione.

> 🔴 **L'elenco qui sopra è INCOMPLETO, e la §5.5 «deve bastare da sola» —
> riscritto il 2026-09-12 dopo aver letto i repository, non i documenti.** La
> frase *«consumare e basta»* è vera in **un** punto (la lista ordini legge
> `SELECT v.*`); ovunque altrove il backend **proietta colonne per nome**, e una
> colonna nuova che nessuno nomina non esiste per il frontend. Voce per voce:
>
> | # | Superficie | Che cosa c'è da fare, davvero | Dove |
> | --- | --- | --- | --- |
> | 1 | **Righe ordine/preventivo/ordine d'acquisto — lettura** | `list_righe` e `get_riga` proiettano colonne esplicite: le due date vanno **aggiunte alla SELECT**, o il form di riga non le vede mai | `vendite/db/ordini_repository.py`, `preventivi_repository.py`, l'omologo di `acquisti` |
> | 1-bis | **Righe — scrittura** | `create_riga` ha l'`INSERT` con l'elenco colonne; `update_riga` passa da `execute_dynamic_update` (whitelist del chiamante); nel service il parsing con `optional_iso_date` — una data malformata è un `400`, non un `500` | stessi file + `*_service.py` |
> | 1-ter | **Form di riga (FE)** | due `DatePicker` nel form della riga (`RigheMasterDetailTable` dei tre domini), chiavi i18n di §5.4 | `vendite/components/*RigheDrawer*`, acquisti |
> | 2 | **Articolo — lettura** | ⛔ `ARTICOLI_DETAIL_COLUMNS` è una tupla esplicita di 49 nomi: **le tre colonne nuove non escono** finché non ci sono (§5.3, riquadro). Poi `ARTICOLI_CREATE_COLUMNS` (da cui `_UPDATE_COLUMNS` deriva) per la scrittura e, se `ordinabile=t`, `ARTICOLI_ORDER_COLUMNS` | `catalogo/db/catalogo_repository.py` |
> | 3 | **Lookup** | ⭐ **non è un endpoint**: è **una riga** in `_REL_CONSENTITE` (`core/db/dbops_repository.py`, la whitelist del lookup generico) + `<LookupSelect rel="config.modi_approvvigionamento">` nel drawer — esattamente com'è fatto `config.nature_vendita` | `dbops_repository.py`, `ArticoloDrawer.vue` |
> | 4 | **Commessa** | come scritto sopra. ✅ D-A decisa: il campo è `responsabile_risorsa_umana_id` → `anagrafiche.risorse_umane`. ⚠️ **Serve un lookup di risorse umane**, e oggi l'unico in servizio è `GET /pratiche/operatori/` (per reparto, area `pratiche`): il lookup generico non serve, `risorse_umane` non ha `codice`/`descrizione`. O si libera quello con `skip_area_check` (pattern *lookup cross-dominio* del catalogo BB) o nasce `/anagrafiche/risorse-umane/lookup/` — lo decide il BE; in entrambi i casi envelope `{"results": [...]}` | `commesse_service.py`, drawer commessa |
> | 5 | **Lista ordini (7)** | ✅ davvero niente: `SELECT v.*` in lista e dettaglio | — |
> | 5-bis | **Lista articoli (26)** | ⛔ vedi la voce 2: le righe di `ui.lista_colonna` nascono `attivo=f` e le accende il BE **nello stesso commit** della proiezione | `lista_colonna.csv` + `catalogo_repository.py` |
> | 6 | **Pannello situazione merce** *(mancava del tutto)* | la SELECT su `vw_situazione_merce_ordine` in `vendite_repository` proietta **22 colonne per nome**: `data_consegna_richiesta_cliente`, `data_consegna_confermata` e `giorni_ritardo` vanno aggiunte, e il BB FE `situazioneMerce` deve **renderle** (una colonna «ritardo» nella sezione per riga) — è il posto per cui `giorni_ritardo` esiste | `vendite_repository.py` (≈ r. 4775), `src/vendite/_shared/situazioneMerce/` |
> | 7 | **P-9, se confermata** | `famiglie_service._OBBLIGATORI_CREATE` perde `colonna_billing_account`; il form FE delle famiglie la rende opzionale (§3-bis, censimento) | `famiglie_service.py`, drawer famiglie |
>
> ⚠️ **Un criterio per non scoprirne un'ottava fra sei mesi**: prima di dire che
> una colonna «arriva dalla vista», cercare **`SELECT` con l'asterisco** nel
> repository che la serve. Se la SELECT elenca i nomi, la colonna è un lavoro BE.

⚠️ **Sulla commessa, un fatto che eviterà una ricerca a vuoto: non esiste una
lista configurata `vendite.commesse`.** In `ui.lista_definizione` ci sono
`vendite.commesse_attivita` (id 38, senza vista) e il drill-down di dashboard,
non la commessa. Le tre colonne del Blocco C hanno quindi come sola superficie il
**drawer/API**, finché una lista non verrà configurata — e configurarla è dato,
non un cantiere.

⛔ **Capability solo sul DETTAGLIO**: se serviranno azioni di riga governate, la
sede è il dettaglio, non la lista.

### 5.6 Che cosa NON arriva a BE/FE con questo brief

Niente che riguardi la produzione: **nessun ODL, nessuno stato di copertura,
nessun ciclo di lavorazione, nessun consuntivo**. Se compaiono in una richiesta,
non vengono da qui.

---

## 6. I passi

> ⚠️ La numerazione dei file (`YYYYMMDD-NN`) è **globale per data** e il numero
> libero **scade nel minuto**: si ricontrolla subito prima di salvare, non
> all'inizio del lavoro.

| # | Passo | Fase |
| --- | --- | --- |
| **P-1** | `config.modi_approvvigionamento`: tabella + seed CSV + riga in `fk_index_policy` per la FK che nasce in P-2. 🔴 *2026-09-12*: **niente seed del lock** — `codice_interno` è implicito (§3.2, riquadro); la coppia ATTIVO nasce da `ci_apply` | `00_schema` + `80_data` |
| **P-2** | `catalogo.articoli`: `gestito_a_magazzino` e `lead_time_giorni` in un passo; `modo_approvvigionamento_id` **in due** — 🔴 *2026-09-12*: colonna nullable + FK in `00_schema`, poi in `80_data` **dopo** il seed di P-1: id di `ACQUISTO` risolto per `codice_interno`, backfill, `SET DEFAULT`, `SET NOT NULL` (forma di `20260609-04`, §3.3 riquadro). ✅ default `ACQUISTO` deciso 2026-09-02 | `00_schema` + `80_data` |
| **P-3** | `vendite.ordini_righe` + `vendite.preventivi_righe` + `acquisti.ordini_righe`: le date. ✅ nomi da **D-16** (§2.2), decisa | `00_schema` |
| **P-4** | `vendite.commesse`: `descrizione`, `data_apertura`, `responsabile_risorsa_umana_id` → `anagrafiche.risorse_umane`. ✅ **§4-bis**: `data_apertura` **NOT NULL**, valore iniziale da `data_insert` (deciso 2026-09-02). ✅ *2026-09-12*: bersaglio della FK deciso (**D-A**, §4); + riga in `fk_index_policy`; la coppia ATTIVO nasce da `ci_apply` e si asserisce in P-8, non con DDL | `00_schema` (+ `80_data` per la policy) |
| **P-5** | `fn_push_preventivo_a_ordine` porta avanti la data richiesta (+ toglie il nome morto nel commento). 🔴 *2026-09-12*: la legge dalla **quarta vista** di P-6, non con un `JOIN` suo | `20_code` |
| **P-6** | `catalogo.vw_articoli_dettaglio` + `vendite.vw_ordini_lista` + `vendite.vw_situazione_merce_ordine` + 🔴 `vendite.vw_preventivi_righe_smistabili_ordine` (*2026-09-12*, §5.2). ⚠️ `security_invoker` ri-specificata sulle tre di `vendite`, **non** aggiunta a quella di `catalogo` | `20_code` |
| **P-7** | `ui.lista_colonna`: le righe nuove, append al CSV. 🔴 *2026-09-12*: le tre della lista 26 nascono **`attivo=f`** (§5.3 riquadro); `ordinabile=t` solo se il BE estende la whitelist nello stesso giro | `80_data` |
| **P-8** | pgTAP (§7). 🔴 *2026-09-12*: le righe sono sotto RLS, il trigger «riga spenta» viene da `ci_apply` — vedi il riquadro di §7 | `db/pgtap` |
| **P-9** | ⚠️ **OPZIONALE, da confermare (§3-bis)** — `famiglie_documento.colonna_billing_account` nullable + salto nel guard e nelle due `fn_*_storia_emittente`. 🔴 *2026-09-12*: + `fn_crea_famiglia_documento` (oggi la pretende), + BE/FE (§3-bis censimento) | `00_schema` + `20_code` |

⛔ **L'ordine di fase non è negoziabile**: `00_schema` → `20_code` → `80_data`.
Una `preCondition` di `20_code` **non** deve verificare il *contenuto* di
`80_data`, che gira dopo.

⚠️ **Stato finale `runOnChange: false`** su schema e codice — è vietato e
presidiato in CI (`guardrail_run_on_change.py`); resta lecito solo sul mirror CSV
di `80_data`. E `validCheckSums` **al plurale**: il singolare è una chiave che
Liquibase ignora.

⛔ **Negli YAML si cita il NOME di questo brief**
(`brief-db-modifiche-certe-ciclo-vendita-e-articolo`), **mai il path
`work-in-progress/`**: il documento un giorno si sposterà, e il riferimento deve
sopravvivere al trasloco.

---

## 7. I presidi

| Test | Che cosa prova |
| --- | --- |
| `catalogo/test-articoli-approvvigionamento-v1` | il vocabolario ha i quattro valori; un articolo non può puntare a una riga **spenta**; il default è `ACQUISTO`; `lead_time_giorni` rifiuta il negativo |
| `vendite/test-date-consegna-ordine-v1` | le date si scrivono e si rileggono sulla riga; ⭐ **la data sopravvive al push** preventivo → ordine — provata sul **percorso reale**, chiamando `fn_push_preventivo_a_ordine`, non confrontando due colonne |
| `vendite/test-situazione-merce-ritardo-v1` | `giorni_ritardo` è **NULL** quando `da_spedire` è NULL o zero, ed è valorizzato solo sopra la soglia dell'impegno |

⚠️ **Un `has_column` sulle viste non basta**: prova che la colonna esiste, non
**da dove viene il valore**. Sulle tre viste il test deve confrontare il valore
con la sorgente, altrimenti passa anche se la colonna arriva dal posto sbagliato.

⚠️ **Preambolo obbligatorio** in ogni file (`BEGIN;`, riga di contesto,
`SET CONSTRAINTS ALL IMMEDIATE`), presidiato da
`scripts/guardrail_pgtap_preambolo.py`: senza, il file diventa verde **per
sottrazione**.

⚠️ E la suite ha **rossi preesistenti**: si confronta con
`scripts/pgtap-baseline.sh`, non si attribuisce un rosso a questo lavoro senza
averlo verificato.

> 🔴 **Tre cose cambiate sotto i tre test, dal 2026-09-12:**
>
> * **le righe sono sotto RLS** (`20260909-30`/`-35`): `test-date-consegna-ordine-v1`
>   scrive su `preventivi_righe` e `ordini_righe` come l'applicazione, quindi il
>   preventivo di fixture deve avere un emittente **nella whitelist del contesto
>   del test** — la forma è quella già in uso (memoria *fixture preventivi:
>   `emittente_fiscale_id` + `iva_id`*) e il BA si crea con l'helper **rev 38
>   senza `RETURNING`** (memoria *BA come operatore non di default*), altrimenti
>   la riga sparisce nella policy prima ancora di arrivare al push;
> * **«un articolo non può puntare a una riga spenta» lo fa un trigger di
>   `ci_apply`**, non un changeSet (§3.2, riquadro): il test lo asserisce
>   correttamente, ma sa che su un database senza `--ci-apply` è rosso per
>   assenza. Va scritto nel commento del test, o il primo rosso in CI verrà
>   inseguito nel posto sbagliato;
> * il presidio di `security_invoker` sulle viste è ora **globale e sul merito**
>   (`rls/test-rls-viste-security-invoker.sql`): i tre test qui sopra non ne
>   scrivono una copia, e il «`has_column` non basta» resta l'unica cosa loro.

### ⛔ Il presidio che manca, e riguarda ciò che consegna QUESTO brief

⭐ **Aggiunto il 2026-09-01.** Le tre analisi della giornata hanno fatto uscire
**quattro volte** lo stesso difetto: *una cosa esiste, è costruita bene, e non è
collegata a niente* — il guard tipizzato montato su zero tabelle, due policy RLS
senza `ENABLE`, `magazzino.causali.ambito_causale_id` vuota in **tutte e dieci** le
righe seminate, `config.ambiti` con zero FK entranti. **Nessuna produce un rosso.**

🔴 **Questo brief consegna due candidati alla stessa classe**, e i test della
tabella sopra non li intercettano:

| Deliverable | Perché è un candidato | Il presidio che serve |
| --- | --- | --- |
| `config.modi_approvvigionamento` | è un **catalogo nuovo**: se domani nessuna vista, nessuna funzione e nessun consumatore lo legge, è vivo e inerte esattamente come `config.ambiti` | un registro che elenca i cataloghi **senza FK entranti** — e la FK da `catalogo.articoli` c'è, quindi questo passa: il presidio serve a **provarlo**, non a sperarlo |
| `articoli.gestito_a_magazzino` | `NOT NULL DEFAULT false` ⇒ al rilascio **tutte le righe sono `false`**. La §3.3 lo dice già («la merce va marcata: è un lavoro di dato») ma lo lascia come **nota** | ⛔ una nota non è un presidio: serve un **registro che deve calare** — «articoli con `gestito_a_magazzino = true`», che al rilascio vale zero e deve smettere di valerlo |

⛔ **Attenzione alla POLARITÀ del secondo registro, o nasce con lo stampo
sbagliato.** Le otto viste `dbops` esistenti — e le tre proposte dall'analisi
acquisto — devono restare **vuote**: una riga è un difetto. Questa no: «articoli
con `gestito_a_magazzino = true`» deve **riempirsi**, e lo zero è l'allarme.
⇒ Non è un registro del debito «che deve calare»: è un **controllo di prontezza**,
e va scritto come tale. Chi lo implementasse copiando lo stampo degli altri otto
otterrebbe un presidio verde esattamente nel momento in cui il problema c'è.

⚠️ **Il secondo è il più insidioso**, ed è la ragione per cui questa sezione
esiste: la colonna sarà presente, popolata, con il default fail-safe **giusto** —
e `magazzino` la leggerà trovando che nessun articolo movimenta giacenza. Nessun
errore, nessun test rosso, e un dominio intero che si comporta come se non ci
fosse merce. È **la stessa forma** di `ambito_causale_id`: seminata, valorizzata a
vuoto, e nessuno se n'è accorto per mesi.

⇒ Il presidio **generale** della classe (tre viste in `dbops` che devono restare
vuote — funzioni trigger montate da nessuno, policy su tabelle senza RLS attiva,
cataloghi orfani) è proposto in
[analisi-simmetria-ordini-acquisto §9-bis](analisi-simmetria-ordini-acquisto.md).
⚠️ **È un cantiere di `dbops`, non di questo brief**: qui resta l'obbligo del
registro su `gestito_a_magazzino`, che è nostro e non si può delegare a un cantiere
che forse non parte.

> ⭐ **Dal 2026-09-10 la sede ESISTE, e cambia la forma del registro
> (aggiornamento del 2026-09-12).** `dbops.presidi` è il **catalogo delle viste
> di presidio** — 37 righe al 12-09, non più «otto» — con una `natura`
> (`ZERO` / `REGISTRO` / `LAVORAZIONE` / `CANCELLO` / `INVENTARIO`), una
> `cadenza`, e il digest notturno che le legge
> ([brief-db-un-destinatario-per-i-presidi](../work-done/brief-db-un-destinatario-per-i-presidi.md)).
> ⇒ Il registro di prontezza su `gestito_a_magazzino` **non nasce fuori dal
> catalogo**: è una vista più **una riga in `presidi.csv`**, o il digest non la
> legge e siamo daccapo — *«esiste e non è collegata a niente»* per la quinta
> volta.
>
> ⭐ **E la POLARITÀ ha una forma dichiarabile, non un'eccezione da inventare.**
> Il catalogo non conta «righe = allarme» e basta: ha `colonna_stato` +
> `stato_atteso`, e l'allarme è *«diverso dallo stato atteso»*. ⇒ La vista
> risponde con **una riga sola** — `stato = 'MARCATI'` se esiste almeno un
> articolo con `gestito_a_magazzino = true`, altrimenti `'NESSUNO_MARCATO'` — e
> si iscrive come natura `ZERO`, `colonna_stato = stato`, `stato_atteso =
> 'MARCATI'`. Lo zero suona, il pieno tace: esattamente il verso che questa
> sezione chiedeva, con lo stampo che gli altri usano. ⛔ Non una natura nuova
> per un caso solo.
>
> ⚠️ Le tre viste del §9-bis dell'analisi acquisto **non sono ancora nate**
> (verificato sul catalogo): quando nasceranno, la loro sede è la stessa.

---

## 8. Che cosa NON entra, e dove sta

| Voce | Dove vive | Perché non è qui |
| --- | --- | --- |
| Stato di **copertura** della riga d'ordine | analisi commessa §8.3 | se ODL e ordine d'acquisto saranno agganciati alla riga è **derivabile**: una colonna sarebbe una seconda verità. Va fatta vista, dopo la §7 |
| `uom_id` del componente e **sfrido** sulla BoM | analisi commessa §8.4 | dipendono dal fatto che la distinta di produzione sia o no `articoli_componenti`, che è **immutabile** per un altro motivo |
| **Consuntivo**, ODL, ciclo di lavorazione | analisi commessa §6 e §7 | sono **strutture**, non colonne, e stanno di là dalla decisione |
| Cliente proprio, budget, data di chiusura prevista sulla commessa | analisi commessa §8.5 ⏸️ | dipendono dalla §7 |
| `vw_giacenza` (il segno) e le **causali che mancano** | ⭐ *aggiornato 2026-09-02*: hanno una sede loro, [analisi-db-magazzino-carico-e-scarico](analisi-db-magazzino-carico-e-scarico.md) §4, §3 e §7 | ⚠️ **il fatto è certo, la forma è una decisione**: che vadano toccati non è in dubbio, *come* sì. ✅ *2026-09-02*: la **scelta sul verso è presa** (sta nella quantità), quindi `vw_giacenza` **resta com'è**; di lei resta da scrivere il `COMMENT` che dice perché. 🔴 *2026-09-12*: le causali mancanti sono **quattro**, non una (versamento, reso a fornitore, carico da reso cliente, inventario iniziale — là §3), e con M-2 chiusa ciascuna costa **una riga di seed**: resta `magazzino` perché la primitiva che le legge non esiste ancora, non perché sia indecisa |
| `uq_mag_movimenti_docref` | analisi magazzino D-4, con la risposta in [carico e scarico **§6**](analisi-db-magazzino-carico-e-scarico.md) — 🔴 *fino al 2026-09-12 questa cella diceva «§8-quater», sezione traslocata il 02-09: era lo stesso riferimento morto che la revisione incrociata aveva sanato negli altri documenti* | ⭐ la forma ora **c'è** — identità `(sorgente, chiave, verbo, discriminante fisico)`, colonna e non tabella. Resta fuori di qui perché è `magazzino` e perché la D-4 è di Tid, non perché manchi il disegno |
| `causali.ambito_causale_id` | analisi magazzino D-8 | ⭐ *aggiornato*: gli appunti di revisione lo chiudono («valorizzare», + `NOT NULL` perché l'undicesima causale non rinasca vuota). ⇒ smetterà di essere una decisione, ma resta `magazzino`: andrà in un piano suo, non qui |
| Chi scrive un movimento di magazzino | analisi magazzino D-1 | la forma del riferimento al documento è la prima decisione aperta. ⚠️ *2026-09-12*: **chi** scrive è deciso (M-2, la primitiva guidata da due cataloghi); resta aperto solo **come dichiara l'origine** |
| 🔴 **`catalogo.articoli.requires_lotto`** *(voce nuova, 2026-09-12)* | [carico e scarico §7-quater](analisi-db-magazzino-carico-e-scarico.md), M-5 — **decisa** il 02-09 | ⚠️ **tocca `catalogo.articoli`, cioè P-2, ed è certa quanto le tre del Blocco B** (boolean `NOT NULL DEFAULT false`, decide l'articolo e non la causale). Non entra in P-2 per una ragione sola, ed è quella scritta nell'analisi: *«va aggiunta insieme alla tabella dei lotti, o la decisione non ha chi la governa»* — una colonna senza il suo lettore è la classe del §7. ⇒ **Seconda occasione dichiarata** in cui `articoli` verrà toccata. ✅ **DECISO (Tid, 2026-09-12, D-B): aspetta i lotti** — non entra in P-2 |
| **Prezzo di riferimento del fornitore** sull'articolo | analisi acquisto §9, D-8 | ⚠️ **tocca `catalogo.articoli`, cioè P-2.** Le due forme in campo (una colonna sull'articolo *oppure* la tabella `catalogo.articoli_fornitori`) sono una decisione aperta ⇒ chi esegue P-2 sappia che quella tabella **potrebbe essere toccata una seconda volta**, e non consideri P-2 l'ultimo intervento su di lei |
| **Discriminante di ciclo** sugli stati (`stati_doc_ordini`, `stati_doc_ddt`) | analisi acquisto §7, D-3 | il fatto è certo — le due tabelle sono **condivise con `acquisti`** e non hanno modo di dire a quale ciclo appartiene uno stato. ✅ *2026-09-12*: la **forma è confermata** (Tid, 02-09): **satellite** `config.stati_doc_ordini_ambiti` + gemello DDT, `ambito` come CHECK a due valori. Resta fuori di qui perché è il Lotto 0 del cantiere acquisto — e perché **D-17** lo lega alla vista di M-3, non a questo brief |
| Ancora doppia degli **indirizzi documento** | analisi acquisto §7-bis, D-6b | tocca un BB usato da **5 domini di vendita**. ✅ *2026-09-12*: **decisa A** (Tid, 02-09) — l'ancora diventa una mappa `tipo_indirizzo → colonna` sul BB. ⚠️ Non è DDL: è backend, e resta del cantiere acquisto |
| Partita di acquisto, reso a fornitore, **chiusura del ramo credito** | analisi acquisto §8, D-14 | è il cantiere acquisto, e poggia su un motore di stato che non esiste |

### ⭐ Una convenzione che invece entra, e non costa una riga di DDL

L'analisi acquisto ha stabilito una regola che **vale per tutto il progetto** e che
finora non era scritta da nessuna parte:

> `numero` (+ `serie`, `anno`) è **sempre e solo il numero NOSTRO**, quello che
> assegna un registro. Il numero della **controparte** ha un nome proprio e non
> occupa mai quella colonna.

⚠️ **Perché riguarda anche la vendita**, benché il caso sia emerso sugli acquisti:
il «vostro riferimento» del cliente su un ordine di vendita è lo stesso concetto,
oggi non ce l'ha nessun documento, e il giorno che servirà **la tentazione sarà di
metterlo dove c'è posto**. Su `acquisti.ddt` quella tentazione ha già prodotto il
danno: `numero` **è** il numero del fornitore, e `famiglie_documento.colonna_numero`
puntata lì lo sovrascriverebbe.

⛔ Qui non si aggiunge nessuna colonna — nessuno l'ha chiesta. Si scrive la regola,
perché il costo di scriverla adesso è zero e quello di scoprirla dopo è una
migrazione.

---

### ⚠️ Revisione del 2026-09-01 (sera) — il filtro ha tenuto

Gli appunti di revisione sulle due analisi hanno chiuso o proposto **D-1** (ledger a
catalogo), **D-4** (l'indice si toglie, la regola passa su una chiave
dell'operazione), **D-6** (sciolta: il «movimento senza documento» non è un caso
reale), **D-7** (assorbita) e **D-8**; hanno ristretto **D-2/D-3** e rinviato
**D-5**.

⭐ **Ripassati i tre blocchi voce per voce: non cambia niente.** Nessuna colonna,
nessuna nullabilità, nessun default, nessuna vista, nessuna riga di lista.

Non è una coincidenza fortunata, ed è la prova che il §1 valeva la pena: le voci
di questo brief stanno su `vendite` e `catalogo`, le decisioni stanno su
`magazzino`. Muovendo le seconde, le prime non si spostano.

⇒ Della revisione è cambiata **solo la §8**, e solo nello *stato* di due voci
escluse: la loro forma adesso esiste. Restano fuori perché sono di un altro
dominio, non perché siano indecise.

---

## 9. Riferimenti

* [analisi-db-commessa-e-produzione-predisposizione.md](analisi-db-commessa-e-produzione-predisposizione.md)
  — perché il punto di fermata non è la commessa, e la §8 da cui questo brief è estratto
* [analisi-db-magazzino-aggancio-documento-e-produzione.md](analisi-db-magazzino-aggancio-documento-e-produzione.md)
  — le decisioni D-1 → D-9, nessuna delle quali tocca questo brief
* [analisi-db-magazzino-carico-e-scarico.md](analisi-db-magazzino-carico-e-scarico.md)
  — *(aggiunta il 2026-09-12)* M-1 → M-9, chiuse fra il 02-09 e il 04-09: sono
  loro a fare di questo brief un **prerequisito** (§1, riquadro) e a chiedere
  `requires_lotto` (§8)
* [analisi-simmetria-ordini-acquisto.md](analisi-simmetria-ordini-acquisto.md)
  — terza origine (2026-09-01): il §3-bis viene dal suo §6, la convenzione del §8
  dal suo §6 «I DUE numeri», il presidio del §7 dal suo §9-bis. ⚠️ Le sue
  decisioni aperte (D-2, D-6b, D-13) non toccano questo brief; **D-8 sì**, di
  striscio, perché insiste su `catalogo.articoli`
* Convenzioni SQL (naming, §6c sul `codice_interno`): `docs/it/linee-guida-sql.md`
* Standard liste e `<ListaConfigurabile>`: `docs/it/dev/frontend/frontend-standards.md`
* Il residuo del nome morto in `fn_push_preventivo_a_ordine`:
  [brief-db-prefisso-sul-registro-e-allineamento-contatori.md](../work-done/brief-db-prefisso-sul-registro-e-allineamento-contatori.md) §6.3
  — ✅ ancora lì il 2026-09-12 (riga 141 del corpo): P-5 resta l'occasione

---

## 10. Verifica del 2026-09-12 — che cosa è cambiato sotto il brief

> Il brief è stato riletto **contro il database vivo** (doc auto-gen), contro i
> repository del backend e contro ciò che è entrato in esercizio fra il 01-09 e
> il 12-09 (undici giorni, ~120 PR). ⭐ **Il metodo che ha trovato i difetti**: per
> ogni affermazione operativa, aprire l'oggetto che nomina — non il documento che
> lo descrive. Sette dei dodici punti erano **già falsi il giorno in cui sono
> stati scritti**; cinque sono diventati falsi dopo.

### 10.1 I tre blocchi reggono

Nessuna colonna, tipo, nullabilità, default o vista dichiarata nei Blocchi A, B, C
cambia. Le decisioni di Tid del 02-09 (nomi D-16, default `ACQUISTO`,
`data_apertura` da `data_insert`) restano. Il filtro della §1 ha tenuto anche
contro le otto decisioni M-* chiuse dopo: nessuna **modifica** una voce di qui
— tre la **leggono** (§1, riquadro), ed è ciò che alza la priorità del brief.

### 10.2 I dodici punti, e dove stanno le correzioni

| # | Che cosa diceva il brief | Che cosa è vero | Gravità | Dove |
| --- | --- | --- | --- | --- |
| 1 | il lock su `codice_interno` si semina in `automation_lock_columns` | è **implicito**: nessuna riga | seed inutile | §3.2 |
| 2 | *(taceva)* | la FK articoli→vocabolario genera la coppia ATTIVO a `ci_apply`; il pgTAP «riga spenta» dipende da lei | test rosso in CI senza saperlo | §3.2, §7 |
| 3 | `NOT NULL DEFAULT ACQUISTO` in un passo, «la sequenza è cerimonia» | la sequenza è imposta dalla **timeline** `00_schema → 80_data`: migrate morto su dev e in CI | 🔴 **migrate fallito** | §3.3, §4-bis, P-2 |
| 4 | P-9 tocca tre oggetti, «cinque righe» | i lettori sono **sette** più BE e FE; `fn_crea_famiglia_documento` la pretende | P-9 a metà | §3-bis |
| 5 | la FK del responsabile genera un guard `BEFORE ROW` da verificare | `soggetti_ruoli` non ha `attivo`: **niente** nasce; e il generato sul figlio è AFTER | premessa falsa | §4 |
| 6 | *(taceva)* | il progetto referenzia le persone interne con `risorsa_umana_id` (tre tabelle di `pratiche`) | **decisione** D-A | §4, §10.3 |
| 7 | `security_invoker` «reloption di tutte e tre» | `vw_articoli_dettaglio` non ce l'ha, e non deve; il presidio è sul criterio dal 07-09 | doc falsa | §5.2 |
| 8 | *(taceva)* | il push legge da `vw_preventivi_righe_smistabili_ordine`, proiezione esplicita: **quarta vista** | P-5 senza sorgente | §5.2, P-6 |
| 9 | «niente da fare per la lista» | vero per ordini (`SELECT v.*`), **falso per articoli** (49 nomi in tupla) e per il pannello situazione merce (22 nomi) | 🔴 **colonna vuota, nessun rosso** | §5.3, §5.5 |
| 10 | chiavi i18n `catalogo.articoli.*`, `vendite.ordini_righe.*`, `config.modi_approvvigionamento.*` | i vicini sono `catalogo.col_*` e `vendite.ordini.riga_*`; il vocabolario non ha chiavi (mostra `descrizione`) | forma — **decisione** D-C | §5.4 |
| 11 | il registro di prontezza è «un cantiere di `dbops` che forse non parte» | `dbops.presidi` esiste dal 10-09; la polarità si dichiara con `stato_atteso` | forma del presidio | §7 |
| 12 | §8: «§8-quater», D-3 e D-6b «da confermare», una causale mancante, D-1 → D-8 | riferimento morto; D-3 e D-6b **chiuse** il 02-09; le causali sono quattro; D-9 esiste; `requires_lotto` decisa (M-5) | stati stantii | §1, §8, §9 |

⚠️ **E la RLS sulle righe** (`20260909-30`/`-35`) non è un tredicesimo punto: non
cambia una riga del piano, cambia come si scrivono le fixture di P-8 (§7,
riquadro).

### 10.3 Le tre decisioni — ✅ tutte prese da Tid il 2026-09-12

| # | Domanda | Decisione | Dove è applicata |
| --- | --- | --- | --- |
| **D-A** | Il responsabile della commessa punta a `anagrafiche.soggetti_ruoli` (com'era scritto) o a `anagrafiche.risorse_umane` (com'è fatto in `pratiche`)? | ✅ **`risorse_umane`** — `responsabile_risorsa_umana_id`. Il block ATTIVO che ne nasce è il quarto della sua specie su quella tabella, dichiarato | §4 (tabella + riquadro), §5.5 voce 4, P-4 |
| **D-B** | `catalogo.articoli.requires_lotto` (M-5, decisa) entra in P-2 o aspetta la tabella dei lotti? | ✅ **aspetta i lotti**: una colonna senza lettore è la classe del §7 | §8 |
| **D-C** | Le chiavi i18n seguono i vicini (`catalogo.col_*`, `vendite.ordini.riga_*`) o la regola `<area>.<entità>.*`? | ✅ **i vicini** — elenco definitivo nel riquadro di §5.4 (tredici chiavi, tre in più per il drawer commessa) | §5.4 |

⛔ **P-9 resta OPZIONALE** e non è fra le tre: la domanda è la stessa del 01-09,
con un censimento più onesto (§3-bis).

⭐ **Con le tre decisioni prese il brief è di nuovo ESEGUIBILE**: il piano è la
§6 (P-1 → P-8, P-9 se confermata), i presidi la §7, e nessuna voce aspetta
qualcuno. ⚠️ L'osservazione su `docs/it/dev/api.md` («le righe non hanno la
RLS», falso dal 09-09) è **fuori dal brief**: Tid la passa al BE.

---

## 11. Registro delle revisioni

| Data | Cosa |
| --- | --- |
| 2026-09-01 | Prima stesura dalle due analisi commessa e magazzino; a sera la terza origine (analisi acquisto) e la §8 aggiornata dagli appunti di revisione |
| 2026-09-02 | Decisioni di Tid: nomi D-16 (§2.2), default `ACQUISTO` e `data_apertura` da `data_insert` (§4-bis riscritta), correzione del fatto su `format('%I', NULL)` (§3-bis) |
| 2026-09-04 | Riferimenti aggiornati alla nascita di [analisi-db-magazzino-carico-e-scarico](analisi-db-magazzino-carico-e-scarico.md) |
| 2026-09-12 | 🔴 **Verifica contro il DB vivo e le implementazioni del 01→12-09**: dodici punti corretti in loco con nota datata (§10.2), tre decisioni aperte a Tid (§10.3). I tre blocchi non cambiano. ⭐ Il brief passa da «parallelo a magazzino» a **prerequisito** del prossimo cantiere (§1) |
| 2026-09-12 | ✅ **Le tre decisioni prese da Tid nella stessa sessione**: D-A `responsabile_risorsa_umana_id → risorse_umane` (§4, P-4, §5.5); D-B `requires_lotto` aspetta i lotti (§8); D-C chiavi i18n dei vicini, elenco definitivo di tredici chiavi (§5.4). Il brief è eseguibile: piano in §6, presidi in §7 |
