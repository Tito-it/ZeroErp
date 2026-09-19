# Brief DB — l'errore porta un bersaglio, non un nome

> 📦 **ARCHIVIATO il 2026-08-24**, spostato da `work-in-progress`. Il cantiere è
> chiuso su tutti e quattro i lati; l'unica voce rimasta (i due candidati `T-5`
> del §L6) **non è arretrato**: per decisione il roll-out riprende *quando lo
> chiede un caso*.
>
> ⚠️ **I riferimenti a questo file dentro i corpi SQL e nei changelog citano il
> vecchio percorso** (`work-in-progress/…`), e resteranno così: i primi vivono
> nei `COMMENT ON FUNCTION`, cioè nel database — la doc in `dbzero` è solo il
> loro specchio — e i secondi in changeSet già mergiati, che non si toccano.
> Sono **28 file**: chi ci arriva da lì non ha perso niente, il documento è qui.

> **Cos'è.** Il piano per far sì che un errore, oltre a *dire* cosa è successo,
> dica **su quale cosa** — in una forma che l'interfaccia possa trasformare in un
> gesto («vai lì») e che chi diagnostica possa leggere come coordinata esatta.
>
> **Perimetro: DB per primo** (decisione di Tid, 2026-08-22). La convenzione
> nasce dove l'errore viene sollevato; il consumo lato BE/FE è dichiarato in §7
> ma **non** è questo brief.
>
> ✅ **APPLICATO E VERDE (2026-08-24).** Quattro changeSet (`20260823-01…04`),
> tre CSV, il controllo **(G)** del guardrail di CI e la quarta riga della
> tabella dei canali in `linee-guida-sql`. **19 asserzioni pgTAP su tre file**
> (8 sul canale, 4 sul cancello, 7 sul pilota — questi ultimi da 5 che erano),
> più il presidio del catalogo messaggi. Il guardrail passa: **un solo mittente
> su tutti e tre i canali**; `dbops.vw_bersagli_non_dichiarati` è **vuota**.
>
> ⭐ **Tutti e quattro i lati sono chiusi** *(aggiornato 2026-08-24, sera)*: il
> **DB** (L1-L4), il **roll-out** (L6, a fine corsa: 8 funzioni, 9 tipi), il
> **backend** (B-1: cinque punti di traduzione, envelope `targets`) e il
> **frontend** (B-2/B-3: toast con azioni, ospite globale, **8 destinazioni su
> 9 tipi**). Il dettaglio è in §7-bis.
>
> 🎉 **E il `T-3b` È FATTO — applicato e verde il 2026-08-24** (changeSet
> `20260824-13` + la riga 937 di `messaggi_errore.csv`, nella **stessa
> passata**). ⭐ **Il cantiere ha raggiunto il proprio scopo**: la frase che
> l'operatore legge non porta più nessuna chiave interna.
>
> ```text
> prima  «Non si puo' numerare il documento 19563: la fattura che rettifica
>         non e' ancora numerata (documento 835). Numera prima quella.»
> dopo   «Non si puo' numerare il documento: rettifica righe di altri documenti
>         che non risultano ancora numerati. Documenti da numerare prima: 2.»
>         + canale  FATTURA:19753,FATTURA:19752,FATTURA:19754
> ```
>
> ⭐ **Le due domande del §7-ter sono state decise da Tid** (dettaglio in fondo
> a quella sezione): **(1)** il bersaglio del 937 ha **due ruoli** — il
> documento da numerare, **sempre e per primo**, poi i padri bloccanti visibili
> — che è la forma dichiarata dal §4.2 e mai realizzata dal pilota; **(2)** una
> **frase sola** per entrambi i rami, con un unico `%s` che porta il
> **conteggio** dei bloccanti, e la `soluzione` riscritta perché regga anche
> dove il pulsante non c'è.
> ⚠️ **La testa dell'array è una garanzia, non un'estetica**: il canale compatto
> tiene i primi cinque elementi, quindi il documento in testa è ciò che dice
> *quale* anche quando i padri sono sette. Senza quel primo bersaglio il T-3b
> non si sarebbe potuto fare. **8/8 pgTAP verdi come applicazione.**
>
> ✅ **COLLAUDATO IN-APP il 2026-08-24 (Tid) — su DUE superfici**, lotto
> `LTF-0005803`: il **toast** porta il pulsante e il click apre la fattura; e
> dal **messaggio della scheda Segnalazioni** il documento è linkato e si apre.
> ⭐ La prima è la strada difficile (200 col fallimento nel payload), la seconda
> è l'errore **persistito** — cioè il lettore che il §1 dice essere quello che
> conta. §7-bis.8.
>
> ⚠️ **E va detto cosa NON è stato esercitato**, perché un brief archiviato si
> legge come «provato per intero»: manca la terza superficie — la strada
> dell'**envelope**, cioè una chiamata che fallisce con errore HTTP — e sono
> stati provati **1 tipo su 9**. Passano tutte dallo stesso resolver e degradano
> allo stesso modo, ma esercitate non lo sono.
>
> 🔵 **Resta UNA cosa, e non è lavoro arretrato**: **due candidati T-5** (§L6,
> «fine corsa»), che si convertono *quando lo chiede un caso*.
> ⛔ **La proposta L5 è ARCHIVIATA — respinta da Tid il 2026-08-24**, sulla
> misura del §L5: riprodurrebbe 9 bersagli su 14 già coperti, e ne inventerebbe
> **138 mai vagliati**.
> ✅ **E le due domande di fondo del §8 sono CHIUSE** (Tid, 2026-08-24):
> `error_log` **non** diventa una superficie per tutti — se mai si mostrasse,
> solo ai tecnici e dietro permesso, *«o continuiamo a creare tabelle per gli
> appunti tecnici che poi qualcuno mette a video»* — e il catalogo messaggi
> **non** prende una dimensione «superficie», perché le superfici si separano
> nei **percorsi**, non nel catalogo.
>
> ⚠️ **Il catalogo dei tipi** è il prerequisito, applicato dall'altro cantiere
> il 2026-08-22; questo lotto gli ha aggiunto `key_selector` (T-1d).
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
| **bersaglio** | interfaccia **e** diagnosi | `{ tipo, id }` | ✅ **c'è, dal 2026-08-24** — canale `DATATYPE`, envelope `targets`, pulsante. *(Alla stesura mancava: è la riga per cui il brief è nato.)* |

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
([analisi-osservabilita-log.md](../work-done/analisi-osservabilita-log.md), Passo A). Se il
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
  [analisi-osservabilita-log.md](../work-done/analisi-osservabilita-log.md)), e su quel
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
>
> 🎉 **E il 2026-08-24 questa frase è diventata vera anche nel codice.** Per due
> giorni il §4.2 ha dichiarato due bersagli e il pilota ne ha emesso uno: la
> divergenza l'ha trovata il BE rileggendo il codice contro il brief (§7-ter,
> Rilievo 1), non un test. Il `T-3b` (`20260824-13`) l'ha chiusa, e la forma
> definitiva del 937 è quella dichiarata qui.
>
> ⭐ **Ne è uscita una regola che questo paragrafo non aveva**, ora nelle
> linee-guida §5: **in testa va la cosa SU CUI l'errore è successo**, poi quelle
> da sistemare. Non è ordine estetico — il canale compatto tiene i primi cinque
> elementi, quindi la testa è ciò che sopravvive al tetto, ed è l'unica cosa che
> dice *quale* quando l'errore arriva dentro un'elaborazione massiva.

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
| **T-3b** | Il pilota, **parte sottrattiva**: l'id esce dalla prosa | `20_code` + `80_data` | ✅ **APPLICATO il 2026-08-24** — `20260824-13` e la riga 937 del CSV, nella stessa passata. La frase perde entrambi gli id e guadagna il **conteggio**; il bersaglio guadagna il **documento da numerare in testa**. ⭐ La condizione del §5.3-bis era «B-1 e B-2 in servizio», ed è stata rispettata: il pulsante esisteva e collaudato **prima** che l'id sparisse. Dettaglio e decisioni: §6 lotto **L7** e §7-ter |
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
distinti — **T-3a** e **T-3b** — e ~~questo brief non può chiudere il secondo~~.

> ✅ **La sequenza ha retto, e vale la pena registrare che è servita davvero.**
> Il `T-3a` è del 23/08, B-1 e B-2 del 24/08 mattina, il `T-3b` del 24/08
> pomeriggio: fra il momento in cui il pulsante è comparso e quello in cui l'id
> è sparito dalla frase non c'è stato nessun intervallo scoperto.
> ⭐ **E la trappola che questo paragrafo prevedeva si è manifestata al terzo
> punto, non ai primi due**: la `soluzione` a catalogo diceva *«Numerare prima
> il documento indicato»*, e senza id non aveva più referente. È stata riscritta
> nello stesso changeSet, in una forma che regge **anche quando il pulsante non
> c'è** — perimetro emittente, permessi, area bloccata (§4.3).
> ⚠️ Il quarto rischio previsto — *«su un'emissione di lotto l'id nella frase è
> oggi l'unica cosa che dice quale»* — **non è stato ignorato: è stato risolto**,
> ed è la ragione del primo bersaglio del §7-ter.

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

✅ **Richiesta all'altro cantiere — ACCOLTA** *(verificato il 2026-08-24)*: la
riga «primi adottanti gratuiti» del suo §4-bis è ora barrata e marcata
**SUPERATA**, con le tre ragioni riportate per intero. ⭐ E là hanno aggiunto
una frase che vale più della rinuncia: *«ne è uscita una regola, che vale più
del regalo»*. ⭐ **Il resto di quel paragrafo regge e vale**: il vocabolario
condiviso e la tabella tipo→schermata scritta una volta sola restano il guadagno
vero della fusione.

---

## 6. Il piano di sviluppo

> ✅ **SCRITTO IL 2026-08-23 — quattro changeSet, tre CSV, due file pgTAP
> nuovi, uno esteso, un controllo di CI e la tabella dei canali nelle linee
> guida.** ⛔ **Non applicato**: l'apply è di Tid.
>
> ⚠️ **Numerazione.** La sequenza `NN` è globale **per data**, e la data è
> cambiata: i changeSet sono `20260823-01…04`, non i 63-66 previsti quando il
> piano è stato scritto. ⚠️ E il numero **06** di oggi è già di un altro
> cantiere (`fn_run_automations` resiliente): la sequenza è condivisa, e va
> riletta prima di ogni file — non dedotta dal proprio lotto.
>
> ⭐ **E il 2026-08-24 la stessa avvertenza si è ripagata due volte**: il
> roll-out del L6 ha preso `01…10`, l'altro cantiere `11-12` e `14`, e il
> **L7** — il `T-3b` — è il **13**. Il numero non si deduce dal proprio lotto
> nemmeno a poche ore di distanza.
>
> ⛔ `runOnChange: false` ovunque in `00_schema` e `20_code`, `validCheckSums`
> **al plurale**, `logicalFilePath` sempre, **un changeSet per file**. L'unico
> `runOnChange: true` è il mirror CSV già esistente (il **55** dell'altro
> cantiere), che si **estende in place** e non si duplica.

### L1 — Il canale, e la casella dove viaggia — ✅ **APPLICATO il 2026-08-24**

È il lotto che rende esistente il bersaglio. Da solo non produce ancora nessun
pulsante, ma è quello su cui poggiano tutti gli altri.

| # | File | Fase | Cosa |
| --- | --- | --- | --- |
| **01** | `alter-config-tipi-entita-key-selector` | `00_schema/config` | La colonna della **chiave dell'entità** (Q-C): `key_selector text NOT NULL` con `CHECK (IN ('id','uid'))`. ⭐ **Stesso nome che porta `config.sorgenti`**, di proposito: è la stessa convenzione, e chi cerca l'una trova l'altra. ⚠️ **Nasce con `DEFAULT 'id'` e il default si toglie nello stesso changeSet**: serve a riempire le 4 righe esistenti — che sono tutte a chiave numerica — senza lasciare a chi semina un valore che eredita in silenzio. ⛔ **E non tocca il giornale**: per `event_log` l'`entity_id` resta **la PK `id`, sempre** — la colonna serve a chi *punta* a un'entità da fuori, che è il bersaglio. La distinzione l'aveva già scritta l'[analisi](../work-done/analisi-osservabilita-log.md) alla sua domanda 12 |
| — | `config/tipi_entita.csv` + il changeSet **55** | `80_data` (CSV) | La colonna nuova nel CSV **e** nella lista `columns:` del mirror. ⛔ **Non nasce un loader nuovo**: il 55 è `runOnChange`, si estende in place e alla prossima passata rilegge il file |
| **02** | `update-fn-log-and-raise-error-bersaglio` | `20_code/script` | ⭐ **Il cuore.** `script.fn_log_and_raise_error` legge `p_context->'bersaglio'`, ne compone la forma compatta e la fa uscire sulla casella strutturata. **La firma non cambia** (§4.4): i 1.093 punti di sollevamento vivi non si toccano |
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
| **Non deriva niente da sola** | Nessuna composizione automatica dalle chiavi `<tipo>_id` già presenti nel contesto: era il **L5**, ⛔ **respinto il 2026-08-24** sulla misura — e quindi non è più nemmeno una proposta aperta |

### L2 — Il pilota: il 937 — ✅ **APPLICATO il 2026-08-24**

| # | File | Fase | Cosa |
| --- | --- | --- | --- |
| **03** | `update-fn-numera-fattura-bersaglio` | `20_code/vendite` | `vendite.fn_numera_fattura_opz_emessa` costruisce il bersaglio **per ramo** (§4.3): `FATTURA` con l'id del padre quando il padre è **visibile**, **nessun bersaglio** quando non lo è. ⛔ **Il messaggio non si tocca**: è il T-3a, additivo per costruzione |
| — | `db/pgtap/vendite/test-numera-nota-credito-riferimento-v1.sql` | test | Si estende: il ramo visibile porta il bersaglio, il ramo fail-closed **non** lo porta, e in entrambi il codice e la frase restano quelli di oggi |

⭐ **Il pilota non chiede nessun seed**: punta a `FATTURA`, che è già a catalogo
dal L4 dell'altro cantiere. È la prova che la strada «una voce per volta» (Q-D)
parte in discesa.

⚠️ **La guardia oggi produce un valore polimorfo** — `rif.id::text` oppure la
stringa `'riga N'` — e va **spezzata in due variabili**: una per la frase, una
per il bersaglio. Sono due lettori, e questo brief esiste per non farli più
condividere lo stesso canale.

### L3 — Il presidio del vocabolario — ✅ **APPLICATO il 2026-08-24**

| # | File | Fase | Cosa |
| --- | --- | --- | --- |
| **04** | `create-vw-bersagli-non-dichiarati` | `20_code/dbops` | I tipi scritti nei **corpi delle funzioni vive** e assenti da `config.tipi_entita`. Gemella di `dbops.vw_eventi_non_dichiarati` (nata col L4) e di `vw_codici_errore_da_dichiarare` |
| — | `db/pgtap/dbops/test-vw-bersagli-non-dichiarati.sql` | test | La vista è **vuota**: se non lo è, la build è rossa e dice quale tipo manca |

⭐ **È questo cancello a rendere sicura la Q-D.** Il catalogo cresce una voce per
volta *perché* dimenticarsene non è possibile: chi scrive un bersaglio su un tipo
non dichiarato lo scopre in CI, non in esercizio.

⚠️ **Statico, non sui dati** (§5.1, T-4): si legge `pg_proc.prosrc`, **non**
`dbops.error_log` — che non dice né se un ramo è mai stato percorso né se conti
qualcosa.

### L4 — La convenzione scritta — ✅ **FATTA il 2026-08-23**

| File | Cosa |
| --- | --- |
| `docs/it/linee-guida-sql.md` §5 | ⭐ **La quarta riga della tabella dei canali**, che oggi ne ha tre (`p_error_code` → backend, `p_context->>'campo'` → frontend, `VARIADIC` → operatore). Il bersaglio è il quarto destinatario, e va **in quella tabella**: è il posto dove chi scrive una guard va a guardare |
| idem | La regola delle classi (Q-E) e la forma dell'array (§4.2), **con l'avvertenza del nome**: `bersaglio`, non `target` — che in 16 punti significa già un'altra cosa |

### L5 — La derivazione automatica — ⛔ **ARCHIVIATA: RESPINTA (Tid, 2026-08-24)**

> ⛔ **Decisione: non si fa.** Il roll-out resta **esplicito, uno alla volta**.
> La sezione resta scritta perché la misura che l'ha respinta vale più della
> proposta: dice **quanto** vale l'esplicito, non solo che si preferisce.

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

#### 📏 LA MISURA — 2026-08-24, sui corpi vivi *(1082 punti di sollevamento, 410 funzioni)*

⭐ **Non su un campione: sul totale**, e con un metro che non richiede giudizio.
I **14 punti che il bersaglio ce l'hanno** sono verità nota — lì qualcuno ha già
deciso, caso per caso, dove va mandato l'operatore. La domanda diventa
verificabile: *applicando la regola candidata a quei 14, quante volte esce lo
stesso bersaglio?*

| Esito | Punti | Quali |
| --- | ---: | --- |
| ✅ **Identico** | **9** | I due `E_FLUSSI_*`, `E_FATTURA_SENZA_RIGHE`, i due `E_SCADENZE_*`, i due `E_LOTTO_NON_RIUTILIZZABILE`, i due `E_DDT_*` |
| ⛔ **Nessun bersaglio** | 1 | `E_DEFINIZIONE_BOZZA_ESISTENTE`: il contesto porta `tipo_prestazione_id` e `emittente_fiscale_id` — **l'entità di destinazione non è nominata da nessuna parte**. È il caso che il brief chiama «il più netto del roll-out», ed è esattamente quello che la derivazione non sa fare |
| ⚠️ **Parziale** | 1 | `E_FATTURA_RETTIFICATA_SENZA_NUMERO`: darebbe il solo `fattura_id`, cioè il documento **su cui** l'errore è successo, e perderebbe i **padri bloccanti** — la metà azionabile. ⛔ E prima del `T-3b` avrebbe dato l'elemento **sbagliato dei due** |
| ⛔ **Entità sbagliata** | 2 | `E_OFFERTA_CONTRATTO_GIA_GENERATO` e `E_OFFERTA_ORDINE_GIA_GENERATO`: il contesto ha `offerta_id`, ma il bersaglio vero è il **contratto** (o l'ordine) **già generato**. Il commento nel corpo lo dice con le stesse parole: *«si manda l'operatore sull'ORDINE che esiste, non sull'offerta che ha già aperto»* |
| ⚠️ **Guardia persa** | 1 | `E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO`: tipo e valore sarebbero giusti, ma il bersaglio vero nasce da una `SELECT` che verifica che il preventivo **esista** — quell'errore copre due casi, «non c'è» e «c'è ma è nello stato sbagliato». Senza la guardia, nel primo caso comparirebbe un pulsante **che non apre niente** |

➡️ **9 su 14: due terzi.** E i cinque mancati sbagliano in **quattro modi
diversi**, che è il dato peggiore: non c'è una correzione sola da aggiungere
alla regola.

⛔ **E c'è il lato che la proposta non guardava: i punti che il bersaglio NON ce
l'hanno.** La derivazione, per come è pensata, non si applica ai 14 — si applica
a **tutti**. Sui 1068 punti senza bersaglio farebbe fuoco su **138**:

| Classe del codice | Punti | Perché non dovrebbe farne nessuno |
| --- | ---: | --- |
| `DATO_ERRATO` | 49 | È un campo sbagliato in un form: l'operatore è **già sulla cosa**, e il canale giusto è `COLUMN` |
| `CONFLITTO_STATO` | 35 | L'unica classe legittima — ma il roll-out **li ha già riletti uno per uno** (§L6) e conclusi «esclusioni motivate»: la derivazione riaprirebbe a tappeto proprio la lista che si è deciso di non fare |
| `TECNICO` | 22 | ⛔ Vietati dalla **Q-E**: su un 500 non c'è nessun gesto |
| `NON_TROVATO` | 17 | ⛔ *Se la cosa non si trova, non ci si può andare*: un pulsante verso un id che non esiste |
| altri (`NON_ESEGUIBILE`, `NON_PERMESSO`, fuori catalogo) | 15 | |

⭐ **Il numero che decide non è 9 su 14: è 138 pulsanti che nessuno ha vagliato**,
di cui al massimo 35 in una classe ammissibile. E il §5.5 dice perché non sono
neutri: *un bersaglio inutile insegna a ignorare il pulsante*. Sommato
all'asimmetria già scritta qui sopra — sul canale `COLUMN` un valore sbagliato è
**inerte**, un bersaglio sbagliato è **attivo** — la derivazione automatica
comprerebbe 9 punti già coperti al prezzo di 138 non verificati.

➡️ ⛔ **DECISO da Tid il 2026-08-24: L5 è ARCHIVIATA, respinta**, con questa
misura come motivazione. Il roll-out resta **esplicito, uno alla volta** — che è
anche ciò che il §L6 ha già deciso per conto suo. ⚠️ Da rifare **solo** se cambia il
presupposto: un catalogo che dichiari, per codice, quale chiave del contesto è
il bersaglio — che però non è più una derivazione, è il roll-out scritto altrove.

*(Misura riproducibile: i corpi vivi in `docs/it/dbzero/*/funzioni/*.md`, le
classi da `error_policies_generated.py`.)*

### L6 — Il roll-out *(T-5)* — 🏁 **a FINE CORSA** *(il passo DB che resta è il `T-3b`)*

> ⚠️ **Che cosa si «rolla», e cosa NO** *(domanda di Tid, 2026-08-24 — vale la
> pena averla scritta, perché in questo progetto «log» sono due cose diverse).*
>
> Il roll-out tocca **il codice**: per ogni codice errore scelto si rivede **la
> funzione che lo solleva**, aggiungendo `bersaglio` al contesto. Da lì in poi
> gli errori di quel tipo lo portano.
>
> ⛔ **Le righe già scritte in `dbops.error_log` non si toccano**, e non è una
> rinuncia: una riga di log è la **fotografia di un momento** e il bersaglio si
> compone al sollevamento, coi dati di allora — ricostruirlo dopo vorrebbe dire
> inventare cosa il database *avrebbe detto*, magari su un ramo che nel
> frattempo è cambiato. E i due lettori del bersaglio sono vivi: il pulsante
> esiste solo nell'istante dell'errore. È il §5.4, *«non si tocca `error_log`»*.
>
> ⚠️ **Da non confondere con `vendite.event_log`**, il giornale dell'altro
> cantiere: quello le entità le nomina di suo, in colonne dedicate
> (`entity_type` / `entity_id`), e il roll-out non lo riguarda. I due condividono
> il **vocabolario** (`config.tipi_entita`), non il meccanismo.

Il pilota ha dimostrato che il disegno regge. Da qui in avanti è un lavoro **a
scaglioni**, un messaggio per volta, con la regola di §5.5: **solo sulle classi
rimediabili**.

**Misurato il 2026-08-24 sui corpi delle funzioni vive** — non su `error_log` —
cercando i punti di sollevamento che passano un **id interno** fra i valori
della frase:

| Classe | Punti | Codici | Funzioni |
| --- | ---: | ---: | ---: |
| `DATO_ERRATO` | 235 | 24 | 135 |
| `NON_TROVATO` | 39 | 22 | 38 |
| `CONFLITTO_STATO` | 37 | 29 | 24 |
| `NON_PERMESSO` | 2 | 2 | 2 |
| `NON_ESEGUIBILE` | 1 | 1 | 1 |
| ~~`TECNICO`~~ ⛔ **fuori perimetro** (Q-E) | ~~21~~ | ~~7~~ | ~~16~~ |

⭐ **Non sono 314 interventi.** I `DATO_ERRATO` sono 235 punti su **24 codici**:
la maggior parte è un id di *parametro sbagliato*, dove il bersaglio non serve —
l'operatore sta guardando quel campo, e il canale giusto è `COLUMN`. ⚠️ La
selezione si fa **per codice**, non per punto, ed è una lettura da fare a mano:
un conteggio non sa distinguere «l'id della cosa che devi aprire» da «l'id che
hai sbagliato a scrivere».

#### Primo scaglione — ✅ **APPLICATO E VERDE il 2026-08-24**

| # | File | Cosa |
| --- | --- | --- |
| — | `config/tipi_entita.csv` | **+3 tipi**: `PREVENTIVO` (**`uid`**), `CONTRATTO` (`id`), `ORDINE_VENDITA` (`id`). ⛔ Nessun changeSet: il mirror `20260822-55` è `runOnChange` e si estende in place |
| **01** | `update-fn-push-offerta-bersaglio` | I due guard di idempotenza di `fn_push_offerta_a_contratto` |
| **02** | `update-fn-push-preventivo-bersaglio` | Il rifiuto di `fn_push_preventivo_a_ordine` |
| **03** | `update-fn-genera-ddt-bersaglio` | I due rifiuti di evasione di `fn_genera_ddt_da_ordine`; `E_DDT_ORDINE_NOT_FOUND` escluso |
| — | i **tre** pgTAP esistenti | estesi, non duplicati: `test_fn_push_offerta_a_contratto` 9→10, `test-fn-push-preventivo-a-ordine-v1` 9→11, `test-fn-genera-ddt-da-ordine-v1` 24→26 |

⭐ **La cosa che questo scaglione ha insegnato, e che il piano non aveva:**

> **Il bersaglio non è l'entità nominata nella frase.**

I due messaggi dell'offerta dicono *«L'offerta 412 ha già generato il
contratto»*. Puntare all'offerta sarebbe stato naturale — è il soggetto — e
**inutile**: l'operatore l'offerta ce l'ha davanti, è da lì che ha premuto il
pulsante. Quello che non riesce a raggiungere è il **contratto già generato**.
Il bersaglio risponde a *«dove devi andare»*, non a *«di cosa stiamo
parlando»*. ⚠️ È la ragione per cui il roll-out si fa **codice per codice**: un
conteggio non sa distinguere le due cose.

⭐ **E il preventivo è il primo uso reale di `key_selector`** — ~~si cita per
`uid`~~ ⚠️ **corretto il 2026-08-24 su rilievo del backend: si cita per `id`.**
La colonna ha fatto comunque il suo mestiere, solo al secondo giro: vedi il
riquadro qui sotto.

⚠️ **Due rami senza bersaglio, e sono voluti**: il preventivo che **non esiste**
(o non è visibile sotto RLS) — l'errore copre due casi con lo stesso codice, e
solo uno ha un posto dove mandare qualcuno. Presidiato dal test 11.

⚠️ Nella frase resta l'id numerico: **due canali, due lettori**. Toglierlo è il
`T-3b` — che ~~aspetta il frontend~~ ✅ **non aspetta più nessuno dal
2026-08-24**: B-1 e B-2 sono in servizio (§7-bis), quindi il pulsante c'è e il
§5.3-bis è soddisfatto.

**I DDT chiudono la famiglia** — ✅ scritti (`20260824-03`):
`E_DDT_ORDINE_STATO_NON_EVADIBILE` e `E_DDT_NIENTE_DA_EVADERE` portano il
bersaglio sull'**ordine**, e `E_DDT_ORDINE_NOT_FOUND` **no**.

⭐ **L'obiezione da tenere in mente, perché tornerà**: *«l'operatore l'ordine lo
sta già guardando, che senso ha un pulsante “vai all'ordine”?»*. Ce l'ha quando
l'evasione parte **in massa**: lì la frase dice **quale** ordine ha rifiutato e
non ci porta. È lo stesso caso del 937 dentro un giro di lotto — e vuol dire che
il bersaglio vale anche su errori che *sembrano* già contestualizzati.

⭐ **E lì il bersaglio non costa niente**: si compone una volta sola subito dopo
la lettura dell'ordine — a quel punto esiste **ed è visibile** — senza nessuna
query in più e senza rami condizionali.

#### Secondo scaglione — «gli errori dentro un giro» — ✅ **APPLICATO E VERDE**

Il primo scaglione aveva convertito errori che nascono da **un gesto** (apri
un'offerta, premi «genera»). Questi no: nascono **dentro un giro automatico**,
dove l'operatore non sta guardando nessuna delle entità nominate.

| # | Funzione | Codice | Bersaglio |
| --- | --- | --- | --- |
| **07** | `fn_get_or_create_lotto` | `E_LOTTO_NON_RIUTILIZZABILE` | `LOTTO` — **su entrambi** i punti in cui è sollevato |
| **05** | `fn_assign_numero_fattura` | `E_FATTURA_SENZA_RIGHE` | `FATTURA` |
| **06** | `fn_genera_scadenze_fattura` | `E_SCADENZE_BASE_NON_PRONTA`, `E_SCADENZE_TERMINE_MANCANTE` | `FATTURA` |
| — | `test-genera-scadenze-fattura-v1` | | **esteso 14 → 16** |

⭐ **È qui che l'obiezione «ma ce l'ha già davanti» cade del tutto**: il lotto
che blocca un'emissione l'operatore non lo sta guardando affatto, e la fattura
senza righe è una fra molte dentro il giro.

⚠️ **Due esclusioni nuove, e la prima è una lezione di costo**:

| Escluso | Perché |
| --- | --- |
| `E_COMMESSA_NON_MODIFICABILE`, `E_ONERE_SEGMENT_DUPLICATO` | Il bersaglio avrebbe senso (la commessa), ma vivono in `fn_upsert_commessa_attivita` — **firma da 40 parametri**. Toccarla obbliga alla passata `%TYPE` su tutte: lavoro e rischio sproporzionati all'aggiunta di un bersaglio. Aspettano un giro in cui quella funzione si tocchi per un motivo suo |
| `E_VALORE_MANCANTE` | ⛔ Vive **nella stessa funzione** del 06 e ha un context **identico** ai due convertiti — ma parla di un **campo**, non di un'entità: il suo canale è `COLUMN`. Per questo la sostituzione è ancorata al **codice** e non alla riga di contesto: un'ancora più larga gli avrebbe messo il bersaglio addosso |

⭐ **Il secondo caso è il più istruttivo dell'intero roll-out**: due punti su tre
di una funzione hanno lo stesso identico contesto, e solo due su tre vanno
convertiti. È la prova che *«un roll-out a tappeto»* non esiste — la domanda si
fa a ogni ramo, e qui il test **16** la presidia.

#### Terzo scaglione — «gli errori che nascono da una lista» — ✅ **APPLICATO E VERDE**

| # | Funzione | Codici | Bersaglio |
| --- | --- | --- | --- |
| **08** | `pratiche.fn_prendi_in_carico_flusso` | `E_FLUSSI_PRESA_CARICO_STATO_ERRATO`, `E_FLUSSI_GIA_ASSEGNATO` | `FLUSSO` — composto una volta, riusato da entrambi |
| **09** | `pratiche.fn_fork_definizione` | `E_DEFINIZIONE_BOZZA_ESISTENTE` | `DEFINIZIONE_WORKFLOW` — le bozze che bloccano |
| — | `config/tipi_entita.csv` | | **+2 tipi**: `FLUSSO`, `DEFINIZIONE_WORKFLOW` (9 in totale) |

⭐ **E qui c'è il caso più netto dell'intero roll-out.** La frase del `09` è:

> *«Esiste già una bozza di edizione workflow per lo scope (tipo prestazione 12,
> emittente 32).»*

Nomina lo **scope**, e la bozza che blocca **non la nomina affatto** — e non è un
difetto del messaggio: quel documento un nome utile non ce l'ha, e metterci un id
tecnico sarebbe proprio il difetto che questo cantiere esiste per togliere.

⭐ **Quindi il bersaglio, lì, non aggiunge comodità: aggiunge un'informazione che
la frase — per come è costruita — non può dare.** È il caso che mostra meglio
perché i due lettori vogliono due canali, e non una frase più ricca.

⚠️ **I due tipi nuovi non esistono in `config.sorgenti`**, quindi non c'è nessun
codice con cui doverli far coincidere: la regola della coincidenza vale dove i
due cataloghi si intersecano, e qui non si intersecano.

⚠️ **`fn_fork_definizione` è `SECURITY DEFINER`** — misurato, non dedotto: è di
`titodb` e **non** è nel registro `dbops.sec_functions_owner`, quindi il
`CREATE OR REPLACE` la lascia dov'è. Da non confondere con le `SECURITY DEFINER`
di `postgres`, che dopo la riscrittura vogliono `dbops.fn_sync_functions_owner`.

#### 🔴 La correzione del backend sul `key_selector` — e l'errore ha un nome

**Rilievo del BE, 2026-08-24**, e ha ragione. Il `20260824-02` faceva citare il
preventivo per **uid**, con la motivazione *«è la chiave nativa con cui il
progetto lo indirizza da fuori»*. Misurato — da loro, e riverificato qui:

| Cosa | Misura |
| --- | --- |
| Rotte del preventivo | tutte `<int:preventivo_id>` |
| Prop del drawer | `Number` |
| Endpoint che accettano un **uid** di preventivo | **zero** |
| `uid` vs `id` su `vendite.preventivi` | **165 / 165 / 165** — l'uid è un surrogato 1:1, non un'identità che sopravvive alle revisioni |

⛔ Un bersaglio a uid avrebbe prodotto **un pulsante che non apre niente** —
cioè esattamente il difetto che `key_selector` esiste per evitare, e che la
testata del `20260823-01` dichiara a chiare lettere.

⭐ **L'errore ha un nome, ed è istruttivo: ho riempito la colonna con la
risposta dell'ALTRO catalogo.** `config.sorgenti.key_selector` dice con quale
chiave il **lineage** collega un documento; `config.tipi_entita.key_selector`
dice con quale chiave lo si **raggiunge**. Stesso nome — scelto apposta, perché
è la stessa convenzione — ma **due domande diverse**: è la distinzione che
entrambi i brief dichiarano fin dal principio (*«vocabolari che si intersecano,
domande no»*), e il valore l'ho copiato da uno all'altro lo stesso.

➡️ **La regola che ne esce, e vale per ogni tipo futuro:**

> **Il valore di `key_selector` si MISURA sulle rotte del frontend.
> Non si eredita da `config.sorgenti`, e non si deduce dall'esistenza di una
> colonna `uid`.**

⚠️ **E ora nessun tipo usa `uid`**: tutti e nove hanno `id`. La colonna resta, e
vale la pena dire perché invece di lasciarlo intuire: oggi registra un fatto
**verificato** invece di una supposizione — e la differenza si vede solo il
giorno in cui qualcuno sbaglia, che è appunto oggi. Il giorno in cui una
superficie pubblica (portale, shop) indirizzerà un documento per uid, quella
riga cambia con **un seed** e nessuna funzione si tocca.

⭐ **Nota di metodo**: il difetto l'ha trovato **il primo consumatore**, ed è la
prova che il canale serviva — un bersaglio scritto e mai letto non avrebbe mai
detto di essere sbagliato. È anche il primo ritorno utile dalla consegna B-1.

#### 🏁 Il roll-out è a FINE CORSA — misurato il 2026-08-24

Non «finito»: **a fine corsa**. Dei `CONFLITTO_STATO` che passano un id restano
**21 punti su 15 codici**, e riletti con la lente sono quasi tutti **esclusioni
motivate**, non lavoro arretrato:

| Cosa resta | Quanti | Perché non si converte |
| --- | ---: | --- |
| La famiglia **resi** (`E_RESO_*`, `E_ACCREDITO_*`) | 9 punti | I messaggi non nominano un'altra entità: l'operatore è **sul reso**. Un pulsante «vai al reso» da dentro il reso non è un gesto |
| `E_COLONNA_NON_MODIFICABILE`, `E_OFFERTA_TRANSIZIONE_NON_AMMESSA` | 2 | I `%s` sono un **nome di colonna** e due **stati**, non entità. Il canale del primo è `COLUMN` |
| `E_DEFINIZIONE_NON_PUBBLICABILE`, `E_DEFINIZIONE_NO_PUBBLICATA`, `E_PREV_NESSUNA_RIGA_ATTIVA` | 3 | Il documento nominato è **quello che l'operatore ha aperto** |
| `E_COMMESSA_NON_MODIFICABILE`, `E_ONERE_SEGMENT_DUPLICATO` | 2 | ⚠️ Esclusione di **costo**: `fn_upsert_commessa_attivita` ha 40 parametri (vedi sopra) |
| 🔵 `E_FORNITORE_NON_ATTIVO`, `E_ACCREDITO_GIA_ESEGUITO` | 2 | **Gli unici due candidati veri rimasti**, e nessuno dei due è ovvio: il primo vorrebbe un tipo `SOGGETTO` e una rotta all'anagrafica, il secondo dipende da dove si apre la coda accrediti |

⭐ **La conclusione operativa**: continuare a tappeto vorrebbe dire aggiungere
pulsanti che non aiutano — e il §5.5 dice che un bersaglio inutile non è
neutro, perché insegna a ignorare il pulsante. **Il roll-out riprende quando lo
chiede un caso**, non per completare una lista.

⚠️ **E la classe `NON_TROVATO` (39 punti, 22 codici) resta fuori quasi per
intero**, per una ragione di principio già emersa tre volte: *se la cosa non si
trova, non c'è nessun posto dove mandare l'operatore*.

#### ⛔ Tre esclusioni su tre codici toccati — il roll-out non è meccanico

| Ramo escluso | Perché |
| --- | --- |
| il ramo **fail-closed** del 937 | il padre non è visibile: il valore in mano non è nemmeno un id di fattura |
| il **preventivo inesistente** | l'errore copre due casi, e solo uno ha una destinazione |
| **`E_DDT_ORDINE_NOT_FOUND`** | l'ordine non c'è, o la RLS lo nasconde — per chi opera è la stessa cosa |

⚠️ **È la lezione operativa del primo scaglione**: la domanda *«c'è un posto
dove mandarlo?»* va fatta **a ogni ramo**, non a ogni codice. Un roll-out fatto
a tappeto avrebbe prodotto tre pulsanti che aprono il vuoto.

➡️ ~~**Primo scaglione proposto**: i `CONFLITTO_STATO`, 29 codici.~~ *(scelto, e in corso.)* Sono per definizione Sono per
definizione *«questa cosa è in uno stato che non permette l'operazione»* — cioè
esattamente i casi in cui l'operatore deve **andare a vedere quella cosa**. È la
stessa famiglia del pilota.

⚠️ Ogni conversione porta con sé, quando serve, **la riga di catalogo del tipo**
(§5.1 T-1c): due file, e il presidio L3 fa fallire la build se ci si dimentica.

### L7 — Il `T-3b`: l'id esce dalla prosa — 🎉 **APPLICATO E VERDE il 2026-08-24**

È il passo per cui il cantiere esiste, ed è l'unico **sottrattivo**: fin qui si
era sempre aggiunto. Passaggio, misure e domande sono in **§7-ter**; qui ci
sono le decisioni e i file.

| # | File | Fase | Cosa |
| --- | --- | --- | --- |
| **13** | `update-fn-numera-fattura-t3b` | `20_code/vendite` | `vendite.fn_numera_fattura_opz_emessa` costruisce il bersaglio a **due ruoli** — il documento da numerare **in testa**, poi i padri bloccanti visibili in ordine di id — e passa al `VARIADIC` **un solo valore**, `v_n_bloccanti`. ⚠️ Sparisce il `CASE WHEN v_bersagli IS NULL` del pilota: con il documento in testa l'array non è mai vuoto |
| — | `config/messaggi_errore.csv`, riga **937** | `80_data` (CSV) | Il `messaggio` passa da **due** segnaposto a **uno** (il conteggio) e la `soluzione` si riscrive. ⛔ **Stessa passata del 13**, mai il CSV per primo (§5.3): il mirror `runOnChange` del changeSet **20260614-08** ripesca il file, non nasce nessun loader |
| — | `db/pgtap/vendite/test-numera-nota-credito-riferimento-v1.sql` | test | Da 7 a **8 asserzioni**. I test 6 e 7 passano dall'**insieme** alla **stringa esatta** — l'ordine è diventato una proprietà — e il **test 8** è nuovo: la frase non nomina nessuno dei tre id e porta il conteggio |
| — | `docs/it/linee-guida-sql.md` §5 | doc | L'esempio del bersaglio mostra ora la forma a due ruoli e il conteggio nel `VARIADIC`, e la tabella delle regole guadagna la riga **«in testa la cosa su cui l'errore è successo»** |

#### ⭐ Le due decisioni, e perché non erano dettagli di stesura

**1. Il bersaglio del 937 ha DUE RUOLI.** Il §4.2 lo dichiarava dal primo giro;
il pilota emetteva il solo padre. ⛔ **È ciò che rende POSSIBILE il T-3b**:
tolti entrambi gli id dalla frase con un bersaglio solo, dentro un giro di lotto
— dove l'errore arriva su una fattura fra molte — *quale* non lo direbbe più
nessuno. Il primo elemento è sempre presente **per costruzione**: se
`p_fattura_id` non fosse visibile a chi opera, la `SELECT … FOR UPDATE` più in
alto non l'avrebbe trovato e si sarebbe usciti con `E_FATTURA_NON_TROVATA`.

**2. Una frase sola, col conteggio.** Un `%s` che porta `v_n_bloccanti`, non un
identificativo: *«Documenti da numerare prima: 2»*. ⭐ Non è un ripiego — è
esattamente ciò che le linee guida chiedono, dove giustificano il tetto di
cinque bersagli dicendo *«quanti sono lo dice già la frase»*. Fino a ieri il 937
era l'unico messaggio col bersaglio che quel conteggio non lo diceva.

⛔ **Perché non due messaggi, uno per ramo.** Sarebbe stato più preciso in teoria
— nel ramo fail-closed il rimedio è diverso, non «numera» ma «chiedi a chi
gestisce quel perimetro» — e costava un codice nuovo a catalogo, la sua classe,
le policy rigenerate lato BE e un secondo ramo di sollevamento. La differenza si
dice nella `soluzione`, che è il posto dove questa casa scrive cosa fare.

⚠️ **Il padre invisibile entra nel CONTEGGIO ma non fra i pulsanti**, e i due
tipi di `JOIN` restano opposti come nel pilota: la frase dice *quanti* mancano,
i pulsanti dicono *dove si può andare*. Sono due domande diverse sulle stesse
righe.

#### La prova, non la deduzione

```text
frase   Non si puo' numerare il documento: rettifica righe di altri documenti
        che non risultano ancora numerati. Documenti da numerare prima: 2.
canale  FATTURA:19753,FATTURA:19752,FATTURA:19754
        ^ la nota (19753) NON è l'id più basso: è in testa perché è il soggetto
```

⭐ **Quel dettaglio è il test 7**, e non è un vezzo: la nota è stata creata fra i
due padri apposta, così l'asserzione distingue *«primo perché è il soggetto»* da
*«primo perché è il più piccolo»* — che sarebbe stata una coincidenza.

📌 **Una nota per BE/FE, che non è un blocco.** Su `ErroreRigaInfo` — l'errore
persistito, letto dalla lista fatture del lotto — la riga **è già** quella
fattura, quindi il primo pulsante lì è ridondante; sul toast del runner, dove
nessuno sa quale documento ha rifiutato, è invece l'informazione principale. Se
desse fastidio si nasconde **a video** il bersaglio che coincide con la riga:
non si toglie dal database, che non sa su quale superficie l'errore verrà letto.

#### 📋 Il debito documentale che questo passo lascia fuori dal perimetro DB — ✅ **CHIUSO dal BE il 2026-08-24**

⚠️ **Quattro punti citano la frase VECCHIA del 937**, e da oggi descrivono un
messaggio che non esiste più. Nessuno di loro **rompe** — i test lo fabbricano a
mano, non lo leggono dal catalogo, e infatti restano verdi — ma una finta che
imita una frase ritirata si legge come documentazione, ed è così che una casa si
ritrova a credere in un messaggio che nessuno solleva.

⭐ **Cercandoli, erano SEI.** I due che questa tabella non aveva sono in fondo, e
non è un rimprovero al passaggio: il perimetro DB non poteva vederli. È la
seconda volta in questo cantiere che *«i punti si cercano, non si conoscono»*
(la prima fu il quinto punto di traduzione, §7-bis.1).

| # | Dove | Cosa c'era scritto | Esito |
| --- | --- | --- | --- |
| 1 | `docs/it/backend/vendite/manual/api_lotto_fatture_list.md` | un payload d'esempio con `errore_messaggio` nella forma vecchia | ✅ payload **e** la riga della tabella campi, che prometteva un messaggio *«che nomina il documento»* |
| 2 | `backend/apps/vendite/tests/services/test_bersaglio_pipeline.py` | `hint="Numerare prima il documento indicato…"` — la `soluzione` riscritta | ✅ |
| 3 | `backend/apps/core/tests/services/test_db_error_target.py` | idem, più il `message` a due id | ✅ |
| 4 | `backend/apps/vendite/tests/services/test_pipeline_step_executor.py` | il messaggio completo nella forma vecchia | ✅ e con lui l'**asserzione**: vedi sotto |
| **5** | ⭐ `backend/apps/core/services/error_messages_fallback.py` | il **ripiego** del 937 — quello che si mostra quando il messaggio del catalogo non arriva — diceva *«le righe di **una** fattura … numerare prima **quella**»*: singolare, e senza il caso «fuori dal perimetro» | ✅ riscritto al plurale, senza `%s` |
| **6** | ⭐ `docs/it/backend/vendite/manual/api_fattura_giornale.md` | un secondo payload d'esempio, scritto **il giorno prima** nel cantiere `event_log` e non ancora committato: per questo non poteva essere in lista | ✅ |

⛔ **E non erano solo quattro stringhe.** Due cose andavano oltre la prosa:

* **le finte portano ora DUE bersagli**, `FATTURA:835,FATTURA:820`. Un finto a
  un bersaglio solo riproduce una forma che il database **non solleva più**, e i
  test di trasporto smetterebbero di provare che il **secondo** elemento arriva
  — cioè proprio ciò che il `T-3b` ha aggiunto. Gli assert a valle sono passati
  da uno a due elementi, **in ordine**;
* **un'asserzione diceva il falso.** In `test_pipeline_step_executor` c'era
  `assertIn("835", message)` con il commento *«è l'unica cosa che dice QUALE
  documento numerare prima»*. Oggi quella frase non porta nessun id: il test ora
  verifica che il messaggio del database arrivi **intatto** (`"Documenti da
  numerare prima"`) invece di essere appiattito sul generico del giro
  per-fattura, che è la cosa che quel test è nato per misurare.

✅ **3919 test verdi** dopo l'allineamento (l'unico rosso della suite è il
presidio `NULLS` su un file di un altro cantiere, estraneo a questo).

⚠️ **Un settimo punto NON va toccato**: la riga **R-3** di
[brief-db-event-log-scope-e-riga-parlante.md](brief-db-event-log-scope-e-riga-parlante.md)
cita la frase vecchia raccontando cosa si leggeva sul lotto 6260 il 2026-08-23.
Lì è **storia**, ed è giusta com'è.

### Ordine, dipendenze e cosa resta fuori

```text
01 ──► 55 (CSV)          la chiave dell'entità, e il seme che la riempie
02 ──► 03 ──► 04         il canale, il primo che ci scrive, il cancello
```

* **02 prima di 03**: il pilota scrive in una casella che dev'esistere;
* **01 è indipendente** dagli altri tre: non blocca il pilota, che punta a un
  tipo a chiave numerica;
* **04 dopo 03**, per nascere con qualcosa da misurare — ma non è un vincolo
  tecnico.

⛔ **Cosa NON entra in questo piano**, e sono conferme del §5.4: nessuna FK su
niente, `dbops.error_log` non si tocca, l'envelope API è del backend (§7), e i
756 messaggi **non** si riscrivono — ~~il T-3b, cioè l'id che esce dalla prosa,
resta appeso a B-1/B-2 e non lo chiude questo brief~~.

> ✅ **SUPERATA il 2026-08-24**: il T-3b è il lotto **L7** qui sopra, ed è
> applicato. L'ordine è diventato `02 ──► 03 ──► 13`, cioè il canale, il primo
> che ci scrive, e la sottrazione — con B-1/B-2 in mezzo, che è il vincolo di
> sequenza del §5.3-bis e non una dipendenza di changeSet.

---

## 7. Cosa tocca dopo, e a chi *(dichiarato qui, **pianificato in §7-bis**)*

> ➡️ **Le tre consegne di questa tabella sono diventate un piano il 2026-08-24: §7-bis.**
> Questa resta la dichiarazione — *cosa* serve e a chi; là c'è il *come*, e le
> tre misure che hanno spostato il baricentro del lavoro.

| | Chi | Cosa |
| --- | --- | --- |
| **B-1** | BE | ✅ **Il canale è APPLICATO e provato dal vivo** (`20260823-02`; `diag.datatype_name` letto da psycopg il 2026-08-24). Si legge **`diag.datatype_name`** — lo stesso posto da cui il backend legge già `constraint_name` per il codice e `column_name` per i campi — e si porta nell'envelope accanto a `code` / `message` / `ui_action` / `fields`. ⚠️ **Il contratto vale solo dentro `P0001`**, come per `CONSTRAINT`: fuori di lì quel campo lo riempie PostgreSQL da sé. Forma: `TIPO:id[,TIPO:id]`, al massimo cinque; stringa vuota = nessun bersaglio. ⭐ È **lo stesso lavoro già fatto due volte** — `CONSTRAINT`→`code` (05/08) e `COLUMN`→`fields` (08/08) |
| **B-2** | FE | il gesto: dal bersaglio a una destinazione. ⚠️ **E non è una rotta**: misurato il 2026-08-24, `FATTURA` una rotta non ce l'ha — si apre solo in un drawer. ⭐ La tabella però esiste già ed è il registro `DOCUMENTO_DRAWERS`: si riusa, non si scrive (§7-bis.3) |
| **B-3** | FE | il degrado di §4.3 — bersaglio non risolvibile → nessun pulsante, messaggio invariato |

⭐ **Un effetto laterale che vale da solo**: `ui_action` oggi è un canale
prodotto e non consumato — 126 codici promettono «evidenzia il campo» e nessun
componente legge `azioneUi`. Un errore che porta un bersaglio è il primo pezzo di
frontend che ha una **ragione** per leggere quel canale, e rende scrivibile il
presidio **C2** di
[analisi-presidi-percorso-storto.md](analisi-presidi-percorso-storto.md).

### B-1 · Backend — dal canale all'envelope ✅ **eseguibile**

**Dove.** `backend/apps/core/services/db_error_fields.py` — è il modulo che
possiede già la lettura degli altri due canali strutturati
(`structured_db_error_code`, `structured_db_error_field`) ed è
*volutamente senza dipendenze interne*. Il terzo lettore va lì, accanto ai suoi
gemelli, e non altrove.

**Cosa leggere.** `diag.datatype_name` — lo stesso `diag` da cui il modulo legge
già `constraint_name` e `column_name`.

**Il contratto**, identico nella forma a quello del 05/08 e dell'08/08:

> **`P0001` + `datatype_name` valorizzato = le entità a cui l'errore si
> riferisce.**

⛔ **E vale SOLO dentro `P0001`.** Fuori di lì quel campo lo riempie PostgreSQL
da sé — è il suo uso legittimo, le violazioni di dominio — esattamente come
`constraint_name` su un `23xxx` contiene il nome del vincolo. Il modulo ha già
questa difesa per il codice: qui va ripetuta, non reinventata.

**La forma sul filo**: `TIPO:id[,TIPO:id]`, **al massimo cinque**. Stringa
vuota = nessun bersaglio (come per `column_name`, un valore che nasce da
un'espressione NULL arriva vuoto, non assente).

**La validazione, speculare a quella del database.** Il modulo ha già
`_COLUMN_RE` per il campo; qui servono le due gemelle —
`^[A-Z][A-Z0-9_]{0,30}$` per il tipo e `^[0-9a-fA-F-]{1,36}$` per l'id — e
valgono per la stessa ragione già scritta lì: *le due metà dello stesso canale
vanno guardate uguale*. ⚠️ Un elemento che non passa si **scarta in silenzio**:
il percorso d'errore non può fallire per colpa del bersaglio, ed è la regola che
il lato DB rispetta già.

**Nell'envelope**, accanto a `code` / `message` / `ui_action` / `fields` /
`hint`:

```json
"targets": [{"type": "FATTURA", "id": "835"}]
```

⚠️ **Due nomi diversi per la stessa cosa, e non è una svista**: la chiave nel
contesto del database è `bersaglio` (italiano, come `campo` e `parametro`, e
perché `target` là dentro è già occupata da altro); il campo dell'envelope è
`targets` con dentro `type`, perché l'envelope è in inglese (`fields`, `hint`,
`ui_action`). La traduzione avviene **al confine**, in `error_translator.py`.

> 🔧 **Rettifica del 2026-08-24 (BE).** Questo paragrafo diceva `target` al
> **singolare**. Il nome deciso da Tid — e quello **già in servizio** — è
> **`targets`**, al plurale come `fields`: il campo è sempre un array (§4.2,
> decisione del 2026-08-22), e un plurale che porta una lista è ciò che il
> resto dell'envelope fa già. ⚠️ Il codice non è stato cambiato per seguire il
> testo: è il testo ad essere allineato al contratto in servizio, perché
> l'envelope è **pubblicato** (`/api/schema/`) e rinominarlo costerebbe una
> rottura per chi lo legge. Vedi §7-bis.6, **Q-F**.

⛔ **Cosa il backend NON deve fare:**

| Non fare | Perché |
| --- | --- |
| **Risolvere la rotta** | Il backend non sa che schermate esistono. Consegna `type` + `id`, la rotta è del frontend |
| **Fallire su un tipo sconosciuto** | Un tipo che il frontend non conosce degrada a «nessun pulsante» (B-3). Un 500 al posto di un errore di dominio sarebbe il difetto peggiore |
| **Leggere `dbops.error_log`** | Il contesto ricco resta al database, per chi diagnostica. Il canale basta |

### B-2 · Frontend — da `type` a un gesto

Una **tabella sola** `type → rotta`, e il pulsante *«Vai al documento»*.

⭐ **È la stessa tabella della futura timeline per entità**
([analisi-osservabilita-log.md](../work-done/analisi-osservabilita-log.md), Passo A): i due
consumatori condividono il vocabolario `config.tipi_entita`, quindi la mappa si
scrive **una volta**. Se nascesse due volte, divergerebbe — ed è la ragione per
cui il `tipo` è logico e non è mai un nome di tabella (§4.2).

⚠️ **L'id è opaco.** Per `PREVENTIVO` è un `uid`, per gli altri otto è un `id`
numerico: la differenza è dichiarata nel catalogo (`key_selector`) e il
frontend non deve dedurla dal formato del valore.

**Vocabolario al 2026-08-24** — nove tipi: `LOTTO`, `COMMESSA`, `FATTURA`,
`TASK_RUN`, `PREVENTIVO`, `CONTRATTO`, `ORDINE_VENDITA`, `FLUSSO`,
`DEFINIZIONE_WORKFLOW`. ⚠️ Cresce **una voce per volta**, insieme al messaggio
che la usa: la mappa del frontend può restare indietro, e quando succede il
degrado di B-3 fa il suo mestiere.

### B-3 · Frontend — il degrado, che è parte del disegno

**Nessun pulsante** quando: il tipo non è nella mappa, l'utente non ha il
permesso, il record non è nel suo perimetro emittente, la riga non esiste più.
⛔ **Il messaggio si mostra sempre e non cambia.**

⭐ **Non è una gestione dell'errore: è il patto.** Il bersaglio è **un'offerta,
non una promessa** (§4.3) — il database lo scrive senza sapere chi leggerà, e
tre rami del roll-out sono stati lasciati **apposta** senza bersaglio proprio
per non offrire un pulsante che porta nel vuoto.

### E un effetto laterale che vale da solo

`ui_action` oggi è un canale **prodotto e non consumato**: 126 codici promettono
«evidenzia il campo» e nessun componente legge `azioneUi`. Un errore che porta
un bersaglio è il primo pezzo di frontend che ha una **ragione** per leggere quel
canale, e rende scrivibile il presidio **C2** di
[analisi-presidi-percorso-storto.md](analisi-presidi-percorso-storto.md).

## 7-bis. Il piano di sviluppo BE/FE *(scritto il 2026-08-24)*

> ✅ **FATTO IL 2026-08-24, tutto tranne il `T-3b`.** Sette lotti di backend
> (B1..B7) e sei di frontend (F1..F6), **3.912 test verdi** — inclusa la passata
> con `ZEROERP_TEST_DB_E2E=1`, che stavolta è **verde piena**: il rosso atteso
> («DB avanti rispetto a git») era il file delle policy indietro, e i due CSV di
> `W_BERSAGLIO_MALFORMATO` lo hanno riallineato.
> ⭐ **Provato dal vivo, non dedotto**: chiamata reale a
> `script.fn_log_and_raise_error` da psycopg → `diag.datatype_name` =
> `FATTURA:835,FATTURA:820`, e il test end-to-end la ripete a ogni corsa.
> ⛔ **Resta fuori il `T-3b`** — l'id che esce dalla prosa del 937 — che è un
> passo **del database** e ora è sbloccato: B-1 e B-2 sono in servizio (§5.3-bis).

> **Cos'è.** La §7 dichiarava tre consegne — `B-1` al backend, `B-2` e `B-3` al
> frontend — e diceva bene *cosa* serve. Questo è il piano per farle, scritto
> dopo aver **misurato il terreno**, e la misura ha spostato il baricentro: il
> lavoro grosso non è leggere la casella nuova (sono dieci righe), è che **i
> punti in cui un errore del database diventa un errore dell'applicazione sono
> quattro**, e tre dei quattro buttano via la diagnostica strutturata prima che
> arrivi all'envelope. ⛔ **Fra i tre c'è la strada del pilota.**
>
> ⚠️ **Perimetro.** Qui non si tocca nessun file di `db/`: il lotto DB è
> applicato e chiuso. Si tocca `backend/` e `frontend/`, più `api.md` e
> `frontend-standards.md`, che sono i due documenti dove questa convenzione va a
> vivere.

### 7-bis.1 🔴 Il rilievo: i punti di traduzione sono cinque, non uno

Un errore sollevato da `script.fn_log_and_raise_error` arriva al backend come
`DatabaseError` con la sua diagnostica: codice su `CONSTRAINT`, campo su
`COLUMN`, bersaglio su `DATATYPE`, causa su `DETAIL`, soluzione su `HINT`.
**Poi qualcuno lo traduce**, e la traduzione decide cosa sopravvive.

| | Dove | Cosa porta all'envelope oggi | Cosa perde |
| --- | --- | --- | --- |
| 1 | `ErrorTranslator._from_database_error` — il `DatabaseError` che arriva **nudo** al middleware | `hint`, `fields` | — |
| 2 | `payload_helpers.translate_db_errors` — **46 punti** di chiamata nei domini | `hint` soltanto | ⛔ `fields` |
| 3 | `ErrorManager.raise_from_database_error` — **9 punti** | niente | ⛔ `hint`, `fields` |
| 4 | `pipeline_step_executor._run_per_fattura_task` — ⭐ **la strada del 937** | il solo `message_primary` | ⛔ `hint`, `fields` |
| 5 | `pratiche._raise_known_db_error` — **12 punti** | `hint` soltanto | ⛔ `fields` |

> ⚠️ **Il quinto non era in questa tabella quando è stata scritta.** È emerso il
> 2026-08-24 col roll-out del terzo scaglione, che passa proprio di lì
> (`E_FLUSSI_*`, `E_DEFINIZIONE_BOZZA_ESISTENTE`). ⭐ **È la conferma della
> regola che questa sezione stessa enuncia**: il BB unifica la **lettura**, non
> il **trasporto** — e un punto di traduzione va **cercato**, non aspettato.
> Da lì la scelta di tenere **un test per punto**: il prossimo che nascesse
> senza il suo tornerebbe a perdere il bersaglio in silenzio.

⚠️ **E non sono cinque copie da riparare cinque volte**: dietro ci sono **42
`except DatabaseError`** nei service. Un rimedio per punto di cattura è
esattamente la forma in cui questa casa ha già visto divergere il codice.

⭐ **Ne esce un difetto già vivo, che non è del bersaglio.** Il canale `COLUMN`
esiste dall'08/08 e — col ripiego su `parametro` — lo valorizzano **quasi tutti**
i punti di sollevamento del database. Ma `api.md` scrive *«il backend lo legge
già»*, ed è vero **per un lettore su cinque**: appena un service traduce (cioè
sempre, in ogni dominio) il nome della colonna **si perde**. Il frontend, che ha
136 binding pronti su `campiErrati`, su un errore nato in PL/pgSQL non riceve
niente. ⛔ **Il bersaglio, scritto nello stesso posto, farebbe la stessa fine.**

➡️ **La sede unica esiste già, e ha pure il parametro giusto.**
`ErrorManager.raise_error` accetta `cause`, e **33 punti gliela passano**. Se è
da lì che si deriva la diagnostica — `hint`, `fields`, `bersagli` — i punti 3 e
4 sono coperti **senza toccarli**, e il punto 2 costa una riga (`cause=exc`, che
oggi non passa). ⭐ **È la mossa del database applicata al backend**: la
composizione in una sede sola, come `fn_log_and_raise_error` compone la casella
per tutti i 1.093 punti di sollevamento.

### 7-bis.2 I lotti del backend

| # | Lotto | File | Cosa |
| --- | --- | --- | --- |
| **B1** | La **lettura** della casella | `apps/core/services/db_error_fields.py` | `structured_db_error_target(exc)` — gemella di `structured_db_error_code` e `structured_db_error_field`. Legge `diag.datatype_name`, ritorna una tupla di `{tipo, id}` (vuota → `None`). ⛔ **Qui il guard sullo SQLSTATE SERVE**, al contrario di `COLUMN`: fuori da `P0001` quel campo lo riempie PostgreSQL da sé (un `22P02` ci mette il nome di un tipo). È il patto scritto in §4.4. ⚠️ La regex è lo **specchio** di quella del database (`^[A-Z][A-Z0-9_]{0,30}$` e id numerico-o-uuid) e il tetto è **cinque**: le due metà dello stesso canale si guardano uguale, com'è già per `COLUMN` |
| **B2** | Il **trasporto** — ⭐ il lotto vero | `service_errors.py` · `error_manager.py` · `payload_helpers.py` | `ServiceError` prende `fields` e `bersagli`; `ErrorManager.raise_error`, quando riceve una `cause` che è un errore DB, li **deriva** (insieme a `hint`, che oggi deriva solo se il chiamante glielo passa a mano); `translate_db_errors` passa `cause=exc`. ⛔ **Il campo `hint` e il campo `fields` esplicitamente passati dal chiamante VINCONO**: la derivazione è un ripiego, non un'imposizione — è la stessa precedenza che il database dà a `campo` su `parametro` |
| **B3** | L'**envelope** | `error_translator.py` | `ApiError` prende il campo nuovo; `to_api_error` lo legge dal `ServiceError` **e** da `_from_database_error`; ⛔ e va **ricopiato in `_apply_policy`**, che costruisce un `ApiError` nuovo — è il punto esatto in cui `fields` si era già perso una volta, e il commento in quel metodo lo dice. ⚠️ **Su un codice di classe `TECNICO` il bersaglio si toglie**: è la Q-E letta dal lato che consegna, e vale anche se un giorno il database sbagliasse a metterlo (non c'è gesto su un 500) |
| **B6** | Il **runner**, che non passa dall'envelope | `pipeline_runner.py` · `vendite/api/views.py` | 🔴 Gli endpoint del runner rispondono **200 anche quando la catena si ferma per errore**: il fallimento è `motivo_stop` + `errore: {code, message, detail}`, costruito a mano in `_drive_lotto_until_done`. È il **quinto** punto di appiattimento, ed è **la strada del pilota**. Il blob prende `hint`, `fields`, `targets` — gli stessi tre nomi dell'envelope, perché il consumatore a video sia uno solo. ⚠️ È un **contratto**: va aggiornato anche l'`inline_serializer` di `@extend_schema` |
| **B7** | Il bersaglio si **persiste** *(strada asincrona)* | `pipeline_runner.py` · `vendite_repository.py` · `types.py` | ⭐ **Il lettore che conta è qui** (§1: «l'operatore cinque minuti dopo»): un giro batch fallisce quando non c'è nessuno davanti allo schermo, e l'unica cosa che resta è una riga scritta. ⚠️ **Costa meno del toast**: nessuna DDL (`fatture_log.meta` e `task_runs.meta` sono già `jsonb NOT NULL`), il punto di scrittura esiste già ed è già fuori dall'`atomic` dello step (`_persist_fattura_error_safely`), e la query della lista fatture **seleziona già `err.meta`** ed estrae già una chiave da lì (`error_code`). Si aggiunge `bersagli` accanto, con la stessa convenzione |
| **B4** | I **test** | `apps/core/tests/…` | ⚠️ `db_error_fakes.FakeDiag` porta oggi **quattro** campi e non ha né `column_name` né `datatype_name`: `test_db_error_field_column.py` si è dovuto scrivere il proprio finto. Alla seconda copia si estende quello condiviso (regola del 2). Unitari sulla lettura (forma buona, tipo minuscolo, id storto, sesto elemento, SQLSTATE non `P0001`); **un test per ciascuno dei punti di traduzione**, che è il difetto che questo piano ha trovato; e un **E2E opt-in** (`ZEROERP_TEST_DB_E2E=1`) contro la funzione vera, sul modello di `test_db_error_fields.py` |
| **B5** | La **documentazione** | `docs/it/dev/api.md` | La riga nuova nella tabella dell'envelope, e la sezione dei canali strutturati che diventa **tre**. ⛔ **E si corregge la riga che oggi dice il falso**: *«il backend lo legge già; le funzioni non lo mandano ancora»* — le funzioni lo mandano dall'08/08, ed è il backend a perderlo per strada |

⭐ **B2 vale da solo, anche a bersaglio spento**: rimette in servizio il canale
`COLUMN` su tutti gli errori nati in PL/pgSQL, cioè accende 136 binding che oggi
esistono e non si illuminano mai.

### 7-bis.3 I lotti del frontend

⚠️ **Due misure prima di progettare**, entrambe fatte sul codice:

| Fatto | Conseguenza sul disegno |
| --- | --- |
| ⛔ **`FATTURA` non ha una rotta.** Non esiste `vendite/fatture`: la fattura si apre **solo** in un drawer, da quattro punti diversi (riga del lotto, tool fatturazione, drawer commessa, chip di lineage) | Il gesto del §2 **non è «vai a una pagina»**, è «apri il documento». La «tabella di rotte» del §3 nasce quindi come **tabella di aperture** |
| ⭐ **E quella tabella esiste già**: `vendite/_shared/documenti/documentoDrawers.js` mappa `DOCUMENTO_DRAWER_TIPI` → drawer + nome della prop dell'id, con il suo host (`DocumentoDrawerHost`) e il suo comando (`useDocumentoDrawer.apri(tipo, id)`) | Il bersaglio **non chiede una mappa nuova**: chiede che i codici di `config.tipi_entita` e le chiavi di quel registro **coincidano**, esattamente come il §5.1-bis chiede che coincidano con `config.sorgenti` |

| # | Lotto | File | Cosa |
| --- | --- | --- | --- |
| **F1** | Il bersaglio **arriva** | `core/composables/useApiHandler.js` | `bersagli` accanto a `campiErrati` e `azioneUi`: stessa forma, stesse regole (si azzera a ogni `execute`, si popola anche in `silent`). ⭐ **Costa una riga e serve 122 file**: è il punto in cui il canale diventa disponibile ovunque senza toccare nessun componente |
| **F2** | Il bersaglio **si risolve** | `core/bersagli.js` *(nuovo)* | `risolviBersaglio({tipo, id})` → `{ etichetta, apri() }` **oppure `null`**. Il `null` è il §4.3, ed è metà del lavoro: tipo fuori mappa, area bloccata (`auth.isAreaBlocked`), veste che non è quella dell'operatore → **nessun gesto**, e il messaggio resta quello di prima. ⚠️ **Mai un pulsante che porta in un vicolo cieco**, e mai un `catch` silenzioso al posto del controllo |
| **F3** | Il bersaglio **si vede** | *(dipende dalla Q-G)* | Il gesto a video. Vedi la decisione aperta: oggi **nessun toast di questa casa sa portare un pulsante**, e `useNotify` espone quattro funzioni che passano solo `{severity, summary, life}` |
| **F4** | Le **etichette** | `locales/it.json` · `en.json` | Le chiavi `config.tipi_entita.*` — **oggi non esistono nel frontend**, e sono l'indirizzo che il database ha già scritto nella colonna `etichetta_key` del catalogo. ⭐ È il patto dei tre livelli già in `frontend-standards`: il DB emette l'indirizzo, il BE lo trasporta senza interpretarlo, il FE lo risolve. ⚠️ Una chiave che non esiste **non dà errore: dà testo mancante** — quindi si semina insieme al tipo, come il §5.1 T-1c fa col catalogo |
| **F6** | Il gesto **sull'errore persistito** | `core/components/ErroreRigaInfo.vue` · `LottoDrawer.vue` | ⭐ **Il posto migliore, e c'era già.** Quel popover è nato il 2026-08-21 da un rilievo di Tid, contro *«l'errore annunciato da un toast e poi sparito per sempre»*: è letteralmente la casa di un errore che si legge dopo. Prende una prop `bersagli` e disegna lo stesso gesto del toast, risolto dallo stesso `risolviBersaglio`. ⛔ **Un resolver solo, due superfici**: se le due divergessero, il pulsante direbbe due cose diverse sullo stesso errore |
| **F5** | La **documentazione** | `frontend-standards.md` · `catalogo-building-block-frontend.md` | Il paragrafo gemello di quello di `campiErrati`, e la riga di `useApiHandler` nel catalogo BB |

⭐ **E un effetto laterale che la §7 aveva già visto**: `azioneUi` è ferma da
mesi perché nessun componente ha una ragione per leggerla. Un errore che porta
un bersaglio è la prima ragione — ma ⚠️ **non si accende `ui_action` in questo
piano**: sono 176 scelte fatte quando nessuno poteva verificarle a video, e
vanno rilette in un passo suo (`api.md` lo scrive già).

### 7-bis.4 Ordine, e cosa dipende da cosa

```text
B1 ──► B2 ──┬─► B3 (envelope) ──► F1 ─┐
            ├─► B6 (runner)   ────────┼─► F2 ──┬─► F3  (toast, host globale)
            └─► B7 (persist)  ────────┘        └─► F6  (ErroreRigaInfo)
                                          F4 ──┘
B4 (test) accompagna B1..B3 · B5/F5 (doc) chiudono
```

* **B2 è il lotto che vale**: è la lettura unica su cui poggiano i tre trasporti;
* ⭐ **Tre produttori, un consumatore.** L'envelope (B3), il blob del runner
  (B6) e la riga persistita (B7) portano gli **stessi tre nomi**; a video il
  gesto lo disegna **un resolver solo** (F2). Se divergessero, lo stesso errore
  direbbe due cose diverse a seconda di come è arrivato;
* ⛔ **Il pilota si misura su B6, non su B3.** Il 937 esce dentro un 200: finché
  non si vede il bersaglio in `errore.targets` di quella risposta, il resto è
  teoria — ed è l'errore che avrei fatto fermandomi all'envelope;
* **F1/F6 non servono a niente senza il loro produttore**, e non fanno danno: un
  campo assente dà un array vuoto;
* **F4 prima di F3 e F6**, o il primo pulsante nasce senza etichetta.

### 7-bis.5 Cosa NON si fa

* ⛔ **Non si tocca `db/`.** ➡️ E il `T-3b` — l'id che esce dalla prosa del 937 —
  **non è più appeso**: aspettava «B-1 e B-2 in servizio» (§5.3-bis) e dal
  2026-08-24 lo sono. È il passo che resta, ed è del team DB;
* ⛔ **Non si accende `ui_action`** (sopra, F3);
* ⛔ **Non si semina il catalogo dei tipi in anticipo**: è la Q-D, e il cancello
  che la rende sicura (`dbops.vw_bersagli_non_dichiarati`) è già in CI;
* ⛔ **Non si estende il bersaglio agli errori nati in Python.** Ci si potrà
  arrivare — `ServiceError` avrà il campo — ma un canale nuovo si accende su un
  produttore solo, e il produttore è il database.

### 7-bis.6 ✅ Le decisioni — chiuse da Tid il 2026-08-24

| # | Domanda | Decisione |
| --- | --- | --- |
| ~~**Q-F**~~ | Il nome del campo nell'envelope | ✅ **`targets`, elementi `{type, id}`.** Le chiavi dell'envelope sono inglesi e restano tali; la collisione che al §4.2 ha imposto `bersaglio` vive nel `context` del database, non qui. ⚠️ Il frontend lo espone come **`bersagli`**, esattamente come fa oggi `fields` → `campiErrati`: la lingua cambia al confine, e il confine è uno solo |
| ~~**Q-G**~~ | Dove si disegna il gesto | ✅ **Toast con azioni, persistente** sui bersagli — `useNotify` impara a portare pulsanti e `useApiHandler` li compone. ⭐ Una sede sola: i **122** file che usano `useApiHandler` lo prendono senza una riga di modifica. ⛔ **Ma non è l'unica sede** — vedi Q-J |
| ~~**Q-H**~~ | Il BB della traduzione | ✅ **Piena: `diagnostica_db(exc)`.** ⭐ **E la ragione che ha deciso è quella giusta, non la mia**: la forma minima (derivare dentro `raise_error`) non toglieva le quattro letture parziali — ne aggiungeva una quinta, lasciando in piedi il difetto sotto un rimedio. E sarebbe stata **implicita**: copriva 3 punti su 4 *a patto* che il chiamante passi `cause=exc`, cosa che fanno 33 chiamate su 173. ⚠️ Il BB unifica la **lettura**, non il **trasporto**: che il valore arrivi all'envelope va comunque scritto in ciascun punto |
| ~~**Q-I**~~ | *(nuova)* Il pilota non passa da un envelope HTTP | ✅ **`errore` del runner porta `hint`/`fields`/`targets`.** 🔴 **Il rilievo che l'ha aperta**: gli endpoint del runner rispondono **200 anche quando la catena si ferma per errore** — il fallimento è un campo del payload (`motivo_stop` + `errore: {code, message, detail}`), perché la catena può aver eseguito qualche step e quel lavoro va raccontato. È un **quinto** punto di appiattimento, costruito a mano in `pipeline_runner._drive_lotto_until_done`, e il piano non l'aveva. ⛔ Senza questa decisione **il 937 non avrebbe mai mostrato un gesto**: `useApiHandler` vede un 200 e non ha niente da leggere |
| ~~**Q-J**~~ | *(nuova)* La strada **asincrona** | ✅ **Il bersaglio si persiste, e arriva anche lì.** ⭐ **Ed è il lettore che conta**: il §1 dice che il caso vero è *«l'operatore cinque minuti dopo, che sta rimediando»* — cioè il giro batch, che fallisce quando non c'è nessuno davanti allo schermo. Il toast è il caso facile. ⚠️ **Costa molto meno del toast**, misurato: `fatture_log.meta` e `task_runs.meta` sono già `jsonb NOT NULL` (**nessuna DDL, nessun passaggio al team DB**); la query della lista fatture **seleziona già `err.meta`** e già ne estrae `error_code`; il punto di scrittura esiste già ed è già nel posto giusto (`_persist_fattura_error_safely`, fuori dall'`atomic` dello step, best-effort). ⭐ E la casa a video è **`ErroreRigaInfo`**, nato il 2026-08-21 proprio contro *«l'errore annunciato da un toast e poi sparito per sempre»*: il gesto lì sta meglio che nel toast |
| ~~**Q-K**~~ | *(nuova)* Chi ospita il drawer aperto dal toast | ✅ **Un `DocumentoDrawerHost` globale in `App.vue`**, accanto a `<Toast />`, pilotato da `useDocumentoDrawer`. ⭐ Riusa tutto ciò che c'è — il registro, la sequenza chunk→mount→apertura, la chiusura globale al cambio di rotta (`registraDrawerChiudibile`) — e vale per qualunque bersaglio da qualunque schermata. ⛔ L'alternativa «il toast naviga, la vista apre» cade su `FATTURA`, che una vista non ce l'ha: bisognerebbe inventarne una solo per ospitare un drawer |
| ~~**Q-L**~~ | *(nuova)* Quali dei quattro tipi si risolvono | ✅ **`FATTURA` e `COMMESSA` col registro esistente; `LOTTO` con un deep-link `?open=<id>` su `LottiListView`** (il modello è già in servizio in `ContrattiListView`); **`TASK_RUN` resta muto** — nessuna schermata, quindi nessun pulsante, che è esattamente il degrado del §4.3 |

⭐ **E una scoperta della Q-L che vale oltre il bersaglio**: le chiavi di
`DOCUMENTO_DRAWER_TIPI` **sono già** i `config.sorgenti.codice_interno`. Cioè la
convergenza che il §5.1-bis chiede fra `config.tipi_entita` e `config.sorgenti`
**è già vera anche sul frontend**, senza che nessuno l'avesse dichiarato: la
tabella tipo→destinazione non è da costruire, è da riconoscere.

---

### 7-bis.7 ✅ Il roll-out del 2026-08-24 — allineati BE e FE, e le due strade che mancavano

> **Cos'è.** Il DB ha portato il bersaglio su **8 funzioni** e il catalogo a
> **9 tipi**. Il BE e il FE sono stati allineati lo stesso giorno; qui restano
> i due punti che **non** si chiudono lato applicazione, perché sono decisioni.

✅ **Verificato dal vivo** — sollevando gli errori veri dal database e leggendo
l'envelope prodotto: **7 codici su 7** del roll-out arrivano col loro bersaglio,
attraverso tutti i punti di traduzione (`DEFINIZIONE_BOZZA_ESISTENTE`,
`FLUSSI_GIA_ASSEGNATO`, `FLUSSI_PRESA_CARICO_STATO_ERRATO`,
`DDT_ORDINE_STATO_NON_EVADIBILE`, `VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO`,
`LOTTO_NON_RIUTILIZZABILE`, `FATTURA_SENZA_RIGHE`).

🔴 **Un QUINTO punto di traduzione, che era rimasto indietro.**
`pratiche_service._raise_known_db_error` (**12 punti di chiamata**) portava il
solo `hint`. ⛔ **Ed è la strada del terzo scaglione**: senza il rimedio, il caso
che questo brief chiama *«il più netto dell'intero roll-out»* —
`E_DEFINIZIONE_BOZZA_ESISTENTE`, dove la frase la bozza che blocca **non la
nomina affatto** — sarebbe arrivato a video senza nessun gesto. Sanato, e ora
c'è **un test per ciascuno dei cinque** punti.
⭐ È la conferma della regola già scritta al §7-bis.1: *il BB unifica la lettura,
non il trasporto* — un punto di traduzione nuovo va **cercato**, non aspettato.

**La mappa del frontend, dopo:** `FATTURA`, `COMMESSA`, `LOTTO`, `CONTRATTO`,
`ORDINE_VENDITA`, `DEFINIZIONE_WORKFLOW`, `FLUSSO`, `PREVENTIVO` — **8 tipi su
9**. ⛔ Resta fuori il solo `TASK_RUN`, e non è un ritardo: nessuna schermata
mostra un giro per id. ⭐ `DEFINIZIONE_WORKFLOW` è la prima
destinazione che è una **pagina** e non un pannello, e la prima che vive in
`amm-software` — dove il route guard non guarda l'area ma `isAdmin`: il pulsante
segue la stessa regola, o porterebbe su «accesso negato».

#### ✅ `FLUSSO` — chiuso il 2026-08-24 (BE + FE)

Il deep-link della dashboard pratiche voleva **`?pratica_id=<X>&flusso_id=<Y>`**
e senza `pratica_id` non faceva nulla (`if (!praticaId) return`), **in
silenzio**. Il bersaglio porta il solo flusso, perché la pratica non è ciò di
cui l'errore parla.

| Dove | Cosa |
| --- | --- |
| BE | `GET /api/v1/pratiche/flussi/<id>/pratica/` → `{pratica_id}`. ⭐ **L'unica rotta dei flussi non annidata sotto la pratica**, e risponde a una domanda sola: *«dove vive questa cosa?»*. Non è un secondo modo di **leggere** un flusso — il dettaglio resta uno solo, con la sua verifica di appartenenza |
| FE | `applyFlussoDeepLink()`: `?flusso_id=` da solo ora risolve la pratica e prosegue dalla porta di sempre. ⭐ Vale **oltre il bersaglio** — un link, una ricerca, una notifica |
| — | `FLUSSO` entra nella mappa delle destinazioni |

⛔ **E il join sulla pratica non è decorativo — misurato**: `pratiche.flussi`
**non ha RLS**, `pratiche.pratiche` sì. Una lettura del solo `flussi`
risponderebbe per qualunque flusso, anche di una pratica fuori perimetro: un id
di troppo, e un pulsante che porta su una schermata che rifiuterà di aprirsi.
Con il join decide la RLS della pratica, e un flusso non raggiungibile è
**indistinguibile da uno che non esiste**.
✅ Provato dal vivo su entrambi i rami: senza contesto operatore il resolver
rifiuta (fail-closed), con il contesto risponde la pratica giusta.

⚠️ **Non si riusa `get_flusso`**, ed è la lezione che questa casa aveva già
imparato una volta (`get_flusso_esito_config`): quella proiezione fa **nove
join** per restituire una colonna, e la sua risposta dipende anche da join che
con la domanda non c'entrano.

#### ✅ `PREVENTIVO` — chiuso il 2026-08-24 dal team DB

> **Il difetto che questo brief temeva si è verificato — al contrario, e si è
> chiuso in giornata.** Il §L6 scriveva che *«un id numerico avrebbe prodotto un
> pulsante che non apre niente, e il difetto si sarebbe scoperto dal frontend,
> mesi dopo»*. È successo con l'**`uid`**, e l'ha visto il frontend lo stesso
> giorno in cui il tipo è nato.

**Cosa è stato misurato** *(BE, 2026-08-24)*: il catalogo dichiarava
`key_selector = uid` e il database scriveva `pv.uid::text` — ma la rotta API del
dettaglio è `path("<int:preventivo_id>/", …)`, la prop del drawer è
`preventivoId: { type: [Number, null] }`, e gli endpoint che accettano un uid di
preventivo sono **zero**. Mapparlo avrebbe prodotto un pulsante che apre il vuoto.

**Cosa ha fatto il team DB** *(`20260824-10`, applicato)*:

| Dove | Cosa |
| --- | --- |
| `fn_push_preventivo_a_ordine` | una riga di corpo: `pv.uid::text` → `pv.id::text` |
| `tipi_entita.csv` | `PREVENTIVO,…,uid` → `id` — mirror `runOnChange`, nessun changeSet di seed |
| Test 10 | allineato: asserisce `PREVENTIVO:<id>` |

⭐ **E la regola che ne è uscita vale oltre questo caso** — è nella testata del
changeSet e merita di stare anche qui:

> **Il valore di `key_selector` si MISURA sulle rotte del frontend. Non si
> eredita, e non si deduce dal fatto che una colonna `uid` esista.**

⚠️ **Adesso nessuno dei nove tipi usa `uid`.** La colonna resta, e il perché è
scritto invece di lasciarlo intuire: oggi registra un **fatto verificato** invece
di una supposizione, e il giorno in cui una superficie pubblica indirizzerà per
uid quella riga cambia **con un seed**, senza toccare nessuna funzione. Se quel
giorno non arriva, sarà costata una parola per riga.
⭐ Il frontend tiene il campo `chiave` per la stessa ragione, e lo scrive.

✅ **Verificato dal vivo dopo la correzione**: sollevato l'errore vero su un
preventivo vero, l'envelope porta `[{"type": "PREVENTIVO", "id": "48"}]` — id
numerico, coincidente con la riga.

⭐ **E si è visto anche il degrado, per caso**: una sonda che aveva codificato due
volte il JSON ha prodotto un `context` con `bersaglio` a **stringa**. Il database
ha scritto `W_BERSAGLIO_MALFORMATO` (`forma=string letti=0 validi=0`), lasciato
la casella vuota e **sollevato lo stesso l'errore di dominio** — cioè esattamente
ciò che il L1 aveva promesso: *la funzione che serve a riportare un errore non
può essere quella che lo distrugge*.

---

### 7-bis.8 ✅ Il collaudo in-app — 2026-08-24

> **Cosa è stato provato**, da Tid, sull'applicazione vera: il **pilota**, cioè
> il caso che ha fatto nascere il cantiere.

| | |
| --- | --- |
| Lotto | **6260** · `LTF-0005803`, verbo «Rendi definitive» |
| Fattura da numerare | **19563** (senza numero) |
| Bersaglio composto dal database | `[{"tipo": "FATTURA", "id": "835"}]` — misurato sulla guardia, non dedotto |
| Esito | il toast porta **«Apri Fattura 835»**, e il click **apre il drawer della fattura** |

⭐ **E non è la strada facile: è quella che nessun percorso felice tocca.**
«Rendi definitive» risponde **200** col fallimento dentro il payload, quindi
`useApiHandler` non vede nessun errore e il canale dell'envelope **non passa di
lì**. Quel pulsante esiste solo perché il bersaglio attraversa, nell'ordine:

```text
fn_numera_fattura_opz_emessa   il bersaglio per ramo (padre visibile)
  -> _run_per_fattura_task     punto di traduzione 4, che portava il solo message_primary
  -> errore{} del runner       B6, il blob dentro la risposta 200
  -> verdettoRunner            che prima leggeva solo code/message/detail
  -> azioniDaBersagli          risoluzione + degrado
  -> ospite globale in App.vue drawer aperto da qualunque schermata
```

#### ✅ Seconda superficie collaudata: la scheda **Segnalazioni** del lotto

Stesso giorno, subito dopo. Dal **messaggio** della segnalazione il documento è
linkato e **si apre**.

⭐ **Ed è l'errore PERSISTITO**, cioè il lettore che il §1 chiama *«l'operatore
cinque minuti dopo, che sta rimediando»* — quello che legge a giro finito,
magari il mattino seguente, quando il toast non esiste più da un pezzo. Il toast
serve chi c'era; questa scheda serve chi non c'era.

⛔ **E il gesto NON è costruito su `fattura_id`**, che pure sta nella stessa
riga: quello è il documento che ha **fallito** — nel collaudo la 19563, che
l'operatore sta già guardando in quella lista — mentre il bersaglio è la
**835**, dove deve andare. Due entità diverse, ed è la lezione del primo
scaglione applicata alla superficie dove sarebbe stato più facile sbagliare.

⚠️ **Cosa NON è ancora provato in-app**, e va detto perché la tentazione è di
dichiarare tutto verde: la strada **dell'envelope** (una chiamata che fallisce
davvero) e gli altri sette tipi. ⭐ Sono però le strade **più semplici** — quella
dell'envelope è l'unica che già funzionava prima di questo cantiere — e tutte e
tre passano dallo stesso resolver.

⛔ **E la ragione per cui il collaudo è costato fatica va tenuta** *(rilievo di
Tid)*: **gli errori che portano un bersaglio sono, per costruzione, quelli che
l'interfaccia cerca di impedire.** La classe è `CONFLITTO_STATO` — *«questa cosa
è in uno stato che non permette l'operazione»* — ed è lo stesso stato su cui il
frontend disabilita il pulsante (misurato: `can_genera_ordine` sul preventivo,
i livelli `PRENDIBILI` sulla coda flussi). Dal percorso felice non ci si arriva.
➡️ Ne discende che i casi collaudabili sono due: quelli in cui il vincolo sta su
**un'altra entità** (il 937, l'evasione massiva, il lotto dentro un giro) e
quelli in cui l'operatore agisce su uno **stato stantio** — che è poi il modo
vero in cui questi errori scattano in esercizio.

---

## 7-ter. 🔵 Il `T-3b` — passaggio al team DB *(scritto dal BE il 2026-08-24)*

> **Cos'è.** L'ultimo passo del cantiere: **l'id esce dalla prosa del 937**.
> Aspettava *«B-1 e B-2 in servizio»* (§5.3-bis) — e dal 2026-08-24 lo sono, con
> due superfici collaudate in-app (§7-bis.8). Non aspetta più niente.
>
> ⛔ **Perimetro: è del team DB.** Tocca `20_code/vendite` (la funzione che
> solleva) e `80_data` (il CSV dei messaggi). Il BE qui misura e chiede, non
> scrive.
>
> 🔴 **Ma non è scrivibile com'è**, ed è la ragione di questa sezione: rileggendo
> il pilota contro il §4.2 sono emerse **due cose che il piano non aveva**. La
> **prima è una scelta di modello** — quanti bersagli ha davvero il 937 — non un
> dettaglio di stesura; la seconda è un ramo che non può perdere l'id.

### La misura — sul corpo della funzione viva, 2026-08-24

Il messaggio **937** ha **due** `%s`, e il chiamante passa:

```text
p_fattura_id::text    ->  19563   il documento DA numerare
v_primo_bloccante     ->  835     il documento che BLOCCA
```

Il **bersaglio** invece ne copre **uno solo**:

```sql
jsonb_build_object('tipo', 'FATTURA', 'id', rif.id::text)   -- il solo PADRE
```

### 🔴 Rilievo 1 — togliere entrambi gli id lascia scoperto il primo

La frase diventerebbe *«Non si può numerare il documento: la fattura che
rettifica non è ancora numerata»*. Dentro **un giro di lotto** — dove l'errore
arriva su una fattura fra molte — **quale** non lo direbbe più né la prosa né il
bersaglio.

⚠️ È esattamente il rischio che il **§5.3-bis** aveva previsto: *«su un'emissione
di lotto l'id nella frase è oggi l'unica cosa che dice quale»*. Il bersaglio
doveva essere la risposta — ma risponde per il padre, non per il documento.

⭐ **E c'è una divergenza fra questo brief e il codice.** Il §4.2 scrive che il
937 *«ne ha due, il documento da numerare e la fattura rettificata»*, ed è
**la ragione per cui la forma è un array**. Il pilota ne emette uno. Non è un
difetto introdotto ieri: il pilota è nato così, e nessuno l'aveva riletto contro
quella frase.

### 🔴 Rilievo 2 — il ramo fail-closed non può perdere l'id

Quando il padre **non è visibile** (RLS), il secondo valore non è nemmeno un id:

```sql
min(COALESCE(rif.id::text, 'riga ' || fr.riga_rettificata_id::text))
```

e in quel ramo **il bersaglio è assente per scelta** (§4.3: *a un padre
invisibile non si può mandare nessuno*). Lì togliere l'id dalla prosa lascia
l'operatore con **meno di oggi**, e non c'è nessun pulsante a compensare.

### 🔵 Le due domande — poste come domande

| # | Domanda | Perché non la decide il BE |
| --- | --- | --- |
| **1** | Il bersaglio del 937 diventa **due elementi** — il documento da numerare *e* il padre bloccante — come il §4.2 dichiara? | È una scelta su **cosa l'errore indica**, cioè modello. ⭐ E cambia il T-3b: con due bersagli gli id possono uscire entrambi; con uno solo, il primo `%s` deve restare |
| **2** | Nel ramo **fail-closed** cosa resta nella frase? | Lì un bersaglio non c'è e non ci può essere. ⭐ Se la risposta è «l'id resta», il T-3b diventa **per ramo** — due messaggi o una frase che regge in entrambi — e non una sottrazione di `%s` |

### ⛔ I vincoli, che invece non sono negoziabili

* **Catalogo e chiamanti nello STESSO changeSet** (§5.3). Mai il CSV per primo:
  meno valori dei segnaposto degrada a **`%s` letterale a video** più un
  `W_MESSAGGIO_ARITA` nel log — brutto e semi-silenzioso;
* ⭐ Il cancello c'è ed è **statico**: il **test 5** di
  `test-catalogo-messaggi-errore-completo.sql` confronta i segnaposto del
  catalogo con l'arità dei punti di sollevamento. Prende il difetto **in CI** —
  ma solo se i due lati viaggiano nella stessa passata;
* ⚠️ **Va rivista anche la `soluzione` a catalogo**, che oggi dice *«Numerare
  prima il documento **indicato**»*: senza id in prosa, «indicato» non ha più
  referente — a meno che il referente non diventi il pulsante, e allora la frase
  va detta in modo che regga anche quando il pulsante **non c'è** (ramo
  fail-closed, permessi, perimetro).

### ⛔ Cosa il BE NON chiede

* **Nessun bersaglio nuovo altrove**: il roll-out è a fine corsa (§L6), e questo
  passo riguarda il solo 937;
* **Nessun cambio all'envelope**: `targets` è in servizio e collaudato, la forma
  regge già due elementi (il §4.2 l'aveva previsto proprio per questo caso);
* **Nessun backfill**: le righe già scritte non si toccano — il messaggio si
  compone al sollevamento.

⭐ **Il frontend è già pronto per la risposta 1**: con due bersagli disegna due
pulsanti senza modifiche — è il motivo per cui la decisione del 2026-08-22 volle
l'array anche con un elemento solo.

### ✅ Le risposte — decise da Tid il 2026-08-24, e già applicate

| # | Decisione | Conseguenza sul codice |
| --- | --- | --- |
| **1** | ✅ **Due ruoli.** Il bersaglio del 937 porta il **documento da numerare** — sempre, e **in testa** — poi i **padri bloccanti visibili**, in ordine di id. È la forma che il §4.2 dichiarava e che il pilota non aveva | La `SELECT` del bersaglio compone `jsonb_build_array(<il documento>) \|\| <i padri>`. Sparisce il `CASE WHEN v_bersagli IS NULL`: l'array non è mai vuoto |
| **2** | ✅ **Una frase sola per entrambi i rami, col conteggio.** Un `%s`, e ci va `v_n_bloccanti`. Nel ramo fail-closed la frase è la stessa; il pulsante del padre non compare, ma resta quello del proprio documento | Il `VARIADIC` passa **un solo valore**. La riga 937 del CSV passa da due segnaposto a uno, e la `soluzione` è riscritta |

⭐ **Perché la prima non era una scelta di resa.** Il BE l'aveva vista giusta:
con un bersaglio solo il `T-3b` **non si poteva fare**. Il primo elemento è ciò
che risponde al Rilievo 1, ed è sempre disponibile per costruzione — se
`p_fattura_id` non fosse visibile a chi opera, la funzione sarebbe già uscita
con `E_FATTURA_NON_TROVATA` molto prima della guardia.

⭐ **E l'ordine è una garanzia.** Il canale compatto tiene i **primi cinque**
elementi per ordinalità: in testa, il documento sopravvive al tetto anche su una
nota che rettifica righe di sette fatture diverse. In coda sarebbe stato il
primo a cadere, proprio nel caso in cui serve di più. La regola è ora nelle
linee-guida §5, perché non riguarda solo questo messaggio.

⛔ **Perché non due messaggi** (l'altra strada della domanda 2): nel ramo
fail-closed il rimedio è davvero diverso — non «numera», ma «chiedi a chi
gestisce quel perimetro» — ma un codice nuovo costa la sua classe, le policy
rigenerate lato BE e un secondo ramo di sollevamento. Quella differenza si dice
nella `soluzione`, ed è dove questa casa scrive cosa fare.

✅ **I tre vincoli del BE sono stati rispettati alla lettera**: catalogo e
chiamante nella **stessa passata** (applicati insieme alle 13:28 del
2026-08-24); nessun bersaglio nuovo altrove; nessun cambio all'envelope, che
regge già due elementi senza una riga di modifica. E la `soluzione` è stata
riscritta perché regga **anche quando il pulsante non c'è**.

📋 **Cosa il DB restituisce al BE/FE**, e non è una richiesta: su
`ErroreRigaInfo` il primo bersaglio coincide con la riga da cui si sta leggendo
l'errore, quindi lì il pulsante è ridondante (sul toast del runner è invece
l'informazione principale). Se dà fastidio si nasconde a video il bersaglio che
coincide con la riga — dal database non si toglie, perché il database non sa su
quale superficie l'errore verrà letto.

➡️ **Il piano, i file e la prova**: §6 lotto **L7**.

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

### ✅ Chiuse — le due di fondo, decise da Tid il 2026-08-24

**3. ⛔ `error_log` NON diventa una superficie per tutti.** *(Era: «diventerà
leggibile in-app?»)*

➡️ **Decisione: no.** E se un giorno qualcosa di quel diario si mostrasse, vale
**solo per i tecnici, dietro accesso autorizzato** — mai per chiunque apra
l'applicazione.

⭐ **La motivazione è la più importante scritta in questo brief, perché è la
ragione per cui il brief esiste.** Parole di Tid: *«altrimenti continuiamo a
creare altre tabelle per mettere le segnalazioni tecniche che poi qualcuno mette
a video… un loop infinito. Tutto il lavoro attuale è stato per dividere le due
aree.»*

⛔ **Il loop è reale, e va nominato per poterlo riconoscere**: si separa
l'appunto tecnico dalla frase per la persona (§2, due lettori due canali); poi
si mette l'appunto a video «così si vede meglio»; a quel punto l'appunto è
diventato una frase per una persona, e serve un terzo posto dove mettere gli
appunti. La separazione non si difende scrivendo meglio: si difende **negando la
superficie**.

➡️ **Regola operativa che ne discende**, e vale oltre questo brief: *ogni
schermata che mostri `dbops.error_log` — o qualunque diario tecnico — nasce
dietro un permesso*. Non «visibile agli amministratori per convenzione»: un
permesso dichiarato, come per ogni altra area.

⭐ **Conseguenza qui, concreta**: l'assunto del §2 **regge**, e con lui le scelte
che ci si appoggiano — su tutte `primo_bloccante`, che il `T-3b` ha tolto dalla
frase e **lasciato nel contesto**. Era la decisione giusta e resta tale.

⚠️ La domanda gemella resta al **Passo A** di
[analisi-osservabilita-log.md](../work-done/analisi-osservabilita-log.md), ma ci arriva
**decisa**: lì si progetta una timeline per chi indaga, non una vetrina.
*(Riferimento aggiornato il 2026-08-24: era «Passo 3», che dal 22/08 è diviso in
**A** forense e **B** aggregato.)*

**4. ⛔ Il catalogo messaggi NON distingue le superfici.** *(Era: «deve
distinguerle?»)*

➡️ **Decisione: no**, e non serve. Parole di Tid: *«lo stesso messaggio lo
potrebbero leggere diverse persone, ma non tutti leggono tutti i messaggi. La
maggior parte di quello fatto finora sono attività da operatore interno: non è
pensabile che uno dallo shop lanci la fatturazione.»*

⭐ **Il punto che scioglie la domanda**: le superfici non si separano nel
**catalogo**, si separano nei **percorsi**. Un utente dello shop non attraversa
la funzione che numera un lotto, quindi il messaggio 937 non lo raggiunge — non
perché il catalogo lo nasconda, ma perché quella strada non è sua. Il timore
(«la stessa frase davanti a tre pubblici») descriveva una sovrapposizione che
**oggi non esiste**.

⛔ **Quindi niente dimensione «superficie»** accanto a `lingua`: sarebbe 756
messaggi moltiplicati per un pubblico che su quasi tutti non passa mai.

⚠️ **Quando tornerà a valere, e come si riconosce**: il giorno in cui un codice
viene sollevato **anche** su un percorso raggiungibile dallo shop o dal portale.
Allora è **quel messaggio** a doversi rivolgere a quel lettore — un caso, non una
colonna. È lo stesso criterio del roll-out: *riprende quando lo chiede un caso*.

---

## 9. Registro

| Data | Cosa |
| --- | --- |
| 2026-08-24 (§8 chiuso) | ✅ **LE DUE DOMANDE DI FONDO SONO DECISE, e il brief non ha più domande aperte.** *(3)* ⛔ **`error_log` non diventa una superficie per tutti**: se mai si mostrasse, **solo ai tecnici e dietro un permesso dichiarato**. ⭐ La motivazione di Tid è la ragione stessa del cantiere: *«altrimenti continuiamo a creare altre tabelle per mettere le segnalazioni tecniche che poi qualcuno mette a video… un loop infinito; tutto il lavoro attuale è stato per dividere le due aree»*. Il loop va saputo riconoscere — si separa l'appunto dalla frase, poi si mette l'appunto a video, e serve un terzo posto per gli appunti: **la separazione si difende negando la superficie, non scrivendo meglio**. ⭐ Conseguenza concreta: l'assunto del §2 regge, e con lui il `primo_bloccante` che il `T-3b` ha tolto dalla frase e lasciato nel contesto. 📌 Il vincolo è stato **portato dove verrà consumato** — Passo A di `analisi-osservabilita-log.md` — perché lì si progetta la timeline, e una decisione che vive solo nel brief che l'ha generata è una decisione che il prossimo non trova. *(4)* ⛔ **Il catalogo messaggi non prende una dimensione «superficie»**: *«non tutti leggono tutti i messaggi; non è pensabile che uno dallo shop lanci la fatturazione»*. ⭐ Il punto che scioglie la domanda: **le superfici si separano nei percorsi, non nel catalogo** — chi sta nello shop non attraversa la funzione che numera un lotto, quindi il 937 non lo raggiunge. La sovrapposizione temuta oggi non esiste, e il giorno che esistesse sarebbe **quel messaggio** a doversi rivolgere a quel lettore: un caso, non una colonna |
| 2026-08-24 (L5 respinta · ErroreRigaInfo) | ⛔ **L5 ARCHIVIATA — respinta da Tid**, sulla misura fatta sui **corpi vivi**: 1082 punti di sollevamento, 410 funzioni. ⭐ **Il metro non chiede un giudizio**: i 14 punti che il bersaglio ce l'hanno sono verità nota, quindi si chiede alla regola candidata di riprodurli. Ne riproduce **9 su 14**, e i cinque mancati sbagliano in **quattro modi diversi** — nessun bersaglio (l'entità non è nominata nel contesto), bersaglio parziale (il 937: perde i padri bloccanti), **entità sbagliata** (i due `E_OFFERTA_*`: manderebbe all'offerta, e il corpo dice testualmente il contrario) e **guardia di esistenza persa** (il preventivo che non c'è → un pulsante che non apre niente). ⭐ **Ma il numero che ha deciso è un altro**: la derivazione non si applica ai 14, si applica a tutti — sui 1068 punti senza bersaglio farebbe fuoco su **138**, di cui 22 `TECNICO` (vietati dalla Q-E), 17 `NON_TROVATO`, 49 `DATO_ERRATO` e 35 `CONFLITTO_STATO` **già riletti uno per uno** dal §L6. Nove punti già coperti al prezzo di 138 non vagliati, e un bersaglio inutile non è neutro (§5.5). 🆕 **`ErroreRigaInfo`: chiuso il rilievo restituito dal team DB** — `BersaglioAzioni` prende `entitaCorrente` e non rende il bersaglio che coincide con la riga. ⛔ Il filtro sta nel **componente** e non nei due chiamanti (stessa ragione della normalizzazione), e il **toast non passa di lì** perché è l'unica superficie dove quel bersaglio è l'informazione principale. ⚠️ Assente = nessun filtro: un pulsante di troppo si vede, uno nascosto per sbaglio no |
| 2026-08-24 (BE, allineamento al T-3b) | ✅ **Chiuso il debito documentale che il §6 L7 lasciava al BE** — e i punti erano **sei, non quattro**: oltre ai quattro dichiarati, il **ripiego** di `error_messages_fallback.py` (che il perimetro DB non poteva vedere: è la frase che si mostra quando il messaggio del catalogo **non arriva**, ed era rimasta al singolare) e il payload d'esempio di `api_fattura_giornale.md`, scritto il giorno prima nell'altro cantiere e ancora non committato. ⭐ **È la seconda volta che in questo cantiere «i punti si cercano, non si conoscono»** (la prima fu il quinto punto di traduzione). ⛔ **E non erano quattro stringhe**: le finte sono passate a **due bersagli** — un finto a uno solo riproduce una forma che il database non solleva più, e i test di trasporto smetterebbero di provare che il secondo elemento arriva — e un'asserzione **diceva il falso** (`assertIn("835", message)`, col commento *«è l'unica cosa che dice QUALE documento»*): ora misura che la frase del database arrivi **intatta**, che è ciò per cui quel test è nato. ✅ **3919 verdi**. 📌 Il frontend **non ha richiesto niente**, verificato sul percorso vero: `BersaglioAzioni` cicla sulle azioni e l'etichetta porta già l'id, quindi i due pulsanti si distinguono da soli — la previsione del §7-ter ha retto. |
| 2026-08-24 (T-3b eseguito) | 🎉 **IL `T-3b` È FATTO, E IL CANTIERE HA RAGGIUNTO IL PROPRIO SCOPO**: la frase del 937 non porta più nessuna chiave interna. Applicato alle 13:28 — changeSet `20260824-13` e la riga 937 di `messaggi_errore.csv` **nella stessa passata**, come il §5.3 pretende. ⭐ **Le due domande del §7-ter, decise da Tid.** *(1)* Il bersaglio ha **due ruoli**: il documento da numerare **in testa**, poi i padri bloccanti visibili in ordine di id. ⛔ **Non era una scelta di resa: era ciò che rendeva possibile il passo.** Con un bersaglio solo, tolti gli id dalla frase, dentro un giro di lotto *quale* fattura ha rifiutato non lo direbbe più nessuno — il Rilievo 1 del BE. Il primo elemento c'è sempre **per costruzione**: se il documento non fosse visibile a chi opera, la funzione sarebbe uscita con `E_FATTURA_NON_TROVATA` molto prima della guardia. *(2)* **Una frase sola** per entrambi i rami, con un `%s` che porta il **conteggio** — non un identificativo — e la `soluzione` riscritta perché regga **anche dove il pulsante non c'è**. ⭐ **E ne è uscita una regola generale**, ora nelle linee-guida §5: *in testa al bersaglio va la cosa **su cui** l'errore è successo*. Non è estetica — il canale compatto tiene i primi cinque elementi, quindi la testa è ciò che sopravvive al tetto, e dentro un'elaborazione massiva è l'unica cosa che dice *quale*. ✅ **Verde**: 8/8 sul pilota come applicazione (da 7, il test 8 è nuovo; i test 6 e 7 sono passati dall'insieme alla **stringa esatta**, perché l'ordine è diventato una proprietà), catalogo messaggi 6/6, bersagli-non-dichiarati 4/4, guardrail (G) muto, e **nessuna regressione su 222 file di `vendite`**. ⭐ **La prova, non la deduzione**: la frase è *«…Documenti da numerare prima: 2»* e il canale `FATTURA:19753,FATTURA:19752,FATTURA:19754` — dove `19753` è la nota, che **non è l'id più basso**: è in testa perché è il soggetto, ed è esattamente ciò che il test 7 distingue da una coincidenza. 📋 Restituito a BE/FE un rilievo che non blocca: su `ErroreRigaInfo` il primo bersaglio coincide con la riga, quindi lì il pulsante è ridondante (sul toast del runner è invece l'informazione principale) — si nasconde a video, non si toglie dal database |
| 2026-08-24 (passaggio T-3b) | 📋 **Scritto il passaggio del `T-3b` al team DB (§7-ter)** — l'ultimo passo del cantiere, e da oggi sbloccato: B-1 e B-2 sono in servizio e collaudati su due superfici. 🔴 **E non è scrivibile com'era previsto.** Rileggendo il pilota contro il §4.2 sono emerse due cose che il piano non aveva. **(1)** Il messaggio ha due `%s` — il documento DA numerare e quello che BLOCCA — ma il bersaglio ne copre **uno solo**, il padre: togliere entrambi gli id lascia scoperto il primo, e dentro un giro di lotto **quale** non lo direbbe più né la prosa né il pulsante. È il rischio che il §5.3-bis aveva previsto, e la risposta doveva essere il bersaglio. ⭐ **Ne esce una divergenza fra questo brief e il codice**: il §4.2 dichiara che il 937 ha **due** bersagli — ed è la ragione per cui la forma è un array — mentre il pilota ne emette uno. Non è un difetto di ieri: il pilota è nato così e nessuno l'aveva riletto contro quella frase. **(2)** Nel ramo **fail-closed** il secondo valore non è nemmeno un id (`'riga N'`) e il bersaglio è assente per scelta (§4.3): lì togliere l'id lascerebbe l'operatore con **meno di oggi**, senza nessun pulsante a compensare. ➡️ Le due domande sono poste **come domande** — la prima è una scelta di modello, non di stesura. ⛔ Restano invece non negoziabili i vincoli del §5.3 (catalogo e chiamanti nello **stesso** changeSet, mai il CSV per primo; il test 5 li prende in CI solo se viaggiano insieme) e la revisione della `soluzione` a catalogo, che oggi dice «il documento **indicato**» e senza id non ha più referente. ⭐ Il frontend è già pronto alla risposta 1: con due bersagli disegna due pulsanti senza modifiche — è il motivo per cui l'array fu voluto anche con un elemento solo |
| 2026-08-24 (segnalazioni) | ✅ **Il bersaglio è anche sulla scheda Segnalazioni del lotto, e collaudato in-app**: dal messaggio il documento è linkato e si apre. ⭐ È l'errore **persistito** — il lettore che il §1 chiama «l'operatore cinque minuti dopo»: il toast serve chi c'era, questa scheda chi non c'era. **DB** (loro): `fn_list_lotto_segnalazioni` ritorna `target jsonb`. **BE** (mio): la colonna in coda alla SELECT e nella riga, più il tipo. ⚠️ **E la loro nota era giusta dove io stavo per «correggerla»**: la firma della funzione mette `target` in 16ª posizione, ma il repository **non fa `SELECT *`** — nomina le colonne e non prende `id` — quindi lì è davvero `row[14]`. Due frame diversi, entrambi veri; l'unico modo di saperlo era leggere il repository invece della firma. ⚠️ **Due test sulla mappatura POSIZIONALE**, perché è il difetto che sarebbe silenzioso: un off-by-one metterebbe `fuori_job_count` dentro `target` — un numero al posto di un array, cioè **nessun pulsante senza nessun errore**. Uno dei due presidia anche che `target ≠ fattura_id`. 🔴 **Accolto il loro rilievo su `error_code`**: `PipelineErrorLogger` scriveva `code`, ora scrive `error_code`. ⭐ Ed era una lezione **già pagata una volta** — `marca_fattura_in_errore` ha lo stesso identico commento dal giorno in cui il difetto emerse su `fatture_log`, e non era stata applicata all'altro scrittore. Verificato prima di rinominare: nessun lettore di `meta->>'code'` oltre al loro COALESCE, nessuna vista né Python legge `error_log.context->>'code'`. Le 17 righe storiche restano leggibili, nessun backfill. 🆕 **Estratto `core/components/BersaglioAzioni.vue`** alla 2ª copia (regola del 2, dichiarato a Tid): la resa dei pulsanti, usata da `ErroreRigaInfo` e dalla cella del messaggio. ⛔ Il **toast non passa di lì** — riceve azioni già composte perché vive nel template PrimeVue col suo `closeCallback`, e condividerlo porterebbe i18n e store dentro un toast; il pezzo condiviso vero è `azioniDaBersagli`. ⛔ E la **normalizzazione la fa il componente**, non il chiamante: è il bug già commesso una volta (payload inglese, resolver che legge `tipo` → nessun pulsante, in silenzio). ✅ 3.927 test verdi, E2E compresa |
| 2026-08-24 (collaudo in-app) | ✅ **PROVATO SULL'APPLICAZIONE VERA da Tid — sul pilota.** Lotto `LTF-0005803` (6260), «Rendi definitive» sulla fattura **19563**: il toast porta **«Apri Fattura 835»** e il click **apre il drawer della fattura**. Il bersaglio composto dal database è stato misurato in parallelo (`[{"tipo":"FATTURA","id":"835"}]`), non dedotto dal video. ⭐ **Ed è la strada DIFFICILE**: quell'endpoint risponde **200** col fallimento dentro il payload, quindi il canale dell'envelope non passa di lì — il pulsante esiste solo perché il bersaglio attraversa `_run_per_fattura_task` (il punto di traduzione 4) e il blob `errore` del runner (**B6**), cioè i due punti trovati e sanati in giornata. Un percorso felice non li tocca. ⛔ **E il collaudo ha prodotto un rilievo di Tid che vale oltre il cantiere**: *gli errori che portano un bersaglio sono, per costruzione, quelli che l'interfaccia cerca di impedire* — la classe è `CONFLITTO_STATO`, ed è lo stesso stato su cui il frontend spegne il pulsante (misurato: `can_genera_ordine` sul preventivo, livelli `PRENDIBILI` sulla coda flussi). Dal percorso felice **non ci si arriva**: restano i casi in cui il vincolo sta su un'ALTRA entità e quelli di **stato stantio**, che è poi il modo vero in cui scattano in esercizio. §7-bis.8. ⚠️ **Non provate** le altre due superfici (envelope su chiamata fallita, errore persistito di un giro asincrono) né gli altri sette tipi: sono strade più semplici e passano dallo stesso resolver, ma non sono state esercitate. ⚠️ E prima del collaudo è servito un `kill -HUP` su gunicorn: girava senza autoreload da prima del codice |
| 2026-08-24 (sesto giro BE/FE) | ✅ **`PREVENTIVO` chiuso dal team DB, e la mappa del frontend arriva a 8 tipi su 9.** La richiesta scritta ieri è stata accolta (`20260824-10`, applicato sul DB di prova): `pv.uid::text` → `pv.id::text` e `key_selector` da `uid` a `id`. ⭐ **E la regola che ne è uscita vale oltre il caso**, dalla testata del changeSet: *«il valore di `key_selector` si MISURA sulle rotte del frontend; non si eredita, e non si deduce dal fatto che una colonna `uid` esista»*. ⚠️ Adesso **nessuno dei nove tipi usa `uid`**; la colonna resta e il frontend tiene il campo `chiave`, perché il giorno che servirà cambierà **con un seed** invece che con codice. ✅ **Verificato dal vivo** contro il DB corretto: `[{"type": "PREVENTIVO", "id": "48"}]`, id numerico e coincidente con la riga. ⭐ **E si è visto per caso anche il degrado**: una mia sonda che codificava due volte il JSON ha prodotto `bersaglio` a stringa — il database ha scritto `W_BERSAGLIO_MALFORMATO` (`forma=string letti=0 validi=0`), lasciato la casella vuota e sollevato **lo stesso** l'errore di dominio. È la promessa del L1 mantenuta in esercizio, non in un test. ⛔ Resta fuori il solo `TASK_RUN`, e non è un ritardo: nessuna schermata mostra un giro per id. ⚠️ Il changeSet è arrivato a monte col merge del ramo DB (`17d69c17d`): al momento della scrittura non era ancora pushato, e il frontend degradava da sé (id non numerico → nessun pulsante) — l'allineamento non rompeva nulla su un DB indietro. ✅ 3.921 test verdi |
| 2026-08-24 (undicesimo giro) | 🔴 **Correzione su rilievo del BACKEND, e ha ragione**: il bersaglio del preventivo citava l'**uid**, ma le rotte sono `<int:preventivo_id>` e gli endpoint che accettano un uid sono **zero** — sarebbe stato un pulsante che non apre niente. Scritto il `20260824-10` (una riga di corpo), corretto il CSV (`PREVENTIVO,…,uid` → `id`, mirror runOnChange) e allineato il test 10. ⭐ **L'errore ha un nome e va tenuto**: ho riempito `config.tipi_entita.key_selector` con la risposta di `config.sorgenti.key_selector` — stesso nome, scelto apposta, ma **due domande diverse** (il lineage contro le rotte), che è la distinzione che entrambi i brief dichiarano dal principio. ➡️ Regola scritta: **il valore si MISURA sulle rotte, non si eredita**. ⚠️ Verificato anche che l'uid non è un'identità cross-revisione (165 righe, 165 uid, 165 id): nessuna sfumatura di dominio proteggeva la scelta sbagliata. ⭐ **E il difetto l'ha trovato il primo consumatore**: è la prova che il canale serviva — un bersaglio scritto e mai letto non avrebbe mai detto di essere sbagliato |
| 2026-08-24 (quinto giro BE/FE) | ✅ **Chiuso `FLUSSO`, e scritta la richiesta su `PREVENTIVO`.** **FLUSSO**: rotta nuova `GET /pratiche/flussi/<id>/pratica/` — l'unica dei flussi non annidata sotto la pratica, e risponde a una domanda sola («dove vive questa cosa?») invece di essere un secondo modo di leggerlo. Il deep-link della dashboard ora apre dal solo `flusso_id`, e ⭐ **vale oltre il bersaglio**: link, ricerca, notifiche. ⛔ **E il join sulla pratica non è decorativo — misurato**: `pratiche.flussi` **non ha RLS**, `pratiche.pratiche` sì; una lettura del solo `flussi` avrebbe risposto per qualunque flusso, anche fuori perimetro. ⚠️ **Non si riusa `get_flusso`** (nove join per una colonna, e la sua visibilità dipende da join che con la domanda non c'entrano): è la stessa lezione che questa casa aveva già scritto in `get_flusso_esito_config`. ✅ Provato dal vivo su **entrambi** i rami: senza contesto operatore il resolver rifiuta, col contesto risponde la pratica giusta. 🔵 **PREVENTIVO**: richiesta al team DB, due righe (`pv.uid::text` → `pv.id::text`, e `key_selector` da `uid` a `id`). ⭐ Il difetto che il §L6 temeva — *«un id numerico avrebbe prodotto un pulsante che non apre niente, e si sarebbe scoperto mesi dopo»* — **si è verificato al contrario, e si è scoperto in giornata**: nessun endpoint accetta un uid di preventivo (verificato), la rotta è `<int:preventivo_id>` e la prop del drawer è `Number`. La motivazione dell'uid è vera per `config.sorgenti` e **falsa per le schermate**. ⛔ L'alternativa (un endpoint pubblico che risolve l'uid) costa un contratto in più mantenuto per un caso solo. **Mappa del frontend: 7 tipi su 9.** ✅ 3.921 test verdi, E2E compresa |
| 2026-08-24 (quarto giro BE/FE) | ✅ **Allineati BE e FE al roll-out del DB** — 8 funzioni, 9 tipi a catalogo. **Provato dal vivo**: sollevati gli errori veri dal database, **7 codici su 7** arrivano all'envelope col loro bersaglio. 🔴 **Trovato un QUINTO punto di traduzione rimasto indietro**: `pratiche_service._raise_known_db_error` (12 punti di chiamata) portava il solo `hint`, e **è la strada del terzo scaglione** — senza il rimedio `E_DEFINIZIONE_BOZZA_ESISTENTE`, cioè «il caso più netto dell'intero roll-out», sarebbe arrivato a video senza gesto. Sanato, con **un test per ciascuno dei cinque** punti. ⭐ Conferma la regola del §7-bis.1: *il BB unifica la lettura, non il trasporto* — un punto nuovo va cercato, non aspettato. 🔴 **E un difetto in ciò che avevo già consegnato**: l'identificativo viaggiava come **stringa** dentro prop dichiarate `Number` (`fatturaId`, `contrattoId`, `ordineId`) — avviso in sviluppo, difetto silenzioso in produzione dove la validazione delle prop non c'è. ⭐ Corretto leggendo `key_selector` dal catalogo invece di dedurre il tipo dal valore, che è **esattamente ciò che la B-2 prescrive**: la mappa del frontend ora dichiara `chiave: 'id' | 'uid'` per ogni destinazione. 🆕 **Frontend**: mappa a 6 destinazioni (`+CONTRATTO`, `+ORDINE_VENDITA`, `+DEFINIZIONE_WORKFLOW`), supporto alle rotte con **parametro di percorso** e al guard `isAdmin` di `amm-software` — la definizione workflow è la prima destinazione che è una **pagina** e non un pannello. Nove etichette `config.tipi_entita.*` in `it`/`en`. ⛔ **Due tipi restano senza destinazione, e non è un ritardo del frontend** (§7-bis.7): **`PREVENTIVO`** — il catalogo dice `uid`, ma il documento si apre solo per **id numerico** (prop `Number`, rotta `<int:preventivo_id>`): il difetto che il brief temeva si è verificato **al contrario**, e serve una decisione; **`FLUSSO`** — il deep-link vuole `pratica_id` **e** `flusso_id`, e il bersaglio porta solo il secondo. Nel frattempo il degrado del §4.3 fa il suo mestiere. 🔧 **Rettificato il §7**, che scriveva `target` al singolare: il nome deciso e **in servizio** è `targets`, plurale come `fields`. Allineato il testo, non il codice — l'envelope è pubblicato in `/api/schema/`. ✅ **3.918 test verdi**, E2E compresa; lint e build del frontend puliti |
| 2026-08-24 (decimo giro) | 📋 **Scritte le consegne BE/FE in forma eseguibile** (§7). ⭐ **B-1 non è più una richiesta generica**: dice il modulo (`backend/apps/core/services/db_error_fields.py`, che possiede già i due canali gemelli e non ha dipendenze interne), il campo (`diag.datatype_name`), il contratto («solo dentro `P0001`», con la difesa già scritta lì per `constraint_name`), le due regex speculari a quelle del database, il punto di traduzione (`error_translator.py` ~228) e tre cose che il backend **non** deve fare. ⚠️ Dichiarata anche una asimmetria che sorprenderebbe: la chiave nel contesto DB è `bersaglio` (italiano, e perché `target` là è già occupata), il campo dell'envelope è `target`/`type` (inglese, come `fields` e `hint`) — la traduzione avviene **al confine**. ⭐ E B-2 chiarisce che la tabella `type → rotta` è **la stessa** della futura timeline per entità: si scrive una volta, o diverge |
| 2026-08-24 (nono giro) | ✅ **Terzo scaglione APPLICATO** (baseline `pratiche` verde). 📊 **Stato del roll-out**: **13 codici**, **9 funzioni**, **14 punti di sollevamento**, **9 tipi** a catalogo — e `dbops.vw_bersagli_non_dichiarati` sempre **vuota**. 🏁 **E il roll-out è a FINE CORSA, non finito**: dei `CONFLITTO_STATO` che passano un id restano 21 punti su 15 codici, e riletti con la lente sono **quasi tutti esclusioni motivate** — la famiglia resi («sei già sul reso»), i `%s` che sono colonne o stati, i documenti che l'operatore ha già aperto, e i due bloccati dal costo della funzione a 40 parametri. ⭐ **Restano due soli candidati veri** (`E_FORNITORE_NON_ATTIVO`, `E_ACCREDITO_GIA_ESEGUITO`) e nessuno dei due è ovvio. ⭐ **La conclusione, scritta perché nessuno riapra la lista a tappeto**: continuare vorrebbe dire aggiungere pulsanti che non aiutano — e un bersaglio inutile non è neutro, insegna a ignorare il pulsante. Il roll-out riprende quando lo chiede un caso |
| 2026-08-24 (ottavo giro) | 🛠️ **TERZO SCAGLIONE SCRITTO — «gli errori che nascono da una lista»**: due changeSet (`20260824-08/09`, schema `pratiche`), tre codici, due tipi nuovi a catalogo (`FLUSSO`, `DEFINIZIONE_WORKFLOW` — nove in totale). ⛔ Non applicato. ⭐ **Contiene il caso più netto dell'intero roll-out**: `E_DEFINIZIONE_BOZZA_ESISTENTE` nomina lo **scope** (tipo prestazione, emittente) e la bozza che blocca **non la nomina affatto** — quel documento un nome utile non ce l'ha, e metterci un id tecnico sarebbe il difetto che il cantiere esiste per togliere. Lì il bersaglio non aggiunge comodità: **aggiunge un'informazione che la frase, per come è costruita, non può dare**. È l'argomento migliore che questo cantiere abbia prodotto per i due canali separati. ⚠️ Terza volta che un `EXISTS` diventa una raccolta — stessa scansione, in più gli id, e array perché se le bozze fossero più d'una vanno viste tutte; il predicato non cambia (`jsonb_agg` su zero righe è NULL). ⚠️ `fn_fork_definizione` è `SECURITY DEFINER`: verificato che è di `titodb` e **non** nel registro `sec_functions_owner`, quindi nessun blocco di proprietà da aggiungere |
| 2026-08-24 (settimo giro) | ✅ **Secondo scaglione APPLICATO e verde** (`20260824-05/06/07` — il `04` era occupato da un altro cantiere, rinominato in `07`: il numero vive in **tre** posti, nome file, `logicalFilePath` e `id`). Test del piano rate **16/16**, baseline senza regressioni nuove. 📊 **Stato del roll-out, misurato sul codice**: **10 codici** portano ora un bersaglio, su **7 funzioni** e **11 punti di sollevamento** — tutti di classe `CONFLITTO_STATO`. ⭐ E `dbops.vw_bersagli_non_dichiarati` resta **vuota**: dieci conversioni e zero tipi fuori catalogo, che è il senso di aver messo il cancello prima del roll-out e non dopo |
| 2026-08-24 (sesto giro) | 🛠️ **SECONDO SCAGLIONE SCRITTO — «gli errori dentro un giro»**: tre changeSet (`20260824-05/06/07`), quattro codici, cinque punti di sollevamento, e il test del piano rate esteso **14 → 16**. ⛔ Non applicato. ⭐ **Il tema è nuovo e più forte del primo**: questi errori nascono dentro un giro automatico, non da un gesto — il lotto che blocca un'emissione l'operatore non lo sta guardando affatto, e la fattura senza righe è una fra molte. Qui l'obiezione «ma ce l'ha già davanti» cade del tutto. ⚠️ **Due esclusioni, e la seconda è la più istruttiva di tutto il roll-out**: `E_VALORE_MANCANTE` vive nella STESSA funzione dei due rifiuti del piano rate e ha un context **identico**, ma parla di un campo — il suo canale è `COLUMN`. Per questo la sostituzione è ancorata al **codice** e non alla riga di contesto: un'ancora più larga gli avrebbe messo il bersaglio addosso, e il presidio è il test 16. ⚠️ L'altra esclusione è di **costo**: `E_COMMESSA_NON_MODIFICABILE` e `E_ONERE_SEGMENT_DUPLICATO` vivono in `fn_upsert_commessa_attivita`, che ha una firma da **40 parametri** — toccarla obbliga alla passata `%TYPE` su tutte, sproporzionata all'aggiunta di un bersaglio |
| 2026-08-24 (quinto giro) | ✅ **Primo scaglione APPLICATO, tutto verde.** I tre pgTAP estesi passano — offerta **10/10**, preventivo **11/11**, DDT **26/26** — e con i tre file del canale, del cancello e del pilota fanno **66 asserzioni** sul cantiere. ⭐ **E il cancello del vocabolario è VUOTO**: `dbops.vw_bersagli_non_dichiarati` non elenca niente, cioè ogni tipo scritto nei corpi vivi è a catalogo. È la prova che la scelta di far crescere il catalogo una voce per volta regge — non perché ci si ricorda, ma perché dimenticarsene farebbe fallire la build. Il guardrail resta verde: un solo mittente su tutti e tre i canali strutturati |
| 2026-08-24 (quarto giro) | ✅ **Famiglia CHIUSA: scritto anche il DDT** (`20260824-03`), e con lui il primo scaglione è completo — tre changeSet, tre tipi a catalogo, tre pgTAP esistenti estesi (mai un file nuovo). ⛔ Non applicato. ⭐ **La lezione operativa dello scaglione**: su tre codici convertiti ci sono state **tre esclusioni di ramo** — il fail-closed del 937, il preventivo inesistente, `E_DDT_ORDINE_NOT_FOUND`. La domanda «c'è un posto dove mandarlo?» va fatta **a ogni ramo**, non a ogni codice: un roll-out a tappeto avrebbe prodotto tre pulsanti che aprono il vuoto. ⭐ **E un'obiezione che tornerà, con la sua risposta**: «l'operatore l'ordine lo sta già guardando» — vero sul singolo, falso sull'**evasione in massa**, dove la frase dice quale ordine ha rifiutato e non ci porta. Il bersaglio vale anche sugli errori che *sembrano* già contestualizzati. ⚠️ **Fuori cantiere, trovato leggendo**: `fn_genera_ddt_da_ordine` solleva `E_VALIDAZIONE` con dentro `'p_ordine_id deve essere > 0'` — cioè un **nome di parametro nel `VARIADIC`**, che è la cosa che le linee guida vietano perché quei valori compongono la frase che legge l'operatore. Non toccato qui |
| 2026-08-24 (terzo giro) | ✅ **Primo scaglione APPLICATO.** Il test del preventivo è **verde, 11/11**, e con lui la prova che `key_selector = 'uid'` funziona end-to-end: il bersaglio esce come `PREVENTIVO:<uuid>`, e sul preventivo inesistente non esce affatto. ⛔ **Un difetto mio all'apply, e non era l'unico**: i due changeSet avevano una precondizione «i tipi devono essere già a catalogo» che ha fatto fallire il migrate. Sbagliata due volte: `80_data` gira **dopo** `20_code`, quindi non poteva che trovare zero (la stessa finestra che avevo documentato io stesso nel `20260823-02`); e soprattutto **non era una verifica di quel livello** — la funzione non legge il catalogo a runtime, e il vocabolario lo presidia la CI. Tolta, col motivo scritto in testata di entrambi i file. 🔴 **E il test dell'offerta è rosso — ma NON per causa mia**: fallisce identico su `HEAD` senza le mie modifiche, nel fixture, con una violazione di RLS. Vedi la riga qui sotto |
| 2026-08-24 (fuori cantiere) | 🔴 **Trovato verificando: 12 file pgTAP su 16 sono rossi, e nessuno li misurava.** `scripts/pgtap-baseline.sh` cerca in `db/pgtap/*/*.sql` — **un livello solo** — quindi le tre sottocartelle di `vendite` (`offerte_commerciali`, `contratti`, `fixtures`) sono **fuori dalla baseline**. ⭐ La causa dei rossi sembra comune e ha una data: il **2026-08-07** il pgTAP è passato da girare come owner a girare come **applicazione**, quindi la RLS ha cominciato a mordere — e quei fixture scelgono «il primo emittente attivo per id» invece dell'emittente **del perimetro di chi opera** (per cui esiste già l'helper `script.fn_pgtap_emittente_operatore()`). Due forme dello stesso difetto: la violazione diretta del `WITH CHECK`, e un `NULL` propagato da una riga che la RLS nasconde. ⚠️ **Non è di questo cantiere e non si risolve qui**, ma tocca questo cantiere in un punto: la mia asserzione **10** vive in uno di quei file, e finché il fixture non regge non è verificabile |
| 2026-08-24 (secondo giro) | 🛠️ **ROLL-OUT, primo scaglione: SCRITTO** — due changeSet (`20260824-01/02`), tre tipi nuovi a catalogo (`PREVENTIVO` per **uid**, `CONTRATTO`, `ORDINE_VENDITA`) e i **due pgTAP esistenti estesi** invece di due file nuovi. ⛔ Non applicato. ⭐ **E lo scaglione ha insegnato una cosa che il piano non aveva: il bersaglio NON è l'entità nominata nella frase.** Sui due rifiuti dell'offerta la frase nomina l'offerta — che l'operatore ha già davanti — mentre la cosa irraggiungibile è il **documento già generato**: il bersaglio risponde a «dove devi andare», non a «di cosa stiamo parlando». È la conferma che il roll-out va fatto **codice per codice**: un conteggio non distingue le due cose. ⭐ **Secondo guadagno: `key_selector` è stato esercitato per la prima volta** — il preventivo si cita per `uid`, e con l'id numerico il pulsante non avrebbe aperto niente (difetto che si sarebbe scoperto dal frontend, mesi dopo). ⚠️ `EXISTS` diventato una raccolta nei due guard dell'offerta: stessa scansione, in più gli id — e sono **array**, perché se i documenti generati fossero più d'uno (l'anomalia che il guard esiste per fermare) l'operatore deve vederli tutti |
| 2026-08-24 | ✅ **APPLICATO, e verde: 19 asserzioni su tre file** (8 canale, 4 cancello, 7 pilota) più il presidio del catalogo messaggi. Verificato dopo l'apply: `key_selector` seminato dal mirror `runOnChange` senza toccare il loader, `dbops.vw_bersagli_non_dichiarati` **vuota**, guardrail verde con **un solo mittente su tutti e tre i canali**. ⛔ **Un difetto mio, e i test l'hanno preso al primo colpo**: il file sul canale aveva una **parentesi di chiusura in meno** in quattro asserzioni su otto — non compilava affatto. ⭐ **La correzione non è stata mettere la parentesi**: le asserzioni sono state riscritte col **verbo in un'istruzione separata**, che è la regola di casa (la snapshot di statement) e che *incidentalmente* toglie di mezzo cinque livelli di parentesi annidate dentro un `is()`. La regola esisteva per un'altra ragione e ha protetto da questa: annidare la chiamata dentro l'asserzione era il difetto a monte. ⚠️ Il rilievo di Tid era *«è una regressione del tuo lavoro?»* — no: il difetto stava **solo nel file di test**, e il changeSet non era nemmeno arrivato a essere esercitato. 📋 Misurato il menu del roll-out (§6 L6) **sul codice**: 314 punti di sollevamento passano un id interno, ma su 78 codici — la selezione si fa per codice e a mano, perché un conteggio non distingue «l'id da aprire» da «l'id sbagliato a scrivere» |
| 2026-08-23 | 🛠️ **SCRITTO IL LOTTO — quattro changeSet (`20260823-01…04`), tre CSV, tre file pgTAP, il controllo (G) del guardrail e la quarta riga della tabella dei canali in `linee-guida-sql`. ⛔ Nulla applicato: l'apply è di Tid.** ⭐ **Le cose verificate PRIMA di scrivere, non dedotte**: che il canale `DATATYPE` sopravviva al giro (`GET STACKED DIAGNOSTICS PG_DATATYPE_NAME`); che la logica di composizione regga su sette casi (due validi, uuid, uno storto, tutti storti, sette, vuoto, chiave assente); che le colonne da ancorare col `%TYPE` abbiano **esattamente** i tipi di adesso (`atttypid::regtype`, che ignora il typmod) — quindi né firma né `RETURNS TABLE` cambiano e non serve nessun `DROP`; e che il guardrail col controllo (G) resti **verde** (girato sul database: unico mittente su tutti e tre i canali). ⚠️ **Due cose scoperte scrivendo, che il piano non aveva**: (1) `fn_log_error_only` scrive via **dblink**, cioè in transazione autonoma — le righe di `error_log` dei test **sopravvivono al ROLLBACK**, e ora è scritto nel file di test invece di essere creduto il contrario; (2) `jsonb_build_object('bersaglio', NULL)` **non** vuol dire «nessun bersaglio»: sarebbe una chiave presente e inutilizzabile, cioè un `W_` su un ramo che funziona — da cui il `CASE` nel pilota. 🔴 **Un richiamo di Tid, ed è la terza volta**: `%TYPE` in firma, `RETURNS TABLE` e `DECLARE`. Il meccanismo ha un nome ed è scritto in memoria — **riprodurre il corpo vivo porta con sé il debito della funzione** in una forma che sembra corretta perché combacia col database. Sanato in entrambe le funzioni, e dove il tipo resta esplicito ora c'è scritto **perché** (un conteggio, un interruttore, il nome di una colonna, una colonna che non esiste). ⏱️ **Chiusa la verifica lasciata in sospeso ieri**: `trg_event_log_gen_tx_id_ins_upd` **è nato** con l'automazione delle 21:00, e `event_log` ha le sue prime 12 righe scritte dalla pipeline vera |
| 2026-08-22 (sesto giro) | 📋 **Scritto il piano (§6)**: cinque lotti, quattro changeSet numerati (**63-66**), due append ai CSV, un controllo di CI, tre file pgTAP e una tabella da estendere in `linee-guida-sql`. ⭐ **Le tre decisioni che il piano ha dovuto prendere per essere scrivibile**, e stanno tutte nel L1: (1) **il ricco resta nel contesto, il compatto viaggia** — `p_context->'bersaglio'` è l'array del §4.2 e finisce in `error_log`, la casella dell'eccezione porta `TIPO:id`, e li scrive **lo stesso chiamante una volta sola**; (2) **la funzione non legge il catalogo a runtime** — valida solo la forma, il vocabolario lo presidia la CI (L3), perché una query dentro il percorso d'errore è una dipendenza che non si vuole; (3) **un bersaglio malformato non distrugge mai l'errore di dominio** — casella vuota e `W_BERSAGLIO_MALFORMATO` nel log, che è la lezione del 18/08 tradotta. ⚠️ **Il L5 (derivazione automatica dalle chiavi `<tipo>_id`) è retrocesso a proposta**: con la Q-E servirebbe leggere la classe a runtime e con la Q-D varrebbe per tre tipi — ma la ragione vera è che un bersaglio sbagliato è **attivo** (porta l'operatore altrove), mentre un `COLUMN` sbagliato è inerte: non merita la stessa scorciatoia. 🔧 **Allineati i riferimenti superati** dopo l'apply dell'altro cantiere, di qua e di là (§3 di questo brief; §3.1, §3.2, §3.5, §3.8 e §4-bis dell'altro) |
| 2026-08-22 (quinto giro) | ✅ **Chiuse tutte e cinque le domande del quarto giro, e il brief diventa scrivibile.** ⭐ **Q-A: via A** — il bersaglio esce dal `RAISE` su una **casella strutturata nuova**, terza volta che questa casa fa la stessa mossa (`CONSTRAINT` 05/08, `COLUMN` 08/08), con la composizione in **una sede sola** dentro `fn_log_and_raise_error`. ⭐ **Q-B: la chiave è `bersaglio`** — i 16 punti che usano `target` per il nome di una tabella non si toccano, e nessuna parola resta con due significati. ⭐ **Q-C: la chiave dell'entità la dichiara il catalogo**, sulla convenzione di `config.sorgenti.key_selector`: la regola vive accanto al tipo, non nella testa di chi scrive il frontend. ⭐ **Q-D: il catalogo cresce col roll-out**, una voce per volta insieme al messaggio che la usa — niente voci che promettono una destinazione irraggiungibile, e il presidio **T-4** impedisce di dimenticarsene. ⭐ **Q-E: bersaglio solo sugli errori rimediabili, mai sui `TECNICO`** — su un 500 non c'è gesto, e l'entità resta negli appunti per chi indaga. ⏱️ **Nel frattempo il L4 dell'altro cantiere è stato applicato** (53-60, più 61-62 del suo L2): la colonna del **T-1d** è ora un changeSet nuovo. ❌ **E una segnalazione mia che era sbagliata**: avevo dato per «residuo» la FK `fk_event_log_tipo_entita` senza riga in `dbops.fk_index_policy`. **Non è un residuo, è una decisione scritta** (loro §4, L4): la FK è su `entity_type`, che è **già la prima colonna di `ix_event_log_entity_time`** — coperta per prefisso — e registrarla a `consentito=false` sarebbe **attivamente dannoso**, perché il ramo del `DROP` estrae il nome dal `dll_command` e cancellerebbe un indice non dedicato che serve alla query forense. ⭐ Avevo guardato la tabella e non il brief: la regola «gli indici FK sono opt-in» ha un'eccezione per prefisso, e loro l'avevano già vista |
| 2026-08-22 (quarto giro) | 🔎 **Rilettura critica contro il cantiere `event_log`**, misurando sul database e sul codice invece che sul testo. ⭐ **Il disegno regge; a non reggere è la sua premessa operativa**, e sono quattro rilievi. 🔴 **(1) Il canale del §4.1 non arriva al frontend**: `p_context` va solo in `error_log`, e i cinque canali strutturati del `RAISE` sono **tutti occupati** (`ERRCODE`, `CONSTRAINT`, `COLUMN`, `DETAIL`, `HINT`) — quindi «serve solo una convenzione» vale per chi diagnostica e **non** per il gesto, che è la ragione del brief. Nasce il §4.4 e con lui **Q-A**; **B-1 non è eseguibile** com'era scritta. 🔴 **(2) La chiave `target` è già in uso**: **16 punti di sollevamento in 6 file** la scrivono come **stringa**, e dentro c'è `schema.tabella` — cioè proprio ciò che il §4.2 vieta. Proposta: `bersaglio` (**Q-B**). 🔴 **(3) Contrapposizione vera con l'altro brief**: i due codici che il suo §4-bis regala come «primi adottanti gratuiti» **non lo sono** — uno porta per definizione un tipo fuori catalogo (farebbe fallire il T-4), l'altro punta a un'entità inesistente, e sono entrambi `TECNICO`. Da lì la regola mancante: **il bersaglio è per gli errori rimediabili, non per i 500** (§5.5, **Q-E**). 🔴 **(4) C'è una scadenza**: i changeSet 53-60 del L4 sono **scritti e non applicati**, quindi ogni colonna che il bersaglio vuole nel catalogo costa **zero oggi** e una migrazione domani — e la misura dice che il seed ha 4 tipi (manca `SOGGETTO`) e che le due letture **non concordano sull'identificativo** (`entity_id` è `bigint`, ma `soggetti.id` è `uuid` e `sorgenti` ha `key_selector = uid`). Nascono **T-1d**, §5.1-bis, **Q-C** e **Q-D**. ⚠️ Corretti inoltre due punti che dicevano il falso: il §5.3 (dal 18/08 la `format()` è protetta: il difetto **degrada**, non alza più `22023` — e un cancello statico esiste già) e il §4.3 sul 937 (il secondo valore **non è sempre un id di fattura**: nel ramo fail-closed è la stringa `riga N` di un documento invisibile). ⭐ **E una scoperta che vale il giro**: **due punti di sollevamento vivi su tre** scrivono già una chiave `<tipo>_id` nel contesto — il bersaglio si può **derivare in una sede sola**, come l'08/08 ha fatto con `parametro`→`COLUMN` (nuovo **T-5b**). ⚠️ **Nota di metodo, richiamata da Tid nello stesso giro**: le misure di questo brief sono sul **codice** (`pg_proc.prosrc`, i file di `20_code`), non sulle righe di `dbops.error_log` — un registro di sviluppo senza recinto fra test ed esercizio, che non misura né frequenza né gravità. Le due misure che erano nate «a conteggio di righe» sono state rifatte sui corpi delle funzioni (§4.1) e ridotte a eco (§4.2). ⛔ Nulla applicato, nessun file di migrazione toccato |
| 2026-08-22 (terzo giro) | ⛔ **T-1 e T-1b escono da questo brief**: sono stati assorbiti da [brief-db-event-log-scope-e-riga-parlante.md](brief-db-event-log-scope-e-riga-parlante.md) (**D-17**, §3.7, lotto **L4**). ⭐ **La decisione di Tid non cambia — cambia dove si esegue**: decidevano su `event_log.entity_type`, e una decisione su una colonna deve stare dove vive la colonna. ⚠️ Il rischio che il secondo giro aveva previsto si è avverato al contrario: quel cantiere ha **applicato per primo** una scelta opposta (un `CHECK` invece del catalogo), quindi non c'è un apply da coordinare ma una correzione in avanti da scrivere — la scrive lui. ⭐ **E la collisione ha prodotto due cose utili**: il catalogo porterà `modo_risoluzione_emittente`, che rende inutile il `CASE` scritto a mano nel loro trigger; e si è capito che **i due vocabolari non sono lo stesso insieme** — il giornale è un sottoinsieme proprio del bersaglio, selezionato da «l'emittente dev'essere derivabile». Da lì il nuovo **T-1c**. 🔴 Rettificato il §3, che dava `TASK_RUN` per presente in `event_log`: non lo è più dal 2026-08-22 |
| 2026-08-22 (secondo giro) | ✅ **Chiuse le due domande che bloccavano la scrittura**, entrambe verso la forma più larga: **catalogo chiuso** per i tipi (con `event_log.entity_type` che lo adotta — nasce **T-1b**) e **`target` sempre array**. ⭐ Nessuna delle due è una preferenza di stile: la prima evita due vocabolari per la stessa nozione, la seconda evita di cambiare la forma di una chiave **già in servizio** il giorno del secondo bersaglio — e il secondo bersaglio esiste già oggi, sul messaggio pilota. 🔴 **Ne discende un vincolo di coordinamento che prima non c'era**: T-1b tocca `event_log`, che è anche l'oggetto del **Passo 0** dell'osservabilità (emittente + RLS + correlation + actor). Stessa tabella, stessa funzione di scrittura: **un apply solo**, e la sorte delle righe storiche si decide di là, non qui |
| 2026-08-22 | Stesura, su richiesta di Tid dopo il collaudo NC resi. ⭐ **Il disegno è cambiato durante la discussione, ed è la parte utile**: la proposta di partenza era `schema.tabella.id` nel messaggio; ragionandoci è emerso che la domanda «id o frase umana» **non ha risposta** perché presuppone che l'errore sia testo, e che all'operatore non serve il *nome* del record ma **arrivarci**. Da lì i tre strati e il bersaglio. ⭐ Il canale c'è già (`p_context` → `dbops.error_log.context`) e la quasi totalità dei sollevamenti lo valorizza: manca la **convenzione**, non la macchina. 🔴 Segnalata la trappola §5.3 (catalogo e chiamanti nello stesso changeSet, lezione del cantiere segnaposti). ⛔ Nulla applicato |

---

*Brief DB — il bersaglio dell'errore (22 agosto 2026).*
