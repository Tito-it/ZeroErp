## 📘 Documentazione Concettuale – Vista `documenti.vw_template_personalizzati_scarto`

> 👀 **Vedi anche**
>
> [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) (§ «Il modello standard»)
> [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni)
> [documenti.fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile)

### 🎯 Scopo

(20-10-2026 — brief `brief-db-modelli-documento-standard`, §4.1 Q-5)

Un modello **personalizzato** da un'azienda non riceve più gli aggiornamenti del modello standard
da cui è partito. La vista dice, per ogni modello personalizzato, **quanto è rimasto indietro**, così
la lista Modelli documento lo può segnalare prima che una stampa si fermi.

### Una riga per modello personalizzato

Ogni modello di un emittente, attivo e con una versione pubblicata, per cui esiste uno standard
predefinito attivo dello stesso tipo di documento e della stessa sorgente. Si confrontano la
versione **in uso** del modello (la pubblicata col numero più alto) e l'ultima versione pubblicata
dello standard.

L'origine di una copia la dichiara la versione che l'ha ripresa dallo standard
(`template_documenti_versioni.derivata_da_versione_id`); le versioni successive della stessa copia
la **ereditano** senza ripeterla.

### Lo stato, in quest'ordine

| Stato | Significato |
|---|---|
| `CONTESTO_SUPERATO` | la versione in uso legge i dati in una forma (`versione_contesto`) più vecchia di quella dello standard. È il caso che **si ferma alla stampa**: viene per primo |
| `ORIGINE_NON_DICHIARATA` | nessuna versione dice da dove viene (modelli nati prima dello standard, o scritti da zero) |
| `ALLINEATA` | parte dall'ultima versione standard |
| `STANDARD_AVANTI` | parte da una versione standard precedente: funziona, ma non ha l'aggiornamento |

⚠️ La forma dei dati che il sistema prepara è una costante del backend, che il database non conosce.
Il riferimento è lo **standard**: le sue versioni le pubblicano i changeSet che accompagnano ogni
cambio di forma.

`security_invoker`: la vista legge con i permessi di chi la interroga.

### Test

`db/pgtap/documenti/test-documenti-template-standard-v1.sql` (test 26-30).
