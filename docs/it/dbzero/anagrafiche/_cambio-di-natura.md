### 🔁 Il cambio di natura del soggetto

> **Ultimo aggiornamento**: 24 novembre 2026

La **natura** di un soggetto è la sua natura di dettaglio (`tipo_soggetto_dettaglio_id`: privato, ditta
individuale, società di capitali, società di persone, ente…), e ogni natura di dettaglio appartiene a una
**macro-tipologia** (`config.tipi_soggetto`: persona fisica, persona giuridica, ente). Dalla natura
dipendono la partita IVA, i dati societari e la loro forma giuridica, il sesso, il regime PA, i titoli IVA
ammessi, i tipi d'indirizzo ammessi e obbligatori, i ruoli che il soggetto può avere. Cambiarla vuol dire
che una parte di ciò che il soggetto ha può non andare più bene: il database lo dice prima, e rifiuta il
cambio finché c'è anche un solo motivo aperto.

#### Che cosa si può cambiare

* **Dentro la stessa macro-tipologia**: una ditta individuale diventa un privato, una società di persone
  diventa una società di capitali. Il passaggio a un'altra macro-tipologia è sempre rifiutato, da qualunque
  strada arrivi: una società non diventa una persona fisica, un ente non diventa una società.
* **Da nessuna natura a una natura**: un soggetto senza natura la riceve senza il controllo della
  macro-tipologia e dei documenti, che hanno bisogno di una natura di partenza.
* ⛔ **Da una natura a nessuna natura: mai.** Una natura scritta non si svuota, per nessuno: è la regola
  dell'identificativo applicata alla natura. Passare da una natura a nessuna e poi a un'altra, in due
  salvataggi, salterebbe la macro-tipologia, i documenti e le nature ammesse dai ruoli, che hanno bisogno
  di una natura di partenza.

#### ⛔ Il cambio non pulisce niente

Nessun trigger e nessuna funzione cancella, chiude o azzera dati per far passare un cambio di natura. Il
database rifiuta ed **elenca tutti i motivi**; chi lavora li toglie a mano, con gli strumenti che ha già (il
drawer dei titoli IVA, gli indirizzi, l'eliminazione dei dati societari), e poi riprova. La regola vale anche
per il SUPER_ADMIN: il suo diritto di correggere codice fiscale e partita IVA non si estende al cambio di
natura.

#### I motivi di rifiuto, nell'ordine

La regola è una sola, `anagrafiche.fn_check_cambio_natura_soggetto`, e restituisce i motivi in un ordine
fisso. Il primo è anche quello che il rifiuto solleva; gli altri viaggiano nel contesto dell'errore, perché
l'applicazione li possa mostrare tutti.

| # | Motivo | Codice | Come si toglie |
| --- | --- | --- | --- |
| 0 | La natura nuova è nessuna natura | `E_CAMBIO_NATURA_VERSO_NESSUNA` | Non si toglie: si sceglie un'altra natura della stessa famiglia. Quando c'è, è l'unico motivo restituito |
| 1 | La natura nuova è di un'altra macro-tipologia | `E_CAMBIO_NATURA_ALTRA_MACRO_TIPOLOGIA` | Non si toglie. Quando c'è, è l'unico motivo restituito: gli altri non hanno senso |
| 2 | La partita IVA nasce o sparisce (una delle due nature non ne ha) e il soggetto compare già in un documento, in qualunque ruolo | `E_CAMBIO_NATURA_CON_DOCUMENTI` | Non si toglie: il documento porta l'identità fiscale di allora. Fra due nature che tengono tutte e due la partita IVA i documenti non bloccano |
| 3 | La natura nuova non ha partita IVA e la riga ne porta una | `E_CAMBIO_NATURA_PIVA_NON_APPLICABILE` | Svuotandola nello stesso salvataggio, cosa che solo il SUPER_ADMIN può fare: una partita IVA già scritta è bloccata |
| 4 | Il flag di Pubblica Amministrazione è a `S` e la natura nuova non lo ammette | `E_CLIENTE_PA_NON_AMMESSO` | Il flag a `N`, nello stesso salvataggio |
| 5 | Lo split payment è a `S` e la natura nuova non lo ammette | `E_SPLIT_PAYMENT_NON_AMMESSO` | Il flag a `N`, nello stesso salvataggio |
| 6 | Titoli IVA vigenti che la natura nuova non ammette, visibili a chi agisce | `E_TIPO_SOGGETTO_CON_TITOLI_IVA_NON_AMMESSI` | Chiudendo i titoli |
| 7 | Titoli IVA vigenti non ammessi, presentati ad altre aziende e quindi invisibili a chi agisce | `E_CAMBIO_NATURA_TITOLI_ALTRI_EMITTENTI` | Chi li vede: il SUPER_ADMIN o l'altra azienda. Il motivo dice solo quanti sono |
| 8 | La natura nuova non ha dati societari e il soggetto ne ha | `E_CAMBIO_NATURA_CON_DATI_SOCIETARI` | Con l'eliminazione dei dati societari, prima del cambio |
| 9 | Indirizzi del soggetto di un tipo che la natura nuova non ammette | `E_CAMBIO_NATURA_INDIRIZZI_NON_AMMESSI` | Eliminando quegli indirizzi |
| 10 | Indirizzi dei ruoli del soggetto di un tipo che la natura nuova non ammette | `E_CAMBIO_NATURA_INDIRIZZI_RUOLO_NON_AMMESSI` | Eliminando quegli indirizzi dal ruolo |

I motivi sono di due famiglie. Quelli **della riga del soggetto** (la partita IVA e i due flag del regime PA)
si giudicano sui valori **proposti**: chi li corregge nello stesso salvataggio della natura passa. Quelli
**di altre tabelle** (documenti, titoli, dati societari, indirizzi) si tolgono prima, in un altro posto.

#### Ciò che va dato, non tolto

Alcune conseguenze del cambio non sono dati da togliere ma da **dare**: la forma giuridica che la natura nuova
ammette, il sesso che pretende, la partita IVA o il codice fiscale obbligatori, i dati societari che chiede,
gli indirizzi obbligatori del soggetto e dei suoi ruoli. Non sono motivi della regola: li giudicano i guard
che esistono già, sullo stato a cui si arriva, e chi cambia natura li fornisce nello stesso salvataggio o
nella stessa transazione.

| Che cosa | Chi lo controlla | Quando |
| --- | --- | --- |
| Gli undici motivi | `anagrafiche.trgfn_soggetti_guard_cambio_natura` | Subito, all'UPDATE della riga, prima degli altri guard `a10` di `soggetti` (l'immutabilità di CF, P.IVA e stato parla prima, in `a05`) |
| Codice fiscale e partita IVA obbligatori | `anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori` | Subito |
| Il sesso | `anagrafiche.trgfn_soggetti_guard_sesso_policy` | Subito |
| I flag del regime PA (anche fuori dal cambio) | `anagrafiche.trgfn_soggetti_guard_regime_pa` | Subito |
| La forma giuridica dei dati societari (natura e paese) | `anagrafiche.trgfn_soggetti_guard_forma_giuridica_natura` | Al COMMIT, anche quando cambia lo stato |
| I dati societari che la natura pretende | `anagrafiche.trgfn_soggetti_guard_dati_societari_required` | Al COMMIT |
| Gli indirizzi obbligatori del soggetto | `anagrafiche.trgfn_soggetti_guard_indirizzi_required` | Al COMMIT |
| Gli indirizzi obbligatori dei ruoli | `anagrafiche.trgfn_soggetti_guard_obbligatori_ruoli` | Al COMMIT |

I controlli al COMMIT sono constraint trigger differiti: dentro la transazione l'ordine dei passi è libero, e
conta lo stato finale. Fa eccezione la forma giuridica: il suo guard sui dati societari è immediato e confronta
la forma con la natura salvata, quindi si cambia **prima la natura, poi la forma**.

#### ⭐ Una regola, due lettori

La stessa funzione alimenta il rifiuto e la proposta. Il guard la chiama coi valori della riga che si sta
salvando; il picker delle nature, `anagrafiche.fn_nature_proponibili_soggetto`, la chiama per ogni natura
con la riga salvata, e dice quali sono ammesse e, delle altre, il primo motivo. Ciò che il picker propone è
ciò che il guard accetta: non esiste una seconda lista delle nature «modificabili».

#### Chi vede che cosa

La regola gira coi permessi di chi la chiama, perché i titoli IVA sono visibili per azienda: chi agisce vede
i propri, e il motivo 6 nomina il primo di questi. Due letture vanno sopra la visibilità, e rispondono il
minimo: quanti titoli non ammessi ci sono in tutto (`anagrafiche.fn_titoli_iva_non_ammessi_conta`, da cui il
motivo 7) e il tipo del primo documento in cui il soggetto compare (`anagrafiche.fn_soggetto_primo_documento`).
Nessuna delle due restituisce un id, un numero o un'azienda.
