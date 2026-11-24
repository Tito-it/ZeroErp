### 🧩 Il guard di ruolo di una specializzazione

> **Ultimo aggiornamento**: 24 novembre 2026

Una **specializzazione di ruolo** è la tabella che porta i dati propri di un ruolo d'impresa (il fornitore, il
vettore, il gestore…) e nomina, con `soggetto_ruolo_id`, la riga di `anagrafiche.soggetti_ruoli` che dice «questo
soggetto ha questo ruolo». La chiave esterna garantisce che quella riga esista; il guard di ruolo garantisce che
sia **del ruolo giusto**: una riga dei fornitori punta a un ruolo `FO`, mai al ruolo cliente o vettore dello stesso
soggetto.

#### Un corpo solo, cambia il codice del ruolo

Le trigger function della famiglia hanno tutte lo stesso corpo: passano `soggetto_ruolo_id` e il codice del ruolo
atteso a `script.fn_guard_soggetto_ruolo`, e riscrivono la colonna col valore che questa restituisce, che è
quello passato. Il controllo sta solo lì.

| Trigger function | Tabella | Ruolo |
| --- | --- | --- |
| `trgfn_bank_guard_ruolo_bank_branches` | `bank_branches` | `BANK_B` |
| `trgfn_clienti_guard_ruolo_cliente` | `clienti` | `CL` |
| `trgfn_emittenti_fiscali_guard_ruolo_emi_fis` | `emittenti_fiscali` | `EF` |
| `trgfn_fornitori_guard_ruolo_fornitore` | `fornitori` | `FO` |
| `trgfn_gestori_guard_ruolo_gestore` | `gestori` | `GE` |
| `trgfn_psp_guard_ruolo_psp` | `psp` | `PSP` |
| `trgfn_resellers_guard_ruolo_reseller` | `resellers` | `RE` |
| `trgfn_vettori_guard_ruolo_vettore` | `vettori` | `VT` |

Il guard dei clienti è dell'area dei clienti, ma è lo stesso corpo. Fra le specializzazioni, le filiali bancarie
sono l'unica in cui più righe condividono un ruolo: un ruolo `BANK_B` ha tutte le sue filiali (l'unicità è su ruolo,
ABI e CAB); le altre hanno un vincolo unico sul solo `soggetto_ruolo_id`, una riga per ruolo.

#### Quando scatta

Prima di ogni inserimento e di ogni modifica della riga, qualunque colonna cambi: anche una modifica che non tocca
il ruolo lo ricontrolla.

#### Che cosa risponde

* `E_SOGGETTI_RUOLI` — il ruolo non è passato, non esiste, o è di un altro tipo. Un solo codice per i tre casi:
  il messaggio non dice quale. Scattando prima della scrittura, il guard parla anche prima del `NOT NULL` della
  colonna.
* `E_COD_INT_RUOLO` — il codice del ruolo atteso non è in `config.tipi_ruoli`: un difetto di configurazione, non
  dell'operatore.

#### ⛔ Che cosa non fa

* **Non crea il ruolo.** Verifica soltanto: la riga di `soggetti_ruoli` la crea chi scrive la specializzazione
  (la funzione di creazione del ruolo, o il chiamante), prima.
* **Non guarda il soggetto.** La delegata saprebbe confrontare anche il soggetto, ma il guard non glielo passa;
  che il soggetto sia attivo, o che la sua natura ammetta il ruolo, lo controllano altri trigger, su
  `soggetti_ruoli` (la natura alla nascita del ruolo).
* **Non vede il ruolo che cambia, e non serve.** Su `soggetti_ruoli` né il soggetto né il tipo si cambiano:
  due lucchetti (`E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE`, `E_SOGGETTO_RUOLO_TIPO_IMMUTABILE`). Un ruolo è
  «questo soggetto, questo tipo»: quello sbagliato si toglie e si mette quello giusto. Per questo la
  specializzazione non resta mai su un ruolo che nel frattempo è diventato di un altro tipo.
* **Non dipende da chi scrive.** Gira coi permessi di chi scrive, e `soggetti_ruoli` non ha visibilità per azienda:
  ogni ruolo esistente si vede.
