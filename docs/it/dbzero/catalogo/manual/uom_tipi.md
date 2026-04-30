## 📘 Documentazione Concettuale – Tabella `catalogo.uom_tipi`

> 👀 **Vedi anche**
>
> **Approfondimento Tabelle**
> • [`catalogo.unita_misura`](/dbzero/catalogo/tabelle/unita_misura)
> • [`catalogo.unita_misura_conversioni`](/dbzero/catalogo/tabelle/unita_misura_conversioni)
> • [`catalogo.articoli_uom_operativa`](/dbzero/catalogo/tabelle/articoli_uom_operativa)

## Scopo

Definire il catalogo delle **tipologie/dimensioni fisiche** delle unita' di
misura, separato dal catalogo delle UoM, per governare in modo esplicito le
famiglie di conversione ammesse.

## Contesto

`catalogo.uom_tipi` e' la tabella di classificazione che completa
`catalogo.unita_misura`.

Prima della sua introduzione, il sistema aveva un unico catalogo UoM e una
tabella di conversioni globali, ma senza una dimensione semantica che
impedisse accoppiamenti incoerenti come:

* `metri -> grammi`
* `kg -> kWh`
* `litri -> pezzi`

Con `catalogo.uom_tipi`, ogni UoM viene assegnata a una famiglia omogenea
(`MASSA`, `LUNGHEZZA`, `ENERGIA`, `IMBALLAGGIO`, ecc.) e le conversioni globali
possono essere controllate a livello DB.

## Input

La tabella riceve e governa questi attributi principali:

* `codice` identificativo stabile della tipologia
* `descrizione` leggibile per amministrazione e documentazione
* `attivo` per attivazione/disattivazione logica

Tipologie iniziali previste:

* `LUNGHEZZA`
* `MASSA`
* `VOLUME`
* `AREA`
* `ENERGIA`
* `POTENZA`
* `TEMPO`
* `QUANTITA`
* `IMBALLAGGIO`
* `VALUTA`
* `GENERICO`

## Output

La tabella fornisce al dominio questi effetti strutturali:

* classificazione univoca di ogni riga di `catalogo.unita_misura`
* base di validazione per `catalogo.unita_misura_conversioni`
* separazione esplicita tra conversioni globali standard e conversioni
  articolo-specifiche

## Regole

* Ogni riga di `catalogo.unita_misura` appartiene a **una sola** tipologia.
* Le conversioni globali in `catalogo.unita_misura_conversioni` sono ammesse
  solo tra UoM della **stessa** tipologia.
* Le conversioni dipendenti dall'articolo restano in
  `catalogo.articoli_uom_operativa`, soprattutto per packaging/logistica.
* `IMBALLAGGIO` serve a classificare UoM come `pallet`, `collo`, `scatola`,
  ma non implica che esista una conversione globale universale fra esse.
* `GENERICO` e' un fallback controllato e non deve diventare il contenitore
  ordinario di UoM eterogenee.

## Dipendenze DB

* `catalogo.unita_misura.tipo_uom_id`
* `catalogo.unita_misura_conversioni`
* trigger/funzioni guard che validano la compatibilita' tipologica delle
  conversioni globali

## Note di migrazione

* La tabella e' introdotta con seed base e backfill su `catalogo.unita_misura`.
* Nel seed corrente `SMC` e' classificata come `ENERGIA` tecnica/commerciale
  per mantenere coerenti le conversioni globali gia' presenti (`SMC` ↔ `KWH`
  / `MJ`).
* La classificazione di alcuni casi legacy puo' essere raffinata in un secondo
  passaggio, ma il modello introdotto resta invariato: **no conversioni globali
  cross-type**.

---

{% include-markdown "signature-core.md" %}
