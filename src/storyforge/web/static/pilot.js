// Optionale, vom normalen Geschichtenprojekt getrennte SF-005-Testwerkstatt.
(() => {
  const byId = id => document.getElementById(id);
  const make = (tag, value, css) => {
    const node = document.createElement(tag);
    if (value !== undefined) node.textContent = String(value);
    if (css) node.className = css;
    return node;
  };
  async function call(path, options) {
    const response = await fetch('/api/pilot' + path, {
      ...options, headers: {'Content-Type': 'application/json'}
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  }
  let group = localStorage.getItem('storyforge-pilot-group');
  let running = null;
  let revealed = false;
  const status = (message, error=false) => {
    const node = byId('pilot-status');
    node.textContent = message;
    node.classList.toggle('danger', error);
  };
  function label(text, value) {
    const row = make('p');
    row.append(make('strong', text + ': '), document.createTextNode(String(value ?? 'nicht verfügbar')));
    return row;
  }
  function ratingForm(run) {
    const form = make('div', undefined, 'pilot-rating');
    const fields = [['fascination','Faszination'],['originality','Originalität'],
      ['mystery','Geheimnisqualität'],['logic','Innere Logik'],
      ['emotion','Emotionale Bedeutung'],['audio','Hörspielpotenzial'],
      ['develop','Weiterentwicklungswunsch']];
    for (const [key,title] of fields) {
      const wrapper = make('label', title);
      const select = make('select');
      select.dataset.rating = key;
      for (const [value,caption] of [['','Nicht zutreffend / überspringen'],
        ...[1,2,3,4,5].map(x => [String(x),String(x)])]) {
        const option = make('option', caption); option.value = value; select.append(option);
      }
      wrapper.append(select); form.append(wrapper);
    }
    const notes = make('textarea'); notes.placeholder = 'Freie Anmerkungen';
    form.append(notes);
    const save = make('button','Bewertung speichern','quiet');
    save.onclick = async () => {
      const rating = {notes: notes.value};
      for (const select of form.querySelectorAll('select')) {
        rating[select.dataset.rating] = select.value ? Number(select.value) : null;
      }
      try {
        await call('/ratings/' + run.blind_id,{method:'POST',body:JSON.stringify(rating)});
        status('Bewertung gespeichert.'); await refresh();
      } catch (error) {status(error.message,true);}
    };
    form.append(save); return form;
  }
  async function refresh() {
    if (!group) return;
    const [runs, report] = await Promise.all([
      call('/groups/' + group + '/blind'),call('/groups/' + group + '/report')]);
    byId('pilot-controls').classList.remove('hidden');
    byId('pilot-group-label').textContent = 'Vergleich ' + group.slice(0,8) +
      ' · ' + report.case.id + ' · ' + report.model;
    byId('pilot-repetition').max = String(report.repetitions);
    const root = byId('pilot-results'); root.replaceChildren();
    for (const run of runs) {
      const card = make('article',undefined,'result-card');
      card.append(make('h5','Ergebnis ' + run.blind_id.slice(0,8)),label('Status',run.status));
      if (run.error) card.append(label('Fehler',run.error));
      for (const candidate of run.candidates || []) {
        const section = make('div',undefined,'item');
        section.append(make('strong',candidate.title),make('p',candidate.description),
          label('Mechanismus',candidate.mechanism),label('Hörspielpotenzial',candidate.audio_potential));
        const details = make('details');
        details.append(make('summary','Vollständiges Ergebnis'),
          make('pre',JSON.stringify(candidate.details,null,2)));
        section.append(details);
        card.append(section);
      }
      if (run.status === 'fertig') card.append(run.rated ? make('p','Bewertet') : ratingForm(run));
      root.append(card);
    }
    for (const [id,format] of [['pilot-json','json'],['pilot-md','markdown']]) {
      const a = byId(id); a.href = '/api/pilot/groups/' + group + '/export/' + format + '?reveal=' + revealed;
      a.download = 'storyforge-pilot-' + group.slice(0,8) + (format === 'json' ? '.json' : '.md');
    }
  }
  byId('pilot-create').onclick = async () => {
    const model = byId('model-select').value;
    if (!model) {status('Wähle zuerst ein lokal verfügbares Ollama-Modell.',true); return;}
    try {
      const created = await call('/groups',{method:'POST',body:JSON.stringify({
        case_id:byId('pilot-case').value,model,
        repetitions:Number(byId('pilot-repetitions').value),
        temperature:Number(byId('pilot-temperature').value),
        num_predict:Number(byId('pilot-tokens').value)
      })});
      group = created.id; revealed = false; localStorage.setItem('storyforge-pilot-group',group);
      status('Vergleich angelegt. Starte die Verfahren einzeln.'); await refresh();
    } catch (error) {status(error.message,true);}
  };
  byId('pilot-run').onclick = async () => {
    if (!group || running) return;
    try {
      const arm = byId('pilot-arm').value, repetition = Number(byId('pilot-repetition').value);
      const job = await call('/groups/' + group + '/runs?arm=' + arm + '&repetition=' + repetition,{method:'POST'});
      running = job.id; byId('pilot-cancel').classList.remove('hidden');
      byId('pilot-run').disabled = true; status('Modell arbeitet …');
      while (running === job.id) {
        await new Promise(resolve => setTimeout(resolve,600));
        const state = await fetch('/api/jobs/' + job.id).then(x => x.json());
        if (state.status === 'läuft' || state.status === 'abbruch angefordert') continue;
        status(state.status === 'fertig' ? 'Ergebnis lokal gespeichert.' : state.error || state.status,
          state.status !== 'fertig'); break;
      }
    } catch (error) {status(error.message,true);} finally {
      running = null; byId('pilot-run').disabled = false;
      byId('pilot-cancel').classList.add('hidden'); await refresh();
    }
  };
  byId('pilot-cancel').onclick = async () => {
    if (running) await fetch('/api/jobs/' + running + '/cancel',{method:'POST'});
  };
  byId('pilot-reveal').onclick = async () => {
    try {
      const report = await call('/groups/' + group + '/report?reveal=true');
      revealed = true;
      const root = byId('pilot-revealed'); root.replaceChildren(make('h4','Auflösung'));
      for (const run of report.runs) {
        const card = make('div',undefined,'item');
        card.append(label('Ergebnis',run.blind_id.slice(0,8)),
          label('Verfahren / Wiederholung',run.arm + ' / ' + run.repetition),
          label('Modellaufrufe',run.metrics?.calls),
          label('Eingabetoken',run.metrics?.prompt_tokens),
          label('Ausgabetoken',run.metrics?.output_tokens),
          label('Laufzeit (s)',run.metrics?.wall_seconds));
        root.append(card);
      }
      await refresh();
    } catch (error) {status(error.message,true);}
  };
  call('/cases').then(cases => {
    const select = byId('pilot-case');
    for (const item of cases) {
      const option = make('option',item.id + ' · ' + item.title);
      option.value = item.id; select.append(option);
    }
    if (group) refresh().catch(error => {group = null; localStorage.removeItem('storyforge-pilot-group'); status(error.message,true);});
  }).catch(error => status(error.message,true));
})();
