# Brief DB — Righe e componenti di documento: i tre debiti rimasti

> **Chi chiede:** team DB (`dev/db-tid`), 2026-10-08. **A chi:** team DB; il §3 tocca anche il
> dominio approvazioni (BE).
> **Origine:** il §5 di `brief-db-righe-e-componenti-le-altre-famiglie` (archiviato in `work-done/`
> il 2026-10-08). Quel giro ha chiuso i quattro punti di D19 e ha trovato questi tre, che non
> erano nel suo perimetro. Un brief solo per tutti e tre, per decisione di Tid.
> **Stato:** ⏳ **APERTO, deciso, sviluppo non iniziato.** D-1, D-2 e D-3 decisi da Tid il
> 2026-10-08 (in fondo a ciascun paragrafo, con l'istruttoria che li regge).
> **Nel registro dei difetti DB:** voce **D20** di `migliorie-generali-da-test-valutazione.md`, che
> rimanda qui.

## 1. 🟡 Righe d'ordine e di preventivo: la quantità cambia fuori bozza

Sulle righe d'ordine il building block `vendite.trgfn_doc_righe_lock_fuori_bozza` è montato **solo
sul DELETE**: INSERT e UPDATE restano aperti di proposito, perché `data_consegna_confermata` cambia
dopo la conferma (decisione di Tid del 14 settembre). Le righe del preventivo non hanno nessun lock
(il flusso di approvazione dei prezzi scrive `stato_approvazione_prezzo` sulle righe anche fuori
bozza). A livello DB quindi la quantità di una riga d'ordine confermato o di un preventivo emesso si
può cambiare, e a un ordine confermato si può aggiungere una riga. Il BE lo impedisce già
(`richiedi_righe_in_bozza`): la regola esiste, ma solo da un lato.

Dal `20261008-34` i **componenti** delle tre famiglie sono chiusi fuori bozza. Su una riga **kit**
quel cambio lo respinge quindi il lock del componente, attraverso la propagazione della quantità o
l'init dei componenti; su una riga **semplice** passa. È la forma che il `20261005-17` aveva corretto
sul contratto («un effetto, non una regola»), un livello più in alto.

**Direzione proposta:** un lock per **colonna** sulle due tabelle di righe, che lasci aperto solo
ciò che il dominio cambia dopo la conferma (`data_consegna_confermata` sull'ordine; sul preventivo
le marche di approvazione, se il censimento del flusso lo conferma).

⏳ **D-1 (Tid):** quali colonne restano scrivibili fuori bozza, per ordine e per preventivo.

**Istruttoria (2026-10-08, sulla struttura).**

* Nessuna funzione DB modifica `ordini_righe` o `preventivi_righe` dopo averle create: zero `UPDATE`
  nei corpi della doc auto-generata. Chi le crea per copia scrive in un documento in bozza
  (`fn_push_preventivo_a_ordine` crea l'ordine `DRAFT`, `fn_crea_revisione_preventivo` la rev
  `DRAFT`). Il lock a tre porte non ferma nessun percorso DB.
* Preventivo: le marche di approvazione **non** chiedono colonne aperte. Una riga `PENDING` è
  congelata da `script.trgfn_righe_guard_pending` (anche `attivo`: non si spegne), e un
  `PENDING`/`REJECTED` su una riga attiva ferma emissione, accettazione e revisione
  (`fn_check_prezzi_autorizzati`, `fn_check_prezzi_in_attesa`). L'esito arriva quindi sempre in
  bozza. Resta fuori solo il preventivo **annullato** con una riga in attesa: lì l'esito sarà
  respinto dal lock, ed è il ciclo di vita della pratica (`refactor-prezzi.md` §4.7, BE).
* Ordine: l'unica colonna del dominio dopo la conferma è `data_consegna_confermata`. Oggi nemmeno
  il BE la lascia cambiare dopo la conferma (`richiedi_righe_in_bozza` chiude tutto): la decisione
  del 14 settembre non ha ancora un verbo.

✅ **Deciso da Tid il 2026-10-08.**

* **Preventivo:** righe chiuse fuori bozza sulle tre porte, **nessuna colonna aperta**.
* **Ordine:** righe chiuse fuori bozza sulle tre porte; resta scrivibile la sola
  `data_consegna_confermata`, e **solo negli stati da evadere** (`CONFERMATO`,
  `PARZIALMENTE_EVASO`). In `EVASO`, `ANNULLATO` e negli altri stati è chiusa anche lei.
* **Forma:** non un trigger nuovo accanto al building block, ma un argomento in più a
  `vendite.trgfn_doc_righe_lock_fuori_bozza` — l'elenco delle colonne ammesse fuori bozza, valido
  solo sull'UPDATE, col confronto a allowlist già usato da `trgfn_righe_guard_pending`
  (`to_jsonb(OLD) - ammesse` contro `to_jsonb(NEW) - ammesse`, più le colonne di audit e `tx_id`).
  ⚠️ Da risolvere in sviluppo: «stati da evadere» si legge da un **flag** dello stato se il
  catalogo `config.stati_doc_ordini` ne ha uno, non da due codici cablati nel montaggio.
* **Ricaduta BE (richiesta al team):** il verbo che cambia `data_consegna_confermata` dopo la
  conferma, sopra la porta che il DB lascia aperta.

## 2. 🟡 `user_update` nullable ben oltre le righe di documento

Letto dal catalogo il 2026-10-08: `user_update` è nullable su circa 140 tabelle, in tutti gli schemi
applicativi (`acquisti`, `anagrafiche`, `catalogo`, `config`, `magazzino`, `ui`, `vendite`…).
`linee-guida-sql.md` §7 lo vuole `NOT NULL` ovunque. Il `20261008-31` ha chiuso soltanto la famiglia
delle righe e dei componenti di documento.

Il numero è una fotografia: la regola vale a una tabella come a cento. Quello che manca davvero è
un **presidio**: oggi niente ferma una tabella nuova che nasce con la colonna nullable.

**Direzione proposta:** prima il presidio (un pgTAP che elenca le tabelle con `user_update`
nullable e accetta solo quelle dichiarate come debito), poi la bonifica per schema, ogni volta con
la preCondition «zero NULL» del `20261008-31`.

⏳ **D-2 (Tid):** presidio con registro del debito che cala, oppure bonifica in un giro solo.

**Istruttoria (2026-10-08, sulla struttura).** `script.trgfn_audit_data_user_generic` scrive
`user_update` su ogni INSERT e UPDATE (`COALESCE` con fallback `CURRENT_USER`): dove è montato,
il `NOT NULL` non può rompere chi scrive per copia. L'unico ostacolo sono le righe NULL già
presenti. Il registro che cala serve quando ogni chiusura chiede una decisione; qui la chiusura è
meccanica.

✅ **Deciso da Tid il 2026-10-08: un giro solo, presidio compreso.** Presidio pgTAP e bonifica
nello stesso giro, un changeSet per schema con l'elenco delle tabelle scritto per esteso e la
preCondition «zero NULL» del `20261008-31`. Nel registro del debito entrano solo le tabelle
**senza** trigger di audit, se ce ne sono: quelle sono un trovato a parte, non una bonifica.

## 3. 🟡 Un componente spento IN ATTESA passa nella revisione

Il guard di testa della revisione (`fn_check_prezzi_in_attesa`, «prima l'esito, poi la revisione»,
`20260924-34`) guarda solo i componenti **attivi**. Uno spento in `PENDING` non blocca, ed è giusto,
perché un componente spento non deve bloccare per sempre. Con D-1 del brief precedente però ora si
**copia**, con la sua marca e la pratica della rev N. Se nella rev N+1 qualcuno lo riaccende, torna
un prezzo in attesa legato alla pratica della revisione vecchia: è lo stesso caso che il
`20260924-34` ha chiuso per le righe. Vale identico per l'offerta, dal `20261005-19`.

Non è solo del DB: tocca il ciclo di vita della pratica su una revisione superata
(`refactor-prezzi.md` §4.7, dominio approvazioni).

⏳ **D-3 (Tid):** quale delle tre strade.
* la revisione rifiuta anche con uno spento in attesa;
* lo spento in attesa si copia senza marca e torna a chiedere l'approvazione quando si riaccende;
* riaccenderlo nella rev N+1 è rifiutato finché la pratica della rev N non ha un esito.

**Istruttoria (2026-10-08, sulla struttura).** Sui componenti il ciclo di approvazione **non
esiste**: nessun verbo li mette in `PENDING` né dà loro un esito (`approvazioni_prezzo_service`
lavora solo su righe di preventivo, contratto e offerta; il contratto dell'operatore rifiuta
`stato_approvazione_prezzo` sul componente; le funzioni DB la marca la **copiano** soltanto), e
non c'è nemmeno il controllo L2 (`update_componente`: «riservato a L1/L2/L3 futuro»). In più dal
`20261008-34` i componenti della rev N emessa sono chiusi. Quindi:

* la **terza strada** blocca per sempre: l'esito non si può scrivere sul componente chiuso della
  rev N;
* la **prima** pure: lo spento della rev N non si può più correggere (chiuso e congelato), e il
  documento non si revisionerebbe più;
* la **seconda** non apre un buco nuovo: oggi qualunque prezzo di componente passa senza
  controllo, perché la policy sui componenti non c'è.

✅ **Deciso da Tid il 2026-10-08: seconda strada.** Nella revisione di preventivo e offerta
(`fn_crea_revisione_preventivo`, `fn_crea_revisione_offerta`) un componente **spento** in
`PENDING` si copia con `stato_approvazione_prezzo` e `pratica_approvazione_prezzo_id` a NULL.
Approvato e rifiutato continuano a copiarsi 1:1; un componente **attivo** in `PENDING` continua a
fermare la revisione (`fn_check_prezzi_in_attesa`). ⚠️ **Debito dichiarato:** la nuova richiesta
di approvazione alla riaccensione appartiene all'L3 dei componenti, che oggi non esiste. Va in un
brief suo quando quel ciclo si costruisce, non qui.
