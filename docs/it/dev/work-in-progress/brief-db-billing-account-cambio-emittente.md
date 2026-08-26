# Brief DB — un billing account può cambiare emittente?

> **Natura di questo documento:** ~~⚠️ è una riflessione di dominio, non un
> piano. Non c'è una consegna da scrivere finché la domanda del titolo non ha
> una risposta.~~
> ✅ **Superata il 2026-08-26**: la domanda ha una risposta (§5, D-1) e il piano
> c'è (§6). Il documento resta una riflessione di dominio **con** una consegna in
> coda, non al posto suo.
>
> **Destinatario:** Tid, per la decisione. Il team DB solo dopo.
>
> **Origine.** Tid, 2026-08-26, leggendo la D-3 di
> [brief-db-emittente-commessa-invariante.md](brief-db-emittente-commessa-invariante.md):
> *«ho il dubbio che sia corretto spostare un billing account da un emittente ad
> un altro; credo che al più in futuro si determini la duplica di un BA su altro,
> ma spostare quel BA è un problema ai fini fiscali: non può scomparire un
> cliente che ha già delle fatture con un emittente perché è andato ad un
> altro»*.
>
> **Separato apposta** dal brief sull'invariante della commessa (richiesta di
> Tid, stesso giorno): là c'è un difetto con un rimedio chiaro, qui una domanda
> di dominio con implicazioni fiscali. Mescolarli farebbe rimandare il primo in
> attesa del secondo.
>
> ✅ **CANTIERE DB CHIUSO il 2026-08-26 — M1…M6, eseguiti e APPLICATI.**
> ChangeSet `20260826-46` … `-49` più il `-53` (i `COMMENT` che raccontavano il
> modello di prima); un codice errore nuovo; un pgTAP `plan(8)`; 4 pagine
> `manual/`, la sezione sulla tabella e due guide. Registro nel **§8**.
>
> 🔴 **Resta BE-1** — verificare che l'endpoint del mapping restituisca davvero
> il 409 e non lo mangi in un `except Exception` (§6.7) — e, **in pausa, M7**:
> la capability per il gesto FE non si costruisce finché il frontend non la
> chiede.
>
> ⚠️ **Migrazione applicata da Tid il 2026-08-26** — l'autorizzazione l'ha data
> lui, comando per comando ([[feedback_mai_applicare_migrazioni_db]]).
>
> ⭐ **E il cantiere ha smesso di essere facoltativo.** Non per una decisione di
> dominio, ma per una conseguenza strutturale: nel momento in cui l'altro brief
> mette il `NOT NULL` e il vincolo al billing account, la colonna
> `vendite.commesse.emittente_soggetto_ruolo_id` diventa **una copia congelata**
> di un dato che vive altrove. Spostare il mapping la rende falsa in silenzio, e
> il guard di là non se ne accorge perché nessuno riscrive quella riga. La
> rilettura completa è nel **§2.1**.

---

## 1. La domanda, in una riga

`anagrafiche.emittenti_fiscali_billing_account` dice a quale emittente fiscale
appartiene un billing account. Quella riga **si può aggiornare**. La domanda è se
debba potersi.

---

## 2. Cosa dice la struttura — e conferma l'intuizione di Tid

⭐ **La fattura NON segue il cliente: congela il proprio emittente.**
`vendite.fatture.emittente_soggetto_ruolo_id` è **`NOT NULL`**, ha un indice
proprio (`ix_fatture_emitt_data`), e accanto c'è persino un
`emittente_snapshot jsonb` — cioè una copia congelata dei dati dell'emittente al
momento dell'emissione. Il progetto ha già deciso, e bene, che **il documento
fiscale porta con sé chi lo ha emesso**.

⇒ **Spostare un BA non riscrive la storia: la orfana.** Le fatture restano
sull'emittente vecchio; il cliente passa al nuovo. Da quel momento l'operatore
dell'emittente che ha emesso quelle fatture continua a **vedere il documento** e
smette di **vedere il cliente**. È esattamente il difetto che Tid descrive, e non
è un'ipotesi: discende dalle colonne.

⚠️ **E il perimetro è preso sul serio dappertutto, tranne qui.**
`vendite.fatture` ha `trg_fatture_a10_guard_emittente_scope`, che impedisce di
scrivere un documento fuori dal proprio emittente. L'albero dei billing account
ha `fn_guard_albero_ba_emittente`, che vieta di mescolare due emittenti fra padre
e figli. Ma la riga che **decide** l'emittente di un BA ha solo due presidi — il
default globale unico e l'omogeneità dell'albero — e **nessuno dei due guarda la
storia già scritta**.

### 2.1 ⭐ E dal 2026-08-26 non è più solo la fattura a congelare l'emittente

Il cantiere gemello
([brief-db-emittente-commessa-invariante.md](brief-db-emittente-commessa-invariante.md))
mette `NOT NULL` su `vendite.commesse.emittente_soggetto_ruolo_id` e la vincola
al billing account. ⇒ Da quel momento **anche la commessa porta una copia** di un
dato che vive altrove.

⚠️ **E il guard di là, di proposito, non la difende.** Scatta su
`UPDATE OF billing_account_id, emittente_soggetto_ruolo_id`: se il mapping del BA
cambia, la riga della commessa **non viene riscritta da nessuno**, quindi nessun
trigger si sveglia e la copia resta lì, falsa. La scelta è giusta — l'alternativa
(rivalidare a ogni `UPDATE`) renderebbe **non più modificabili** tutte le commesse
del cliente, con un errore che parla di una colonna che nessuno stava toccando —
ma sposta il presidio **qui**.

⇒ **La conseguenza pratica.** Con l'emittente stantìo sulla commessa, la riga
resta visibile a chi non dovrebbe vederla e sparisce a chi dovrebbe: è
esattamente il danno del §2 dell'altro brief — *lavoro che esiste nel database,
non compare da nessuna parte e non viene mai fatturato* — solo che qui non serve
che qualcuno sbagli a scrivere: basta una correzione di anagrafica fatta con le
migliori intenzioni.

⭐ È il motivo per cui la risposta alla D-2 («che cosa conta come storia?») non è
più una questione di prudenza: **la commessa è storia** perché il modello, da
quel cantiere in poi, le fa portare una copia.

### 2.2 ⚠️ Chi fa il movimento, oggi: **non c'è nessun `UPDATE`**

Letto il 2026-08-26 in `backend/apps/anagrafiche/db/emittenti_fiscali_repository.py`.
La sotto-risorsa espone **`create_mapping`** e **`delete_mapping`**, e basta.
⇒ «Spostare un BA da un emittente all'altro» dal frontend è, in due tempi:

1. **cancella** il mapping sull'emittente A — e da quel momento il BA ricade sul
   **gestore globale**, che è già un cambio di emittente, non un limbo;
2. **crea** il mapping sull'emittente B.

⭐ Ne discende una cosa che semplifica il presidio: **i movimenti da guardare sono
tre** — `INSERT`, `UPDATE`, `DELETE` della riga di mapping — ed è **esattamente**
la stessa terna che il guard dell'albero (`trgfn_efba_guard_albero_emittente`) già
presidia. Il cancello nuovo è un fratello di uno che c'è, sulla stessa tabella.

⚠️ E il passo 1 da solo **è già** lo spostamento: un guard che controllasse solo
l'`INSERT` lascerebbe passare tutto, perché il danno lo fa la cancellazione.

### 2.3 ⚠️ Il mapping **nasce da solo**, e questo dice dov'è la finestra di correzione

`anagrafiche.trgfn_billing_account_link_ef` è un `AFTER INSERT` su
`billing_account`: crea il mapping verso l'emittente **dell'operatore che sta
creando il cliente**, letto dalla GUC `app.current_user_id`.

⇒ Un billing account **non passa mai** da uno stato «senza emittente»: nasce già
mappato, e se l'operatore era loggato sull'emittente sbagliato, nasce **mappato
male**. È il caso del §3 — l'errore di inserimento ordinario — e conferma che una
via d'uscita serve davvero.

⭐ Ma dice anche **quando** quella via è ancora percorribile: subito, prima che
sul quel BA sia passato del lavoro. Che è precisamente la forma **b**.

---

## 3. La tensione da sciogliere, ed è vera

⛔ **Vietare e basta ha un costo.** Un billing account può nascere sotto
l'emittente sbagliato: è un errore di inserimento ordinario. Se il legame è
immutabile, quell'errore non si corregge più — e la via d'uscita diventa
cancellare e rifare, che è peggio, o lasciare il dato sbagliato, che è peggio
ancora.

⇒ La domanda vera **non è** «si può cambiare?» ma **«fino a quando?»**. E la
risposta plausibile è: *finché non c'è storia fiscale*. Che è una riga sola di
condizione, ma ne apre un'altra — ▼ D-2.

---

## 4. Le tre forme possibili — ✅ **scelta la b (D-1); la c non è codice**

> ⚠️ *Era «nessuna scelta, sono da pesare». Pesate il 2026-08-26: si costruisce
> la **b** e non si costruisce niente per la **c**, che con una fornitura nuova è
> già possibile oggi. Motivazione in **§5, D-1**; la tabella resta perché mette
> le tre forme una accanto all'altra.*

| | Forma | Regge? | Costo |
| --- | --- | --- | --- |
| **a** | **Divieto assoluto**: il legame BA→emittente è immutabile dalla nascita | ✅ nessuna storia si orfana mai | ⛔ un BA nato sbagliato non si corregge |
| **b** | **Divieto condizionato alla storia**: libero finché il BA non ha documenti fiscali, vietato dopo | ✅ protegge ciò che va protetto e lascia correggere gli errori | ⚠️ dipende tutto da cosa conta come «storia» (D-2) |
| **c** | **Si duplica, non si sposta** — l'ipotesi di Tid: il cliente nasce una seconda volta sotto l'altro emittente, e il BA vecchio resta con la sua storia | ✅ fiscalmente è la forma più pulita: nessun documento cambia padrone | ⚠️ apre «chi è il cliente» su due BA gemelli — e il problema si sposta su chi li deve riconoscere come la stessa persona |

⭐ **b e c non sono alternative**: rispondono a due bisogni diversi. La **b** serve
a correggere un errore; la **c** serve quando il cliente passa **davvero**
all'altro emittente e da lì in avanti lavora lì. Probabilmente servono entrambe.

---

## 5. ❓ ~~Le domande aperte~~ → **chiuse il 2026-08-26**

### ✅ D-1 CHIUSA — **b**, e la **c** non è un lavoro di database

> ~~quale forma, fra le tre del §4?~~

✅ **Si costruisce la forma b** — libero finché non c'è storia, vietato dopo — e
**non si costruisce niente per la c**. Le due ragioni non si somigliano:

**Perché b.** È la sola delle tre che risponde a entrambe le frasi già dette in
questo documento senza contraddirne nessuna: *«non può scomparire un cliente che
ha già delle fatture con un emittente»* (Tid) e *«un BA nato sbagliato deve
potersi correggere»* (§3). La **a** paga la prima negando la seconda; la **b** le
tiene tutte e due, e il §2.3 mostra che la finestra di correzione esiste davvero
— il mapping nasce da solo con l'emittente dell'operatore, quindi l'errore si fa
al minuto zero e lì si corregge.

**Perché la c non è codice.** ⭐ La struttura dice che *«duplicare il BA»* non è
un'operazione disponibile: `uq_billing_instance_utility` è `UNIQUE
(istanza_utility_id, utility_id)` su `anagrafiche.billing_account` — **per una
istanza di utility esiste un billing account e uno solo**. Un «BA gemello» sulla
stessa fornitura non si può scrivere, e non perché manchi una funzione: perché un
indice univoco lo vieta.

⇒ **E la forma giusta della c è già possibile, oggi, senza toccare il
database.** Se il cliente passa *davvero* all'altro emittente, quello che nasce è
una **fornitura nuova** — `istanze_utilities` nuova, e da lì il suo billing
account, mappato sull'emittente B. I documenti vecchi restano dove sono, con chi
li ha emessi. È esattamente la pulizia fiscale che la **c** cercava, ottenuta
senza gemelli: non ci sono due BA per la stessa cosa, ci sono due cose.

⚠️ **Quello che resta scoperto, e va detto**: se un giorno servisse davvero un
secondo BA sulla **stessa** istanza di utility, la conversazione non parte da
«come li teniamo insieme» ma da «che cosa diventa `uq_billing_instance_utility`».
Non è questo cantiere.

### ✅ D-2 CHIUSA — storia = **ciò che ha già congelato una copia dell'emittente**

> ~~che cosa conta come «storia» che blocca?~~ *Le due risposte in campo erano:
> solo le fatture emesse (criterio fiscale), oppure anche commesse, DDT, ordini.*

✅ **Il criterio non è «quanto è grave», è una proprietà del modello**: blocca
ciò che porta **una copia dell'emittente che nessuno riscriverà più**. Con quel
criterio la lista si compila da sola, e sono **due** cose:

| Oggetto | Perché è storia | Come si conta |
| --- | --- | --- |
| `vendite.fatture` | `emittente_soggetto_ruolo_id` **`NOT NULL`** *e* `emittente_snapshot jsonb` accanto: il documento fiscale porta con sé chi lo ha emesso (§2) | `EXISTS` su `billing_account_id` — indice `ix_fatture_ba_data` |
| `vendite.commesse` | dopo il cantiere gemello, `emittente_soggetto_ruolo_id` è `NOT NULL` e vincolata al BA: **è una copia** (§2.1) | `EXISTS` su `billing_account_id` — indice `ix_commesse_ba_utility` |

⛔ **E per lo stesso criterio, ordini e DDT NON entrano.** Non perché contino
meno: perché il loro emittente **non è una copia stantìa**. Hanno il proprio
`trgfn_*_guard_emittente_ba` (elenco nel §4.1 dell'altro brief), quindi la
coerenza col BA gliela ricontrolla un trigger a ogni scrittura. Metterli nella
lista bloccherebbe più casi senza chiudere nessun buco in più — e «blocca di
più» non è un argomento.

⭐ **Il timore del §5 originale si dissolve da solo**: *«su un BA appena creato con
una commessa vuota bloccherebbe una correzione ancora legittima»*. Un BA appena
creato **non ha commesse**: la commessa nasce al primo push (§2.3). La finestra
di correzione è «prima che ci sia passato del lavoro», che è la definizione
operativa di «errore appena fatto».

⚠️ **E quando la finestra è chiusa, la via d'uscita non è la forza: è la D-1.**
Se sul BA è già passato del lavoro, la risposta è la **c** — fornitura nuova
sotto l'altro emittente — non un `UPDATE` a mano che orfana i documenti.

⛔ **Niente riallineamento a cascata delle commesse non fatturate**, ed è una
tentazione da nominare per rifiutarla. Sarebbe la «terza via» comoda: se non ci
sono fatture, riscrivi l'emittente sulle commesse e lascia passare. ⇒ Vorrebbe
dire riscrivere in blocco **la colonna di perimetro** di righe che l'operatore
che fa il gesto, sotto RLS, **non vede nemmeno**. Un rimedio che agisce fuori dal
campo visivo di chi lo ha innescato non è un rimedio.

### ✅ D-3 CHIUSA — li tiene insieme il **soggetto**, e c'è già

> ~~con la forma «duplica», chi tiene insieme i due BA?~~

✅ **Basta il soggetto a monte: nessuna colonna nuova, nessun concetto nuovo.**
`anagrafiche.billing_account.soggetto_ruolo_id` è **`NOT NULL`** e
`anagrafiche.istanze_utilities.soggetto_id` pure: due billing account nati per lo
stesso cliente sotto due emittenti **risalgono già** alla stessa persona
giuridica, per costruzione. Non sono «due clienti» per il database: sono due
posizioni dello stesso soggetto.

⛔ **Una colonna «BA gemello di» sarebbe un doppione con l'aggravante di poter
mentire**: due sorgenti di verità sulla stessa domanda, e quella nuova
manutenuta a mano. La domanda che il frontend deve poter fare — *«quali posizioni
ha questo cliente, e presso chi?»* — si risponde dal soggetto, che è dove la
risposta è già vera.

⚠️ Ne resta una consegna **di lettura**, non di modello: chi guarda un cliente
deve vedere **tutte** le sue posizioni, anche quelle di un altro emittente — e la
RLS, giustamente, non gliele mostra. Non è un buco di questo cantiere: è la
domanda «cosa può vedere un operatore fuori dal proprio perimetro», che ha già la
sua sede (`config.user_emittenti_fiscali`). Segnalata, non risolta qui.

### ✅ D-4 CHIUSA — no, non aspetta. ⚠️ **Ma non è più vero il contrario**

> ~~la correzione della commessa deve aspettare questa decisione?~~

✅ **Confermato: non aspetta.** L'altro cantiere mette `NOT NULL` sulla colonna e
la vincola al billing account, ed è giusto qualunque cosa si decida qui. La
separazione dei due brief regge.

⚠️ **La dipendenza però esiste, e va nell'altro verso.** Il §2.1 la scrive per
esteso: **è questo cantiere che ha bisogno di quello**, non viceversa — la
commessa entra nella definizione di «storia» (D-2) solo dopo che il `NOT NULL` di
là l'ha resa una copia congelata. ⇒ Vincolo d'ordine reale:

* **M1 dipende da L3** dell'altro brief per la parte «commesse»;
* la parte «fatture» **non dipende da niente** e si può consegnare prima.

⭐ E c'è una ragione per **non** consegnarle a distanza: fra il `NOT NULL` di là e
il cancello di qua, un cambio di mapping produrrebbe commesse con l'emittente
stantìo — cioè il danno del §2.1, in una finestra che si sarebbe aperta da sé. La
raccomandazione è **stessa release**; il vincolo tecnico è solo M1 dopo L3.

---

## 6. Piano di sviluppo

> ⛔ **Nessun file scritto, nessuna migrazione applicata**
> ([[feedback_mai_applicare_migrazioni_db]]): l'esecuzione parte su «procedi».
>
> Valgono le **stesse regole di lotto** scritte nel §7 dell'altro brief e non si
> ripetono: numerazione `NN` globale per data
> ([[feedback_liquibase_numerazione_globale_per_data]]), un `changeSet` per file,
> `logicalFilePath`, `runOnChange: false`, corpo dalla doc auto-gen e firma
> dall'ultimo YAML ([[feedback_autogen_firma_perde_type]]), `%TYPE` ovunque,
> errori con codici registrati.

### 6.0 Il quadro in una tabella

| Lotto | Cosa | Fase | Dipende da | Sblocca |
| --- | --- | --- | --- | --- |
| **M1** | `fn_get_storia_emittente_ba` (quanto pesa) + `fn_guard_ba_cambio_emittente` (fail-fast) | `20_code` | ⛔ **L3** dell'altro brief, per la parte «commesse» | la forma **b** |
| **M2** | `fn_guard_ba_gestore_globale_storia` — il **raggio N** | `20_code` | M1 | lo spostamento del default globale |
| **M3** | `trgfn_efba_guard_storia_emittente` + trigger `a10` sui **tre movimenti** | `20_code` | M1, M2 | il cancello |
| **M4** | codice `E_BA_EMITTENTE_CON_STORIA` + messaggio | `80_data` | — (stesso PR di M3) | il cancello CI dei codici |
| **M5** | pgTAP | `db/pgtap` | M3 | — |
| **M6** | documentazione | `docs/` | tutti | — |
| **M7** | ⏸️ capability `fn_check_ba_emittente_puo_cambiare` per il gesto FE | `20_code` | M1 | **non si costruisce finché il FE non la chiede** |

⭐ **M1 si può spezzare in due consegne**, se serve andare prima: la parte
«fatture» non dipende da niente e chiude il caso fiscale — quello che Tid ha
sollevato — mentre la parte «commesse» aspetta L3 dell'altro brief (D-4). ⚠️ Ma
consegnarle a distanza apre la finestra del §2.1: raccomandato stesso rilascio.

---

### 6.1 M1 — «Quanta storia ha questo billing account», e il cancello

**File**: `20_code/anagrafiche/AAAAMMGG-NN-create-fn-storia-emittente-ba-mctit.yaml`
· `20_code/anagrafiche/AAAAMMGG-NN-create-fn-guard-ba-cambio-emittente-mctit.yaml`

```sql
anagrafiche.fn_get_storia_emittente_ba(
    p_billing_account_id anagrafiche.billing_account.id%TYPE)
  RETURNS TABLE (n_fatture bigint, n_commesse bigint)
  STABLE SECURITY DEFINER SET search_path TO 'pg_catalog','public'
```

Due `count(*)` su `billing_account_id`, e basta. ⚠️ **`SECURITY DEFINER`, per la
stessa ragione scritta dentro `fn_guard_albero_ba_emittente`**: `vendite.fatture`
e `vendite.commesse` hanno la RLS accesa, e da `SECURITY INVOKER` la storia di un
altro emittente sarebbe **invisibile** — il guard direbbe «nessuna storia, si può
spostare» proprio nel caso che deve bloccare
([[reference_trigger_guard_legge_sotto_rls]]).

⭐ **Restituisce i conteggi, non un booleano, e serve**: il messaggio che legge
l'operatore deve dire *quante* fatture e *quante* commesse — un «non si può»
senza numeri manda a cercare a mano cosa c'è sotto. ⚠️ E i due conteggi sono
indicizzati (`ix_fatture_ba_data`, `ix_commesse_ba_utility`): è una lettura di
struttura, non una misura di popolazione.

```sql
anagrafiche.fn_guard_ba_cambio_emittente(
    p_billing_account_id  anagrafiche.billing_account.id%TYPE,
    p_emittente_sr_prima  anagrafiche.emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id%TYPE,
    p_emittente_sr_dopo   anagrafiche.emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id%TYPE)
  RETURNS void
  SECURITY DEFINER SET search_path TO 'pg_catalog','public'
```

1. `p_billing_account_id IS NULL` → `RETURN` (è la riga del gestore globale: la
   guarda M2);
2. `prima IS NOT DISTINCT FROM dopo` → `RETURN` — ⭐ **è la riga che tiene aperta
   la manutenzione ordinaria**: cancellare un mapping specifico quando il gestore
   globale punta **allo stesso** emittente non sposta niente e deve passare;
3. legge i conteggi; se entrambi a zero → `RETURN`;
4. altrimenti solleva `E_BA_EMITTENTE_CON_STORIA`.

⛔ **Nessuna GUC di override, nessuna eccezione per il pregresso**: è la stessa
frase che il `COMMENT` di `fn_guard_albero_ba_emittente` porta già scritta —
*«un invariante con l'interruttore non è un invariante»*.

⚠️ **Nessun controllo sui figli.** Un BA il cui *figlio* ha storia è già protetto
dal guard dell'albero (`fn_guard_albero_ba_emittente`): spostare il padre da solo
renderebbe l'albero misto e viene respinto lì, con un errore che dice la cosa
giusta. Aggiungere qui una risalita sarebbe un secondo presidio sullo stesso
caso, con due messaggi diversi per lo stesso rifiuto.

---

### 6.2 M2 — Il raggio N: spostare il gestore globale

**File**: `20_code/anagrafiche/AAAAMMGG-NN-create-fn-guard-ba-gestore-globale-storia-mctit.yaml`

Calco di `anagrafiche.fn_guard_albero_ba_gestore_globale`, che questo stesso
movimento lo presidia già per l'omogeneità dell'albero. La riga con
`billing_account_id IS NULL` e `is_default = true` decide l'emittente di **tutti
i BA non mappati**: cambiarla li sposta in blocco.

⇒ Il guard blocca se **esiste almeno un** billing account senza mapping specifico
che abbia storia:

```sql
EXISTS (SELECT 1 FROM anagrafiche.billing_account ba
         WHERE NOT EXISTS (SELECT 1 FROM anagrafiche.emittenti_fiscali_billing_account e
                            WHERE e.billing_account_id = ba.id)
           AND (<ba ha fatture> OR <ba ha commesse>))
```

⭐ **Un solo semi-join, non un ciclo**: al gemello dell'albero serve visitare ogni
BA perché deve dire *quale coppia* è mista; qui la domanda è «esiste storia», e
la risposta è la stessa dopo il primo che la trova.

⚠️ **In pratica questo cancello chiude quasi sempre**, ed è corretto: spostare il
gestore globale su un'installazione che ha già fatturato vorrebbe dire
ri-attribuire retroattivamente l'emittente di tutto ciò che non ha un mapping
suo. Non è una configurazione, è una riscrittura della storia.

---

### 6.3 M3 — Il cancello: i **tre movimenti**, come il fratello che c'è già

**File**: `20_code/anagrafiche/AAAAMMGG-NN-create-trgfn-efba-guard-storia-emittente-mctit.yaml`

```text
anagrafiche.trgfn_efba_guard_storia_emittente()
trg_emittenti_fiscali_ba_a10_guard_storia_emittente_ins_upd_dlt
    BEFORE INSERT OR UPDATE OR DELETE ON anagrafiche.emittenti_fiscali_billing_account
```

⚠️ **In un `BEFORE DELETE` il ritorno è `OLD`, non `NEW`** (`NEW` lì è `NULL`, e
un `RETURN NULL` **annulla la cancellazione in silenzio**): è la differenza fra
un guard che blocca dicendolo e uno che fa sparire il gesto senza errori. Il
fratello `z95` non ha il problema perché è `AFTER` e ritorna `NULL` di proposito.

La tassonomia dei movimenti è **quella già scritta** in
`trgfn_efba_guard_albero_emittente`, e non si reinventa:

| Movimento | «prima» | «dopo» |
| --- | --- | --- |
| `INSERT` di un mapping specifico | l'emittente **del gestore globale** | `NEW.emittente_soggetto_ruolo_id` |
| `UPDATE` dell'emittente sul mapping | `OLD.emittente_soggetto_ruolo_id` | `NEW.emittente_soggetto_ruolo_id` |
| `UPDATE` che sposta il mapping da un BA a un altro | si chiama il guard **due volte**, una per BA | idem |
| `DELETE` del mapping specifico | `OLD.emittente_soggetto_ruolo_id` | l'emittente **del gestore globale** |
| riga con `billing_account_id IS NULL` (il default) | → delega a **M2** | |

⚠️ **`BEFORE` e non `AFTER`, ed è una differenza motivata dal fratello.** Il
guard dell'albero è `z95 AFTER` perché *rilegge il mapping* per risolvere
l'emittente: gli serve lo stato finale. Questo no — «prima» e «dopo» li ricava da
`OLD`/`NEW`, quindi può stare in `a10`, che è la fase dei guard di blocco
(`linee-guida-trigger.md`).

⛔ **E una trappola da non prendere: sul `DELETE` non si usa
`script.fn_get_ba_emittente_sr_id` per calcolare il «dopo».** In un `BEFORE
DELETE` la riga c'è ancora, quindi il risolutore risponderebbe **il mapping che
si sta cancellando** — cioè «prima» e «dopo» coinciderebbero e il guard non
scatterebbe mai. Il «dopo» del `DELETE` si legge **direttamente** dalla riga
`is_default`.

⚠️ I due trigger convivono senza ordine critico (`a10` prima di `z95`), e sono
complementari: uno dice «l'albero non può diventare misto», l'altro «la storia
non si sposta».

---

### 6.4 M4 — Il codice (`80_data`)

⛔ **Solo append ai CSV, nessun loader nuovo**
([[feedback_messaggi_errore_no_new_loader]]).

| Campo | Valore |
| --- | --- |
| `codice` | `E_BA_EMITTENTE_CON_STORIA` |
| `classe` | **`CONFLITTO_STATO`** |

⭐ **Perché `CONFLITTO_STATO` e non `DATO_ERRATO`**, ed è la descrizione della
classe a deciderlo, testuale: *«non c'è un campo da correggere, è la situazione
che non lo consente»*. Qui l'emittente scelto non è sbagliato — è la storia già
scritta che non lo ammette. È lo stesso ragionamento con cui
`E_EMITTENTE_NON_MODIFICABILE` è passato da 400 a 409 il 2026-08-06.
⇒ Ne discende che **nel contesto non va la chiave `campo`**: non c'è nessun campo
da accendere.

**Il messaggio** (`VARIADIC` = la frase che legge una persona — mai un nome di
colonna o di parametro):

> `Il cliente %s ha già %s fatture e %s commesse con l'emittente %s: spostarlo lascerebbe quei documenti senza il cliente a cui appartengono.`

⚠️ **Arità**: quattro `%s`, quattro valori
([[reference_messaggi_errore_segnaposto_rompe_format]]).
⚠️ `causa` e `soluzione` vanno compilate: la `soluzione` è la **D-1**, scritta in
italiano comprensibile — *«se il cliente è passato davvero all'altro emittente,
si apre presso di lui una nuova fornitura; i documenti già emessi restano con chi
li ha emessi»* ([[feedback_doc_linguaggio_comprensibile]]).
⚠️ L'`id` di `messaggi_errore.csv` è un progressivo da **rileggere** al momento
di scrivere.

**Nel contesto** (`jsonb`) vanno `billing_account_id`, il `codice` del BA,
`n_fatture`, `n_commesse`, `emittente_sr_prima`, `emittente_sr_dopo`.

⏸️ **`bersaglio`: non ora.** Sarebbe utile (*«vai a vedere le fatture che
bloccano»*), ma la regola dice che in testa va **la cosa su cui l'errore è
successo** — il billing account — e `BILLING_ACCOUNT` **non è** a catalogo in
`config.tipi_entita` (ci sono `COMMESSA`, `FATTURA`, `ORDINE_VENDITA`,
`PREVENTIVO`, `CONTRATTO`, `LOTTO`, `FLUSSO`, `TASK_RUN`,
`DEFINIZIONE_WORKFLOW`). Metterci in testa una `FATTURA` violerebbe l'ordine, che
è portante e non estetico. ⇒ Se lo si vuole, prima si aggiunge
`BILLING_ACCOUNT` a `tipi_entita.csv` (con `modo_risoluzione_emittente` e
`key_selector`), e diventa una decisione sua.

---

### 6.5 M5 — I presidi

**File**: `db/pgtap/anagrafiche/test-ba-cambio-emittente-storia-v1.sql`
(dal template, con le tre righe di preambolo obbligatorie).

1. BA **senza storia**: `DELETE` del mapping ⇒ **passa** (la finestra di
   correzione del §2.3 esiste ancora);
2. BA **senza storia**: `INSERT` del mapping sull'altro emittente ⇒ passa;
3. BA **con una fattura**: `DELETE` del mapping ⇒ `throws_ok(…, 'P0001')` +
   `throws_like` sulla frase;
4. BA **con una commessa e nessuna fattura**: `DELETE` ⇒ blocca (è il pezzo che
   dipende da L3 dell'altro brief);
5. `UPDATE` del mapping verso **lo stesso** emittente ⇒ **passa** (il ramo 2 del
   §6.1: se non si sposta niente, non si blocca niente);
6. spostamento del **gestore globale** con un BA non mappato che ha storia ⇒
   blocca (M2).

⚠️ Le fixture **si fabbricano** i due emittenti, i due BA e i documenti: un test
che cerca fra i dati esistenti passa a vuoto in CI (`AGENTS.md`, corollario sui
test).
⚠️ `throws_ok` **sempre con lo SQLSTATE** ([[feedback_pgtap_throws_ok_senza_sqlstate]]).
⚠️ La fixture scrive in `vendite.fatture` e `vendite.commesse` **sotto RLS**: va
costruita con la veste operatore giusta, o non vede quello che ha appena scritto
([[reference_pgtap_scope_svuotare_user_id_non_e_fail_closed]]).
⚠️ Prima e dopo: `scripts/pgtap-baseline.sh anagrafiche vendite`.

---

### 6.6 M6 — Documentazione

| Dove | Cosa |
| --- | --- |
| `docs/it/dbzero/anagrafiche/manual/` | scheda per le tre funzioni nuove |
| `docs/it/guide/generazione-cliente.md` | «l'emittente di un cliente si sceglie una volta»: la finestra di correzione e cosa la chiude |
| `docs/it/guide/fatturazione.md` | il perché fiscale, in linguaggio non tecnico |
| `COMMENT ON` | su ogni funzione, dentro il changeSet che la crea — citando **il nome del brief**, mai il path `work-in-progress/` ([[feedback_no_path_wip_negli_yaml]]) |

---

### 6.7 Consegne fuori dal database

**BE-1 — niente di obbligatorio, e va verificato che sia vero.** La classe
`CONFLITTO_STATO` è già mappata a 409 dalla catena centralizzata
(`config.classi_errore` → `apps/core/services/error_policies.py`): l'endpoint che
cancella e crea i mapping (`EmittentiFiscaliBillingAccountRepository`) dovrebbe
restituire il 409 con il messaggio senza modifiche. ⚠️ **Da provare, non da dare
per scontato**: se quel percorso cattura `Exception`, il messaggio del database si
perde e l'operatore legge un 500 muto.

**FE-1 — il gesto va spento prima, non punito dopo.** Oggi l'operatore scopre il
divieto premendo. La forma giusta è la capability (`linee-guida-sql.md` §12), e la
sua sede DB è **M7** — che però ⛔ **non si costruisce a vuoto**: si scrive quando
il frontend la chiede, e sul **dettaglio** del cliente, mai per riga di lista
([[reference_capabilities_solo_su_dettaglio]]).

---

### 6.8 Cosa questo piano **non** costruisce

* ⛔ **Nessuna colonna «BA gemello di»** (D-3): il legame è il soggetto, e c'è già.
* ⛔ **Nessun riallineamento a cascata** delle commesse non fatturate (D-2).
* ⛔ **Nessuna modifica a `uq_billing_instance_utility`**: la forma **c** si fa con
  una fornitura nuova, non con un billing account gemello (D-1).
* ⛔ **Nessun `UPDATE` di comodo** per sanare un caso: se ne esistono, si guardano
  e si decidono, non si riscrivono alla cieca
  ([[feedback_dev_db_non_e_ricostruito_da_zero]]).
* ⛔ **Non si tocca il guard dell'albero** (§7): è presidiato e non va ridiscusso.

## 7. Cosa NON è in questo brief

* **L'invariante dell'emittente sulla commessa** (nullable, coerenza col BA):
  [brief-db-emittente-commessa-invariante.md](brief-db-emittente-commessa-invariante.md).
* **L'omogeneità dell'albero dei BA**, che è già presidiata e non va ridiscussa
  (`fn_guard_albero_ba_emittente`).

---

## 8. Registro

### 2026-08-26 · Nascita

Estratto dalla D-3 del brief sull'invariante della commessa, su richiesta di Tid
di **separare le competenze**: là un difetto con un rimedio chiaro, qui una
domanda di dominio con implicazioni fiscali, che ha bisogno di essere pensata e
non di essere programmata.

⭐ La struttura conferma l'intuizione che l'ha fatto nascere: la fattura congela
il proprio emittente (`NOT NULL` + `emittente_snapshot`), quindi spostare il
billing account non sposta i documenti — **li orfana**, e il cliente sparisce
dalla vista di chi quelle fatture le ha emesse.

⛔ Nessuna decisione presa, nessun file scritto.

### 2026-08-26 · Le quattro domande chiuse, e il piano (§6)

Richiesta di Tid: *«prepara un piano all'interno dei documenti per l'esecuzione;
credo che non ci siano domande aperte»*. Rilette una per una contro la
**struttura** — non contro i dati — le quattro si chiudono davvero, e tre lo
fanno per una ragione che nel brief non c'era ancora:

* ✅ **D-1 → forma b**, e la **c** non è codice: `uq_billing_instance_utility`
  (`UNIQUE (istanza_utility_id, utility_id)`) rende il «BA gemello» **non
  scrivibile**. La forma pulita della c esiste già senza database: una fornitura
  nuova presso l'altro emittente.
* ✅ **D-2 → storia = ciò che porta una copia congelata dell'emittente**:
  `vendite.fatture` e `vendite.commesse`. ⛔ Ordini e DDT **no**, e non per
  clemenza: hanno un `trgfn_*_guard_emittente_ba` che li ricontrolla a ogni
  scrittura, quindi la loro copia non invecchia.
* ✅ **D-3 → il soggetto, e c'è già**: `billing_account.soggetto_ruolo_id` è
  `NOT NULL`. Nessuna colonna nuova.
* ✅ **D-4 → confermato che il cantiere gemello non aspetta**, ⚠️ **ma la
  dipendenza è nell'altro verso** (§2.1): è questo che ha bisogno di quello.

⭐ **La cosa che ha cambiato lo stato del documento** è il §2.1: nel momento in
cui l'altro cantiere mette il `NOT NULL`, la commessa porta **una copia
congelata** dell'emittente, e il suo guard — che scatta su `UPDATE OF`, per non
congelare le commesse — di proposito non la difende. ⇒ Questo brief smette di
essere una riflessione facoltativa e diventa il presidio che chiude l'invariante
dall'altro capo.

⚠️ Due letture di struttura che il piano ha dovuto fare, e non erano nel brief:
il backend **non ha nessun `UPDATE`** sul mapping (si sposta con `DELETE` +
`INSERT`, §2.2 — quindi il guard sull'`INSERT` da solo non presidierebbe niente),
e il mapping **nasce da solo** con l'emittente dell'operatore
(`trgfn_billing_account_link_ef`, §2.3 — quindi un BA non è mai «senza
emittente», e quando nasce sbagliato lo nasce subito).

⛔ Nessun file scritto, nessuna migrazione applicata: sette lotti in §6.0,
l'esecuzione parte su «procedi».

### 2026-08-26 · Esecuzione — M1, M2, M3, M4, M5

> ⛔ **File scritti, migrazione NON applicata** — *vero al momento in cui questa
> voce è stata scritta; Tid ha applicato più tardi lo stesso giorno.*
> ([[feedback_mai_applicare_migrazioni_db]]).

| # | File | Lotto |
| --- | --- | --- |
| 46 | `20_code/anagrafiche/…-create-fn-storia-emittente-ba-mctit.yaml` | **M1a** |
| 47 | `20_code/anagrafiche/…-create-fn-guard-ba-cambio-emittente-mctit.yaml` | **M1b** |
| 48 | `20_code/anagrafiche/…-create-fn-guard-ba-gestore-globale-storia-mctit.yaml` | **M2** |
| 49 | `20_code/anagrafiche/…-create-trgfn-efba-guard-storia-emittente-mctit.yaml` | **M3** |
| — | `80_data/sql/config/*.csv` — `E_BA_EMITTENTE_CON_STORIA` (`CONFLITTO_STATO`, id 1006) | **M4** |
| — | `db/pgtap/anagrafiche/test-ba-cambio-emittente-storia-v1.sql` `plan(8)` | **M5** |

**⚠️ Due scarti dal piano.**

1. ⭐ **M2 prende due parametri (`prima`, `dopo`) invece di nessuno.** Il gemello
   dell'albero (`fn_guard_albero_ba_gestore_globale`) non ne ha perché è `AFTER`
   e rilegge; questo è chiamato da un `BEFORE`, dove «prima» e «dopo» vivono solo
   in `OLD`/`NEW` e vanno passati.
2. ⭐ **M2 non compone il messaggio: delega a M1b.** Trova il primo billing
   account non mappato con storia (`ORDER BY` + `LIMIT 1`, deterministico) e gli
   passa la palla. Così l'errore del raggio N **nomina un cliente vero** invece
   di dire «da qualche parte», e l'implementazione resta una sola.

⭐ **Il pgTAP prova la forma «b» in coppia**, ed è la parte che conta: la
**stessa** chiamata sullo **stesso** cliente, prima e dopo che gli sia passata
una commessa — passa, poi blocca. È l'unico modo di dimostrare che la finestra
di correzione esiste davvero e non è solo dichiarata. ⚠️ Il guard si chiama
**direttamente**, con `prima`/`dopo` espliciti: il percorso via trigger su due
emittenti diversi vorrebbe un secondo emittente fiscale nello scope
dell'operatore, che quella fixture non fabbrica — il montaggio del trigger sui
**tre** movimenti è presidiato strutturalmente (`pg_trigger.tgtype`).

**Cosa resta**

* ~~**M6** — documentazione.~~ ✅ **Fatto il 2026-08-26**: 4 pagine `manual/`
  (`fn_guard_ba_cambio_emittente`, `fn_get_storia_emittente_ba`,
  `fn_guard_ba_gestore_globale_storia`, `trgfn_efba_guard_storia_emittente`) +
  `generazione-cliente.md` e `fatturazione.md`.
  ⛔ E `generazione-cliente.md` **non nominava mai l'emittente**: il legame
  nasce lì, da un trigger, con quello dell'operatore che sta creando il cliente —
  quindi un cliente può *nascere sbagliato* e non era scritto da nessuna parte.
* ⏸️ **M7** — la capability per il gesto FE: **non si costruisce** finché il
  frontend non la chiede.
* **BE-1** — verificare che l'endpoint del mapping restituisca davvero il 409 e
  non lo mangi in un `except Exception` (§6.7).
* ⚠️ Il pgTAP **non è stato eseguito**: serve il database, e l'apply non è
  autorizzato.

### 2026-08-26 · Le note che raccontavano il modello di prima

Segnalazione di Tid: *«quelle note che accennano al fatto che il billing account
potesse cambiare emittente vanno sistemate»*.

⭐ **Aveva ragione, e l'origine è legittima**: prima del `-49` quel legame **era**
un attributo mobile, e la documentazione lo diceva perché allora era vero. Tre
frasi, tutte **dentro il database**:

* `trgfn_efba_guard_albero_emittente` — *«se il mapping viene spostato da un BA a
  un altro (caso teorico: la UNIQUE lo rende raro)»*;
* `fn_guard_albero_ba_emittente` — *«il movimento che si dimentica sempre:
  cambiare l'emittente di un BA…»*;
* `fn_guard_albero_ba_gestore_globale` — *«cambia in blocco l'emittente di tutti
  i BA senza mapping specifico»*.

Nessuna è falsa **sul meccanismo** — quei guard devono ancora coprire quei
movimenti — ma tutte lasciano credere che lo spostamento sia ordinario.

⛔ **E non si è scritto «non si può fare»**, che era la formulazione proposta:
sarebbe sbagliato quanto la nota vecchia, nell'altra direzione. La decisione D-1
è la forma **b** — *libero finché non c'è storia, vietato dopo* — e la ragione
sta nel §2.3: un billing account **nasce già agganciato** all'emittente di chi lo
crea, quindi può nascere sbagliato. Con un legame immutabile quell'errore non si
correggerebbe più. ⇒ La frase giusta nomina la **condizione**, non il divieto.

**`20260826-53`** — quattro `COMMENT ON`, nessuna funzione ricreata: è l'unico
modo di correggere una frase che vive nel database senza toccare il codice che la
porta. ⭐ Aggiunta anche `trgfn_billing_account_link_ef`, che nell'elenco non
c'era: è la funzione che **apre** la finestra di correzione, ed è la pagina su
cui il lettore arriva quando si chiede da dove venga l'emittente di un cliente.

**Doc concettuale**: la sezione «Quando questo legame si può ancora cambiare»
sulla pagina della tabella (con la tabella dei due casi) + una nota su ognuna
delle quattro funzioni.
