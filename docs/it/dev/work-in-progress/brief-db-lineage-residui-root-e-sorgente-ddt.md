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
> **Stato.** 2026-08-26 — analisi e misure. **Nessun file scritto, nessuna
> migrazione.** Due domande di modello prima di qualunque riga di SQL (§1.3 e
> §2.4); la terza voce invece non ha domande aperte — la richiesta è scritta
> (§3.4).
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

## 0. Le tre voci in una riga

| # | Cosa | Gravità | Chi lo vede oggi |
| --- | --- | --- | --- |
| **1** | Il `root` di un nodo con più sorgenti si sceglie su `from_tipo_id`, cioè su un **id di `config.sorgenti`** e non su una chiave stabile | 🟠 fragilità silenziosa, nessun effetto oggi | nessuno — finché gli id non cambiano |
| **2** | `commesse_sorgenti` ha righe **`DDT_VENDITA`** che non producono nessun arco: quelle commesse risultano **senza origine** nel grafo | 🔴 dato vero non rappresentato | chi apre il pannello «Passaggi» di quelle due commesse, e la colonna «Transito» dei due DDT |
| **3** | La colonna «Transito» **chiama «Fattura» una nota di credito**, e mostra il numero **nudo** (`1`): la natura e il codice parlante non escono dalla summary | 🔴 dice la parola sbagliata | **ogni** operatore che guarda la lista resi o la lista ordini |

⭐ **Le tre hanno una cosa in comune, ed è il motivo per cui stanno insieme**: la
cura sta **sul nodo o sull'arco**, mai sulle sette viste di lista che li
proiettano. Chi apre `vw_documento_lineage_nodi` / `vw_documento_lineage` le
sistema in un giro solo.

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

### 1.5 Il presidio che manca

Nessun pgTAP oggi asserisce niente sul `root` di un nodo multi-sorgente. Qualunque
cura scelta, serve un test che dica **la regola** e non il dato di oggi (lezione
del rilievo 3 del §0.2 del brief madre): *«a parità di `ruolo`, il `root` di un
nodo è ⟨la regola⟩»*, seed-agnostico.

---

## 2. 🔴 Due commesse dichiarano di non avere origine

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
[collaudo-in-app-nota-credito-resi.md](collaudo-in-app-nota-credito-resi.md).

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

* La sorgente è già lì: la CTE della frontiera conosce `frontiera_tipo_id` e
  `frontiera_uid`, e `vw_documento_lineage_nodi` porta già
  `natura_doc_codice` (rev 2026-08-20). È **un `LEFT JOIN` sul nodo di
  frontiera**, lo stesso che il BE scrive a mano in `get_lineage_nodo`.
* ⚠️ **`LEFT`, non `JOIN`**: `natura_doc_id` è nullable su `vendite.fatture`, e
  sugli altri sette tipi di nodo la natura è NULL **ed è corretto** (la natura è
  un asse diverso dal tipo, ed esiste solo per le fatture).
* Poi le **sei** `vw_*_lista` la portano avanti come già fanno con
  `frontiera_fase`, e i sei repository la proiettano accanto a
  `frontiera_tipo_codice`.

⭐ **E la ragione dichiarata nel `COMMENT` va aggiornata di conseguenza**, perché
è la seconda volta che quella frase è vera a metà. Il `20260825-20` ha corretto
*«varrebbe sempre NULL»* in *«il consumatore la ricava per conto suo»*. Ma il
consumatore che la ricava è **uno**, e i consumatori che non possono sono
**sei**: la frase giusta diventa *«la colonna c'è perché la chiave del nodo di
frontiera non esce dalla summary, e senza di lei ogni lista chiama Fattura una
nota di credito»*.

### 3.5 Cosa fa il BE/FE nel frattempo

**Niente, e aspetta** ([[feedback_be_fe_attende_prerequisiti_db]]). Il lavoro a
valle è piccolo e già scritto qui, così quando la colonna arriva è un giro solo:

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
da tradurre, il giorno che si accende.

---

### 3.6 ⚠️ E il secondo difetto della stessa famiglia: il numero nudo

La stessa colonna «Transito» mostra **`1`** e non `NC0000001`, perché
`vw_documento_lineage_nodi` espone `fatture.numero` come `codice` del nodo,
mentre per gli altri sei tipi il `codice` è già parlante (`DDT0000031`,
`ORD0000227`). Misurato sul reso 24 all'apply del 2026-08-25.

⭐ **Sede identica**: il nodo. Chi mette mano a `vw_documento_lineage_nodi` per
la natura guardi anche questo — sono un giro solo.

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

---

{% include-markdown "signature-core.md" %}
