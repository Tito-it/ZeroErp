# Brief DB — Lo storico porta il proprio perimetro, e non lo ricalcola

> Stato: 🟠 **analisi e disegno — non iniziato.**
> Origine: **D3** di
> [migliorie-generali-da-test-valutazione.md](migliorie-generali-da-test-valutazione.md).
> Eredita il §9 di
> [brief-db-perimetro-emittente-righe-documento.md](../work-done/brief-db-perimetro-emittente-righe-documento.md),
> **che su questo punto sbagliava due volte** — vedi §6.
>
> Stima: **≈ 3 giornate**, metà delle quali disegno e presidio.
> ⛔ **Il lavoro è UNO, non 120**: la forma delle tabelle di storico è uniforme e
> generata da `dbops.fn_ensure_storico_table`. Chi legge «120 tabelle» e stima di
> conseguenza sta stimando il problema sbagliato.

---

## 1. Il difetto, detto sul modello

> **Lo storico di una riga protetta è la stessa informazione della riga.**

`vendite.fatture` è protetta da due policy. Ogni sua **versione precedente** non
lo è. La storicizzazione è automatica e cattura lo snapshot **completo** della
riga: chi non può vedere una fattura può leggerne tutte le revisioni.

⇒ Il perimetro non è una proprietà del *dato corrente*: è una proprietà del
**fatto**. Se vale per la riga, vale per la sua storia.

⚠️ **E lo `storico` non entra nel criterio del presidio del perimetro**
(`dbops.vw_rls_perimetro_scoperto`): quelle tabelle sono **gemelle** delle madri,
non figlie — nessuna FK le lega, e il criterio guarda le FK. Non è una svista del
presidio: è che questo è un meccanismo **diverso**, e vuole una difesa sua.

---

## 2. La decisione portante: si CATTURA, non si deriva

> **Ogni tabella di storico porta il proprio scope in una colonna, valorizzata
> alla scrittura e mai più ricalcolata. La policy legge quella colonna.**

Tre ragioni, tutte sul **modello**. ⛔ Nessuna delle tre poggia su un conteggio di
righe: valgono su un database vuoto come su uno pieno.

### 2.1 Una riga di storico è un fatto DATATO, e il perimetro fa parte del fatto

Registra com'era una riga in un istante. La sua verità è quella di **allora**.

⇒ Se il perimetro si ricalcolasse a runtime risalendo alla madre **viva**, il
presente riscriverebbe la visibilità del passato: un documento che cambiasse
emittente cambierebbe **chi può leggere la propria storia**.
⭐ *Un archivio che cambia quando cambia il presente non è un archivio.*

### 2.2 Il modello AMMETTE la riga senza madre — per progetto, non per incidente

`dbops.fn_ensure_storico_table` **non genera la foreign key**, e lo dichiara nel
proprio codice:

> *«non si genera più la fk perché bloccerebbe la cancellazione delle righe della
> tabella e non è corretto»*

⇒ Una policy che risale alla madre ha un ramo **non determinabile per
contratto**. ⛔ E va gestito **anche se oggi quel ramo fosse vuoto**: zero
occorrenze non significa che il caso non esiste, significa che non c'è ancora un
controesempio.

### 2.3 Il dato è disponibile ESATTAMENTE quando serve

`script.trgfn_storico_generic` è montato `BEFORE UPDATE OR DELETE` e serializza
`to_jsonb(NEW)` / `to_jsonb(OLD)`: **quando scrive ha in mano la riga intera, e
la madre esiste ancora.**

⇒ Il perimetro è **catturabile** nel momento in cui è certo. Non c'è nessun
bisogno di ricostruirlo dopo, quando può non esserci più.

---

## 3. Perché una COLONNA e non lo snapshot JSONB

Lo snapshot contiene già i valori della riga, quindi la tentazione è leggere di
lì (`snapshot ->> 'emittente_soggetto_ruolo_id'`). ⛔ È la scelta peggiore delle
due, per tre ragioni **di progetto**:

| | |
| --- | --- |
| **Contratto contro serializzazione** | lo snapshot è *come* la riga è stata salvata, non *che cosa* la riga promette. Se cambia forma — una colonna rinominata, uno snapshot ridotto — la policy **si rompe in silenzio**, e il sintomo di una policy rotta è *vedere di più* |
| **Costo per riga** | una policy è valutata **per ogni riga letta**. Un `->>` con cast non usa indici: è un costo strutturale, non un dettaglio di tuning |
| **Il caso del satellite** | una riga di `fatture_righe` non ha l'emittente **nemmeno nello snapshot**, perché non ce l'ha la riga. Con la colonna il trigger risale una volta sola e congela; con il JSON non c'è niente da leggere |

---

## 4. La forma, in concreto

### 4.1 La colonna

Il generatore aggiunge a ogni tabella di storico **una** colonna di scope,
valorizzata dal trigger. ⚠️ Il nome e il tipo si decidono in fase di disegno, e
la domanda vera è **quante colonne servono**: gli assi di perimetro in uso oggi
sono l'**emittente** (per soggetto-ruolo o per emittente fiscale) e il **billing
account**. ⛔ Decidere «una colonna generica» o «una per asse» è la prima cosa da
fissare: cambiarla dopo significa rigenerare 120 tabelle.

### 4.2 La mappa: dove sta lo scope, per ogni madre

⚠️ `trgfn_storico_generic` è **generico** — non sa quale sia la colonna di scope
della madre che sta specchiando. ⇒ Serve una **mappa dichiarata**, nello stile di
`dbops.fk_index_policy`: per ogni tabella, *dove* si prende lo scope.

| Caso | Come si ricava |
| --- | --- |
| la madre porta la colonna (`vendite.fatture`, `vendite.commesse`) | **copia diretta** dalla riga che il trigger ha già in mano |
| la madre è un satellite (`vendite.fatture_righe`) | **risalita una volta sola**, alla scrittura, e si congela il risultato |
| la madre non è in RLS | **nessuno scope**: la tabella di storico non si arma, e la riga di mappa lo **dichiara** |

⭐ La mappa è anche il registro del debito: una tabella di storico senza riga di
mappa è una tabella che nessuno ha ancora guardato, e il presidio la deve vedere.

### 4.3 La policy

Una sola forma, generata: veste `OPERATORE`, `FOR SELECT`, sulla colonna di
scope. ⚠️ **`FOR SELECT` e non `FOR ALL`**: lo storico lo scrive il trigger, non
l'applicazione — e una `WITH CHECK` su una scrittura di sistema non difende
niente e può bloccare la storicizzazione.

---

## 5. I passi, e il costo

| # | Passo | Stima |
| --- | --- | --- |
| 1 | **Il disegno**: quante colonne di scope, come si chiamano, la forma della mappa | ½ g — ⭐ **è la parte che conta** |
| 2 | `dbops.fn_ensure_storico_table`: colonna + policy nel `format()` già esistente | ½ g |
| 3 | La **mappa** (`dbops.storico_scope_policy` o simile) + il suo seed | ½ g |
| 4 | `trgfn_storico_generic`: valorizzare lo scope leggendo la mappa | ½ g |
| 5 | **Backfill** delle righe già scritte: uno script parametrico, non uno per tabella | ½ g |
| 6 | **pgTAP**: una storico nuova *nasce* protetta; lo scope è **congelato** e non segue la madre; una tabella senza riga di mappa è **vista** | ½ g |

⇒ **≈ 3 giornate.**

### ⛔ E si fa PRIMA che `acquisti` e `magazzino` crescano

Il §9 del brief del perimetro diceva il contrario — *«un generatore ha senso
quando le madri sono ferme»* — e **quell'argomento è rovesciato**: vale per un
lavoro **manuale** (120 policy a mano si rifanno a ogni tabella nuova), ma un
generatore **esiste proprio per assorbire le tabelle nuove**.

⇒ Farlo adesso significa che le tabelle di `acquisti` e `magazzino` **nascono
protette**. Farlo dopo significa un backfill più grande e, nel frattempo, uno
storico aperto **anche sui domini nuovi**.

---

## 6. ⛔ Le due cose che il §9 sbagliava, e perché sono scritte qui

Restano registrate perché sono il tipo di errore che **ferma o svia un cantiere**,
ed è già successo tre volte nel registro del perimetro (§11.12 e §11.18 di quel
brief): una *ragione* scritta male non viene riletta da nessuno.

1. **«Derivando lo scope dalla madre»** — è la formula che non regge (§2.1, §2.2).
2. **«Aspettare che le madri siano ferme»** — l'argomento giusto porta alla
   conclusione **opposta** (§5).

⚠️ **E una terza, di metodo, che riguarda come è nata questa analisi**: la prima
stesura portava come argomento il numero di righe orfane misurato sul database di
sviluppo. ⛔ È una fotografia, e *le decisioni non si prendono sui dati di test,
che possono non essere veritieri* (Tid, 2026-09-11). L'argomento vero è **2.2**:
il generatore non crea la FK **di proposito**, quindi il caso esiste nel modello
— e quel fatto vale identico su un database vuoto.

---

## 7. Cosa NON fare

* ⛔ **niente 120 policy scritte a mano**: nascerebbero disallineate, e la prima
  tabella nuova le renderebbe incomplete;
* ⛔ **niente scope letto dal JSONB** (§3);
* ⛔ **niente risalita a runtime alla madre** (§2.1, §2.2);
* ⛔ **niente `FOR ALL`** su una tabella che scrive solo il trigger (§4.3);
* ⚠️ **non fermarsi allo `storico`**: `dbops.audit_log` è la **stessa forma** —
  `params` e `result` in JSONB contengono argomenti ed esito di operazioni su
  documenti protetti, e la tabella è senza RLS con `zeroerp_app` che ci ha
  `SELECT, INSERT, UPDATE, DELETE`. È dichiarato nel D3 come secondo caso: non è
  questo brief, ma va deciso se ci entra.

---

*Analisi 2026-09-11 — letture di **struttura** sul database `zeroerp`
(`pg_proc`, `pg_trigger`, `pg_class.relrowsecurity`, colonne delle tabelle di
storico). ⛔ Nessun conteggio di righe è usato come argomento.*
