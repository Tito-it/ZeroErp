# Brief DB — l'errore porta un bersaglio, non un nome

> **Cos'è.** Il piano per far sì che un errore, oltre a *dire* cosa è successo,
> dica **su quale cosa** — in una forma che l'interfaccia possa trasformare in un
> gesto («vai lì») e che chi diagnostica possa leggere come coordinata esatta.
>
> **Perimetro: DB per primo** (decisione di Tid, 2026-08-22). La convenzione
> nasce dove l'errore viene sollevato; il consumo lato BE/FE è dichiarato in §7
> ma **non** è questo brief.
>
> ⛔ **Di questo brief non è stato applicato niente**: nessuna migrazione,
> nessun CSV. Il piano, con i changeSet numerati, è il §6. ⚠️ **Il catalogo dei
> tipi invece esiste**, ed è stato applicato dall'altro cantiere il 2026-08-22:
> è il prerequisito, non un passo di qui.
>
> ✅ **Ed è SCRIVIBILE dal quinto giro (2026-08-22): le cinque domande che il
> quarto aveva aperto sono tutte chiuse** — §8, `Q-A`…`Q-E`. In breve: il
> bersaglio esce dal `RAISE` su **una casella strutturata nuova**, l'appunto si
> chiama **`bersaglio`**, la chiave dell'entità **la dichiara il catalogo**, il
> catalogo **cresce col roll-out** una voce per volta, e il bersaglio si mette
> **solo sugli errori rimediabili, mai sui `TECNICO`**.
>
> ⚠️ **Il L4 dell'altro cantiere è stato applicato il 2026-08-22** (changeSet
> 53-60, più 61-62 del suo L2): la colonna che il `T-1d` chiede a
> `config.tipi_entita` è quindi **un changeSet nuovo**, non più una riga
> aggiunta a una DDL non ancora eseguita.
>
> **Origine.** Collaudo della nota di credito resi, 2026-08-22. Il messaggio
> **937** dice all'operatore *«Non si può numerare il documento 835»*: una chiave
> interna dentro una frase destinata a una persona. Da lì la domanda di Tid — se
> convenisse scrivere `schema.tabella.id` (`anagrafiche.soggetti.100`) invece di
> un id nudo — e il ragionamento che ne è uscito, che è il §1.
>
> ⛔ **COSA NON SI GESTISCE PIÙ QUI (2026-08-22).** I passi **T-1** (il catalogo
> dei tipi di entità) e **T-1b** (l'adozione da parte di `event_log`) sono stati
> **assorbiti** da
> [brief-db-event-log-scope-e-riga-parlante.md](brief-db-event-log-scope-e-riga-parlante.md)
> — §3.7, decisione **D-17**, lotto **L4**. Decidevano su `event_log.entity_type`,
> che è **la tabella di quel cantiere**, e quel cantiere aveva già applicato una
> scelta diversa. Qui restano come **dipendenza**, non come passi: §3 e §5.1.
> ⭐ Tutto il resto — i tre strati, la forma `target`, il pilota 937, il roll-out,
> le consegne BE/FE — **resta di questo brief**.
>
> **Cosa NON è.** Non è
> [brief-db-segnaposti-messaggi-errore.md](../work-done/brief-db-segnaposti-messaggi-errore.md)
> (chiuso il 18/08): quello riguarda i `%s` che restano letterali o che fanno
> fallire il messaggio. Qui il contenitore funziona: si discute **cosa metterci
> dentro**. ⚠️ I due si toccano in un punto solo, ed è una trappola: §5.3.

---

## 1. Perché «id o frase umana» non ha una risposta

La domanda presuppone che l'errore sia **testo**. Finché lo è, ogni scelta è un
compromesso fra due lettori che non hanno bisogno della stessa cosa:

| Chi | Quando | Cosa gli serve |
| --- | --- | --- |
| Operatore, sul momento | è appena successo | **cosa faccio adesso** — non identificare una riga |
| Operatore, cinque minuti dopo | sta rimediando | **arrivare** a quel record |
| Chi diagnostica | ore o giorni dopo | coordinate esatte, più la sequenza |

Il secondo è quello che conta, ed è la chiave del disegno: all'operatore non
serve *il nome* del record — gli serve **andarci**. Un identificativo dentro una
frase, per quanto umano, resta una cosa da ricopiare a mano in un campo di
ricerca.

**Le due strade ovvie, e perché nessuna delle due basta:**

| Strada | Perché non regge |
| --- | --- |
| **Identificativo umano nella frase** | spesso **non esiste**: sul 937 il documento un numero non ce l'ha, ed è tutta la ragione dell'errore. È ambiguo (due clienti omonimi) e invecchia — la frase si compone al sollevamento, il nome può cambiare dopo |
| **`schema.tabella.id` nella frase** | per l'operatore è **più** tecnico, non meno: è l'opposto dell'obiettivo. E fa uscire i nomi delle tabelle su superfici che non sono solo interne (§4.2) |

---

## 2. La soluzione — tre strati, uno per lettore

Due dei tre esistono già e non si toccano.

| Strato | Per chi | Cosa dice | Oggi |
| --- | --- | --- | --- |
| `messaggio` | operatore | cosa è successo, in italiano, **senza identificativi** | c'è (`config.messaggi_errore.messaggio`) |
| `soluzione` | operatore | cosa fare — sul 937 è già scritta bene | c'è, poco sfruttata a video |
| **bersaglio** | interfaccia **e** diagnosi | `{ tipo, id }` | 🔴 **manca** |

Il frontend riceve il bersaglio e disegna **un gesto**, non una lettura: *«Vai al
documento»*. L'operatore non legge nessun id e nessuno schema. Chi diagnostica
legge il bersaglio nel log e ha la coordinata esatta.

⭐ **Non c'è più il compromesso**, perché i due lettori smettono di condividere
lo stesso canale.

---

## 3. Il `tipo` è un'entità logica, non una tabella

~~E il vocabolario **esiste già**: `vendite.event_log.entity_type` usa
`LOTTO | FATTURA | COMMESSA | TASK_RUN`.~~

⛔ **Rettifica del 2026-08-22, e non è un dettaglio.** Quel vocabolario non è più
quello: il Passo 0 dell'osservabilità è stato applicato in giornata e ha
**espulso `TASK_RUN`** da `event_log` (sua decisione D-3, gli eventi di un giro
senza padrone sono tornati su `commesse_push_log`). Oggi la colonna ammette
`LOTTO | COMMESSA | FATTURA`.

⭐ **E la ragione dell'espulsione è ciò che tiene insieme i due cantieri**: nel
giornale un tipo entra solo se **l'emittente è derivabile** dall'entità, perché è
quello a decidere chi vede la riga. Un giro non ha padrone, quindi non entra.

> **I due vocabolari non sono lo stesso insieme.** Quello del **giornale** è
> selezionato da *«l'emittente dev'essere derivabile»*; quello del **bersaglio**
> da *«il frontend ha una rotta per arrivarci»* — e comprende benissimo un
> `TASK_RUN`, un `SOGGETTO`, un `DDT`. Il giornale è un **sottoinsieme proprio**
> del bersaglio.

⚠️ Un catalogo tagliato sui soli tipi del giornale renderebbe il bersaglio
inutilizzabile su metà del suo caso d'uso; due cataloghi separati sarebbero la
stessa nozione governata in due modi. La soluzione — **un catalogo, due letture**,
distinte dalla colonna `modo_risoluzione_emittente` — è nel §3.7 dell'altro brief.

Riusarlo vale più di quanto sembri: significa **una tabella di rotte sola** —
«portami a questa cosa» diventa una funzione unica, condivisa fra il bersaglio
di un errore e la futura timeline per entità
([analisi-osservabilita-log.md](analisi-osservabilita-log.md), Passo A). Se il
bersaglio portasse il nome della tabella, servirebbe una seconda mappa
tabella → schermata: la stessa conoscenza in due posti, cioè il modo in cui
divergono.

~~⚠️ **Oggi quel vocabolario non è un vocabolario**: `entity_type` è `text`
libero, senza CHECK né catalogo.~~

✅ **Non è più vero dal 2026-08-22 (allineamento del quinto giro).** Il catalogo
`config.tipi_entita` è **applicato** e `vendite.event_log.entity_type` è una **FK
verso di lui** (`fk_event_log_tipo_entita`, `ON UPDATE CASCADE`); il `CHECK`
intermedio è stato tolto nello stesso passaggio. ⭐ **Il prerequisito di questo
brief quindi c'è**: il `tipo` ha un vocabolario, e resta da dargli la chiave
(§5.1, T-1d) e i tipi che serviranno al roll-out, uno per volta (T-1c).

> ✅ **DECISO (Tid, 2026-08-22): catalogo chiuso, e `event_log` lo adotta.**
> Non solo il bersaglio: la stessa nozione — *«che cosa è questa entità»* —
> governata in due modi sarebbe peggio di non governarla affatto. `entity_type`
> smette di essere `text` libero e punta allo stesso catalogo.
>
> ➡️ **La decisione resta valida e non si tocca. Cambia solo DOVE vive:**
> il catalogo si costruisce nel brief `event-log-scope-e-riga-parlante`
> (**D-17**, §3.7, lotto **L4**), perché è là che vive la colonna che lo adotta.
> Qui è un **prerequisito da consumare**, non un passo da eseguire.

⚠️ ~~**Due avvertenze sull'adozione**, entrambe da verificare **prima** di posare
il vincolo:~~ ✅ **Entrambe risolte il 2026-08-22 nell'altro cantiere**, e vale
la pena leggere come: la prima decidendo di **azzerare** `event_log` (sua D-4,
`TRUNCATE` autorizzato), la seconda **arrivando primi** — il Passo 0 è stato
applicato in giornata, quindi non c'è nessun apply da coordinare: c'è una
correzione in avanti da scrivere (il loro **L4**). Il testo resta perché la
seconda avvertenza aveva ragione, e il coordinamento è mancato lo stesso.

* le righe già scritte in `event_log` vanno controllate contro il catalogo: un
  CHECK/FK su valori storici fuori vocabolario non si applica. ⚠️ Il valore di
  quelle righe è comunque discutibile (§0-bis di
  [analisi-osservabilita-log.md](analisi-osservabilita-log.md)), e su quel
  cantiere è già in discussione se azzerare la tabella: **decidere lì, non qui**;
* 🔴 **`event_log` è toccato anche dal Passo 0** di quel piano (colonna
  emittente + RLS + `correlation_id` + `actor` + `entity_id` reale). Sono
  modifiche allo stesso oggetto: **un apply solo**, o si riapre due volte la
  stessa tabella e la stessa funzione di scrittura. Chi arriva secondo eredita
  il lavoro del primo — vedi **T-1b**.

---

## 4. Dove vive il bersaglio

### 4.1 Il canale esiste ed è già in servizio — ⚠️ **ma solo verso il log**

> 🔴 **RETTIFICA DEL 2026-08-22 (quarto giro), ed è il rilievo più grosso di
> questo brief.** La frase in fondo a questo paragrafo — *«non serve macchina
> nuova, serve una convenzione»* — è vera per **un lettore su due**. Il contesto
> arriva a chi diagnostica; **al frontend non arriva affatto**, e il gesto del §2
> è tutto lì. Il perché è in §4.4, che è nuovo e va letto prima di scrivere
> qualunque changeSet.

`script.fn_log_and_raise_error` ha **già** il parametro del contesto in firma:

```sql
fn_log_and_raise_error(p_area text, p_function_name text, p_error_code text,
                       p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
```

`p_context` finisce in `dbops.error_log.context` (jsonb, NOT NULL, default
`'{}'`), ed è già valorizzato dalla quasi totalità dei punti di sollevamento,
nella forma libera:

```sql
jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id)
jsonb_build_object('fattura_id', p_fattura_id)
```

✅ **Misurato il 2026-08-22 sui CORPI DELLE FUNZIONI VIVE** (`pg_proc.prosrc`,
non le righe di log — vedi il riquadro sotto), e la premessa regge:

| Sui **1.093** punti di sollevamento vivi | |
| --- | ---: |
| valorizzano un contesto `jsonb_build_object` | **1.054** (96%) |
| portano già almeno una chiave `<qualcosa>_id` | **717** (66% — è un *minimo*: la misura guarda i primi 255 caratteri della chiamata) |

Le chiavi più scritte sono `lotto_id`, `fattura_id`, `commessa_id`,
`articolo_id`, `preventivo_id`.

⭐ **È la stessa scoperta** che l'08/08 ha fatto viaggiare `parametro` sul canale
`COLUMN` coprendo *«217 dei 380 punti senza toccarne nessuno»*: la convenzione
del bersaglio, in buona parte, **è già scritta nel codice** e non è mai stata
trasmessa. Vedi il **T-5b** in §5.1.

> ⚠️ **Nota di metodo, e vale per tutto il brief.** Le misure qui sopra sono sul
> **codice** — quante funzioni *scrivono* quella chiave — non sulle righe di
> `dbops.error_log`. È una distinzione che cambia la conclusione, non lo stile:
> `error_log` è un registro di **sviluppo**, senza recinto fra la suite di test
> e l'esercizio, e i suoi conteggi non dicono né quanto un caso sia frequente né
> quanto un difetto sia grave. Servono, al più, come **eco** di ciò che il
> codice già fa. *(Regola di Tid, ribadita il 2026-08-22.)*

**Non serve macchina nuova per il LOG: serve una convenzione.**
⛔ **Per il frontend serve invece un canale che oggi non esiste — §4.4.**

### 4.2 La forma proposta

Chiave **annidata**, non due chiavi piatte, per non collidere con le chiavi
libere già in uso (`parametro`, `valore`, `fattura_id`, …) e per essere
riconoscibile da un presidio con un solo predicato.

> 🔴 **RETTIFICA DEL 2026-08-22 (quarto giro): il nome `target` COLLIDE, ed è
> già in servizio con un altro significato.** Misurato:
>
> **La misura è sul codice**: **16 punti di sollevamento in 6 file** di `20_code`
> scrivono `'target'` dentro il proprio contesto — fra questi
> `fn_apply_chiusura_scadenze`, `fn_ensure_storico_table` e i due trigger di
> dispatch delle surrogate di `config.parameters`.
>
> ⛔ **E il valore che ci mettono è esattamente ciò che questo paragrafo vieta**:
> `config.tipi_soggetto_dettaglio.codice_interno`, `vendite.contratti` — cioè
> **schema.tabella**, come **stringa**. Quindi il predicato unico non esiste (una
> stringa e un array sotto la stessa chiave), il presidio **T-4** dovrebbe
> distinguere due forme legittime, e chi un domani leggesse `context->'target'`
> ne troverebbe una che è il nome di una tabella.
>
> ⚠️ Che poi in `dbops.error_log` ci siano 1.343 righe con quella chiave **non
> aggiunge niente**: è l'eco di quei 16 punti su un database di sviluppo, e non
> misura né la frequenza né la gravità. Il difetto è che **due significati
> condividono un nome**, e lo si vede leggendo il codice.
>
> ✅ **DECISO (Tid, 2026-08-22): la chiave è `bersaglio`.** Zero collisioni
> (verificato), ed è la lingua delle chiavi che questa casa legge già —
> `campo`, `parametro`, `valore`. I 16 punti esistenti **non si toccano**: il
> loro `target` continua a voler dire ciò che ha sempre voluto dire.
>
> ⚠️ Nel resto del brief la chiave compare ancora come `target` dove il testo è
> quello originale: **ovunque si legge `bersaglio`.**

La forma del valore, invece, non è toccata dal rilievo e resta quella decisa:

> ✅ **DECISO (Tid, 2026-08-22): `target` è sempre un ARRAY**, anche con un solo
> elemento. I casi a due bersagli esistono già — il **937** ne ha due, il
> documento da numerare e la fattura rettificata — e partire dal singolo
> significherebbe cambiare la forma di una chiave **già in servizio** il giorno
> che serve il secondo. Il frontend con un elemento disegna un pulsante, con due
> ne disegna due.

```sql
jsonb_build_object(
    'target', jsonb_build_array(
        jsonb_build_object('tipo', 'FATTURA', 'id', p_fattura_id)
    )
)
```

⚠️ **Mai un oggetto nudo quando l'elemento è uno**: sarebbe una seconda forma da
riconoscere, e chi consuma dovrebbe interrogare il tipo prima di iterare — cioè
esattamente il costo che l'array evita.

⚠️ **Il nome della tabella non entra mai nel bersaglio.** Non è pignoleria: il
catalogo dei messaggi è **uno solo** (`config.messaggi_errore`) e serve anche il
portale cliente e lo shop B2C (`CLIENTE_PORTALE`, `SHOP_CUSTOMER`). Un messaggio
scritto per l'operatore può affacciarsi su una superficie pubblica, e lì i nomi
delle tabelle sono ricognizione regalata. Nel `context` il nome resta comunque
dentro il database — ma il `tipo` logico è **anche** ciò che serve al frontend,
quindi non c'è ragione di avere due forme.

### 4.3 Il bersaglio è un'offerta, non una promessa

Il bersaglio può puntare a qualcosa che **chi legge non può aprire**: permessi,
perimetro emittente, record cancellato. Lato DB non c'è nulla da fare — il
bersaglio si scrive comunque — ma va dichiarato qui perché è il patto col
frontend: **il messaggio si mostra lo stesso, il pulsante non compare**. Mai un
pulsante che porta in un vicolo cieco.

📌 E ne discende una regola per il **testo**: non si nomina in chiaro una riga
che il lettore non può vedere. ~~⚠️ Sul 937 la questione è quasi teorica —
quell'id è il `riga_rettificata_id` di una riga che l'operatore vede
legittimamente, quindi è un dato che possiede già.~~ Vale per gli altri
messaggi, dove l'id non sarebbe ricavabile da nulla di visibile.

> 🔴 **RETTIFICA DEL 2026-08-22 (quarto giro): sul 937 NON è teorica, ed è
> proprio il ramo che il pilota deve gestire.** Letto il corpo della guardia
> (`20260821-05`), il secondo valore passato al `VARIADIC` è
>
> ```sql
> COALESCE(rif.id::text, 'riga ' || fr.riga_rettificata_id::text)
> ```
>
> — cioè **non è sempre l'id di una fattura**. Il ripiego scatta esattamente
> quando la fattura rettificata **non è visibile** (la guardia è fail-closed
> sulla RLS: `LEFT JOIN`, e un padre invisibile conta come bloccante), e in quel
> ramo il messaggio nomina **una riga di un documento che il lettore non può
> aprire**. È vero che il numero è ricavabile dai dati che l'operatore possiede
> — `riga_rettificata_id` sta sulla *sua* riga — ma il bersaglio costruito da
> quel valore sarebbe un tipo che non esiste (`FATTURA_RIGA`) e un pulsante che
> porta in un vicolo cieco garantito.
>
> ➡️ **Conseguenza sul T-3**: il pilota non è «aggiungere una chiave». La
> guardia va ristrutturata per produrre **un bersaglio tipato per ramo** — id di
> `FATTURA` quando il padre è visibile, **nessun bersaglio** quando non lo è —
> e i bloccanti sono un `count(DISTINCT)`, quindi *n*: è il caso che giustifica
> l'array, non un caso a due.

### 4.4 🔴 Come il bersaglio ARRIVA al frontend *(sezione nuova — quarto giro)*

Il §4.1 dava per scontato che bastasse la convenzione. **Non basta**: il
contesto **non esce dal database**. `script.fn_log_and_raise_error` lo consegna
a `dbops.error_log` (via `fn_log_error_only`) e poi solleva un'eccezione i cui
canali strutturati sono **cinque, tutti già occupati**:

| Canale del `RAISE` | Cosa porta oggi | Da quando |
| --- | --- | --- |
| `ERRCODE` | `P0001` — il contratto «errore di dominio» | — |
| `CONSTRAINT` | **il codice errore** | 2026-08-05 |
| `COLUMN` | **il campo da evidenziare** (da `context->>'campo'`, ripiego su `parametro`) | 2026-08-08 |
| `DETAIL` | la `causa` di catalogo → `error.detail` | — |
| `HINT` | la `soluzione` di catalogo → `error.hint` | 2026-08-18 |

⛔ **Quindi `B-1` come è scritta in §7 non è eseguibile**: al backend non arriva
niente da mettere nell'envelope. Il bersaglio, scritto solo nel `context`, serve
**il terzo lettore** (chi diagnostica) e **non il primo gesto** — cioè non la
ragione per cui questo brief esiste.

⭐ **E la decisione è di questo cantiere, non del BE**: il canale lo apre chi
solleva.

**Le tre vie, e cosa costano:**

| | Via | Esito |
| --- | --- | --- |
| A | Un **canale strutturato nuovo** del `RAISE` — restano liberi `SCHEMA`, `TABLE`, `DATATYPE` — con dentro una forma compatta (`FATTURA:835,FATTURA:820`) | ✅ **È il pattern di casa**, per la terza volta: `CONSTRAINT` (05/08), `COLUMN` (08/08). Una sede sola, il presidio `guardrail_codice_errore_strutturato.sql` già esiste e va esteso. ⚠️ I nomi dei canali sono impropri (`TABLE` porterebbe un tipo logico, non una tabella) e su un errore **non** `P0001` PostgreSQL li riempie da sé: il contratto dev'essere «`P0001` + canale valorizzato», come per `CONSTRAINT` |
| B | Il bersaglio **dentro `DETAIL`**, accodato alla `causa` | ⛔ `DETAIL` è testo per una persona e viaggia già a video come `error.detail`: metterci una struttura significa farla leggere per parsing e mostrarla a chi non deve vederla |
| C | Il backend **rilegge `dbops.error_log`** per `tx_id` | ⛔ Un giro in più sul database per ogni errore, e `error_log` non ha recinto fra aree né fra test ed esercizio. Il canale d'errore non può dipendere da una query di lettura |

> ✅ **DECISO (Tid, 2026-08-22): via A — una casella strutturata nuova.**
> Il bersaglio esce dal `RAISE` su un canale suo, in forma compatta, e la
> composizione si scrive **in un posto solo**: dentro `fn_log_and_raise_error`,
> esattamente come `campo`→`COLUMN`. ⭐ È la terza volta che questa casa fa la
> stessa mossa (`CONSTRAINT` il 05/08, `COLUMN` l'08/08): il backend sa già
> leggere una casella della diagnostica, e il presidio che vieta agli altri di
> scriverci — `scripts/sql/guardrail_codice_errore_strutturato.sql` — esiste già
> e va solo esteso.

**Quale delle tre caselle libere** *(proposta di chi scrive, non una decisione di
Tid)*: **`DATATYPE`**. `TABLE` e `SCHEMA` PostgreSQL li riempie da sé su ogni
violazione di vincolo vera (classe `23xxx`), quindi il contratto sarebbe più
fragile; e chiamare `TABLE` la casella che porta un **tipo logico** — in un brief
il cui §4.2 vieta i nomi di tabella — è un invito a fraintendere. `DATATYPE`
dice *«che genere di cosa»*, che è quasi il mestiere giusto.

⛔ **E vale lo stesso patto delle altre due**: *«`P0001` + casella valorizzata =
bersaglio»*. Fuori da `P0001` quel campo può averlo scritto PostgreSQL, e il
backend non deve fidarsene.

⭐ **Con la via A il T-5b (§5.1) diventa quasi gratis**: due punti di
sollevamento vivi su tre hanno già una chiave `<tipo>_id` nel contesto, e la
derivazione si scrive **una volta**, nel punto in cui si compone la casella.

---

## 5. I passi DB

### 5.1 La convenzione, e dove si scrive

| | Passo | Fase | Cosa fa |
| --- | --- | --- | --- |
| ~~**T-1**~~ | ~~Il **catalogo** dei tipi di entità~~ | — | ⛔ **NON È PIÙ UN PASSO DI QUESTO BRIEF.** Assorbito da [brief-db-event-log-scope-e-riga-parlante.md](brief-db-event-log-scope-e-riga-parlante.md) §3.7 / **D-17** / lotto **L4**. Resta il **prerequisito**: senza catalogo il `tipo` è testo libero e il presidio T-4 non ha contro cosa misurare |
| ~~**T-1b**~~ | ~~`event_log.entity_type` adotta il catalogo~~ | — | ⛔ **Idem.** Decideva su una colonna di un altro cantiere, che nel frattempo l'ha vincolata: la correzione in avanti la scrive **lui**, nel suo L4 (changeSet 55-57) |
| **T-1c** | ✅ **DECISO: il catalogo cresce col roll-out, una voce alla volta** | `80_data`, insieme a ogni passo di T-5 | Il seed applicato (changeSet **55**) ha **quattro righe**: `LOTTO`, `COMMESSA`, `FATTURA`, `TASK_RUN` — cioè il giornale più il tipo che dimostra la seconda lettura. ➡️ **Decisione di Tid (2026-08-22)**: ogni messaggio che riceve un bersaglio **si porta dietro la riga di catalogo che gli serve**, e non si semina in anticipo un tipo che nessuna schermata sa ancora raggiungere. ⭐ **Regge perché il presidio T-4 fa fallire la build** su un tipo non dichiarato: dimenticarsene non è possibile. ⚠️ **Due file per ogni passo del roll-out** — la funzione e il seed — ed è scritto qui perché nessuno lo scopra a valle. ⛔ **E dove il tipo esiste già in `config.sorgenti` il `codice` dev'essere IDENTICO** (`DDT_VENDITA`, non `DDT`), o la sovrapposizione dichiarata diventa la stessa cosa chiamata in due modi |
| **T-1d** | ✅ *(nuovo, DECISO)* **Il catalogo dichiara la chiave dell'entità** | `00_schema/config` + `80_data` | ⚠️ `event_log.entity_id` è **`bigint`**; ma `anagrafiche.soggetti.id` è un **`uuid`**, e `config.sorgenti` dichiara `key_selector = uid` per `PREVENTIVO` e `OFFERTA_COMMERCIALE`: **le due letture dello stesso catalogo non concordano sull'identificativo**. ➡️ **Decisione di Tid (2026-08-22): lo dice il catalogo** — una colonna in `config.tipi_entita` sulla stessa convenzione di `key_selector`. ⏱️ **Costa un changeSet**: la tabella è stata applicata il 2026-08-22 (§5.1-bis) |
| **T-2** | La forma `target` nelle linee guida | doc | `docs/it/linee-guida-sql.md` **§5, tabella dei tre canali** — non una sezione nuova: là è già scritto cosa va in `p_error_code`, in `p_context->>'campo'` e nel `VARIADIC`. Il bersaglio è **la quarta riga di quella tabella**, ed è l'unico posto dove chi scrive una guard la cerca |
| **T-3a** | Il pilota, **parte additiva**: **937** porta il bersaglio | `20_code` | `E_FATTURA_RETTIFICATA_SENZA_NUMERO` — bersaglio tipato **per ramo** (§4.3 rettificato): `FATTURA` quando il padre è visibile, niente quando non lo è. ⚠️ Nessuna modifica al messaggio: è additivo e non può peggiorare nulla |
| **T-3b** | Il pilota, **parte sottrattiva**: l'id esce dalla prosa | `20_code` + `80_data` | ⛔ **NON prima che B-1 e B-2 siano in servizio** — §5.3-bis. Finché il pulsante non c'è, togliere l'id lascia l'operatore con **meno** di oggi, e la `soluzione` a catalogo dice *«numerare prima il documento indicato»*: senza indicato |
| **T-4** | Il presidio | pgTAP / CI | un `target` con `tipo` fuori vocabolario fa fallire. ⚠️ **Statico, non sui dati**: si misura sui punti di sollevamento (come il test 5 del catalogo messaggi), non su `error_log` — che mescola test ed esercizio e non prova che un ramo sia mai stato percorso |
| **T-5** | Roll-out | vari | i messaggi che oggi mettono un id nella prosa, **uno alla volta** |
| **T-5b** | ⭐ *(nuovo)* La **derivazione** dalle chiavi già scritte | `20_code/script` | Due punti di sollevamento vivi su tre scrivono già `fattura_id`, `commessa_id`, `lotto_id`… nel proprio contesto (§4.1, misura sul codice): `fn_log_and_raise_error` può comporre il bersaglio da lì, in **una sede sola**, senza toccare i punti di sollevamento — è la mossa dell'08/08 su `parametro`→`COLUMN`. ⚠️ **Opt-in per codice, mai globale**: un `soggetto_id` nel contesto non è sempre il soggetto dove mandare l'operatore, e un pulsante che porta nel posto sbagliato è peggio di nessun pulsante (stessa ragione già scritta per `COLUMN`) |

### 5.1-bis 🔴 La finestra si chiude all'apply del L4 — e oggi è aperta

**Misurato il 2026-08-22 sul database e sul repo:**

| Fatto | Misura |
| --- | --- |
| I changeSet **53-60** del L4 dell'altro cantiere | **scritti, non committati, NON applicati** — `databasechangelog` si ferma a `20260822-52` |
| `config.tipi_entita` | esiste **solo come file**: `codice`, `etichetta_key`, `modo_risoluzione_emittente`, `obsoleto_dal`, `note` |
| Il seed | 4 righe (T-1c) |

⭐ **Quindi tutto ciò che questo brief chiede al catalogo costa ZERO oggi** — si
aggiunge una colonna a un `CREATE TABLE` non ancora eseguito — e **domani costa
una migrazione su una tabella per cui l'altro brief ha promesso «da qui in poi
solo seed»** (suo §9.4, impegno 1). È l'unico punto di questo brief con una
scadenza.

**Cosa va deciso prima dell'apply:**

1. **T-1d** — la chiave dell'entità: una colonna (`chiave` / `key_selector`, i
   valori `id` | `uid`) oppure la regola scritta «`id` è sempre la PK, e i tipi
   con chiave diversa non entrano»;
2. **T-1c** — se il seed nasce con i tipi che il bersaglio userà davvero
   (`SOGGETTO` almeno) o se li aggiunge il roll-out uno alla volta. ⭐ La seconda
   è legittima — «aggiungere un tipo è un seed» — **purché sia scritto qui**,
   perché altrimenti il T-5 scopre il vuoto a valle;
3. ⚠️ **I codici che si sovrappongono a `config.sorgenti` devono COINCIDERE.**
   Quel catalogo ha già `FATTURA`, `COMMESSA`, `DDT_VENDITA`, `PREVENTIVO`,
   `ORDINE_VENDITA`, `RESO_VENDITA`. Se `tipi_entita` seminasse `DDT` dove
   l'altro dice `DDT_VENDITA`, la «sovrapposizione dichiarata» diventerebbe
   **la stessa cosa chiamata in due modi** — che è peggio di due cataloghi.

### 5.2 Perché il 937 come pilota

È il caso che ha fatto nascere il brief, è **in collaudo adesso**, e ha la
proprietà che serve a un pilota: l'identificativo umano **non esiste** (il
documento non ha numero). Se il disegno regge lì, regge dove è più facile.

### 5.3 🔴 La trappola: le due modifiche del messaggio vanno insieme

Togliere l'id dalla frase significa togliere un `%s`. I valori arrivano dal
chiamante come `VARIADIC p_valori`, e il cantiere dei segnaposti ha già pagato
questa lezione: ~~**meno valori dei segnaposto → `22023`**, cioè un errore
tecnico opaco al posto dell'errore di dominio — e il caso rotto sarebbe
**proprio quello che il messaggio esiste per gestire**.~~

> ⚠️ **RETTIFICA DEL 2026-08-22 (quarto giro): la conseguenza non è più quella,
> la regola sì.** Verificato sul database: dal **18/08** la `format()` dentro
> `fn_log_and_raise_error` è avvolta in `BEGIN … EXCEPTION WHEN OTHERS`, quindi
> l'errore di dominio **non sparisce più**. Oggi il difetto degrada a: messaggio
> col **`%s` letterale a video** e un `W_MESSAGGIO_ARITA` nel log — brutto e
> semi-silenzioso, non un `22023`.
>
> ⭐ **E c'è già un cancello**: il **test 5** di
> `db/pgtap/script/test-catalogo-messaggi-errore-completo.sql` confronta
> staticamente i segnaposto del catalogo con l'arità dei punti di sollevamento.
> Quindi sbagliare l'ordine **si paga in CI**, non a video — a patto che i due
> lati stiano nella **stessa passata**.
>
> ⚠️ Il commento di quel test descrive ancora il vecchio comportamento
> («l'errore di dominio SPARISCE»): **è debito documentale**, non un difetto del
> test, che continua a misurare la cosa giusta.

➡️ Per ogni messaggio toccato, **catalogo e chiamanti nello stesso changeSet**.
Mai il CSV per primo.

### 5.3-bis ⛔ E c'è una SECONDA trappola, di sequenza: il DB non può andare da solo

Il T-3b (togliere l'id dalla prosa) è **corretto e prematuro finché non esiste
il consumatore**. Perché in mezzo c'è un intervallo in cui:

* il messaggio non nomina più il documento;
* il bersaglio viaggia, ma **il frontend non lo legge** — B-2 non è scritta, e
  `ui_action` è ferma da mesi nella stessa condizione (§7);
* la `soluzione` a catalogo del 937 dice *«Numerare prima il documento
  indicato»* — e **non c'è più niente di indicato**.

⭐ **Su un'emissione di lotto è peggio che teorico**: l'errore arriva su una
fattura fra molte, e l'id nella frase è oggi l'unica cosa che dice *quale*.

➡️ **Regola per tutto il roll-out, non solo per il pilota:** il bersaglio si
**aggiunge** quando è pronto il DB (additivo, non peggiora nulla); l'id si
**toglie** dalla prosa solo dopo che B-1 e B-2 sono in servizio. Sono due passi
distinti — **T-3a** e **T-3b** — e questo brief non può chiudere il secondo.

### 5.4 Cosa NON si fa

- ⛔ **Non si riscrivono i 756 messaggi.** Il bersaglio si aggiunge solo dove un
  identificativo serve davvero — cioè dove oggi c'è un id nella prosa;
- ⛔ **Non si tocca `error_log`**: la colonna `context` c'è già ed è jsonb;
- ⛔ **Non si tocca l'envelope API**: è §7, lato BE.

### 5.5 ⛔ Chi NON è un primo adottante *(l'unico punto in cui i due brief si contrappongono)*

Il §4-bis di
[brief-db-event-log-scope-e-riga-parlante.md](brief-db-event-log-scope-e-riga-parlante.md)
offre a questo cantiere, «senza costo», i due codici nati con L1:

> *«`E_EVENT_LOG_SCOPE_NON_RISOLTO` ed `E_EVENT_LOG_ENTITY_TYPE_IGNOTO` mettono
> già `entity_type` + `entity_id` nel context: hanno già la forma del bersaglio,
> solo non sotto la chiave `target`. Convertirli è una riga, e sono i primi
> adottanti gratuiti del loro T-5.»*

⛔ **Il regalo non si può accettare, per tre ragioni indipendenti** — verificate
sui CSV applicati:

| | Perché no |
| --- | --- |
| 1 | `E_EVENT_LOG_ENTITY_TYPE_IGNOTO` porta **per costruzione** un `entity_type` **fuori catalogo** — è la sua definizione. Un bersaglio con quel `tipo` è esattamente ciò che il **T-4** deve far fallire: il presidio si accenderebbe sul primo adottante |
| 2 | `E_EVENT_LOG_SCOPE_NON_RISOLTO` si solleva quando **l'entità non esiste**. Il bersaglio punterebbe al vuoto **sempre**, non «a volte» come nel degrado di §4.3: un pulsante che non compare mai non è un consumatore |
| 3 | Sono entrambi **`TECNICO` (500)**. Per `api.md` è la classe in cui *«l'operatore non può farci niente»*, e l'altro brief stesso scrive che su un `TECNICO` la chiave `campo` **non entra** nel contesto. Il bersaglio segue la stessa logica: è un **gesto per l'operatore**, e su un 500 non c'è gesto |

➡️ **Ne esce una regola che mancava a questo brief** — ✅ **decisa da Tid il
2026-08-22**, e che va nel T-2:

> **Il bersaglio si mette sugli errori davanti a cui l'operatore ha qualcosa da
> fare** — le classi `CONFLITTO_STATO` (259), `DATO_ERRATO` (272),
> `NON_TROVATO` (91), `NON_ESEGUIBILE` (32), `NON_PERMESSO` (25) — **e non sui
> `TECNICO` (76).** Su un `TECNICO` l'entità nel contesto resta dov'è: è
> materiale per chi diagnostica, e la chiave `target`/`bersaglio` non la
> rivendica.

🔵 **Richiesta all'altro cantiere** *(non applicata da qui: è il suo file)*: la
riga «primi adottanti gratuiti» del suo §4-bis va marcata come superata, con
questo motivo. ⭐ **Il resto di quel paragrafo regge e vale**: il vocabolario
condiviso e la tabella tipo→schermata scritta una volta sola restano il guadagno
vero della fusione.

---

## 6. Il piano di sviluppo

> ⚠️ **Numerazione.** La sequenza `NN` è **globale per data** fra tutte le
> cartelle. Al 2026-08-22, dopo l'apply del L4/L2 dell'altro cantiere, sono
> occupati fino a **`20260822-62`**: qui si parte da **63**. Da **riverificare**
> al momento della scrittura.
>
> ⛔ `runOnChange: false` ovunque in `00_schema` e `20_code`, `validCheckSums`
> **al plurale**, `logicalFilePath` sempre, **un changeSet per file**. L'unico
> `runOnChange: true` è il mirror CSV già esistente (il **55** dell'altro
> cantiere), che si **estende in place** e non si duplica.

### L1 — Il canale, e la casella dove viaggia

È il lotto che rende esistente il bersaglio. Da solo non produce ancora nessun
pulsante, ma è quello su cui poggiano tutti gli altri.

| # | File | Fase | Cosa |
| --- | --- | --- | --- |
| **63** | `alter-config-tipi-entita-key-selector` | `00_schema/config` | La colonna della **chiave dell'entità** (Q-C): `key_selector text NOT NULL` con `CHECK (IN ('id','uid'))`. ⭐ **Stesso nome che porta `config.sorgenti`**, di proposito: è la stessa convenzione, e chi cerca l'una trova l'altra. ⚠️ **Nasce con `DEFAULT 'id'` e il default si toglie nello stesso changeSet**: serve a riempire le 4 righe esistenti — che sono tutte a chiave numerica — senza lasciare a chi semina un valore che eredita in silenzio. ⛔ **E non tocca il giornale**: per `event_log` l'`entity_id` resta **la PK `id`, sempre** — la colonna serve a chi *punta* a un'entità da fuori, che è il bersaglio. La distinzione l'aveva già scritta l'[analisi](analisi-osservabilita-log.md) alla sua domanda 12 |
| — | `config/tipi_entita.csv` + il changeSet **55** | `80_data` (CSV) | La colonna nuova nel CSV **e** nella lista `columns:` del mirror. ⛔ **Non nasce un loader nuovo**: il 55 è `runOnChange`, si estende in place e alla prossima passata rilegge il file |
| **64** | `update-fn-log-and-raise-error-bersaglio` | `20_code/script` | ⭐ **Il cuore.** `script.fn_log_and_raise_error` legge `p_context->'bersaglio'`, ne compone la forma compatta e la fa uscire sulla casella strutturata. **La firma non cambia** (§4.4): i 1.093 punti di sollevamento vivi non si toccano |
| — | `config/codici_errore.csv` + `messaggi_errore.csv` | `80_data` (CSV) | **+1 codice** `W_BERSAGLIO_MALFORMATO` (classe `AVVISO`, gemello di `W_MESSAGGIO_ARITA`) e **+1 messaggio** (id **982**, il primo libero). ⚠️ Solo append: i mirror `runOnChange` esistenti li ripescano |
| — | `scripts/sql/guardrail_codice_errore_strutturato.sql` | CI | Il controllo **(G)**, gemello di (A) per `CONSTRAINT` e (F) per `COLUMN`: **un solo mittente** sulla casella nuova. Nasce **subito e con zero violazioni**, per la stessa ragione per cui nacque (F) |
| — | `db/pgtap/script/test-bersaglio-canale-strutturato.sql` | test | Il canale porta ciò che deve; un bersaglio malformato **non** distrugge l'errore di dominio; la casella resta vuota quando il bersaglio non c'è |

**La forma compatta, e perché non è jsonb.** La casella dell'eccezione è
**testo**: il bersaglio ci viaggia come `TIPO:id`, più elementi separati da
virgola.

```text
FATTURA:835                    un bersaglio
FATTURA:835,FATTURA:820        due
```

⚠️ **Il ricco resta nel contesto, il compatto viaggia.** `p_context->'bersaglio'`
è l'array di oggetti del §4.2 e finisce in `dbops.error_log` per chi diagnostica;
la casella porta la versione minima per il gesto. **Li scrive lo stesso
chiamante, una volta sola**: non sono due verità, è la stessa proiettata su due
lettori.

⛔ **Massimo cinque elementi.** Oltre, il frontend non disegna più un gesto ma un
elenco — e *quanti* sono lo dice già la frase (sul 937 c'è `v_n_bloccanti`).

#### ⛔ Tre cose che la funzione NON fa, e sono decisioni

| Non fa | Perché |
| --- | --- |
| **Non legge il catalogo a runtime** | Sarebbe una query in più dentro il percorso d'errore, e un catalogo irraggiungibile diventerebbe un errore dentro l'errore. La funzione **valida solo la forma** (`^[A-Z][A-Z0-9_]*$` per il tipo, id non vuoto) — esattamente come fa già col nome del campo. ⭐ **Il vocabolario lo presidia la CI** (L3), che è dove un errore di programmazione va scoperto |
| **Non fallisce mai per colpa del bersaglio** | Un bersaglio malformato lascia la casella **vuota** e scrive `W_BERSAGLIO_MALFORMATO` nel log. È la lezione del 18/08 tradotta: *la funzione che serve a riportare un errore non può essere quella che lo distrugge*. ⛔ E il `W_` **resta un `W_`**: si logga, non si solleva |
| **Non deriva niente da sola** | Nessuna composizione automatica dalle chiavi `<tipo>_id` già presenti nel contesto: è il **L5**, ed è una proposta, non questo lotto |

### L2 — Il pilota: il 937

| # | File | Fase | Cosa |
| --- | --- | --- | --- |
| **65** | `update-fn-numera-fattura-bersaglio` | `20_code/vendite` | `vendite.fn_numera_fattura_opz_emessa` costruisce il bersaglio **per ramo** (§4.3): `FATTURA` con l'id del padre quando il padre è **visibile**, **nessun bersaglio** quando non lo è. ⛔ **Il messaggio non si tocca**: è il T-3a, additivo per costruzione |
| — | `db/pgtap/vendite/test-numera-nota-credito-riferimento-v1.sql` | test | Si estende: il ramo visibile porta il bersaglio, il ramo fail-closed **non** lo porta, e in entrambi il codice e la frase restano quelli di oggi |

⭐ **Il pilota non chiede nessun seed**: punta a `FATTURA`, che è già a catalogo
dal L4 dell'altro cantiere. È la prova che la strada «una voce per volta» (Q-D)
parte in discesa.

⚠️ **La guardia oggi produce un valore polimorfo** — `rif.id::text` oppure la
stringa `'riga N'` — e va **spezzata in due variabili**: una per la frase, una
per il bersaglio. Sono due lettori, e questo brief esiste per non farli più
condividere lo stesso canale.

### L3 — Il presidio del vocabolario

| # | File | Fase | Cosa |
| --- | --- | --- | --- |
| **66** | `create-vw-bersagli-non-dichiarati` | `20_code/dbops` | I tipi scritti nei **corpi delle funzioni vive** e assenti da `config.tipi_entita`. Gemella di `dbops.vw_eventi_non_dichiarati` (nata col L4) e di `vw_codici_errore_da_dichiarare` |
| — | `db/pgtap/dbops/test-vw-bersagli-non-dichiarati.sql` | test | La vista è **vuota**: se non lo è, la build è rossa e dice quale tipo manca |

⭐ **È questo cancello a rendere sicura la Q-D.** Il catalogo cresce una voce per
volta *perché* dimenticarsene non è possibile: chi scrive un bersaglio su un tipo
non dichiarato lo scopre in CI, non in esercizio.

⚠️ **Statico, non sui dati** (§5.1, T-4): si legge `pg_proc.prosrc`, **non**
`dbops.error_log` — che non dice né se un ramo è mai stato percorso né se conti
qualcosa.

### L4 — La convenzione scritta

| File | Cosa |
| --- | --- |
| `docs/it/linee-guida-sql.md` §5 | ⭐ **La quarta riga della tabella dei canali**, che oggi ne ha tre (`p_error_code` → backend, `p_context->>'campo'` → frontend, `VARIADIC` → operatore). Il bersaglio è il quarto destinatario, e va **in quella tabella**: è il posto dove chi scrive una guard va a guardare |
| idem | La regola delle classi (Q-E) e la forma dell'array (§4.2), **con l'avvertenza del nome**: `bersaglio`, non `target` — che in 16 punti significa già un'altra cosa |

### L5 — La derivazione automatica *(proposta, NON decisa)*

Due punti di sollevamento vivi su tre scrivono già una chiave `<tipo>_id` nel
contesto (§4.1). La tentazione è comporre il bersaglio da lì, senza toccare
nessun chiamante — è ciò che l'08/08 ha fatto con `parametro`→`COLUMN`.

⚠️ **Ma le due decisioni di oggi le tolgono metà del guadagno**, e va detto prima
di scriverla:

* con la **Q-E** la derivazione dovrebbe conoscere la **classe** del codice, cioè
  leggere `config.codici_errore` dentro il percorso d'errore — la query che il
  L1 ha deciso di non fare;
* con la **Q-D** varrebbe solo per i tipi già a catalogo, cioè oggi tre;
* ⛔ e soprattutto: sul canale `COLUMN` un valore sbagliato è **inerte** (il
  frontend non trova quel campo e non evidenzia niente); un **bersaglio**
  sbagliato è **attivo** — porta l'operatore in un posto che non c'entra. Non è
  lo stesso rischio, e non merita la stessa scorciatoia.

➡️ **Si valuta dopo il pilota**, misurando su un campione quante volte la chiave
`<tipo>_id` più ovvia è davvero l'entità dove si vorrebbe andare. Fino ad allora
il roll-out è **esplicito, uno alla volta**.

### Ordine, dipendenze e cosa resta fuori

```text
63 ──► 55 (CSV)          la chiave dell'entità, e il seme che la riempie
64 ──► 65 ──► 66         il canale, il primo che ci scrive, il cancello
```

* **64 prima di 65**: il pilota scrive in una casella che dev'esistere;
* **63 è indipendente** dagli altri tre: non blocca il pilota, che punta a un
  tipo a chiave numerica;
* **66 dopo 65**, per nascere con qualcosa da misurare — ma non è un vincolo
  tecnico.

⛔ **Cosa NON entra in questo piano**, e sono conferme del §5.4: nessuna FK su
niente, `dbops.error_log` non si tocca, l'envelope API è del backend (§7), e i
756 messaggi **non** si riscrivono — il T-3b, cioè l'id che esce dalla prosa,
resta appeso a B-1/B-2 e non lo chiude questo brief.

---

## 7. Cosa tocca dopo, e a chi *(dichiarato, non pianificato qui)*

| | Chi | Cosa |
| --- | --- | --- |
| **B-1** | BE | portare `target` nell'envelope d'errore, accanto a `code` / `message` / `ui_action` / `fields`. 🔴 **NON è eseguibile finché il DB non apre il canale (§4.4)**: oggi al backend non arriva niente da mettere nell'envelope, perché `p_context` si ferma a `dbops.error_log`. ⭐ Quando il canale ci sarà, il lato BE è **lo stesso lavoro già fatto due volte** — `CONSTRAINT`→`code` (05/08) e `COLUMN`→`fields` (08/08) |
| **B-2** | FE | il gesto: da `target` a una rotta. ⭐ È la **stessa** tabella di rotte della timeline per entità (§3): si scrive una volta |
| **B-3** | FE | il degrado di §4.3 — bersaglio non risolvibile → nessun pulsante, messaggio invariato |

⭐ **Un effetto laterale che vale da solo**: `ui_action` oggi è un canale
prodotto e non consumato — 126 codici promettono «evidenzia il campo» e nessun
componente legge `azioneUi`. Un errore che porta un bersaglio è il primo pezzo di
frontend che ha una **ragione** per leggere quel canale, e rende scrivibile il
presidio **C2** di
[analisi-presidi-percorso-storto.md](analisi-presidi-percorso-storto.md).

---

## 8. Domande

### Chiuse — 2026-08-22, da Tid

1. ✅ **Il vocabolario dei tipi: CATALOGO CHIUSO**, e `event_log.entity_type` lo
   adotta. Motivo: la stessa nozione governata in due modi è peggio che non
   governarla. ➡️ **La decisione regge; la sua ESECUZIONE è passata all'altro
   brief** (D-17, §3.7, L4) perché lì vive la colonna. Qui resta come
   prerequisito, più il nuovo **T-1c**: controllare che il catalogo non nasca
   tagliato sui soli tipi *giornalabili*, o il bersaglio perde metà del proprio
   vocabolario (§3).
2. ✅ **Il bersaglio è SEMPRE UN ARRAY**, anche con un elemento solo. Motivo: i
   casi a due bersagli esistono già (il 937), e cambiare la forma di una chiave
   in servizio costa più che nascere larghi. Forma in §4.2.

### ✅ Chiuse — le cinque del quarto giro, decise da Tid il 2026-08-22

| # | Domanda | Dove |
| --- | --- | --- |
| ~~**Q-A**~~ | ✅ **CHIUSA (Tid, 2026-08-22): via A**, una casella strutturata nuova del `RAISE` — come `CONSTRAINT` (05/08) e `COLUMN` (08/08). Proposta la casella `DATATYPE`, col patto «`P0001` + casella valorizzata = bersaglio» | §4.4 |
| ~~**Q-B**~~ | ✅ **CHIUSA (Tid, 2026-08-22): la chiave è `bersaglio`.** `target` resta ai 16 punti che la usano già per il nome di una tabella: nessuna riscrittura, nessuna parola con due significati | §4.2 |
| ~~**Q-C**~~ | ✅ **CHIUSA (Tid, 2026-08-22): lo dichiara il catalogo.** `config.tipi_entita` prende una colonna per la chiave (`id` \| `uid`), sulla convenzione già in uso in `config.sorgenti.key_selector`. ⭐ Il motivo che ha deciso: la regola vive **accanto al tipo**, non nella testa di chi scrive il frontend — e un pulsante che porta nel posto sbagliato è peggio di nessun pulsante | §5.1-bis · T-1d |
| ~~**Q-D**~~ | ✅ **CHIUSA (Tid, 2026-08-22): il catalogo cresce col roll-out**, una voce per volta, insieme al messaggio che la usa. ⭐ Niente voci che promettono una destinazione che nessuna schermata raggiunge, e il presidio T-4 impedisce di dimenticarsene | §5.1-bis · T-1c |
| ~~**Q-E**~~ | ✅ **CHIUSA (Tid, 2026-08-22): sì sulle classi rimediabili, NO sui `TECNICO`.** Il bersaglio è un gesto per l'operatore, e su un 500 non c'è gesto: l'entità resta negli appunti, per chi indaga. Stessa logica già in servizio per il campo da evidenziare | §5.5 |

### Aperte — non bloccano la scrittura

3. 🔵 **`error_log` diventerà leggibile in-app?** Se sì il `context` smette di
   essere solo diagnostico e diventa una superficie: cambia cosa è lecito
   scriverci. Domanda gemella del Passo 3 di
   [analisi-osservabilita-log.md](analisi-osservabilita-log.md).
4. 🔵 **Il catalogo messaggi distingue le superfici?** Operatore, portale
   cliente, shop leggono lo stesso `config.messaggi_errore`. ⚠️ È più grossa di
   questo brief e non lo blocca, ma è la domanda che gli sta sotto.

---

## 9. Registro

| Data | Cosa |
| --- | --- |
| 2026-08-22 (sesto giro) | 📋 **Scritto il piano (§6)**: cinque lotti, quattro changeSet numerati (**63-66**), due append ai CSV, un controllo di CI, tre file pgTAP e una tabella da estendere in `linee-guida-sql`. ⭐ **Le tre decisioni che il piano ha dovuto prendere per essere scrivibile**, e stanno tutte nel L1: (1) **il ricco resta nel contesto, il compatto viaggia** — `p_context->'bersaglio'` è l'array del §4.2 e finisce in `error_log`, la casella dell'eccezione porta `TIPO:id`, e li scrive **lo stesso chiamante una volta sola**; (2) **la funzione non legge il catalogo a runtime** — valida solo la forma, il vocabolario lo presidia la CI (L3), perché una query dentro il percorso d'errore è una dipendenza che non si vuole; (3) **un bersaglio malformato non distrugge mai l'errore di dominio** — casella vuota e `W_BERSAGLIO_MALFORMATO` nel log, che è la lezione del 18/08 tradotta. ⚠️ **Il L5 (derivazione automatica dalle chiavi `<tipo>_id`) è retrocesso a proposta**: con la Q-E servirebbe leggere la classe a runtime e con la Q-D varrebbe per tre tipi — ma la ragione vera è che un bersaglio sbagliato è **attivo** (porta l'operatore altrove), mentre un `COLUMN` sbagliato è inerte: non merita la stessa scorciatoia. 🔧 **Allineati i riferimenti superati** dopo l'apply dell'altro cantiere, di qua e di là (§3 di questo brief; §3.1, §3.2, §3.5, §3.8 e §4-bis dell'altro) |
| 2026-08-22 (quinto giro) | ✅ **Chiuse tutte e cinque le domande del quarto giro, e il brief diventa scrivibile.** ⭐ **Q-A: via A** — il bersaglio esce dal `RAISE` su una **casella strutturata nuova**, terza volta che questa casa fa la stessa mossa (`CONSTRAINT` 05/08, `COLUMN` 08/08), con la composizione in **una sede sola** dentro `fn_log_and_raise_error`. ⭐ **Q-B: la chiave è `bersaglio`** — i 16 punti che usano `target` per il nome di una tabella non si toccano, e nessuna parola resta con due significati. ⭐ **Q-C: la chiave dell'entità la dichiara il catalogo**, sulla convenzione di `config.sorgenti.key_selector`: la regola vive accanto al tipo, non nella testa di chi scrive il frontend. ⭐ **Q-D: il catalogo cresce col roll-out**, una voce per volta insieme al messaggio che la usa — niente voci che promettono una destinazione irraggiungibile, e il presidio **T-4** impedisce di dimenticarsene. ⭐ **Q-E: bersaglio solo sugli errori rimediabili, mai sui `TECNICO`** — su un 500 non c'è gesto, e l'entità resta negli appunti per chi indaga. ⏱️ **Nel frattempo il L4 dell'altro cantiere è stato applicato** (53-60, più 61-62 del suo L2): la colonna del **T-1d** è ora un changeSet nuovo. ❌ **E una segnalazione mia che era sbagliata**: avevo dato per «residuo» la FK `fk_event_log_tipo_entita` senza riga in `dbops.fk_index_policy`. **Non è un residuo, è una decisione scritta** (loro §4, L4): la FK è su `entity_type`, che è **già la prima colonna di `ix_event_log_entity_time`** — coperta per prefisso — e registrarla a `consentito=false` sarebbe **attivamente dannoso**, perché il ramo del `DROP` estrae il nome dal `dll_command` e cancellerebbe un indice non dedicato che serve alla query forense. ⭐ Avevo guardato la tabella e non il brief: la regola «gli indici FK sono opt-in» ha un'eccezione per prefisso, e loro l'avevano già vista |
| 2026-08-22 (quarto giro) | 🔎 **Rilettura critica contro il cantiere `event_log`**, misurando sul database e sul codice invece che sul testo. ⭐ **Il disegno regge; a non reggere è la sua premessa operativa**, e sono quattro rilievi. 🔴 **(1) Il canale del §4.1 non arriva al frontend**: `p_context` va solo in `error_log`, e i cinque canali strutturati del `RAISE` sono **tutti occupati** (`ERRCODE`, `CONSTRAINT`, `COLUMN`, `DETAIL`, `HINT`) — quindi «serve solo una convenzione» vale per chi diagnostica e **non** per il gesto, che è la ragione del brief. Nasce il §4.4 e con lui **Q-A**; **B-1 non è eseguibile** com'era scritta. 🔴 **(2) La chiave `target` è già in uso**: **16 punti di sollevamento in 6 file** la scrivono come **stringa**, e dentro c'è `schema.tabella` — cioè proprio ciò che il §4.2 vieta. Proposta: `bersaglio` (**Q-B**). 🔴 **(3) Contrapposizione vera con l'altro brief**: i due codici che il suo §4-bis regala come «primi adottanti gratuiti» **non lo sono** — uno porta per definizione un tipo fuori catalogo (farebbe fallire il T-4), l'altro punta a un'entità inesistente, e sono entrambi `TECNICO`. Da lì la regola mancante: **il bersaglio è per gli errori rimediabili, non per i 500** (§5.5, **Q-E**). 🔴 **(4) C'è una scadenza**: i changeSet 53-60 del L4 sono **scritti e non applicati**, quindi ogni colonna che il bersaglio vuole nel catalogo costa **zero oggi** e una migrazione domani — e la misura dice che il seed ha 4 tipi (manca `SOGGETTO`) e che le due letture **non concordano sull'identificativo** (`entity_id` è `bigint`, ma `soggetti.id` è `uuid` e `sorgenti` ha `key_selector = uid`). Nascono **T-1d**, §5.1-bis, **Q-C** e **Q-D**. ⚠️ Corretti inoltre due punti che dicevano il falso: il §5.3 (dal 18/08 la `format()` è protetta: il difetto **degrada**, non alza più `22023` — e un cancello statico esiste già) e il §4.3 sul 937 (il secondo valore **non è sempre un id di fattura**: nel ramo fail-closed è la stringa `riga N` di un documento invisibile). ⭐ **E una scoperta che vale il giro**: **due punti di sollevamento vivi su tre** scrivono già una chiave `<tipo>_id` nel contesto — il bersaglio si può **derivare in una sede sola**, come l'08/08 ha fatto con `parametro`→`COLUMN` (nuovo **T-5b**). ⚠️ **Nota di metodo, richiamata da Tid nello stesso giro**: le misure di questo brief sono sul **codice** (`pg_proc.prosrc`, i file di `20_code`), non sulle righe di `dbops.error_log` — un registro di sviluppo senza recinto fra test ed esercizio, che non misura né frequenza né gravità. Le due misure che erano nate «a conteggio di righe» sono state rifatte sui corpi delle funzioni (§4.1) e ridotte a eco (§4.2). ⛔ Nulla applicato, nessun file di migrazione toccato |
| 2026-08-22 (terzo giro) | ⛔ **T-1 e T-1b escono da questo brief**: sono stati assorbiti da [brief-db-event-log-scope-e-riga-parlante.md](brief-db-event-log-scope-e-riga-parlante.md) (**D-17**, §3.7, lotto **L4**). ⭐ **La decisione di Tid non cambia — cambia dove si esegue**: decidevano su `event_log.entity_type`, e una decisione su una colonna deve stare dove vive la colonna. ⚠️ Il rischio che il secondo giro aveva previsto si è avverato al contrario: quel cantiere ha **applicato per primo** una scelta opposta (un `CHECK` invece del catalogo), quindi non c'è un apply da coordinare ma una correzione in avanti da scrivere — la scrive lui. ⭐ **E la collisione ha prodotto due cose utili**: il catalogo porterà `modo_risoluzione_emittente`, che rende inutile il `CASE` scritto a mano nel loro trigger; e si è capito che **i due vocabolari non sono lo stesso insieme** — il giornale è un sottoinsieme proprio del bersaglio, selezionato da «l'emittente dev'essere derivabile». Da lì il nuovo **T-1c**. 🔴 Rettificato il §3, che dava `TASK_RUN` per presente in `event_log`: non lo è più dal 2026-08-22 |
| 2026-08-22 (secondo giro) | ✅ **Chiuse le due domande che bloccavano la scrittura**, entrambe verso la forma più larga: **catalogo chiuso** per i tipi (con `event_log.entity_type` che lo adotta — nasce **T-1b**) e **`target` sempre array**. ⭐ Nessuna delle due è una preferenza di stile: la prima evita due vocabolari per la stessa nozione, la seconda evita di cambiare la forma di una chiave **già in servizio** il giorno del secondo bersaglio — e il secondo bersaglio esiste già oggi, sul messaggio pilota. 🔴 **Ne discende un vincolo di coordinamento che prima non c'era**: T-1b tocca `event_log`, che è anche l'oggetto del **Passo 0** dell'osservabilità (emittente + RLS + correlation + actor). Stessa tabella, stessa funzione di scrittura: **un apply solo**, e la sorte delle righe storiche si decide di là, non qui |
| 2026-08-22 | Stesura, su richiesta di Tid dopo il collaudo NC resi. ⭐ **Il disegno è cambiato durante la discussione, ed è la parte utile**: la proposta di partenza era `schema.tabella.id` nel messaggio; ragionandoci è emerso che la domanda «id o frase umana» **non ha risposta** perché presuppone che l'errore sia testo, e che all'operatore non serve il *nome* del record ma **arrivarci**. Da lì i tre strati e il bersaglio. ⭐ Il canale c'è già (`p_context` → `dbops.error_log.context`) e la quasi totalità dei sollevamenti lo valorizza: manca la **convenzione**, non la macchina. 🔴 Segnalata la trappola §5.3 (catalogo e chiamanti nello stesso changeSet, lezione del cantiere segnaposti). ⛔ Nulla applicato |

---

*Brief DB — il bersaglio dell'errore (22 agosto 2026).*
