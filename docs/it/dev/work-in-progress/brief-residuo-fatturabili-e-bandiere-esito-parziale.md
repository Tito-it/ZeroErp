# Brief — Il residuo che scavalca il rifiuto, e le bandiere che restano alzate

> **Tipo**: brief di difetti emersi in collaudo (DB + BE + FE) · **Data**: 2026-09-04 ·
> **Owner**: Tid · **Branch**: `dev/backend-tid`
>
> **Stato**: 🔴 **APERTO** — cinque difetti, nessuno corretto. Due sono di
> **modello** e vanno prima degli altri.
>
> ✅ **Le due decisioni sono prese (Tid, 2026-09-04)** e il brief è pronto per il
> team DB su `dev/db-tid`. Non c'è nessun bivio residuo da sciogliere: **§9**
> descrive una forma sola.
>
> - **D1+D2 → il perimetro si consegna A MONTE**: il pull marchia col batch del
>   giro ciò che accetta, la select fattura solo quello;
> - **D4 → simmetria**: `fn_annulla_lotto_da_draft` disattiva i task run, come
>   già fa la sorella `fn_riporta_lotto_a_draft`.
>
> **Da dove viene.** Eseguendo
> [collaudo-in-app-esito-parziale-pull-commessa.md](collaudo-in-app-esito-parziale-pull-commessa.md)
> — la voce **V1** del cantiere fan-out
> ([brief-be-fan-out-isolato-e-esito-parziale.md](brief-be-fan-out-isolato-e-esito-parziale.md)
> §13.1) — la **prova 1 è passata** e la **prova 2 è uscita rossa**, ma per una
> ragione che il copione non prevedeva: il lavoro della commessa **respinta** è
> finito in fattura lo stesso.
>
> ⭐ **La prova 2 non ha quindi misurato ciò che doveva misurare.** Il savepoint
> per-commessa non è stato né confermato né smentito: la materia era contaminata
> da righe residue di un giro precedente. Resta da rifare su materia pulita —
> **dopo** i difetti D1 e D2, altrimenti misura di nuovo il residuo.

---

## 0 · In una riga

Il pull sa rifiutare una commessa e lo scrive in tre posti, ma **il rifiuto non
decide niente**: il perimetro di ciò che verrà fatturato non è quello che il
pull consegna — è tutto ciò che si trova libero in `attivita_fatturabili` per
quella competenza. Una riga liberata da un giro disfatto è indistinguibile da
una appena prodotta, quindi la commessa respinta viene fatturata lo stesso. In
più, chi guarda il cruscotto **non può sapere quale** commessa è stata
rifiutata, e la segnalazione del mese **resta accesa** anche dopo che il lotto
è stato annullato.

---

## 1 · I fatti datati

Materia costruita apposta il 2026-09-04, competenza `2026-09`, tre commesse da
tre clienti diversi, tutte nate da push (quindi con la loro riga `ROOT`):

| Commessa | Ordine sorgente | Attività | Ruolo nel collaudo |
| --- | --- | --- | --- |
| 34136 | `ORD0036003` (ROOT) + `ORD0036006` (COLLEGATO) | 3 | sana, multi-sorgente |
| **34137** | `ORD0036005` | 1 | ⭐ **guastata** (ROOT → COLLEGATO, riga 17005) |
| 34138 | `ORD0036004` | 1 | sana |

Due giri, in quest'ordine:

| Ora | Lotto | Cosa è successo |
| --- | --- | --- |
| 17:18:08 | **10140** `LTF-0009180` | giro **senza guasto** (il guasto era finito per errore su 4277, una commessa di agosto fuori perimetro). Tre fatture, tutto `COMPLETATO`. Nascono le righe `attivita_fatturabili` **26828 · 26829 · 26830** |
| ~17:2x | — | il lotto 10140 viene **riportato in lavorazione**: le attività tornano `NON_EMESSA`, ⚠️ **le tre righe `attivita_fatturabili` restano** |
| 17:32:37 | **10141** `LTF-0009181` | giro **con il guasto su 34137**. Il pull rifiuta 34137 — e la fattura di 34137 nasce lo stesso |
| dopo | — | il lotto 10141 viene **annullato**: fatture cancellate, attività di nuovo `NON_EMESSA`, ⚠️ **le tre righe `attivita_fatturabili` restano ancora** |

---

## 2 · D1 🔴 · Il rifiuto per-commessa non arriva alla fattura

**Il fatto.** Sul lotto 10141 il pull ha rifiutato 34137 e lo ha scritto per
esteso:

```
task_run 2836 · pull_attivita_da_commessa · ERRORE · tentativo 1
error_code    E_PULL_COMMESSA
error_message Pull attivita' completato con 1 commesse su 3 in errore
meta          { totale: 3, ok: 2, falliti: 1, commesse_fallite: [34137] }

log di lotto 6613 · status 'C' (critica) · «Errore emissione commessa 34137»
```

E nello stesso lotto è nata la fattura **28785** (BA 173, Azienda ConTutto) con
la riga **14925** da 15,00 — cioè **il lavoro di 34137**. Insieme a questo,
`commesse_attivita 64556` è rimasta `NON_EMESSA`: lo stesso lavoro risultava
**fatturato e ancora da emettere**, che al giro successivo è un doppione.

**Perché succede.** Lo step `select_attivita` è un involucro sottile su
`vendite.fn_select_attivita_fatturabili`, che sceglie le righe di
`attivita_fatturabili` per **competenza, tipo documento, emittente, billing
account, utility** — cioè per *coordinate*, non per *provenienza*. Non chiede a
nessuno se il pull di quella commessa, in **questo** giro, sia andato a buon
fine. Le righe 26828/26829/26830 erano lì dal giro delle 17:18, libere e in
competenza: per lo step a valle erano lavoro legittimo come qualunque altro.

**Perché è un difetto di modello, non un caso di nicchia.** La pipeline
**dichiara** un esito parziale per commessa: `commesse_fallite` è una promessa,
e una promessa che non regge fino al documento non è una promessa. Il rollback
del savepoint protegge il pezzo che il pull ha scritto in **questo** giro — ma
il perimetro di ciò che verrà fatturato non è definito dal pull, è definito da
ciò che sta in tabella. Finché le due cose non coincidono, «commessa rifiutata»
e «commessa non fatturata» sono due affermazioni diverse.

⚠️ **E non dà nessun errore.** Il lotto è in ERRORE per il task del pull, ma la
fattura di troppo è una fattura normale: nessun codice, nessuna criticità sua.

---

## 3 · D2 🔴 · Una riga liberata è indistinguibile da una appena prodotta

⚠️ **Attenzione a non leggerlo come «il cleanup dimentica di cancellare».** Non
è così, e la prima stesura di questo brief lo diceva male. `fn_annulla_lotto_da_draft`
e `fn_riporta_lotto_a_draft` passano entrambe per `fn_cleanup_fatture_by_ids`,
che chiama `vendite.fn_libera_attivita_fatturabili`: le righe si **liberano**,
non si cancellano, ed è **giusto** — quel lavoro non è perso, è lavoro ancora da
fatturare, e cancellarlo sarebbe il difetto vero.

**Il fatto.** Le righe 26828 · 26829 · 26830 hanno `data_insert = 17:18:08`,
cioè il giro del lotto 10140. Sono sopravvissute a una **riapertura** e poi a un
**annullo**, e a oggi sono lì, correttamente liberate:

```
26828 | commessa 34136 | fattura_riga_id NULL | lock_in_fatturazione f
26829 | commessa 34137 | fattura_riga_id NULL | lock_in_fatturazione f
26830 | commessa 34138 | fattura_riga_id NULL | lock_in_fatturazione f
```

**Dov'è allora il difetto.** Nel fatto che una riga liberata **non porta nessuna
memoria di quale giro l'abbia prodotta**, e nessuno gliela chiede. Da lì in poi
è indistinguibile da una riga appena consegnata dal pull, e
`fn_select_attivita_fatturabili` la raccoglie per coordinate. Quindi:

⭐ **il perimetro di un giro oggi è «tutto ciò che è libero e in competenza»,
non «ciò che il pull ha consegnato»** — e finché è così, l'esito parziale del
pull è una scrittura sul registro senza effetto su ciò che viene fatturato.

D1 e D2 sono quindi **la stessa crepa vista da due lati**: il pull calcola un
perimetro (`ok` / `commesse_fallite`) e poi non lo consegna a nessuno; lo step a
valle ne ricostruisce uno suo, per coordinate, e i due divergono senza che
niente dia errore.

---

## 4 · D3 🟡 · Il cruscotto non dice **quale** commessa è fallita

**Il fatto.** Il dato esiste, in due posti (`task_run.meta.commesse_fallite` e
il log di lotto con `status = 'C'`), e **nessuna delle due superfici del
cruscotto lo pubblica**:

- `vendite.vw_dash_competenza_gruppi` — le righe del drill-down — ha 30 colonne
  e **nessuna** che porti l'esito di un giro. Il frontend non può disegnare quel
  che non riceve;
- `vendite.vw_dash_competenza_errori` — il pannello «errori vivi» — espone
  `lotto_id`, `lotto_codice`, `stato_lotto`, `task_code`, `error_code`,
  `messaggio` ed emittente. **Nessun `commessa_id`.** Il messaggio stesso lo
  ammette e rimanda altrove: *«dettaglio sui log di lotto»*.

**Perché è un difetto.** L'operatore legge «una su tre è fallita» e non ha modo
di sapere su quale riga agire senza aprire il lotto e leggersi il log. È un
difetto di **trasporto**, non di calcolo: la pipeline sa chi ha rifiutato, e lo
perde per strada verso la schermata da cui si lavora.

⚠️ **Sommato a D1 è peggio**: la riga di 34137 mostrava lavoro `DA_EMETTERE`
del tutto ordinario, mentre quel lavoro era già dentro una fattura DRAFT. Sulla
riga non c'era **nessun** indizio — né dell'errore, né della fattura.

---

## 5 · D4 🟡 · L'errore di un lotto annullato resta «vivo»

**Il fatto.** Dopo l'annullo del lotto 10141 la segnalazione sul calendario di
settembre è rimasta accesa. È **fedele al dato**: la CTE `task_err` di
`vw_dash_competenza_errori` prende i `task_run` in `ERRORE` con `attivo IS TRUE`
che non abbiano un tentativo successivo `COMPLETATO` dello stesso task — e
**non guarda lo stato del lotto**. Il run 2836 è ancora `ERRORE` e ancora
`attivo`, quindi l'evento resta:

```
TASK_ERRORE · lotto 10141 · LTF-0009181 · stato_lotto COMPLETATO
             · pull_attivita_da_commessa · E_PULL_COMMESSA
```

**Perché è un difetto.** La lista si chiama **errori vivi**. Un lotto annullato
non è più lavoro in corso: il suo errore è storia, non una cosa da rimediare.
Chi annulla deve abbassare la bandiera — disattivando il run, o chiudendolo con
un esito, o escludendo dalla vista i lotti che non sono più in lavorazione. Da
decidere quale delle tre, ma non «nessuna».

---

## 6 · D5 🟡 · Lista vuota e calendario acceso — divergenza da confermare a video

**Il fatto riferito**: dopo l'annullo, il pannello degli errori si è svuotato
mentre il calendario continua a segnare l'errore.

**Cosa dice il database**: il conteggio mensile e la lista leggono **la stessa
vista** con lo stesso predicato, e a DB sono d'accordo — entrambi danno **1**
per `2026-09`. Quindi la divergenza non è nei dati: il pannello si azzera
(`erroriFetch.reset()` al cambio mese/refresh) e non rifà la fetch, restando
vuoto finché non lo si risollecita.

🩺 **Verifica**: ricarica la pagina e riseleziona settembre. Se la riga
riappare, è questo; se resta vuota con il badge acceso, allora è altro e va
guardato a parte.

---

## 7 · Aperta · il gruppo dell'ordine ROOT di 34136 non viene mai pullato

Le attività **64553 e 64554** (ordine `ORD0036003`, che è la sorgente **ROOT**
di 34136) non sono state pullate in **nessuno dei due giri**, pur essendo
`APPROVATA` / `NON_EMESSA`, con `tipo_doc_fiscale_id` valorizzato, e pur
risultando alla lane (`fn_list_commesse_emittibili` → `total_non_emesse = 2`).
Di 34136 passa solo il gruppo del COLLEGATO (`ORD0036006`).

Può essere un'emissione mirata che escludeva quel gruppo. È successo però due
volte su due, e la seconda il giro era sul mese: **da chiarire prima di
richiudere il collaudo**, perché se non è la mirata è un terzo difetto.

---

## 8 · Cosa questo brief **non** dice

⛔ **Non dice che il savepoint per-commessa è rotto.** La prova 2 doveva
misurare *«una commessa rifiutata non si porta via il lavoro di quelle passate
prima»*, e su questo giro non l'ha misurato: le fatture nascevano da righe
preesistenti, non dal pull. La proprietà resta **asserita nei test e non
eseguita in applicazione** — che è la ragione per cui il collaudo esiste.

La prova 2 va rifatta su materia pulita, **dopo** D1 e D2.

---

## 9 · Proposta di lavoro

### La forma decisa per D1+D2 — il perimetro si consegna

**Il pull consegna, la select riceve.** Chi calcola il perimetro è lo stesso che
lo dichiara, così le due cose non possono divergere.

⛔ **Non è «cancellare le righe liberate»**: quel lavoro è ancora da fatturare, e
cancellarlo perderebbe lavoro vero.

**I tre pezzi, in forma concreta:**

1. `vendite.fn_emit_attivita_fatturabili_da_commessa` riceve **l'identità del
   giro** — oggi la sua firma è
   `(p_commessa_id, p_only_approved, p_dry_run, p_gruppi)` e **non ha nessun
   parametro di batch**: va aggiunto;
2. la funzione **marchia** con quell'identità le righe che accetta, **su
   entrambi i rami** — quello di `INSERT` e quello di `UPDATE`. Il ramo di
   update è quello che conta: è lì che passano i residui;
3. `vendite.fn_select_attivita_fatturabili` sceglie **per quel marchio**, non
   più per sole coordinate. Una commessa respinta non è marchiata, quindi non
   viene fatturata.

Il backend passa già il `lock_batch_id` del lotto a `select_attivita`
(`LottoContext`), quindi il valore da consegnare al pull ce l'ha in mano: la
modifica lato BE è il passaggio di un parametro.

✅ **L'incognita che questo brief lasciava aperta è chiusa: il pull ri-adotta i
residui.** Cerca la riga esistente per `(sorgente_tipo_id, sorgente_uid)` — dove
`sorgente_uid` è l'UUID deterministico ricavato da `segment_key` — e se la trova
la **aggiorna** invece di inserirne una nuova. Quindi marchiare sul ramo di
update è sufficiente: un residuo di un giro disfatto viene ripreso e rimarchiato
dal primo giro in cui quella commessa passa, e **niente lavoro va perso**.

### Il resto, in ordine

1. **D1+D2** nella forma qui sopra — è tutto dentro due funzioni SQL; il backend
   le avvolge e basta;
2. **rifare la prova 2** del collaudo: è l'unica che dice se il savepoint
   per-commessa regge;
3. **D3** — `commessa_id` (e codice) su `vw_dash_competenza_errori`; una colonna
   d'esito sulle righe del drill-down, così la riga rifiutata si riconosce a
   video. A cascata: riga BE, catalogo lista, colonna FE;
4. **D4 · simmetria** — `fn_annulla_lotto_da_draft` disattiva i task run del
   lotto, esattamente come già fa `fn_riporta_lotto_a_draft` (che infatti
   restituisce `annullati_task_run`). Due sorelle non possono comportarsi
   diversamente sulla stessa cosa. La vista `task_err` non si tocca;
5. **D5** e il **§7** — verificare a video, e riclassificare.

ℹ️ Le tre righe 26828/26829/26830 **non vanno cancellate**: sono lavoro
legittimo da fatturare. Vanno però tenute presenti nel rifare il collaudo, o
riprodurranno D1 finché D1 non è chiuso.

---

## 10 · Come riprodurre

1. tre commesse su un mese, da tre clienti diversi, nate da push (§La materia
   del copione);
2. lancia un giro **senza guasto**: nascono le righe `attivita_fatturabili`;
3. **riporta il lotto in lavorazione** (o annullalo): le attività tornano
   `NON_EMESSA`, le righe `attivita_fatturabili` **restano**;
4. guasta una commessa (ROOT → COLLEGATO) e rilancia;
5. il task del pull chiude in `ERRORE` con quella commessa fra le
   `commesse_fallite` — **e la sua fattura c'è lo stesso**.
