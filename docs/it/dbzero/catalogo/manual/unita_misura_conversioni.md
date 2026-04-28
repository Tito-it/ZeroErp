## 📘 Documentazione Concettuale – Tabella `catalogo.unita_misura_conversioni`

> 👀 **Vedi anche**
>
> **Approfondimento Tabelle**
> • [`catalogo.unita_misura`](/dbzero/catalogo/tabelle/unita_misura)  
> • [`catalogo.uom_tipi`](/dbzero/catalogo/tabelle/uom_tipi)  
> • [`catalogo.articoli_uom_operativa`](/dbzero/catalogo/tabelle/articoli_uom_operativa)  
>
> **Approfondimento Funzioni**
> • [`catalogo.fn_get_uom_factor`](/dbzero/catalogo/funzioni/fn_get_uom_factor)  

## Scopo

Definire le **conversioni globali standard** tra unita' di misura, indipendenti
dall'articolo, da usare come fallback quando non esiste una conversione
articolo-specifica.

## Contesto

`catalogo.unita_misura_conversioni` non descrive confezioni o rapporti
commerciali legati a un singolo articolo. Descrive invece conversioni valide in
modo generale all'interno della stessa famiglia di misura.

Esempi tipici:

* `kg -> g`
* `m -> cm`
* `kWh -> MWh`

Il suo uso principale e' il fallback della funzione `catalogo.fn_get_uom_factor`
quando manca una riga attiva in `catalogo.articoli_uom_operativa`.

## Input

La tabella riceve e governa questi attributi principali:

* `uom_from_id` UoM sorgente
* `uom_to_id` UoM destinazione
* `fattore` moltiplicatore da `from` a `to`
* `valido_dal`, `valido_al` finestra temporale di validita'
* `attivo` stato logico della conversione
* `meta` eventuali metadati amministrativi

## Output

La tabella fornisce al sistema:

* una base di conversione globale standard tra UoM omogenee
* un fallback riusabile da funzioni, trigger e servizi
* una gestione temporalizzata delle conversioni quando i fattori cambiano nel tempo

## Regole

* `fattore` deve essere positivo.
* `uom_from_id` e `uom_to_id` non possono coincidere.
* Non sono ammessi overlap temporali sulla stessa coppia `(uom_from_id, uom_to_id)`.
* Le conversioni globali sono ammesse solo tra UoM della stessa `catalogo.uom_tipi`.
* Le conversioni dipendenti dal prodotto non vanno qui, ma in `catalogo.articoli_uom_operativa`.

## Dipendenze DB

* `catalogo.unita_misura`
* `catalogo.uom_tipi`
* `catalogo.articoli_uom_operativa`
* `catalogo.fn_get_uom_factor`
* trigger guard che validano la compatibilita' tipologica

## Note di migrazione

* La tabella nasce come fallback globale e resta tale anche dopo l'introduzione di `catalogo.uom_tipi`.
* Il nuovo controllo tipologico restringe il perimetro alle sole conversioni same-type.
* Per packaging/logistica (`collo`, `scatola`, `pallet`) la sede corretta resta
  `catalogo.articoli_uom_operativa`, perche' il fattore dipende spesso
  dall'articolo e non dalla UoM in assoluto.

---

{% include-markdown "signature-core.md" %}
