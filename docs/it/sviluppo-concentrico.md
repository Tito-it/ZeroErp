# Il Manifesto dello Sviluppo Concentrico

### Una proposta di progettazione software nata dalla pratica.

*2 marzo 2026*

---

## I.

Negli ultimi decenni abbiamo costruito software con approcci molto diversi: waterfall, agile, modulare, microservizi, event-driven.

Ognuno ha prodotto risultati utili in certi contesti e limiti evidenti in altri. Il problema non è scegliere un'etichetta, ma mantenere coerenza strutturale mentre il sistema cresce.

La proposta dello Sviluppo Concentrico parte da qui: trattare il software come una crescita per strati, non come un insieme di parti giustapposte.

---

## II.

L'immagine degli anelli di un albero aiuta a capire il modello.

Ogni anello nasce appoggiandosi a quelli precedenti. Gli strati più interni portano il carico maggiore e devono restare coerenti nel tempo. Gli strati esterni aggiungono capacità, senza rompere il senso del centro.

Nel software, questo significa: consolidare un nucleo comune e far crescere il sistema in anelli successivi, con dipendenze chiare dall'interno verso l'esterno.

---

## III. I Principi

**1) Il nucleo si progetta con rigore e si cambia solo quando serve davvero.**
Il centro definisce linguaggio, invarianti e regole condivise. Non deve essere instabile, ma neppure intoccabile: va evoluto solo per correggere limiti reali emersi durante la crescita.

**2) Il nucleo è un protocollo operativo.**
Non è "il modulo principale", ma il punto in cui sono esplicite le regole non negoziabili del sistema.

**3) Se un anello esterno rivela una debolezza interna, si corregge alla fonte.**
Le soluzioni tampone hanno un costo nascosto. Quando possibile, è meglio migliorare il livello interno che introdurre scorciatoie permanenti.

**4) Gli strati esterni dipendono dagli interni, non il contrario.**
Gli anelli esterni possono conoscere i servizi del centro; il centro non deve dipendere da dettagli periferici.

**5) Integrazione minima, vocabolario condiviso massimo.**
Le integrazioni non scompaiono sempre, ma diventano più semplici se esiste un protocollo comune (nomi, eventi, stati, regole).

**6) Crescita incrementale con coerenza verificabile.**
Ogni anello aggiunge valore concreto e rispetta i contratti degli anelli interni.


---

## IV. Cosa non è lo Sviluppo Concentrico

**Non sostituisce automaticamente altri metodi.**
Può convivere con pratiche agile, modulari o a servizi, se queste non compromettono la coerenza del centro.

**Non promette assenza di integrazioni.**
In sistemi reali alcune integrazioni sono inevitabili. L'obiettivo è ridurne numero, fragilità e costo evolutivo.

**Non è una teoria "one-size-fits-all".**
È una proposta utile soprattutto dove il dominio è ricco, i dati sono centrali e la longevità del sistema conta.

---

## V. Come praticarlo

**Parti dal centro, ma in modo concreto.**
Definisci subito: invarianti, ciclo di vita principale, regole di audit/tracciabilità, error model.

**Cresci un anello per volta.**
Ogni incremento deve chiudere un percorso end-to-end reale, non solo "aggiungere codice".

**Quando tocchi il centro, fallo con disciplina.**
Versiona i contratti, valuta impatto sugli anelli superiori, applica migrazioni e test di regressione.

**Metti le regole dove non possono essere aggirate.**
Per un sistema DB-first, i vincoli critici vanno nel database (vincoli, trigger, funzioni), non solo nel codice applicativo.

**Testa coerenza oltre alla correttezza.**
Non basta chiedere "funziona?". Devi chiedere anche: "rispetta i contratti del nucleo?", "introduce duplicazioni di regole?", "sposta logica dove non dovrebbe stare?".

---

## VI. Benefici attesi

Quando il modello è applicato bene:

- l'impatto di una modifica è più prevedibile;
- onboarding e manutenzione migliorano, perché esiste un centro leggibile;
- diminuiscono eccezioni locali, adapter ridondanti e logiche duplicate;
- il sistema resta evolvibile anche con anni di stratificazione.

Non è una promessa di semplicità assoluta. È un modo per evitare complessità superflua.

---

## VII. Nota sullo stile tecnico

La qualità strutturale non è in contrasto con velocità e consegne: è ciò che evita di pagare interessi elevati sul debito tecnico.

Curare naming, schema dati, contratti API, gestione errori e tracciabilità non è estetica: è affidabilità operativa.

In questa prospettiva, la "bellezza" di un sistema coincide con chiarezza, coerenza e assenza di elementi inutili.

---

## VIII.

Trent'anni di software gestionale mi hanno insegnato che la complessità non sparisce, ma può essere governata.

Lo Sviluppo Concentrico è una proposta pratica per far crescere sistemi ERP senza perdere integrità nel tempo: un anello alla volta, con un centro chiaro e regole condivise.

---

*La metodologia dello Sviluppo Concentrico è stata formalizzata il 2 marzo 2026 durante la progettazione di ZeroERP, sistema ERP open-source per le aziende italiane. Nasce dalla pratica sul campo e resta aperta a miglioramenti attraverso l'uso reale.*

*Michele Carlo - Autore*

---

> *Zero complessità superflua. Crescita concentrica. Coerenza lungo tutti gli anelli.*
