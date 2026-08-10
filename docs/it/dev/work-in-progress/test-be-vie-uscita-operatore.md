# Test in-app — le vie d'uscita per l'operatore

> ## ✅ GIRO ESEGUITO — 10/10, 2026-08-10 (Tid, in app)
>
> I dieci casi passano tutti. Il valore del giro però non sta lì: ha fatto
> emergere **due difetti che nessuno dei dieci cercava** — §3, **A1** e **A2** —
> entrambi sulla stessa lacuna, cioè che la logica delle capability conosce solo
> il percorso felice e non modella gli stati **chiusi**.
>
> **Aperto, e per questo il documento resta qui e non in `work-done`:**
>
> 1. **A1 + A2** — brief passato al team DB il 2026-08-10; le stringhe i18n
>    restano a carico del FE, in attesa dei nomi chiave.
> 2. ✅ **La decisione del §5 è PRESA** (Tid, 2026-08-10): *«la nota spiega lo
>    stato chiuso»*, quindi compare anche accanto a un pulsante vivo. Passata al
>    team DB insieme ad A1/A2, con i **due effetti collaterali** che la
>    formulazione non copriva — vedi §5.
>
> Quando il team DB rientra su A1, A2 e §5, questo documento va in `work-done`.

> **Cosa si sta provando:** la metà a video di
> [brief-db-vie-uscita-operatore.md](../work-done/brief-db-vie-uscita-operatore.md) +
> [brief-be-fe-vie-uscita-operatore.md](../work-done/brief-be-fe-vie-uscita-operatore.md).
> **Chi prova:** Tid, in app.
> **Preparato da:** BE/FE, 2026-08-05. Documento **vivo**: si spunta e si annota
> mentre si prova.
>
> **La regola che si sta verificando** (R1+R3 del brief DB), ed è l'unica cosa da
> tenere in testa guardando ogni schermata:
>
> > **O la via d'uscita c'è, o c'è scritto perché non c'è.**
>
> Tre esiti possibili per ogni caso: ✅ come atteso · ⚠️ funziona ma non convince
> (decisione di dominio da riguardare) · ❌ non torna (difetto). **Annota anche i
> ⚠️**: la metà del valore di questo giro sta lì.

---

## 0. Prerequisiti — da fare PRIMA, o metà delle prove mente

| #   | Cosa                                                                                  | Perché                                                                                                                                                                                                     | ✔   |
| --- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --- |
| P1  | `sudo systemctl reload zeroerp-gunicorn`                                              | Gunicorn in dev **non ha autoreload**: `error_policies.py` è cambiato e senza reload i 409 nuovi escono come errore generico. Un T4 fallito senza aver fatto questo non è un difetto, è un backend vecchio | ☐   |
| P2  | Frontend aggiornato (`vite build` già fatto il 2026-08-05; se usi il dev server, HMR) | Senza, la nota «nessuna azione» non esiste proprio nel bundle                                                                                                                                              | ☐   |
| P3  | L'operatore con cui entri deve avere **l'emittente fiscale 32** nello scope           | Tutti i documenti qui sotto sono di EF=32. Fuori scope non danno errore: **spariscono** (RLS fail-closed) o rispondono 404. Un «documento non trovato» è quasi sempre questo, non un bug                   | ☐   |
| P4  | Se un drawer è rimasto aperto da prima del reload, **chiudilo e riaprilo**            | Le capability sono lette al caricamento del dettaglio: un drawer aperto mostra lo stato di dieci minuti fa. È anche il meccanismo che T4 sfrutta di proposito                                              | ☐   |

---

## 1. Elenco da spuntare (sintesi)

| #   | Caso                                                    | Dove                    | ✔ | Esito                                                                   |
| --- | ------------------------------------------------------- | ----------------------- | - | ----------------------------------------------------------------------- |
| T1  | «Annulla» **acceso** su preventivo ACCETTATO            | `PRV0000192`            | X | ✅ OK                                                                    |
| T2  | «Annulla» **acceso** su preventivo EMESSO               | `PRV0000189`            | X | ✅ OK                                                                    |
| T3  | «Annulla ordine» **acceso** su ordine CONFERMATO        | `ORD0000610`            | X | ✅ OK                                                                    |
| T4  | «Annulla» **spento col motivo** (tooltip)               | `PRV0000144`            | X | ✅ OK                                                                    |
| T5  | Nota «nessuna azione» — ordine EVASO                    | `ORD0005175`            | X | ✅ OK                                                                    |
| T6  | Nota «nessuna azione» — DDT CONSEGNATO                  | `DDT0000338`            | X | ✅ OK — testo conforme al seed (`consegnato_usa_reso`)                   |
| T7  | Nota «nessuna azione» — DDT RESO                        | `DDT0000062`            | X | ✅ OK — testo conforme al seed (`reso`)                                  |
| T8  | Resa responsive della nota (sidebar / finestra stretta) | uno dei T5–T7           | X | ✅ OK                                                                    |
| T9  | Il 409 col messaggio di dominio (forzatura a due tab)   | `PRV0000192`            | X | ✅ OK — ha parlato un guard **diverso** da quello atteso, vedi dettaglio |
| T10 | L'annullamento **esegue davvero** (stato → ANNULLATO)   | un preventivo di scarto | X | ✅ OK — ma la coda del caso ha prodotto **A2**                           |

**Esito del giro: 10/10 ✅.** Non è però un giro senza risultato: ha fatto emergere
**due anomalie** (§3, A1 e A2) che nessuno dei dieci casi cercava, ed è
esattamente quello per cui il documento chiedeva di annotare anche i ⚠️.

---

## 2. I casi, in dettaglio

### T1 ✅ — «Annulla» acceso su preventivo ACCETTATO

**È il verbo che prima non esisteva**: un preventivo ACCETTATO offriva una sola
azione (`push_commessa`) e nient'altro — non si annullava, non tornava indietro.

1. Vendite → Preventivi → cerca **`PRV0000192`** (id 1816, cliente `BAC/0000042`)
2. Click sulla riga → si apre il drawer

**Cosa devi vedere:** nella barra azioni sotto l'intestazione, un pulsante
**Annulla** rosso *outlined*, accanto alle azioni già note (Genera ordine /
Smistamento). Non grigio, non assente.

Alternativa equivalente: `PRV0000191` (id 1271).

> **Esito ✅** — Annulla presente e acceso.

### T2 ✅ — «Annulla» acceso su preventivo EMESSO

Stessa cosa dall'altro stato ripristinato. Cerca **`PRV0000189`** (id 535).
Qui l'Annulla convive con Accetta / Rifiuta / Crea revisione: verifica che
**non abbia spinto le altre fuori** dalla barra o sotto il fold.

> **Esito ✅** — Annulla convive con Accetta / Rifiuta / Crea revisione senza spingerle fuori dalla barra.

### T3 ✅ — «Annulla ordine» acceso su ordine CONFERMATO

Vendite → Ordini → **`ORD0000610`** (id 633). Deve comparire **Annulla ordine**
accanto a «Invia a commessa».

⚠️ Nota: è **l'unico** ordine CONFERMATO annullabile in tutto il database
(vedi §4). Se lo annulli in T10, questo caso non è più ripetibile.

> **Esito ✅** — «Annulla ordine» presente accanto a «Invia a commessa».

### T4 ✅ — Il bottone spento col motivo

**È la novità vera del cantiere**: fino a ieri qui il bottone era *acceso* e il
rifiuto arrivava dopo il click.

Vendite → Preventivi → **`PRV0000144`** (id 302, ACCETTATO, `BAC/0000053`).
Equivalenti: `PRV0000143` (301), `PRV0000141` (299), `PRV0000140` (298).

**Cosa devi vedere:**

- «Annulla» **c'è**, ed è **grigio** — non nascosto (decisione presa: spento con
  motivo è meglio di assente);
- passandoci sopra il mouse, il tooltip dice:
  > *Il preventivo è già stato inviato a fatturazione: annulla prima le attività in commessa.*
- il click non fa nulla.

**Segnale di difetto da riconoscere:** se al posto della frase leggi
`vendite.preventivi.azione_reason.gia_in_commessa`, è una chiave i18n non
risolta. Il guard automatico è verde, quindi non dovrebbe succedere — ma se
succede, quello è il testo da copiare nell'annotazione.

> **Esito ✅** — bottone grigio col tooltip di dominio. Nessuna chiave i18n grezza.

### T5 ✅ — La nota sull'ordine EVASO

Vendite → Ordini → **`ORD0005175`** (id 5388). Equivalente: `ORD0005174` (5387).

**Cosa devi vedere:** nessun pulsante di stato, e al loro posto una riga muted
con icona ℹ️:

> *L'ordine è evaso: lo stato si ricalcola dai DDT, non si imposta a mano.*

**Perché conta:** prima qui c'era **il vuoto** — nessun pulsante e nessuna
spiegazione, indistinguibile da un caricamento fallito.

> **Esito ✅** — la nota compare al posto dei pulsanti.

### T6 ✅ — La nota sul DDT CONSEGNATO

Vendite → DDT → **`DDT0000338`** (id 518). Equivalente: `DDT0000337` (517).

> *La merce è consegnata: per farla rientrare si registra un reso, non si annulla il DDT.*

Questo è il caso in cui la nota non si limita a spiegare: **indica la strada**
(il reso). Valuta se il testo ti sembra abbastanza esplicito per un operatore
che non conosce il modello.

> **Esito ✅** — a video: *«La merce è consegnata: per farla rientrare si registra
> un reso, non si annulla il DDT.»* Corrisponde alla chiave
> `vendite.ddt.stato_info.consegnato_usa_reso`, seminata in `stati_doc_ddt.csv`
> (id 5). Testo giudicato **sufficientemente esplicito**: indica la strada, non
> si limita a spiegare.

### T7 ✅ — La nota sul DDT RESO

Vendite → DDT → **`DDT0000062`** (id 140). Equivalente: `DDT0000061` (139).

> *Questo DDT è rientrato con un reso: lo stato segue il reso da solo.*

> **Esito ✅** — a video: *«Questo DDT è rientrato con un reso: lo stato segue il
> reso da solo.»* Corrisponde a `vendite.ddt.stato_info.reso` (id 7).

### T8 ✅ — Resa responsive della nota

Su uno qualsiasi fra T5–T7:

- **apri e chiudi la sidebar**: la nota deve andare a capo da sola, **senza**
  stringere o mandare a capo i pulsanti accanto (è `flex: 1 1 12rem`);
- **restringi la finestra sotto 1024px** (o prova su tablet): le azioni
  collassano nel kebab `⋮` — la nota deve restare **leggibile e in chiaro**, non
  finire dentro il menu;
- controlla che il tono sia quello di una **risposta**, non di un allarme (grigio
  muted, non un banner colorato). Se ti sembra troppo poco visibile, è un ⚠️ da
  annotare: è una scelta, non un vincolo.

> **Esito ✅** — la nota va a capo da sola e resta leggibile in chiaro, fuori dal kebab.

### T9 ✅ — Il 409 col messaggio di dominio (forzatura)

Dopo T4 il messaggio d'errore **non è più raggiungibile dalla UI normale**: il
bottone è spento prima. Resta la difesa in profondità, e per esercitarla serve
una corsa deliberata:

1. apri **`PRV0000192`** (annullabile) e **lascia il drawer aperto**;
2. in un'altra tab, manda lo **stesso** preventivo in commessa (Smistamento);
3. torna alla prima tab — che ha capability stantie — e clicca **Annulla**.

**Cosa devi vedere:** un banner d'errore con il messaggio di dominio
(*«Il preventivo è già stato inviato a fatturazione…»* o *«Righe già fatturate in
commessa…»*).

**Cosa NON devi vedere:** *«Errore durante l'operazione database»* o *«Errore di
validazione»*. Se leggi una di queste due, il sospetto numero uno è **P1 non
fatto** (backend non ricaricato) — verificalo prima di segnalarlo come difetto.

> **Esito ✅ — con una precisazione che vale la pena tenere.**
>
> A video: *«Transizione del preventivo non ammessa: da EVASO a ANNULLATO.»*
>
> È un messaggio **di dominio**, che è ciò che il caso doveva provare: nessuna
> traccia di «Errore durante l'operazione database» o «Errore di validazione».
> Ha però parlato un guard **diverso** da quello previsto qui sopra: lo
> smistamento ha portato il preventivo da ACCETTATO a **EVASO**, quindi scatta
> per primo il guard della matrice di transizione (EVASO→ANNULLATO non esiste),
> non quello «già in commessa». Entrambi sono di dominio: ha risposto quello che
> arriva prima. **Non è un difetto**, ma l'attesa scritta nel caso era imprecisa.

### T10 ✅ — L'annullamento esegue davvero

Finora abbiamo guardato i bottoni. Qui si preme.

⚠️ **ANNULLATO è terminale**: dalla matrice non esiste transizione in uscita. Il
documento che scegli è **bruciato**. Candidato di scarto suggerito:
**`PRV0000188`** (id 534, EMESSO, `BAC/0000053`) — non il più recente, non uno di
quelli già in commessa.

1. apri il preventivo, click **Annulla**
2. deve comparire il **dialog di conferma** (`requires_confirm` è nel seed)
3. conferma

**Cosa devi vedere:** toast di successo, il drawer si ricarica, il **Tag di stato
diventa ANNULLATO**, e la barra azioni si aggiorna da sola.

**Da guardare subito dopo, ed è la prova più interessante del giro:** dallo stato
ANNULLATO **che cosa offre il drawer?** Se la barra resta vuota e muta, abbiamo
appena creato un settimo stato senza uscita e senza spiegazione — cioè
esattamente il difetto che questo cantiere è nato per chiudere, su uno stato che
prima nessuno raggiungeva. **Annotalo: è il primo posto dove mi aspetto che
qualcosa non torni.**

> **Esito ✅ per l'annullamento** — toast, ricarica del drawer, Tag → ANNULLATO,
> barra azioni aggiornata da sola.
>
> ⚠️ **La domanda in coda al caso ha trovato la risposta che si temeva**: dallo
> stato ANNULLATO il drawer non offre nulla **e non spiega perché**. Registrata
> come **A2**. Il caso previsto che «è il primo posto dove mi aspetto che
> qualcosa non torni» — e infatti.

---

## 3. Cosa non torna — da compilare mentre provi

Per ogni anomalia, questi quattro dati mi bastano quasi sempre per capire senza
farti riprovare:

| Dato                                   | Dove prenderlo                                                                           |
| -------------------------------------- | ---------------------------------------------------------------------------------------- |
| **Documento**                          | numero + id (es. `PRV0000144` / 302)                                                     |
| **Cosa ti aspettavi / cosa hai visto** | una riga per parte                                                                       |
| **`request_id`**                       | è nel banner d'errore, o nella risposta API (`meta.request_id`) — mi porta dritto al log |
| **Codice errore o chiave grezza**      | il `code` del banner (es. `E_DATABASE`), oppure la chiave i18n se la vedi a video        |

### Registro

| #  | Caso | Documento | Cosa si è visto | Tipo |
| -- | ---- | --------- | --------------- | ---- |
| A1 | coda di T9 | `PRV0000192` (1816), ora EVASO | Due motivi che promettono un passo **già avvenuto** | ❌ |
| A2 | coda di T10 | qualunque preventivo chiuso | Stato chiuso **senza spiegazione**: barra vuota e muta | ❌ |

### A1 — «sarà disponibile dopo l'accettazione» su un preventivo già accettato

Su `PRV0000192`, portato in **EVASO** dallo smistamento di T9, il drawer mostra:

> *«L'integrazione con la commessa sarà disponibile dopo l'accettazione del preventivo.»*
> *«La generazione dell'ordine sarà disponibile dopo l'accettazione del preventivo.»*

Il preventivo **è già stato accettato** — è evaso proprio per quello. La causa
sono le due condizioni gemelle in `script.fn_available_actions_preventivo`:

```sql
ELSIF v_stato_cod <> 'ACCETTATO' THEN
    v_push_reason_key   := '...push_commessa_reason.non_accettato'
    v_ordine_reason_key := '...genera_ordine_reason.non_accettato'
```

`<> 'ACCETTATO'` mette nello stesso ramo due situazioni **opposte**: prima
dell'accettazione (DRAFT, EMESSO) la frase è un'istruzione corretta; dopo o fuori
(EVASO, ANNULLATO, RIFIUTATO, SCADUTO) è **falsa** — promette un passo già
avvenuto, o che non avverrà mai. L'operatore conclude che gli manchi qualcosa da
fare.

⚠️ **Il pulsante Smistamento cliccabile su EVASO non è parte dell'anomalia**: è
voluto (`showSmistamento` include EVASO, «EVASO = consuntivo») e la dialog blocca
le azioni. Serve a guardare com'è andato lo smistamento, non ad agire.

### A2 — gli stati chiusi dei preventivi non spiegano nulla

`config.stati_doc_preventivi` ha `meta = {}` su **tutti e quattro** gli stati
chiusi: `RIFIUTATO` (5), `SCADUTO` (7), `ANNULLATO` (9), `EVASO` (10). La
funzione **legge già** `sdp.meta->>'nessuna_azione_key'` e la espone quando
nessuna azione è abilitata: manca solo il **dato**, non il codice.

Conseguenza: ANNULLATO — lo stato che *questo stesso cantiere* ha appena reso
raggiungibile — mostra barra vuota e nessuna spiegazione. È esattamente il
difetto che il cantiere è nato per chiudere, sullo stato che prima nessuno
raggiungeva.

⚠️ Verificato nella matrice `transizioni_stati_preventivi`: quei quattro stati
**non hanno alcuna transizione in uscita**. Le note non devono quindi suggerire
ripartenze (revisioni, riaperture) senza conferma che siano praticabili per
altra via — altrimenti si ripete A1, cioè si promette un'azione inesistente.

**Stessa lacuna, altri due domini**: `stati_doc_ordini` → ANNULLATO (6) e
FATTURATO (7); `stati_doc_ddt` → ANNULLATO (6). Gli altri stati chiusi di ordini
e DDT la nota ce l'hanno, e T5–T7 lo confermano in app.

### Stato: brief inviato al team DB

Entrambe passate al team DB il **2026-08-10** (una riga di seed per A2, un ramo
`ELSIF` su `fase = 'CHIUSO'` per A1). Le stringhe i18n nuove
(`push_commessa_reason.stato_chiuso`, `genera_ordine_reason.stato_chiuso` e le
note degli stati chiusi) sono lato FE, in attesa dei nomi chiave definitivi.

### Sospetti tipici, per non perdere tempo

| Sintomo                                                         | Prima causa da escludere                                                                       |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Errore generico invece del messaggio di dominio                 | **P1**: backend non ricaricato                                                                 |
| La nota «nessuna azione» non compare da nessuna parte           | **P2**: frontend non aggiornato                                                                |
| Il documento non si trova / 404 aprendolo                       | **P3**: emittente fuori scope (RLS), non un bug                                                |
| Il bottone è acceso quando dovrebbe essere spento (o viceversa) | **P4**: drawer aperto da prima, capability stantie. Chiudi e riapri                            |
| Vedi una chiave (`vendite.…`) al posto del testo                | Chiave i18n mancante nei locales — copiala pari pari                                           |
| Il testo c'è ma è sbagliato/ambiguo                             | **Non è un difetto tecnico**: è un dato (`meta` dello stato). Si cambia il seed, non il codice |

---

## 4. Cosa NON è provabile oggi, e non è un difetto

Scritto qui perché «non l'ho trovato» non diventi una segnalazione.

| Caso                                                                        | Perché                                                                                                                                                                                                                                                                                                |
| --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Ordine con annullamento bloccato** (bottone spento + motivo, lato ordini) | Nel database **non esiste un solo ordine** in questa condizione: il ramo `reasons` dell'ordine non è mai passato per il video. È lo stesso codice del preventivo (che T4 esercita), ma resta non osservato. Se crei un ordine CONFERMATO con un DDT collegato, quello è il caso da guardare per primo |
| **Nota su ordine PARZIALMENTE_EVASO**                                       | ⚠️ **SUPERATO dalla decisione del §5 (2026-08-10).** Era vero finché la nota rispondeva alla lista vuota: la chiave è seminata ma non compariva mai, perché quegli ordini hanno sempre azioni vive. Con «la nota spiega lo stato» comparirà **su ogni** ordine parzialmente evaso — ed è un effetto su uno stato **aperto** che la decisione non copriva: segnalato al team DB |

## 5. La decisione lasciata aperta — guardala mentre provi

Il team DB ha dichiarato che **5 ordini EVASO su 32 non ricevono la nota**,
perché hanno ancora «Invia a fatturazione» abilitata: la regola è «la nota
risponde alla lista vuota», e con un bottone vivo la lista vuota non c'è.

Se durante T5 ti capita un ordine EVASO **con** un pulsante acceso e **senza**
spiegazione dello stato, la domanda è:

> «Evaso» è un'informazione che serve all'operatore **anche** quando c'è ancora
> qualcosa da fare, o solo quando non c'è più niente?

Lato frontend **non c'è alcun vincolo**: la nota si affianca già alle azioni vive
(è una riga in coda alla barra, non un rimpiazzo dei pulsanti). Se decidi che la
spiegazione accompagna sempre lo stato chiuso, costa **una riga in tre funzioni
DB e zero righe di frontend**. È una scelta di dominio, ed è tua.

> ## ✅ **DECISIONE PRESA — Tid, 2026-08-10**
>
> > **«La nota spiega lo stato chiuso»**: comparirebbe sempre su un ordine evaso,
> > anche accanto al pulsante ancora vivo. L'operatore leggerebbe «è evaso, lo
> > stato si ricalcola dai DDT» e avrebbe comunque il suo bottone.
>
> Cioè: la nota **non è più la risposta a uno schermo vuoto**, è l'informazione di
> stato. Il presupposto che la faceva sparire — `v_nessuna_azione`, il «nessun
> bottone vivo» — decade.
>
> **Conseguenza tecnica**: nelle tre funzioni `fn_available_actions_*` (preventivo,
> ordine, ddt) il campo si emette sempre che lo stato abbia una nota seminata:
>
> ```sql
> -- da
> 'nessuna_azione_key', CASE WHEN v_nessuna_azione THEN v_nessuna_key END
> -- a
> 'nessuna_azione_key', v_nessuna_key
> ```
>
> e il calcolo di `v_nessuna_azione` diventa codice morto. Zero righe di frontend:
> `DrawerActionsBar` rende già la nota accanto alle azioni vive.
>
> ⚠️ **Due effetti che la decisione, come formulata, non copriva** — passati al
> team DB insieme alla decisione:
>
> 1. **`ORDINI / PARZIALMENTE_EVASO` si accende.** Ha già la nota seminata
>    (*«Evasione in corso: lo stato si ricalcola a ogni DDT.»*) ma **non è uno
>    stato chiuso** (`fase = IN_CORSO`), e finora non compariva mai proprio perché
>    quegli ordini hanno sempre azioni vive — è il caso registrato in §4. Con la
>    nuova regola comparirà su **ogni** ordine parzialmente evaso. Sembra un
>    guadagno (dice che lo stato si muove da sé), ma è un cambiamento su uno stato
>    **aperto**, non deciso qui.
> 2. **Il nome del campo diventa falso.** `nessuna_azione_key` si mostrerà proprio
>    quando le azioni **ci sono**. Il vocabolario giusto il frontend ce l'ha già:
>    le chiavi i18n stanno sotto `vendite.<dominio>.stato_info.*`. Proposta di
>    rinomina a `stato_info_key` — 3 funzioni DB + 8 drawer FE, il backend non lo
>    tocca (passa il blob invariato).

---

## 6. Rigenerare l'elenco dei documenti

Gli id/numeri qui sopra sono una **fotografia del 2026-08-05**: se nel frattempo
qualcuno annulla o fattura, cambiano. Per rifare la lista (dal server backend,
canale di sistema — le tabelle hanno RLS e senza contesto si legge zero e si
conclude il falso):

```sql
-- preventivi con l'azione annulla, divisi fra accesi e spenti
SELECT p.id, p.numero, s.codice_interno,
       a->>'enabled' AS acceso,
       (SELECT string_agg(r->>'codice', ',')
          FROM jsonb_array_elements(COALESCE(a->'reasons','[]'::jsonb)) r) AS motivi
  FROM vendite.preventivi p
  JOIN config.stati_doc_preventivi s ON s.id = p.stato_doc_preventivo_id
  CROSS JOIN LATERAL jsonb_array_elements(
        script.fn_available_actions_preventivo(p.id)->'available_actions') a
 WHERE a->>'key' = 'annulla'
 ORDER BY acceso DESC, p.id DESC;

-- documenti in stato chiuso che espongono la nota (ordini e DDT)
SELECT 'ORD' AS tipo, o.id, o.numero, x.nota
  FROM vendite.ordini o
  CROSS JOIN LATERAL (SELECT script.fn_available_actions_ordine(o.id)
                             ->>'nessuna_azione_key' AS nota) x
 WHERE x.nota IS NOT NULL
UNION ALL
SELECT 'DDT', d.id, d.numero, x.nota
  FROM vendite.ddt d
  CROSS JOIN LATERAL (SELECT script.fn_available_actions_ddt(d.id)
                             ->>'nessuna_azione_key' AS nota) x
 WHERE x.nota IS NOT NULL
 ORDER BY 1, 2 DESC;
```

> ⚠️ **Non usare `blob ? 'nessuna_azione_key'`** per filtrare. La chiave è
> **sempre presente** nel blob: quando non si applica il valore è `null`, non è la
> chiave a mancare. Il test di presenza risponde quindi vero per **tutti** i
> documenti (118 invece di 36, misurato). Va guardato il **valore**, non la
> chiave. Nessuna conseguenza lato frontend — `null` è falsy e la nota non viene
> resa — ma è una trappola per chiunque scriva una query o un pgTAP su questo
> campo.
