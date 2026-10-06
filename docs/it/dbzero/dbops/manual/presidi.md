## 📘 Documentazione Concettuale – Tabella `dbops.presidi`

> 👀 **Vedi anche**
>
**Approfondimento guide:**
>
• [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — *il meccanismo condiviso: la misura e il registro*
>
**Approfondimento funzioni:**
>
• [dbops.fn_conta_presidio](/dbzero/dbops/manual/fn_conta_presidio)
>
**Approfondimento tabelle:**
>
• [dbops.presidi_testi](/dbzero/dbops/manual/presidi_testi) — *il testo per chi deve agire*
> • [dbops.riferimenti_morti_esenzioni](/dbzero/dbops/manual/riferimenti_morti_esenzioni)
> • [dbops.codici_errore_senza_policy](/dbzero/dbops/manual/codici_errore_senza_policy)
> • [dbops.processi](/dbzero/dbops/manual/processi)
>

### 🎯 Scopo Principale
(latest review 10-09-2026)

Il database ha una trentina di **viste di controllo**: guardano se qualcosa si è
rotto in silenzio — un lavoro notturno fallito, un operatore configurato a metà,
una tabella che dovrebbe filtrare e non filtra.

Fanno il loro mestiere. Il problema è un altro, e questa tabella nasce da lì:

> **Guardare non è di nessuno.**

Il 9 settembre 2026 un lavoro notturno era fallito **quattro notti di fila**. La
riga che lo diceva stava in una vista che porta nel nome ciò che serviva —
*`vw_coda_lavori_da_guardare`* — ed è rimasta lì quattro notti. Il controllo
aveva funzionato benissimo: non aveva un destinatario.

`dbops.presidi` è il pezzo che mancava: **per ogni vista di controllo, che cosa
significa una sua riga**. È quello che permette a un programma di prendere
quelle viste e portarne il contenuto davanti a una persona, senza sommergerla.

---

### ⭐ Perché non bastava «manda un elenco delle viste non vuote»

Perché **non tutte le viste dicono la stessa cosa quando non sono vuote**.

* Su `vw_coda_lavori_da_guardare` una riga è un guasto **di adesso**: un lavoro è
  fallito stanotte.
* Su `vw_riferimenti_morti_da_sanare` le righe sono un **debito noto**, con un
  registro accanto che dice quali sono già state decise: l'allarme non è «ce ne
  sono», è «ce n'è una che nessuno aveva registrato».
* Su `vw_trigger_functions` ci sono **duemila righe** ed è la condizione normale:
  è l'elenco dei trigger del database, non un allarme.

Un avviso che non distingue questi tre casi si apre con duemila righe di
inventario. E un avviso rumoroso viene ignorato al secondo invio — cioè finisce
esattamente come il controllo che voleva salvare.

⭐ **E nessuna delle tre nature è deducibile dal nome della vista.** La sa chi
l'ha scritta, e infatti in trentuno casi su trentadue era già scritta — in
prosa, nel commento della vista, cioè in una forma che nessun programma può
leggere. Questa tabella la rende leggibile a una macchina senza toglierla di lì.

---

### Le cinque nature

| Natura | Che cosa significa una riga | Va nel digest? |
| --- | --- | --- |
| **ZERO** | un guasto **adesso**: qualunque riga è un allarme | sì, e per prima |
| **REGISTRO** | un **debito noto**. L'allarme è la voce che *nessuno aveva registrato* | sì, se il registro non la conosce |
| **LAVORAZIONE** | una **coda** che qualcuno o qualcosa consuma, o una **spia** da guardare per tendenza | sì, come tendenza |
| **CANCELLO** | è **già presidiata** altrove — in CI o in un test — e quel controllo blocca già il lavoro | no: ripetere ciò che un cancello ha già fermato è rumore |
| **INVENTARIO** | un **panorama**: elenca anche i sani | no, mai |

⛔ **Anche un inventario si dichiara.** Se una vista mancasse dal catalogo non si
saprebbe se è un inventario o una dimenticanza — e la differenza è tutta lì.

---

### ⭐ Il debito si tiene con un registro, non con un numero

La strada breve sarebbe stata una colonna `soglia`: *«oggi sono 508, l'allarme
scatta a 509»*. È stata scartata, e la ragione vale oltre questo caso.

Un numero vede solo il **totale**. È cieco sullo **scambio**: un debito saldato e
un difetto nuovo comparsi lo stesso giorno lasciano il conteggio fermo, e il
controllo tace.

E non è un caso di scuola. Su `vw_processi_che_bypassano` c'è oggi **una** riga:
un ruolo tecnico che scavalca i filtri, dichiarato, con la data in cui verrà
ritirato. Il giorno in cui quel debito si chiude e — nello stesso giro — un altro
ruolo prende lo stesso privilegio senza dichiararlo, il numero resta **uno**, e
il controllo sulla sicurezza delle righe diventa muto.

⇒ La colonna `registro` porta il **nome della tabella** che tiene le voci note.
Il progetto ne aveva già tre, tutte con la stessa forma: una voce per caso, il
motivo scritto, la data.

⚠️ Dove il registro non esiste ancora, `registro` è vuoto **e la nota dice che
quello è il lavoro**. Un vuoto dichiarato, non una dimenticanza.

---

### ⭐ Si dichiara lo stato *atteso*, non quelli di allarme

Su quattro viste la domanda non è «è vuota?». Portano una colonna di stato, e la
regola scritta nel loro commento è *«nessuna riga NON_DICHIARATO»*: una riga
dichiarata è **attesa**, e suonare su di essa vorrebbe dire suonare su una cosa
già decisa.

Si sarebbe potuto elencare gli stati **di allarme**. Sembra più naturale ed è la
scelta sbagliata, perché è quella permissiva:

> Uno stato **nuovo**, aggiunto domani a una di quelle viste, non sarebbe
> nell'elenco — e cadrebbe nel **silenzio**.

È l'unico verso in cui un controllo marcisce senza che nessuno se ne accorga.
Perciò si dichiara l'unico stato **accettato**, e l'allarme è tutto il resto:
uno stato nuovo cade nell'allarme, e chi lo aggiunge deve venire qui a decidere.

⭐ E si prende gratis il caso a più valori. Su `vw_rls_perimetro_scoperto` gli
stati sono **tre**: uno atteso, uno che è un allarme, e uno che è una riga di
registro da togliere. *«Diverso da quello atteso»* prende gli altri due senza
doverli nominare.

---

### ⚠️ Due colonne che sembrano dettagli e non lo sono

**`cadenza`** non è solo una scelta di rumore, è anche una di **costo**:
`vw_riferimenti_morti_da_sanare` ricompila circa cinquecento funzioni a ogni
lettura. Non è una vista da interrogare tutte le notti, e il costo è un attributo
della singola riga — non una proprietà del digest.

**`perimetro`** risponde a una domanda che sfugge: *questo conteggio è onesto
letto da un programma senza utente?* Tre viste leggono tabelle protette dal
filtro per righe. Un comando lanciato da un timer non ha una veste, quindi il
filtro le rende **zero** — e su una vista che deve restare vuota, «zero righe» e
«non ho potuto vedere» **si scrivono uguale**. Quelle tre si contano solo
attraverso [`dbops.fn_conta_presidio`](/dbzero/dbops/manual/fn_conta_presidio), e
di quelle il digest riporta il **numero** e non le righe.

---

### Chi lo spegne, e con quali parole

Dal 2026-10-06 ogni presidio che può accendersi dice anche **a chi tocca
spegnerlo**, nella colonna `chi_agisce`:

| Valore | Chi è | Che cosa significa per chi legge il pannello |
| --- | --- | --- |
| `AMMINISTRATORE` | chi usa l'applicazione | «puoi sistemarlo tu» |
| `SISTEMISTA` | chi gestisce server, servizi, timer e ruoli del database | «da segnalare a chi gestisce il server» |
| `SVILUPPO` | serve una modifica al codice o al database | «da segnalare allo sviluppo» |

È un **dato** e non una frase perché il pannello deve poter distinguere *«tocca a
te»* da *«inoltra»*, e il digest deve poterli raggruppare. È obbligatoria su ogni
natura tranne `INVENTARIO`, che non si accende: lo impone un vincolo del database.

Le **parole** per chi agisce — cosa vuol dire una riga, cosa fare — stanno in
[`dbops.presidi_testi`](/dbzero/dbops/manual/presidi_testi). La `nota` di questa
tabella e il `COMMENT` della vista restano scritti per chi **mantiene** il
presidio, e non si riscrivono.

---

### ⛔ Che cosa NON sta qui

**Il destinatario.** A chi arriva la posta è un fatto di **questa installazione**,
non del software: un indirizzo dentro un catalogo o viaggia su ogni installazione
o rende la riga non seminabile. È la stessa ragione per cui la cadenza dei lavori
notturni non sta su `dbops.processi` e le sveglie dei comandi stanno nei file di
deploy del backend: *come e a chi si suona è un fatto di deploy, e vive dove vive
il deploy*.

**La soglia.** Vedi sopra.

**Le viste stesse.** Nessuna è stata toccata: sono già scritte bene, e il
catalogo rende leggibile a un programma ciò che loro spiegano già in prosa.

---

### Come si aggiunge una riga

1. Si scrive la vista, con il suo `COMMENT` come sempre.
2. Si aggiunge una riga al CSV di seed, `80_data/sql/dbops/presidi.csv`, con
   `chi_agisce` (vuota, cioè `NULL`, solo su un `INVENTARIO`).
3. Se il presidio può accendersi, si aggiunge la riga `it` a
   `80_data/sql/dbops/presidi_testi.csv`: significato e azione.
4. ⛔ **Non c'è un passo 4.** Se il passo 2 si dimentica, il test
   `db/pgtap/dbops/test-catalogo-presidi-v1.sql` diventa rosso: è il verso che
   impedisce a una vista nuova di nascere fuori dal digest. E il verso opposto —
   una riga di catalogo che non trova più la sua vista — è il test accanto. Se
   si dimentica il passo 3, è rosso `db/pgtap/dbops/test-presidi-testi-v1.sql`;
   senza `chi_agisce` la riga la rifiuta il database.

⚠️ Il seed è un mirror `runOnChange`: rilegge **tutto** il file a ogni migrate,
quindi appendere una riga ri-propone ai vincoli anche tutte quelle già scritte.
Prima di toccarlo conviene provare l'upsert su tutte le righe dentro una
transazione che si annulla.

---

*Brief: `docs/it/dev/work-done/brief-db-un-destinatario-per-i-presidi.md`;
`chi_agisce` e i testi: `docs/it/dev/work-in-progress/brief-db-presidi-cosa-significa-cosa-fare.md`.*
