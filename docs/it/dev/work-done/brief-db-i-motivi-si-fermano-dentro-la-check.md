# Brief DB — i motivi si fermano dentro la check

> **Destinatario:** team DB (`dev/db-tid`). Aperto il 2026-09-08.
>
> **In una riga:** una `script.fn_check_*` sa **perché** si rifiuta, **con quale
> codice** e — a volte — **cosa scrivere nella frase**. Due di queste tre cose
> non escono da lì: non arrivano ai presidi del catalogo codici, e non arrivano
> al messaggio che l'operatore legge.
>
> **Origine.** Sono i due residui misurati chiudendo
> [brief-db-coda-primo-motivo-in-un-posto-solo](../work-done/brief-db-coda-primo-motivo-in-un-posto-solo.md)
> (§9.5). Non sono buone intenzioni: hanno i loro numeri, presi il 2026-09-08.
>
> ⛔ **Nessuna misura decide niente qui.** I conteggi dicono **quanto è largo il
> perimetro**, non se il lavoro vada fatto. A decidere è la struttura.

---

## 1. ⭐ È una cosa sola, vista da due lati

Il pattern «la madre CHIAMA la check» ([linee-guida-sql §12.5.2](../../linee-guida-sql.md))
sposta la regola dentro la `fn_check_*`, e fa bene: rifiuto e tooltip non
«coincidono oggi», **non possono divergere**.

⚠️ Ma sposta anche **due cose che fuori servivano**:

| Cosa resta dentro la check | Chi la perde |
| --- | --- |
| il **codice**, che nella check è un letterale ma sulla riga di sollevamento non c'è | i presidi del catalogo codici, che il letterale lo cercano **accanto alla chiamata** |
| i **valori** della frase — quando la check non li emette | il messaggio: a comporlo resta il chiamante, con quello che ha in mano |

⇒ **Un cantiere solo, due passi.** Separarli sarebbe peggio: far emettere
`valori` alle check chiude il secondo lato **e** rende i loro siti estraibili
con l'helper — cioè l'`H-4` ritirato dall'altro brief.

---

## 2. Le due misure — fatti datati, 2026-09-08

### 2.1 🔴 Trentacinque codici fuori dal rubinetto degli accumulatori

`dbops.vw_codici_errore_forme_condizione` — la sorgente dei tre presidi del
catalogo codici — trova un punto di sollevamento così: una riga con un
**letterale `'E_...'`** e una `fn_log_and_raise_error` **entro sei righe**
(`chiamata_vicina`).

Nel pattern §12.5 il letterale sta **nella check**, dove nessuna chiamata gli sta
vicino. Misurato: **35 codici** nominati solo lì.

| Presidio | Cosa perde |
| --- | --- |
| cancello del **terzo lato** («ha una policy?») | ✅ **niente** — tutti e 35 sono a catalogo |
| ⭐ **rubinetto degli accumulatori** B-7 («questo codice ha acquistato una condizione che non aveva?») | 🔴 **tutti e 35** |
| lente `check_messaggio_vs_condizione` | 🔴 gli stessi 35 |

⛔ **Il danno non è «un codice senza policy»** — quello non succede. È che
**trentacinque codici possono allargarsi a una condizione nuova senza che
nessuno se ne accorga**, ed è esattamente il modo in cui si forma un
accumulatore: *«nessuno crea un codice generico di proposito. Si prende quello
che c'è già e lo si usa anche per questo caso qui, una volta sola.»*

⚠️ **E non l'ha causato l'altro cantiere.** Anche prima quei siti sollevavano
`v_primo ->> 'codice'`, senza letterale: è una proprietà del pattern, non una
regressione. Il numero non è cresciuto.

### 2.2 🔴 Sei check su tredici possono comporre una frase con l'arità sbagliata

Nelle tredici della «forma B» la check **non emette `valori`**: la frase la
compone il chiamante, con un numero **fisso** di valori presi dai propri dati
(`v_numero`, `p_gruppo_key`, `NEW.codice`…). Ma i codici che quelle check
possono emettere **non hanno tutti lo stesso numero di segnaposto**:

| Check | Segnaposto dei suoi codici |
| --- | --- |
| `fn_check_commessa_annullabile` | 1 / 2 🔴 |
| `fn_check_commessa_chiudibile` | 1 / 2 🔴 |
| `fn_check_documento_escludibile_da_giro` | 1 / 2 🔴 |
| `fn_check_ordine_confermabile` | 1 / 2 🔴 |
| `fn_check_preventivo_emettibile` | 1 / 2 🔴 |
| `fn_check_rinuncia_reversibile` | 0 / 1 🔴 |
| le altre sette | uniformi ✅ |

⇒ Se il primo motivo è quello a **due** segnaposto e il chiamante passa **un**
valore, `format()` non compone: scatta il ripiego (`W_MESSAGGIO_ARITA` nel log)
e a video esce **il messaggio grezzo, coi `%s`**.

⚠️ **È l'incidente del 2026-09-01 in un'altra forma** — quello di
`E_REGISTRO_SERIE_NON_AMMESSA`, dove a video usciva *«Registro X1»* con la serie
al posto della famiglia. Lì i valori c'erano ma in ordine sbagliato; qui possono
non bastare affatto.
⛔ **E nessun test lo vedrebbe**: i pgTAP di quei siti asseriscono `P0001`, non
la frase resa.

---

## 3. Il piano

| Passo | Cosa | Dove |
| --- | --- | --- |
| **V-1** | ⭐ La vista dei presidi impara la forma **«codice da un motivo»**: dal punto che solleva risale alla `fn_check_*` chiamata e ai codici che quella nomina | `20_code/dbops` |
| **V-2** | Ri-base **motivata** delle tre baseline che quella vista alimenta: i 35 codici entrano, e la prima corsa dirà quali hanno davvero più di una famiglia | `scripts/`, con la ragione nel commit |
| **C-1** | Far emettere **`valori`** alle sei check con arità mista — le altre sette **dopo**, e solo se serve | `20_code/script` |
| **C-2** | I sei siti corrispondenti passano a `script.fn_raise_primo_motivo_se_presente` | `20_code/vendite` |
| **P-1** | Per ogni sito toccato da `C-2`, un `throws_like` sulla **frase resa** — prima di toccarlo | `db/pgtap/vendite` |
| **P-2** | La soglia del rubinetto in `test-rubinetto-primo-motivo-v1.sql` **cala** da 13 a 7 | `db/pgtap/script` |

⚠️ **L'ordine non è negoziabile**: `C-1` prima di `C-2`. Spostare un sito
all'helper prima che la sua check emetta `valori` manda a video i `%s` grezzi —
è il motivo per cui `H-4` è stato ritirato dall'altro brief.

---

## 4. ⛔ Cosa NON si fa

* ⛔ **Non si aggiunge `p_valori` all'helper.** Svuoterebbe la terza convenzione:
  il chiamante ricomporrebbe i valori a mano, e l'helper diventerebbe un
  involucro attorno a niente ([§4.2 dell'altro brief](../work-done/brief-db-coda-primo-motivo-in-un-posto-solo.md));
* ⛔ **Non si allarga il marcatore del rubinetto** per prendere anche i siti
  fuori perimetro: lì il `-> 0` è **legittimo** finché la check non emette
  `valori`, e un cancello che boccia il caso giusto viene spento;
* ⛔ **Non si riscrivono i 1200 punti a codice letterale** per uniformare la
  forma: è l'alternativa già scartata, e si fa dal lato che **guarda** (una
  vista) non da quello che **scrive**;
* ⛔ **Nessun codice errore nuovo**: le check *nominano* codici già a catalogo.
  Se per scriverne una servisse un codice nuovo, il difetto è a monte.

---

## 5. ⚠️ Il rischio del passo V-1, e va guardato prima

La vista alimenta **tre** presidi. Insegnarle una forma nuova fa **entrare** 35
codici che oggi non vede: alcuni scopriranno di avere più di una famiglia di
condizione, e la CI si fermerà su di loro.

⭐ **È il comportamento giusto, non un incidente** — ed è già successo il
2026-09-07, quando una famiglia nuova (`VALORE_ATTESO`) fermò il rubinetto su
otto codici. Lì la lezione fu:

> Una famiglia nuova produce **due** effetti che si assomigliano e vanno
> separati uno per uno: cambia il metro su chi già usava quel codice, e **rende
> visibile** ciò che prima era illeggibile. ⛔ Il primo si ri-basa, il secondo
> **no**: è una segnalazione vera arrivata in ritardo. Il discriminante è il
> **conteggio dei punti**.

⚠️ Qui vale identico, ed è tutto il `V-2`: ⛔ **la baseline non si aggiorna per
far passare la CI.** Ogni codice che entra si guarda una volta, e la ragione va
nel messaggio di commit.

---

## 6. Cosa non si tocca

* **Le teste dei siti**: quale check chiamare, su cosa. Non è questo cantiere.
* **`script.fn_log_and_raise_error`** e **`script.fn_raise_primo_motivo_se_presente`**:
  le firme non cambiano.
* **L'ordine dell'array dei motivi**: è il contratto della check, e `C-1` non lo
  tocca — aggiunge `valori`, non riordina.
* **Nessuna migrazione si applica** senza che Tid lo dica, per quel comando.
