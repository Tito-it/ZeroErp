# Brief DB — i residui del lineage: il `root` che dipende dagli id, la commessa senza origine, e la nota di credito che si chiama «Fattura»

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine.** Voce **L7.5** di
> [brief-db-lineage-arco-reso-nota-credito.md](../work-done/brief-db-lineage-arco-reso-nota-credito.md):
> *«portare a un cantiere suo i due residui del §7»*. Sono usciti da lì e non
> sono di lì: il cantiere dell'arco `S` li ha **esposti**, non creati.
> ⭐ **Dal 2026-08-26 sono TRE**: alla chiusura del brief madre è arrivato qui
> anche il suo §7-bis (§3) — un brief non si chiude *sopra* un difetto aperto,
> e quello ha la stessa sede degli altri.
>
> **Stato.** ✅ **2026-08-29 — TUTTE E QUATTRO LE VOCI SONO APPLICATE, e la 3
> è arrivata fino a video.** Sei changeSet: `20260828-22` … `-25` (le quattro
> voci) più `20260829-01` e `-02`, che hanno chiuso la coda del §3.4 — la
> colonna sulle viste di lista — e portato l'estrazione del §3-ter. Il BE/FE
> del §3.5 è scritto e committato (`dd562af68`).
>
> ⛔ **Resta il solo §3.6**, e non è più una domanda: ✅ **la decisione è stata
> presa il 2026-08-29** — una sola sede, forma `numero - serie` senza anno, e la
> data **fuori** dal codice (§3.6-ter). Quel che manca è **scriverla**: una sede
> in DB che la compone, e il nodo del grafo che la legge.
>
> *(Superato: «2026-08-28 — tutte e quattro SCRITTE, provate e NON applicate».
> Quella riga è rimasta vera per un giorno e falsa per due, ed è la ragione per
> cui questo aggiornamento esiste: è esattamente il difetto della voce 4 —
> la documentazione che nessuno rilegge perché «si aggiorna da sola».)*
>
> **Le due domande di modello hanno avuto risposta**, e nessuna delle due dai
> dati: il §2.4 da **chi scrive** le righe (§2.4-bis), il §1.3 da una
> **decisione dichiarata** (§1.6). *(E il §3.6, che il 28/08 «restava fuori
> perché era una decisione e non un fix», è stato deciso il 29 — sopra.)*
>
> *(Superato: «2026-08-26 — analisi e misure, nessun file scritto». Resta qui
> perché è la data di nascita del cantiere.)*
>
> ⚠️ **La seconda voce è più grossa di come il brief madre la descriveva.**
> Diceva *«2 righe `DDT_VENDITA` che non producono nessun arco — residuo?»*.
> Misurate: non sono un residuo, sono **`ROOT`**, sono l'**unica** sorgente delle
> loro commesse, una è di **nove giorni fa**, e i due DDT esistono. Il risultato
> è che due commesse vive dichiarano nel grafo di **non avere origine**.
>
> **Correlati:**
> [vw_documento_lineage_archi](/dbzero/vendite/manual/vw_documento_lineage_archi) ·
> [vw_documento_lineage](/dbzero/vendite/manual/vw_documento_lineage)

---

## 0. Le quattro voci in una riga

| # | Cosa | Gravità | Chi lo vede oggi |
| --- | --- | --- | --- |
| **1** | Il `root` di un nodo con più sorgenti si sceglie su `from_tipo_id`, cioè su un **id di `config.sorgenti`** e non su una chiave stabile | 🟠 fragilità silenziosa, nessun effetto oggi | nessuno — finché gli id non cambiano |
| **2** | `commesse_sorgenti` ha righe **`DDT_VENDITA`** che non producono nessun arco: quelle commesse risultano **senza origine** nel grafo | 🔴 dato vero non rappresentato | chi apre il pannello «Passaggi» di quelle due commesse, e la colonna «Transito» dei due DDT |
| **3** | La colonna «Transito» **chiama «Fattura» una nota di credito**, e mostra il numero **nudo** (`1`): la natura e il codice parlante non escono dalla summary | 🔴 dice la parola sbagliata | **ogni** operatore che guarda la lista resi o la lista ordini |
| **4** | La **descrizione** di `vw_documento_lineage_archi` non nomina l'arco **`T`**, che esiste dal 2026-08-28 — e la doc **manuale** sulla stessa pagina dice «dodici lettere». Le due si contraddicono | 🟠 doc che dice il falso su un vocabolario dichiarato **chiuso** | chi apre la doc della vista per sapere quali archi esistono |

**Stato al 2026-08-29 — tutte applicate.**

| # | changeSet | presidio | esito |
| --- | --- | --- | --- |
| **1** | `20260828-24` (`rango_origine`) + `20260828-25` (la `inc` lo legge) | pgTAP **41**, **43**, **44** | ✅ nessun lavoro BE/FE: la regola vive nella vista |
| **2** | `20260828-24` (arco **`U`**, DDT → Commessa) | pgTAP **13**, **42** | ✅ misurato il 29/08: le due commesse hanno `n_sorgenti = 1` e root `DDT0000030` / `DDT0010839` |
| **3** | `20260828-22` + **`20260829-01`** (la colonna sulle **sette** viste di lista) | pgTAP **7**, **40**, **31..37** | ✅ BE/FE in `dd562af68`. ⛔ La metà «numero nudo» (§3.6) resta aperta |
| **4** | `20260828-23` (`COMMENT` che nomina `T`) | la doc auto-gen | ✅ |
| **3-ter** | **`20260829-02`** — `tipo_codice_interno` nel grafo + suffisso `_interno` canonico | pgTAP **40..46** | ✅ non era nel brief: nasce dal §3-ter, sotto |

⭐ **Le voci 1 e 2 sono finite nello stesso `CREATE OR REPLACE`**, come diceva
la nota qui sotto: riscrivere due volte in due giorni una vista con
`security_invoker` è il modo di perderla.

⭐ **Le prime tre hanno una cosa in comune, ed è il motivo per cui stanno
insieme**: la cura sta **sul nodo o sull'arco**, mai sulle sette viste di lista
che li proiettano. Chi apre `vw_documento_lineage_nodi` /
`vw_documento_lineage` le sistema in un giro solo.

⭐ **E la quarta si paga zero** se si fa in quello stesso giro: è una riga di
`COMMENT`, e chi sta già riscrivendo `vw_documento_lineage_archi` per la voce 2
la scrive senza aprire niente in più (§3-bis).

---

## 1. 🟠 Il `root` dipende dall'ordine degli id di `config.sorgenti`

### 1.1 Il fatto

Nella CTE `inc` di `vendite.vw_documento_lineage` il `root` di un nodo si sceglie
così:

```sql
ORDER BY (ruolo = 'ROOT') DESC NULLS LAST, from_tipo_id, from_uid
```

Quando **nessuna** delle sorgenti porta `ruolo = 'ROOT'` — cioè quando gli archi
in gioco sono quelli che il `ruolo` non ce l'hanno affatto — il primo criterio
pareggia e a decidere resta **`from_tipo_id`**, che è la **PK di
`config.sorgenti`**.

### 1.2 La misura, sul caso che l'ha esposto

Nota di credito **20024**, dopo l'arco `S` (2026-08-25):

| | |
| --- | --- |
| `n_sorgenti` | **2** (era 1) |
| sorgenti forward | commessa 322 via `G`, reso 24 via `S` |
| `ruolo` dei due archi | **`NULL` entrambi** |
| `root_codice` scelto | `CMM-20260719090755356-a2b9f9` (**la commessa**) |
| perché | `config.sorgenti`: `COMMESSA = 13`, `RESO_VENDITA = 15` — **e 13 < 15** |

⭐ **La fragilità è del 2026-07-14** (la `inc` nasce lì), ma **fino al 2026-08-25
non era raggiungibile**: la nota di credito aveva **una sola** sorgente forward e
il pareggio non entrava mai in gioco. L'arco `S` è il primo a portarci due archi
`ruolo IS NULL` sullo stesso nodo.

⛔ **Se un giorno `config.sorgenti` venisse riseminata con altri id**, il `root`
di **ogni** nota di credito passerebbe dalla commessa al reso. Senza errori,
senza log, senza una riga in più da nessuna parte: solo un valore diverso — che è
esattamente la forma di difetto che il cantiere madre ha già pagato due volte (la
lettera `'R'` scritta in tre posti, la prosa del `COMMENT` mai riletta).

### 1.3 ❓ Le due domande, prima di scrivere

1. **Qual è la regola vera?** «Il `root` di una nota di credito è la commessa,
   non il reso» è una **decisione di dominio** o è il caso che oggi dà la
   risposta giusta? Perché se è una decisione va **dichiarata**, e se non lo è
   allora il pareggio va risolto in modo che non dipenda da niente di mutabile.
2. **Il `ruolo` è il posto giusto?** Gli archi `B`/`E`/`F` portano
   `ruolo = ruolo_link` da `commesse_sorgenti` (`ROOT`/`COLLEGATO`) e per loro il
   primo criterio decide da solo. `G` e `S` non hanno un `ruolo` **perché non
   c'è una tabella ponte che lo scriva**. La domanda è se il rango vada
   **dichiarato sull'arco** (una colonna calcolata nella vista archi, come
   `is_ramo_inverso`) invece che dedotto dal tipo del nodo.

> ✅ **RISPOSTO il 2026-08-28.** Vedi §1.6.

### 1.4 Le due cure candidate

| | Cura | Pro | Contro |
| --- | --- | --- | --- |
| **a** | Ordinare su `s.codice_interno` invece che su `from_tipo_id` | una riga, e `codice_interno` è **immutabile** (trigger DB) | l'ordine diventa **alfabetico**: `COMMESSA` < `RESO_VENDITA` regge oggi per caso, come 13 < 15 |
| **b** | Un **rango dichiarato** sull'arco, nella vista archi, accanto a `is_ramo_inverso` | la regola è **scritta**, in un posto solo, e si legge | va deciso il rango di tutti gli undici archi, non solo di due |

⭐ **La (a) è più corta e non è la cura**: sostituisce una coincidenza numerica
con una coincidenza alfabetica. La (b) è la forma che il progetto ha già scelto
per `is_ramo_inverso` — *una proprietà dell'arco, calcolata una volta sola nella
vista archi, letta dai consumatori* — e ha il vantaggio di rendere la domanda
1.3.1 **obbligatoria**: non si può scrivere un rango senza aver deciso la regola.

> ✅ **Scelta la (b) il 2026-08-28.**

### 1.5 Il presidio che manca

> ✅ **Non manca più**: pgTAP **41**, **43** e **44**.

Nessun pgTAP oggi asserisce niente sul `root` di un nodo multi-sorgente. Qualunque
cura scelta, serve un test che dica **la regola** e non il dato di oggi (lezione
del rilievo 3 del §0.2 del brief madre): *«a parità di `ruolo`, il `root` di un
nodo è ⟨la regola⟩»*, seed-agnostico.

### 1.6 ⭐ La regola, dichiarata — `20260828-24` e `20260828-25`

**`rango_origine`, una colonna della vista archi**, accanto a `is_ramo_inverso`.
Dichiara quanto è **a monte** il documento **sorgente** dell'arco:

| rango | che cosa | archi |
| ---: | --- | --- |
| **10** | la **trattativa** — dove il flusso comincia | `A` `B` `C` `D` |
| **20** | l'**impegno** — il documento che vincola | `E` `F` `H` |
| **30** | l'**esecuzione** — la commessa, che è già un effetto | `G` |
| **40** | la **consegna** — il DDT | `U` `R` |
| **50** | il **ritorno** — ciò che il flusso rimanda indietro | `S` `T` `N` |

E la `inc` diventa
`ORDER BY (ruolo='ROOT') DESC NULLS LAST, rango_origine, from_uid`.

⭐ **L'ordine dei tre criteri *è* la regola**, e va letto così:

1. **`ruolo='ROOT'` prima di tutto.** Quando una tabella ponte ha **dichiarato**
   qual è l'origine (`commesse_sorgenti.ruolo_link`, sui rami `B`/`E`/`F`/`U`),
   quella dichiarazione batte qualunque scala generale: *un dato scritto da chi
   sa vale più di una regola dedotta*.
2. **`rango_origine`**, fra archi che un ruolo non ce l'hanno.
3. **`from_uid`**, tie-break residuo — e vale **solo** dove il modello non ha una
   preferenza. È immutabile, quindi stabile; non è significativo, ed è meglio
   dirlo che fingere una regola che non c'è.

**Le due gare vere** — le uniche due destinazioni che ricevono davvero più archi
forward:

| destinazione | contendenti | vince | perché |
| --- | --- | --- | --- |
| `FATTURA` | `G` commessa (30) · `S` reso (50) | la **commessa** | è il risultato di prima, ma per una **ragione** invece che per 13 < 15: un reso è una *conseguenza*, non un'origine |
| `DDT` | `H` ordine (20) · `T` reso (50) | l'**ordine** | ⚠️ **questa gara non l'aveva vista nessuno**: un DDT di ri-consegna *order-backed* ha davvero entrambi gli archi in ingresso, dal 2026-08-28 |

⛔ **E non è «ordinare sul tipo con un altro nome»** — l'obiezione è giusta e la
risposta sta nella **provenienza** del numero:

* il rango è **scritto**, e si legge; `from_tipo_id` era un effetto collaterale
  dell'ordine di inserimento di una tabella di catalogo;
* riseminare `config.sorgenti` non sposta più niente;
* un arco **nuovo** senza rango vale `NULL`, e il pgTAP **41** lo prende. Con
  `from_tipo_id` l'arco nuovo prendeva un ordinamento silenzioso e plausibile,
  cioè la specie di difetto che non fallisce mai.

⚠️ **`R` e `N` hanno un rango pur non gareggiando mai** (la `inc` filtra
`NOT is_ramo_inverso`): un'eccezione *«tanto non serve»* è il buco da cui passa
il prossimo arco senza rango.

⚠️ **I pareggi rimasti sono deliberati.** `A`/`D` (offerta e preventivo verso lo
stesso ordine si escludono per costruzione — `documento_origine_tipo` è una
colonna sola) ed `E`/`F` (ordine e contratto sulla stessa commessa, dove il
modello non ha una preferenza e `ruolo_link` decide prima).

---

## 2. 🔴 Due commesse dichiarano di non avere origine

> ✅ **CHIUSA il 2026-08-28 — arco `U`, nel `20260828-24`.** Misurato in
> transazione annullata: le due commesse passano da `n_sorgenti = 0` e
> `root_codice` vuoto a **`n_sorgenti = 1`** con root `DDT0000030` e
> `DDT0010839`. E sono gli **unici due nodi** dell'intero grafo il cui root si
> muove: la nuova regola del §1.6, da sola, non ha spostato nient'altro.

### 2.1 Il fatto, misurato il 2026-08-26

`vendite.commesse_sorgenti` per tipo di sorgente:

| sorgente | righe | arco prodotto |
| --- | ---: | --- |
| `PREVENTIVO` | 47 | `B` |
| `ORDINE_VENDITA` | 28 | `E` |
| `CONTRATTO` | 3 | `F` |
| **`DDT_VENDITA`** | **2** | ⛔ **nessuno** |

Le due righe:

| `commesse_sorgenti.id` | commessa | `sorgente_uid` | `ruolo_link` | inserita |
| ---: | ---: | ---: | --- | --- |
| 154 | 188 | 54 → `DDT0000030` | **`ROOT`** | 2026-07-10 |
| 7789 | 15370 | 15848 → `DDT0010839` | **`ROOT`** | **2026-08-17** |

### 2.2 ⛔ Perché non è «un residuo», e il brief madre lo diceva più mite

Quattro misure, tutte contrarie all'ipotesi «vecchie righe da buttare»:

1. **`ruolo_link = 'ROOT'`** su entrambe — non `COLLEGATO`, non `NULL`: chi le ha
   scritte stava dicendo *«questa commessa nasce da qui»*;
2. sono l'**unica** sorgente delle rispettive commesse — nessuna delle due ha
   anche un preventivo, un ordine o un contratto;
3. **i due DDT esistono** (`DDT0000030`, `DDT0010839`), non sono id orfani;
4. la seconda è del **2026-08-17**, nove giorni fa. Non è archeologia.

⭐ **Ed è materiale vivo del collaudo in corso**: `DDT0010839` è il DDT dei resi
`5797`/`5799` della tabella in cima a
[collaudo-in-app-nota-credito-resi.md](../work-done/collaudo-in-app-nota-credito-resi.md).

### 2.3 Cosa si vede a video, oggi

Lineage delle due commesse:

| commessa | `n_sorgenti` | `root_codice` | `is_transitato` |
| --- | ---: | --- | --- |
| 188 (`CMM-20260710145604304-c6a64e`) | **0** | *(vuoto)* | `t` |
| 15370 (`CMM-20260816224228686-b9946f`) | **0** | *(vuoto)* | `t` |

⛔ **`n_sorgenti = 0` non è «non lo so»: è un'affermazione.** Il pannello
«Passaggi» di quelle due commesse scrive *«nessuna origine»* — la stringa
`vendite.lineage.nessuna_origine` — sopra due commesse che un'origine ce l'hanno,
scritta nella loro tabella dei legami.

E il verso opposto: sulla **lista DDT**, `DDT0010839` non mostra nella colonna
«Transito» la commessa (e quindi le fatture) che ne sono nate. Il documento è a
monte di un flusso che il grafo non racconta.

⚠️ **È la stessa specie del cantiere madre** — *un legame che esiste nel dato e
non nel grafo* — con una differenza che vale: lì il dato era in una tabella nata
apposta (`resi_righe_accrediti`) e la risposta era ovvia; qui il dato è in una
tabella **generica** (`commesse_sorgenti`), e prima di leggerlo va deciso se
quello che dice è ammesso.

### 2.4 ❓ La domanda di dominio, che viene prima dell'arco

> **Un DDT può essere sorgente di commessa?**

Non è una domanda sul grafo: è una domanda sul **modello**. Le tre risposte
possibili portano a tre lavori diversi, e nessuno dei tre è «aggiungere un arco»
da solo:

| Risposta | Cosa comporta |
| --- | --- |
| **Sì, è ammesso** | serve il **dodicesimo arco** `DDT → Commessa`, gemello di `B`/`E`/`F` (stessa forma, chiave `d.id::text` — ⚠️ e va **verificata**, la chiave di `commesse_sorgenti.sorgente_uid` è polimorfa: uuid per il preventivo, `id::text` per gli altri), col perimetro RLS su **entrambi** gli estremi come da regola del 2026-08-25 |
| **No, non è ammesso** | le due righe sono un **difetto di scrittura**: va trovato **chi le scrive** (una è di nove giorni fa, quindi il percorso è vivo) e chiuso con un `CHECK`/trigger; le righe si bonificano |
| **Sì ma solo in un caso** (es. DDT standalone senza ordine) | serve la **condizione**, e va scritta dove si vede — arco condizionato, o vincolo sul tipo ammesso |

⛔ **Non si sceglie leggendo il grafo**: due righe su 80 non dicono se sono la
regola o l'eccezione. Si sceglie leggendo **chi le scrive**, ed è la prima cosa
da misurare — è la stessa istruzione che ha evitato il difetto sull'arco `S`
(*«il legame va letto, non trasportato»*: prima si guarda a cosa serve la
colonna, poi la si usa).

### 2.4-bis. ⭐ Chi le scrive — letto il 2026-08-28

**Un handler di prima classe, con un nome, uno di cinque.**

La catena di scrittura è una sola e non ha rami: `HandlerDdt` →
`CommesseRepository.link_sorgente` → `vendite.fn_link_commessa_sorgente` →
`INSERT INTO vendite.commesse_sorgenti`.

| anello | cosa dice |
| --- | --- |
| `HandlerDdt`, in `commesse_source_handlers.py` | `sorgente_codice = "DDT_VENDITA"`, sottoclasse di `BaseSourceHandler` come gli altri quattro. **Non è un percorso laterale: è un handler registrato del push** |
| `link_sorgente` (BE) | **generica** — passa avanti il `sorgente_tipo_id` che l'handler le dà, senza sapere quale sia |
| `fn_link_commessa_sorgente` (DB) | **generica anch'essa** — nessuna whitelist di tipi: legge `target_table` e `key_selector` da `config.sorgenti` e normalizza la chiave. ⛔ **Il DB non ha mai detto che un DDT non può essere sorgente**: non c'è nessun vincolo da violare |

⭐ **Quindi la risposta alla domanda del §2.4 è «Sì, è ammesso»**, ed è una
risposta di **modello**, non un'inferenza dalle due righe: quelle due righe sono
il *prodotto* di un handler costruito apposta, non il residuo di qualcosa.
Il lavoro che ne segue è il **dodicesimo arco** `DDT → Commessa`.

⚠️ **E la chiave si legge, non si copia** — è la trappola che il §2.5 nomina.
Letto da `config.sorgenti` il 2026-08-28:

| sorgente | id | `key_selector` | `target_table` | è un nodo del grafo? |
| --- | ---: | --- | --- | --- |
| `PREVENTIVO` | 2 | **`uid`** | `vendite.preventivi` | sì |
| `CONTRATTO` | 4 | `id` | `vendite.contratti` | sì |
| `ORDINE_VENDITA` | 6 | `id` | `vendite.ordini` | sì |
| **`DDT_VENDITA`** | **8** | **`id`** | `vendite.ddt` | **sì** |
| **`ATTIVITA_CONSUMI`** | 12 | `id` | `vendite.attivita_consumi` | ⛔ **NO** |

Per il ramo nuovo la chiave è quindi `d.id::text`, come `E` e `F` e **non** come
`B`. Il modo giusto di saperlo è quello usato qui: leggere `key_selector`, non
guardare il vicino.

### 2.4-ter. ⛔ E il gemello che il §2.1 non poteva vedere

Gli handler sono **cinque**, non quattro. Il quinto è `HandlerConsumi`,
`sorgente_codice = "ATTIVITA_CONSUMI"`, e scrive nella stessa
`commesse_sorgenti` passando dalla stessa funzione generica.

⛔ **Ma `ATTIVITA_CONSUMI` non è un nodo del grafo**: `vw_documento_lineage_nodi`
ha otto rami e un consumo non è fra loro — non è un documento. Quindi per quelle
righe **non basta un arco**: mancherebbe prima il nodo da cui farlo partire.

⚠️ **Nella tabella del §2.1 non compare, e non è una prova che il caso non
esista**: è una specie che oggi non ha righe. Sono due difetti della stessa
famiglia — *un handler che scrive un legame che il grafo non sa rappresentare* —
di taglia molto diversa, e vanno tenuti distinti: il primo è un arco, il secondo
è la domanda se un consumo debba essere un nodo. **Il secondo non è di questo
cantiere**, ma va nominato qui perché è dove si troverà chi cercherà i gemelli.

### 2.5 ⚠️ Se la risposta è «sì», due cose da non ripetere

* la **chiave** dei rami `B`/`E`/`F` **non è la stessa** — `p.uid::text`,
  `o.id::text`, `c.id::text` — e un ramo scritto con la chiave copiata dal
  vicino **non dà errore**: azzera quel gruppo di archi. Il test **38** lo
  direbbe insieme al conteggio per lettera;
* il **perimetro RLS**: `commesse_sorgenti` ha `relrowsecurity = f` e non dà
  perimetro. Il ramo nuovo deve passare da `vendite.ddt` **e** da
  `vendite.commesse`, che la policy ce l'hanno entrambe. È la regola scritta in
  testa alla vista il 2026-08-25, e questo sarebbe il primo ramo a doverla
  rispettare per nascita invece che per correzione.

---

## 3. 🔴 Come un nodo FATTURA si presenta in lista

> **Arrivato qui dal §7-bis del brief dell'arco `S`**, che si è chiuso il
> 2026-08-26 e non poteva chiudersi *sopra* un difetto aperto. Trovato
> misurando la consegna in-app. Non è un
> difetto introdotto da questo cantiere: è un difetto **preesistente** che questo
> cantiere rende **strutturale**, ed è la ragione per cui va qui e non in §7.

### 3.1 Il fatto

Sulla riga del reso 24 la colonna «Transito» rende, oggi, il chip

> `→ [Fattura] 1 · IN_CORSO`

dove **`1` è la nota di credito 20024**. Il pgTAP **35** asserisce che l'arco `S`
arriva **sempre** a una `NOTA_CREDITO`: quindi su questa lista l'etichetta
sbagliata non è un caso limite, è **il caso**.

⛔ E la colonna esiste per rispondere a *«questo reso è già stato accreditato, e
con quale documento»* (§5-bis-b). Chiamare «Fattura» l'accredito è dire la cosa
sbagliata **proprio nel punto** per cui la colonna è stata seminata.

### 3.2 Perché il frontend non può rimediare da solo

La regola esiste già ed è una sola: `lineageDocumentoLabel(t, te, tipo, natura)`
— *la natura vince sul tipo quando c'è*. È stata scritta il 2026-08-21 per
esattamente questo motivo (`vendite.fatture` è **una** tabella; fattura e nota di
credito si distinguono solo per `natura_doc_id`) ed è già usata dai chip di
`DocumentoCollegamentiBar` e dalle tappe della dialog.

🔴 **Alla cella della lista quel dato non arriva, e non può arrivare.** Il
pannello lo ricava in `VenditeRepository.get_lineage_nodo`:

```sql
LEFT JOIN vendite.vw_documento_lineage_nodi nfr
       ON nfr.tipo_id = l.frontiera_tipo_id
      AND nfr.uid     = l.frontiera_uid      -- ⬅ la chiave
```

Il join ha bisogno di **`frontiera_uid`**. `vw_documento_lineage` ce l'ha; le
**sei** `vw_*_lista` **no** — proiettano `frontiera_tipo_id`, `frontiera_codice`,
`frontiera_stato_codice_interno`, `frontiera_fase`, e la chiave del nodo si ferma
lì. Verificato eseguendo il join dalla lista: `ERRORE: la colonna
v.frontiera_uid non esiste`.

⛔ **Quindi non c'è un rimedio BE onesto**, e va detto perché la tentazione c'è:
si potrebbe joinare `vendite.fatture` + `config.nature_doc_fiscale` filtrando su
`frontiera_tipo_id = FATTURA`. Sarebbe **il tipo cablato nel backend** — cioè la
cosa che il grafo esiste per non fare — moltiplicata per sei repository, e
divergerebbe dal pannello alla prima modifica di uno dei due.
[[feedback_no_quick_fix_soluzione_assoluta]].

### 3.3 La misura

Contati i nodi la cui frontiera è una nota di credito, in contesto operatore, il
2026-08-26:

| nodo | quanti | dove si vede |
| --- | ---: | --- |
| `ORDINE_VENDITA` | 1 | lista ordini, colonna «Transito» → **oggi scrive «Fattura»** |
| `RESO_VENDITA` | 1 | lista resi, colonna «Transito» → **il caso di questo cantiere** |
| `COMMESSA` | 1 | drawer commessa (pannello, già corretto) |
| `FATTURA` | 1 | la NC frontiera di sé stessa |

⚠️ **Uno su quattro è già a video oggi**, sulla lista ordini, dal 2026-08-21. Non
se n'è accorto nessuno perché è **una riga**; sul reso diventa la regola.

### 3.4 La richiesta

**Esporre `frontiera_natura_doc_codice` su `vendite.vw_documento_lineage`.**

> ✅ **SCRITTA il 2026-08-28 — `20260828-22`.** Provata in `BEGIN`/`ROLLBACK`,
> **non applicata**. Presidio: pgTAP **40**.

* ⛔ **Correzione a questa richiesta: il join NON va aggiunto, c'è già.** La
  frase qui sotto diceva *«è un `LEFT JOIN` sul nodo di frontiera»* ed era vera
  a metà: la CTE `frontiera` fa **già** `LEFT JOIN vw_documento_lineage_nodi nd`,
  perché le serve `nd.pipeline_rank` per il tie-break del `ROW_NUMBER()`.
  L'unica cosa che mancava era **portare avanti una colonna che quel join già
  vedeva**. Costo reale: una colonna, zero accessi in più.
  ⭐ Vale come regola: prima di aggiungere un join a una CTE, guardare **cosa
  quella CTE già tocca per altri motivi**.
* *(Testo originale, superato:)* la sorgente è già lì: la CTE della frontiera
  conosce `frontiera_tipo_id` e `frontiera_uid`, e `vw_documento_lineage_nodi`
  porta già `natura_doc_codice` (rev 2026-08-20). È un `LEFT JOIN` sul nodo di
  frontiera, lo stesso che il BE scrive a mano in `get_lineage_nodo`.
* ⚠️ **E la colonna sta in ULTIMA posizione**, non accanto alle sorelle
  `frontiera_*`: `CREATE OR REPLACE VIEW` può solo **appendere**, e metterla in
  mezzo vorrebbe dire `DROP … CASCADE` delle viste di lista che leggono questa.
  Chi rilegge l'elenco delle colonne non ci veda un disordine da sistemare.
* ⚠️ **`LEFT`, non `JOIN`**: `natura_doc_id` è nullable su `vendite.fatture`, e
  sugli altri sette tipi di nodo la natura è NULL **ed è corretto** (la natura è
  un asse diverso dal tipo, ed esiste solo per le fatture).
* ✅ **Poi le viste di lista la portano avanti** come già fanno con
  `frontiera_fase` — fatto il 2026-08-29 con `20260829-01`.
  ⛔ **Ed erano SETTE, non sei**: c'è anche `vw_fatture_lista`, che porta le
  stesse quattro colonne `frontiera_*` delle sorelle. La settima non ha (ancora)
  la colonna «Transito» a catalogo, quindi il difetto lì non si vedeva — ed è
  esattamente il motivo per cui entra: il giorno in cui qualcuno la aggiunge, il
  chip nasce con l'etichetta sbagliata **dove nessuno guarda**.
  ⚠️ **E i repository non la proiettano affatto**: fanno `SELECT v.*`, quindi la
  colonna arriva al frontend da sola. La riga *«i sei repository la proiettano»*
  descriveva un lavoro che non esiste.

⭐ **E la ragione dichiarata nel `COMMENT` va aggiornata di conseguenza**, perché
è la seconda volta che quella frase è vera a metà. Il `20260825-20` ha corretto
*«varrebbe sempre NULL»* in *«il consumatore la ricava per conto suo»*. Ma il
consumatore che la ricava è **uno**, e i consumatori che non possono sono
**sei**: la frase giusta diventa *«la colonna c'è perché la chiave del nodo di
frontiera non esce dalla summary, e senza di lei ogni lista chiama Fattura una
nota di credito»*.

### 3.5 ✅ Cosa fa il BE/FE — fatto il 2026-08-29

> **Chiuso**, commit `dd562af68`. Piano e registro completo in
> [piano-be-fe-lineage-natura-frontiera-liste.md](piano-be-fe-lineage-natura-frontiera-liste.md).
> ⚠️ Due dei quattro punti qui sotto si sono rivelati diversi da come erano
> scritti — il **1** non aveva lavoro dentro (`SELECT v.*`) e il **4** non era
> scrivibile nella forma richiesta (vedi sotto). Restano com'erano perché la
> differenza fra ciò che si prevede e ciò che si trova è l'informazione utile.

*(Testo originale:)* **Niente, e aspetta**
([[feedback_be_fe_attende_prerequisiti_db]]). Il lavoro a valle è piccolo e già
scritto qui, così quando la colonna arriva è un giro solo:

1. sei repository: `v.frontiera_natura_doc_codice` nella `SELECT`;
2. `LineageFrontieraChip`: prop `naturaCodice` e `lineageDocumentoLabel` al posto
   di `lineageTipoLabel` — **la funzione esiste già**, cambia la chiamata;
3. le **sei** liste passano la prop — ⚠️ e vanno passate **tutte e sei**: una
   prop dichiarata e non passata è un cancello che sembra esserci
   ([[feedback_bb_legge_non_trasporta]]);
4. un test nel presidio delle sei liste, gemello di
   `test_ogni_lista_decodifica_il_tipo_della_frontiera`.

⚠️ **Le chiavi i18n ci sono già tutte** (`vendite.lineage.natura_nota_credito`,
`natura_fattura`, `natura_nota_debito`, in `it.json` e `en.json`): non c'è niente
da tradurre, il giorno che si accende. ✅ **Verificato: era vero.**

#### ⭐ Cosa è andato diversamente da come è scritto qui sopra

| punto | previsto | trovato |
| --- | --- | --- |
| **1** | «sei repository: la colonna nella `SELECT`» | ⛔ **Nessun lavoro**: tutti e sette fanno `SELECT v.*` e la colonna arriva da sola |
| **2** | prop + `lineageDocumentoLabel` al posto di `lineageTipoLabel` | ✅ come previsto. In più: `lineageTipoLabel` **non è più esportata** — senza consumatori restava l'unica porta da cui il difetto rientra |
| **3** | «le sei liste passano la prop» | ✅ e toccavano comunque quella riga: il **tipo** ha cambiato nome col `20260829-02`, e senza quel rename il chip sarebbe rimasto **muto** (il gate è su `tipoCodice`) |
| **4** | «un test gemello di `test_ogni_lista_decodifica_il_tipo_della_frontiera`» | ⛔ **Non scrivibile in quella forma**: con `SELECT v.*` nel sorgente del repository non c'è niente da cercare, e un test scritto per analogia sarebbe stato verde a vuoto. Il presidio si è spostato dove la traduzione avviene davvero — i `.vue` — e il vecchio test si è **ribaltato**: da «ogni repository decodifica» a «nessuno ridecodifica» |

---

### 3.6 ⚠️ E il secondo difetto della stessa famiglia: il numero nudo

La stessa colonna «Transito» mostra **`1`** e non `NC0000001`, perché
`vw_documento_lineage_nodi` espone `fatture.numero` come `codice` del nodo,
mentre per gli altri sei tipi il `codice` è già parlante (`DDT0000031`,
`ORD0000227`). Misurato sul reso 24 all'apply del 2026-08-25.

⭐ **Sede identica**: il nodo. Chi mette mano a `vw_documento_lineage_nodi` per
la natura guardi anche questo — sono un giro solo.

⛔ **Ma non è dello stesso giro del `20260828-22`, e il motivo è che ha una
domanda dentro.** Letto il 2026-08-28: l'identità di una fattura sono **tre**
colonne — `anno` (smallint), `serie` (varchar), `numero` (bigint), tutte
nullable finché il documento non è numerato — e **non esiste in DB un codice
parlante canonico** per una fattura. `vw_fatture_lista` espone le tre colonne
separate e lascia comporre al consumatore; cinque funzioni SDI compongono a modo
loro un `codice_doc` come `anno || serie || numero`.

⚠️ **Quindi «mostrare `NC0000001`» non è un fix, è una decisione**: *qual è il
codice parlante di una fattura, e chi lo possiede*. Se si sceglie di comporlo nel
nodo, quella diventa la **settima** forma in giro per il progetto, e le altre sei
restano dove sono. La cura onesta è una sola sede che lo dichiara — e va decisa
prima, non dentro un changeSet che parla di natura.

#### 3.6-bis ⭐ Lo stato della decisione al 2026-08-29, e l'asimmetria in una riga

✅ **Tid ha deciso la metà «chi lo possiede»: UNA SOLA SEDE.**
✅ **E poche ore dopo anche l'altra metà, «che forma ha»: vedi §3.6-ter.**
⛔ Resta la **bonifica** delle forme esistenti, che è il lavoro vero.

**L'asimmetria, letta dalla struttura e non dai dati.** Per DDT, ordine, reso e
preventivo la colonna `numero` **è** il codice parlante: un `varchar`, del tipo
`DDT0000031`. Per la fattura `numero` è un **`bigint`**, cioè un contatore, e
l'identità sono tre colonne — `anno` (smallint), `serie` (varchar), `numero` —
**tutte e tre nullable** finché il documento non è numerato. Due esempi reali
letti il 2026-08-29:

| documento | `anno` | `serie` | `numero` |
| --- | --- | --- | --- |
| una fattura | 2026 | `VX2` | 103 |
| una nota di credito | 2026 | **vuota** | 1 |

⛔ **Quindi il `1` a video non è sbagliato: è ambiguo.** Nello stesso anno
possono esistere una fattura `1` e una nota di credito `1`, e in lista sono
indistinguibili. ⚠️ E la **serie vuota** non è un caso limite: è la riga qui
sopra, cioè proprio la nota di credito del §3.1.

**Le due domande da chiudere:**

1. **Che forma ha**, su una riga sola — e cosa si scrive quando la serie è vuota
   e quando il documento **non è ancora numerato** (prima di «Rendi definitive»
   le tre colonne sono NULL, e il chip ha già la sua fallback `non_numerato`).
2. **Quale delle forme esistenti diventa quella ufficiale**, o se è nuova.

#### 3.6-ter ✅ La forma, decisa da Tid il 2026-08-29

> **`numero - serie`, senza anno.** In prosa: *«fattura n. 1 - VX2 del
> 21/08/2026»* — il numero e la serie compongono il codice, **la data resta un
> dato a sé** e sta accanto, non dentro.

| caso | cosa esce |
| --- | --- |
| fattura `2026 \| VX2 \| 103` | `103 - VX2` |
| nota di credito `2026 \| serie vuota \| 1` | **`1`** — nessun trattino orfano |
| non ancora numerata (le tre colonne NULL) | **NULL**, così il consumatore usa la fallback che ha già (`vendite.lineage.non_numerato` sul chip) |

⛔ **L'anno esce di proposito**: la regola dichiarata è *«accanto c'è sempre la
data»*, e ripetere l'anno dentro il codice lo direbbe due volte.

**La domanda che ne è nata, e la sua risposta.** Verificato il 2026-08-29
leggendo la struttura: nel lineage **non viaggia nessuna data** — non
`vw_documento_lineage_nodi`, non la frontiera della summary, non
`fn_documento_lineage`, non il chip. Cioè la premessa della regola è vera nelle
liste e nei drawer (dove la data è una colonna della riga) e **falsa proprio nei
due posti di questo cantiere**.

> ✅ **Decisione di Tid: la data NON entra nel chip. Se serve, sta fuori.**
> Niente colonna data nel grafo.

⚠️ **La conseguenza, dichiarata invece che scoperta dopo**: nella colonna
«Transito» e nelle tappe del pannello il codice viaggia **senza data**, quindi
due documenti con la stessa natura, lo stesso numero e nessuna serie sono
indistinguibili lì. È un'ambiguità **accettata**, non un difetto rimasto aperto.

⭐ **E il §3.6 vale molto meno di quanto sembrava**, il che spiega perché non
serviva farlo di fretta: la voce 3 gli ha già tolto il pezzo che faceva danno.
Il chip diceva `→ Fattura 1` su un accredito — **la parola sbagliata**; oggi dice
`→ Nota di credito 1`. Quel che resta non è più «fattura o nota?» ma un numero
incompleto fra documenti della stessa natura.
⚠️ E sul documento che ha aperto la voce non cambia **niente**: la nota di
credito del reso 24 ha la **serie vuota**, quindi col formato nuovo resta `1`.

**Cosa resta da fare, ed è poco:** una **sola sede** in DB che compone
`numero - serie` accanto alla fattura, e il nodo del grafo che la legge al posto
di `fatture.numero`. Le sei composizioni esistenti si riportano su quella —
⛔ **tranne quella SDI**, che è una stringa per una macchina e va dichiarata
deliberatamente diversa (§3.6-bis).

⚠️ **E una distinzione da non perdere**: la composizione delle funzioni SDI
(`COALESCE(anno) || COALESCE(serie) || COALESCE(numero)`, **senza separatore** →
`2026VX2103`) è una stringa **per una macchina**, non per una persona. Unificarla
con l'etichetta umana sembra economia e non lo è: sono due contratti con due
committenti diversi, e il giorno che uno dei due cambia si scopre di averli
legati. Va dichiarata **deliberatamente diversa**, non fusa.

---

## 3-bis. 🟠 La descrizione della vista archi non nomina `T` — e si contraddice da sé

> **Ereditata il 2026-08-28** dal cantiere
> [brief-db-ddt-riconsegna-eredita-testata.md](../work-done/brief-db-ddt-riconsegna-eredita-testata.md)
> (§13.5 e §14.2), che l'ha trovata chiudendosi. Non è di lì: quel cantiere ha
> **aggiunto** l'arco, questo possiede la vista.

### 3-bis.1 Il fatto

Il changeSet `20260828-05` aggiunge l'arco **`T`** (reso → DDT di ri-consegna)
alla `UNION ALL` di `vendite.vw_documento_lineage_archi`, ma **non contiene
nessun `COMMENT ON VIEW`**. La descrizione della vista è quindi rimasta quella
del 2026-08-25:

> *«grafo archi normalizzato A-H + R e N (rami di ritorno) + S»*

**Senza `T`.** E quella frase non è un ornamento: è ciò che la doc auto-gen
stampa in cima alla pagina della vista, cioè la prima riga che legge chi vuole
sapere **quali archi esistono**.

### 3-bis.2 ⛔ Perché non è una svista cosmetica

Due ragioni, e la seconda è quella che la rende una voce e non una nota.

**1 · La pagina si contraddice da sola.** La doc **manuale** — scritta il
2026-08-28, `include-markdown` in cima alla stessa pagina — dichiara:

> *«**`arco`**: lettera diagnostica `A`..`H`, `R`, `N`, `S`, `T` — **dodici**
> dal 2026-08-28»*

Undici lettere sopra, dodici sotto, sulla stessa schermata. Chi legge non ha
modo di sapere quale delle due frasi sia la vecchia — e la più autorevole in
apparenza (la descrizione ufficiale della vista) è proprio quella sbagliata.

**2 · Il vocabolario è dichiarato CHIUSO, e presidiato.** Un pgTAP enumera le
lettere ammesse e **fallisce apposta** a ogni arco nuovo, per costringere chi lo
aggiunge a passare di lì (è il cricchetto che ha preso la regressione del §11 di
quel brief). Un elenco di riferimento che ne nomina **una in meno** di quante il
`WHERE` ne produce toglie valore al cricchetto: il prossimo che allarga
l'elenco legge la descrizione per sapere da dove parte, e parte da un numero
sbagliato.

### 3-bis.3 La richiesta

> ✅ **SCRITTA il 2026-08-28 — `20260828-23`.** Provata in `BEGIN`/`ROLLBACK`,
> **non applicata**.

Un `COMMENT ON VIEW vendite.vw_documento_lineage_archi` che nomini `T` insieme
alle altre. Nessuna riga di logica, nessun test nuovo: la doc auto-gen si
rigenera e la contraddizione sparisce.

⚠️ **Non ha aspettato le voci 1 e 2**, come invece diceva la riga qui sopra
(*«nello stesso changeSet che tocca la vista»*, superata). Due ragioni: quelle
due voci hanno una decisione davanti e non si sa quando arrivano, e un
`COMMENT ON VIEW` **da solo** non richiede il `CREATE OR REPLACE` — cioè non
corre il rischio di azzerare `security_invoker`, che è una reloption invisibile
in `pg_get_viewdef`. Aspettare avrebbe tenuto in piedi una frase falsa per
guadagnare un changeSet in meno.

⭐ E il testo nuovo non si limita ad aggiungere la lettera: **dichiara il numero
e il presidio** — *«DODICI lettere dal 2026-08-28, e il vocabolario è CHIUSO: il
pgTAP 13 le enumera e fallisce apposta a ogni arco nuovo»*. Chi allarga l'elenco
trova scritto, nella descrizione stessa, che deve tornare a riscriverla.

⚠️ **La regola che questa voce lascia scritta**: un `CREATE OR REPLACE VIEW` che
cambia *cosa la vista produce* e non tocca il suo `COMMENT` lascia indietro
l'unica documentazione che si rigenera da sé — ed è la sola che nessuno pensa a
rileggere, proprio perché «si aggiorna da sola».

---

## 3-ter. ⭐ L'estrazione che la voce 3 ha reso evidente — il tipo viaggiava in id

> **Nata il 2026-08-29 aprendo le viste per il `20260829-01`, decisa da Tid,
> consegnata dal team DB nello stesso giro** (`20260829-02`). Non era nel brief,
> ma è di qui: è la **stessa vista** e la stessa specie di difetto.

### 3-ter.1 Il fatto

Il grafo esponeva il tipo di un nodo **solo come `tipo_id`**, e ogni consumatore
che voleva il codice si scriveva lo stesso `LEFT JOIN config.sorgenti`: **undici
volte** nel backend — sette repository di lista, due in `get_lineage_nodo`, due
in `list_lineage_passaggi`.

⛔ **E una di quelle undici era già stata dimenticata.** La lista resi, nata il
2026-08-25, il join non ce l'aveva: colonna a catalogo, dato a database, e a
video **niente** — senza un errore. Il presidio Python che esiste da allora
serviva a sorvegliare quella copia, cioè presidiava il **sintomo**.

### 3-ter.2 ⛔ Perché non è «erano tante»

L'argomento non è il conteggio, ed è il motivo per cui la richiesta regge:
**nella stessa vista la *natura* usciva già in chiaro come codice, e il *tipo*
no**. Due attributi dello stesso nodo, due convenzioni diverse. La voce 3 ha
aggiunto la natura come `codice` accanto a un tipo che restava un id — cioè ha
reso l'asimmetria visibile invece di crearla.

⚠️ E il `from_tipo_id` della voce 1 era la stessa specie: un id di catalogo usato
come se fosse una chiave stabile.

### 3-ter.3 Cosa è stato fatto

`tipo_codice_interno` e `frontiera_tipo_codice_interno` sul grafo e sulle sette
viste di lista, e — nello stesso changeSet — il **suffisso `_interno` reso
canonico** anche sulle nature (`natura_doc_codice` → `natura_doc_codice_interno`).

| | prima | dopo |
| --- | ---: | ---: |
| join scritti a mano nei 7 repository di lista | 7 | **0** |
| in `get_lineage_nodo` | 2 | **0** |
| in `list_lineage_passaggi` | 2 | **2** |

⚠️ **I due che restano non sono un residuo**: `fn_documento_lineage` espone
`from_tipo_id`/`to_tipo_id` e non i codici, e quei join servono anche per
`key_selector`. Una sede, non sette. Da valutare quando quella funzione si
riapre.

⭐ **Tolto anche un join che non era una decodifica**: `get_lineage_nodo` si
ricavava la natura della frontiera con un `LEFT JOIN vw_documento_lineage_nodi`
suo. Dal `20260828-22` la vista la porta, quindi erano **due sedi** della stessa
regola — e la seconda ricalcolava dall'esterno una frontiera che la CTE della
vista risolve col tie-break su `pipeline_rank`. Confrontate le due strade su
tutti i **439** nodi del grafo con `IS DISTINCT FROM`: **0 divergenze** su **82**
righe con una natura non nulla.

### 3-ter.4 ⛔ E il rename ha rotto quattro cose, di cui una in silenzio

Il `20260829-02` ha rinominato `natura_doc_codice` **anche dove il backend la
leggeva**, e la suite Django era **verde su tutte e quattro**: `get_lineage_nodo`
è mockato in ogni test che lo tocca.

| cosa | sintomo |
| --- | --- |
| `get_lineage_nodo` e `list_lineage_passaggi` | **500** sul pannello «Passaggi» di tutti e **sette** i domini |
| filtro per natura della lista fatture | **500** |
| il Tag della natura su **ogni riga** della lista fatture | **spariva, senza errore** |

⛔ **L'ultima è la peggiore**, e vale come regola generale: un rename a DB rompe
**due specie** di consumatore e solo la prima fa rumore. Chi legge la colonna in
una `WHERE` dà 500 e qualcuno lo segnala; chi la legge in una **cella** smette di
disegnare, e non lo segnala nessuno.

⚠️ **Trovate ri-eseguendo l'SQL estratto dai file sul database vero**, non dalla
suite ([[feedback_rinomina_db_binding_mockato]]).

---

## 4. Cosa NON è di questo brief

* L'arco `S` e il perimetro RLS: **fatti e applicati** (`20260825-19/20/21`).
* Il BE/FE della lista resi: **fatto** il 2026-08-26 (§5 DB-F.4 del brief madre).
* Il raggruppamento `MAN:<commessa>` e l'ipotesi «una nota per reso»: §4 del
  brief madre, decisione presa e da non riaprire senza motivo.
* `fn_accredita_riga_reso` che passa `sorgente => NULL` **senza dirlo**: il
  valore è giusto, manca il commento di due righe. Voce minore del §7 madre,
  non merita un cantiere: si chiude alla prossima modifica di quella funzione.

---

## 5. Registro

### 2026-08-26 · Nascita

Estratto dal §7 del brief dell'arco `S` per la voce **L7.5**, con le misure
rifatte sul DB vivo in contesto operatore
(`script.fn_pgtap_set_contesto_operatore` — ⚠️ senza, `zeroerp_app` legge **zero**
righe e lo zero somiglia a un dato).

⭐ **La misura ha cambiato la seconda voce.** Il brief madre chiedeva *«un DDT è
sorgente di commessa, o quelle due righe sono un residuo?»*. Le quattro misure
del §2.2 rendono «residuo» l'ipotesi meno probabile: `ROOT`, sorgente unica, DDT
esistenti, una riga di nove giorni fa. La domanda resta aperta, ma non è più
neutra — e ciò che intanto è certo è che **due commesse vive dichiarano di non
avere origine**, che è un'affermazione falsa fatta dal grafo.

**Nessun file scritto, nessuna migrazione, nessuna decisione presa.**

### 2026-08-28 · Arriva la quarta voce

Il cantiere `brief-db-ddt-riconsegna-eredita-testata` si è chiuso e ha lasciato
qui il **§3-bis**: la descrizione di `vw_documento_lineage_archi` non nomina
l'arco `T`. ⭐ È entrata **qui** e non è morta con l'archiviazione di quel brief
perché la sede di una voce è **l'oggetto che tocca**, non il cantiere che l'ha
vista: quella vista è di questo file, che la apre già per le voci 1 e 2.

---

### 2026-08-28 · Le due voci senza domande sono scritte, e la seconda ha una risposta

**Scritti — provati, NON applicati.**

| file | voce | cosa fa |
| --- | --- | --- |
| `20260828-22-update-vw-documento-lineage-frontiera-natura-mctit.yaml` | **3** | `CREATE OR REPLACE` della summary: espone `frontiera_natura_doc_codice` + `COMMENT` riscritto |
| `20260828-23-comment-vw-documento-lineage-archi-arco-t-mctit.yaml` | **4** | solo `COMMENT ON VIEW` sulla vista archi: nomina `T`, dichiara «dodici» e il cricchetto |
| `db/pgtap/vendite/test-documento-lineage-v1.sql` | **3** | `plan(39) → plan(40)`, colonne del test **7**, e il test **40** nuovo |

**La prova.** L'SQL **estratto dai due YAML** (non ricopiato) eseguito in
`BEGIN`/`ROLLBACK`: le due viste si creano, `security_invoker=on` sopravvive, la
colonna nuova esce in posizione 26 e la suite dà **40/40 verdi, nessuno skip**.
⚠️ **Girata da owner**, quindi il test **38** — il perimetro RLS — in quella
corsa è verde per costruzione: quello vale solo alla suite vera, come
`zeroerp_app`, dopo il migrate.

⭐ **Il test 40 non è una tautologia, ed è il motivo per cui esiste.** Ri-deriva
la natura per la strada opposta a quella della vista: rilegge il nodo di
frontiera dalla sua **chiave** e confronta. L'errore che prende è quello
plausibile — esporre la natura del **nodo proprio** al posto di quella della
**frontiera**: stesso tipo, nessun errore alla creazione, e su ogni nodo che è
frontiera di sé stesso (la maggioranza) i due valori coincidono. Sarebbe verde
ovunque tranne che sulle righe per cui la colonna esiste.
⚠️ E usa `IS DISTINCT FROM`, non `<>`: la natura è NULL su sette tipi di nodo su
otto: con `<>` quelle righe non entrerebbero **mai** nel conteggio, e il test
sarebbe verde anche se la colonna valesse sempre NULL.

**La misura che ha risposto al §2.4** (§2.4-bis): la catena di scrittura è una
sola — `HandlerDdt` → `link_sorgente` → `fn_link_commessa_sorgente` — e
`HandlerDdt` è un **handler registrato del push**, uno di cinque, non un
percorso laterale. Né il BE né il DB hanno una whitelist di tipi: **il database
non ha mai detto che un DDT non può essere sorgente di commessa**.
⭐ La risposta «sì, è ammesso» viene quindi dal **modello** — da chi scrive e da
come è costruito — e non dalle due righe: quelle sono il prodotto dell'handler,
non un residuo.

⛔ **E il gemello** (§2.4-ter): il quinto handler è `HandlerConsumi`,
`ATTIVITA_CONSUMI`, che scrive nella stessa tabella ma **non è un nodo del
grafo**. Oggi non ha righe, e questo non prova niente: è un difetto della stessa
famiglia e di taglia diversa, e non è di questo cantiere.

**Restano aperte** la voce **1** (§1.3, due domande) e la scrittura della voce
**2** (l'arco, ora che la domanda ha risposta), più il §3.6, che si è rivelato
una decisione e non un fix.

*(Superato in giornata: le voci 1 e 2 sono state decise e scritte poche ore
dopo — sotto.)*

### 2026-08-28 · Le decisioni prese, e le altre due voci scritte

**Le due domande di modello, decise.** Il §2.4 dalla lettura di **chi scrive**
(§2.4-bis); il §1.3 con la cura **(b)**, il rango dichiarato sull'arco (§1.6).
⭐ Nessuna delle due è stata decisa **contando righe**: la prima leggendo la
catena di scrittura, la seconda dichiarando una scala sul flusso.

| file | voci | cosa fa |
| --- | --- | --- |
| `20260828-24-…-archi-sorgente-ddt-e-rango-mctit.yaml` | **1** e **2** | arco `U` (DDT → Commessa, tredicesima lettera) + colonna `rango_origine` |
| `20260828-25-…-lineage-root-rango-mctit.yaml` | **1** | la CTE `inc` ordina su `rango_origine` invece che su `from_tipo_id` |
| `test-documento-lineage-v1.sql` | **1** e **2** | `plan(40) → plan(44)`, test **6** e **13** allargati, test **41**…**44** nuovi |

⭐ **Perché 1 e 2 in un `CREATE OR REPLACE` solo**: toccano la stessa vista, e
riscriverla due volte in due giorni è il modo di perdere `security_invoker` —
una reloption invisibile in `pg_get_viewdef`, che un `CREATE OR REPLACE` che non
la ripete **azzera senza errori**.

#### La prova — round-trip sul RISULTATO, non sul testo

L'SQL **estratto dai quattro YAML** eseguito in `BEGIN`/`ROLLBACK`, con una
fotografia degli archi prima e dopo:

| verifica | atteso | ottenuto |
| --- | --- | --- |
| archi preesistenti **spariti** | 0 | **0** |
| archi **comparsi** oltre a `U` | 0 | **0** |
| archi con `rango_origine` NULL | 0 | **0** (13 lettere, tutte con rango) |
| archi `U` prodotti | i 2 legami del §2.1 | **2**, entrambi `ruolo = ROOT` |
| `security_invoker` sulle due viste | `on` | **`on`** |
| nodi il cui **root cambia** | solo le 2 commesse | **solo le 2 commesse** |
| suite pgTAP | 44/44 | **44/44, nessuno skip** |

⭐ **L'ultima riga è la più informativa, e non è il risultato che ci si
aspetterebbe**: il passaggio da `from_tipo_id` a `rango_origine`, da solo, non
sposta **nessun** root. Sul DB di sviluppo di oggi l'ordine accidentale degli id
**coincide** con la scala dichiarata su ogni nodo. ⚠️ E questo non dice «allora
non serviva»: dice che il difetto era **invisibile**, che è la ragione per cui
era sopravvissuto dal 2026-07-14.

#### ⭐ La prova di MUTAZIONE, e un buco trovato nel presidio

Un test che non sa fallire non presidia niente. La CTE `inc` è stata riscritta
in quattro modi sbagliati, rigirando la suite ogni volta:

| mutazione | test **43** | test **44** |
| --- | --- | --- |
| `rango_origine DESC` — la scala letta al contrario | 🔴 **ROSSO** | verde |
| `ORDER BY` senza `(ruolo='ROOT')` — la dichiarazione ignorata | 🔴 **ROSSO** | verde |
| ritorno a `from_tipo_id` — il vecchio id di seed | 🟢 verde | verde |
| **un solo** `array_agg` disallineato dagli altri due | 🟢 verde | 🔴 **ROSSO** |

⛔ **La quarta riga ha trovato un buco vero**, ed era nel presidio che avevo
appena scritto. Il test 43 fa un `JOIN` sull'arco scelto e **conta le
violazioni**: un root composto a pezzi — il tipo da un arco, l'uid da un altro —
non trova nessun arco, quindi il nodo **esce dal join** e smette di essere
contato. ⚠️ *Un test che conta i cattivi diventa muto proprio quando il dato è
così rotto da sparire dal conteggio* — è la stessa specie del
[[feedback_test_ordine_relativo_passa_se_manca]]. Da lì il **44**, che conta al
rovescio: parte dai nodi che **dichiarano** un root e pretende che l'arco esista.

⚠️ **La terza riga resta verde ed è dichiarata tale nel file**, come vuole la
regola zero: è un **presidio**, non una riproduzione. Diventerà rosso il giorno
in cui l'ordine degli id divergerà dalla scala — che è il giorno per cui esiste.

#### Cosa resta

* **§3.6** — il numero nudo: è una **decisione**, non un fix (una fattura non ha
  un codice parlante canonico in DB: `anno` + `serie` + `numero`, tutti
  nullable). Non tocca nessuno dei quattro changeSet.
* **Il gemello `ATTIVITA_CONSUMI`** (§2.4-ter): altro cantiere, e prima di un
  arco servirebbe un **nodo**.
* ~~⛔ **Il migrate**: quattro changeSet e un file pgTAP, **scritti e provati, mai
  applicati**.~~ ✅ **Superato il 2026-08-29**: applicati, più altri due
  (`20260829-01/02`). Vedi la voce sotto.

### 2026-08-29 · Applicato, e la voce 3 arriva a video

> ⚠️ **Registrato dal lato BE/FE** (autorizzazione di Tid): il lavoro DB di
> questa giornata è del team, il migrate l'ha fatto il team, qui si scrive solo
> ciò che è stato **verificato** — nomi di colonna letti da
> `information_schema`, changeSet letti da `DATABASECHANGELOG`, SQL rieseguito
> in contesto operatore.

**Il migrate è passato.** I quattro changeSet del 28/08 risultano in
`DATABASECHANGELOG`, e con loro `20260829-01` (la colonna sulle **sette** viste
di lista, coda del §3.4) e `20260829-02` (il §3-ter: `tipo_codice_interno` nel
grafo e il suffisso `_interno` canonico).

**Le quattro voci, verificate una per una:**

* **1** — `rango_origine` in vista. Nessun lavoro BE/FE: la regola vive dov'è
  scritta.
* **2** — misurato in contesto operatore: `CMM-…c6a64e` e `CMM-…b9946f` hanno
  `n_sorgenti = 1` e root `DDT0000030` / `DDT0010839`. **Le due commesse hanno
  smesso di dichiarare di non avere origine**, ed è ciò che la voce chiedeva.
* **3** — DB + BE + FE, commit `dd562af68`. I quattro nodi con una nota di
  credito come frontiera sono **esattamente** i quattro che il §3.3 aveva
  contato il 26/08 (`ORDINE_VENDITA`, `RESO_VENDITA`, `COMMESSA`, `FATTURA`).
* **4** — `COMMENT` applicato, la doc auto-gen non si contraddice più.

⭐ **E il §3-ter è nato da qui**: aprendo le viste per la voce 3 si è visto che
la natura usciva come **codice** e il tipo come **id**. Undici decodifiche
scritte a mano nel backend sono diventate due.

⛔ **Resta aperto solo il §3.6**, e la metà «chi lo possiede» è decisa: **una
sola sede**, e in giornata è arrivata anche la **forma**: `numero - serie`,
senza anno, con la data dichiaratamente **fuori** dal codice (§3.6-ter). Da qui
in poi il §3.6 non è più una domanda ma un lavoro corto: una sede che la compone
e il nodo che la legge.

⚠️ **Una lezione da questo giro, e non è tecnica.** Questo brief ha detto
*«provati, NON applicati»* per **due giorni dopo** che erano stati applicati.
È lo stesso difetto della **voce 4** — un testo di riferimento che nessuno
rilegge — su un documento che quella voce l'aveva appena diagnosticata negli
altri. *La riga di stato di un cantiere vivo invecchia più in fretta di
qualunque `COMMENT`, e non ha nessuna doc auto-gen che la rigeneri.*

---

{% include-markdown "signature-core.md" %}
