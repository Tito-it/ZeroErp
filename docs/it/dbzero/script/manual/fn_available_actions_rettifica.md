## 📘 Documentazione Concettuale – Funzione `script.fn_available_actions_rettifica()`

> 👀 **Vedi anche**
>
> • [script.fn_available_actions_documento_interno](/dbzero/script/funzioni/fn_available_actions_documento_interno) — **dove sta la regola**: le chiavi del blob, da dove vengono le azioni e la terna di «Registra»
> • [magazzino.rettifiche](/dbzero/magazzino/tabelle/rettifiche) — il documento
> • la gemella: [script.fn_available_actions_inventario](/dbzero/script/funzioni/fn_available_actions_inventario)
>
> **Piano:** [brief-db-magazzino-lotto-2-bis-be-fe](/dev/work-in-progress/brief-db-magazzino-lotto-2-bis-be-fe) R-1

---

### 🎯 Scopo Principale
(scritta il 22-09-2026)

La capability di una rettifica di magazzino per il dettaglio API — quali azioni proporre, quali
spegnere e perché, che cosa si può ancora modificare.

**È un involucro**, e non ha una regola propria: chiama
`script.fn_available_actions_documento_interno('RETTIFICA', id)`, dove la regola
sta una volta sola per le due famiglie di documenti interni (D-L2-h). Esiste
perché il backend chiama per **entità**, come negli altri otto domini, e perché
il giorno in cui la rettifica avesse una chiave in più si sdoppia l'involucro,
non la regola.

`NULL` se il documento non si legge: il 404 lo dà il backend sulla testata.

{% include-markdown "signature-core.md" %}
