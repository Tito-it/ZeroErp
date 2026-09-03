# Guida – Mandare in pensione una voce di catalogo (`obsoleto_dal`)

> (latest review 30-06-26)
>
> Destinatari: analisti funzionali, sviluppatori database e backend
>
> Vedi anche
>
> * [Brief – Deprecabilità del catalogo](/dev/work-done/brief-db-deprecabilita-catalogo-vs-istanze)
> * [Brief – Filtro lookup + guard `obsoleto_dal`](/dev/work-done/brief-db-obsoleto-dal-filtro-lookup-e-guard)
> * [Linee guida SQL](/linee-guida-sql)
> * [Guida – Configurazione delle pratiche](/guide/gestione-pratiche-configurazione)

---

## In una frase

A volte una voce di catalogo (un tipo di pratica, un'aliquota IVA, un termine di pagamento…)
**non va più usata per le cose nuove**, ma **non si può cancellare** perché documenti e pratiche
già fatti la usano. `obsoleto_dal` serve esattamente a questo: **mandarla in pensione** senza
rompere lo storico.

> 💡 **La metafora**: è come un **modello di prodotto fuori produzione**. Non lo vendi più (non
> lo offri per un nuovo ordine), ma chi l'ha già comprato continua ad avere garanzia e ricambi.
> La voce "in pensione" resta valida per chi la usava già; semplicemente non la si sceglie più
> per il nuovo.

---

## I due concetti da non confondere

Una voce di catalogo ha **due interruttori diversi**, che rispondono a due domande diverse:

| Interruttore | Domanda a cui risponde | Quando lo usi |
|---|---|---|
| **`attivo`** | *"È una voce **valida**?"* | Spegnerlo significa *"questa voce non esiste più, per nessuno"*. Da non usare se qualcuno la sta già referenziando: rompe i dati esistenti. |
| **`obsoleto_dal`** | *"È ancora **scegliibile per il nuovo**?"* | È quello giusto per "mandare in pensione": la voce resta valida per lo storico, ma sparisce dalle scelte per il nuovo. |

> ⚠️ **L'errore classico** è usare `attivo = false` per "ritirare" una voce. Sembra funzionare,
> ma i documenti che la usano filtrano per `attivo` → si rompono. E giustamente il database lo
> impedisce. Per "ritirare" si usa **sempre** `obsoleto_dal`, mai `attivo`.

### I tre stati di `obsoleto_dal`

È semplicemente una **data**:

| Valore | Significato |
|---|---|
| **vuoto** (NULL) | Voce pienamente selezionabile. |
| **data futura** | **Ritiro programmato**: ancora selezionabile fino a quella data, poi non più. |
| **data passata (o oggi)** | Voce **in pensione**: non più offerta per il nuovo. |

---

## Cosa fa il sistema, da solo

Una volta che una voce è "in pensione", scattano **due protezioni automatiche** — più una
garanzia sullo storico:

1. **Le tendine la nascondono.** Le liste di scelta "per il nuovo" non la mostrano più. (Chi
   consulta lo *storico* o *filtra* può invece ancora vederla: serve a ritrovare le pratiche
   vecchie di quel tipo.)
2. **Il database rifiuta di crearci sopra cose nuove.** Anche se qualcuno provasse a forzare la
   creazione (via importazione, script, errore di programma), il database **blocca** con un
   messaggio chiaro. È la rete di sicurezza: *la tendina nasconde, il database rifiuta*.
3. **Lo storico resta intatto.** Le pratiche e i documenti già creati su quella voce continuano
   a funzionare e ad avanzare normalmente. Niente viene cancellato o invalidato.

---

## Come mettere in pensione una voce (operativo)

Per chi gestisce i dati, l'azione è una sola: **valorizzare la data `obsoleto_dal`** della voce.

* Vuoi ritirarla **da subito**? Metti la data di **oggi**.
* Vuoi un **ritiro programmato** (es. "da inizio anno prossimo")? Metti la **data futura**: fino
  a quel giorno resta selezionabile.

Non serve (e non si deve) cancellare la voce né toccare `attivo`. Per **rimetterla in uso**,
basta svuotare di nuovo `obsoleto_dal`.

---

## La ricetta per lo sviluppatore (riuso su un nuovo catalogo)

Il bello è che il meccanismo è **generico**: per applicarlo a un nuovo catalogo (es. l'IVA) il
lavoro è minimo, perché le funzioni "cervello" esistono già.

### Passo 1 — Aggiungi la colonna al catalogo

Una sola colonna sulla tabella di catalogo:

```sql
ALTER TABLE <schema>.<catalogo>
  ADD COLUMN IF NOT EXISTS obsoleto_dal date NULL;
```

### Passo 2 — La selezione si adegua da sola

Il lookup generico [`dbops.fn_get_lookup_codici`](/dbzero/dbops/funzioni/fn_get_lookup_codici)
**rileva da solo** la colonna `obsoleto_dal` (esattamente come fa con `attivo`). **Non c'è
niente da fare lato database.** Lato applicazione, chi serve la "selezione per il nuovo" chiede
di nascondere gli obsoleti (parametro `includi_obsoleti = false`); chi serve filtri/storico
lascia il valore di default e li vede tutti.

> Se il catalogo **non ha** la colonna `obsoleto_dal`, il lookup funziona come prima e restituisce
> tutto: nessuna configurazione per-tabella, nessuna rottura.

### Passo 3 — Vieta le nuove istanze (la rete di sicurezza)

Per ogni tabella "figlia" che non deve accettare nuove righe su una voce in pensione, si aggancia
**un trigger** alla funzione-guard generica già pronta
[`dbops.trgfn_child_requires_non_obsolete_parent`](/dbzero/dbops/funzioni/trgfn_child_requires_non_obsolete_parent):

```sql
CREATE TRIGGER trg_<figlio>_a10_<catalogo>_require_non_obsoleto_ins_upd
  AFTER INSERT OR UPDATE OF <colonna_fk>
  ON <schema>.<figlio>
  FOR EACH ROW
  EXECUTE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent(
    '<schema_catalogo>', '<catalogo>', 'obsoleto_dal', '<colonna_fk>', 'id'
  );
```

**Una riga `CREATE TRIGGER` per relazione**, nient'altro: la logica vive tutta nella funzione
condivisa. L'errore parlante (`E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`) è già registrato.

### Cosa NON devi toccare

* La funzione di lookup e la funzione-guard sono **generiche e già esistenti**: non si copiano,
  non si duplicano.
* Niente nuova logica per ogni catalogo: solo la colonna (passo 1) e l'aggancio del trigger
  (passo 3).

---

## Cosa NON fa (limiti e buon senso)

* **Non blocca le istanze esistenti.** Una pratica già creata su una voce poi andata in pensione
  continua ad avanzare di stato normalmente: il guard scatta **solo** quando si crea una riga
  nuova o si ri-collega esplicitamente la riga a un'altra voce.
* **È separato da `attivo`.** Una voce in pensione resta `attivo = true`: è voluto. I due assi
  sono indipendenti.
* **Vale per le istanze, non automaticamente per la configurazione collegata.** Se anche un altro
  pezzo di *configurazione* (es. una regola che genera automaticamente pratiche) non deve più
  puntare a una voce in pensione, è una scelta a parte: o si ritira quella configurazione, o le
  si aggancia anch'essa il trigger. Non succede da solo.

---

## Quando smettere di cablare a mano

Oggi si aggancia **un trigger per relazione**: semplice e leggibile finché i casi sono pochi.
Se un domani i punti da proteggere diventassero **molti** (es. un'aliquota IVA referenziata da
decine di tabelle, per molti cataloghi), conviene passare a un **generatore automatico** dei
trigger, sullo stile del framework che già genera i controlli su `attivo`. Per ora è
**volutamente rinviato**: la funzione-cervello è già la base pronta per quel passo.

---

## Esempio reale già realizzato

Il primo uso del pattern è sulle **pratiche**:

* Cataloghi con `obsoleto_dal`: `pratiche.tipi_prestazione` e `pratiche.template_flussi`.
* Guard agganciato su `pratiche.pratiche` (per il tipo) e `pratiche.flussi` (per il template).
* Caso concreto: i vecchi tipi `PREVENTIVI_IMMEDIATA` / `PREVENTIVI_DIFFERITA`, confluiti nel
  tipo unico `PREVENTIVI`, sono stati **messi in pensione** valorizzando `obsoleto_dal` — senza
  cancellare nulla e senza toccare `attivo`. Le pratiche storiche di quei tipi restano valide.

---

## In sintesi

| Vuoi… | Fai… |
|---|---|
| Ritirare una voce dal nuovo, tenendo lo storico | valorizza `obsoleto_dal` |
| Programmare un ritiro futuro | `obsoleto_dal` = data futura |
| Rimetterla in uso | svuota `obsoleto_dal` |
| Eliminarla davvero (nessuno la usa) | è un altro discorso: `attivo` / cancellazione |
| Applicare il pattern a un nuovo catalogo | colonna `obsoleto_dal` + un trigger per relazione |

---

{% include-markdown "signature-core.md" %}
