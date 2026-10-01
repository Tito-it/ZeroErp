# Guida — Mandare in pensione una voce di catalogo (`obsoleto_dal`)

> **Ultimo aggiornamento**: 19 settembre 2026
>
> **Destinatari**: analisti funzionali, sviluppatori database e backend
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [dbops.fn_get_lookup_codici](/dbzero/dbops/funzioni/fn_get_lookup_codici) — il lookup generico, con l'asse `obsoleto_dal` (`p_includi_obsoleti`)
> * [dbops.trgfn_child_requires_non_obsolete_parent](/dbzero/dbops/funzioni/trgfn_child_requires_non_obsolete_parent) — il guard che rifiuta le nuove istanze su una voce in pensione
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — il gemello sull'altro asse (`attivo`)
>
> **Vedi anche** — tabelle:
>
> * [pratiche.tipi_prestazione](/dbzero/pratiche/tabelle/tipi_prestazione) · [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — i cataloghi con la colonna **e** il guard agganciato
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) · [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — le tabelle figlie protette
>
> **Vedi anche** — guide correlate:
>
> * [Configurazione delle pratiche](/guide/gestione-pratiche-configurazione) — il catalogo su cui il pattern è nato
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — gli altri ritiri che usano questo stesso asse
> * [Linee guida SQL](/linee-guida-sql) — le regole generali su catalogo e istanze

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

| Interruttore       | Domanda a cui risponde                     | Quando lo usi                                                                                                                               |
| ------------------ | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **`attivo`**       | *"È una voce **valida**?"*                 | Spegnerlo significa *"questa voce non esiste più, per nessuno"*. Da non usare se qualcuno la sta già referenziando: rompe i dati esistenti. |
| **`obsoleto_dal`** | *"È ancora **scegliibile per il nuovo**?"* | È quello giusto per "mandare in pensione": la voce resta valida per lo storico, ma sparisce dalle scelte per il nuovo.                      |

> ⚠️ **L'errore classico** è usare `attivo = false` per "ritirare" una voce. Sembra funzionare,
> ma i documenti che la usano filtrano per `attivo` → si rompono. E giustamente il database lo
> impedisce. Per "ritirare" si usa **sempre** `obsoleto_dal`, mai `attivo`.

### I tre stati di `obsoleto_dal`

È semplicemente una **data**:

| Valore                    | Significato                                                                   |
| ------------------------- | ----------------------------------------------------------------------------- |
| **vuoto** (NULL)          | Voce pienamente selezionabile.                                                |
| **data futura**           | **Ritiro programmato**: ancora selezionabile fino a quella data, poi non più. |
| **data passata (o oggi)** | Voce **in pensione**: non più offerta per il nuovo.                           |

---

## Cosa fa il sistema

Una volta che una voce è "in pensione", valgono **tre regole**: una sul nuovo, una sul database,
una sullo storico.

1. **Le tendine possono nasconderla — e ognuna deve chiederlo.** L'asse `obsoleto_dal` vive nel
   lookup generico, ma **una lista mostra la voce in pensione finché non chiede di escluderla**:
   il valore di default è *mostra tutto*, perché le liste esistenti non devono cambiare
   comportamento da sole. Chi vuole la "selezione per il nuovo" passa `includi_obsoleti = false`
   (sul componente di selezione: `:includi-obsoleti="false"`).

   > ⚠️ **Conseguenza operativa**: valorizzare `obsoleto_dal` **non fa sparire la voce
   > dall'applicazione**. Finché quella tendina non è dichiarata "per il nuovo", l'operatore
   > continua a vederla e a poterla scegliere. Se serve che sparisca, la tendina va adeguata.

2. **Il database rifiuta di crearci sopra cose nuove — dove il guard è agganciato.** Anche se
   qualcuno provasse a forzare la creazione (importazione, script, errore di programma), il
   database **blocca** con un messaggio chiaro
   (`E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`). È la rete di sicurezza: *la tendina nasconde, il
   database rifiuta*. Ma il guard è **per relazione** (vedi *Dove è applicato*, in fondo):
   su un catalogo senza guard, la colonna da sola non impedisce nulla.

3. **Lo storico resta intatto.** Le pratiche e i documenti già creati su quella voce continuano
   a funzionare e ad avanzare normalmente. Niente viene cancellato o invalidato.
   (Chi consulta lo *storico* o *filtra* continua a vedere la voce: serve a ritrovare le pratiche
   vecchie di quel tipo.)

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

Una sola colonna sulla tabella di catalogo: una `date` NULL
([istruzione](#area-tecnica-esempi)).

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
[`dbops.trgfn_child_requires_non_obsolete_parent`](/dbzero/dbops/funzioni/trgfn_child_requires_non_obsolete_parent)
([istruzione](#area-tecnica-esempi)). La funzione non ha firma: riceve i suoi argomenti dal
`CREATE TRIGGER`, in quest'ordine — schema e nome del catalogo, la colonna-data del padre, la
colonna FK del figlio e, se la FK non punta alla PK, la colonna referenziata.

Timing `AFTER INSERT OR UPDATE OF <colonna_fk>`: l'`UPDATE OF` fa scattare il controllo **solo
quando cambia il riferimento al catalogo**, così gli avanzamenti di stato di un'istanza storica
non vengono mai bloccati.

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

## Dove è applicato

**La colonna** è su undici cataloghi, in quattro schemi:

| Schema      | Cataloghi con `obsoleto_dal`                                                           |
| ----------- | -------------------------------------------------------------------------------------- |
| `pratiche`  | `tipi_prestazione`, `template_flussi`                                                  |
| `config`    | `classi_errore`, `codici_errore`, `eventi_dominio`, `registri_giornale`, `tipi_entita` |
| `dbops`     | `processi`, `presidi`                                                                  |
| `pagamenti` | `vendite_contabili_stati`, `vendite_contabili_righe_stati`                             |

**Il guard** è agganciato su due relazioni, entrambe nel dominio pratiche:

| Figlio (istanza)    | FK                    | Padre (catalogo)            |
| ------------------- | --------------------- | --------------------------- |
| `pratiche.pratiche` | `tipo_prestazione_id` | `pratiche.tipi_prestazione` |
| `pratiche.flussi`   | `template_flusso_id`  | `pratiche.template_flussi`  |

> 💡 **Le due colonne non vanno lette insieme**: un catalogo può portare `obsoleto_dal` per
> governare le proprie *viste e selezioni* (è il caso di `config.*` e `dbops.processi`, dove le
> viste di presidio filtrano `obsoleto_dal IS NULL`) senza che nessuno debba essere bloccato
> nella creazione di istanze. Il guard si aggiunge quando esiste una **tabella figlia** che non
> deve più puntare lì.

Il primo uso è sulle pratiche, ed è quello con entrambi i pezzi: i tipi
`PREVENTIVI_IMMEDIATA` e `PREVENTIVI_DIFFERITA` sono **in pensione** — confluiti nel tipo unico
`PREVENTIVI` — senza che sia stato cancellato nulla e senza aver toccato `attivo`; le pratiche
storiche di quei tipi restano valide e avanzano.

---

## In sintesi

| Vuoi…                                           | Fai…                                                                                                                  |
| ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Ritirare una voce dal nuovo, tenendo lo storico | valorizza `obsoleto_dal`                                                                                              |
| Programmare un ritiro futuro                    | `obsoleto_dal` = data futura                                                                                          |
| Rimetterla in uso                               | svuota `obsoleto_dal`                                                                                                 |
| Eliminarla davvero (nessuno la usa)             | è un altro discorso: `attivo` / cancellazione                                                                         |
| Applicare il pattern a un nuovo catalogo        | colonna `obsoleto_dal` + la tendina che chiede `includi_obsoleti = false` + (se c'è un figlio da proteggere) il guard |

---

## Area tecnica — esempi

**Aggiungere la colonna al catalogo** — è l'unico intervento sulla tabella:

```sql
ALTER TABLE <schema>.<catalogo>
  ADD COLUMN IF NOT EXISTS obsoleto_dal date NULL;
```

**Cablaggio reale del guard** — l'uno riga per relazione, con i cinque argomenti del caso
pratiche:

```sql
CREATE TRIGGER trg_pratiche_a10_tipi_prestazione_require_non_obsoleto_ins_upd
  AFTER INSERT OR UPDATE OF tipo_prestazione_id
  ON pratiche.pratiche
  FOR EACH ROW
  EXECUTE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent(
    'pratiche', 'tipi_prestazione', 'obsoleto_dal', 'tipo_prestazione_id', 'id'
  );
```

**Ritirare una voce / rimetterla in uso** — le due operazioni sui dati, una sola colonna:

```sql
-- ritiro immediato
UPDATE pratiche.tipi_prestazione SET obsoleto_dal = CURRENT_DATE WHERE codice = '<codice>';

-- ritiro programmato
UPDATE pratiche.tipi_prestazione SET obsoleto_dal = DATE '2027-01-01' WHERE codice = '<codice>';

-- ritorno in uso
UPDATE pratiche.tipi_prestazione SET obsoleto_dal = NULL WHERE codice = '<codice>';
```

**Chi ha ancora istanze su una voce in pensione** — la lista delle istanze storiche, che il
ritiro **non** tocca; serve a sapere quante ce ne sono prima di decidere:

```sql
SELECT p.tipo_prestazione_id, t.codice, t.obsoleto_dal, count(*) AS pratiche
FROM pratiche.pratiche p
JOIN pratiche.tipi_prestazione t ON t.id = p.tipo_prestazione_id
WHERE t.obsoleto_dal IS NOT NULL AND t.obsoleto_dal <= CURRENT_DATE
GROUP BY 1, 2, 3
ORDER BY pratiche DESC;
```

---

{% include-markdown "signature-core.md" %}
