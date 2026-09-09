# Brief DB — il documento trattenuto conta e passa lo stesso

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-09. **A chi:** team DB.
> **Risposta del team DB:** 2026-09-09 — §5 in poi.
> **Seguito di:** [brief-db-documento-trattenuto-da-un-lotto-vivo](brief-db-documento-trattenuto-da-un-lotto-vivo.md).
>
> **In una riga:** il verdetto «trattenuto da un lotto vivo» funziona, ma due
> strade non lo attraversano: la **card** lo conta ancora, e il **giro di massa**
> lo prende ancora. Il secondo ha già prodotto un lotto.
>
> ⇒ **E leggendo il percorso vero** (§5) le due strade non sono dove sembravano:
> la card non filtra perché **non ha il dato**, e il giro non passa dalla lane.
> ⇒ **Più tre difetti del predicato già applicato** (§6), che estenderlo
> moltiplicherebbe.
> ⇒ **E un quarto, trovato cercando cosa si può riusare** (§9.2): la lane ha uno
> **specchio dichiarato**, e da T-4 dice il falso.

---

## 1. Come è nato

Collaudo a video di Tid, 2026-09-09, su `09/2026`. La card «Da emettere» dice
**4**; l'elenco sotto ne mostra 3 e sbarra `ORD0036005`, trattenuto da
**LTF-0010331**. Premuto **«Fattura»** sulla card, `ORD0036005` è finito in un
lotto nuovo — **LTF-0010332**, poi annullato.

---

## 2. Che cosa abbiamo misurato

> ⚠️ Tabella del **2026-09-09**, sul database di sviluppo: è un **fatto datato**,
> non il motivo di niente. Il motivo sta sul modello, e sta nel §5.

| Sorgente | Dice |
| --- | --- |
| `vw_dash_competenza_gruppi_riepilogo` | `n_gruppi 2 · n_attivita 3 · n_gruppi_trattenuti 1` ✅ esclude |
| `vw_dash_competenza_mensile` — la CARD | `n_attivita 4 · valore 300` 🔴 **include** |
| `fn_list_emittibili_lane` | `ORD0036005` **non** fra i `gruppi_coperti` ✅ esclude |
| `LTF-0010332`, il lotto nato dal gesto | perimetro dichiarato **vuoto** (giro di massa) e un **esito** su `ORD0036005` 🔴 |

⭐ **Il verdetto in sé è corretto**: `emissione_blocco_lotto_codice` punta a
`LTF-0010331` — il lotto **vivo** — e non a `LTF-0010332`, che è annullato.

⚠️ E `ORD0036005` risulta adesso `ERRORE` in **due** lotti.

🔴 **Correzione del team DB su due righe di questa tabella** (2026-09-09), e non
sono dettagli: la **prima** misura una vista che **l'applicazione non legge**
(§5.2), la **terza** misura una funzione che **non è la porta da cui il giro
passa** (§5.3). Sono misure giuste su oggetti che non stanno nel percorso —
sarebbero verdi anche a difetto intatto.

---

## 3. 🔵 Che cosa serve

1. **Che la card conti come la lista.** Il numero su cui l'operatore decide
   comprende lavoro che non può prendere, e le due cifre convivono sulla stessa
   schermata.
2. **Che il giro non prenda ciò che la lane non ha offerto.** L'esclusione oggi
   vale sull'elenco e non su ciò che il giro poi prende davvero: il lotto qui
   sopra è nato dopo che la lane aveva già escluso quel documento.

✅ **Confermate entrambe** dal team DB. Cambia **dove** si fanno, non **se**.

---

## 4. ⚪ Una domanda, non una richiesta

La colonna «lotto del tentativo» mostra `LTF-0010332` su tutte e tre le righe,
**anche se quel lotto è annullato**. Tid preferirebbe non vederla in quel caso.

⚠️ Ma il tentativo **è avvenuto**, e quella è l'unica traccia a video che spieghi
perché il documento è tornato disponibile. ⛔ Quello che non regge è com'è
adesso: mostrato come se contasse ancora.

⇒ La scelta è di modello, e la lasciamo a voi e a Tid. **Risposta nel §7.**

---

> ⬛ **Da qui in poi risponde il team DB** — 2026-09-09

## 5. Le due richieste reggono — le sedi no

### 5.1 La card non filtra perché **non ha il dato**

Sono due piani diversi, e il verdetto vive su quello sbagliato per la card:

| | grana | ha il verdetto? |
| --- | --- | --- |
| `vw_dash_competenza_attivita` | **attività** di commessa | ⛔ no |
| `vw_dash_competenza_mensile` — **la card** | aggrega la precedente | ⛔ no, e non può |
| `vw_dash_competenza_gruppi` — **la lista** | **gruppo** (documento) | ✅ sì, `emissione_blocco_*` |

⇒ Non è che la card «si è dimenticata di filtrare»: il verdetto sta **un piano
sopra** di lei, e un aggregato non può leggere una colonna che la sua sorgente
non espone. ⭐ Il rimedio è **portare il verdetto alla grana più bassa** — la
sede resta una, cambia da dove la si interroga.

### 5.2 🔴 E il conteggio corretto ieri non lo legge nessuno

`vw_dash_competenza_gruppi_riepilogo` — la vista che il changeSet `20260909-24`
ha insegnato a escludere i trattenuti, con tanto di `n_gruppi_trattenuti` a
dichiarare il calo — **non è nel percorso dell'applicazione**.

Il riepilogo che il frontend mostra sotto la lista lo calcola una query scritta
nel backend (`get_dash_competenza_gruppi_accessori`), che legge
`vw_dash_competenza_gruppi` **una volta** e ci fa girare sopra cinque conteggi.
Quella query non esclude niente e non ha `n_gruppi_trattenuti`.

⚠️ **Fatto datato, 2026-09-09**: cercato `n_gruppi_trattenuti` in tutto il
repository, compare **solo** nel changeSet che lo crea, nel suo pgTAP e nei due
brief. **Zero consumatori.** La query del backend che l'ha scavalcata è del
26-08, cioè **quattordici giorni prima** del changeSet che ha corretto la vista.

⭐ **La regola che questo caso illustra è già scritta**, ed è la
[§12.5.3 delle linee guida SQL](../../linee-guida-sql.md): *«la domanda da farsi
prima di scegliere la vista è **da dove si preme quel pulsante** — non quale
lista parla di questa cosa»*. Qui non c'è un pulsante ma un **numero**, e vale
identica: si consegna dove il numero **viene letto**.

⛔ Ne discende che **T-3 del brief precedente non ha cambiato niente a video**, e
va detto lì: quel cantiere si dichiara «perimetro DB completo», e per una delle
sue quattro consegne non è vero.

✅ **Decisa (D-1, §8.0): la vista si RITIRA**, col suo `manual/`. Le due sedi
della stessa aggregazione non convivono, e quella che ha perso è la vista: il
riepilogo che serve applica i **filtri dell'operatore**, e un aggregato per
(mese, stadio, emittente) non può applicarli. Finché resta viva senza lettori è
un oggetto che *sembra* presidiare un conteggio e non ne presidia nessuno.

### 5.3 Il giro di massa: la porta è il **pull**, non la lane

Il percorso vero, letto dal codice vivo:

```text
fn_list_emittibili_lane            → quali TERNE (emittente, tipo doc, utility)
                                     ⇒ QUANTI LOTTI NASCONO          ← T-4 è qui
        ↓  poi, dentro la pipeline del lotto
fn_list_commesse_emittibili        → quali COMMESSE visitare         ← nessun filtro
fn_emit_attivita_fatturabili_da_commessa
                                   → quali RIGHE emettere            ← nessun filtro
fn_select_attivita_fatturabili     → fattura solo ciò che il pull ha firmato
```

⇒ **La lane non decide che cosa il giro prende: decide quanti giri partono.**
Togliere il trattenuto dal suo conteggio toglie le sue righe dal *totale della
terna*; se la terna ha altro lavoro, il lotto **nasce comunque** e il pull poi
rastrella tutto ciò che trova. È esattamente `LTF-0010332`.

⭐ **La forma giusta esiste già in casa, ed è quella del perimetro mirato.**
`p_gruppi` è applicato in **due** punti — «quali commesse visitare» e «quali
righe emettere» — e il commento di `fn_list_commesse_emittibili` dice per
iscritto che il primo *non sostituisce* il secondo. Il trattenuto va nello stesso
posto, e il punto **decisivo è il secondo**: il trattenuto è per **documento**, e
una commessa ne alimenta più d'uno.

⛔ **E non basta il primo.** Filtrare le sole commesse escluderebbe anche i
documenti sani della stessa commessa: sarebbe un blocco più largo della regola.

### 5.4 ⚠️ Il giro non deve escludere **sé stesso**

Gli esiti si scrivono **dopo** il fan-out delle commesse. Al primo pull di un
giro non ce n'è nessuno, quindi il filtro non morde. Al **rerun dello stesso
lotto** — «avanza step» dal drawer, resume di un giro fermo — gli esiti del primo
tentativo ci sono e il lotto è ancora vivo: il pull troverebbe i propri documenti
trattenuti **da sé stesso** e non emetterebbe più niente.

⛔ **In silenzio**, ed è la forma peggiore: nessun errore, un lotto che riparte e
non produce niente, indistinguibile da un mese senza lavoro.

⇒ Il filtro esclude sempre il **lotto corrente**. Il pull riceve già l'identità
del giro (`p_emit_batch_id`), e da quella il lotto si risolve senza aggiungere
parametri: `fatturazione_lotti.lock_batch_id` ha un `UNIQUE`.

---

## 6. 🔴 Tre difetti del predicato **già applicato**

Non sono aggiunte a questo cantiere: sono correzioni di ciò che è in servizio dal
2026-09-09. Vanno decise **prima** di estendere lo stesso predicato a una terza
porta, o l'estensione le moltiplica.

### 6.1 ⛔ «Vivo» include i lotti **chiusi**, e il cancello non ha valvola

Il predicato di `vw_documenti_trattenuti_da_lotto` è `NOT is_abortito`. Letto sul
contratto — il seed di `config.stati_doc_fiscale`, che è progetto e non
fotografia:

| stato | `is_abortito` | `congela_fiscale` | `chiude_lotto` | per il predicato di oggi |
| --- | :---: | :---: | --- |
| DRAFT | f | f | f | trattenuto ✅ |
| EMESSA | f | f | f | trattenuto ✅ |
| **DEFINITIVA** | **f** | t | **t** | **trattenuto** 🔴 — ma il giro è **finito** |
| INVIATA · REGISTRATA | f | t | f | trattenuto 🔴 |
| ANNULLATA | t | t | f | libero ✅ |

⇒ Un documento fatturato in un lotto **regolarmente chiuso** resta trattenuto
**per sempre**.

⛔ **E l'uscita non c'è.** Togliere un documento dal giro è ammesso solo se il
lotto è **pre-fiscale** e il documento è in **ERRORE**
(`fn_check_documento_escludibile_da_giro`, motivi 1 e 4). Su un lotto DEFINITIVA
il primo motivo blocca, e il congelamento fiscale non ha un interruttore.

🔴 **Il caso vivo non è ipotetico, ed è un verbo che esiste**: «Riporta da
emettere» riporta le righe di commessa a `NON_EMESSA` e **non tocca gli esiti**.
⇒ Da ieri quel lavoro torna in «Da emettere», la riga è spenta con un gesto verso
un lotto chiuso, e la lane non lo offre **mai più**. È il difetto che il cantiere
voleva evitare, girato di 180 gradi.

🔴 **E la correzione ovvia è sbagliata anch'essa — provato scrivendola.** La
prima stesura di `R-0`/`L1` definiva il predicato come
`NOT is_abortito AND NOT chiude_lotto`, perché *«ha finito» sembra chiamarsi
`chiude_lotto`*. Non regge, e lo dice il **catalogo delle transizioni**:
`DEFINITIVA → INVIATA` è ammessa per il lotto, e INVIATA ha `chiude_lotto = f`.
⇒ Un lotto chiuso e poi inviato sarebbe tornato «aperto».

⭐ **`chiude_lotto` marca la TRANSIZIONE che chiude, non la PROPRIETÀ di essere
chiuso**: gli stati che vengono *dopo* non la portano. È la stessa forma di
difetto, un piano più in là — e sarebbe passata, perché in sviluppo un lotto in
INVIATA non c'è.

⭐ **L'asse giusto c'era già: `congela_fiscale`.** Vero su DEFINITIVA, INVIATA,
REGISTRATA e ANNULLATA; falso su DRAFT ed EMESSA.

> **Il predicato diventa `in_gioco`** = `COALESCE(NOT congela_fiscale, true)`,
> letto dalla sede unica e **fail-closed**: stato non risolvibile ⇒ trattenuto.

⚠️ **E il fail-closed è la ragione per cui i derivati sono DUE, non uno.** La
stessa colonna serve due domande che vogliono la risposta prudente **opposta**
sull'ignoto:

| domanda | chi la fa | ignoto ⇒ |
| --- | --- | --- |
| «si può ancora **uscire** dal giro?» | i quattro `fn_check_*` | `pre_fiscale = false` — non si tocca |
| «il lotto **trattiene** ancora?» | questa vista | `in_gioco = true` — non ci si mette le mani |

⛔ Con un flag solo, un lotto senza stato risolvibile sarebbe **libero** per un
secondo giro **e** non estraibile dal primo: il peggio dei due, in silenzio.
⭐ Sui sei stati a catalogo i due coincidono: differiscono **solo** sul settimo
caso, ed è tutta la ragione per cui sono due.

⭐⭐ **E coincide con la PORTA D'USCITA, che è la ragione per cui è quello giusto
e non una coincidenza.** `fn_check_documento_escludibile_da_giro` ammette di
togliere un documento dal giro **solo se il lotto è pre-fiscale**.
⇒ **Trattenuto ⇔ si può ancora uscire.** Se i due predicati divergessero
esisterebbe un documento trattenuto **senza via d'uscita** — cioè il cancello
senza chiave di questo stesso §6.1, ricomparso da un'altra porta.

⚠️ **E il pgTAP non se ne sarebbe accorto**: `test-documento-trattenuto-da-lotto-v1.sql`
ha cinque testimoni e nessuno è un lotto **chiuso**. ⚠️ In sviluppo, al
2026-09-09, i lotti finiscono quasi tutti ANNULLATA — è scritto nel brief
precedente come fatto datato — quindi il caso non si produce da solo: è
**verde per sottrazione**, e il testimone va **costruito**.

### 6.2 ⚠️ Manca il vincolo di competenza — e l'asimmetria è **dentro la stessa vista**

In `vw_dash_competenza_gruppi` convivono due LATERAL a tre righe di distanza:

| | lega |
| --- | --- |
| l'**esito** del tentativo | `gruppo_key` **e** `competenza_mese` del lotto |
| il **trattenuto** | la sola `gruppo_key` |

⭐ La motivazione del primo è scritta nel changeSet che l'ha fatto: *«il legame è
(documento, mese di competenza): senza il mese, il documento di settembre
erediterebbe l'errore di agosto»*. La stessa frase, parola per parola, vale per
il secondo — e non è stata applicata.

⇒ **Ma il vincolo giusto non è l'uguaglianza**, ed è la parte da non copiare a
occhio: lane e selezione lavorano in modo **cumulativo**
(`competenza_mese <= quella del lotto`), quindi un lotto di settembre trattiene
il documento anche per le competenze **precedenti**, e **non** per quella di
ottobre.

> Il legame è `lotto_competenza_mese >= competenza_mese della riga`.

⚠️ La vista espone già `lotto_competenza_mese`, e **nessuno la legge**: la
colonna c'è dal primo giorno e serviva a questo.

⚠️ **Attenzione nel pull**: `fn_list_commesse_emittibili` filtra la competenza
con l'**uguaglianza** mentre lane e `fn_select_attivita_fatturabili` usano il
`<=`. Non è materia di questo cantiere, ma decide dove il vincolo va scritto —
il posto sicuro è la **riga**, cioè il pull (M-1), dove la competenza della riga
c'è davvero.

### 6.3 ⚠️ Il verdetto è acceso a **ogni stadio**, anche su ciò che è già fatturato

Il LATERAL non guarda lo stadio. Un documento appena fatturato ha esito
`COMPLETED` sul suo lotto, che resta **DRAFT** finché non si preme «Rendi
definitive» ⇒ risulta **trattenuto**, e il conteggio che esclude i trattenuti lo
toglierebbe dai **fatturati**.

⇒ Il blocco significa qualcosa solo dove c'è un gesto da spegnere, cioè su
**`DA_EMETTERE`**. Sugli altri stadi lo stadio racconta già la storia — e per
`EMESSA_NON_FATTURATA` c'è già la dimensione `motivo_non_fatturata`, che il
valore `GIRO_IN_CORSO` lo porta da sé.

⛔ **Non si aggiunge un secondo vocabolario per la stessa cosa**: `GIRO_IN_CORSO`
e `TRATTENUTO_DA_LOTTO` risponderebbero alla stessa domanda su due stadi
diversi. Il verdetto si **restringe**, non si duplica.

---

## 7. ⚪ La risposta alla domanda del §4

**Stiamo con la lettura del brief, e la regola è già scritta.** Il tentativo è
avvenuto: la traccia resta. Ciò che non regge è **mostrarla come se contasse
ancora**.

⇒ Il difetto non è «si vede una colonna di troppo»: è che `ultimo_lotto_codice`
esce da un LATERAL che **non guarda lo stato del lotto**, quindi la colonna non
dice *quale delle due cose* sta dicendo — «il giro è in corso lì» oppure «lì c'è
stato un tentativo, ed è finito».

**La forma**: il lotto del tentativo esce **con il suo stato**, e chi rende
decide come dirlo (attenuato, barrato, con l'etichetta «annullato»). Una colonna
che porta il fatto e il suo stato non ha bisogno di essere nascosta.

⛔ **Non si toglie il dato**: è l'unica traccia a video del perché il documento è
tornato disponibile — toglierla lascerebbe l'operatore davanti a un documento che
ricompare senza spiegazione.
⚠️ **Ma il gesto verso quel lotto si spegne quando è annullato**: un bersaglio
verso un lotto morto è il «pulsante in un vicolo cieco» che
[api.md](../api.md) vieta esplicitamente.

---

## 8. Il piano

> **Decisione di Tid, 2026-09-09**: si fa la **strada B** — la sede unica del
> criterio — e la si fa **per intero e subito**, senza il passo tampone.
> Non c'è produzione: non c'è niente da riparare in fretta, e la fretta è
> l'unica cosa che avrebbe giustificato il cerotto.
>
> ⛔ **E c'è un secondo vincolo, ed è di metodo**: *«noto troppi passaggi tra DB
> e BE perché non abbiamo chiuso delle cose, o le abbiamo chiuse a metà»*.
> ⇒ In questo piano **non ci sono decisioni aperte**. Le tre che c'erano sono
> chiuse in §8.0, con il perché. Il **contratto** (§8.2) è scritto per intero
> **prima** che qualcuno scriva una riga: nomi, tipi, significati e chiavi i18n.
> Chi lavora sul backend o sul frontend non deve chiedere niente al team DB per
> partire.

### 8.0 Le tre decisioni che erano aperte — chiuse qui

| | Era | **Decisa così** | Perché |
| --- | --- | --- | --- |
| **D-1** | `vw_dash_competenza_gruppi_riepilogo` torna a essere letta o si ritira? | **Si RITIRA** (`DROP VIEW` + si cancella il suo `manual/`) | Non è stata scavalcata per sbaglio: è stata **superata per progetto**. Il riepilogo che serve applica i **filtri dell'operatore**, e una vista aggregata per (mese, stadio, emittente) non può applicarli. Tenerla viva significa tenere un oggetto che *sembra* la sede di un conteggio e non lo è — ed è esattamente ciò che ha fatto passare T-3 |
| **D-2** | si fa la sede unica della **fase di un lotto**? | **Sì**, `vw_lotti_fase`, **con tutti e cinque i lettori nello stesso passo** | Cinque letture inline della stessa cosa hanno già prodotto §6.1. Farla con un lettore solo sarebbe peggio di non farla |
| **V-1** | come si mostra il «lotto del tentativo» quando è annullato? | **Esce con il suo stato**; il testo resta, il **gesto** si spegne | Il tentativo è avvenuto ed è l'unica traccia del perché il documento è tornato disponibile. Ciò che non regge è mostrarlo come se contasse: quindi si aggiunge il fatto mancante — lo stato — invece di togliere il dato |

⭐ **Una quarta, che il piano B rende obbligatoria e va detta subito**:
`fn_diagnostica_gruppi_fatturabili` **non** riceve un contatore in più
(l'ipotesi `R-2` della stesura precedente). Riceve la **sede**: conta le classi
che il classificatore le consegna. Il contatore sarebbe stata la quinta
condizione scritta due volte.

---

### 8.1 La forma — un criterio, due fattori, tre letture

**Il classificatore**: una riga di `commesse_attivita`, e la risposta alla
domanda *«questa riga può entrare in un giro di fatturazione, e se no perché?»*.

> `vendite.vw_commesse_attivita_emittibilita` — una riga per riga di commessa,
> con `classe_emittibilita` a **vocabolario chiuso**.

| Classe | Quando |
| --- | --- |
| `EMESSA` | `stato_emissione = EMESSA` — è già uscita |
| `ANNULLATA` | `stato_emissione = ANNULLATA` |
| `RIFIUTATA` | non emessa, e l'approvazione è stata **negata** |
| `NON_APPROVATA` | non emessa, e l'approvazione **non è ancora arrivata** |
| `TRATTENUTA` | non emessa, approvata, ma **un lotto in gioco la tiene** |
| `PRONTA` | non emessa, approvata, libera |

#### ⭐ I due fattori sono ORTOGONALI, e qui sta il punto

Il difetto di oggi non è che i criteri siano due: è che **uno dei due era
implicito**. La lane pretende anche che la **testata** della commessa sia
emittibile; la diagnostica non lo mette nel proprio «pronta» e lo espone a
parte — di proposito, per poter dire *«le righe sarebbero pronte, è la commessa
a essere in BOZZA»*. ⇒ Due oggetti «uguali tranne un punto voluto», e un
lettore non può distinguere una differenza **nuova** da una **voluta**.

> **La riga ha una classe. La testata ha un flag. Chi decide dichiara quali
> dei due usa.**

| Chi | Cosa pretende |
| --- | --- |
| `fn_list_emittibili_lane` | `classe = PRONTA` **e** `commessa_emittibile` |
| `fn_diagnostica_gruppi_fatturabili` | conta **per classe**, ed espone il flag **a parte** |
| `fn_emit_attivita_fatturabili_da_commessa` (il pull) | `classe = PRONTA` **e** `commessa_emittibile`, **più** l'eccezione del proprio lotto |

⇒ Le due funzioni restano diverse — una filtra, l'altra conta — ma **non
possono più divergere sul criterio**, perché il criterio non è più scritto in
nessuna delle due.

#### ⛔ Che cosa il classificatore NON contiene, e non è una dimenticanza

**L'ammissibilità della riga** è intrinseca. Il **perimetro della domanda** no:
dipende da chi chiede. Restano quindi al chiamante, e nessuno li sposta dentro
la vista:

* il **tetto di competenza** (`competenza_mese <= …`): è il parametro della
  chiamata. È anche la ragione per cui `n_fuori_competenza` resta un conteggio
  della diagnostica e non una classe — quella riga è **pronta**, solo non per
  *questo* mese;
* i filtri di **perimetro** — billing account, utility, emittente, corsia
  immediata/differita, `p_gruppi`;
* l'**auto-esclusione del pull** (il proprio lotto): esiste solo per chi sta
  eseguendo un giro, e una vista non sa quale sia.

⚠️ **`tipo_doc_fiscale_id IS NOT NULL` esce dai criteri**, e non è una svista: è
un ramo **irraggiungibile** da quando il `CHECK` è validato (`20260815-30`), e la
diagnostica ha già tolto il proprio contatore per questa ragione
(`20260815-31`). I due presidi che lo tengono vero **esistono già**: i test 9 e
10 di `test-diagnostica-gruppi-fatturabili-v1.sql`.

#### La catena, dal basso

```text
config.stati_doc_fiscale        i tre assi, a catalogo
        ↓
vendite.vw_lotti_fase           ⭐ NUOVA — la fase di UN lotto, fail-closed una volta sola
        ↓
vendite.vw_documenti_trattenuti_da_lotto    quale documento un lotto in gioco tiene
        ↓
vendite.vw_commesse_attivita_emittibilita   ⭐ NUOVA — la CLASSE di una riga
        ↓
   ┌────────────────┬─────────────────────────┬──────────────────────────┐
 la lane        la diagnostica              il pull            la dashboard
 (filtra)       (conta per classe)     (filtra + il proprio lotto)   (spiega)
```

---

### 8.2 Il contratto — scritto prima, per non chiedersi niente dopo

> ⛔ **Questa sezione è il rimedio ai palleggi.** Tutto ciò che cambia di nome,
> tipo o significato è qui. Chi scrive il backend o il frontend parte da questa
> tabella e non aspetta nessuno.

#### 8.2.1 `vendite.vw_lotti_fase` — NUOVA

| Colonna | Tipo | Significato |
| --- | --- | --- |
| `lotto_id` | `bigint` | la chiave |
| `stato_codice_interno` | `varchar` | lo stato, per nome stabile |
| `is_abortito` · `congela_fiscale` · `chiude_lotto` | `boolean` **nullable** | i tre assi **grezzi**: sono il fatto, e un fatto ignoto si dice ignoto |
| `pre_fiscale` | `boolean` **NOT NULL** | «si può ancora **agire** sul documento?» — `COALESCE(NOT congela_fiscale, false)` |
| `in_gioco` | `boolean` **NOT NULL** | «il lotto **trattiene** ancora?» — `COALESCE(NOT congela_fiscale, true)` |

⭐ **Due derivati, stesso asse, fail-closed OPPOSTO** — e differiscono in **un
solo** caso, lo stato non risolvibile, che è precisamente la ragione per cui
sono due (§6.1). Sui sei stati a catalogo coincidono.
⚠️ **Non è la coppia della prima stesura**: là `in_gioco` era definito su
`chiude_lotto` ed era **sbagliato**. Correggendo la formula l'avevo tolto del
tutto, e quella seconda mossa era di troppo — la formula era sbagliata,
l'esistenza no.

⚠️ **Il fail-closed sta nel derivato, non nei grezzi**: se anche i tre assi
fossero già difesi, la stessa colonna direbbe «fatto» e «difesa» insieme, per
giunta con default in direzioni opposte (`is_abortito → false`,
`congela_fiscale → true`). Scritto una volta qui, non cinque volte fuori.
⚠️ **L'assenza di riga** significa lotto inesistente o fuori perimetro RLS. I
quattro `fn_check_*` la trattano già come errore (`E_LOTTO_NON_TROVATO`); chi
fa `LEFT JOIN` usa gli stessi valori chiusi.

#### 8.2.2 `vendite.vw_commesse_attivita_emittibilita` — NUOVA

| Colonna | Tipo | Significato |
| --- | --- | --- |
| `commessa_attivita_id` | `bigint` | la chiave — **1:1 con la riga di commessa** |
| `commessa_id` · `commessa_codice` | | la testata |
| `commessa_stato_codice_interno` · `commessa_stato_descrizione` | | per la logica e per la frase (alias fedeli, §6c) |
| `commessa_emittibile` | `boolean` | **il secondo fattore**, esposto e mai fuso nella classe |
| `gruppo_key` | `text` | da `fn_build_gruppo_fatturabile_key`, unica fonte |
| `competenza_mese` · `tipo_doc_fiscale_id` | | ciò su cui il chiamante applica il **suo** perimetro |
| `emittente_soggetto_ruolo_id` · `utility_id` · `billing_account_id` · `fatturazione_immediata` | | la **terna** e il perimetro, presi dove stanno |
| `stato_emissione` · `stato_approvazione` | | i fatti grezzi, per chi deve mostrarli |
| **`classe_emittibilita`** | `varchar` | il vocabolario chiuso di §8.1 |
| **`trattenuta_da_lotti`** | `bigint[]` | i lotti in gioco che la tengono, **ordinati**; `NULL` = non trattenuta |

⚠️ `NULL` e non array vuoto: è la convenzione già in uso sul perimetro del
lotto, e distingue «non trattenuta» da «trattenuta da nessuno», che non
significa niente.
⚠️ L'array è **ordinato per `lotto_id`**: chi ne vuole uno prende il primo e
non scommette.

⭐ **Una cosa è finita QUI invece che nei consumatori, ed è meglio così**: il
**legame di competenza** del trattenuto. §8.2.3 lo dava ai tre chiamanti, ma la
vista la competenza della riga ce l'ha — quindi il legame
`lotto_competenza_mese >= competenza della riga` è applicato **una volta sola**,
e i consumatori non devono ricordarselo. Era la riga che si dimentica.

#### 8.2.3 Oggetti DB modificati

| Oggetto | Che cosa cambia per chi lo legge |
| --- | --- |
| `vw_documenti_trattenuti_da_lotto` | il predicato diventa `pre_fiscale` (§6.1) e nasce il legame di competenza (§6.2). **Nessuna colonna nuova** |
| `fn_list_emittibili_lane` | **firma e uscita invariate**. Cambia da dove prende i criteri |
| `fn_list_commesse_emittibili` | **firma e uscita invariate** |
| `fn_emit_attivita_fatturabili_da_commessa` | **firma e uscita invariate**: il lotto corrente si risolve da `p_emit_batch_id`, che già riceve |
| `fn_diagnostica_gruppi_fatturabili` | **+2 colonne in coda**: `n_trattenute bigint`, `lotti_trattenenti jsonb` (array ordinato di `{id, codice}`, `[]` se nessuno). ⚠️ Le righe trattenute **escono da `n_pronte`** |
| `vw_dash_competenza_attivita` | **+2 colonne in coda**: `emissione_trattenuta boolean`, `emissione_trattenuta_da_lotti bigint[]` |
| `vw_dash_competenza_gruppi` | il verdetto `emissione_blocco_*` si accende **solo su `DA_EMETTERE`** (§6.3). **+3 colonne in coda**: `ultimo_lotto_id bigint`, `ultimo_lotto_stato varchar`, `ultimo_lotto_pre_fiscale boolean` |
| `vw_dash_competenza_mensile` | `n_attivita` e `valore_tot` **escludono** le trattenute. **+2 colonne in coda**: `n_attivita_trattenute integer`, `valore_trattenuto numeric` |
| `vw_dash_competenza_gruppi_riepilogo` | ⛔ **RITIRATA** (D-1) |
| indice | ⭐ **nuovo**: `ix_fatturazione_lotti_esiti_gruppo_key` — il classificatore cerca per `gruppo_key`, e l'unico indice che c'è è la `UNIQUE (lotto_id, gruppo_key)`, che per quella ricerca non serve. Indice **manuale**, non governato dalla policy FK |

⚠️ **Tutte le colonne nuove vanno IN CODA**: il backend legge la mensile e la
lista gruppi **per posizione**, e una colonna in mezzo sposta in silenzio tutte
quelle dopo.
⚠️ **`security_invoker` va ri-specificato** in ogni `CREATE OR REPLACE VIEW`:
non è visibile in `pg_get_viewdef` e PostgreSQL lo azzera senza dirlo.

#### 8.2.4 Contratto verso il backend e il frontend

| Superficie | Campo | Tipo | Significato |
| --- | --- | --- | --- |
| card competenza (mensile) | `n_attivita` | int | **esclude** le trattenute |
| | `n_attivita_trattenute` | int | quante ne sono state tolte |
| | `valore_trattenuto` | string | il loro valore (**stringa**: è denaro) |
| riepilogo lista gruppi | `n_gruppi`, `n_attivita`, `valore` | | **escludono** i trattenuti |
| | `n_gruppi_trattenuti` | int | quanti ne sono stati tolti |
| riga della lista gruppi | `emissione_blocco_reason` | string \| null | invariato — `TRATTENUTO_DA_LOTTO`, ora solo su `DA_EMETTERE` |
| | `emissione_blocco_reason_key` | string \| null | invariata |
| | `emissione_blocco_lotto_id` · `_codice` | | invariati |
| | `ultimo_lotto_id` | int \| null | ⭐ nuovo — per il gesto |
| | `ultimo_lotto_stato` | string \| null | ⭐ nuovo — il `codice_interno` |
| | `ultimo_lotto_pre_fiscale` | bool \| null | ⭐ nuovo — «quel tentativo conta ancora?». **Se false: testo sì, gesto no.** ⚠️ Stesso nome e stesso flag di `vw_lotti_fase`: un vocabolario solo per tutto il cantiere |
| gruppi non serviti (esito del giro) | `motivo` | string | ⭐ nuovo valore `TRATTENUTO_DA_LOTTO` |
| | `dettaglio` | string | la frase, che **nomina il lotto** |
| | `lotto_id` · `lotto_codice` | | ⭐ nuovi — il gesto si costruisce **da qui** |

⛔ **Il gesto NON passa dal canale `targets` dell'envelope**: quello porta il
bersaglio di un **errore** sollevato dal database, e qui non c'è nessun errore —
c'è un esito con un elenco strutturato che il frontend già riceve. Deciso, così
non resta niente da verificare a valle.

#### 8.2.5 Le chiavi i18n — l'elenco completo, da creare nello stesso giro

| Chiave | Dove | Testo (it) |
| --- | --- | --- |
| `vendite.emissione.blocco_reason.trattenuto_da_lotto` | ✅ **esiste già** | — |
| `vendite.dashboard_competenza.trattenuti_dichiarazione` | card + riepilogo | «{n} non selezionabili: già in un giro in corso» |
| `vendite.dashboard_competenza.ultimo_esito_lotto_annullato` | colonna tentativo | «tentativo nel lotto {lotto}, poi annullato» |
| `vendite.fatturazione.gruppo_non_servito.trattenuto_da_lotto` | esito del giro | «trattenuto dal lotto {lotto}, ancora in lavorazione» |

⚠️ **Una `reason_key` emessa dal database e assente dai `locales` è un tooltip
vuoto**, e `scripts/check_i18n_keys.py` fa fallire la build. ⇒ Le tre chiavi
nuove nascono **nello stesso giro** del backend, non dopo.

---

### 8.3 I passi — cinque lotti, ognuno chiuso in sé

⚠️ **Non è una scaletta di comodo**: ogni lotto finisce con qualcosa di
**verificabile**, e il successivo non torna sui file del precedente. È così che
si evitano i rimbalzi.

#### ✅ L1 — La fase del lotto (DB) — **SCRITTO il 2026-09-09, non applicato**

| | |
| --- | --- |
| Cosa | `vw_lotti_fase` + l'adozione dei **quattro** `fn_check_*`. ⚠️ Il **quinto** lettore (`vw_documenti_trattenuti_da_lotto`) adotta la sede in **L2**, dove viene riscritto comunque: due changeSet sullo stesso oggetto non servono |
| ChangeSet | `20260909-51` (la vista) · `-52` `-53` `-54` `-55` (i quattro lettori) |
| pgTAP | `test-vw-lotti-fase-v1.sql` (**P-9**, plan 6) — **verde** |
| Fatto quando | i pgTAP **esistenti** dei quattro `fn_check_*` sono verdi **senza essere stati toccati** |
| ⭐ | è la prova che l'adozione non cambia nessuna decisione: cambia solo da dove si legge il fatto |

**Provato il 2026-09-09, prima di applicare** (fatti datati):

| Prova | Esito |
| --- | --- |
| i cinque cancelli statici della CI | ✅ verdi |
| l'SQL **estratto** dai changeSet, eseguito in una transazione annullata | ✅ i cinque corpi compilano |
| **equivalenza sui dati veri**: stesso esito prima e dopo su 83 lotti, 26 coppie (lotto, fattura) e 59 coppie (lotto, documento) | ✅ **0 divergenze su 251 chiamate** |
| identità delle funzioni dopo il `%TYPE` in firma | ✅ **0 firme cambiate**, nessun overload |
| `P-9` con la vista creata dentro la transazione | ✅ **6/6** |

🔴 **E la prova ha trovato un difetto nel changeSet, prima che uscisse**: la
prima stesura definiva `in_gioco = NOT is_abortito AND NOT chiude_lotto`, e su
`INVIATA`/`REGISTRATA` diceva «aperto» su un lotto già chiuso (§6.1). Corretto
in `pre_fiscale`, e il caso è ora il **test 3** di `P-9`.

#### ✅ L2 — Il predicato corretto (DB) — **SCRITTO il 2026-09-09, non applicato**

| | |
| --- | --- |
| Cosa | `-56` la sede guadagna il **secondo derivato** `in_gioco` · `-57` `vw_documenti_trattenuti_da_lotto` lo legge e adotta la sede (è il **quinto lettore** di L1, fatto qui perché la vista viene riscritta comunque) |
| pgTAP | `test-vw-lotti-fase-v1.sql` **plan 8** · `test-documento-trattenuto-da-lotto-v1.sql` **plan 7** — entrambi verdi |
| ⚠️ Il legame di **competenza** | **non è in questa vista**: non conosce la competenza della riga che la interroga. Espone `lotto_competenza_mese` e lo dichiara nel proprio `COMMENT`; lo applicano i consumatori in **L3** e **L4**, con `>=` e **non** `=` (la selezione è cumulativa) |

**Provato il 2026-09-09** (fatti datati):

| Prova | Esito |
| --- | --- |
| i sei cancelli statici della CI | ✅ verdi |
| `P-9` con `-56` e `-57` in transazione | ✅ **8/8** |
| il test del trattenuto, idem | ✅ **7/7** |
| **mutazione 1** — rimesso `NOT is_abortito` | ✅ i test **6 e 7 rossi**, gli altri cinque **verdi** |
| **mutazione 2** — la correzione «ovvia» `NOT is_abortito AND NOT chiude_lotto` | ✅ il **6 torna verde**, il **7 resta rosso** — è esattamente il difetto che il test 7 esiste per prendere |

🔴 **E anche qui la prova ha trovato un difetto prima che uscisse.** La stesura
di L2 stava per usare `pre_fiscale`, **capovolgendo il fail-closed** del test 4:
un lotto senza stato risolvibile sarebbe diventato **libero**. Da lì il secondo
derivato — §6.1.

#### ✅ L3 — Il classificatore e i suoi quattro lettori — **SCRITTO il 2026-09-09, non applicato**

| | |
| --- | --- |
| ChangeSet | `-58` l'indice · `-59` il **classificatore** · `-60` la lane · `-61` la discovery commesse · `-62` **il pull** · `-63` la diagnostica (`DROP`+`CREATE`: `RETURNS TABLE` cambia) |
| pgTAP | `test-vw-commesse-attivita-emittibilita-v1.sql` (9) · `test-pull-non-prende-trattenuti-v1.sql` (**P-5**, 5) · `test-specchio-lane-diagnostica-v1.sql` (**P-8**, 4) · `test-diagnostica-gruppi-fatturabili-v1.sql` 12 → **14** (**P-7**) |
| ⛔ | qui, e solo qui, si tocca la lane. Il §8.5 diceva di non toccarla: valeva per il cerotto, **non** per la sede unica |

**Provato il 2026-09-09** (fatti datati):

| Prova | Esito |
| --- | --- |
| i sei cancelli statici + il guardrail alias `codice_interno` | ✅ verdi |
| **specchio sui dati veri**: righe ammesse dalla lane vs classe `PRONTA` | ✅ **0 divergenze in entrambe le direzioni** |
| **lane invariata**: uscita prima/dopo su 5 combinazioni di parametri | ✅ **0 divergenze** |
| **diagnostica**: i contatori non toccati, prima/dopo | ✅ **0 righe divergenti** |
| e l'invariante «il calo di `n_pronte` è esattamente `n_trattenute`» | ✅ **0 violazioni** |
| il test **esistente** della diagnostica, contro L3 | ✅ **12/12 senza modifiche** |
| i quattro pgTAP nuovi/aggiornati | ✅ 9/9 · 5/5 · 4/4 · 14/14 |
| **mutazione**: lane nuova + diagnostica vecchia — cioè lo **stato del 09-09** | ✅ `P-8` **rosso su 1 e 3**, verde sul 2 |

⭐ **La mutazione è la prova che il cantiere cercava**: ricostruito il giorno in
cui lo specchio si è rotto, `P-8` sarebbe stato **rosso lo stesso giorno**.

⭐ **E la catena si vede end-to-end sui dati veri**: l'unico gruppo trattenuto
del database esce da `n_pronte`, entra in `n_trattenute`, e `lotti_trattenenti`
nomina **LTF-0010331** — il lotto del collaudo di Tid.

⚠️ **Un effetto atteso e verificato**: dalla discovery delle commesse sparisce
una commessa (34137) che ha **una sola riga, trattenuta**. Non ha niente da
dare, e visitarla produceva un pull a vuoto registrato come lavorato.

#### ✅ L4 — La dashboard: il conteggio e il tentativo — **APPLICATO il 2026-09-09 (17:52)**

> 🔴 **Un secondo lettore della vista ritirata non era stato censito** — vedi
> L4-bis in coda a questa sezione. Trovato lo stesso giorno rilanciando la
> baseline pgTAP, non da una segnalazione a video.

| | |
| --- | --- |
| DB | `-64` ritira il riepilogo (D-1) · `-65` `vw_dash_competenza_attivita` (+2) · `-66` `vw_dash_competenza_gruppi` (verdetto dall'aggregato, +3 per il tentativo) · `-67` `vw_dash_competenza_mensile` (`FILTER` + 2) |
| BE | `vendite_repository` (mensile +2 · lista gruppi +3 · riepilogo con `FILTER` e `n_gruppi_trattenuti`) · `vendite_service` (la quota trattenuta nella cella della card) · `types.py` |
| FE | `DashboardCompetenzaView.vue`: la card dichiara la quota trattenuta · il riepilogo dichiara i gruppi tolti · il titolo del tentativo dice **se conta ancora** e il gesto verso il lotto si spegne · **4 chiavi i18n** in `it.json` e `en.json` |
| pgTAP | `test-vw-dash-competenza-v1.sql` 20 → **23** — verde |

**Provato il 2026-09-09** (fatti datati):

| Prova | Esito |
| --- | --- |
| **la card sul caso del collaudo** (09/2026, DA_EMETTERE) | ✅ `n_attivita` **3** (era 4) · `n_attivita_trattenute` **1** · valore **285** (era 300) · trattenuto **15** |
| la lista | ✅ `ORD0036005` · `TRATTENUTO_DA_LOTTO` · **LTF-0010331** |
| **V-1**, il lotto del tentativo | ✅ `LTF-0010332` esce con `ANNULLATA` / `pre_fiscale = f`; `LTF-0010331` con `DRAFT` / `t` |
| il verdetto fuori da `DA_EMETTERE` | ✅ **0 righe**, senza nessun filtro sullo stadio |
| costo del join al classificatore su `vw_dash_competenza_attivita` | ✅ 5,4 → 5,7 ms, e **106 righe prima, 106 dopo** (non moltiplica) |
| `test-vw-dash-competenza-v1.sql` | ✅ **23/23** |
| il cancello `check_i18n_keys.py` | ✅ pulito |

⭐ **La card ora dice esattamente quello che dice la lista** — che era la
richiesta 1 del backend, verificata sui numeri del collaudo.

⚠️ **Il `FILTER` invece della `WHERE` non è teoria**: il test `15-ter` asserisce
**entrambe** le metà — il numero cala **e la riga resta**. Con una `WHERE` il
bucket sparirebbe proprio quando il numero serve.

⚠️ **La build del frontend non è stata lanciata**: `vite` non è installato sul
server DB. Le modifiche `.vue` e i `locales` vanno provate a video sul server
backend — ⛔ e finché non lo sono, i campi sono *dichiarati e non letti*, che
§12.5.5 chiama peggiore della loro assenza.

⭐ **Due decisioni prese scrivendo, e vale la pena saperle:**

1. **§6.3 si è risolto da sé.** Il verdetto doveva «accendersi solo su
   `DA_EMETTERE`»: non serve nessun filtro, perché la classe `TRATTENUTA` vuole
   `NON_EMESSA + APPROVATA`, che **è** quello stadio. È vero per costruzione,
   non per disciplina — e il presidio (`15-quinquies`) lo asserisce lo stesso.
2. **Il verdetto si legge dalla CLASSE, non dall'array.** `trattenuta_da_lotti`
   è valorizzato anche su una riga già `EMESSA` il cui documento è in un lotto
   vivo: guardando l'array, un documento appena fatturato — esito `COMPLETED`
   su un lotto ancora `DRAFT` — risulterebbe «trattenuto» e **uscirebbe dai
   conteggi dei fatturati**.

#### 🔴 L4-bis — il censimento dei lettori si era fermato al primo

Il `-64` ritira `vendite.vw_dash_competenza_gruppi_riepilogo`, e la sua
intestazione **censisce i lettori**: nomina il test `15-ter` di
`test-vw-dash-competenza-v1.sql` e lo fa togliere nello stesso giro. ✅ Quello.

⛔ **I lettori erano due.** Il test 10 di
`db/pgtap/vendite/test-vw-dash-competenza-gruppi-v1.sql` — *«A5/A9: il riepilogo
coincide con la somma dell'elenco»* — legge la stessa vista, e non è stato
guardato. Applicato il `-64`, quel file muore con
`la relazione "vendite.vw_dash_competenza_gruppi_riepilogo" non esiste`.

⚠️ **E non è «un test rosso»: è un ERRORE di esecuzione**, quindi `psql` si
ferma lì e il file perde il plan. Otto asserzioni sane eseguite, `pg_prove` che
dice `Bad plan. You planned 9 tests but ran 8`, e il rosso che in un elenco di
277 file si legge come uno qualunque.

✅ **Rimedio 2026-09-09**: il test 10 è stato **tolto**, non riscritto — il suo
soggetto non esiste più, e l'invariante che portava è già dichiarato dove il
numero si calcola (`P-10`, Django). Il perché sta scritto in coda al file, dove
il test stava: *un test che sparisce senza dire dove è finito ciò che
verificava lascia un buco che nessuno sa di avere.*

⭐ **La lezione, e vale oltre questo caso**: la ricerca dei lettori si fa sul
**nome dell'oggetto in tutto il repository**, non sui file che si ha in mente.
Qui il primo lettore era quello che il cantiere stava già toccando — cioè quello
che si sarebbe trovato comunque — e il secondo stava in un file che il cantiere
non apriva.

```bash
grep -rn "<nome_oggetto>" --include='*.sql' --include='*.py' --include='*.vue' .
```

#### ✅ L5 — La diagnosi che smette di mentire — **SCRITTO il 2026-09-09**

| | |
| --- | --- |
| BE | `MOTIVO_TRATTENUTO_DA_LOTTO` + l'helper `_motivo_trattenuto` (il ramo serve in **due** punti: si estrae, non si ricopia) · `spiega_gruppi_non_serviti` porta `lotto_id`/`lotto_codice` nel dettaglio strutturato |
| FE | l'etichetta del motivo (i18n, `it` + `en`) e la voce del toast che **nomina il lotto** |
| test | `TrattenutoDaLottoTests` — **7 casi** in `test_fatturazione_job_helpers.py` |

**Provato il 2026-09-09** — ⚠️ Django non è installato sul server DB, quindi la
suite non è stata lanciata: la **logica** è stata eseguita in isolamento (le
funzioni non dipendono da Django), **14/14**, e comprende i **cinque** casi
preesistenti, tutti invariati.

| Prova | Esito |
| --- | --- |
| un gruppo trattenuto **non** cade più su `NON_DETERMINATO` | ✅ |
| e la frase **nomina il lotto**, e non dice più «verificare emittente e utility» | ✅ |
| il verso opposto: senza trattenute il ripiego resta **identico** | ✅ |
| pronte **e** trattenute insieme → vince il trattenuto | ✅ |
| ma la **testata bloccata** vince comunque (causa certa, precede) | ✅ |
| più lotti → nomina il primo e conta gli altri | ✅ |
| il dettaglio strutturato porta il lotto, e **solo** su quel motivo | ✅ |
| non approvate · rifiutate · sconosciuto · fuori competenza · già emesse | ✅ **invariati** |

**L'ordine dei rami**, che è la parte da non sbagliare:

1. nessuna riga → gruppo sconosciuto;
2. ci sono **pronte** → testata non emittibile › corsia fallita › **trattenuto** › non determinato;
3. nessuna pronta e ci sono **trattenute** → trattenuto;
4. non approvate › rifiutate › fuori competenza › …

⭐ Il ramo compare in **due** punti (2 e 3) e sta in un helper: ricopiarlo
sarebbe la seconda sede di una frase che deve restare una.
⚠️ E sta **prima del ripiego** e **dopo le due cause certe**: «trattenuto» è
certo (si sa quale lotto), quindi batte il generico; una testata bloccata vale
comunque.

⚪ **Il gesto è dove RESTA, non nel toast** — ed è una scelta dichiarata, non
una consegna a metà. Il piano diceva «il gesto sull'esito del giro»: un pulsante
dentro un toast che sparisce dopo cinque secondi non è un gesto, e `useNotify`
ha solo `errorConAzioni` (persistente, ma questo non è un **errore**: nulla si è
rotto). ⇒ Nel toast vanno le **parole** che nominano il lotto; il **gesto** sta
sulla riga della lista, dove esiste già da `L4` e dove resta finché serve.
⛔ Inventare un `warnConAzioni` per un solo punto di chiamata sarebbe
un'estensione di un building block condiviso che nessuno ha chiesto.

> 🔴 **Perché L5 non è un dettaglio.** Oggi un gruppo trattenuto cade nel
> ramo di ripiego, e l'operatore legge:
> *«N attività risultano pronte ma il gruppo non è entrato in nessun lotto:
> verificare emittente e utility della commessa»*.
> Emittente e utility sono **a posto**: la frase manda a controllare due cose
> giuste e non nomina l'unica che conta. È il §9.2 visto da chi lo subisce.

**L'ordine dei rami nella funzione** — si scrive, perché un ordine non scritto
è un ordine che il prossimo cambia:

1. nessuna riga → gruppo sconosciuto;
2. ci sono righe **pronte** → testata non emittibile › corsia fallita ›
   **trattenuto** › non determinato;
3. nessuna pronta e ci sono **trattenute** → trattenuto;
4. non approvate › rifiutate › fuori competenza › …

⭐ Il ramo «trattenuto» compare in due punti: si estrae in un helper locale, non
si ricopia. ⚠️ E sta **prima** del ripiego e **dopo** le due cause certe: è una
causa **certa** (si sa quale lotto), quindi batte il generico, e non batte una
testata bloccata, che vale comunque.

---

#### 🔴 L6 — I quattro presidi nuovi erano MUTI proprio dove gira la CI

> Trovato il 2026-09-09 sera lanciando la baseline contro `zeroerp_ci`, cioè il
> database **ricostruito dai changelog**. Su `dbdev` erano tutti e quattro
> verdi.

```text
❌ REGRESSIONI — rossi NUOVI, non erano in baseline:
   test-pull-non-prende-trattenuti-v1.sql            ERRORE_FIXTURE   (P-5)
   test-specchio-lane-diagnostica-v1.sql             ERRORE_FIXTURE   (P-8)
   test-vw-commesse-attivita-emittibilita-v1.sql     ERRORE_FIXTURE   (L3)
   test-vw-lotti-fase-v1.sql                         ERRORE_FIXTURE   (P-9)
```

**Una sola causa**, identica per tutti e quattro:

```text
ERRORE: Nessun emittente fiscale attivo: le fixture non hanno su cosa lavorare.
CONTESTO: funzione PL/pgSQL fn_pgtap_emittente_operatore() riga 55 a RAISE
```

⛔ **E non è un rosso qualunque: è un ERRORE, quindi il file non esegue NEMMENO
UNA asserzione.** `pg_prove` stampa `Bad plan. You planned 8 tests but ran 0`.
La copertura di quei quattro presidi su un database ricostruito valeva **zero**,
non «parziale».

### Che cosa era successo

Le intestazioni dei quattro file dichiarano tutte, con parole loro, *«i casi si
costruiscono, non si cercano: su un database ricostruito da zero un testimone
trovato non esiste»*. **E costruivano tutto — tranne il mondo sotto**: l'emittente
lo prendevano con `script.fn_pgtap_emittente_sr_operatore()` (che lo **cerca**) e
il cliente con un `ORDER BY b.id LIMIT 1` su `anagrafiche.billing_account`.

⇒ Su `zeroerp_ci` `anagrafiche` è **vuoto**, e non per un difetto: emittenti,
soggetti e billing account sono seed di **`dati_macchina`** — nascono dall'uso,
e un database ricostruito dai changelog non li ha. Misurato quel giorno:
`emittenti_fiscali` 0 · `auth_user` 0 · `user_emittenti_fiscali` 0 ·
`billing_account` 0. Il **catalogo** invece c'è tutto (articoli, unità di
misura, valute, tipi documento, stati commessa): il confine è esattamente
quello dichiarato in [linee-guida-sql §11.7](/linee-guida-sql).

⭐ **La disciplina era scritta e non applicata fino in fondo.** Non è una svista
di distrazione: è che «costruire i casi» sembra riferirsi alle *righe di
dominio* — le commesse, i lotti, le attività — mentre il pezzo che manca è
sempre lo stesso e sta sotto: **l'azienda e chi ci lavora**.

### Il rimedio, e la sede c'era già

Lo stesso 2026-09-09 questa casa ha costruito i mattoncini che servono, per il
cantiere del perimetro emittente sui satelliti:
`dbops.fn_pgtap_crea_emittente_operatore()` (`20260909-26`) e
`dbops.fn_pgtap_crea_cliente_ba()` (`20260909-31`, terzo argomento dal `-43`).
⇒ Non c'era niente da inventare: i quattro file **non li usavano**.

| File | Come è stato sanato | Runner |
| --- | --- | --- |
| `test-vw-lotti-fase-v1.sql` | costruisce l'azienda e apre il contesto sul suo operatore | **resta `app`** |
| `test-vw-commesse-attivita-emittibilita-v1.sql` | azienda + cliente costruiti | `owner`, motivato |
| `test-pull-non-prende-trattenuti-v1.sql` | idem | `owner`, motivato |
| `test-specchio-lane-diagnostica-v1.sql` | idem | `owner`, motivato |

### ⚠️ Perché tre su quattro passano a `owner`, e uno no

Il primo ha bisogno del **solo emittente**, e quello un operatore lo può
costruire: resta `app`, quindi continua a esercitare la RLS.

Gli altri tre hanno bisogno anche di un **cliente fatturabile**, e lì
`dbops.fn_pgtap_crea_cliente_ba` **non gira come `zeroerp_app`** — verificato in
transazione annullata su entrambi i database:

* l'`INSERT` su `anagrafiche.billing_account` è un `… RETURNING id`, quindi la
  riga appena scritta va anche **riletta**;
* la policy di lettura è `fn_scope_ef_whitelist_via_efba(utente, ba)`, cioè
  «questo BA è legato a un emittente del tuo perimetro?»;
* ma il legame lo scrive `trg_billing_account_z90_link_ef_ins`, che è un
  trigger **z90**, cioè *dopo*.

⇒ Al momento del `RETURNING` il legame non esiste ancora e la riga non è
visibile a chi l'ha appena scritta. ⚠️ Su `zeroerp_ci` il difetto **non si
vedeva**, perché con un solo emittente il ripiego al gestore di default cade
sulla stessa azienda: è il caso in cui due database rispondono diverso alla
stessa domanda, e quello popolato ha ragione.

⛔ **E aprire il contesto prima non risolve, peggiora**: con un operatore in
sessione il legame lo scrive **anche** il trigger, e i due si scontrano su
`uq_emittenti_fiscali_ba` — *un BA ha esattamente un emittente*.

⇒ Il marcatore `pgtap-runner: owner` è quello previsto dal **criterio 2** di
`scripts/testpgtap.sh` (*«la fixture costruisce un mondo che l'operatore non
deve/può creare»*), ed è la stessa motivazione dei **sei** call-site esistenti
di quel building block (`db/pgtap/rls/*-satelliti.sql`), che infatti su
`zeroerp_ci` sono verdi.
⚠️ **Il costo va detto**: da owner quei tre file non esercitano più la RLS. Non
è la cosa che verificano — le loro asserzioni filtrano sugli id costruiti, e la
`security_invoker` delle viste è presidiata da
`rls/test-rls-viste-security-invoker.sql` — ma è un passo indietro, ed è il
prezzo di un building block che oggi non ha una via per l'applicazione.
🔴 **Resta aperto**: se `fn_pgtap_crea_cliente_ba` imparasse a farsi rileggere
(legame scritto *prima* del `RETURNING`, o nessun `RETURNING`), i tre
tornerebbero `app` e il marcatore sparirebbe da nove file. È un cantiere suo.

### ⭐ La lezione, e non è «usare il building block»

Un test verde su `dbdev` e un test verde su un database ricostruito **non sono
la stessa affermazione**, e la differenza non si vede rileggendo il file: si
vede solo lanciandolo là. Questi quattro *dichiaravano* in intestazione di
essere costruiti, e la dichiarazione era sincera — semplicemente si fermava un
livello sopra il punto in cui il database si svuota.

⇒ **Un presidio nuovo si prova sui DUE database prima di dichiararlo fatto**,
e il comando è già in casa:

```bash
PGTAP_ENV_FILE=db/internal.ci.env PGTAP_BASELINE=db/pgtap/baseline-rossi-ci.tsv \
  scripts/pgtap-baseline.sh vendite
```

### 8.4 I presidi

⭐ **Ogni prova ha il suo contrario.** Col solo verso «blocca» passerebbe anche
un predicato che blocca **tutto**; col solo «non blocca», uno che non blocca
**mai**.

| | File | Prova | Il suo contrario |
| --- | --- | --- | --- |
| **P-1** | `test-documento-trattenuto-da-lotto-v1.sql` | lotto **chiuso** (DEFINITIVA) ⇒ **libero** | lotto DRAFT ⇒ trattenuto (esiste, test 1) |
| **P-2** | idem | competenza **successiva** al lotto ⇒ **libera** | competenza **precedente** ⇒ trattenuta (il cumulativo) |
| **P-3** | `test-vw-dash-competenza-v1.sql` | su `FATTURATA` il verdetto è **spento** | su `DA_EMETTERE` è acceso (esiste, 15-bis) |
| **P-4** | idem | la card **esclude** e **dichiara** in `n_attivita_trattenute` | il bucket **non sparisce** quando è tutto trattenuto |
| **P-5** | ⭐ nuovo, sul pull | non emette un documento trattenuto da un **altro** lotto in gioco | **riprende** i propri documenti al **rerun** dello stesso lotto |
| **P-6** | `test-documento-trattenuto-da-lotto-v1.sql` | dopo «Riporta da emettere» da un lotto **chiuso**, il documento **torna offerto** | — è il gemello negativo di §6.1 |
| **P-7** | `test-diagnostica-gruppi-fatturabili-v1.sql` | una riga trattenuta è in `n_trattenute` e **non** in `n_pronte`, e `lotti_trattenenti` la nomina | una riga libera resta in `n_pronte` (esiste, test 2-3) |
| **P-8** | ⭐ nuovo — **il presidio dello specchio** | su una fixture costruita, le righe ammesse dalla lane e quelle contate `PRONTA` dalla diagnostica sono **le stesse** | e con la testata in BOZZA **divergono**, perché è il fattore che solo la lane pretende |
| **P-9** | ✅ `test-vw-lotti-fase-v1.sql` (plan 8) | `pre_fiscale`/`in_gioco` veri su DRAFT ed EMESSA | falsi su DEFINITIVA, **INVIATA**, **REGISTRATA** e ANNULLATA · ⭐ e sull'**ignoto DIVERGONO** (test 8): è l'unico posto in cui la differenza fra i due flag è visibile |
| **P-10** | ⭐ nuovo — **Django**, con DB | il riepilogo della lista **esclude** i trattenuti e li dichiara | il totale di perimetro **non** cambia (è l'altro numero) |

⚠️ **I casi si costruiscono**, non si cercano fra i lotti di oggi: su un
database ricostruito da zero un testimone «trovato» non esiste, e il test
diventa verde smettendo di verificare.

⭐ **`P-8` è quello che vale il cantiere**: esisteva uno specchio **dichiarato**
e niente che verificasse che fosse ancora tale. Con `P-8` in casa, T-4 sarebbe
stato rosso il giorno stesso.

⚠️ **`P-10` è in Django e non in pgTAP** perché il numero lo calcola una query
del backend: il presidio va dove sta il calcolo. Si appoggia a
`richiedi_db_provvisto` (`ZEROERP_TEST_DB_E2E`, acceso in CI).

---

### 8.5 ⛔ Cosa NON si fa

* ⛔ **Non si toccano le cinque `fn_list_*_da_pushare`**: la loro regola
  (`LIBERA`) c'è già — §3.1 del brief precedente, e vale ancora;
* ⛔ **Non si fonde la testata nella classe**: `commessa_emittibile` resta un
  fattore **a parte**, o la diagnostica perde la sola cosa che sa dire meglio
  della lane (§8.1);
* ⛔ **Non si porta il tetto di competenza dentro il classificatore**: è
  perimetro della domanda, non ammissibilità della riga;
* ⛔ **Non si estrae in funzione** l'aggancio al trattenuto — §9.4, e la ragione
  è di **piano di esecuzione**;
* ⛔ **Non si unifica `classe_emittibilita` con lo `stadio`** della dashboard:
  lo stadio dice *a che punto del ciclo* è il lavoro (e arriva fino a
  `FATTURATA`), la classe dice *se può entrare in un giro*. Il confine si
  **dichiara** e si presidia: dentro `vw_dash_competenza_attivita`,
  `stadio = DA_EMETTERE` ⇔ `classe ∈ {PRONTA, TRATTENUTA}` con la testata
  emittibile — ed è un'asserzione di `P-8`;
* ⛔ **Non si cancellano gli esiti** per liberare un documento: l'esito dice
  com'è andata. Se un giorno servirà una valvola sarà un **verbo**, con motivo e
  traccia, non una `DELETE`;
* ⛔ **Nessun codice errore nuovo**: qui non si solleva niente, si **offre di
  meno**;
* ⛔ **Nessuna migrazione applicata senza che Tid lo dica**, e la numerazione
  dei changeSet si assegna **al momento di scrivere** (è globale per data e
  scade nel minuto).

---

### 8.6 Stato — 2026-09-09

| | |
| --- | --- |
| Analisi | ✅ fatta, letta dal codice vivo (doc auto-gen + backend) |
| Censimento del riuso | ✅ fatto — §9 |
| Decisioni | ✅ **nessuna aperta**: D-1, D-2 e V-1 chiuse in §8.0 |
| Contratto DB ↔ BE ↔ FE | ✅ scritto per intero — §8.2 |
| DB | ✅ **L1** (`-51..-55`), **L2** (`-56`, `-57`), **L3** (`-58`..`-63`) e **L4** (`-64`..`-67`) applicati il 2026-09-09, pgTAP verdi · ⚠️ **L4-bis**: un secondo lettore della vista ritirata è emerso dopo l'apply e il suo pgTAP è stato sanato · 🔴 **L6**: i quattro presidi nuovi erano MUTI su `zeroerp_ci` (fixture che *cercava* emittente e cliente invece di costruirli) — sanati, verdi ora su **entrambi** i database |
| BE / FE | ✅ **L4 e L5 scritti e ora PROVATI** sul server backend (2026-09-09): suite Django **4574 verde**, `npm run build` verde, lint pulito |
| ✅ Chiuso | suite · build · **collaudo a video** fatto da Tid, e i numeri riletti dal backend sulla cella `09/2026 · DA_EMETTERE`: riepilogo **1**, trattenuti **2**, perimetro **3** — `1 + 2 = 3`, le tre cifre si riconciliano fra loro e con la lista |

⛔ **`changelog-autogen.yaml` non è stato toccato**: si rigenera con lo script,
e non a mano. I cinque file nuovi entrano in quel giro.

### ✅ CHIUSO il 2026-09-09

Il difetto di partenza è chiuso: la card diceva **4** e la lista ne mostrava
**3**. Ora la card conta **solo ciò che si può prendere**, **dichiara** quanti ne
ha tolti, e il totale di perimetro resta quello di tutta la cella.

⚠️ **Quello che la prova sul server backend ha trovato, e che il DB non poteva
vedere**: 31 test rossi, per tre cause tutte della stessa famiglia — colonne e
firme avanzate a DB, fixture rimaste indietro. La terza merita di essere
ricordata: `fn_segna_esito_gruppo_lotto` non è più uno scalare ma
`TABLE(marcati, usciti, fuori_perimetro)`, e chiamata in contesto scalare il
record esce **intero** — `fetchone()[0]` restituiva la stringa `('1','0','0')`,
che non solleva e non sarà mai `1`. La produzione era già allineata.

⭐ **P-10 del §8.4 è in casa** (`test_riepilogo_esclude_trattenuti.py`), e il
caso lo **costruisce**: il lotto in gioco si fabbrica invece di cercarlo, o su
un database ricostruito da zero il test farebbe `skipTest` e diventerebbe verde
smettendo di verificare — che è ciò che questo stesso §8.4 vieta.

📌 **Ricade sul BE, e non è di questo brief**: il contesto operatore RLS è stato
estratto in `apri_contesto_operatore` (BB in `apps/core/tests/db_e2e.py`), col
guard che le tre copie non avevano — `SET LOCAL` fuori da una transazione
PostgreSQL lo **ignora**, e lì si legge zero credendo di aver misurato.

## 9. Riuso — il censimento fatto **prima** di scrivere

> Richiesta di Tid, 2026-09-09: *«prima di implementare verifica che non stiamo
> replicando della logica che non si possa già riutilizzare»*. Il censimento ha
> cambiato il piano: ha trovato un **quarto difetto** (§9.2) e ha spostato il
> cantiere dal cerotto alla **sede unica** — la strada B che Tid ha scelto (§8).

### 9.1 Quello che c'è già e **non si riscrive**

| Oggetto | Risponde a | Perché **non** è la sede di questo cantiere |
| --- | --- | --- |
| `fn_build_gruppo_fatturabile_key` | qual è la chiave del documento | ✅ **si usa**, e resta l'unica fonte: nessun consumatore la ricostruisce |
| `vw_documenti_trattenuti_da_lotto` | è trattenuto? | ✅ **è la sede**: `R-0` la **corregge**, non ne affianca una seconda |
| `fn_get_stato_push_segment` + le cinque `fn_list_*_da_pushare` | LIBERA / ALLOCATA / EMESSA | misurano l'**esito** del lavoro, non che il lavoro sia **in corso** — §3.1 del brief precedente, e vale ancora |
| `vw_lotti_gruppi_serviti` | quali gruppi un lotto ha **servito** | un documento in ERRORE **non è servito** e va trattenuto lo stesso: risponderebbe «no» proprio sul caso |
| `fn_esito_gruppi_giro` | a **consuntivo**, che fine ha fatto un gruppo | ancorata ai lotti di **un giro**; qui la domanda è su un documento, prima che un giro esista |
| `script.fn_gruppi_di_commessa_nel_lotto` | commessa → documenti in un lotto | è la conversione per chi ha in mano la **commessa**; `M-1` lavora **per riga** e la chiave ce l'ha già |
| `script.fn_check_commessa_pronta_fatturazione` | la **testata** può passare a PRONTA? | altra entità, altra domanda |
| `conta_con_perimetro` (BB backend) | quante righe sto **nascondendo** | serve quando il `WHERE` le ha già tolte; qui restano nel perimetro e basta un `COUNT(*) FILTER`. ⚠️ Scritto perché è la cosa che si prende d'istinto |

### 9.2 🔴 Il difetto che il censimento ha trovato: **lo specchio della lane**

`vendite.fn_diagnostica_gruppi_fatturabili` è dichiarata, nel proprio manuale,
**«lo specchio di `fn_list_emittibili_lane` — i criteri che questa fotografia
conta uno per uno»**. Esiste apposta: fino al 2026-08-15 quella query viveva in
Python ed era *l'ultima copia dei filtri della lane fuori dal database*.

⛔ **T-4 ha aggiunto un criterio alla lane e non l'ha aggiunto allo specchio.**

⇒ Da ieri, un gruppo **trattenuto** che l'operatore chiede di fatturare:

1. la lane non lo offre ⇒ il giro non lo serve;
2. il backend chiede alla diagnostica **perché**;
3. la diagnostica risponde `n_pronte = 1` e una `terne_pronte` valorizzata —
   cioè **«era pronto»**.

⚠️ È una **diagnosi falsa**, ed è esattamente il difetto che la lane descrive
nel proprio commento a proposito del taglio (*«a valle diventerebbe una diagnosi
FALSA su gruppi che erano solo oltre il taglio»*). Lì è stato evitato con un
errore parlante; qui è rientrato dalla finestra.

⇒ **La prima stesura proponeva qui un contatore `n_trattenute`.** Era un
cerotto: sarebbe stata la **quinta** condizione scritta due volte, e il criterio
successivo sarebbe ricaduto nello stesso buco. ✅ **Superata dalla decisione di
Tid** (§8): la diagnostica non riceve un contatore, riceve la **sede** — conta le
classi che il classificatore le consegna (§8.1).

⭐ Resta **P-8**, il presidio che lega i due: *esisteva uno specchio dichiarato e
niente che verificasse che fosse ancora tale*. Un test che confronta le righe
ammesse dalla lane con quelle contate `PRONTA` dalla diagnostica, su una fixture
costruita, sarebbe diventato rosso il giorno di T-4.

### 9.3 ⭐ La duplicazione vera: **cinque letture della fase di un lotto**

Cercando dove vive «in che stato è questo lotto», i punti sono **cinque**, e
ognuno rifà da capo lo stesso `LEFT JOIN config.stati_doc_fiscale` con la
propria difesa fail-closed:

| Punto | Legge | Difesa |
| --- | --- | --- |
| `script.fn_check_lotto_riportabile_a_draft` | `congela_fiscale` | `COALESCE(…, true)` |
| `script.fn_check_fattura_eliminabile_da_lotto` | `congela_fiscale` (lotto **e** fattura) | `COALESCE(…, true)` |
| `script.fn_check_documento_escludibile_da_giro` | `congela_fiscale` | `COALESCE(…, true)` |
| `script.fn_check_lotto_annullabile` | `codice_interno` (regola su **uno** stato: legittima) | confronto secco |
| `vendite.vw_documenti_trattenuti_da_lotto` | `is_abortito` | `COALESCE(…, false)` |

⭐ **E il precedente è scritto in casa**: il commento di
`fn_check_lotto_riportabile_a_draft` racconta che `NOT IN ('DRAFT','EMESSA')`
erano **otto copie della stessa frase**, e che `congela_fiscale` è nata proprio
per toglierle. ⇒ Il flag ha già ucciso l'elenco di stati; quello che è rimasto
duplicato è **il modo di leggerlo**.

⛔ **E non è duplicazione innocua: è la duplicazione che ha prodotto §6.1.** In
un posto solo, che espone i tre assi accanto e un booleano che si deve
**nominare**, scriverlo implementandolo come «non annullato» è molto più
difficile che farlo di sfuggita dentro una `WHERE`.

**`vw_lotti_fase`** — il lotto **L1** del piano: un lotto, i tre assi grezzi e
**un solo** derivato (`pre_fiscale`), fail-closed una volta sola, adottata da
tutti e cinque i lettori.

✅ **Decisa (D-2, §8.0): si fa, e con tutti e cinque i lettori nello stesso
passo** — è il lotto **L1** del piano. Una sede nuova con **un** lettore e
quattro copie ancora in giro sarebbe un oggetto che *sembra* la sede e non lo è,
cioè peggio di nessuna sede.

⭐ **E la prova che l'adozione è a comportamento invariato è già scritta**: i
pgTAP dei quattro `fn_check_*` devono restare verdi **senza essere toccati**.

### 9.4 ⛔ Ciò che invece **non** si estrae, e il perché

I tre consumatori (lane, pull, vista di riga) ripetono la stessa forma:

```text
NOT EXISTS (SELECT 1 FROM vendite.vw_documenti_trattenuti_da_lotto t
             WHERE t.gruppo_key            = <chiave della riga>
               AND t.lotto_competenza_mese >= <competenza della riga>
               AND t.lotto_id IS DISTINCT FROM <lotto corrente>)
```

Sembra chiedere una funzione `fn_documento_trattenuto(...)`. ⛔ **Non la si
scrive**, e la ragione è di **piano di esecuzione**: una funzione — scalare o
tabellare — dentro un `NOT EXISTS` diventa opaca al pianificatore, che non può
più spingere il filtro dentro né trasformarlo in **semi-join**. La verrebbe
valutata **una volta per riga candidata**, e la lane gira su tutte le righe di
competenza di un perimetro. ⚠️ Il costo per riga di una funzione su questa
catena è già dichiarato, e misurato, in `vw_dash_competenza_attivita`.

⭐ **La sede è già la vista**: il predicato *è* dentro di lei, e ciò che si
ripete sono le **condizioni di aggancio** — che dipendono dalla riga chiamante e
in una funzione dovrebbero comunque diventare parametri. ⇒ Si tengono in chiaro,
si **dichiarano** nel commento di ciascun consumatore, e le presidia `P-2` e
`P-5`: due delle tre condizioni sono proprio quelle che un consumatore si
dimentica.

⚠️ **Se un quarto consumatore arriva, la decisione si riapre.** Con tre siti la
regola del 2 è già superata in numero: qui non si estrae per un motivo tecnico
dichiarato, non perché siano pochi — ed è la differenza che va scritta, o al
prossimo giro qualcuno «finisce il lavoro».

---

*Brief di lavoro — sezioni §1-§4 del team backend, §5 in poi del team DB.*
