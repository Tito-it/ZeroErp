### 🏢 I dati societari: chi decide che cosa, e da dove si scrivono

> **Ultimo aggiornamento**: 24 novembre 2026

I dati societari di un soggetto (forma giuridica, REA, capitale, socio unico, liquidazione, canale della
fattura elettronica, data di costituzione) stanno in `anagrafiche.dati_societari`, una riga al più per
soggetto. Tre livelli decidono che cosa la riga deve contenere, e ognuno ha il suo controllo.

#### La natura decide se ci sono

La natura del soggetto (`config.tipi_soggetto_dettaglio.dati_societari_policy`) dice se la riga è vietata,
facoltativa o pretesa:

| Policy | Che cosa vuol dire | Chi la tiene |
| --- | --- | --- |
| `NONE` (il privato) | la riga non può esserci | `anagrafiche.trgfn_dati_societari_guard_tipo_soggetto`, alla nascita della riga, per primo (fase `a05`: prima della forma e del canale) |
| `OPTIONAL` (ditta individuale, società di persone, ente non commerciale) | la riga può esserci o no | — |
| `REQUIRED` (società di capitali) | la riga deve esserci | `anagrafiche.trgfn_soggetti_guard_dati_societari_required`, al COMMIT, e il verbo di eliminazione, che non la toglie |

Un soggetto senza natura non ha una pretesa: la riga non si scrive (`E_DATI_SOCIETARI_TIPO_DETTAGLIO_NON_CONFIGURATO`),
e la sua assenza non è un errore.

#### La forma decide che cosa chiedere

Se la riga c'è, la forma giuridica c'è (la colonna è obbligatoria, e il verbo la rifiuta mancante con
`E_DATI_SOCIETARI_FORMA_GIURIDICA_OBBLIGATORIA`), e deve essere dello Stato del soggetto e
ammessa dalla sua natura, secondo la matrice `config.forme_giuridiche_tipi_soggetto_dettaglio`
(`anagrafiche.fn_forma_giuridica_ammessa`). Poi è la forma a chiedere REA e capitale, con le sue due policy:
una SRL li pretende, un'associazione vieta il capitale, una ditta individuale li lascia liberi. Il controllo è
di `anagrafiche.trgfn_dati_societari_guard_forma_giuridica`.

#### Il canale decide il recapito

Il canale della fattura elettronica (`destinatario_fe`) è facoltativo: `P` pretende la PEC, `C` il codice SDI;
senza canale i due recapiti sono liberi. Il codice SDI, quando c'è, ha la sua forma. Lo controlla
`anagrafiche.trgfn_dati_societari_guard_canale_fe`. Né il codice SDI né la PEC sono unici: un intermediario o
un commercialista servono più clienti.

#### ⛔ Una porta per scrivere, una per eliminare

L'applicazione legge la tabella e non la scrive: ha soltanto `SELECT`. Si scrive con
`anagrafiche.fn_scrivi_dati_societari`, che crea o aggiorna la riga con lo stato intero della sezione, e si
elimina con `anagrafiche.fn_elimina_dati_societari`, che rifiuta quando la natura la pretende. Il verbo di
scrittura prende prima la riga del soggetto sotto lucchetto: due salvataggi concorrenti della stessa sezione
non si urtano, il secondo aspetta e aggiorna. La riga è del suo soggetto e non passa a un altro
(`E_DATI_SOCIETARI_SOGGETTO_IMMUTABILE`). Alla nascita
del soggetto le due porte di creazione decidono se scriverla con
`anagrafiche.fn_scrivi_dati_societari_alla_nascita`. Le porte non portano regole: i controlli stanno nei
trigger della tabella e scattano da qualunque strada. Il permesso lo decide l'applicazione.

#### Che cosa si controlla subito e che cosa al COMMIT

* **Subito**: alla nascita della riga la natura che la ammette; a ogni scrittura la forma e il canale. Sono
  trigger `BEFORE ROW` e il rifiuto arriva sull'istruzione.
* **Al COMMIT**, perché soggetto e riga si scrivono in due istruzioni: la riga pretesa dalla natura
  (`anagrafiche.trgfn_soggetti_guard_dati_societari_required`), la forma ammessa dalla natura quando cambia la
  natura, e il suo paese quando il SUPER_ADMIN cambia lo stato del soggetto
  (`anagrafiche.trgfn_soggetti_guard_forma_giuridica_natura`), il soggetto e la forma attivi (i due
  controlli generici del padre attivo).

Un cambio di natura resta dentro la stessa macro-tipologia (una società di capitali può diventare di persone,
non un ente né una persona fisica): lo dice `anagrafiche.fn_check_cambio_natura_soggetto`. Dentro una stessa
operazione si cambia **prima la natura, poi la forma**: la forma nuova si giudica sulla natura nuova, e la
forma vecchia sulla natura nuova si giudica al COMMIT. Verso una natura che non ammette la riga (una ditta che
diventa privato) il cambio è rifiutato finché la riga c'è (`E_CAMBIO_NATURA_CON_DATI_SOCIETARI`): la si
elimina prima, col suo verbo.
