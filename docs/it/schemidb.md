## Organizzati per funzionalità e responsabilità:
<table>
  <thead>
    <tr>
      <th>Schema</th>
      <th>Descrizione</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong><a href="/it/dbzero/acquisti/">acquisti</a></strong></td>
      <td>
        Processi di approvvigionamento e ciclo passivo.
        <ul>
          <li>Esempi: <code>richieste_offerta</code>, <code>ordini_acquisto</code>, <code>ddt_acquisto</code>, <code>fatture_acquisto</code></li>
          <li>Integrazione con <em>listini fornitori</em> e condizioni d’acquisto</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="/it/dbzero/anagrafiche/">anagrafiche</a></strong></td>
      <td>
        Contiene tutte le tabelle legate all'anagrafica soggetti (persone fisiche e giuridiche).
        <ul>
          <li>Esempi: <code>soggetti</code>, <code>indirizzi</code>, <code>contatti</code></li>
          <li>Usa identificatori UUID e naming coerente</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="/it/dbzero/catalogo/">catalogo</a></strong></td>
      <td>
        Anagrafica articoli, attributi, UoM, listini e distinte base.
        <ul>
          <li>Esempi: <code>articoli</code>, <code>unita_misura</code>, <code>articoli_uom_operativa</code>, <code>listini</code>, <code>distinte_base</code></li>
          <li>Base dati per vendite, acquisti e magazzino</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="/it/dbzero/config/">config</a></strong></td>
      <td>
        Contiene tabelle di configurazione parametrica e lookup.
        <ul>
          <li>Esempi: <code>stati</code>, <code>nazioni</code>, <code>contatti_ruoli</code></li>
          <li>Normalizzazione forte, spesso referenziate da altri schemi</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="/it/dbzero/contabilita/">contabilita</a></strong></td>
      <td>
        ⛔ <strong>Schema VUOTO e fuori perimetro</strong> — zero tabelle, zero funzioni, zero viste.
        <ul>
          <li>⚠️ Questa scheda elencava <code>piano_conti</code>, <code>registrazioni</code>, <code>liquidazioni_iva</code>, <code>partite</code>: <strong>non esistono</strong>, erano intenzioni scritte come esempi (corretto 01-09-2026)</li>
          <li>Se un giorno servirà, sarà un <strong>aggancio a una contabilità esterna</strong>, e la forma del piano dei conti la detta il <strong>sistema di destinazione</strong> — non questo progetto</li>
          <li>⛔ Nessuna scrittura automatica da vendite/acquisti: non è implementata e non è prevista</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="/it/dbzero/magazzino/">magazzino</a></strong></td>
      <td>
        Logistica, ubicazioni e movimentazione fisica.
        <ul>
          <li>Esempi: <code>magazzini</code>, <code>ubicazioni</code>, <code>movimenti</code>, <code>costo_medio</code>, <code>inventari</code>, <code>trasferimenti</code></li>
          <li>La <strong>giacenza non è una tabella</strong>: è la vista <code>vw_giacenza</code>, somma del ledger <code>movimenti</code>. Stessa cosa per il valore (<code>vw_giacenza_valorizzata</code>).</li>
          <li><code>lotto</code> e <code>seriale</code> sono <strong>colonne</strong> di <code>movimenti</code>, non tabelle proprie.</li>
          <li>Tracciabilità e valorizzazione su UoM base</li>
          <li>⚠️ <strong>Modello disegnato, non in esercizio</strong> (misurato 21-08-2026): tutte le tabelle operative sono a 0 righe.</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="/it/dbzero/pagamenti/">pagamenti</a></strong></td>
      <td>
        Termini, metodi, scadenze e riconciliazioni.
        <ul>
          <li>Esempi: <code>termini_pagamento</code>, <code>metodi_pagamento</code>, <code>scadenze</code>, <code>riconciliazioni</code></li>
          <li>Supporto a incassi/pagamenti, effetti e matching</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="/it/dbzero/vendite/">vendite</a></strong></td>
      <td>
        Ciclo attivo: preventivi, ordini, DDT, fatture e resi.
        <ul>
          <li>Esempi: <code>preventivi</code>, <code>ordini</code>, <code>ddt</code>, <code>fatture</code>, <code>attivita_fatturabili</code></li>
          <li>Integrazione con pricing, fulfillment e contabilizzazione IVA</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="/it/dbzero/pratiche/">pratiche</a></strong></td>
      <td>
        Motore di workflow operativo: pratiche, flussi, giornale di bordo, stati e sospensioni.
        <ul>
          <li>Esempi: <code>pratiche</code>, <code>flussi</code>, <code>giornale</code>, <code>allegati_pratiche</code></li>
          <li>Ogni evento significativo (nuovo cliente, ordine, assistenza) genera una pratica tracciata</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="/it/dbzero/documenti/">documenti</a></strong></td>
      <td>
        Motore documentale parametrico: modelli, asset, documenti generati e file persistenti (render PDF).
        <ul>
          <li>Esempi: <code>template_documenti</code>, <code>template_asset</code>, <code>documenti_generati</code></li>
          <li>Genera i documenti ufficiali (es. preventivo, offerta) da template versionati</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="/it/dbzero/ui/">ui</a></strong></td>
      <td>
        Metadati di presentazione: liste configurabili, colonne, preset per profilo/emittente.
        <ul>
          <li>Esempi: <code>lista_definizione</code>, <code>lista_colonna</code>, <code>lista_preset</code>, <code>lista_preferenza_utente</code></li>
          <li>Personalizzazione delle liste senza logica di business</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="/it/dbzero/script/">script</a></strong></td>
      <td>
        Logica applicativa (viste e funzioni) legate ai processi ERP.
        Favorisce riuso, mantenibilità e isolamento della logica.
        <ul>
          <li>Esempi: <code>vw_clienti_attivi</code>, <code>fn_calcolo_fattura()</code></li>
          <li>Include anche: <code>fn_get_stradario_by_indirizzo()</code>, etc.</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="/it/dbzero/dbops/">dbops</a></strong></td>
      <td>
        Strumenti DB per DBA (vista/funzioni tecniche, metadata, monitoring).
        <ul>
          <li>Esempi: <code>vw_function_list</code>, <code>fn_foreign_keys_info(text)</code></li>
          <li>Nessuna logica applicativa, solo strumenti per DBA e manutentori</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="/it/dbzero/storico/">storico</a></strong></td>
      <td>
        Tabelle di audit/storico con versioning temporale dei dati. 
        Tutte le tabelle che richiedono "storicizzazione" saranno replicate qui
        <ul>
          <li>Esempi: <code>soggetti_storico</code>, <code>contratti_storico</code></li>
          <li>Usato per audit, confronto tra versioni, report du dati storici</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="/it/dbzero/maintenance/">maintenance</a></strong></td>
      <td>
        Centralizza i processi periodici e le attività di manutenzione del DB (schedulati tramite <code>pgAgent</code>).
        <ul>
          <li>Esempi: <code>job_run_log</code>, <code>apply_storicizza_defaults_job()</code>, <code>run_and_log(...)</code></li>
          <li>Best practice: tutte le procedure di manutenzione e i relativi log vivono qui</li>
          <li>Pattern standard: logging esecuzioni, advisory lock per evitare overlap, wrapper dei job</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong>public</strong></td>
      <td>
        Mostra solo tabelle pubbliche (non pubbliche), ad esempio version_info   
        <ul>
          <li>Esempi: <code>version_info</code>, <code>ecc...</code></li>
          <li>Solo tabelle o funzioni non pubbliche</li>
        </ul>
      </td>
    </tr>
  </tbody>
</table>



>
>
>## Navigazione per schema
>
- [acquisti](/it/dbzero/acquisti/)
- [anagrafiche](/it/dbzero/anagrafiche/)  
- [catalogo](/it/dbzero/catalogo/)  
- [config](/it/dbzero/config/)  
- [contabilita](/it/dbzero/contabilita/)
- [dbops](/it/dbzero/dbops/)  
- [documenti](/it/dbzero/documenti/)
- [magazzino](/it/dbzero/magazzino/)
- [maintenance](/it/dbzero/maintenance/)   
- [pagamenti](/it/dbzero/pagamenti/)   
- [pratiche](/it/dbzero/pratiche/)
- [script](/it/dbzero/script/)  
- [storico](/it/dbzero/storico/) 
- [ui](/it/dbzero/ui/)
- [vendite](/it/dbzero/vendite/) 

>
> In ciascuna pagina di schema troverai un unico indice con le tabelle, le funzioni e le view corrispondenti.
> 
---

---
{% include-markdown "signature-core.md" %}
