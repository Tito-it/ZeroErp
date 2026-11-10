## 📘 Documentazione Concettuale – Tabella `catalogo.unita_misura`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.uom_tipi](/dbzero/catalogo/tabelle/uom_tipi) — la famiglia a cui ogni unità appartiene
> * [catalogo.unita_misura_conversioni](/dbzero/catalogo/tabelle/unita_misura_conversioni) — i fattori globali fra due unità della stessa famiglia, uguali per ogni articolo
> * [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa) — le unità in cui si vende o si movimenta un articolo, con il fattore verso la sua base
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — l'unità base dell'articolo, in `uom_id`
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_unita_misura_guard_tipo](/dbzero/catalogo/funzioni/trgfn_unita_misura_guard_tipo) — vieta di cambiare famiglia a un'unità che ha conversioni, e lega il calendario al tempo
> * [vendite.fn_articolo_erogazioni](/dbzero/vendite/funzioni/fn_articolo_erogazioni) — il lettore di `conta_dal_calendario`
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — il blocco della disattivazione di un'unità ancora usata

---

### 🎯 Scopo Principale

È l'elenco delle unità di misura del sistema (pezzo, chilogrammo, litro, giorno…): ogni
quantità di articoli, documenti e movimenti la nomina con una chiave verso questa tabella.
Ogni unità appartiene a una sola famiglia di `catalogo.uom_tipi`.

La tabella dice che cosa un'unità è, non quanto vale rispetto a un'altra: i fattori stanno
in `unita_misura_conversioni` (fra unità della stessa famiglia, per tutti gli articoli) e in
`articoli_uom_operativa` (per un solo articolo, per esempio la scatola da 50 pezzi).

---

### Il codice identifica l'unità

`codice` è unico e si salva normalizzato: senza spazi ai lati e in maiuscolo. Così `kg` e
`KG` sono lo stesso codice, e l'unicità non distingue le maiuscole. Le altre tabelle non
puntano al codice ma all'`id`: cambiare il codice di un'unità non rompe i riferimenti.

`descrizione` è il nome esteso; `descrizione_fattura` è il nome da mostrare sui documenti,
facoltativo. Nel database nessuna funzione né vista legge `descrizione_fattura`: la usa il
backend.

---

### La famiglia è obbligatoria, e dopo le conversioni non cambia

`tipo_uom_id` non può essere vuoto e punta a una famiglia esistente e attiva. La famiglia
serve a una sola regola: una conversione globale si scrive solo fra due unità della stessa
famiglia (si può convertire chilogrammi in grammi, non metri in grammi).

Per tenere la regola anche nel tempo, la famiglia di un'unità che compare in almeno una
conversione non si cambia: prima si tolgono le conversioni, poi si cambia la famiglia.

---

### Le unità che si contano dal calendario

`conta_dal_calendario` dice se un canone a durata (fonte `DURATA`) misura la quantità
contando il calendario in questa unità:

* `GIORNO`: i giorni coperti dal periodo;
* `MESE`: i mesi coperti, con il mese parziale in proporzione ai giorni;
* vuoto: l'unità non si conta dal calendario.

Lo legge `vendite.fn_articolo_erogazioni`: un canone a durata si propone e si ammette solo
per un articolo la cui unità si conta dal calendario.

Contare dal calendario ha senso solo per un'unità di tempo: il valore è ammesso solo se la
famiglia dell'unità è `TEMPO` (codice interno di `uom_tipi`), altrimenti
`E_UOM_CALENDARIO_NON_TEMPO`. Il controllo scatta alla creazione dell'unità e quando cambiano
la famiglia o il conteggio. Nel seed lo hanno `GG` (giorno) e
`MESE`; le ore (`HH`) no, perché un pacchetto di ore è un canone a quantità fissa.

---

### Un'unità usata non si spegne

`attivo = false` ritira un'unità senza cancellarla. Non si può spegnere un'unità che ha
ancora righe attive che la usano: articoli, unità operative degli articoli, conversioni,
righe di listino, righe dei documenti di vendita e di acquisto. Per le righe che non hanno
un proprio `attivo` (le righe di fattura, le righe dei documenti di acquisto, le attività di
commessa) basta che una riga esista. Al contrario, una riga attiva
non può puntare a un'unità spenta, e un'unità attiva non può stare in una famiglia spenta:
il controllo scatta alla fine della transazione.

---

### Codici errore

* `E_UOM_TIPO_IN_USO` — cambio di `tipo_uom_id` su un'unità che compare in una conversione globale.
* `E_UOM_CALENDARIO_NON_TEMPO` — `conta_dal_calendario` su un'unità che non è di famiglia `TEMPO`.
* `E_ATTIVO_PADRE_NON_ATTIVO` — un'unità attiva in una famiglia non attiva, alla fine della
  transazione.
* `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` — spegnimento di un'unità che ha ancora righe attive che
  la usano; `E_ATTIVO_BLOCK_CHILDREN_EXIST` quando la riga che la usa non ha un proprio
  `attivo`.

---

### Test

* `db/pgtap/catalogo/test-uom-tipi-global-conversioni-v1.sql` — un'unità nasce con la sua
  famiglia, e una conversione fra due famiglie diverse è rifiutata.
* `db/pgtap/vendite/test-canone-durata-v1.sql` — quali unità si contano dal calendario, e il
  canone a durata che ne dipende.
* `db/pgtap/script/test-fn-codice-normalizzato-v1.sql` — la normalizzazione del codice.

* `db/pgtap/catalogo/test-uom-fattore-e-regole-v1.sql` — il cambio di famiglia rifiutato con
  una conversione e ammesso senza, il calendario rifiutato su un'unità di massa e ammesso su
  una di tempo.

---

### Note di migrazione

* 2026-04-28 — nasce `tipo_uom_id`, con la tabella `uom_tipi`: le unità che esistevano già
  ricevono la loro famiglia con un riempimento iniziale.
* 2026-10-29 — nasce `conta_dal_calendario`, per i canoni a durata (brief
  `brief-db-contratto-righe-periodiche-in-commessa`).
* 2026-11-09 — i due controlli sulla famiglia escono con codici registrati, e il calendario si
  lega alla famiglia `TEMPO` (brief-db-revisione-catalogo, giro 2).

---

{% include-markdown "signature-core.md" %}
