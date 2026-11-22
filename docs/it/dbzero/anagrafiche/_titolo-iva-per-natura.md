### 🧾 Il titolo IVA ammesso dalla natura del soggetto

> **Ultimo aggiornamento**: 22 novembre 2026

Un titolo IVA **in vigore** deve essere ammesso dalla natura di dettaglio del suo titolare: quali tipi di titolo
ammette ogni natura lo dice `config.tipi_titolo_iva_tipi_soggetto_dettaglio`. Una dichiarazione d'intento su un
privato entrerebbe nel risolutore e cambierebbe l'aliquota delle sue righe: la regola esiste per impedirlo.

#### In vigore: attivo, e valido almeno fino a oggi

Un titolo è in vigore se è attivo e la sua data di fine (`valido_al`) manca o non è ancora passata
(`anagrafiche.fn_titolo_iva_vigente`). «Oggi» è il giorno operativo, la data nel fuso dell'azienda, non quella
della sessione.

* La data d'inizio non conta: un titolo che comincia domani è già in vigore, perché è già scritto per cambiare
  delle aliquote.
* Un titolo chiuso o spento **non si giudica**: tenerne la storia non cambia nessuna aliquota, e una natura
  che oggi non lo ammetterebbe non lo rende sbagliato.
* Il criterio è la data di fine e non il solo `attivo`, perché un titolo con righe di ambito o con movimenti di
  plafond non si disattiva (`E_ATTIVO_BLOCK_CHILDREN_EXIST`): per farlo uscire si chiude `valido_al`.

#### Ammesso: una riga attiva della matrice

La domanda «questa natura ammette questo tipo di titolo?» ha una sede sola, `anagrafiche.fn_titolo_iva_ammesso`:
sì se c'è una riga **attiva** della matrice per la coppia. Nessuna riga vuol dire non ammesso: una natura senza
righe non è libera, è chiusa. Un soggetto senza natura non è titolare di niente.

#### Le strade che toccano la regola

La regola lega dati di tre tabelle, e ognuna delle strade che la cambiano ha il suo controllo:

| Che cosa cambia | Chi controlla | Rifiuto |
| --- | --- | --- |
| si scrive un titolo: nascita, cambio di tipo o di titolare, riattivazione, proroga della data di fine | `anagrafiche.trgfn_soggetti_titoli_iva_guard_tipo_soggetto` | `E_TITOLO_IVA_NON_AMMESSO_PER_TIPO_SOGGETTO`; soggetto senza natura: `E_DATO_FISCALE_SENZA_TIPO_SOGGETTO` |
| il soggetto cambia natura | `anagrafiche.fn_check_cambio_natura_soggetto`, che legge `anagrafiche.fn_titoli_iva_non_ammessi` e `anagrafiche.fn_titoli_iva_non_ammessi_conta` | titoli che chi agisce vede: `E_TIPO_SOGGETTO_CON_TITOLI_IVA_NON_AMMESSI`; titoli presentati ad altri emittenti: `E_CAMBIO_NATURA_TITOLI_ALTRI_EMITTENTI`; natura tolta con titoli in vigore: `E_DATO_FISCALE_SENZA_TIPO_SOGGETTO` |
| una riga della matrice smette di ammettere: spenta, cancellata o spostata su un'altra coppia | `config.trgfn_tipi_titolo_iva_tipi_soggetto_dettaglio_guard_ritiro`, che legge `anagrafiche.fn_titolo_iva_vigente_su_natura_esiste` | `E_TITOLO_IVA_AMMISSIONE_IN_USO` |

Tutte e tre giudicano solo i titoli in vigore. Per questo il rimedio è lo stesso: chi vuole cambiare la natura del
soggetto, o ritirare una riga della matrice, chiude prima i titoli che la nuova regola non ammette; chiusi, restano
come storia e non fermano più niente. Il passare del tempo non crea casi nuovi: un titolo può solo uscire dal
vigore, mai entrarci da solo.

#### ⭐ Perché due lettori girano sopra la RLS

I titoli sono visibili per emittente: un operatore vede solo quelli presentati agli emittenti del suo perimetro.
Il cambio di natura e il ritiro di una riga della matrice, invece, devono sapere di **tutti** i titoli del soggetto,
o un operatore potrebbe cambiare la natura di un soggetto che ha una dichiarazione presentata a un'altra azienda.

* `anagrafiche.fn_titoli_iva_non_ammessi` gira coi permessi di chi chiama: elenca i titoli che lui vede, e il tipo
  del primo dà il nome al rifiuto.
* `anagrafiche.fn_titoli_iva_non_ammessi_conta` gira coi privilegi del proprietario e risponde solo **quanti**
  sono in tutto. La differenza fra i due conteggi dice che ce ne sono di altri emittenti, senza dire quali.
* `anagrafiche.fn_titolo_iva_vigente_su_natura_esiste` gira coi privilegi del proprietario e risponde solo **sì o
  no**.

Da nessuno dei due lettori privilegiati escono protocollo, plafond o emittente di un titolo.

#### I test

`db/pgtap/anagrafiche/test-soggetti-titoli-iva-tipo-soggetto-v1.sql` prova la regola sulle tre strade: un tipo non
ammesso rifiutato col campo `tipo_titolo_iva_id`, un titolo scaduto che passa e la sua proroga rifiutata, un tipo
senza righe di matrice rifiutato, il ritiro di una riga in uso, il cambio di natura rifiutato per un titolo visibile
e per uno di un altro emittente (invisibile all'operatore), il cambio che passa dopo aver chiuso il titolo, il
titolo su un soggetto senza natura. Il test controlla anche che i due lettori privilegiati abbiano `pg_temp` in
coda al percorso di ricerca.
