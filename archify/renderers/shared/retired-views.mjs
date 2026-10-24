// meta.views (guided views / chapters) was retired in Archify 3.0.0. The
// schemas still accept the old shape so existing files keep validating, but no
// renderer reads it. This pure helper reports that silent drop as a
// non-blocking warning, shared by the renderers (human stderr) and the CLI
// receipts (validate/deliver/finalize diagnostics), like localeDiagnostics.

export function retiredViewsDiagnostics(diagramType, meta) {
  const views = meta?.views;
  if (!Array.isArray(views) || views.length === 0) return [];
  const chapters = views.map((view, index) => {
    const note = typeof view?.note === 'string' ? view.note.trim() : '';
    return {
      index,
      id: typeof view?.id === 'string' ? view.id : undefined,
      label: typeof view?.label === 'string' ? view.label : undefined,
      hasNote: note.length > 0,
      ...(note ? { note } : {}),
    };
  });
  const withNote = chapters.filter((chapter) => chapter.hasNote).length;
  const listing = chapters
    .map((chapter) => `${JSON.stringify(chapter.label ?? chapter.id ?? `#${chapter.index + 1}`)} (id ${chapter.id ?? 'missing'}; ${chapter.hasNote ? 'note will not appear' : 'no note'})`)
    .join(', ');
  const count = chapters.length;
  return [{
    code: 'meta/views-ignored',
    severity: 'warning',
    message: `meta.views is retired in Archify 3.x and ignored: ${count} ${count === 1 ? 'chapter' : 'chapters'} will not appear in the output (${withNote} with a note that will not appear): ${listing}. To keep this content, move status or honesty text into node labels/sublabels or cards and use the Viewer's Route and Lens for paths; see "Upgrading from 2.x" in CHANGELOG.md and schemas/README.md.`,
    subject: { diagramType, path: '/meta/views' },
    evidence: {
      chapters: count,
      chaptersWithNote: withNote,
      views: chapters.map(({ index, ...chapter }) => chapter),
    },
    supportedFixes: [
      'Remove meta.views once its content is carried over; renderers ignore it.',
      'Move status or honesty text from chapter notes into node labels or sublabels, or into cards.',
      'Use the Viewer Route and Lens to show paths and semantic roles instead of guided chapters.',
    ],
  }];
}
