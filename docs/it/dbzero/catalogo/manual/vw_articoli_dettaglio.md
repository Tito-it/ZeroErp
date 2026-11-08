## 📘 Documentazione Concettuale – Vista `catalogo.vw_articoli_dettaglio`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — la tabella da cui parte la vista, una riga per articolo
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — la distinta che decide `has_componenti_alla_data`
> * [config.nature_vendita](/dbzero/config/tabelle/nature_vendita) — la natura di vendita e la sua destinazione
> * [config.modi_approvvigionamento](/dbzero/config/tabelle/modi_approvvigionamento) — il modo di approvvigionamento decodificato
>
> Approfondimento funzioni:
>
> * [script.fn_e_obsoleto](/dbzero/script/funzioni/fn_e_obsoleto) — la regola «ritirato alla data operativa» dietro `e_obsoleto`
> * [catalogo.fn_articolo_padre_di_distinta_in_vigore](/dbzero/catalogo/funzioni/fn_articolo_padre_di_distinta_in_vigore) — la stessa domanda di `has_componenti_alla_data`, per i guard
> * [catalogo.fn_articoli_ammessi](/dbzero/catalogo/funzioni/fn_articoli_ammessi) — il picker, a cui la vista aggiunge le colonne dell'articolo
>
> Guide:
>
> * [Uso di obsoleto](/guide/uso-di-obsoleto) — che cosa vuol dire un articolo ritirato

---

### 🎯 Scopo Principale

L'articolo con le decodifiche dei suoi vocabolari e le capability della distinta, una riga per
articolo. È la vista della lista articoli, del drawer e delle colonne che si uniscono al picker
delle righe.

Si legge e basta: le modifiche vanno sulla tabella `catalogo.articoli`.

---

### Che cosa aggiunge all'articolo

* **Le decodifiche**, sempre in `LEFT JOIN`: unità di misura, tipologia, gruppo, voce di spesa,
  IVA (con l'aliquota), tipologia di listino, natura di vendita, modo di approvvigionamento.
* **La natura di vendita** con la sua destinazione (`natura_vendita_destinazione_tipo`):
  `ORDINE_VENDITA` per la merce, `COMMESSA` per il servizio una tantum, `CONTRATTO` per il
  servizio ricorrente. È la destinazione che instrada la riga venduta.
* **Il modo di approvvigionamento** con `modo_approvvigionamento_codice_interno` per la logica e
  `modo_approvvigionamento_descrizione` a video. La decodifica non si chiama `_codice`, perché il
  valore viene dalla chiave immutabile, e il nome deve dirlo.

---

### Le capability della distinta

* `puo_gestire_bom` è vera se l'articolo è composito e non è solo componente: solo allora il
  drawer apre la gestione della distinta.
* `motivo_non_gestibile_bom` dice perché no: `ARTICOLO_SOLO_COMPONENTE` se l'articolo è solo
  componente (vince anche se è composito), altrimenti `ARTICOLO_NON_COMPOSITO`. È vuoto quando
  la gestione è possibile.
* `has_componenti_alla_data` è vera se l'articolo composito ha almeno un legame attivo in vigore
  alla data operativa.

---

### L'articolo dice se è un onere e se è ritirato

* `e_onere` è vera quando l'articolo ha una causale d'onere; `causale_onere_id` è la causale.
  Servono al picker delle righe (sulla riga d'ordine nuova il form nasconde le date di consegna
  di un onere) e al form dell'articolo, che spegne magazzino, composito, lotto e matricola su un
  onere. Sulla **riga** di documento la domanda «è un onere?» si fa alla vista della riga, che
  guarda la natura fissata sulla riga.
* `obsoleto_dal` è la data del ritiro: vuota, si sceglie; futura, ritiro programmato;
  cancellarla riattiva l'articolo per le scelte nuove. `e_obsoleto` è vera quando l'articolo è
  ritirato alla data operativa, con lo stesso building block del guard di riga e del picker:
  chi legge la vista non confronta date.

Ritirato non vuol dire spento: l'articolo resta `attivo` e valido sulle righe che lo usano già.

---

### I flag che il form spegne non si decidono qui

La vista porta i flag dell'articolo così come sono. Quali campi il drawer mostra spenti lo
decidono le regole di `dbops.lock_columns_conditional`: `requires_lotto`, per esempio, non
entra nella distinta ma si spegne quando l'articolo è usato, come gli altri flag strutturali.

---

### ⭐ Niente `security_invoker`

La vista non ha `security_invoker`, e non deve prenderla per imitazione: `catalogo.articoli`
non ha RLS, e la vista non attraversa tabelle protette.

---

### ⚠️ Che cosa oggi non copre

* **Le colonne nuove vanno in coda.** La vista si estende con `CREATE OR REPLACE VIEW`, che può
  solo aggiungere colonne alla fine; chi legge le colonne per nome (il backend) vede una
  colonna nuova solo quando la nomina. Oggi `obsoleto_dal` ed `e_obsoleto` non sono ancora nella
  proiezione del backend.
* **`has_componenti_alla_data` riscrive la regola a mano.** È la stessa domanda di
  `catalogo.fn_articolo_padre_di_distinta_in_vigore` (legame attivo, in vigore alla data
  operativa), ma scritta di nuovo nella vista.
* **Gli `*_ref_id` ripetono le FK.** `uom_ref_id`, `tipologia_ref_id`, `gruppo_ref_id`,
  `spesa_ref_id` e `iva_ref_id` valgono quanto la FK dell'articolo, quando la voce esiste.

---

### Test

* `db/pgtap/catalogo/test-vw-articoli-dettaglio-bom-capability-v1.sql` — le due capability della
  distinta nei tre casi, compreso l'articolo composito e solo componente.
* `db/pgtap/catalogo/test-vw-articoli-dettaglio-e-onere-v1.sql` — `e_onere` e `causale_onere_id`
  su un onere e su una merce, e la loro posizione dopo `requires_lotto`.
* `db/pgtap/catalogo/test-articoli-approvvigionamento-v1.sql` — le colonne di approvvigionamento
  nella vista.
* `db/pgtap/vendite/test-articolo-ritirato-v1.sql` — `e_obsoleto` alla data operativa.
* `db/pgtap/rls/test-rls-viste-security-invoker.sql` — quali viste devono avere
  `security_invoker`, giudicato sul merito.

---

### Note di migrazione

* 2026-04-28 — nascono le capability della distinta.
* 2026-09-13 — in coda il modo di approvvigionamento, `gestito_a_magazzino` e
  `lead_time_giorni` (brief-db-modifiche-certe-ciclo-vendita-e-articolo).
* 2026-09-18 — in coda `requires_lotto` (brief-db-magazzino-lotto-2-motore).
* 2026-10-19 — la destinazione della merce si chiama `ORDINE_VENDITA` (prima `ORDINE`).
* 2026-10-25 — la vista è ricreata identica, perché `note_target_tipo` cambia tipo e vale
  `ARTICOLO`.
* 2026-11-03 — in coda `e_onere` e `causale_onere_id` (brief-db-addebito-trasporto-ordine).
* 2026-11-06 — in coda `obsoleto_dal` ed `e_obsoleto` (brief-db-articoli-obsoleto-dal).

---

{% include-markdown "signature-core.md" %}
