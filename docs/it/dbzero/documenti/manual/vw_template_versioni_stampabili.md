## 📘 Documentazione Concettuale – Vista `documenti.vw_template_versioni_stampabili`

> 👀 **Vedi anche**
>
> [documenti.fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile)
> [documenti.fn_template_esito_risoluzione](/dbzero/documenti/funzioni/fn_template_esito_risoluzione)
> [documenti.vw_template_personalizzati_scarto](/dbzero/documenti/views/vw_template_personalizzati_scarto)
> [Guida — Documenti e Stampe](/guide/documenti-e-stampe) (§3.1)

### 🎯 Scopo

(21-10-2026 — brief `brief-db-modelli-documento-standard`, §10.3 K-1)

Dice **quali modelli possono stampare oggi**, e con quale versione. È la sede unica di «può
stampare»: chi deve sapere se un modello stampa la legge, invece di ripetere le condizioni.

### Una riga per modello che può stampare

Un modello può stampare se:

* è attivo;
* ha una versione **pubblicata**, attiva e valida alla data operativa dell'azienda.

Per ogni modello c'è al più una riga: le versioni pubblicate attive di uno stesso modello non si
sovrappongono nel tempo (vincolo di esclusione sulla tabella delle versioni).

### Chi la legge

| Lettore | Per che cosa |
|---|---|
| `fn_template_esito_risoluzione` | la regola dei due livelli |
| `fn_risolvi_template_applicabile` | la deduzione del tipo e il modello indicato |
| `fn_personalizza_template_standard` | attraverso la porta: la versione da cui parte una copia |
| `vw_template_personalizzati_scarto` | le due versioni confrontate |

### Note

* La data operativa si calcola una volta per la query.
* `security_invoker`: legge come chi la interroga. Le tabelle dei modelli non hanno RLS.

### Note di migrazione

Prima il predicato era scritto due volte dentro `fn_risolvi_template_applicabile` e una nel
backend (`get_versione_pubblicata_attiva`), che non guardava se il modello è attivo.
