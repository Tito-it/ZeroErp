# Guida — Il catasto delle istanze

> **Ultimo aggiornamento**: 25 novembre 2026
>
> **Destinatari**: sviluppatori database, backend e analisti funzionali
>
> **Vedi anche** — schemi DB:
>
> * [anagrafiche.catasto_unita_immobiliari](/dbzero/anagrafiche/tabelle/catasto_unita_immobiliari) — l'unità catastale
> * [anagrafiche.catasto_unita_immobiliari_indirizzi](/dbzero/anagrafiche/tabelle/catasto_unita_immobiliari_indirizzi) — la ponte fra unità e civici
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza, che nomina la sua unità e la sua precedente
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — il civico
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — la scrittura del cliente, da cui parte la catena
> * [storico.catasto_unita_immobiliari](/dbzero/storico/tabelle/catasto_unita_immobiliari) — le versioni storiche dell'unità
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [anagrafiche.trgfn_clienti_set_parent_istanza](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_parent_istanza) — scrive la catena `parent_istanza_id`
> * [anagrafiche.trgfn_iu_clone_catasto_from_parent](/dbzero/anagrafiche/funzioni/trgfn_iu_clone_catasto_from_parent) — fa scattare il clone
> * [script.fn_clone_catasto_from_parent_by_istanza](/dbzero/script/funzioni/fn_clone_catasto_from_parent_by_istanza) — il clone
> * [script.fn_get_catasto_source_by_istanza](/dbzero/script/funzioni/fn_get_catasto_source_by_istanza) — l'unità da copiare
> * [anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo](/dbzero/anagrafiche/funzioni/trgfn_iu_sync_catasto_unita_indirizzo) — il legame unità-civico
> * [script.fn_subentro_cliente](/dbzero/script/funzioni/fn_subentro_cliente) — chiude il cliente uscente
>
> **Vedi anche** — guide correlate:
>
> * [Generazione di un cliente](/guide/generazione-cliente) — dove il catasto entra nella nascita del cliente
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility) — l'istanza e la sua catena
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — il civico
> * [Glossario termini utility](/glossario/glossario-utility) — i termini del settore

---

## Introduzione

Questa guida racconta il catasto delle istanze nel suo insieme: tre tabelle, due trigger sulle istanze e due
funzioni di `script`, che insieme danno a ogni istanza la sua unità catastale, la legano al civico e la copiano al
subentro.

I dati catastali (foglio, particella, subalterno, categoria, rendita) descrivono l'unità immobiliare in cui si
eroga il servizio: servono alla fatturazione e agli adempimenti del settore.

---

## L'unità catastale non sa di chi è

La riga di `catasto_unita_immobiliari` non dipende né dal cliente né dal contratto, e non ha colonne verso
l'istanza o verso il civico. I legami stanno fuori:

* **l'istanza punta alla sua unità** con `istanze_utilities.catasto_unita_immobiliare_id`;
* **l'unità e il civico** sono legati dalla tabella ponte `catasto_unita_immobiliari_indirizzi`, molti a molti: la
  stessa unità può stare su più civici, e lo stesso civico avere più unità.

```mermaid
%%{init: {'er': {'layoutDirection': 'TB'}}}%%
erDiagram
    istanze_utilities }o--o| catasto_unita_immobiliari : punta_a
    istanze_utilities }o--o| istanze_utilities : parent_istanza_id
    catasto_unita_immobiliari ||--o{ catasto_unita_immobiliari_indirizzi : associata_a
    indirizzi_dettaglio ||--o{ catasto_unita_immobiliari_indirizzi : associato_a
    indirizzi_dettaglio ||--o{ istanze_utilities : luogo_di

    istanze_utilities {
        bigint id PK
        bigint catasto_unita_immobiliare_id FK
        bigint parent_istanza_id FK
        bigint indirizzo_dettaglio_id FK
    }

    catasto_unita_immobiliari {
        bigint id PK
        varchar sezione_catastale
        varchar foglio_catastale
        varchar particella
        varchar subalterno
        varchar categoria_catastale
        numeric rendita_catastale
        integer superficie
    }

    catasto_unita_immobiliari_indirizzi {
        bigint id PK
        bigint catasto_unita_id FK
        bigint indirizzo_dettaglio_id FK
    }

    indirizzi_dettaglio {
        bigint id PK
    }
```

---

## Un'unità per istanza: la copia al subentro

Il modello vuole che ogni istanza abbia la sua unità, mai condivisa con un'altra. Al subentro l'unità
dell'istanza precedente si **clona**: l'istanza nuova riceve una riga nuova con gli stessi dati, e una rettifica
del catasto di chi subentra non tocca quello di chi è uscito. Le istanze chiuse tengono il catasto che avevano.

La regola la scrive l'indice unico `uq_istanze_utilities_catasto_unita_immobiliare`: un'unità è di un'istanza
sola, e un'istanza senza unità è ammessa. La strada del clone la rispetta da sé, perché crea sempre una riga nuova;
un'istanza agganciata a mano all'unità di un'altra è rifiutata dall'indice.

---

## Il flusso del subentro

Il subentro sullo stesso PDP lo fa l'applicazione in una transazione: `script.fn_subentro_cliente` chiude il
cliente uscente, poi l'applicazione crea l'istanza nuova, col PDP e il civico, e il cliente nuovo. Da lì il
database fa il resto da sé.

```text
scrittura del cliente nuovo (INSERT, o UPDATE di pdp_id o data_attivazione, con la data di attivazione)
  │
  ▼
trgfn_clienti_set_parent_istanza          BEFORE, su clienti
  → trova il cliente precedente sullo stesso PDP
  → UPDATE istanze_utilities: parent_istanza_id = istanza del precedente
  │
  ▼
trgfn_iu_clone_catasto_from_parent        AFTER, su istanze_utilities, quando nasce il legame con la
                                          precedente: all'INSERT con la precedente, all'UPDATE che la cambia
  (solo se l'istanza ha una precedente, ha un civico e non ha ancora un'unità)
  → fn_clone_catasto_from_parent_by_istanza
      → l'unità della precedente (fn_get_catasto_source_by_istanza); se non c'è, fine
      → INSERT della copia in catasto_unita_immobiliari
      → UPDATE istanze_utilities: catasto_unita_immobiliare_id = copia
  │
  ▼
trgfn_iu_sync_catasto_unita_indirizzo     AFTER, su istanze_utilities, all'INSERT e al cambio di unità o civico
  → INSERT idempotente della coppia (copia, civico dell'istanza) nella ponte
```

La catena la scrive anche il ramo delle istanze fittizie, senza PDP: lì la precedente è l'ultimo cliente con la
stessa chiave soggetto, utility e azienda. Il clone scatta allo stesso modo, se la fittizia ha un civico.

### Le regole del clone

* **Sorgente unica**: la precedente diretta, da `parent_istanza_id`. Non si risale la catena.
* **Quando nasce il legame**: il clone scatta quando l'istanza nasce con la precedente già scritta, e quando la
  precedente cambia. Una riscrittura uguale della precedente non clona: il clone copia ciò che la precedente ha
  quando il legame nasce, e un'unità che compare dopo sulla precedente non arriva. La rettifica dell'istanza nuova
  si fa su di lei.
* **Idempotente**: un'istanza che ha già un'unità la tiene, anche se la sua precedente cambia: sullo stesso PDP
  l'immobile è lo stesso.
* **Nessun errore senza sorgente**: se la precedente non ha un'unità, il clone non fa niente e il cliente nasce lo
  stesso.
* **Copia l'unità, non i suoi civici**: la copia si lega al solo civico dell'istanza nuova.
* **Contro la concorrenza**: la riga dell'istanza è bloccata durante il clone, così non nascono due copie.

---

## Il resto del ciclo di vita

* **Nascita fuori dal subentro**: l'applicazione inserisce l'unità e la aggancia all'istanza; l'aggancio fa
  scattare il legame col civico, come al subentro.
* **Modifica**: `catasto_unita_immobiliari` è registrata in `config.storico_set_storicizza`, quindi ogni modifica e
  ogni cancellazione lasciano la versione di prima in `storico.catasto_unita_immobiliari`.
* **Il civico**: un legame nella ponte chiede un civico attivo, e un civico che ha legami non si spegne.
* **Il cambio di civico o di unità**: la ponte segue l'istanza. La coppia (unità, civico) che l'istanza aveva
  portato esce, se nessun'altra istanza ha la stessa coppia, e quella nuova entra. Le coppie scritte a mano con
  altri civici restano: la ponte è molti a molti. Il civico lasciato, senza più legami, si spegne.
* **L'unità lasciata**: un'istanza che passa a un'altra unità cancella la prima, se nessun'altra istanza la
  nomina. La sua versione resta nello storico, e i suoi legami coi civici se ne vanno con lei.
* **Cancellazione**: un'unità nominata da un'istanza non si cancella; un'unità cancellata porta via i suoi legami
  coi civici.

---

## Che cosa oggi non copre

* **La cancellazione dell'istanza** non tocca l'unità: un'istanza cancellata lascia la sua unità senza nessuno
  che la nomini.
* **Una catena che si svuota** per un cliente annullato lascia all'istanza l'unità copiata dalla precedente di
  allora.

---

## I test

* `db/pgtap/anagrafiche/test-simula-subentro.sql` — il subentro completo sullo stesso PDP: catena, clone con id
  diverso e dati uguali, legame della copia col civico, duplicato nella ponte rifiutato.
* `db/pgtap/anagrafiche/test-catasto-unita-della-sua-istanza-v1.sql` — un'unità per istanza, il clone
  all'INSERT e non alla riscrittura uguale, la coppia e l'unità lasciate al cambio di civico e di unità.

---

{% include-markdown "signature-core.md" %}
