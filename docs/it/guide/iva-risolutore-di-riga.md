# Guida — Il risolutore IVA di riga

> **Ultimo aggiornamento**: 4 ottobre 2026
>
> **Destinatari**: analisti funzionali, operatori commerciali, sviluppatori backend/frontend, DBA.
>
> **Vedi anche** — funzioni DB:
>
> * [vendite.fn_resolve_iva_riga](/dbzero/vendite/funzioni/fn_resolve_iva_riga) — **il guscio: si chiama questo**
> * [vendite.fn_resolve_iva_riga_it](/dbzero/vendite/funzioni/fn_resolve_iva_riga_it) — la regola italiana
> * [vendite.fn_get_tipo_utenza_fornitura](/dbzero/vendite/funzioni/fn_get_tipo_utenza_fornitura) — l'uso della fornitura, secondo gradino dello stadio A
> * [anagrafiche.fn_consuma_plafond_titolo_iva_righe](/dbzero/anagrafiche/funzioni/fn_consuma_plafond_titolo_iva_righe) — chi consuma il tetto, sul netto della fattura (il risolutore **non** lo fa)
>
> **Vedi anche** — tabelle:
>
> * [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/manual/soggetti_titoli_iva) — i titoli del cliente
> * [anagrafiche.soggetti_titoli_iva_ambiti](/dbzero/anagrafiche/manual/soggetti_titoli_iva_ambiti) — per cosa vale un titolo
> * [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti) — il registro del plafond consumato
> * [config.iva](/dbzero/config/tabelle/iva) · [config.tipi_utenze](/dbzero/config/tabelle/tipi_utenze) · [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
>
> **Vedi anche** — API e frontend:
>
> * [API iva_resolve](/backend/vendite/manual/api_iva_resolve) — l'anteprima esposta ai form
>
> **Vedi anche** — guide correlate:
>
> * [Gestione preventivi](/guide/gestione-preventivi) · [Gestione ordini](/guide/gestione-ordini) · [Gestione DDT](/guide/gestione-ddt) · [Fatturazione](/guide/fatturazione) — i documenti che lo interrogano
> * [Numerazione dei documenti e codici](/guide/numerazione-documenti-e-codici) — l'altro meccanismo condiviso da tutta la famiglia vendite

---

## 1. Il problema che risolve

Ogni riga di documento porta un codice IVA. Sembra un dato che si copia
dall'articolo, e la tentazione è di farlo: il form del preventivo legge
`catalogo.articoli.iva_id`, quello dell'ordine anche, quello del DDT anche, e la
pipeline di fatturazione se lo ricava per conto suo.

**Quattro risposte alla stessa domanda**, che coincidono *per costruzione*:
guardano la stessa colonna. Il difetto non è visibile finché nessuna delle quattro
impara qualcosa che le altre non sanno — e il giorno che una lo impara, divergono
su documenti già emessi.

E c'è da imparare parecchio. L'aliquota di una riga non dipende **solo**
dall'articolo:

| Cosa può cambiarla           | Esempio                                                                                                  |
| ---------------------------- | -------------------------------------------------------------------------------------------------------- |
| l'**uso** della merce        | il gas per uso industriale non ha l'aliquota del gas per uso domestico                                   |
| un **titolo** del cliente    | un esportatore abituale con dichiarazione d'intento non paga l'IVA su ciò che quella dichiarazione copre |
| il **limite** di quel titolo | la dichiarazione ha un plafond: finito quello, si torna all'ordinaria                                    |
| l'**ambito** di quel titolo  | un'agevolazione per disabilità copre certi prodotti, non l'intero listino                                |

⭐ **Un auto-fill dall'articolo non sa niente di tutto questo.** Su un esportatore
abituale propone l'aliquota piena, e nessuno lo segnala: non è un errore che il
sistema può accorgersi di avere.

**La domanda ha una sede sola**: `vendite.fn_resolve_iva_riga`. Non è una regola
della fattura, né dell'ordine, né del DDT — è una funzione che tutti i documenti
interrogano e nessuno riscrive.

> ⛔ **La regola che ne discende, e vale per chi scrive codice:** *mai leggere
> `catalogo.articoli.iva_id` in un service di dominio o in un form.* È il gemello
> esatto della regola del pricing («mai leggere `listini_righe.prezzo`»), e nasce
> dallo stesso difetto.

---

## 2. Due stadi, e vanno letti in ordine

### Stadio A — quale aliquota compete alla MERCE

1. l'**articolo**, se ha un'opinione (`catalogo.articoli.iva_id`);
2. altrimenti l'**uso della fornitura** (`config.tipi_utenze.iva_id`), raggiunto
   attraverso il contratto attivo;
3. altrimenti: *nessuno sa dirlo* — la riga esce con `origine = 'ASSENTE'`.

> ⚠️ **L'ordine non è invertibile, e il motivo è preciso.** L'articolo può dire
> «non ho un'opinione»: la sua colonna è nullabile, e il vuoto **significa**
> qualcosa. L'uso della fornitura **non sa dirlo**: applicato per primo si
> prenderebbe anche cauzioni, spese e servizi, che con la fornitura non c'entrano
> niente.

### Stadio B — un TITOLO del cliente che la sostituisce

Se il cliente ha un titolo valido **su quella riga**, il codice del titolo prende
il posto di quello dello stadio A.

⭐ **«Su quella riga», non «su quel cliente»** — ed è la sostanza di tutto il
meccanismo, non una precisazione. Vedi il capitolo 3.

> ⭐ **Perché l'ordine è questo e non il contrario.** La merce e il suo uso
> decidono l'aliquota **ordinaria**; il cliente non entra *mai* in quella domanda.
> Può soltanto **sostituire** il risultato, e solo mostrando una carta.

---

## 3. Un titolo non è un flag: è un documento

`anagrafiche.clienti.iva_id` — una colonna che prometteva di dire «questo cliente
ha un'IVA sua» — **non esiste, e non è sostituita**: spostarla sul soggetto
riprodurrebbe lo stesso difetto un piano più su — *un valore che vince su tutto
perché nessuno gli ha detto dove fermarsi*.

Al suo posto c'è il **titolo**: una dichiarazione d'intento, una dichiarazione di
uso industriale del gas, un'agevolazione per disabilità, la qualifica di
cooperativa sociale. Ha una prova, una data di inizio e una di fine, dice **a chi**
è stato presentato e dice **per cosa vale**. Registrato una volta, da quel momento
vale da solo su tutti i documenti finché è valido — nessuno lo digita più.

### 3.1 L'ambito: «vale per tutto» oppure «vale per queste voci»

L'ambito è **dichiarato**, mai dedotto da una colonna vuota:

| valore      | significato                                                        |
| ----------- | ------------------------------------------------------------------ |
| `TUTTO`     | il titolo copre ogni riga di documento                             |
| `RISTRETTO` | copre solo ciò che dicono le righe di `soggetti_titoli_iva_ambiti` |

Un titolo ristretto elenca **articoli** oppure **categorie di merce** (gruppo
voce, tipo voce). Un documento di dieci righe con un titolo ristretto a due
articoli produce **due righe agevolate e otto ordinarie**.

> ⛔ **Un titolo `RISTRETTO` senza righe figlie non copre niente, ed è voluto.**
> Il caso si costruisce per forza in due passaggi — prima il titolo, poi il suo
> ambito — quindi un vincolo lo rifiuterebbe a metà strada. Il risolutore lo legge
> come «nessun articolo nell'ambito» e lascia l'aliquota ordinaria: è la direzione
> sicura.

### 3.2 Quando i titoli sono più di uno

Vince **il più specifico**: articolo → categoria di merce → tutto. È la stessa
cascata degli indirizzi.

> ⛔ **A parità di specificità la funzione SOLLEVA.** Non sceglie il più recente,
> non prende il primo. Se due titoli hanno lo stesso diritto di applicarsi alla
> stessa riga non c'è niente da scegliere: è un difetto della **registrazione**, e
> va corretto da chi l'ha fatta. Un'ambiguità risolta sull'ordine degli
> identificativi darebbe una fattura diversa a ogni ricalcolo, e nessuno saprebbe
> mai che c'era una scelta da fare.

### 3.3 Il titolo ha due proprietari, e servono entrambi

Il titolo **appartiene al soggetto** — è lui l'esportatore abituale, non una sua
fornitura: un cliente con tre forniture ha **una** dichiarazione, non tre.

⚠️ Ma una dichiarazione d'intento si **presenta a un fornitore preciso**, con un
protocollo suo e un importo suo. Lo stesso cliente che compra da due società
emittenti presenta **due dichiarazioni**, ognuna col suo plafond. Senza la colonna
dell'emittente i due plafond si consumerebbero da un contatore solo — e non
darebbe **nessun errore**: si vedrebbe solo su un plafond esaurito prima del
dovuto, cioè su precisamente il numero che l'Agenzia delle Entrate verifica.

> 🔴 **Ne discende una cosa che il backend deve sapere.** La tabella dei titoli ha
> la *row security*: senza contesto emittente, il risolutore legge **zero titoli**
> e risponde con l'aliquota ordinaria **senza sollevare**. Non è una lista più
> corta: è un'imposta applicata dove non andava, su un documento che nessuno
> segnalerà. Per questo l'emittente è **obbligatorio** in tutti i punti di chiamata
> applicativi (capitolo 6).

---

## 4. Il plafond, e perché una riga si può spezzare

Solo alcuni titoli — la dichiarazione d'intento — hanno un **tetto di importo**. Il
tetto si consuma all'emissione della fattura, ed è lì che una riga si può spezzare
in due: la parte coperta dal titolo, col suo codice, e il resto con l'aliquota
ordinaria dello stadio A.

Il lavoro è diviso in due, e conviene tenerlo a mente:

| Chi | Che domanda | Che risposta |
| --- | --- | --- |
| il **risolutore**, nella domanda di **consumo** | quale titolo vale su questa riga, e quali sono i due trattamenti? | due righe, **prima il titolo e poi l'ordinario**, senza guardare quanto plafond resta. L'ordine è parte del contratto |
| la **madre del consumo** ([fn_consuma_plafond_titolo_iva_righe](/dbzero/anagrafiche/funzioni/fn_consuma_plafond_titolo_iva_righe)) | quanto copre il titolo, riga per riga? | la quota coperta di ogni riga, sul **netto** della fattura, e il movimento nel registro |

> ⚠️ La parte ordinaria può uscire con `origine = 'ASSENTE'`, ed è corretto: il
> titolo copre un pezzo, e sul resto nessuno sa dire l'aliquota. Sarà il cancello
> all'emissione a fermarla.
>
> ⛔ **Il risolutore NON consuma il plafond**, e non dice quanto il titolo copre: è
> in sola lettura. Il consumo è un atto contabile, e il registro dei movimenti è
> **solo aggiunte**: una forzatura sbagliata si annulla con un contro-movimento,
> non cancellando la riga.

### ⭐ Il plafond si consuma sul NETTO della fattura

Le righe positive consumano, le righe negative — uno sconto, un componente di kit
negativo — **restituiscono**. Una fattura non consuma più della capienza e non
restituisce più di quanto essa stessa consuma.

Esempio: plafond residuo 500, merce 1000 e uno sconto −100, tutto sotto il titolo.
Netto 900, coperti 500: la merce va al titolo per 600 e all'ordinaria per 400, lo
sconto va al titolo per intero. Nel registro: +600 e −100, cioè 500 consumati.

* Le righe si coprono **nell'ordine di stampa**: a plafond quasi esaurito la prima
  per intero, poi una spezzata, poi le altre all'ordinaria.
* Una riga negativa si copre fino a quanto valgono le positive della stessa
  fattura. Restituire plafond consumato da un **altro** documento è il mestiere
  della nota di credito.
* Per questo il risolutore, nel consumo, non guarda il residuo: una riga negativa
  più in basso può restituire capienza a quelle prima, e solo chi vede tutta la
  fattura lo sa.

### ⭐ Un kit si spezza come un'unità sola

In fattura i componenti di un kit non si spezzano uno per uno: il kit è la cosa
venduta, e si divide **tutto insieme**, con la stessa frazione per ogni componente.

* Il titolo si giudica sull'**articolo padre** del kit: se il padre rientra
  nell'ambito del titolo lo seguono tutti i componenti, altrimenti nessuno.
* La quota coperta si calcola sul netto del kit, la somma dei componenti (anche
  quelli negativi).
* Ogni componente va al titolo per quella frazione e all'aliquota ordinaria per il
  resto, e così il numero di kit: un kit da 3 coperto per il 40% esce in fattura
  come **due righe di kit**, «1,2» al titolo e «1,8» all'ordinaria, ciascuna con i
  suoi componenti.
* Un componente a importo zero (un omaggio nel kit) non consuma plafond, ma si
  divide lo stesso: altrimenti le due righe del kit non direbbero più quanti kit
  sono. Un kit che in tutto vale zero è coperto per intero: non consuma niente.

### ⭐ Sui documenti la spezzatura non si fa

Su preventivo, ordine e DDT il titolo si applica **a tutta la riga finché c'è
capienza**: il documento porta un'annotazione che avvisa che il conteggio
effettivo si stabilisce all'emissione della fattura, ed è **lì** che il plafond si
consuma davvero.

> ⭐ **Il modo solido di tenere quella regola non è ricordarsela: è non dare al
> client il parametro con cui romperla.** L'endpoint di anteprima chiede sempre
> l'**anteprima** e non accetta la domanda di consumo — quindi risponde con una
> riga sola, e nessun form può inventare una spezzatura.
>
> ⛔ **E il risolutore non prende importi.** Una spezzatura «proiettata» sul plafond
> residuo, riga per riga, era una terza domanda: non serviva più a nessuno e dava
> un numero che il consumo sul netto avrebbe smentito. È stata ritirata, e chi
> passa un importo riceve un errore invece di una risposta che sembra giusta.

---

## 5. Il guscio: una funzione che smista per paese

Le funzioni sono due, e si chiama sempre e solo la prima:

| Funzione                         | Che cosa fa                                                                                         |
| -------------------------------- | --------------------------------------------------------------------------------------------------- |
| `vendite.fn_resolve_iva_riga`    | **il guscio**: guarda il paese delle due parti e passa la domanda all'implementazione di quel paese |
| `vendite.fn_resolve_iva_riga_it` | la regola **italiana**, e solo quella (i due stadi del capitolo 2)                                  |

> ⛔ **`_it` non si chiama direttamente**: scavalcare il guscio significa scrivere
> «Italia» dentro il chiamante, che è esattamente ciò che il guscio esiste per
> evitare.

**Perché un guscio, se il paese implementato è uno solo.** Perché il costo di
aggiungerne un secondo lo decide **la firma**, non la logica. Con una firma che
prende solo `(articolo, data)` si funziona benissimo in Italia e si è obbligati a
toccare **ogni chiamante** il giorno che si aggiunge un paese. Con il paese dentro
la firma, quel giorno nasce una `_xx` accanto e nessun chiamante cambia.

> ⭐ **E il ramo «paese non previsto» solleva.** Il precedente da cui questo schema
> è copiato — il dispatcher nazionale che valida codice fiscale e partita IVA — quel
> ramo non ce l'ha: su un paese non previsto passa in silenzio, cioè non valida
> niente e nessuno lo sa. Qui si è scelto il contrario.

⚠️ **La data è un parametro, mai «oggi».** È la data di effettuazione
dell'operazione: su un documento vecchio deve restare quella di allora.

---

## 6. Che cosa ritorna: un composito, non un'aliquota

| Campo                   | Cosa dice                                                           |
| ----------------------- | ------------------------------------------------------------------- |
| `iva_id`                | il codice IVA da applicare                                          |
| `quota`                 | sempre `NULL`: quanto copre il titolo lo dice la madre del consumo (la colonna resta per non cambiare la firma) |
| `aliquota`              | la percentuale, già risolta per lo stato dell'emittente             |
| `natura_codice`         | la natura dell'operazione (`N1`…`N7`), quando c'è                   |
| `is_reverse_charge`     | se quella natura è un'inversione contabile                          |
| `esigibilita`           | `I` immediata, `D` differita, `S` scissione                         |
| `split_payment`         | se l'imposta la versa il cliente                                    |
| `riferimento_normativo` | la frase da stampare in fattura                                     |
| `origine`               | **chi ha deciso**: `ARTICOLO`, `TIPO_UTENZA`, `TITOLO`, `ASSENTE`   |
| `titolo_iva_id`         | il titolo che ha sostituito l'aliquota, se ce n'è uno               |

> ⭐ **Perché un composito e non il solo numero.** Chi costruisce una riga fiscale
> ha bisogno di tutte queste cose insieme. Se la funzione tornasse l'aliquota, il
> chiamante andrebbe a riprendersi natura, esigibilità e riferimento normativo per
> conto suo — cioè **ricostruirebbe la decisione fuori dalla sua sede**, che è
> esattamente il problema che questa funzione esiste per chiudere.

### 6.1 `origine` è la parte che si legge per prima

Serve a chi guarda una riga e vuole sapere **perché** porta quel codice. A video
diventa la spiegazione sotto il campo — e non è un lusso: la casella IVA sul
documento è **chiusa**, e un numero che non si può cambiare **e** che non viene
spiegato sarebbe la forma peggiore.

`ASSENTE` non è un errore: in bozza una riga senza IVA è legittima, e sarà il
cancello all'emissione a fermarla. Il cancello c'è su ogni documento che ha un
riepilogo IVA: DDT, ordine, preventivo e **fattura**. Sulla fattura scatta entrando
in EMESSA (anche dal giro del lotto) e dice quale riga non ha l'aliquota
(`E_FATTURA_RIGA_IVA_MANCANTE`, da
[script.fn_check_fattura_emettibile](/dbzero/script/funzioni/fn_check_fattura_emettibile));
il riepilogo della bozza, intanto, si calcola lo stesso, con l'aliquota di quella
riga vuota.

⚠️ Il vocabolario di `origine` è **aperto**: le etichette dei valori noti stanno in
`vendite.iva_origine.*`, e un valore nuovo compare a video come **codice grezzo**,
non come etichetta mancante.

⭐ **C'è un quinto valore, e non sta nel catalogo del database: `MANUALE`.** Dice
«l'aliquota è arrivata dal payload, cioè l'ha scelta una persona». Vive solo nel
`meta` della riga, e non può stare a catalogo perché il risolutore non sa che
esiste un operatore. Con la casella IVA chiusa sui tre domini **non è più
raggiungibile** da un documento: la chiave resta però leggibile in `meta`, e vale
la pena saperlo prima di trovarla.

### 6.2 Due campi che sono TRASPORTATI, non usati

`esigibilita` e `split_payment` non entrano nella scelta del codice: la scissione
dei pagamenti non cambia l'aliquota, cambia **chi versa** l'imposta. Escono nel
composito perché chi costruisce la riga vuole un oggetto solo.

> ⚠️ **Quando il soggetto non è noto quei due campi escono `NULL`, insieme.** Non è
> una dimenticanza: senza il cliente il regime di scissione **non è stato
> determinato**, e rispondere «immediata, non scissa» sarebbe un'**affermazione** su
> un documento che potrebbe andare a una Pubblica Amministrazione. «Non lo so» si
> dice, non si tace.

### 6.3 Che cosa si salva sulla riga, e che cosa no

Nel `meta` della riga di documento sopravvivono **due** chiavi su dieci:
`iva_origine` e `iva_titolo_id`.

⭐ Il criterio: si memorizzano i **fatti che nessuno può ricostruire dopo**.
Aliquota, natura e riferimento normativo si **derivano** da `iva_id` — copiarli
creerebbe una frase che invecchia, ed è il motivo per cui `iva_perc` non esiste
sulle righe di fattura.

---

## 7. Chi lo interroga

```text
                       ┌──────────────────────────────────────┐
  form riga (FE)  ───▶ │  POST /api/v1/vendite/iva/resolve/   │  anteprima
                       └──────────────────┬───────────────────┘  (una parte sola)
                                          │
  service di dominio ─────────────────────┤
  (preventivi · ordini · DDT)             ▼
                            vendite.fn_resolve_iva_riga  ──▶  _it  ──▶  titoli
                                          ▲
  pipeline di fatturazione ───────────────┘   (domanda di consumo: titolo e
                                               ordinario; il plafond lo consuma
                                               la madre, sul netto)
```

| Livello  | Chi                                                                            | Nota                                                                                |
| -------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| Database | `fn_resolve_iva_riga`                                                          | la sede della regola                                                                |
| Backend  | `IvaResolverService` (`risolvi`, `risolvi_anteprima`)                          | guard di chiamata, traduzione errori, normalizzazione — **nessuna regola fiscale**  |
| API      | [`POST /api/v1/vendite/iva/resolve/`](/backend/vendite/manual/api_iva_resolve) | anteprima, sola lettura, nessun `Idempotency-Key`                                   |
| Frontend | `useIvaRisolta`                                                                | la chiamata, l'anti-race e l'etichetta dell'origine stanno **lì**, non nei tre form |

> ⚠️ **L'anteprima è best-effort di proposito**: se non risponde, il campo resta
> com'è e si salva lo stesso. L'autorità è il backend **al salvataggio** — la
> chiamata del form serve a far *vedere*, non a decidere.
>
> ⛔ **L'anteprima non è la prima riga del consumo.** Nel consumo la prima riga è
> il titolo **anche a plafond esaurito**: prenderla per un form applicherebbe il
> titolo a una riga che non ne ha più diritto — un difetto difficile da vedere.

---

## 8. Che cosa NON fa, e non è una mancanza

* **non consuma il plafond** — è sola lettura (capitolo 4);
* **non controlla se il documento è congelato**: è una proprietà del documento, ed
  è responsabilità di chi chiama;
* **non tocca i bundle**: sui componenti di un kit l'aliquota è una scelta di
  composizione già presa, e il risolutore lavora sulla riga;
* **non decide la scissione dei pagamenti**: la trasporta e basta.

---

## 9. ⚠️ Il risolutore non è il «Riepilogo IVA» del documento

Sono due cose diverse, e si confondono facilmente perché portano lo stesso nome
nella testa di chi legge.

|                 | Il risolutore                        | Il Riepilogo IVA                                                                       |
| --------------- | ------------------------------------ | -------------------------------------------------------------------------------------- |
| **domanda**     | *quale codice IVA porta questa riga* | *quanto fa l'imposta di questo documento*                                              |
| **granularità** | la singola riga                      | il documento, raggruppato per aliquota                                                 |
| **dove vive**   | `vendite.fn_resolve_iva_riga`        | le viste `vw_<doc>_riepilogo_iva_dettaglio` e, sui preventivi, una tabella di snapshot |
| **quando**      | mentre si scrive la riga             | ricalcolato a ogni modifica delle righe                                                |

⭐ **E i riepiloghi non sono un meccanismo solo**, per una scelta dichiarata:
ordini e DDT restano **live** (documenti di lavoro: congelare un intermedio crea
debito di riconciliazione, non lo risolve), mentre preventivi e fatture sono
**snapshot**, perché hanno un istante di emissione i cui valori diventano
autorevoli.

⛔ **Non si unificano in una vista generica.** La coerenza della formula fra i tipi
di documento è garantita da un test che li confronta
(`db/pgtap/vendite/test-riepilogo-iva-equivalenza-cross-doc.sql`), non da una vista
unica che forzerebbe una comunanza falsa.

---

## 10. Errori che il risolutore solleva

| Codice                         | Quando                                            | Chi può rimediare                                      |
| ------------------------------ | ------------------------------------------------- | ------------------------------------------------------ |
| `E_IVA_RESOLVE_NON_INVOCABILE` | parametri mancanti o articolo inesistente         | è un **chiamante rotto**, non un errore dell'operatore |
| `E_IVA_TITOLI_AMBIGUI`         | due titoli in pari specificità sulla stessa riga  | chi ha registrato i titoli                             |
| `E_IVA_PAESE_NON_IMPLEMENTATO` | il paese dell'emittente non ha un'implementazione | chi configura l'emittente                              |

---

## Area tecnica — esempi

**Quali titoli ha un cliente, e verso quale emittente** (la tabella ha RLS: si
vede il perimetro dell'operatore connesso):

```sql
SELECT t.id, t.soggetto_id, t.emittente_fiscale_id, tt.codice_interno AS tipo,
       t.ambito, t.validita, t.plafond, t.imponibile_utilizzato
FROM anagrafiche.soggetti_titoli_iva t
JOIN config.tipi_titolo_iva tt ON tt.id = t.tipo_titolo_id
WHERE t.soggetto_id = :soggetto_id
ORDER BY t.id;
```

**Per cosa vale un titolo ristretto:**

```sql
SELECT livello, articolo_id, gruppo_voce_id, tipo_voce_id
FROM anagrafiche.soggetti_titoli_iva_ambiti
WHERE titolo_iva_id = :titolo_id
ORDER BY livello;
```

**Che cosa risponderebbe il risolutore su una riga** (sola lettura, non consuma
niente):

```sql
SELECT * FROM vendite.fn_resolve_iva_riga(
  p_articolo_id          => :articolo_id,
  p_data_riferimento     => :data_documento,
  p_soggetto_id          => :soggetto_cliente_id,
  p_emittente_fiscale_id => :emittente_fiscale_id
);
-- con p_consumo => true (in fondo): quale titolo e i due trattamenti,
-- come nel giro del plafond. Un importo (p_imponibile) non si passa: solleva.
```

> ⚠️ `p_emittente_fiscale_id` è la **chiave primaria** di
> `anagrafiche.emittenti_fiscali`, **non** il `soggetto_ruolo_id` che il pricing
> usa: i due numeri si somigliano abbastanza da passare inosservati, e con quello
> sbagliato il risolutore non trova l'emittente, quindi non trova i suoi titoli, e
> risponde con l'aliquota ordinaria *senza sollevare*.

---
{% include-markdown "signature-core.md" %}
