# Brief al team DB — l'aggregato *parlante* per riga d'ordine

> **Tipo**: brief DB · **Data**: 2026-08-17 · **Richiedente**: perimetro BE/FE ·
> **Stato**: 🟢 **CHIUSO** — accolto e implementato dal team DB il 2026-08-17
> (`20260817-15`, pgTAP **11/11** come applicazione), **con tre cambi rispetto
> alla richiesta**: §8.
>
> ✅ **Pushato e integrato il 2026-08-18** (PR #1282 → `Tito-dev`): changeSet e
> doc auto-gen sono in repository, insieme al backend che li consuma (PR #1283).
> Il corpo pubblicato coincide con quello che il perimetro BE aveva
> introspezionato dalla vista viva per costruirci sopra — nessuna sorpresa fra
> il DB di sviluppo e il changeSet.
>
> **Origine**: [brief-design-partita-merce-generalizzata.md](brief-design-partita-merce-generalizzata.md)
> §21.6 — misura del 2026-08-17 sul DB di sviluppo.
>
> **Serve a**: [brief-design-situazione-merce-ordine.md](brief-design-situazione-merce-ordine.md)
> (cantiere 2, pannello situazione merce). È **l'unico** prerequisito DB che
> quel cantiere ha: tutto il resto — partite, code, `sospetto_duplicato_ordine`,
> `NON_MISURABILE` — è già in produzione dal push del 2026-08-17.

---

## 1. La domanda a cui risponde

Il pannello del cantiere 2 mostra, sull'ordine, **un riassunto per riga
d'ordine** con il dettaglio per partita sotto (decisione D-2, Tid 2026-08-17).

La partita è per **riga di DDT**. Il riassunto per **riga d'ordine** è un
aggregato — e oggi esiste già un aggregato per riga d'ordine,
`vw_contatore_merce`. **Ma non è quello giusto**, e non è un'opinione: è scritto
nella sua stessa documentazione, da questo cantiere.

> *«Questa resta il contatore **GREZZO** che dosa le macchine; chi vuole la
> semantica parlante (`stato`, NULL = "non si applica") legge
> `vw_partite_merce`.»*

## 2. I tre motivi, con le misure

### 2.1 🔴 Il contatore appiattisce i NULL — e il pannello direbbe il falso

`vw_contatore_merce.differenza` **non è mai NULL**, ed è deliberato:
`fn_list_ddt_da_pushare` fa `COALESCE(differenza, 0)` e un NULL smetterebbe di
fatturare una riga in silenzio.

Ma la formula è `tenuti − fatturato` e **non guarda** né `fatturabile` né
`misurabile`. Su una riga d'ordine le cui partite sono tutte `NON_FATTURABILE`:

```text
livello 2 (vw_partite_merce):    differenza NULL       →  «non si applica»
livello 1 (vw_contatore_merce):  tenuti − 0 > 0        →  «N da fatturare»
```

⚠️ È **il falso allarme che il §8.4 ha tolto**, rientrato dalla porta
dell'aggregato.

**Zero occorrenze oggi, e nulla lo impedisce:**

```text
partite NON_FATTURABILE ............................. 3, tutte senza ordine
righe di DDT order-backed su causale NON fatturabile . 5   ← la porta è aperta
```

⭐ E **una di quelle cinque è il caso già scritto nel §8.4-bis**: riga di DDT
**47**, causale `CONTO_VISIONE`, riga d'ordine **172**. Non si contraddice *solo
perché* la corsia ORD l'aveva già fatturata (esce `PAREGGIATA`, 1 e 1). Con
`fatturazione_trigger = 'SPEDITO'` (2 ordini su 95) o col push non ancora
passato, quella riga darebbe `NULL` al livello 2 e **«1 da fatturare»** al
livello 1 — su un conto visione.

### 2.2 Il contatore non ha `stato`

Le sue colonne sono numeri grezzi. La traduzione del verso del saldo — quella
che il §9.3 vuole fatta **una volta sola** e che la richiesta BE-2 vieta
esplicitamente di rifare in Python — sul livello 1 non esiste.

### 2.3 🔴 E il contatore non contiene le righe mai spedite

`vw_contatore_merce` è `FROM pm JOIN vendite.ordini_righe`: una riga d'ordine
senza alcuna partita **non c'è**. È dichiarato nel §15.4 ed era corretto per il
dosatore. Per un pannello è fatale:

```text
righe d'ordine attive ......................... 107
di cui SENZA alcuna partita (mai spedite) ...... 89   ← l'83%
di cui gia' fatturate sulla corsia ORD ......... 12   ← il rilievo A
```

⭐ **Su 89 righe su 107 il pannello dell'ordine sarebbe vuoto.**

## 3. Cosa si chiede — una vista, accanto e non al posto

```text
vendite.vw_situazione_merce_ordine        (nome di lavoro)
```

**Grana**: una riga per **riga d'ordine attiva**.

⛔ **`vw_contatore_merce` NON si tocca.** Dosa la fatturazione (§8.7): ogni
modifica a quella vista è una modifica agli importi di documenti fiscali. La
vista nuova le sta **accanto** — è la stessa forma che il §9.4 raccomanda per
un'eventuale materializzata.

### 3.1 Le colonne proposte

| Colonna | Contenuto |
| --- | --- |
| `ordine_riga_id`, `ordine_id`, `riga_nr`, `articolo_id` | chiave e contesto |
| `ordinato` | `ordini_righe.quantita` |
| `consegnato`, `reso`, `in_riconsegna`, `tenuti` | Σ dalle partite (0 se non ce ne sono) |
| `fatturato_merce`, `fatturato_da_ordine`, `fatturato` | Σ dalle partite + corsia ORD |
| `fatturato_anticipato` | fatturato di merce non ancora uscita — **FE-3**: non è un accredito |
| `da_spedire` | `ordinato − consegnato`, mai negativo — vedi §4.1 |
| `partite_merce` | quante partite ci sono sotto (0 = mai spedita) |
| `misurabile` | `bool_and` delle partite ∧ corsia ORD |
| `differenza` | **con la propagazione dei NULL**, §3.2 |
| `stato` | il vocabolario del §9.3 + il valore nuovo, §3.3 |

### 3.2 ⭐ La regola che è il cuore della richiesta: i NULL si propagano

> **Se nessuna partita ha un conto che si applica, il livello 1 non ha un
> conto.** `differenza` NULL, non zero, non `tenuti`.

```text
tutte le partite hanno differenza NULL  →  differenza NULL
almeno una ha un conto                  →  Σ dei conti che si applicano
nessuna partita (mai spedita)           →  differenza NULL
```

⚠️ **Non è un `COALESCE` da mettere o togliere: è la differenza fra un pannello
che dice «non si applica» e uno che manda un operatore a fatturare un conto
visione.**

### 3.3 Il vocabolario di `stato` — e una domanda di merito

I cinque valori del §9.3 restano. La riga **mai spedita** ne vuole uno nuovo.

⭐ **Proposta: `NON_SPEDITA`, non `DA_SPEDIRE`.** La ragione è che il `stato` del
§9.3 risponde a *«di questa merce, cosa resta da fatturare o accreditare?»*: è
il verso del **saldo**. «Da spedire» è una **quarta** cosa — un arretrato di
spedizione, che il §8.1 ha appena finito di separare dal saldo — e infilarla nel
vocabolario del saldo rifà l'appiattimento che quel rilievo ha tolto.

Quindi:

* `stato = 'NON_SPEDITA'` dice **che non c'è ancora merce**, e `differenza` è
  NULL perché non c'è niente da saldare;
* l'arretrato di spedizione è la **colonna** `da_spedire`, che vale anche per le
  righe **parzialmente** spedite — dove lo stato viene giustamente dalle partite.

❓ **Domanda al team DB**: si condivide la separazione, o si preferisce un
`DA_SPEDIRE` a vocabolario? È l'unica scelta di merito di questo brief.

### 3.4 Sicurezza

`WITH (security_invoker=on)` — obbligatorio: `commesse_attivita` e `ordini`
hanno la RLS. ⚠️ **Va ri-specificata a ogni `CREATE OR REPLACE`**: PostgreSQL la
azzera e non compare in `pg_get_viewdef` (§11.1).

## 4. Le trappole viste da qui

### 4.1 `da_spedire` non può essere negativo

Una riga può essere **sovra-spedita**: `uq_ordini_r_ful_v_pair` non lo impedisce
e le righe manuali sullo stesso articolo esistono (è il `sospetto_duplicato_ordine`
di S6b). `GREATEST(0, ordinato − consegnato)`, come fa già il dosatore.

### 4.2 ⚠️ Le ri-consegne vanno escluse dall'aggregato

Stessa ragione di `vw_contatore_merce` (changeSet `20260817-12`): una riga di
ri-consegna **ha** una riga d'ordine — `fn_genera_ddt_riconsegna` le crea un
fulfillment — e senza `WHERE NOT e_riconsegna` i suoi pezzi verrebbero contati
**due volte**, una nel `consegnato` dell'origine e una come partita a sé.
🔴 È il difetto che il caso D di `test-fn-list-ddt-da-pushare-contatore-v1` ha
fermato a agosto: qui si ripresenterebbe identico.

### 4.3 La riga d'ordine con `MULTIPLA` origine

`vw_partite_merce.origine = 'MULTIPLA'` esiste (§9.1): una riga di DDT che evade
due righe d'ordine. Oggi non succede, ma il modello lo ammette e l'aggregato lo
attraversa. **Che la merce non si duplichi fra le due righe d'ordine va deciso e
scritto**, non lasciato al `LEFT JOIN`.

### 4.4 `preCondition` e `runOnChange`

Nulla di dati in `20_code` (§11.7). `runOnChange: true` vietato (§11.3), e chi
lo spegne corregge `validCheckSums` **al plurale**.

## 5. pgTAP richiesti

`db/pgtap/vendite/test-vw-situazione-merce-ordine-v1.sql`, dal template, con le
tre righe di preambolo e `PGTAP_RUNNER=app`:

* esistenza · `security_invoker` · `columns_are`;
* 🔴 **riga d'ordine mai spedita** → presente, `partite_merce = 0`,
  `differenza` **NULL**, `stato = 'NON_SPEDITA'`, `da_spedire = ordinato`;
* 🔴 **tutte le partite NON_FATTURABILE** → `differenza` **NULL** e non `tenuti`
  (è il §2.1: il ramo che **nessun dato attraversa oggi**, va costruito apposta);
* partite miste (una con conto, una senza) → Σ dei soli conti che si applicano;
* kit senza `coeff_qta` → `misurabile = false`, `differenza` NULL;
* **ri-consegna esclusa** → i pezzi contati una volta sola (§4.2);
* riga sovra-spedita → `da_spedire = 0`, mai negativo;
* **contesto di scope ristretto** → `misurabile = false` / assenza, mai uno zero
  (§8.6).

⚠️ E il collaudo di non-regressione: `scripts/pgtap-baseline.sh vendite`. La
vista è **nuova e non letta da nessuno**, quindi non dovrebbe muovere niente —
ma il §14.1 ricorda che è proprio l'attesa «non cambia nulla» a far saltare i
controlli.

## 6. Cosa NON si chiede

* nessuna tabella, nessun trigger, nessuna funzione;
* **nessuna modifica a `vw_contatore_merce`**, `vw_partite_merce`,
  `vw_af_merce_per_riga`, `vw_resi_da_accreditare`, `fn_list_ddt_da_pushare`;
* nessuna bonifica dati: è una vista, non esiste un «prima» (§9.6);
* nessun codice errore nuovo (non è un guard, è una lettura).

## 7. Cosa può partire senza aspettare

Il perimetro BE ha già cominciato sui pezzi che **non** dipendono da questa
vista: il factory dell'endpoint, il lato **DDT** (completo oggi), il livello 2
sull'ordine (partite filtrate per `ordine_id`) e le due code nell'envelope.
Resta fuori il **solo** riassunto per riga d'ordine.

---

## 8. ✅ La risposta del team DB (2026-08-17) — accolta, con tre cambi

`20260817-15`, applicata, pgTAP **11/11** come applicazione.
`vw_contatore_merce` **non toccata**: i suoi 18 valori sono invariati.

> Il §2.3 era esatto alla riga: **89 righe d'ordine su 107** non hanno alcuna
> partita. Da solo giustificava la vista.

### 8.1 🔴 `da_spedire` — **la mia formula era sbagliata**, e il caso che la smentisce è *il* caso

Avevo proposto `GREATEST(0, ordinato − consegnato)`. È una **seconda formula**
per una grandezza che il DB già calcola, e le due divergono:

```text
ORD0018586 · riga 18946 · ordinato 21 · evaso 21 · reso per ri-consegna 3
  la mia proposta ...  0     ← «niente da spedire»
  quella giusta ....   3     ← il cliente aspetta 3 pezzi
```

⚠️ **La causa**: il `consegnato` di una partita **include le ri-consegne**
(`20260817-11`), quindi non è confrontabile con `ordinato`. Il `GREATEST(0, …)`
non risolveva il problema: lo **nascondeva** portando a zero un numero negativo
che era il sintomo.

🔴 **E la riga 18946 è quella da 21 pezzi del §3 del brief pannello** — il caso
che ha generato l'intero cantiere sarebbe stato il primo a essere letto male, e
avrebbe detto **il contrario della coda ri-consegne**.

✅ Ora `da_spedire` viene dalla formula di `fn_ordine_ha_residuo_evasione`
(`ordinato − evaso + fn_ordine_riga_qta_riconsegna`). Verificato sulle 107 righe.

⭐ **La lezione, e vale oltre questo brief**: una grandezza che il sistema già
calcola non si ri-deriva in una vista nuova con una formula «equivalente». Le
due si scoprono diverse su un caso reale, non in revisione.

### 8.2 `NON_SPEDITA` — accolta, con un argomento in più

Il team DB aggiunge la ragione che mancava: con le righe mai spedite dentro,
**`fatturato_anticipato` smette di essere dormiente** — le 12 righe fatturate e
mai spedite del rilievo A sono esattamente ciò che quella colonna descrive.
Verificato: 12 righe `NON_SPEDITA` con `fatturato_anticipato > 0`.

### 8.3 `MULTIPLA` — si dichiara, non si ripartisce

Zero casi su 27. Se comparisse, la riga esce `misurabile = false`: meglio «non lo
so» di un numero inventato. È la stessa scelta del §8.6.

### 8.4 🔴 Il difetto di RLS che il loro test 10 ha trovato

La prima versione partiva da `vendite.ordini_righe`, che **non ha RLS** — ce l'ha
`vendite.ordini`. Un utente fuori perimetro avrebbe visto tutte le **107 righe
con i conti a zero**: le partite nascoste dalla loro RLS, i `COALESCE` a
trasformarle in zeri.

⭐ **Cioè «non ho il permesso di saperlo» presentato come «non c'è nulla da
fare», sull'intero pannello.** Aggiunto il `JOIN vendite.ordini`: ora restituisce
0 righe invece di 107 azzerate.

⚠️ È il §8.6 del brief partita che si ripresenta in una forma nuova e peggiore:
lì era *una* colonna a zero, qui era **l'intero documento** che sembrava sano. E
il difetto nasceva proprio dai `COALESCE` che servivano a far comparire le righe
mai spedite — la correzione del §2.3 e questo difetto sono la **stessa riga di
codice**.

### 8.5 ⚠️ La correzione alla mia misura — giusta nel numero, da precisare nella causa

Il team DB corregge il mio *«5 righe di DDT order-backed su causale non
fatturabile»* → **è 1**. Il numero è giusto. La ragione data — *«le altre quattro
sono su documenti senza ordine»* — non regge: la mia query faceva `JOIN
ordini_righe_fulfillment`, quindi l'ordine c'è **per costruzione**. Rimisurato:

```text
causale presente e NON fatturabile ......  1   ← la riga 47, l'unica prova vera
causale ASSENTE (DDT in bozza) ..........  4   ← contate per errore
```

🔴 **L'errore era mio, ed è ironicamente quello di cui parla il brief.** Avevo
scritto `COALESCE(ct.fatturabile, false) IS FALSE`: un `COALESCE` che tratta
**«causale assente» come «non fatturabile»**. Ma la causale è obbligatoria solo
all'emissione (§8.4): su un DDT in bozza è un'**astensione**, non
un'affermazione — *«`0` è un'affermazione, `NULL` è un'astensione»*, la stessa
frase che questo cantiere cita due volte.

⚠️ **E la conclusione va corretta di conseguenza**: quelle 4 righe non sono
prova che la porta sia aperta, perché per la decisione D1 un DDT in bozza **non
ha ancora una partita**. La porta resta aperta — la riga 47 esiste — ma su
**un** caso, non su cinque.

### 8.6 Il contratto, introspezionato dalla vista viva

18 colonne, `security_invoker=on`. Le due cose che il BE deve sapere e che il
team DB ha ripetuto:

* ⛔ **non trasformare il vuoto in zero**: `differenza` NULL significa «il conto
  non si applica» (mai spedita · causale non fatturabile · non calcolabile);
* ⛔ **non ri-tradurre il segno del saldo**: `stato` ha **sei** valori —
  `NON_SPEDITA` · `PAREGGIATA` · `DA_FATTURARE` · `DA_ACCREDITARE` ·
  `NON_FATTURABILE` · `NON_MISURABILE`.

**Verificato come applicazione** (contesto operatore, non owner):

```text
107 righe        89 NON_SPEDITA (tutte differenza NULL, 12 con anticipato)
                 11 DA_FATTURARE · 5 PAREGGIATA · 2 DA_ACCREDITARE
le 18 righe che le due viste condividono → differenza IDENTICA, 0 divergenze
riga 18946 → ordinato 21 · tenuti 13 · fatturato 21 · differenza −8
             da_spedire 3 · DA_ACCREDITARE
```

⭐ **L'ultima riga è il cantiere in una riga**: il caso del §3 del brief pannello
— cinque schermate per ricostruirlo — è **una riga sola**, con dentro anche i 3
pezzi da ri-spedire che nessuna delle cinque schermate diceva insieme al resto.

### 8.7 Il guadagno dichiarato dal team DB, e perché conta

Il saldo di questa vista è la **somma dei saldi delle spedizioni**: il fatturato
in anticipo resta fuori. Quindi un ordine fatturato alla conferma e spedito a
metà esce `PAREGGIATA` con `fatturato_anticipato 6` e `da_spedire 6`, invece del
`−6` del contatore — che si leggerebbe **«6 da accreditare»**.

🔴 **È il rilievo A che si chiude a video**, e senza toccare i numeri su cui si
fattura.

## 9. Cosa resta al perimetro BE/FE

* **BE**: l'endpoint `situazione-merce` legge questa vista come livello 1
  (§21.2 del brief partita). ✅ **Fatto e integrato** (PR #1283).
* **FE**: `NON_SPEDITA` entra nella tavolozza insieme a `RICONSEGNA` e
  `NON_MISURABILE` (FE-1); `fatturato_anticipato` e `da_spedire` **non sono
  accrediti** (FE-3).
* **Doc auto-gen**: `docs/it/dbzero/vendite/{views,manual}/vw_situazione_merce_ordine.md`
  ✅ in repository dal push del 2026-08-18.
