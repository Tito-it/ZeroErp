# Brief DB — i due residui del lineage: il `root` che dipende dagli id, e la commessa senza origine

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine.** Voce **L7.5** di
> [brief-db-lineage-arco-reso-nota-credito.md](brief-db-lineage-arco-reso-nota-credito.md):
> *«portare a un cantiere suo i due residui del §7»*. Sono usciti da lì e non
> sono di lì: il cantiere dell'arco `S` li ha **esposti**, non creati.
>
> **Stato.** 2026-08-26 — analisi e misure. **Nessun file scritto, nessuna
> migrazione.** Due domande di modello prima di qualunque riga di SQL, entrambe
> in §1.3 e §2.4.
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

## 0. Le due voci in una riga

| # | Cosa | Gravità | Chi lo vede oggi |
| --- | --- | --- | --- |
| **1** | Il `root` di un nodo con più sorgenti si sceglie su `from_tipo_id`, cioè su un **id di `config.sorgenti`** e non su una chiave stabile | 🟠 fragilità silenziosa, nessun effetto oggi | nessuno — finché gli id non cambiano |
| **2** | `commesse_sorgenti` ha righe **`DDT_VENDITA`** che non producono nessun arco: quelle commesse risultano **senza origine** nel grafo | 🔴 dato vero non rappresentato | chi apre il pannello «Passaggi» di quelle due commesse, e la colonna «Transito» dei due DDT |

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

## 3. 📎 La famiglia accanto: come un nodo FATTURA si presenta in lista

Non è una terza voce di questo brief — è il rimando, perché le due cose si
toccano e chi apre `vw_documento_lineage_nodi` le vede insieme.

| Cosa | Dove sta |
| --- | --- |
| 🔴 la colonna «Transito» chiama **«Fattura»** una nota di credito (`frontiera_natura_doc_codice` non esce dalla summary) | **§7-bis** di [brief-db-lineage-arco-reso-nota-credito.md](brief-db-lineage-arco-reso-nota-credito.md) — **blocca** la resa del cantiere `S` |
| ⚠️ la colonna «Transito» mostra il **numero nudo** (`1`) invece di un codice parlante, perché `vw_documento_lineage_nodi` espone `fatture.numero` come `codice` del nodo, mentre per gli altri sette tipi il `codice` è già parlante (`DDT0000031`, `ORD0000227`) | §7 dello stesso brief, terzo punto — non blocca |

⭐ **Entrambe si curano sul NODO**, non sulle sette viste di lista che lo
proiettano. Se il team DB mette mano a `vw_documento_lineage_nodi` /
`vw_documento_lineage`, conviene guardarle nello stesso giro.

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
