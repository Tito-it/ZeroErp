# Brief — il presidio che guardava i nomi, e la vista scoperta da due mesi

> **Destinatari:** team DB (`dev/db-tid`) e backend.
>
> **Che cos'è.** Nato di traverso il 2026-09-07, da due pgTAP diventati rossi
> che non avevano niente di rotto. Tirando il filo è venuto fuori che la
> proprietà più delicata delle nostre viste — *«questa vista gira col perimetro
> di chi legge»* — era presidiata in **quattro posti diversi, tutti a elenco**, e
> che un elenco copre solo ciò che qualcuno si è ricordato di scriverci.
>
> **Stato:** ✅ **applicato il 2026-09-07** (changeSet alle 10:13, presidio verde,
> nessuna regressione sulla suite). ⛔ **Il brief NON è chiuso**: restano due
> voci, e la prima è del backend — §7.
>
> 🔴 **Trovata una vista scoperta da due mesi** (§3): non è un allarme rosso, ma
> è un varco vero, ed è lo stesso difetto già corretto a luglio su un'altra
> famiglia di viste.

---

## 1. Come si è arrivati qui

Due test rossi il 2026-09-07, su cantieri diversi, con lo stesso messaggio:

```
# Failed test: "le due viste hanno ancora security_invoker=on"
#         have: 1   want: 2
```

⛔ **Non era rotto niente.** La vista `vendite.vw_dash_competenza_gruppi` aveva
la sua reloption; era scritta `true` invece di `on`. Sono lo stesso identico
valore — è un booleano, e PostgreSQL conserva la parola che riceve. I due test
confrontavano la **grafia**.

⚠️ È il modo peggiore in cui un presidio può sbagliare: **segnala il sano**. Chi
lo incontra deve bisezionare fra due cantieri per scoprire che non c'era niente
da correggere, e la volta dopo lo guarda con meno attenzione.

⭐ E la cosa che rende il caso istruttivo: **l'asserzione giusta esisteva già**,
nello stesso repository, in un file dedicato che legge la proprietà invece della
parola — e il cui commento spiega proprio questo caso. I due test rossi erano
**doppioni** di quella asserzione, in una versione peggiore. *Una seconda sede
diverge sempre; queste erano divergiate verso il falso allarme.*

---

## 2. Il problema, in parole semplici

Alcune viste mostrano documenti che appartengono ad **aziende diverse**. Perché
ognuno veda solo i propri, la vista deve avere un interruttore acceso: *«gira
sotto il nome di chi guarda»*.

Se manca, la vista gira sotto il nome del padrone del database — che vede tutto.

⛔ **E non succede niente di visibile.** Nessun errore, nessuna pagina rotta: la
vista continua a rispondere, risponde soltanto **di più**.
⚠️ Peggio: l'interruttore **non compare** quando si stampa la definizione della
vista. Chi la ricrea partendo da lì lo perde, e non se ne accorge.

### ⛔ E la catena si spegne al primo anello, non all'ultimo

L'interruttore **non si propaga**. Una vista che ne legge un'altra, che ne legge
un'altra ancora, fino alla tabella protetta: se **il primo** anello è spento,
tutti quelli sotto non servono a niente — perché «chi guarda», per loro, diventa
il padrone della vista esterna.

*Sei anelli accesi e uno spento fanno una catena spenta.*

---

## 3. 🔴 La vista scoperta

`script.vw_pratica_doc_sorgente` — arriva a **sei tabelle di documenti**
(preventivi, ordini, contratti, DDT, resi, offerte) e l'interruttore non ce l'ha.
Gli anelli sotto ce l'hanno tutti, e non basta (§2).

⚠️ **Non era una scelta di nessuno.** La vista è del **2 luglio 2026**; il
correttivo che ha insegnato la regola al progetto è del **6 luglio**. È una vista
scritta quattro giorni prima della lezione, su cui nessuno è tornato.

⛔ **Ed era invisibile a tutti e tre i modi in cui la cercavamo**:

| dove guardavamo | perché sfuggiva |
| --- | --- |
| nello schema `vendite` | sta in `script` |
| fra le viste che si chiamano `vw_dash_*` | non si chiama così |
| fra quelle che leggono direttamente una tabella protetta | ci arriva **attraverso altre viste** |

**Quanto è grave.** Il backend la legge in join sulle pratiche, che hanno già il
proprio filtro: si vedono i dati del documento d'origine delle pratiche che si
può già vedere, anche quando quel documento è di un'altra azienda. ⇒ Un varco
reale ma **stretto**, non un'esposizione aperta.

✅ **Chiuso il 2026-09-07** dal changeSet `20260907-04`, con un `ALTER VIEW ... SET`
che non tocca la definizione — quindi non può regredire la regola d'ancora che
quella vista implementa.

⚠️ **Cambia anche un comportamento, non solo cosa si nasconde**: quella vista
sceglie *il documento più vivo* fra quelli collegati a una pratica, ordinando su
`risolto` e `terminale` — cioè su dati che ora sono filtrati. Su una pratica con
più sorgenti può vincerne un'altra. È corretto — non si sceglie un'àncora
guardando dati che non si possono vedere — ma va saputo.

⛔ **E il caso non è teorico, verificato sul MODELLO il 2026-09-07**: nulla lega
la sorgente al perimetro della pratica. `pratiche.pratiche_sorgenti` non ha
nessun vincolo né guard che confronti l'emittente del documento con quello della
pratica, e `sorgente_uid` è una chiave polimorfa senza FK. Una pratica di un
emittente **può** puntare a un documento di un altro.
⚠️ Su dati coerenti non si vede nulla — le pratiche e i sei documenti passano
dallo **stesso** `fn_scope_ef_whitelist` — ma «coerenti» è una proprietà che
nessuno impone. ⇒ È il motivo per cui il §7 resta aperto sul lato backend.

---

## 4. ✅ La decisione: si presidia il CRITERIO, non i nomi

**Prima.** Quattro elenchi scritti a mano, in quattro file, per una trentina di
nomi di viste: nove qui, una famiglia per prefisso là, più code esplicite e
controlli sparsi.

**Adesso.** Una domanda sola, che non nomina nessuno:

> *«Esiste una vista che tocca dati protetti — anche attraverso altre viste — e
> non ha l'interruttore?»*

| | prima | adesso |
| --- | ---: | ---: |
| viste sotto presidio | 17 | **65** |
| elenchi da tenere allineati a mano | 4 | **0** |
| viste future | fuori finché qualcuno non le aggiunge | **dentro da sole** |

⭐ **Non è un'idea nuova.** Era già scritta, in prosa, nell'intestazione del file
che oggi si ritira: *«il modo per trovarne altre non è leggere questo elenco, è
rifare la misura»*. Era una raccomandazione; adesso è il test.

⚠️ **Perché gli elenchi non bastavano, e non è un'ipotesi.** Sette viste
`*stato_sorgente*` sono rimaste scoperte per **sette settimane** e sono state
trovate per caso ad agosto. `vw_pratica_doc_sorgente` per **due mesi**, e l'ha
trovata questo criterio il primo giorno che è esistito.

### Cosa costa

Il test è più largo, quindi il giorno in cui qualcuno crea di proposito una
vista senza interruttore diventa rosso e bisogna decidere. ⭐ Ma è esattamente il
momento in cui si vuole decidere: oggi quella decisione non la prende nessuno,
perché nessuno la vede.

---

## 5. Che cosa è entrato

| Cosa | Dove |
| --- | --- |
| `ALTER VIEW script.vw_pratica_doc_sorgente SET (security_invoker = on)` | `20260907-04` |
| Il presidio riscritto sul criterio, ricorsivo, plan 5 | `db/pgtap/rls/test-rls-viste-security-invoker.sql` |
| Il presidio a prefisso, **ritirato** (confluito nel precedente) | ~~`db/pgtap/vendite/test-vw-dash-security-invoker.sql`~~ |
| Quattro doppioni tolti da test funzionali | `test-registro-documento-previsto-v1`, `test-vw-dash-competenza-gruppi-v1`, `test-viste-dash-emittente-v1`, `test-fn-list-commessa-attivita-provenienza-v1` |
| Un controllo indurito (leggeva la parola) | `test-vw-partite-merce-v1` |

### ⭐ Che cosa NON è stato tolto, e il criterio

Cinque controlli locali **restano**: `ui/test-lista-*-seed` (quattro) e
`script/test-vw-giornale-entita`.

> **Si toglie un'asserzione quando è solo una copia del presidio globale, appesa
> a un test che parla d'altro. Si tiene quando è la PRECONDIZIONE di ciò che quel
> file verifica subito dopo** — lì non è un doppione, è il cancello che dà senso
> alle asserzioni seguenti.

⚠️ E leggono già la proprietà nella forma robusta (`IN ('on','true')`): non erano
delle mine.

---

## 6. Come si vede che il presidio funziona davvero

Non basta che sia verde. Provato il 2026-09-07 in tutti i versi:

| si rompe… | esito atteso | verificato |
| --- | --- | --- |
| una vista perde l'interruttore | test 2 rosso, **e la nomina** | ✅ (`script.vw_pratica_doc_sorgente`) |
| il criterio smette di seguire la catena | test 3 rosso | ✅ |
| …e il criterio si restringe in silenzio | test 1 rosso | ✅ |
| una vista sana scritta `= true` | resta verde | ✅ |
| una vista che non tocca dati protetti | **non** entra nel perimetro | ✅ (test 5) |

⛔ **Il test 1 è quello che protegge la migrazione**, ed è il meno ovvio: con la
ricorsione spenta, il test 2 resta **verde** mentre il presidio copre molto meno.
Un criterio che si restringe non produce rossi: produce silenzio. Per questo
l'unico elenco che sopravvive è dentro il test 1, e non è il perimetro — è la
prova che il perimetro non si è ristretto.

---

## 7. Che cosa resta

✅ **Fatto il 2026-09-07**: changeSet applicato (10:13), presidio verde,
`scripts/pgtap-baseline.sh rls ui script vendite` senza regressioni — l'unico
rosso nuovo era il presidio stesso prima del migrate, e nominava il varco.
Documentazione aggiornata: i manual di `script.vw_pratica_doc_sorgente`,
`dbops.vw_codici_errore_forme_condizione` e `dbops.vw_processi_programmazione`.

🔵 **Restano due voci, e nessuna è nostra da chiudere.**

**1. 🔴 Il backend deve guardare le pratiche — ed è l'unica voce con una
scadenza.** `apps/pratiche/db/pratiche_repository.py` è l'unico consumatore. Il
comportamento cambia dove i due perimetri divergono, e il §3 dice che il modello
quella divergenza **la ammette**: nessun vincolo lega la sorgente all'emittente
della pratica.
⛔ La domanda non è «si vede ancora qualcosa» ma **«su una pratica che punta a un
documento di un altro emittente, l'àncora scelta è ancora quella giusta?»** — ed
è una cosa che si guarda a video, non in un test: nessuna suite fabbrica oggi
quel caso.
⭐ Se lo si vuole presidiare invece che collaudare, la strada è un pgTAP che
**costruisce** una pratica con due sorgenti su emittenti diversi e verifica quale
vince da ciascun perimetro. Non esiste, e questa riga è il posto in cui è scritto
che non esiste.

**2. ⚠️ La classe di difetto non è stata cercata altrove.** *Un presidio che
confronta una parola invece della proprietà* qui è saltato fuori per caso, e in
questo giro se ne sono trovati sette esemplari su una proprietà sola. Non
sappiamo se ce ne siano su altre — reloption, `proconfig`, `relpersistence`,
`convalidated`. ⛔ Non è una supposizione da inseguire adesso: è una **misura
sua**, e va fatta da qualcuno che decide di farla, non aggiunta in coda a questo
cantiere.

⚠️ **Quando si chiude questo brief.** Quando la voce 1 ha una risposta — o il
collaudo dice che va bene, o nasce il pgTAP che costruisce il caso. La voce 2 non
lo trattiene: è un cantiere diverso, e si sposta in un documento suo il giorno
che qualcuno lo apre.
