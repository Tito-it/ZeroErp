### 🪪 L'identificativo fiscale del soggetto

> **Ultimo aggiornamento**: 24 novembre 2026

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

Il doppione lo dice **l'indice**, e solo lui. Le due porte di creazione (`anagrafiche.fn_crea_soggetto_pf`
e `anagrafiche.fn_crea_soggetto_pg`) non lo cercano prima: traducono la violazione di quell'indice,
riconosciuta per nome, in `E_ADMIN_CF_DUPLICATO`, con il campo (il codice fiscale per una persona fisica,
la partita IVA per una società che la passa) e la frase «identificativo fiscale». Così la ditta individuale
di chi è già un privato nasce, il doppione vero ha il suo codice, e anche due creazioni concorrenti dello
stesso soggetto ricevono lo stesso rifiuto. Una scrittura diretta che urta l'indice riceve il `23505` del
database.

#### ⛔ Un identificativo scritto non si cambia

Stato, CF e P.IVA sono la chiave: cambiarli farebbe di un soggetto un altro. Per questo:

* un valore scritto non si cambia e non si svuota;
* un campo vuoto si riempie: l'identità passa da incompleta a completa, e da lì in poi il campo è bloccato;
* riscrivere lo stesso valore non è un cambio;
* l'errore di battitura lo corregge solo il SUPER_ADMIN.

Lo stato non è mai vuoto, quindi per lui la regola si riduce all'ultima riga: lo cambia solo il SUPER_ADMIN.
Quando lo cambia, al COMMIT si rilegge anche la forma giuridica dei dati societari, che è di un paese
(`E_FORMA_GIURIDICA_PAESE`). Uno stato portato a vuoto non si sostituisce con lo stato proposto: lo rifiuta
il guard, e per il SUPER_ADMIN la colonna (`NOT NULL`). Lo stato proposto vale solo per chi nasce.

La regola sta in un posto solo, `anagrafiche.fn_id_fiscale_bloccato`, che risponde sul valore del campo e su
chi agisce. La leggono in due:

* il guard `anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile`, che rifiuta la scrittura
  (`E_SOGGETTO_ID_FISCALE_IMMUTABILE`, col campo) col valore che il campo aveva. Sta in fase `a05`: parla
  prima della presenza e del formato, così a chi svuota una P.IVA scritta dice «non si cambia» e non «è
  obbligatoria»;
* il form, attraverso le tre righe di `dbops.lock_columns_conditional` su `codice_fiscale`, `partita_iva` e
  `stato_id`,
  che chiamano `anagrafiche.fn_soggetto_id_fiscale_bloccato` (la stessa regola letta sulla riga) e che
  `dbops.fn_non_editable_fields` valuta per dire quali campi spegnere.

Il form spegne così esattamente ciò che il database rifiuta. Il registro, da solo, non blocca niente: a
bloccare è il guard.

#### ⭐ La forma che il database confronta

Codice fiscale, partita IVA e P.IVA di gruppo si scrivono in **una forma sola**: maiuscole, nessuno spazio,
e un campo vuoto è `NULL`. La dà il database a ogni scrittura, da qualunque strada arrivi, col trigger
`trg_soggetti_a01_normalize_ins_upd` (`anagrafiche.trgfn_soggetti_normalize`), che gira prima di tutti i
guard. Per questo:

* lo stesso CF scritto in minuscolo urta l'indice come quello in maiuscolo;
* riscrivere in minuscolo un CF scritto non è un cambio, e passa anche a chi non può cambiarlo;
* una stringa vuota o di soli spazi è un campo vuoto: la presenza obbligatoria la rifiuta
  (`E_PIVA_OBBLIGATORIA`, `E_CF_OBBLIGATORIO`), e svuotare così un dato scritto è uno svuotamento.

Il formato si giudica quando cambia ciò che giudica (CF, P.IVA, P.IVA di gruppo, stato, natura): un soggetto
con un CF che una configurazione più severa non accetta più resta modificabile negli altri campi. Le regole
del formato scritte oggi sono italiane; uno stato senza validatore passa.
