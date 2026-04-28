## 📘 Documentazione Concettuale – Tabella `catalogo.unita_misura`

> 👀 **Vedi anche**
>
> **Approfondimenti Tabelle**
>
> • [`catalogo.articoli`](/dbzero/catalogo/tabelle/articoli)
> • [`catalogo.uom_tipi`](/dbzero/catalogo/tabelle/uom_tipi)
> • [`catalogo.unita_misura_conversioni`](/dbzero/catalogo/tabelle/unita_misura_conversioni)
>

## Scopo

Centralizzare il catalogo delle unita' di misura utilizzabili nel sistema e
associarle a una tipologia fisica/semantica controllata.

## Contesto

`catalogo.unita_misura` e' la master table delle UoM impiegate da articoli,
movimenti, documenti commerciali e funzioni di conversione.

Ogni UoM descrive come una quantita' viene espressa nel dominio ERP
(`PZ`, `KG`, `LT`, `KWH`, ecc.) e, con l'introduzione di `tipo_uom_id`,
definisce anche a quale famiglia appartiene (`QUANTITA`, `MASSA`, `ENERGIA`,
ecc.).

Questa classificazione consente al DB di distinguere tra:

* conversioni globali standard tra unita' omogenee
* conversioni articolo-specifiche, soprattutto per packaging e logistica

## Input

La tabella riceve e governa questi attributi principali:

* `codice` identificativo univoco della UoM
* `descrizione` descrizione interna/tecnica
* `descrizione_fattura` descrizione breve per documenti
* `tipo_uom_id` collegamento alla tipologia di appartenenza
* `attivo` per attivazione/disattivazione logica

## Output

La tabella fornisce al sistema:

* un vocabolario unico di UoM referenziabile via FK
* la classificazione necessaria per governare le conversioni globali
* descrizioni utilizzabili sia in ambito tecnico sia nei documenti fiscali e commerciali

## Regole

* `codice` deve essere univoco e identificare chiaramente la UoM.
* `descrizione` e' obbligatoria.
* `tipo_uom_id` e' obbligatorio e collega la UoM a una sola famiglia semantica.
* `descrizione_fattura`, se valorizzata, sostituisce la descrizione tecnica nei documenti stampati.
* `attivo = false` consente dismissione logica senza perdita di storico.

## Dipendenze DB

* `catalogo.uom_tipi`
* `catalogo.articoli`
* `catalogo.articoli_uom_operativa`
* `catalogo.unita_misura_conversioni`
* tabelle di dominio che referenziano `uom_id` o `uom_operativa_id`

## Note di migrazione

* `tipo_uom_id` e' stato introdotto per separare la UoM dalla sua dimensione fisica/semantica.
* Le UoM legacy vengono riallineate tramite backfill iniziale verso `catalogo.uom_tipi`.
* La classificazione tipologica prepara il vincolo DB che impedisce conversioni globali cross-type.

---

{% include-markdown "signature-core.md" %}
