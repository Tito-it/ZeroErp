## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_articoli_guard_struttura_se_usato`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — la tabella su cui il guard è montato, con la regola delle colonne bloccate e libere
> * [dbops.lock_columns_conditional](/dbzero/dbops/tabelle/lock_columns_conditional) — le regole gemelle che spengono gli stessi campi nel form
>
> Approfondimento funzioni:
>
> * [catalogo.fn_articolo_usato](/dbzero/catalogo/funzioni/fn_articolo_usato) — il predicato «l'articolo è usato»
> * [catalogo.fn_articolo_colonne_struttura](/dbzero/catalogo/funzioni/fn_articolo_colonne_struttura) — l'elenco leggibile delle colonne strutturali
> * [catalogo.fn_articolo_correggi_struttura](/dbzero/catalogo/funzioni/fn_articolo_correggi_struttura) — la porta amministratore
> * [script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella) — la seconda chiave della porta

---

### 🎯 Scopo Principale

Un articolo usato non cambia le colonne che decidono come si vende e come sta a magazzino. Il
guard rifiuta la modifica, salvo che arrivi dalla porta amministratore.

Le colonne sono otto: `is_composito`, `is_solo_componente`, `natura_vendita_id`,
`causale_onere_id`, `listino_tipologia_id`, `gestito_a_magazzino`, `requires_lotto`,
`requires_serial`. A valle ci sono listini, ordini, bolle e giacenze costruiti su quelle
caratteristiche, e non le rincorrono se cambiano.

---

### Come giudica

* Il guard è `BEFORE UPDATE` delle otto colonne. Se nessuna cambia davvero, esce: un
  salvataggio del form che riscrive gli stessi valori passa.
* Se l'articolo è usato (`catalogo.fn_articolo_usato`), il cambio è rifiutato
  (`E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE`). Il campo è la prima colonna cambiata, nell'ordine
  dell'elenco; il messaggio porta il codice dell'articolo e il nome leggibile del campo.
* Il messaggio non dice dove l'articolo è usato: può essere un documento di un'altra azienda, che
  chi modifica non vede.

Nel form le regole gemelle di `dbops.lock_columns_conditional` chiamano lo stesso predicato, e
spengono il campo prima che l'utente provi a cambiarlo.

---

### La porta amministratore

Passa solo il verbo `catalogo.fn_articolo_correggi_struttura` (SUPER_ADMIN). Il verbo accende
per la sola transazione la GUC `zeroerp.articolo_correggi_struttura` con l'id dell'articolo, e il
guard la onora solo se chi scrive è anche il proprietario della tabella
(`script.fn_is_proprietario_tabella`). Il verbo è SECURITY DEFINER, quindi lo è; una sessione
applicativa che accende la GUC a mano non apre niente.

Dalla porta passa solo questa regola: i guard della distinta, dell'onere e del listino parlano lo
stesso.

---

### L'elenco delle colonne è scritto qui due volte

Un trigger non legge le sue colonne da una funzione. Per questo l'elenco sta nel montaggio
(`UPDATE OF`) e nella scelta del campo cambiato, mentre l'elenco leggibile è
`catalogo.fn_articolo_colonne_struttura`. Un pgTAP controlla che coincidano: chi aggiunge una
colonna al registro senza toccare il guard lo vede rosso.

---

### ⚠️ Che cosa oggi non copre

* **L'etichetta leggibile dei flag è scritta due volte.** Il nome a video di ogni colonna sta
  qui e, per quattro colonne, anche in `catalogo.trgfn_articoli_guard_onere_natura`.
* **Il predicato «usato» ha i suoi limiti**: una FK verso una chiave diversa da `id`, o una FK
  composita, non è giudicata come dovrebbe (vedi `catalogo.fn_articolo_usato`).

---

### Codici errore

* `E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE` — una delle otto colonne cambia su un articolo usato,
  fuori dalla porta amministratore.

---

### Test

* `db/pgtap/catalogo/test-articolo-usato-struttura-v1.sql` — l'articolo usato non cambia
  struttura, anche se l'uso è in un documento di un'altra azienda; IVA e descrizione restano
  libere; il form spegne gli stessi campi; la GUC accesa a mano non apre la porta.
* `db/pgtap/catalogo/test-articolo-colonne-struttura-v1.sql` — il montaggio e la scelta del
  campo nominano esattamente le colonne dell'elenco leggibile.
* `db/pgtap/vendite/test-righe-articolo-ammesso-v1.sql` — un articolo che sta in una riga di
  documento non cambia struttura.

---

### Note di migrazione

* 2026-10-13 — nasce, e prende il posto del guard «solo componente in bozza» e della sua regola
  del form. Quel guard proteggeva un caso solo (le righe in bozza, per `is_solo_componente`) e
  leggeva i documenti con la RLS di chi modifica: le bozze delle altre aziende non le vedeva
  (brief-db-articoli-ammessi-per-documento).

---

{% include-markdown "signature-core.md" %}
