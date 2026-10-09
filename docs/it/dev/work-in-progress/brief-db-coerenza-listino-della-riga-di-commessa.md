# Brief DB — Il listino citato da una riga di commessa: stesso emittente, versione giusta, in vigore

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-09. **A chi:** team DB.
> **Origine:** debito emerso lavorando
> [brief-db-riga-listino-propagata-dalla-commessa](brief-db-riga-listino-propagata-dalla-commessa.md)
> (§6, D-3). Quel brief fa scrivere `listino_riga_id`; questo dice che cosa la
> colonna può contenere.
> **Stato:** 🟡 aperto, da progettare.

## 1. Il problema

Su `vendite.commesse_attivita` (e su `vendite.attivita_fatturabili`, che la copia)
nessuna regola lega la provenienza del prezzo alla commessa:

| Colonna | Cosa garantisce oggi | Cosa manca |
| --- | --- | --- |
| `listino_versione_id` | la FK: la versione esiste | che il listino sia dell'**emittente della commessa** |
| `listino_riga_id` | la FK: la riga esiste | che la riga appartenga a **`listino_versione_id`** (e quindi allo stesso listino) |

Contratto letto il 2026-10-09: nessun trigger su queste due tabelle legge
`listino_versione_id` o `listino_riga_id`, e nessun `CHECK` li confronta. Il
resolver (`fn_resolve_prezzo_listino_v2[_esito]`) sceglie i listini
dell'emittente che gli si passa, ma la madre del push e l'`UPDATE` diretto del BE
(riallinea, sblocca) scrivono quello che ricevono.

⚠️ **E nemmeno lo stato della versione.** I rami del resolver che cercano la
versione da soli la prendono solo `ATTIVA`/`CHIUSA` («Bug A fix: esclude BOZZA»).
Il **percorso rapido** (`p_listino_versione_id_preferito`, usato dal BE in
`pricing_repository`) legge invece la versione che gli si passa **senza guardarne
lo stato**: un prezzo può venire da una versione in `BOZZA`. Su una versione in
`BOZZA` sia `trgfn_listini_righe_guard_stato` sia il guard dei componenti
(`trgfn_listini_righe_comp_guard_immutabilita_v5`) lasciano modificare tutto, per
scelta. Una riga di commessa che cita una riga di una versione in `BOZZA` ha quindi
un prezzo **non riproducibile**, qualunque cosa dica il legame.

## 2. Perché conta: il guard dei listini diventa cieco

`vendite.trgfn_listini_righe_guard_stato` decide se una riga di listino è
«propagata» con un `EXISTS` su `commesse_attivita` e `attivita_fatturabili`. È
`SECURITY INVOKER`, e le due tabelle hanno la RLS per emittente
(`rls_*_ef_whitelist`, attraverso la commessa). Il listino ha
`emittente_soggetto_ruolo_id NOT NULL`, con RLS anch'essa per emittente.

* Se la riga di commessa cita **sempre** un listino del **proprio** emittente, chi
  vede il listino vede anche tutte le commesse che lo citano: il guard vede tutto.
* Se il modello ammette una riga di commessa dell'emittente Y che cita un listino
  dell'emittente X, chi lavora solo su X **non vede** quella commessa. Il guard
  trova zero righe, giudica la riga «non propagata» e la lascia modificare.
  È la forma «il guard giudica su un'assenza»: rifiuta solo per chi vede tutti e
  due gli emittenti.

Oggi il modello lo ammette, perché manca la regola del §1.

## 3. Proposta (da decidere)

**A — la regola sulla riga (raccomandata).** Un guard `BEFORE INSERT OR UPDATE OF
listino_versione_id, listino_riga_id` su `commesse_attivita` e
`attivita_fatturabili`:
1. se `listino_riga_id` è valorizzato, la riga appartiene a `listino_versione_id`,
   e quest'ultimo è valorizzato;
2. se `listino_versione_id` è valorizzato, il listino è dell'emittente della
   commessa;
3. se `listino_versione_id` è valorizzato, la versione **non è in `BOZZA`**: una
   riga di commessa non prende il prezzo da un listino che non è in vigore.
   (Da decidere a parte se anche il percorso rapido del resolver debba rifiutare
   una `BOZZA`, o se lì serva a un'anteprima legittima del contratto in bozza:
   la regola 3 vale comunque sulla riga di commessa.)

Chiude tutti e due i problemi **per costruzione**: con la regola, la cecità del §2
non ha un caso da cui partire. Copre ogni percorso (push, batch, riallinea, sblocca,
emissione), non solo la madre.
⚠️ Va letto sotto RLS: la lettura del listino dentro il guard deve rispondere
anche quando il chiamante non lo vede (`SECURITY DEFINER` di lettura, decisione
sul **valore**). Un listino invisibile non può valere come «coerente».

**B — solo il guard dei listini in `SECURITY DEFINER`.** L'`EXISTS` vedrebbe tutte
le righe. Chiude il §2 ma lascia la provenienza incoerente del §1. Insieme ad A è
difesa in profondità; da solo non basta.

## 4. Da censire prima di scrivere

* i percorsi che scrivono `listino_versione_id`/`listino_riga_id` (madre del push,
  `fn_accredita_riga_reso`, `fn_aggiungi_onere_commessa`, emissione, `UPDATE` del BE
  in `commesse_repository`);
* le righe di commessa esistenti che violerebbero la regola. Il progetto non è in
  produzione, ma un guard nuovo su `UPDATE` rifiuterebbe anche un riallineamento di
  una riga già incoerente;
* i pgTAP che costruiscono righe di commessa con un listino di un altro emittente,
  se ce ne sono.
