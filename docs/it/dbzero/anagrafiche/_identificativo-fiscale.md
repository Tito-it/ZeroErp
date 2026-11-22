### 🪪 L'identificativo fiscale del soggetto

> **Ultimo aggiornamento**: 22 novembre 2026

Un soggetto si riconosce dal suo **stato** e dal suo **identificativo fiscale**. La colonna generata
`id_fiscale_univoco_cf_piva` lo ricava da codice fiscale e partita IVA: vale tutti e due, separati da uno
spazio, quando ci sono entrambi e sono diversi; altrimenti quello dei due che c'è. L'indice unico
`uq_soggetto_idstato_id_fiscale_univoco` vieta due soggetti dello stesso stato con lo stesso identificativo.
Un soggetto senza CF e senza P.IVA non ha identificativo, e non urta nessuno.

#### ⭐ L'identificativo è la coppia, non il solo codice fiscale

Con CF e P.IVA diversi la chiave è la coppia: lo stesso codice fiscale può stare su due soggetti che hanno
partite IVA diverse, o su un soggetto con la P.IVA e su un altro senza. È il caso della persona che è anche
titolare di una ditta individuale: il privato e la ditta hanno lo stesso CF e sono due soggetti. Il modello
lo ammette; nessuna regola dice se debba ammetterlo per ogni natura.

#### ⛔ Un identificativo scritto non si cambia

CF e P.IVA sono la chiave: cambiarli farebbe di un soggetto un altro. Per questo:

* un valore scritto non si cambia e non si svuota;
* un campo vuoto si riempie: l'identità passa da incompleta a completa, e da lì in poi il campo è bloccato;
* riscrivere lo stesso valore non è un cambio;
* l'errore di battitura lo corregge solo il SUPER_ADMIN.

La regola sta in un posto solo, `anagrafiche.fn_id_fiscale_bloccato`, che risponde sul valore del campo e su
chi agisce. La leggono in due:

* il guard `anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile`, che rifiuta la scrittura
  (`E_SOGGETTO_ID_FISCALE_IMMUTABILE`) col valore che il campo aveva;
* il form, attraverso le due righe di `dbops.lock_columns_conditional` su `codice_fiscale` e `partita_iva`,
  che chiamano `anagrafiche.fn_soggetto_id_fiscale_bloccato` (la stessa regola letta sulla riga) e che
  `dbops.fn_non_editable_fields` valuta per dire quali campi spegnere.

Il form spegne così esattamente ciò che il database rifiuta. Il registro, da solo, non blocca niente: a
bloccare è il guard.

#### ⚠️ Che cosa la regola oggi non copre

* **Il database non normalizza CF e P.IVA.** Le maiuscole e gli spazi li toglie solo chi crea il soggetto con
  `anagrafiche.fn_crea_soggetto_pf` o `anagrafiche.fn_crea_soggetto_pg`; una scrittura diretta li lascia come
  sono. Il validatore italiano accetta un codice fiscale in minuscolo, e quel codice non urta lo stesso codice
  in maiuscolo: l'unicità è sul testo scritto.
* **Lo stato non è bloccato.** È metà della chiave, ma nessun guard ne ferma il cambio: un soggetto può
  passare a un altro stato, e con lui l'identificativo cambia perimetro.
* **Una stringa vuota conta come scritta.** Non è NULL: il campo vuoto così scritto è bloccato, e
  l'identificativo la porta dentro. La rifiuta solo il validatore italiano, e solo per un campo che la natura
  prevede: fuori dall'Italia, o come partita IVA di un privato, passa.
