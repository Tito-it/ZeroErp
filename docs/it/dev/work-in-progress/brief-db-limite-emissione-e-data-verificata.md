# Brief DB — il limite di emissione, e il documento che nasce già conforme

> **Destinatario:** team DB (`dev/db-tid`). BE e FE **attendono** i prerequisiti
> ([[feedback_be_fe_attende_prerequisiti_db]]).
>
> **Origine.** Tid, 2026-08-26, dopo tre giorni sul cantiere della numerazione e
> un caso reale: un lotto di competenza **luglio** generato il **25 agosto**
> nasceva con un documento datato **31/07**, cioè con una data che non è più
> trasmissibile.
>
> ⭐ **La motivazione, con le sue parole**, ed è la migliore che sia emersa:
> *«quando stiamo emettendo il lotto massivo, quello che fattura mese competenza
> + 15, non siamo mai in ritardo, quindi il controllo lo passerebbe. Se la
> commessa rimane ferma e viene generato il lotto si avrebbe comunque
> l'errore.»*
> Il controllo **non serve a chi lavora in ordine**: serve a impedire che una
> commessa dimenticata produca un documento che non si può più mandare.
>
> **Correlati:** [brief-db-numerazione-data-documento-e-sequenza.md](brief-db-numerazione-data-documento-e-sequenza.md)
> (il cantiere che ha reso la data una decisione del registro) ·
> [brief-db-registro-e-data-prevista-in-competenza.md](brief-db-registro-e-data-prevista-in-competenza.md)
>
> ⛔ **Stato: analisi, misure e decisioni prese. Nessun file scritto.**

---

## 1. La misura che dimostra che il cancello è al posto giusto

Su tutti i lotti esistenti, confrontando **quando il lotto è nato** con il 15 del
mese successivo alla sua competenza:

| | lotti | margine |
| --- | ---: | --- |
| **in termine** | **46** | da 14 a 43 giorni di anticipo |
| oltre il termine | 6 | da 7 a 40 giorni di ritardo |

⭐ **46 su 52, e non per un pelo**: chi è in termine lo è di almeno due
settimane. Il giro differito di luglio gira nella prima metà di agosto, il
documento porta il 31/07, il termine è il 15/08 — passa senza accorgersene.

I 6 fuori termine sono i casi patologici: commesse rimaste ferme, lotti nati
tardi. **È lì, e solo lì, che il cancello si accende.**

---

## 2. Due forme, perché le due politiche SONO i due tipi di fattura

`registri_fatturazione.politica_data_documento` distingue già l'immediata dalla
differita. Il termine di emissione segue la stessa distinzione, quindi **non è
un parametro globale con una forma sola**:

| politica | tipo | limite di emissione | quando morde |
| --- | --- | --- | --- |
| `OGGI` | immediata | `data_operativa − 12` giorni | se si numera un documento datato più di 12 giorni fa |
| `FINE_MESE_COMPETENZA` | differita | **15 del mese successivo** alla competenza | **solo se il lotto nasce tardi** (6 casi su 52) |

⚠️ **Le due forme non si approssimano.** Con la finestra mobile un documento di
luglio resterebbe emettibile all'infinito, scorrendo in avanti; con la scadenza
per competenza dal **16 agosto** la strada è chiusa e l'unica data possibile è
quella di oggi. Scegliere una forma per entrambe sarebbe sbagliato in un verso o
nell'altro.

⛔ **Questo brief NON afferma la norma**: riporta la lettura di Tid
(«12 giorni fra data di emissione e invio»), che è la fonte su questo. Il
software non deve incorporare un'interpretazione fiscale in una costante: la
incorpora in un **parametro**, che è il motivo per cui i valori 12 e 15 stanno
a configurazione e non nel codice.

---

## 3. Dove agisce: tre punti, tre ruoli diversi

Sono gli stessi tre della data documento, e vanno tenuti distinti.

### 3.1 ⭐ Alla NASCITA: il documento nasce già conforme (decisione di Tid)

> *«il lotto deve nascere con la data giusta, con la data verificata già con le
> regole che stabiliamo, e non con data 31/07 fissa nell'esempio di luglio»*

`fn_calcola_data_documento` smette di restituire il risultato grezzo della
politica e restituisce:

```
GREATEST( data_della_politica , pavimento_effettivo )

pavimento_effettivo = GREATEST( ultima_data_del_sezionale ,
                                limite_di_emissione_del_registro )
```

⛔ **Solo sulla data CALCOLATA, MAI su quella DICHIARATA.** Se un operatore
scrive 31/07 nel dialog, quella data si **rifiuta** — non si sposta in silenzio.
Spostare senza dirlo una scelta esplicita è la classe di difetto che il cantiere
della numerazione ha passato tre giorni a togliere: il clamp vale per il default,
il cancello vale per la dichiarazione.

✅ **La data di nascita diventa dipendente dal tempo, ed è ACCETTATO** (Tid,
2026-08-26: *«è giusto che sia così»*). Lo stesso lotto generato oggi e domani
nasce con due date diverse, e un lotto annullato e rigenerato cambia data —
caso non teorico, è successo il 25/08 sul `LTF-0007307`. Oggi non succede: il
31/07 è stabile per costruzione.

⚠️ È scritto qui come **decisione**, non come riserva: chi legge non deve
fermarsi a chiedersi se sia un effetto indesiderato da evitare. È il prezzo di
«nascere conforme», è stato guardato, e si paga volentieri.

### 3.2 La TARGA

`fn_get_data_minima_numerabile[_lotto]` torna il **pavimento effettivo**, non
più il solo pavimento di sequenza: il DatePicker propone una data già ammessa e
l'errore resta l'eccezione.

### 3.3 Il CANCELLO

`fn_get_next_progressivo` rifiuta sotto il pavimento effettivo.

⛔ **Con un codice errore SUO**, distinto da quello della sequenza. «Il documento
è più vecchio del limite di emissione» e «la data è anteriore all'ultimo numero
emesso» sono due cose diverse, si rimediano in due modi diversi, e dire la
seconda quando è la prima manda a cercare la cosa sbagliata. Classe
`DATO_ERRATO`, `context.campo = data_documento`, bersaglio sul documento.

⚠️ **Il clamp non rende superfluo il cancello**, e va scritto perché sembra di
sì: il pavimento di sequenza si muove mentre altri numerano, quindi un documento
nato conforme può diventare non numerabile dopo. Targa, cancello e dialog
restano tutti e tre.

---

## 4. Dove vive il parametro: slot globale + override, senza ripetizioni

Tid: *«sul registro, ma richiede una ripetizione per ogni registro»*. Vero —
quindi **slot + override**, il pattern già in uso nel progetto:

| dove | cosa |
| --- | --- |
| `config.parameters` | i due valori di default: `12` (immediata) e `15` (giorno del mese, differita) |
| `registri_fatturazione` | due colonne **nullable**: `NULL` = vale il default globale |

Si scrive il valore **una volta sola**; un registro con un'esigenza propria la
dichiara, gli altri tacciono.

❓ **Domanda al team DB (D-1): una colonna o due?**
Una sola colonna il cui *significato* dipende da `politica_data_documento`
(giorni se `OGGI`, giorno-del-mese se `FINE_MESE_COMPETENZA`) è compatta ma
ambigua: un `12` letto come giorno del mese è un valore plausibile e sbagliato.
Due colonne distinte sono inequivocabili ma permettono di valorizzare quella che
la politica non legge — un valore **inerte**, che sembra una configurazione e non
lo è.

⭐ Propendo per **due colonne + un CHECK** che ammetta valorizzata solo quella
coerente con la politica: così l'ambiguità non c'è e il valore inerte nemmeno.
Ma la scelta è vostra, è casa vostra.

---

## 5. ⭐ L'effetto collaterale che chiude un altro cerchio

Il 2026-08-24 Tid segnalava che un lotto di competenza luglio lavorato ad agosto
**non compariva nella scheda «recuperi del mese»**. Il criterio della scheda è
«competenza precedente **e** documento datato nel mese», e con
`FINE_MESE_COMPETENZA` quel documento porta una data di luglio: fuori per
costruzione.

⭐ **Il clamp del §3.1 lo risolve da solo.** Un lotto in ritardo nasce con una
data di oggi, quindi:

* è trasmissibile, perché la sua data è di oggi;
* **compare nei recuperi del mese**, perché porta la data del mese in cui è
  stato lavorato.

Erano la stessa cosa vista da due lati. **Non serve cambiare il criterio della
scheda** — serve che i documenti in ritardo nascano con la data giusta.

⚠️ Vale per i documenti **futuri**: il clamp non retroagisce. I sei già nati con
date arretrate continueranno a non comparire finché non vengono ri-datati dal
dialog.

---

## 6. Le consegne

| | Cosa |
| --- | --- |
| **DB-1** | `config.parameters`: i due default (12 giorni immediata, 15 giorno-del-mese differita), con `description` che dice **che cosa** misurano e che sono una lettura configurabile, non una costante di legge |
| **DB-2** | `registri_fatturazione`: le colonne di override nullable + il CHECK di coerenza con la politica (▶ D-1) |
| **DB-3** | `vendite.fn_get_limite_emissione(p_registro_id, p_competenza_mese) RETURNS date` — **una sola sede** per le due forme: legge la politica, sceglie la forma, applica override o default. Nessun chiamante deve sapere quale forma si applica |
| **DB-4** | `fn_calcola_data_documento`: clamp con `GREATEST(politica, pavimento_effettivo)`. ⛔ Solo sul ramo calcolato, mai sulla data dichiarata |
| **DB-5** | `fn_get_data_minima_numerabile[_lotto]`: tornano il pavimento **effettivo** |
| **DB-6** | `fn_get_next_progressivo`: il cancello confronta col pavimento effettivo, con **codice errore nuovo** (§3.3) + ripiego senza `%s` + policy rigenerate |
| **DB-7** | pgTAP: il flusso normale **passa** (lotto di luglio nato il 5 agosto → 31/07, nessun rifiuto); il lotto tardivo **nasce con la data di oggi**; una data dichiarata sotto il limite viene **rifiutata** e non spostata; le due forme danno due risultati diversi sullo stesso caso; il pavimento effettivo è il massimo dei due |

---

## 7. ⛔ Ordine di accensione, e i documenti già in coda

Come per il cancello sulla sequenza: acceso sui dati di oggi, il limite blocca
lavoro legittimo. Misurato il 2026-08-26 sui sei documenti `EMESSA` da numerare:

| lotto | data doc | giorni indietro | già fermo per la sequenza? | lo blocca il limite? |
| --- | --- | ---: | --- | --- |
| LTF-0000680 | 31/07 | 26 | no (sezionale senza pavimento) | **sì** |
| LTF-0000579 | 31/07 | 26 | sì | — |
| LTF-0001225 | 02/08 | 24 | sì | — |
| LTF-0001296 | 03/08 | 23 | sì | — |
| LTF-0006585 | 23/08 | 3 | sì | — |
| LTF-0006929 | 24/08 | 2 | no | no, passa |

⭐ **Uno solo in più** rispetto a quelli già fermi. È il momento buono per
accendere: fra un mese sarebbero di più, e ognuno andrà ri-datato a mano dal
dialog.

---

## 8. Cosa NON è in questo cantiere

* **Il criterio della scheda «recuperi del mese»**: lo risolve il clamp (§5), non
  si tocca.
* **Un limite SUPERIORE alla data** (documenti datati nel futuro): con
  `FINE_MESE_COMPETENZA` una fattura di competenza corrente nasce datata a fine
  mese, cioè in avanti, ed è il comportamento voluto. Nominato per non
  riscoprirlo come difetto.
* **La trasmissione allo SDI** e i suoi termini reali: qui si presidia la **data
  del documento**, non l'invio. Se un giorno il sistema trasmetterà davvero, il
  termine andrà misurato su quel momento e non su questo.

---

## 9. Registro

### 2026-08-26 · Analisi, misure e decisioni

Nato dalla discussione sul caso `LTF-0007307`. Misurato: 46 lotti su 52 nascono
in termine con almeno due settimane di margine, quindi il cancello non tocca il
flusso normale. Decise da Tid: **clamp alla nascita** sulla data calcolata, forma
del limite **per politica** (12 giorni l'immediata, 15 del mese successivo la
differita), parametro globale con override sul registro, e **la data di nascita
dipendente dal tempo accettata esplicitamente**. Resta la sola D-1, di
struttura, al team DB.
