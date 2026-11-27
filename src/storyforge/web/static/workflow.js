/* Gespräch und kreative Anschlussaktionen; die Geschäftsregeln bleiben im Python-Kern. */
state.turns = [];
state.pendingSource = null;
state.lastMetrics = null;
Object.assign(labels, {personal_conflict:'Persönlicher Konflikt', development:'Entwicklung',
  audio_potential:'Akustisches Potenzial', central_mystery:'Zentrales Geheimnis',
  fictional_assumptions:'Fiktionale Annahmen', research_questions:'Recherchefragen',
  weaknesses:'Mögliche Schwächen', mechanism_card_id:'Mechanismuskarte',
  alternative:'Alternative', kurzbeschreibung:'Kurzbeschreibung', veraenderte_elemente:'Veränderte Elemente',
  bewahrte_elemente:'Bewahrte Elemente', neue_moeglichkeiten:'Neue Möglichkeiten',
  kausale_konsequenzen:'Kausale Konsequenzen', dramaturgische_konsequenzen:'Dramaturgische Konsequenzen',
  figuren_und_geheimnisse:'Figuren und Geheimnisse', hoerspielpotenzial:'Hörspielpotenzial',
  ungeklaerte_auswirkungen:'Ungeklärte Auswirkungen', materialbezug:'Bezug zum Material',
  bedeutung:'Bedeutung', art:'Art des Befunds', bereich:'Analysebereich', status:'Status',
  used_card_ids:'Verwendete Wissenskarten', verwendete_karten_ids:'Verwendete Wissenskarten',
  schutzpruefungen:'Prüfung geschützter Elemente', voraussetzungen:'Voraussetzungen',
  risiken:'Risiken', staerken:'Stärken', offene_fragen:'Offene Fragen'});
renderObject = function (parent, object) {
  const details = new Set(['fictional_assumptions','research_questions','weaknesses',
    'used_card_ids','verwendete_karten_ids']);
  for (const [key, value] of Object.entries(object)) {
    if (['id','base_revision_id','revision_id','mechanism_card_id'].includes(key)) continue;
    if (details.has(key)) {
      if (!value?.length) continue;
      const extra = el('details', undefined, 'more');
      extra.append(el('summary', label(key)));
      renderValue(extra, key, value); parent.append(extra);
    } else renderValue(parent, key, value);
  }
};

const oldChooseProject = chooseProject;
chooseProject = async function (id) {
  state.turns = []; state.pendingSource = null;
  $('results').replaceChildren();
  await oldChooseProject(id);
};
const oldChooseBranch = chooseBranch;
chooseBranch = async function (id) {
  state.turns = []; state.pendingSource = null;
  $('results').replaceChildren();
  await oldChooseBranch(id);
};
const oldSources = sources;
sources = function () {
  const previous = $('source-select').value;
  oldSources();
  for (const turn of state.turns) {
    if (turn.role !== 'assistant' || turn.revision_id !== selectedRevision()?.id) continue;
    const option = el('option', 'Gespräch · ' + turn.content.slice(0, 50));
    option.value = 'turn:' + turn.id;
    $('source-select').append(option);
  }
  if ([...$('source-select').options].some(option => option.value === previous)) $('source-select').value = previous;
  sourceVisibility();
};

const oldRender = render;
render = function () {
  oldRender();
  $('revision-chip').textContent = selectedRevision() ? 'Aktueller Geschichtenstand' : 'Noch kein Projekt';
  $('creative-view').classList.toggle('conversation-layout', state.view === 'V01');
  $('run').textContent = ({V01:'Nachricht senden', V02:'Stoffkeime entwickeln', V03:'Geheimnis untersuchen',
                           V04:'Varianten entwickeln', V05:'Stoff kritisch prüfen'})[state.view] || 'Mit Modell arbeiten';
  $('task').placeholder = state.view === 'V01' ? 'Schreib, was du erkunden möchtest …' : 'Was möchtest du untersuchen?';
  $('task').rows = state.view === 'V01' ? 3 : 6;
};

function actionButton(labelText, callback) {
  const button = el('button', labelText, 'quiet');
  button.type = 'button'; button.onclick = callback;
  return button;
}
function follow(view, reference) {
  state.view = view;
  state.pendingSource = null;
  render();
  if ((view === 'V04' || view === 'V05') && reference) {
    const value = reference.kind === 'turn' ? 'turn:' + reference.id :
      'creative_run:' + reference.runId + (reference.candidateId ? ':' + reference.candidateId : '');
    const option = [...$('source-select').options].find(item => item.value === value);
    if (option) $('source-select').value = value;
    else notice('Diese Quelle ist veraltet oder für die aktive Variante nicht verfügbar.', true);
    sourceVisibility();
  } else {
    state.pendingSource = reference;
  }
  $('task').value = ({V01:'Vertiefe diesen Gedanken und zeige neue Möglichkeiten.',
    V03:'Untersuche das Geheimnis und konkurrierende Erklärungen.',
    V04:'Entwickle eine gezielte Variante dieses Ausgangsmaterials.',
    V05:'Prüfe dieses Ausgangsmaterial kritisch und bewahre seine Stärken.'})[view];
  $('task').focus();
}
function followActions(reference, includePreserve) {
  const actions = el('div', undefined, 'follow-actions');
  for (const [view, title] of [['V01','Im Gespräch vertiefen'],['V03','Geheimnis untersuchen'],
                               ['V04','Varianten entwickeln'],['V05','Kritisch prüfen']]) {
    actions.append(actionButton(title, () => follow(view, reference)));
  }
  if (includePreserve) actions.append(actionButton('Als Idee bewahren', includePreserve));
  return actions;
}
function messageCard(turn, incomplete = false) {
  const card = el('article', undefined, 'result-card ' + (turn.role === 'user' ? 'message-author' : 'message-assistant'));
  if (incomplete) card.classList.add('message-incomplete');
  card.append(el('div', incomplete ? 'Unvollständige Antwort · nicht gespeichert' :
    (turn.role === 'user' ? 'Autor' : 'STORYFORGE'), 'message-meta'));
  if (turn.role === 'assistant') card.append(renderMarkdown(turn.content));
  else card.append(el('p', turn.content));
  if (turn.role === 'assistant' && !incomplete && turn.id) {
    const reference = {kind:'turn', id:turn.id};
    card.append(followActions(reference, async () => {
      try {
        await api('/turns/' + turn.id + '/stage?project_id=' + state.project + '&branch_id=' + state.branch,
                  {method:'POST'});
        notice('Als Entwurf vorgemerkt. Eine verbindliche Übernahme benötigt deine ausdrückliche Freigabe.');
      } catch (error) { notice(error.message, true); }
    }));
  }
  return card;
}
conversation = async function () {
  if (!state.project || !state.branch) return;
  const project = state.project, branch = state.branch;
  const container = $('results');
  const atBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 90;
  const oldScrollTop = container.scrollTop;
  const turns = await api('/projects/' + project + '/turns?branch_id=' + branch);
  if (state.project !== project || state.branch !== branch || state.view !== 'V01') return;
  state.turns = turns;
  container.replaceChildren();
  if (!turns.length) container.append(el('div', 'Schreib den ersten Gedanken zu deiner Geschichte.', 'empty'));
  for (const turn of turns) container.append(messageCard(turn));
  sources();
  container.scrollTop = atBottom ? container.scrollHeight : oldScrollTop;
};
function partialAnswer(job) {
  const container = $('results');
  const atBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 90;
  let card = container.querySelector('[data-partial]');
  if (!card) { card = messageCard({role:'assistant', content:''}, true); card.dataset.partial = '1'; container.append(card); }
  card.querySelector('.markdown').replaceWith(renderMarkdown(job.partial || ''));
  if (atBottom) container.scrollTop = container.scrollHeight;
}

const oldShowResult = showResult;
showResult = function (data, view) {
  if (view === 'V01') return;
  oldShowResult(data, view);
  const cards = [...$('results').querySelectorAll(':scope > .result-card')];
  if (view === 'V02') {
    data.candidates.forEach((candidate, index) => {
      const reference = {kind:'run', runId:data.run_id, candidateId:candidate.id};
      cards[index]?.append(followActions(reference));
    });
  } else if (data.run_id && cards[0]) {
    cards[0].append(followActions({kind:'run', runId:data.run_id}));
  }
};

const oldRecord = record;
record = async function () {
  await oldRecord();
  for (const heading of $('record-view').querySelectorAll('.panel h3')) {
    if (heading.textContent === 'Revisionen') {
      for (const title of heading.parentElement.querySelectorAll('.item strong')) {
        title.textContent = title.textContent.replace(/ · [0-9a-f]{8}$/, '');
      }
    }
  }
  const buttons = [...$('record-view').querySelectorAll('.record-grid button')];
  buttons.forEach((button, index) => {
    const original = button.onclick;
    const run = state.runs[index];
    if (!run) return;
    button.onclick = async () => {
      await original();
      const details = $('record-view').firstElementChild;
      const sections = [...details.querySelectorAll(':scope > .item')];
      sections.forEach((section, candidateIndex) => {
        const candidate = run.candidates[candidateIndex];
        const reference = {kind:'run', runId:run.id, candidateId:run.manifest.procedure === 'V02' ? candidate?.id : null};
        section.append(followActions(reference, run.manifest.procedure === 'V02' && candidate?.id ? async () => {
          try {
            await api('/runs/' + run.id + '/candidates/' + candidate.id + '/stage', {method:'POST'});
            notice('Stoffkeim als Entwurf vorgemerkt. Eine verbindliche Übernahme benötigt deine Freigabe.');
          } catch (error) { notice(error.message, true); }
        } : null));
      });
    };
  });
};

run = async function () {
  if (!state.project || !state.branch) { notice('Lege zuerst ein Projekt an.', true); return; }
  if (!state.model) { notice('Ollama ist offline oder kein Modell installiert.', true); return; }
  const task = $('task').value.trim();
  if (!task) { notice('Schreibe zuerst eine Aufgabe.', true); return; }
  const options = {};
  if (state.view === 'V02') { options.count = Number($('count').value); options.reflect = $('reflect').checked; }
  if (state.view === 'V03') { options.mode = $('mode').value; options.given_truth = $('given-truth').value.trim() || null; }
  if (['V04','V05'].includes(state.view)) {
    const raw = $('source-select').value;
    if (raw === 'frei') options.source = {art:'frei', beschreibung:$('source-text').value.trim()};
    else if (raw.startsWith('turn:')) {
      const turn = state.turns.find(item => item.id === raw.slice(5));
      if (!turn) { notice('Gesprächsquelle ist nicht mehr verfügbar.', true); return; }
      options.source = {art:'frei', beschreibung:turn.content}; options.source_turn_id = turn.id;
    } else {
      const [art,id,candidate_id] = raw.split(':'); options.source = {art,id};
      if (candidate_id) options.source.candidate_id = candidate_id;
    }
    if (!options.source.beschreibung && options.source.art === 'frei') {
      notice('Beschreibe das Ausgangsmaterial.', true); return;
    }
  }
  if (state.view === 'V04') {
    options.operation = $('operation').value;
    options.erhalten = split('erhalten'); options.veraenderbar = split('veraenderbar');
    options.gezielt_aendern = split('gezielt-aendern'); options.moeglichkeiten = split('moeglichkeiten');
  }
  if (state.view === 'V05') {
    options.bereiche = [...$('options').querySelectorAll('input:checked')].map(item => item.value);
    if (!options.bereiche.length) { notice('Wähle mindestens einen Analysebereich.', true); return; }
  }
  if (state.pendingSource && ['V01','V03'].includes(state.view)) {
    if (state.pendingSource.kind === 'turn') options.source_turn_id = state.pendingSource.id;
    else { options.source_run_id = state.pendingSource.runId;
           if (state.pendingSource.candidateId) options.source_candidate_id = state.pendingSource.candidateId; }
  }
  const context = {project:state.project, branch:state.branch, view:state.view};
  try {
    const started = await api('/jobs', {method:'POST', body:JSON.stringify({project_id:context.project,
      branch_id:context.branch, procedure:context.view, task, model:state.model, options})});
    state.job = started.id; state.pendingSource = null;
    $('run').disabled = true; $('cancel').classList.remove('hidden');
    $('working').textContent = context.view === 'V01' ? 'Antwort entsteht …' : 'Modell arbeitet …';
    notice('Anfrage läuft. Du kannst weiter navigieren oder abbrechen.');
    if (context.view === 'V01') { $('task').value = ''; await conversation(); }
    poll(started.id, context);
  } catch (error) { notice(error.message, true); }
};
poll = async function (id, context) {
  while (true) {
    await new Promise(resolve => setTimeout(resolve, 350));
    let job;
    try { job = await api('/jobs/' + id); }
    catch (error) { notice(error.message, true); break; }
    const current = state.project === context.project && state.branch === context.branch && state.view === context.view;
    if (current && context.view === 'V01' && job.partial) partialAnswer(job);
    if (job.status === 'läuft' || job.status === 'abbruch angefordert') continue;
    if (state.job === id) {
      state.job = null; $('run').disabled = false; $('cancel').classList.add('hidden'); $('working').textContent = '';
    }
    if (current) {
      if (job.status === 'fertig') {
        if (context.view === 'V01') {
          await conversation();
          state.lastMetrics = job.result;
          const last = $('results').lastElementChild;
          if (last && job.result.wall_seconds != null) {
            const metrics = el('details', undefined, 'more'); metrics.append(el('summary', 'Antwortdaten'));
            const seconds = job.result.wall_seconds.toFixed(1) + ' s';
            const tokens = job.result.output_tokens == null ? 'nicht verfügbar' : String(job.result.output_tokens);
            const speed = job.result.generation_tokens_per_second == null ? 'nicht verfügbar' :
              job.result.generation_tokens_per_second.toFixed(1) + ' Token/s';
            metrics.append(el('p', `Dauer: ${seconds} · Ausgabetoken: ${tokens} · Tempo: ${speed}`)); last.append(metrics);
          }
        } else { showResult(job.result, context.view); await refreshRuns(); }
        notice('Ergebnis gespeichert. Der bestätigte Geschichtenstand ist unverändert.');
      } else {
        if (context.view === 'V01' && job.partial) partialAnswer(job);
        notice((job.error || 'Anfrage abgebrochen.') + (job.partial ? ' Die Teilantwort ist nicht gespeichert.' : ''), true);
      }
    }
    break;
  }
};

$('run').onclick = run;
$('task').addEventListener('keydown', event => {
  if (state.view === 'V01' && event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault(); if (!state.job) run();
  }
});
document.querySelectorAll('#nav button').forEach(button => button.onclick = () => {
  state.view = button.dataset.view; state.pendingSource = null; render();
});
render();
