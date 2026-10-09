# Brief DB — Il privato può essere fornitore, senza inventarsi una sede legale

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-09.
> **A chi:** team DB (`dev/db-tid`); richieste a BE/FE in §6.
> **Origine:** smoke `smoke-test-soggetti.sh` (assegnazione ruoli) e la domanda di Tid
> «un'azienda può comprare da un privato?» del 2026-10-09.
> **Stato:** 🔵 da fare.

## 1. Il caso di dominio

Un privato senza partita IVA non emette fattura, ma un'azienda **compra** da lui: una
prestazione occasionale (ricevuta, con ritenuta d'acconto quando chi paga è sostituto
d'imposta) o la vendita occasionale di un bene usato. Il privato è quindi un **fornitore**
legittimo (decisione di Tid, 2026-10-09).

Il modello lo prevede già in due punti:

* la natura: `config.tipi_ruoli_nature_ammesse` ammette FORNITORE (`FO`) per la natura `PF`, cioè
  per il privato `PR` e per la ditta individuale `DI`;
* l'anagrafica: il privato `PR` ha la P.IVA non obbligatoria e il codice fiscale obbligatorio
  (`config.tipi_soggetto_dettaglio`), e `anagrafiche.fornitori` porta già `ritenuta_acconto` e
  `ritenuta_aliquota`. **Non serve un flag «soggetto non IVA»**: è il tipo `PR`.

## 2. Che cosa dice oggi la configurazione (contratto, dal seed `80_data`, 2026-10-09)

Gli indirizzi obbligatori del ruolo `FO` (`config.tipi_ruolo_tipi_indirizzo`, tipo ruolo 2):

| Riga | Tipo indirizzo | Obbligatorio | Ripiego |
| --- | --- | --- | --- |
| 13 | `SEDELEG` (sede legale) | sì | — |
| 2 | `FATT` (fatturazione) | sì | `SEDELEG` |
| 4, 5 | `SPED`, `POSTA` | no | `SEDELEG` |

Gli indirizzi ammessi per il privato `PR` (`config.tipi_soggetto_dettaglio_tipi_indirizzo`,
dettaglio 1): `RES`, `DOMFISC`, `FATT`, `POSTA`, `SPED`, `CON`. **La sede legale non c'è**, e
correttamente: un privato non ha una sede.

Per confronto, la ditta individuale `DI` ammette `SEDELEG`, e quindi oggi può essere fornitore
senza forzature.

## 3. I due difetti

### 3.1 Il fornitore privato pretende una sede legale

`trgfn_soggetti_ruoli_guard_indirizzi_required` vuole sul ruolo un `SEDELEG` (riga 13, senza
ripiego). Per un privato il requisito non si può soddisfare con un dato vero.

### 3.2 Gli indirizzi del RUOLO non rispettano la natura del soggetto

Il controllo «questo tipo di indirizzo è ammesso per questo tipo soggetto» esiste solo sugli
indirizzi **del soggetto** (`trgfn_indirizzi_soggetti_guard_tipo_indirizzo`, su
`anagrafiche.indirizzi_soggetti`). Sugli indirizzi **del ruolo** (`anagrafiche.indirizzi`,
`soggetto_ruolo_id`) gira solo `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`, che guarda la
matrice del **ruolo**.

⛔ Conseguenza: oggi un privato **può** diventare fornitore, ma solo dando al ruolo una «sede
legale», cioè un dato falso che sul soggetto il DB rifiuterebbe. «Privato mai fornitore» non è
la regola in vigore: è un blocco che si aggira scrivendo un dato sbagliato. È un'asimmetria del
modello, e va chiusa insieme al 3.1: corretto solo il 3.1, il 3.2 resta un varco per qualunque
ruolo.

## 4. Che cosa si chiede al team DB

### 4.1 Il requisito del fornitore, soddisfacibile da un privato

**Proposta (A):** sulla riga 13 (`FO` × `SEDELEG`) il ripiego `DOMFISC`, dal CSV di `80_data`.

Il motivo sul modello: ciò che il ruolo chiede è **l'indirizzo fiscale** del fornitore. Per una
società il domicilio fiscale segue la sede legale (art. 58 DPR 600/1973: il comune della sede
legale); per una persona fisica è il domicilio fiscale. «Sede legale, o in sua assenza il domicilio fiscale» dice la stessa cosa
per tutte le nature, ed è lo stesso schema che il cliente usa già (riga 1: `FATT` con ripiego
`DOMFISC`).

Effetto sulle società: un fornitore società potrebbe nascere col solo `DOMFISC` sul ruolo. Il
soggetto società ha comunque `SEDELEG` obbligatorio sui suoi indirizzi (dettagli 3 e 4), quindi
il dato resta.

**Alternativa (B), da valutare se la (A) non regge:** la matrice degli indirizzi del ruolo per
**natura** (o dettaglio), non solo per tipo ruolo. È strutturale (una colonna e i due guard da
riscrivere) e oggi nessun altro ruolo la richiede.

⚠️ La riga 2 (`FATT`, ripiego `SEDELEG`) resta com'è: il guard legge un solo ripiego, e
portarlo a `DOMFISC` romperebbe la società che ha la sola sede legale. Per il privato `FATT`
nasce dall'auto-clone del backend (`create_indirizzi_ruolo`).

### 4.2 Gli indirizzi del ruolo rispettano la natura del soggetto

Un guard (o un ramo di `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`) su
`anagrafiche.indirizzi`: il tipo di indirizzo deve essere ammesso anche da
`config.tipi_soggetto_dettaglio_tipi_indirizzo` per il dettaglio del soggetto del ruolo, con la
stessa logica (e lo stesso limite dichiarato, «senza matrice per quel dettaglio: libero») di
`trgfn_indirizzi_soggetti_guard_tipo_indirizzo`. Codice: si riusa
`E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`, con `campo` nel contesto.

⚠️ Il vincolo nuovo non deve trovare righe che lo violano: prima del guard si **censiscono** gli
indirizzi di ruolo non ammessi per il dettaglio del soggetto. Sono dati di sviluppo, ma non si
correggono d'ufficio: cosa farne lo si decide con Tid, guardandoli.

### 4.3 Il messaggio di `E_INDIRIZZO_OBBLIGATORIO_MANCANTE`

Oggi: «Indirizzo obbligatorio mancante per soggetto 85214 per tipo ruolo 1, fallback id 8», cioè
id al posto dei nomi, e due segnaposti che dicono il falso: «soggetto» riceve l'id del
**soggetto_ruolo**, «fallback id» riceve il tipo **richiesto**, non il ripiego (corpo del guard,
argomenti del `VARIADIC`). Si chiede
una frase che nomini il **ruolo** e il **tipo di indirizzo** (e il ripiego, se c'è), per esempio
«Il ruolo Fornitore richiede l'indirizzo Sede legale (o Domicilio fiscale)». Lo stesso vale per
`E_TIPO_INDIRIZZO_NON_PERMESSO`, che riporta `tipo_ruolo_id`.

## 5. pgTAP

Casi da costruire:

* privato `PR` con ruolo `FO` e `DOMFISC` sul ruolo → accettato;
* privato `PR` con ruolo `FO` senza `SEDELEG` né `DOMFISC` → `E_INDIRIZZO_OBBLIGATORIO_MANCANTE`;
* privato `PR` con un indirizzo di ruolo `SEDELEG` → rifiuto (`E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`);
* società con ruolo `FO` e `SEDELEG` sul ruolo → accettato (nessuna regressione);
* ditta individuale con ruolo `FO` e `SEDELEG` → accettato.

## 6. Ricadute su BE/FE (dopo l'applicazione)

* Il flusso Fornitori (`fornitori_service`) crea un fornitore privato passando gli indirizzi del
  soggetto: da provare sul DB vero, con un test che costruisce il privato.
* Dal 2026-10-09 l'endpoint generico `POST /soggetti/{id}/ruoli/` rifiuta `FO` (ha il suo flusso),
  quindi il fornitore privato passa solo dal flusso Fornitori.
* Se il guard del 4.2 tocca percorsi esistenti, la lista di chi scrive indirizzi di ruolo è:
  `SoggettiService.create_indirizzi_ruolo` (clienti, fornitori, assegnazione ruolo) e la view
  `RuoloIndirizziView`.

## 7. Fuori perimetro: il documento passivo del fornitore privato

Il fornitore privato non manda fatture dallo SdI. Quando si aprirà il ciclo della fattura
passiva (cantiere acquisti, oggi col solo modello, e `contabilita` vuoto) serviranno:

* la registrazione manuale del documento come **ricevuta o nota compenso**, non come fattura;
* il calcolo della ritenuta d'acconto e del netto da pagare (i dati del fornitore ci sono già);
* la scadenza del versamento F24 e i dati per la Certificazione Unica.

Nessun brief aperto lo prevede oggi: va annotato fra le decisioni aperte del cantiere acquisti
(PROJECT_CONTEXT), non risolto qui.
