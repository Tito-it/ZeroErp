## 📘 Documentazione Concettuale – Tabella `anagrafiche.indirizzi_dettaglio`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.stradario](/dbzero/config/tabelle/stradario) — la via del civico, e attraverso lei comune, CAP e provincia
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — gli indirizzi dei ruoli che puntano il civico
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — gli indirizzi dei soggetti che puntano il civico
> * [storico.indirizzi_dettaglio](/dbzero/storico/tabelle/indirizzi_dettaglio) — le versioni conservate
>
> Approfondimento viste:
>
> * [anagrafiche.vw_indirizzi_dettaglio](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio) — il civico con comune, CAP e provincia
> * [script.vw_indirizzo_completo](/dbzero/script/views/vw_indirizzo_completo) — la via risolta, da cui si normalizza
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_build_indirizzo_normalizzato](/dbzero/anagrafiche/funzioni/fn_build_indirizzo_normalizzato) — la normalizzazione del civico, in un posto solo
> * [anagrafiche.fn_get_or_create_indirizzo_dettaglio](/dbzero/anagrafiche/funzioni/fn_get_or_create_indirizzo_dettaglio) — il «trova o crea» del civico
> * [anagrafiche.trgfn_indirizzi_dettaglio_normalize](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_dettaglio_normalize) — scrive la riga normalizzata
> * [anagrafiche.trgfn_indirizzi_dettaglio_guard_chiave](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_dettaglio_guard_chiave) — giudica la chiave del civico
> * [anagrafiche.trgfn_indirizzi_dettaglio_protect_update](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_dettaglio_protect_update) — un civico non cambia via
> * [dbops.fn_admin_merge_stradario](/dbzero/dbops/funzioni/fn_admin_merge_stradario) — la fusione delle vie, l'unica che sposta i civici
> * [maintenance.proc_bump_indirizzi_dettaglio](/dbzero/maintenance/funzioni/proc_bump_indirizzi_dettaglio) — la rinormalizzazione dei civici di una via
> * [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic) — lo storico
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — il quadro degli indirizzi e dello stradario
> * [Linee guida SQL §8.4-bis](/linee-guida-sql#84-bis-indici-unique-con-colonne-nullable) — indici `UNIQUE` con colonne nullable

---

### 🎯 Scopo Principale

`anagrafiche.indirizzi_dettaglio` è il civico: una via dello stradario con numero, estensione, palazzina,
scala, piano e interno. Ogni indirizzo fisico è una riga sola, e la puntano tutti quelli che lo usano: gli
indirizzi dei ruoli e dei soggetti, i punti di fornitura, le istanze, i magazzini, le unità catastali.

---

### ⭐ Un civico, una riga

La chiave del civico sono la via e i sei valori del dettaglio, e l'indice `uq_indirizzi_dettaglio_norm_v2` è
`NULLS NOT DISTINCT`: due civici senza numero (`SNC`) con lo stesso dettaglio sono lo stesso civico. La chiave
lavora sui valori **come si salvano**: il trigger di normalizzazione porta tutto in maiuscolo, fa del testo vuoto
nessun valore e scrive l'estensione col `/`, così `a`, `A` e `/A` sono la stessa estensione. Le regole della
normalizzazione stanno in `anagrafiche.fn_build_indirizzo_normalizzato`.

Sulla chiave il guard `anagrafiche.trgfn_indirizzi_dettaglio_guard_chiave` dice che cosa non va, col codice e col
campo: il civico, se c'è, è maggiore di zero (il civico senza numero è il civico vuoto); i valori del dettaglio
hanno almeno una lettera o una cifra; una modifica non porta la riga sulla chiave di un'altra. I `CHECK`
`chk_indirizzi_dettaglio_civico_positivo` e `chk_indirizzi_dettaglio_dettaglio_leggibile` e l'indice restano come
rete.

Chi deve collegare un civico non lo inserisce: lo chiede a `anagrafiche.fn_get_or_create_indirizzo_dettaglio`,
che lo trova o lo crea, e riattiva quello trovato spento.

---

### Correggere un civico vale per tutti

Una modifica sul posto vuol dire «correggo questo indirizzo per tutti quelli che lo usano», e chi lo usa lo
vede subito, perché nessuno ne tiene una copia del testo. Le tre colonne derivate (`via_norm`, `civico_norm`,
`indirizzo_normalizzato`) le riscrive il trigger a ogni scrittura; chi le passa viene ignorato.

---

### ⛔ Un civico non cambia via

Il cambio di `stradario_id` è rifiutato (`anagrafiche.trgfn_indirizzi_dettaglio_protect_update`,
`E_COLONNA_NON_MODIFICABILE`): un civico su un'altra via è un altro civico, e si crea. Lo sposta solo la fusione
delle vie, `dbops.fn_admin_merge_stradario`, che apre la porta per il solo tempo del ripuntamento e la richiude.

Un civico non nasce su una via soppressa (fusa in un'altra, `config.stradario.obsoleto_dal`), né vi si sposta:
lo rifiuta `trg_indirizzi_dettaglio_a10_via_non_soppressa_ins_upd` (`E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`). Un civico
che c'è già si modifica sempre: conta solo il cambio di via.

---

### Quando cambia la via, i civici si rinormalizzano

La via normalizzata del civico è una fotografia del toponimo e del nome della via. Quando cambia ciò da cui
dipende, `maintenance.proc_bump_indirizzi_dettaglio` riscrive i civici di quella via con lo stesso valore, e il
trigger li rinormalizza; il cambio di un toponimo la chiama da sé per ogni via. Non è uno spostamento: non
tocca la via del civico, e non apre la porta della fusione.

---

### Spegnere un civico

Un civico non si spegne finché qualcuno lo punta: lo impediscono i guard generati sulle sei tabelle figlie
(indirizzi dei ruoli e dei soggetti, punti di fornitura, istanze, magazzini, unità catastali). Un civico spento
non si collega a niente di nuovo, e torna in uso quando il «trova o crea» lo trova.

---

### Lo storico è continuo

`storicizza` nasce `true`, e la tabella è fra quelle che tengono il flag acceso
(`config.storico_set_storicizza`): ogni modifica lascia in `storico.indirizzi_dettaglio` la versione nuova (la
prima anche quella di partenza), e ogni cancellazione la sua. Vale per ogni strada: la modifica dal pannello, la
riattivazione del «trova o crea», la fusione di due vie, la rinormalizzazione di una via. La rinormalizzazione
riscrive ogni civico della via, e ognuno lascia una versione anche quando il testo normalizzato non cambia. Una
scrittura che porta il flag a `false` non lascia traccia, e la riga resta senza storico finché qualcuno non lo
riaccende.

---

### La posizione

`civic_geoloc` è il punto del civico, `street_geoloc` la posizione della via. Gli indirizzi dei ruoli e dei
soggetti copiano `civic_geoloc` quando si scrivono; le viste risolte, se il civico non ha il suo punto, usano
quello della via.

---

### ⚠️ Che cosa oggi non copre

* **Un civico la cui via smette di risolversi** (per esempio il comune perde la provincia) esce dalle letture
  che passano da `anagrafiche.vw_indirizzi_dettaglio`, e qualunque sua modifica fallisce con un errore tecnico
  di colonna obbligatoria: la normalizzazione non trova la via e lascia `via_norm` vuota.
* **La porta della fusione è un parametro di sessione** (`zeroerp.maintenance_indirizzi_dettaglio`): chiunque
  scriva può accenderlo, e con la porta accesa il cambio di via passa senza giudizio.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-dettaglio-unicita-v1.sql` — l'indice sulle sette colonne, i tre rifiuti
  del guard, la stessa chiave scritta in modi diversi che trova la stessa riga, la riattivazione.
* `db/pgtap/anagrafiche/test-fn-get-or-create-indirizzo-dettaglio.sql` — il «trova o crea».
* `db/pgtap/maintenance/test-bump-toponomastica-v1.sql` — la rinormalizzazione dopo il cambio di un toponimo,
  senza la porta accesa.
* `db/pgtap/dbops/test-fusioni-comune-stradario-v1.sql` — la fusione che sposta i civici sulla via viva, la via
  soppressa che non riceve civici nuovi.
* `db/pgtap/anagrafiche/test-storico-indirizzi-continuo-v1.sql` — lo storico continuo: il civico nasce col flag
  acceso, due modifiche e la cancellazione lasciano ciascuna la sua versione.

---

### Note di migrazione

* 2026-10-25 — la chiave passa alle sette colonne nude con `NULLS NOT DISTINCT` (prima un civico `SNC` restava
  fuori dall'indice e lo zero era un secondo modo di dirlo), e nasce il guard della chiave.
* 2026-11-03 — la rinormalizzazione di una via smette di accendere la porta della fusione: le basta un
  aggiornamento che non cambia la via.
* 2026-11-07 — la fusione delle vie sposta i civici, e un civico non nasce più su una via soppressa.

---

{% include-markdown "signature-core.md" %}
