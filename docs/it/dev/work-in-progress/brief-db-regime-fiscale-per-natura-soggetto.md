# Brief DB — Il regime fiscale del soggetto segue la sua natura

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-10.
> **A chi:** team DB (`dev/db-tid`); richieste a BE/FE in §6.
> **Origine:** segnalazione di Tid sul drawer soggetti: su un privato compaiono «Cliente PA» e
> «Split payment», e la gestione dei titoli IVA offre tipi che a un privato non si applicano.
> **Stato:** 🔵 da fare.

## 1. Il caso di dominio

Due regole fiscali dipendono dalla **natura** del soggetto, non da una scelta libera:

* **Cliente PA e split payment** (art. 17-ter DPR 633/1972) riguardano la pubblica
  amministrazione e i soggetti che la legge vi assimila. Una persona fisica, privato o ditta
  individuale, non è mai una PA e non è mai in split payment.
* **I titoli IVA** hanno ciascuno un destinatario preciso:
  * la dichiarazione d'intento (`INTENTO`) la presenta un esportatore abituale, cioè un
    soggetto IVA: mai un privato;
  * l'uso industriale o agricolo (`USO_INDUSTRIALE`) presuppone un'attività d'impresa;
  * l'agevolazione per disabilità (`AGEVOLATA_104`) spetta a una persona fisica;
  * cooperativa sociale o ente del terzo settore (`COOPERATIVA`) è una forma giuridica, non una
    persona fisica.

Il modello ha già la sede per regole di questo tipo: `config.tipi_soggetto_dettaglio` porta
`sesso_policy`, `dati_societari_policy`, `piva_obbligatoria` e `cf_obbligatorio`, ognuna col suo
guard su `anagrafiche.soggetti`, ed è da lì che il drawer decide cosa mostrare. Il regime PA e i
titoli IVA sono rimasti fuori.

## 2. Che cosa dice oggi il modello

* `anagrafiche.soggetti.cliente_pa` e `split_payment`: `character(1)` NOT NULL, default `'N'`,
  con i soli `chk_soggetti_cliente_pa` e `chk_soggetti_split_payment` (`IN ('S','N')`). Nessun
  legame con il dettaglio.
* `config.tipi_titolo_iva`: codice, descrizione, `ha_plafond`. Nessun legame con il dettaglio.
* `anagrafiche.soggetti_titoli_iva`: i guard presidiano sovrapposizione, ambito e plafond, non chi
  può essere titolare.

I dettagli in configurazione (seed `80_data`): `PR` privato e `DI` ditta individuale (natura
`PF`), `SP` società di persone e `SC` società di capitali (`PG`), `ENC` ente non commerciale
(`ENTE`).

## 3. I due difetti

### 3.1 Un privato può essere «cliente PA» e «in split payment»

Il DB accetta `cliente_pa = 'S'` e `split_payment = 'S'` su qualunque soggetto. Non è un
dettaglio di interfaccia: i due flag decidono **chi versa l'IVA** in fattura (EsigibilitaIVA
`S` nella FatturaPA, `fn_esigibilita_iva`). Un flag sbagliato produce una fattura sbagliata, e
nessuno se ne accorge al salvataggio.

### 3.2 Un privato può avere un titolo IVA che non può avere

`soggetti_titoli_iva` accetta qualunque tipo su qualunque soggetto: una dichiarazione d'intento
su un privato entra nel risolutore (stadio B) e cambia l'aliquota delle sue righe.

## 4. Che cosa si chiede al team DB

### 4.1 Regime PA per dettaglio

Su `config.tipi_soggetto_dettaglio` due colonne gemelle delle policy esistenti, per esempio
`cliente_pa_ammesso` e `split_payment_ammesso` (`boolean NOT NULL DEFAULT false`); il nome e la
forma, boolean o `presenza_policy_enum`, li decide il team, purché siano simmetrici con
`sesso_policy`. Il valore per dettaglio:

| Dettaglio | Cliente PA | Split payment |
| --- | --- | --- |
| `PR` privato | no | no |
| `DI` ditta individuale | no | no |
| `SP` società di persone | da decidere con Tid | sì |
| `SC` società di capitali | sì | sì |
| `ENC` ente non commerciale | sì | sì |

`SC` ammette entrambi perché split payment e fatturazione PA raggiungono anche le società
controllate dalla PA. Il punto su `SP` resta aperto: §7.

Un guard `BEFORE INSERT OR UPDATE OF cliente_pa, split_payment, tipo_soggetto_dettaglio_id` su
`anagrafiche.soggetti`, sul modello di `trgfn_soggetti_guard_sesso_policy`: un valore `'S'` su un
dettaglio che non lo ammette è rifiutato, con `campo` nel contesto per il form. Il cambio di
dettaglio rientra nel perimetro: una società che diventa privato non si porta dietro il flag.

Codice proposto: `E_REGIME_PA_NON_AMMESSO` (uno solo, col campo nel contesto), più la policy di
messaggio e il ripiego senza `%s`.

### 4.2 Titoli IVA per dettaglio

Una matrice di configurazione `config.tipi_titolo_iva_tipi_soggetto_dettaglio`, sullo schema di
`tipi_soggetto_dettaglio_tipi_indirizzo`. Proposta di seed, da validare con Tid:

| Titolo | Dettagli ammessi |
| --- | --- |
| `INTENTO` | `DI`, `SP`, `SC`, `ENC` |
| `USO_INDUSTRIALE` | `DI`, `SP`, `SC`, `ENC` |
| `AGEVOLATA_104` | `PR` |
| `COOPERATIVA` | `SC`, `ENC` |

Un guard su `anagrafiche.soggetti_titoli_iva` (INSERT e UPDATE di `tipo_titolo_iva_id` e
`soggetto_id`): il tipo deve essere ammesso per il dettaglio del soggetto. ⛔ Per simmetria va
presidiato anche l'altro lato: un soggetto che cambia dettaglio non può lasciare titoli **attivi**
che il nuovo dettaglio non ammette. Lo stesso vale per una riga tolta dalla matrice mentre ci
sono titoli attivi che la usano.

Codice proposto: `E_TITOLO_IVA_NON_AMMESSO_PER_TIPO_SOGGETTO`.

⚠️ Senza righe per un dettaglio, la regola non deve diventare «tutto libero» in silenzio: se il
team sceglie quel ripiego, va dichiarato nel commento del guard, come fa
`trgfn_indirizzi_soggetti_guard_tipo_indirizzo`.

### 4.3 Le righe che già violano

Prima dei guard si **censiscono** i soggetti con un flag `'S'` non ammesso e i titoli attivi non
ammessi. Sono dati di sviluppo, ma non si correggono d'ufficio: cosa farne lo si decide con Tid,
guardandoli.

## 5. pgTAP

* privato `PR` con `cliente_pa = 'S'` → `E_REGIME_PA_NON_AMMESSO`, campo `cliente_pa`;
* ditta individuale `DI` con `split_payment = 'S'` → rifiuto, campo `split_payment`;
* società `SC` con entrambi `'S'` → accettato;
* società `SC` con `split_payment = 'S'` che passa a `PR` → rifiuto;
* privato `PR` con titolo `INTENTO` → `E_TITOLO_IVA_NON_AMMESSO_PER_TIPO_SOGGETTO`;
* privato `PR` con titolo `AGEVOLATA_104` → accettato;
* soggetto con titolo `INTENTO` attivo che passa a `PR` → rifiuto;
* soggetto con titolo `INTENTO` **disattivato** che passa a `PR` → accettato.

## 6. Ricadute su BE/FE (dopo l'applicazione)

* **Lookup dei tipi soggetto** (`lookupTipiSoggettoDettaglio`): espone le due colonne nuove.
* **Drawer soggetti** (`SoggettoDrawer.vue`, sezione «Dati fiscali»): oggi la sezione è sempre
  visibile in modifica. Diventa condizionata dalle colonne nuove, nel composable
  `useSoggettoForm`, come `showSesso` e `showDatiSocietari`. Se il dettaglio non ammette un flag,
  il form lo riporta a `'N'` (stessa logica della proposta ritirata del sesso).
* **Drawer titoli IVA**: il lookup dei tipi titolo si filtra per il dettaglio del soggetto. Endpoint
  e parametro li decide il BE; la regola resta nel guard DB, il filtro è solo comodità.
* **Codici errore**: i due codici nuovi vogliono policy generata, ripiego e chiavi i18n.
* La sezione «Titoli IVA» del drawer resta visibile anche sul privato: per lui `AGEVOLATA_104` è
  legittimo.

## 7. Decisioni aperte per Tid

1. **`SP` e cliente PA.** Una società di persone può essere destinataria della fatturazione PA?
   Il seed della §4.1 lo lascia aperto.
2. **`DI` e `AGEVOLATA_104`.** L'agevolazione è della persona. Se la stessa persona ha anche
   una ditta individuale, si registra sul soggetto `PR` o anche sul `DI`? Il seed della §4.2
   ammette solo `PR`.
3. **Legame fra i due flag.** `cliente_pa = 'S'` implica `split_payment = 'S'`? Non sempre: ci
   sono operazioni escluse dallo split anche verso la PA. Per questo il brief non chiede il
   vincolo, ma la decisione va presa esplicitamente.

## 8. Fuori perimetro, da verificare

`anagrafiche.fornitori` ha un suo `split_payment` (`fornitori_service`, `bools=(…)`), che non
è stato toccato dalla salita dei flag del cliente su `soggetti` (D8). Questo brief non ne ha
verificato il significato. Vanno controllate due cose: che cosa rappresenta sul lato passivo, e
se un fornitore privato può averlo `true`. Se il difetto è lo stesso, rientra in questo brief
come §4.4.
