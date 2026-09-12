# Brief — il presidio che guardava i nomi, e la vista scoperta da due mesi

> **Destinatari:** team DB (`dev/db-tid`) e backend.
>
> **Che cos'è.** Nato di traverso il 2026-09-07, da due pgTAP diventati rossi
> che non avevano niente di rotto. Tirando il filo è venuto fuori che la
> proprietà più delicata delle nostre viste — *«questa vista gira col perimetro
> di chi legge»* — era presidiata in **quattro posti diversi, tutti a elenco**, e
> che un elenco copre solo ciò che qualcuno si è ricordato di scriverci.
>
> **Stato:** ✅ **CHIUSO** (2026-09-07) — entrambe le metà.
> Il DB ha applicato il changeSet `20260907-04` e riscritto il presidio sul
> **criterio** invece che sui nomi; il backend ha risposto alla voce 1 del §7
> costruendo il caso che nessuna suite fabbricava.
>
> **Come si verifica che è chiuso**, e sono tre letture indipendenti:
>
> | Cosa | Esito, 2026-09-07 |
> | --- | --- |
> | `script.vw_pratica_doc_sorgente` ha l'interruttore | `reloptions = {security_invoker=on}` |
> | Viste col flag acceso, su tutto il database | **77** |
> | `db/pgtap/rls/test-rls-viste-security-invoker.sql` | verde (`pgtap-baseline.sh rls`) |
> | `smoke-pratica-doc-sorgente-cross-emittente.py` | verde, e **rosso** con la regressione iniettata |
>
> 🔵 **Esce di qui una coda sola, e non è di questo cantiere**: la voce 2 del §7
> — *un presidio che confronta una parola invece della proprietà* non è stato
> cercato su `proconfig`, `relpersistence`, `convalidated`. Il §7 dice da sé che
> **non trattiene la chiusura**: è una misura sua, e vuole un documento suo il
> giorno che qualcuno la apre.
>
> ⚠️ **Un residuo dichiarato, non un debito nascosto**: il presidio della voce 1
> è uno **smoke**, non un pgTAP. Lo lancia `scripts/smoke-baseline.sh`, **non la
> CI**. Promuoverlo a pgTAP è lavoro del team DB, e non è urgente — prima di
> oggi non c'era niente.
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

🔵 **Restava una voce di là dal DB, ed è chiusa. Ne resta una che non è di
nessuno dei due.**

**1. ✅ Il backend ha guardato le pratiche — chiuso il 2026-09-07.**

La domanda era **«su una pratica che punta a un documento di un altro emittente,
l'àncora scelta è ancora quella giusta?»**. ⭐ **Sì**, e il verso è quello che
serve: dal perimetro ristretto vince il documento **di casa**, non l'estraneo —
che perde non perché sia nascosto, ma perché senza il suo descrittore non è più
`risolto`, e il criterio 1 della regola d'àncora è risolto-first.

⛔ **Non si è potuto guardare a video, e la ragione va scritta perché cambia la
richiesta**: i campi `doc_*` **a livello pratica** oggi non li rende nessuna
schermata. L'unico consumatore di `doc_*` nel frontend è `PraticaPercorso.vue`,
che è il ramo **per-flusso** — e quello non è toccato, perché
`_doc_sorgente_lateral` legge `script.vw_stato_sorgente`, che l'interruttore ce
l'ha da sempre. La lista pratiche non ha nessuna colonna `doc_*` in
`ui.lista_colonna`. ⇒ La risposta si legge dalla vista e dal repository che la
usa, non da una pagina.

⭐ **E la modifica del DB chiude un'asimmetria invece di aprirne una**: fino al
07-09 i due rami potevano dire cose **diverse** sulla stessa pratica — la lista
mostrava il documento di un altro emittente, il percorso no.

**Come è stato provato**, e il caso è stato **costruito**, non cercato:
`backend/scripts/tests/smoke-pratica-doc-sorgente-cross-emittente.py`
(transazione + rollback). Fabbrica un preventivo su un secondo emittente e lo
appende a **due pratiche speculari** — su A come `ROOT`, su B come `COLLEGATO` —
poi legge l'àncora da **tre** perimetri, imposti con `app.current_emittente_id`
(che `fn_check_user_emittente_scope` valuta alla regola 2, **prima** del bypass
super admin: «restringe chiunque»).

⭐ **Le due pratiche speculari non sono simmetria decorativa**, ed è la
correzione che è costata di più. Con una sola, *«dal perimetro di casa ha vinto
il documento di casa»* è compatibile con una vista che sceglie **sempre** il
`COLLEGATO`, o che preferisce l'emittente di chi legge per un'altra ragione.
Sulla pratica B il `ROOT` è il documento **di casa**: letta dal perimetro
**estraneo** deve vincere di nuovo il `COLLEGATO`, che stavolta è l'estraneo.
Stessi due documenti, verdetto opposto, e l'unica cosa cambiata è chi guarda.
⇒ Il perimetro largo (test 4) è la riga di partenza: lì vince il `ROOT` su
entrambe.

⛔ **Cercare quel documento avrebbe dato `SENZA_MATERIA`**: al 2026-09-07 su
questa macchina un solo emittente ha preventivi. Ma «oggi non capita» non è un
fatto sul modello — `pratiche_sorgenti` non ha nessun vincolo che leghi la
sorgente all'emittente della pratica — e un presidio che aspetta i dati giusti
passa a vuoto su un database ricostruito da zero.

⚠️ **Il test 2 dello smoke è quello che protegge gli altri**: se la connessione
non applicasse la RLS i tre perimetri direbbero la stessa cosa e il file
passerebbe **smettendo di verificare**. Lì si esce `SENZA_MATERIA`.

⭐ **Provato anche al contrario**: simulando l'interruttore spento (i perimetri
dei test 5 e 6 non si restringono, che è come girerebbe la vista sotto il
proprietario) diventano rossi *«vince il COLLEGATO di casa»* e *«vince il
COLLEGATO estraneo»* con i due controlli di differenza, **nominandoli**.
⚠️ E il test 2 resterebbe **verde**: la RLS sulla tabella base non c'entra con la
reloption della vista — i discriminanti sono il 5 e il 6.

⚠️ **Un fatto che la vista dice e che vale la pena sapere**: `vw_pratica_doc_sorgente`
**non** legge `pratiche.pratiche`, quindi risponde anche su una pratica di un
altro emittente. Il cancello sulla pratica è del **consumatore** — il `LEFT JOIN`
in `_PRATICA_JOINS` su `pratiche.pratiche`, che ha la RLS — ed è il test 7.

🔴 **E la doc API diceva una cosa sbagliata, scoperta scrivendo questa.**
`backend/pratiche/manual/api_pratica_detail.md` dichiarava che i `doc_*` sono
*«del documento **ROOT** della pratica (`pratiche_sorgenti.ruolo_link='ROOT'`)»*.
Non lo sono dal roll-out **D3b**: l'àncora è il documento **più vivo** fra tutti
i link, e il `ROOT` è il **terzo** criterio, cioè un tiebreak. ⇒ Chi leggeva
quella pagina si aspettava lo stato del preventivo capostipite mentre a video
compariva quello dell'ordine collegato — e su una pratica evoluta
preventivo→ordine sono proprio i due che divergono.
✅ Corretta il 2026-09-07, insieme alla dipendenza da chi legge introdotta dal
`20260907-04`. ⭐ Il difetto non c'entrava con questo cantiere: è emerso perché
per scrivere «che cosa cambia» bisognava prima dire «che cos'era», ed è la
seconda volta in questo giro che *una sede diversa aveva divergiato in silenzio*.

🔵 **Resta preferibile un pgTAP**, e questa riga non lo chiude: uno smoke non lo
lancia la CI. Ma la voce non è più «non esiste niente che fabbrichi quel caso».

**2. ⚠️ La classe di difetto non è stata cercata altrove.** *Un presidio che
confronta una parola invece della proprietà* qui è saltato fuori per caso, e in
questo giro se ne sono trovati sette esemplari su una proprietà sola. Non
sappiamo se ce ne siano su altre — reloption, `proconfig`, `relpersistence`,
`convalidated`. ⛔ Non è una supposizione da inseguire adesso: è una **misura
sua**, e va fatta da qualcuno che decide di farla, non aggiunta in coda a questo
cantiere.

✅ **CHIUSO il 2026-09-07, e archiviato in `work-done/`.** La voce 1 ha una
risposta — il collaudo dice che va bene, e il caso adesso lo fabbrica qualcosa.
La voce 2 non lo trattiene: è un cantiere diverso, e si sposta in un documento
suo il giorno che qualcuno lo apre.

⚠️ **Che cosa esce di qui, perché non si perda nell'archivio** — è la stessa
ragione per cui il brief delle email era uscito dal documento «gli otto
residui»: *un filo vivo dentro un archivio non si legge*.

| Filo | Dove va |
| --- | --- |
| La **voce 2**: la classe di difetto non cercata su `proconfig`, `relpersistence`, `convalidated` | un documento suo, il giorno che qualcuno apre quella misura |
| Il presidio della voce 1 è uno **smoke**, non un pgTAP: lo lancia `smoke-baseline.sh`, **non la CI** | team DB, se e quando lo si vuole promuovere |

⛔ **Nessuno dei due è una condizione di riapertura**: il primo non è mai stato
di questo cantiere, il secondo è un presidio in più dove prima non c'era niente.
