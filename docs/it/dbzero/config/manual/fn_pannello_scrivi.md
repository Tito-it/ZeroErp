## 📘 Documentazione Concettuale – Funzione `config.fn_pannello_scrivi()`

> **Ultimo aggiornamento**: 13 novembre 2026

> 👀 **Vedi anche**
>
> **La lista che legge:** [config.tabelle_gestibili](/dbzero/config/tabelle/tabelle_gestibili)
>
> **Il permesso:** [script.fn_guard_livello](/dbzero/script/funzioni/fn_guard_livello)
>
> **Le colonne che scrive:** [config.fn_pannello_colonne_scrivibili](/dbzero/config/funzioni/fn_pannello_colonne_scrivibili)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

È il **verbo** del pannello «Gestione tabelle»: l'unica strada con cui il
pannello salva una riga. Inserisce una riga nuova (`p_id` vuoto) o modifica
quella con l'`id` dato, e restituisce la riga salvata.

Prima di questo verbo il backend scriveva da sé, e chiedeva il livello `TUTTO`
sulla **Configurazione** per qualunque tabella. Adesso il livello si chiede
sull'**oggetto a cui la riga appartiene**: chi ha `TUTTO` solo sulla
Configurazione non modifica più le causali di magazzino.

---

### Cosa controlla, in ordine

| Passo | Controllo | Se non va |
| --- | --- | --- |
| 0 | la tabella è nella lista con `pannello`, esiste e non ha la RLS | `E_PANNELLO_TABELLA_NON_AMMESSA` |
| 1 | chi agisce ha `TUTTO` sull'oggetto della tabella | `E_PERMESSO_NEGATO` |
| 2 | c'è almeno un campo | `E_PANNELLO_DATI_VUOTI` |
| 2 | ogni campo è una colonna che si può scrivere a mano | `E_PANNELLO_CAMPO_NON_AMMESSO`, con il campo |
| 3 | in modifica, la riga esiste | `E_PANNELLO_RIGA_NON_TROVATA` |

Quali colonne si scrivono lo dice `config.fn_pannello_colonne_scrivibili`, che
legge anche il backend per decidere i campi del form: la regola sta in un posto
solo (dal 27-09-2026). ⭐ Un campo che non va bene si **rifiuta**, non si
ignora: prima il backend lo scartava in silenzio, e un salvataggio sbagliato
sembrava riuscito.

Si scrivono solo i campi mandati: gli altri tengono il valore di prima (o il
default, per una riga nuova). I valori li converte il database, secondo il tipo
di ogni colonna.

⭐ **Un campo di testo svuotato si salva come «nessun valore»** (dal 13-11-2026).
Quando una colonna di testo **può restare vuota**, il verbo salva come `NULL` il
campo arrivato vuoto o con soli spazi: è ciò che manda il form quando si
cancella il contenuto di un campo in modifica. Così l'assenza ha una forma sola,
e le colonne che vietano la stringa vuota (la nota degli assoggettamenti IVA e
degli stili di nota) non rifiutano più il salvataggio. Una colonna di testo
**obbligatoria** riceve il campo vuoto così com'è: per esempio il separatore di
`config.sistema_codici`, dove vuoto vuol dire «nessun separatore». Un testo vero
non si tocca, spazi compresi.

La riga che il verbo restituisce ha l'`id` e le colonne scrivibili: gli stessi
campi del form.

Le regole della tabella (i suoi trigger: audit, codici immutabili, `attivo`,
guard di dominio) valgono come sempre, e i loro rifiuti arrivano col loro
codice. Non c'è la cancellazione: una riga si ritira con `attivo` o
`obsoleto_dal`, come prima.

---

### Perché gira con i privilegi del proprietario

Alcune tabelle della lista sono chiuse all'applicazione: oggi le causali di
magazzino. L'app non le può scrivere direttamente, solo attraverso questo verbo,
che prima controlla il permesso. È il modello «una scrittura = un verbo»
(brief-db-permesso-nel-verbo-di-scrittura).

Per la stessa ragione il verbo **non accetta tabelle con la RLS**: con i
privilegi del proprietario non vedrebbe il perimetro, e non lo sa rimettere per
una tabella qualunque.

Presidio: `db/pgtap/config/test-fn-pannello-scrivi-v1.sql`.

{% include-markdown "signature-core.md" %}
